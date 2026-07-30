from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.analyzer import BasicAnalyzer
from app.api.main import create_app
from app.config import Settings
from app.database import Database
from app.diagnosis import HeuristicDiagnoser
from app.llm import LocalDemoProvider, ProviderRouter
from app.models import EssaySubmission
from app.revision import LocalRevisionAligner
from app.services import RevisionService, SubmissionService


PROMPT = "Should universities provide more quiet study spaces?"


def _submission(student: str, text: str, *, when: datetime, stage: str = "first draft", source: int | None = None,
                prompt: str = PROMPT) -> EssaySubmission:
    return EssaySubmission(
        student_id=student, writing_prompt=prompt, genre="argumentative essay",
        draft_stage=stage, timed=False, tool_use="none", essay_text=text,
        submitted_at=when, revision_of_submission_id=source,
    )


def _stack(tmp_path):
    repository = Database(tmp_path / "revision.db")
    repository.initialize()
    revisions = RevisionService(repository)
    service = SubmissionService(
        repository, BasicAnalyzer(), HeuristicDiagnoser(),
        ProviderRouter(LocalDemoProvider(), LocalDemoProvider()),
        revision_service=revisions,
    )
    return repository, revisions, service


def _drafts(tmp_path, student: str = "REV001"):
    repository, revisions, service = _stack(tmp_path)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first = service.submit(_submission(
        student,
        "Universities should provide quiet rooms because students need concentration. "
        "However, libraries are often full. Therefore, unused rooms should open.",
        when=start,
    ))
    revised = service.submit(_submission(
        student,
        "Universities should provide more quiet study rooms because students need concentration. "
        "For example, libraries are often full during examinations. Therefore, unused seminar rooms should open.",
        when=start + timedelta(days=1), stage="revised draft", source=first.essay_id,
    ))
    return repository, revisions, service, first, revised, start


def test_first_revised_and_final_drafts_form_explicit_group(tmp_path):
    repository, revisions, service, first, revised, start = _drafts(tmp_path)
    assert repository.get_revision_group_for_submission(first.essay_id) is not None
    group = repository.get_revision_group_for_submission(revised.essay_id)
    assert group.member_submission_ids == [first.essay_id, revised.essay_id]
    final = service.submit(_submission(
        "REV001", "Universities should provide quiet rooms. Libraries are full, so unused seminar rooms should open.",
        when=start + timedelta(days=2), stage="final draft", source=revised.essay_id,
    ))
    group = revisions.group(group.revision_group_id)
    assert group.member_submission_ids == [first.essay_id, revised.essay_id, final.essay_id]
    assert group.current_revision_id == final.essay_id
    assert final.revision_snapshot is not None


def test_same_prompt_does_not_automatically_create_relationship(tmp_path):
    repository, _, service = _stack(tmp_path)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first = service.submit(_submission("NOAUTO", "One independent essay has sufficient text for analysis.", when=now))
    second = service.submit(_submission("NOAUTO", "Another independent essay has sufficient text for analysis.", when=now + timedelta(days=1)))
    assert repository.get_revision_group_for_submission(first.essay_id) is None
    assert repository.get_revision_group_for_submission(second.essay_id) is None


def test_candidates_are_same_student_and_require_explicit_choice(tmp_path):
    repository, revisions, service = _stack(tmp_path)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first = service.submit(_submission("CAND", "A prior essay has enough words for local analysis.", when=now))
    second = service.submit(_submission("CAND", "A later essay has enough words for local analysis.", when=now + timedelta(days=1)))
    service.submit(_submission("OTHER", "Another student's essay must not be offered.", when=now))
    candidates = revisions.candidates(second.essay_id)
    assert [item["essay_id"] for item in candidates] == [first.essay_id]
    assert repository.get_revision_group_for_submission(second.essay_id) is None


def test_cross_student_self_duplicate_and_cycle_links_are_rejected(tmp_path):
    repository, revisions, service = _stack(tmp_path)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    a = service.submit(_submission("A", "Student A wrote this sufficiently long first response.", when=now))
    b = service.submit(_submission("B", "Student B wrote this sufficiently long first response.", when=now))
    with pytest.raises(ValueError, match="Cross-student"):
        revisions.create_relationship(a.essay_id, b.essay_id)
    with pytest.raises(ValueError, match="cannot revise itself"):
        revisions.create_relationship(a.essay_id, a.essay_id)
    c = service.submit(_submission("A", "Student A independently wrote another sufficiently long response.", when=now + timedelta(days=1)))
    revisions.create_relationship(a.essay_id, c.essay_id)
    with pytest.raises(ValueError, match="already belongs"):
        revisions.create_relationship(a.essay_id, c.essay_id)
    with pytest.raises(ValueError, match="cycle"):
        revisions.create_relationship(c.essay_id, a.essay_id)


@pytest.mark.parametrize(
    ("source", "target", "expected"),
    [
        ("The proposal helps students.", "The proposal clearly helps students.", "lightly_modified"),
        ("The proposal helps students.", "The new proposal supports many students.", "heavily_modified"),
        ("The proposal helps students.", "The proposal helps students. It also saves time.", "inserted"),
        ("The proposal helps students. It also saves time.", "The proposal helps students.", "deleted"),
        ("The university should provide quiet rooms for students who need concentration.",
         "The university should provide quiet rooms. Students need concentration.", "split"),
        ("Students need quiet places. Libraries provide useful rooms.",
         "Students need quiet places and libraries provide useful rooms.", "merged"),
    ],
)
def test_local_alignment_types(source, target, expected):
    paragraphs, sentences, token_changes = LocalRevisionAligner().align(source, target)
    assert paragraphs and sentences
    assert expected in {item.alignment_type for item in sentences}
    assert token_changes["algorithm_version"] == "local-sequence-alignment-v0.5.0"


def test_revision_snapshot_has_observed_differences_and_no_ability_claim(tmp_path):
    _, _, _, first, revised, _ = _drafts(tmp_path)
    snapshot = revised.revision_snapshot
    assert snapshot.source_submission_id == first.essay_id
    assert snapshot.metric_changes
    assert any(item.metric_id == "word_count" and item.change is not None for item in snapshot.metric_changes)
    assert snapshot.revision_evidence[0]["revision_evidence_id"] == "R001"
    serialized = snapshot.model_dump_json().casefold()
    assert "shows ability improvement" not in serialized
    assert "not proficiency growth" in serialized


def test_major_rewrite_makes_uptake_not_assessable(tmp_path):
    repository, revisions, service = _stack(tmp_path)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first = service.submit(_submission("MAJOR", "Parks give residents exercise space and support community events.", when=now))
    target = service.submit(_submission(
        "MAJOR", "Quantum computers use qubits. Error correction remains difficult. Researchers test new materials.",
        when=now + timedelta(days=1), stage="revised draft", source=first.essay_id,
    ))
    snapshot = target.revision_snapshot
    assert snapshot.major_rewrite
    assert snapshot.comparability.status == "major_rewrite"
    assert all(item.status == "not_assessable" and item.confidence == "insufficient" for item in snapshot.uptake_candidates)


def test_incompatible_analyzer_versions_prevent_metric_and_diagnosis_comparison(tmp_path):
    repository, revisions, _, first, revised, _ = _drafts(tmp_path)
    with repository.connect() as connection:
        connection.execute("UPDATE analysis_runs SET analyzer_version='future-v9' WHERE essay_id=?", (revised.essay_id,))
    snapshot = revisions.recalculate(
        revised.revision_snapshot.revision_group_id, first.essay_id, revised.essay_id,
    )
    assert all(item.comparison_status == "incompatible_version" for item in snapshot.metric_changes)
    assert all(item.status == "not_comparable" for item in snapshot.diagnosis_trajectories)


def test_diagnosis_trajectory_never_calls_single_absence_solved(tmp_path):
    _, _, _, _, revised, _ = _drafts(tmp_path)
    statuses = {item.status for item in revised.revision_snapshot.diagnosis_trajectories}
    assert statuses <= {
        "still_observed", "not_currently_observed", "reduced_signal", "newly_observed",
        "changed_evidence", "not_comparable", "insufficient_evidence",
    }
    assert '"status":"solved"' not in revised.revision_snapshot.model_dump_json().casefold()


def test_revision_snapshot_recalculation_is_append_only(tmp_path):
    _, revisions, _, first, revised, _ = _drafts(tmp_path)
    group_id = revised.revision_snapshot.revision_group_id
    recalculated = revisions.recalculate(group_id, first.essay_id, revised.essay_id)
    history = revisions.history(group_id)
    assert len(history) == 2
    assert history[0].revision_snapshot_id != recalculated.revision_snapshot_id
    assert revisions.latest(group_id).revision_snapshot_id == recalculated.revision_snapshot_id


def test_revision_group_deduplicates_longitudinal_representatives(tmp_path):
    repository, revisions, service, first, revised, start = _drafts(tmp_path)
    final = service.submit(_submission(
        "REV001", "The final draft retains the same task but uses a concise argument and conclusion.",
        when=start + timedelta(days=2), stage="final draft", source=revised.essay_id,
    ))
    records = repository.list_longitudinal_records("REV001")
    included = [row["essay_id"] for row in records if row["is_longitudinal_representative"]]
    assert included == [final.essay_id]
    excluded = [row for row in records if not row["is_longitudinal_representative"]]
    assert len(excluded) == 2 and all(row["revision_exclusion_reason"] for row in excluded)


def test_revision_prompt_local_demo_and_evidence_validation(tmp_path):
    repository, _, _, _, revised, _ = _drafts(tmp_path)
    assert revised.provider.provider_name == "local-demo"
    assert revised.provider.prompt_version == "feedback-prompt-v0.5.0"
    assert revised.provider.schema_version == "structured-feedback-v0.5.0"
    assert revised.provider.feedback.revision is not None
    valid = {item["revision_evidence_id"] for item in revised.revision_snapshot.revision_evidence}
    assert set(revised.provider.feedback.revision.revision_evidence_ids) <= valid
    assert {item.status for item in revised.revision_snapshot.uptake_candidates} >= {"supported", "partially_supported"}
    assert all(item.source_type in {"student_source_sentence", "synthetic_practice_sentence"} for item in revised.provider.feedback.exercises)
    assert all(item.generation_version == "exercise-generator-v0.5.0" for item in revised.provider.feedback.exercises)
    stored = repository.get_feedback_record(revised.essay_id)
    assert stored["validation_status"] == "passed"


def test_revision_api_routes_and_structured_errors(tmp_path):
    settings = Settings(
        database_path=tmp_path / "api.db", llm_provider="local", deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com", deepseek_model="deepseek-chat",
    )
    with TestClient(create_app(settings)) as client:
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        base = _submission("APIREV", "A sufficiently long source essay supports a revision test.", when=now).model_dump(mode="json")
        first = client.post("/api/v1/submissions", json=base)
        assert first.status_code == 201
        target_payload = _submission(
            "APIREV", "A sufficiently long revised essay supports the explicit revision API test.",
            when=now + timedelta(days=1), stage="revised draft",
            source=first.json()["submission_id"],
        ).model_dump(mode="json")
        target = client.post("/api/v1/submissions", json=target_payload)
        assert target.status_code == 201
        group_id = target.json()["revision_snapshot"]["revision_group_id"]
        assert client.get(f"/api/v1/revisions/{group_id}").status_code == 200
        assert client.get(f"/api/v1/revisions/{group_id}/comparison").status_code == 200
        assert client.get(f"/api/v1/submissions/{target.json()['submission_id']}/revision-analysis").status_code == 200
        assert client.get(f"/api/v1/submissions/{target.json()['submission_id']}/revision-candidates").status_code == 200
        error = client.post("/api/v1/revisions", json={"source_submission_id": 9999, "target_submission_id": 9998})
        assert error.status_code == 404 and set(error.json()) == {"error"}


def test_migration_5_preserves_existing_essay_and_adds_revision_tables(tmp_path):
    repository, _, service = _stack(tmp_path)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    saved = service.submit(_submission("MIG5", "Existing data must remain after migration checks.", when=now))
    with repository.connect() as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        columns = {row[1] for row in connection.execute("PRAGMA table_info(essays)")}
        count = connection.execute("SELECT COUNT(*) FROM essays WHERE essay_id=?", (saved.essay_id,)).fetchone()[0]
    assert repository.migration_version() == 11
    assert {"revision_groups", "revision_snapshots"} <= tables
    assert {"revision_of_submission_id", "revision_group_id", "revision_sequence", "revision_stage", "original_draft_stage"} <= columns
    assert count == 1
