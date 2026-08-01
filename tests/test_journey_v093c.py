"""v0.9.3-C Learning Journey tests — semantic contract, states, demo workflow,
practice idempotency, revision semantics, and localization parity.

All journey behavior is exercised through normal service/repository pathways
with the local deterministic provider; no DeepSeek request is made.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

import pytest

os.environ.setdefault("LLM_PROVIDER", "local")

from app.database import Database  # noqa: E402
from app.config import Settings  # noqa: E402
from app.journey.service import (  # noqa: E402
    EVENT_VERSION,
    JourneyService,
)
from app.models import EssaySubmission  # noqa: E402
from app.practice.service import PracticeService  # noqa: E402
from app.services import build_submission_service  # noqa: E402


@pytest.fixture()
def repo(tmp_path):
    db = Database(tmp_path / "journey_test.db")
    db.initialize()
    return db


@pytest.fixture()
def services(repo):
    from app.config import load_settings

    settings = load_settings()
    submission_service = build_submission_service(settings, repo)
    practice_service = PracticeService(repo)
    journey = JourneyService(repo)
    return submission_service, practice_service, journey


def _essay(student_id: str, text: str, *, prompt: str = "What actions matter for sustainability?",
           draft_stage: str = "first draft", revision_of: int | None = None) -> EssaySubmission:
    return EssaySubmission(
        student_id=student_id,
        writing_prompt=prompt,
        genre="argumentative essay",
        draft_stage=draft_stage,
        timed=False,
        tool_use="none",
        essay_text=text,
        revision_of_submission_id=revision_of,
        submitted_at=datetime.now(timezone.utc),
    )


REPETITION_ESSAY = (
    "People should protect the environment. People should recycle more. "
    "People should save water. People should plant trees. People should reduce waste. "
    "People should use public transport. People should teach children about nature. "
    "People should value clean air."
)
SHORT_ESSAY = "The history of history is historical. The history of history is historical."


def _selected_priority(result):
    for signal in result.diagnosis.improvement_priorities:
        if getattr(signal, "selection_status", "") == "selected_priority":
            return signal
    return None


def _full_demo_journey(repo, submission_service, practice_service):
    """Build the complete conservative journey for a synthetic learner."""
    practice_service = practice_service or PracticeService(repo)
    original = submission_service.submit(_essay("JTEST", REPETITION_ESSAY), synthetic=True)
    priority = _selected_priority(original)
    assert priority is not None, "demo fixture must pass the Diagnostic Gate"
    target = practice_service.create_practice_target(
        "JTEST", original.essay_id, priority.diagnosis_id,
        "lexical_repetition_local", priority.interpretation,
        source_priority_id=f"PRIO-{original.essay_id}",
        evidence_ids=priority.source_metrics, gate_status="selected",
    )
    target = repo.save_practice_target(target)
    exercise = repo.save_exercise_instance(practice_service.generate_exercise(target, REPETITION_ESSAY))
    attempt = repo.save_exercise_attempt(
        practice_service.submit_attempt(exercise["exercise_id"], "JTEST", "A valid response reducing repetition.", 1)
    )
    evaluation = repo.save_practice_evaluation(
        practice_service.evaluate_attempt(attempt, target, REPETITION_ESSAY)
    )
    revised = submission_service.submit(
        _essay("JTEST", "Citizens should protect the environment. Communities can recycle more.",
               draft_stage="revised draft", revision_of=original.essay_id),
        synthetic=True,
    )
    group_id = None
    if revised.revision_group_summary:
        group_id = revised.revision_group_summary.revision_group_id
    response = repo.save_within_task_response_candidate(
        practice_service.evaluate_within_task_response(
            "JTEST", target, original.essay_id, revised.essay_id,
            revision_group_id=group_id, major_rewrite=False,
        )
    )
    return {
        "essay_id": original.essay_id,
        "revised_essay_id": revised.essay_id,
        "target": target,
        "exercise": exercise,
        "attempt": attempt,
        "evaluation": evaluation,
        "response": response,
    }


class TestJourneySemanticContract:
    def test_events_map_to_real_source_records(self, repo, services):
        submission_service, practice_service, journey = services
        _full_demo_journey(repo, submission_service, practice_service)
        data = journey.get_journey("JTEST")
        for event in data["events"]:
            assert event["source_record_type"]
            assert event["source_record_id"]
            assert event["deduplication_key"]

    def test_ordering_is_chronological_and_stage_aware(self, repo, services):
        submission_service, practice_service, journey = services
        records = _full_demo_journey(repo, submission_service, practice_service)
        events = journey.get_journey("JTEST")["events"]
        stage_order = {
            "writing_submitted": 1, "analysis_completed": 2, "feedback_available": 3,
            "feedback_priority_available": 4, "practice_available": 5, "exercise_attempted": 6,
            "practice_evaluation_recorded": 7, "revision_submitted": 8,
            "within_task_response_observed": 9,
        }
        # Events belonging to the original submission follow the natural chain.
        original_events = [
            e for e in events
            if e["submission_id"] == records["essay_id"] and e["event_type"] in stage_order
        ]
        order = [stage_order[e["event_type"]] for e in original_events]
        assert order == sorted(order), order
        assert any(e["event_type"] == "writing_submitted" for e in original_events)
        assert any(e["event_type"] == "feedback_priority_available" for e in original_events)
        # The revised submission precedes its response observation.
        revised_index = next(
            i for i, e in enumerate(events)
            if e["event_type"] == "revision_submitted" and e["submission_id"] == records["revised_essay_id"]
        )
        response_index = next(
            i for i, e in enumerate(events)
            if e["event_type"] == "within_task_response_observed"
        )
        assert revised_index < response_index

    def test_journey_deduplication(self, repo, services):
        submission_service, practice_service, journey = services
        _full_demo_journey(repo, submission_service, practice_service)
        events = journey.get_journey("JTEST")["events"]
        keys = [e["deduplication_key"] for e in events]
        assert len(keys) == len(set(keys))

    def test_event_versioning(self, repo, services):
        submission_service, practice_service, journey = services
        _full_demo_journey(repo, submission_service, practice_service)
        for event in journey.get_journey("JTEST")["events"]:
            assert event["event_version"] == EVENT_VERSION

    def test_event_limitations_always_present(self, repo, services):
        submission_service, practice_service, journey = services
        _full_demo_journey(repo, submission_service, practice_service)
        for event in journey.get_journey("JTEST")["events"]:
            assert event["limitations"], event["event_type"]

    def test_get_journey_is_read_only(self, repo, services):
        submission_service, practice_service, journey = services
        _full_demo_journey(repo, submission_service, practice_service)
        before = _table_counts(repo)
        journey.get_journey("JTEST")
        journey.get_journey("JTEST")
        after = _table_counts(repo)
        assert before == after

    def test_no_engagement_trace_written(self, repo, services):
        submission_service, practice_service, journey = services
        _full_demo_journey(repo, submission_service, practice_service)
        journey.get_journey("JTEST")
        with repo.connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM feedback_engagement_traces").fetchone()[0]
        assert count == 0


def _table_counts(repo):
    with repo.connect() as conn:
        return {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "essays", "analysis_runs", "feedback_records", "practice_targets",
                "exercise_instances", "exercise_attempts", "practice_evaluations",
                "within_task_response_candidates", "transfer_evidence_candidates",
                "feedback_engagement_traces",
            )
        }


class TestJourneyStates:
    def test_learner_not_found(self, repo, services):
        _, _, journey = services
        with pytest.raises(LookupError):
            journey.get_journey("S999")

    def test_learner_with_no_submissions(self, repo, services):
        _, _, journey = services
        with repo.connect() as conn:
            conn.execute(
                "INSERT INTO students (student_id, created_at, is_synthetic) VALUES (?, ?, 0)",
                ("EMPTY1", datetime.now(timezone.utc).isoformat()),
            )
        data = journey.get_journey("EMPTY1")
        assert data["state"] == "no_submissions"
        assert data["events"] == []

    def test_submission_without_analysis(self, repo, services):
        _, _, journey = services
        with repo.connect() as conn:
            conn.execute(
                "INSERT INTO students (student_id, created_at, is_synthetic) VALUES (?, ?, 0)",
                ("NOANA", datetime.now(timezone.utc).isoformat()),
            )
        submission = _essay("NOANA", REPETITION_ESSAY)
        repo.save_essay(submission)
        data = journey.get_journey("NOANA")
        assert data["state"] == "submission_without_analysis"
        types = {e["event_type"] for e in data["events"]}
        assert "insufficient_evidence" in types

    def test_analysis_without_priority(self, repo, services):
        submission_service, _, journey = services
        submission_service.submit(_essay("NOPRIO", SHORT_ESSAY, prompt="Should we act?"), synthetic=True)
        data = journey.get_journey("NOPRIO")
        assert data["state"] == "analysis_without_priority"
        types = {e["event_type"] for e in data["events"]}
        assert "feedback_without_priority" in types

    def test_feedback_no_practice_target(self, repo, services):
        submission_service, _, journey = services
        submission_service.submit(_essay("NOTARGET", REPETITION_ESSAY), synthetic=True)
        data = journey.get_journey("NOTARGET")
        assert data["state"] == "feedback_no_practice_target"

    def test_target_no_attempt(self, repo, services):
        submission_service, practice_service, journey = services
        original = submission_service.submit(_essay("NOATT", REPETITION_ESSAY), synthetic=True)
        priority = _selected_priority(original)
        target = practice_service.create_practice_target(
            "NOATT", original.essay_id, priority.diagnosis_id, "lexical_repetition_local",
            priority.interpretation, gate_status="selected",
        )
        repo.save_practice_target(target)
        data = journey.get_journey("NOATT")
        assert data["state"] == "target_no_attempt"

    def test_attempt_no_evaluation(self, repo, services):
        submission_service, practice_service, journey = services
        original = submission_service.submit(_essay("NOEVAL", REPETITION_ESSAY), synthetic=True)
        priority = _selected_priority(original)
        target = repo.save_practice_target(practice_service.create_practice_target(
            "NOEVAL", original.essay_id, priority.diagnosis_id, "lexical_repetition_local",
            priority.interpretation, gate_status="selected",
        ))
        exercise = repo.save_exercise_instance(practice_service.generate_exercise(target, REPETITION_ESSAY))
        repo.save_exercise_attempt(
            practice_service.submit_attempt(exercise["exercise_id"], "NOEVAL", "A response.", 1)
        )
        data = journey.get_journey("NOEVAL")
        assert data["state"] == "attempt_no_evaluation"

    def test_complete_journey_state(self, repo, services):
        submission_service, practice_service, journey = services
        _full_demo_journey(repo, submission_service, practice_service)
        data = journey.get_journey("JTEST")
        assert data["state"] == "journey_events"
        assert data["counts"]["submissions"] == 2
        assert data["counts"]["practice_targets"] == 1
        assert data["counts"]["exercise_attempts"] == 1
        assert data["counts"]["practice_evaluations"] == 1
        assert data["counts"]["within_task_responses"] == 1


class TestPracticeIdempotency:
    def test_exercise_instance_not_duplicated_by_read(self, repo, services):
        submission_service, practice_service, _ = services
        original = submission_service.submit(_essay("IDEM", REPETITION_ESSAY), synthetic=True)
        priority = _selected_priority(original)
        target = repo.save_practice_target(practice_service.create_practice_target(
            "IDEM", original.essay_id, priority.diagnosis_id, "lexical_repetition_local",
            priority.interpretation, gate_status="selected",
        ))
        repo.save_exercise_instance(practice_service.generate_exercise(target, REPETITION_ESSAY))
        instances = repo.list_exercise_instances(practice_target_id=target["practice_target_id"])
        assert len(instances) == 1
        # Repeated reads must not create instances.
        repo.list_exercise_instances(practice_target_id=target["practice_target_id"])
        assert len(repo.list_exercise_instances(practice_target_id=target["practice_target_id"])) == 1

    def test_empty_attempt_is_invalid_and_not_saved(self, repo, services):
        _, practice_service, _ = services
        attempt = practice_service.submit_attempt("EX000001", "IDEM", "   ", 1)
        assert attempt["status"] == "invalid_input"
        with repo.connect() as conn:
            assert conn.execute("SELECT COUNT(*) FROM exercise_attempts").fetchone()[0] == 0

    def test_revision_linkage(self, repo, services):
        submission_service, _, journey = services
        original = submission_service.submit(_essay("REVLINK", REPETITION_ESSAY), synthetic=True)
        revised = submission_service.submit(
            _essay("REVLINK", "Citizens should protect the environment.", draft_stage="revised draft",
                   revision_of=original.essay_id),
            synthetic=True,
        )
        with repo.connect() as conn:
            row = conn.execute("SELECT revision_of_submission_id FROM essays WHERE essay_id=?", (revised.essay_id,)).fetchone()
        assert row[0] == original.essay_id
        types = {e["event_type"] for e in journey.get_journey("REVLINK")["events"]}
        assert "revision_submitted" in types


class TestRevisionResponseSemantics:
    def test_no_mastery_or_causal_language(self, repo, services):
        submission_service, practice_service, _ = services
        _full_demo_journey(repo, submission_service, practice_service)
        with repo.connect() as conn:
            raw = conn.execute("SELECT response_json FROM within_task_response_candidates").fetchone()[0]
        text = json.dumps(json.loads(raw)).lower()
        for forbidden in ("has mastered", "mastered the", "learning gain", "proficiency increase",
                          "transfer achieved"):
            assert forbidden not in text
        # The conservative disclaimer may negate causation but never assert it.
        assert "not proof that feedback caused the change" in text

    def test_response_status_is_conservative(self, repo, services):
        submission_service, practice_service, _ = services
        _full_demo_journey(repo, submission_service, practice_service)
        with repo.connect() as conn:
            raw = json.loads(conn.execute("SELECT response_json FROM within_task_response_candidates").fetchone()[0])
        assert raw["observed_status"] in ("response_candidate_detected", "major_rewrite_limits_attribution")


class TestStudentIdNormalization:
    def test_normalize_trims_and_preserves_case(self):
        from app.ui.student_context import normalize_student_id

        assert normalize_student_id("  S02  ") == "S02"
        assert normalize_student_id("s02") == "s02"
        assert normalize_student_id("   ") == ""
        assert normalize_student_id("") == ""


class TestDemoWorkflow:
    def test_setup_status_cleanup_scope(self, tmp_path):
        db_path = tmp_path / "demo.db"
        Database(db_path).initialize()
        env = os.environ.copy()
        env["DATABASE_PATH"] = str(db_path)
        env["DATABASE_URL"] = f"sqlite:///{db_path}"
        env["LLM_PROVIDER"] = "local"
        env["PYTHONUTF8"] = "1"
        script = pathlib.Path("scripts/demo_journey.py").resolve()
        python = sys.executable

        def run(*args):
            return subprocess.run(
                [python, str(script), *args], cwd=str(pathlib.Path.cwd()),
                env=env, capture_output=True, text=True, encoding="utf-8",
                timeout=300,
            )

        first = run("--setup")
        assert first.returncode == 0, first.stderr
        second = run("--setup")
        assert second.returncode == 0
        assert "idempotent" in second.stdout

        db = Database(db_path)
        journey = JourneyService(db).get_journey("DEMO-001")
        assert journey["state"] == "journey_events"
        assert journey["counts"]["practice_targets"] == 1

        clean = run("--cleanup")
        assert clean.returncode == 0, clean.stderr
        with db.connect() as conn:
            assert conn.execute("SELECT COUNT(*) FROM students WHERE student_id='DEMO-001'").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM essays WHERE student_id='DEMO-001'").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM practice_targets WHERE student_id='DEMO-001'").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0


class TestLocalizationParity:
    def test_journey_keys_parity_and_nonempty(self):
        with open("locales/en.json", encoding="utf-8") as fh:
            en = json.load(fh)
        with open("locales/zh_CN.json", encoding="utf-8") as fh:
            zh = json.load(fh)
        journey_keys = [k for k in en if k.startswith("journey_")]
        assert journey_keys
        for key in journey_keys:
            assert key in zh, f"missing zh key: {key}"
            assert en[key].strip(), f"empty en value: {key}"
            assert zh[key].strip(), f"empty zh value: {key}"
        practice_keys = ["practice_loading", "practice_exercise_loaded",
                         "practice_evaluation_label", "practice_evaluation_completion",
                         "practice_evaluation_action"]
        for key in practice_keys:
            assert key in en and key in zh
            assert en[key] and zh[key]


class TestS02Regression:
    def test_s02_journey_returns_events_not_error(self, repo):
        """S02-style learner with essays/feedback renders events, not an error.

        Uses a fresh DB with the same record pattern; the real S02 regression is
        exercised through the live browser integration layer.
        """
        submission_service = build_submission_service(load_settings(), repo)
        submission_service.submit(_essay("S02", REPETITION_ESSAY), synthetic=True)
        submission_service.submit(_essay("S02", "A second independent draft.", prompt="Another prompt"), synthetic=True)
        journey = JourneyService(repo).get_journey("S02")
        assert journey["learner_found"] is True
        assert journey["events"]
        assert journey["state"] in ("analysis_without_priority", "feedback_no_practice_target")


class TestJourneyApi:
    """Route-level coverage for the new v0.9.3-C endpoints (real HTTP)."""

    @pytest.fixture()
    def client(self, tmp_path):
        from app.api.main import create_app
        from fastapi.testclient import TestClient

        settings = Settings(
            database_path=tmp_path / "api_journey.db", llm_provider="local",
            deepseek_api_key=None, deepseek_base_url="https://example.invalid",
            deepseek_model="deepseek-test",
        )
        app = create_app(settings)
        with TestClient(app) as c:
            yield c

    @pytest.fixture()
    def journeyed_client(self, client):
        # Build the complete journey through the public API.
        submission = {
            "student_id": "JAPI", "writing_prompt": "What actions matter for sustainability?",
            "genre": "argumentative essay", "draft_stage": "first draft", "timed": False,
            "tool_use": "none", "essay_text": REPETITION_ESSAY,
        }
        r = client.post("/api/v1/submissions", json=submission)
        assert r.status_code == 201, r.text
        essay_id = r.json()["submission_id"]
        diagnosis = r.json()["diagnosis"]
        priority = next(
            (s for s in diagnosis.get("improvement_priorities", [])
             if s.get("selection_status") == "selected_priority"),
            None,
        )
        assert priority is not None
        target = client.post("/api/v1/practice-targets", json={
            "student_id": "JAPI", "source_submission_id": essay_id,
            "source_diagnosis_id": priority["diagnosis_id"],
            "target_code": "lexical_repetition_local",
            "target_label": priority["interpretation"],
            "gate_status": "selected",
        }).json()
        exercise = client.post(
            f"/api/v1/practice-targets/{target['practice_target_id']}/exercises",
            json={"source_text": REPETITION_ESSAY},
        ).json()
        attempt = client.post(
            f"/api/v1/exercises/{exercise['exercise_id']}/attempts",
            json={"student_id": "JAPI", "response_text": "A valid response reducing repetition."},
        ).json()
        return client, essay_id, target, exercise, attempt

    def test_journey_endpoint_returns_events(self, journeyed_client):
        client, essay_id, _, _, _ = journeyed_client
        r = client.get("/api/v1/students/JAPI/journey")
        assert r.status_code == 200
        data = r.json()
        assert data["state"] in ("attempt_no_evaluation", "revision_no_response", "journey_events")
        types = {e["event_type"] for e in data["events"]}
        assert {"writing_submitted", "analysis_completed", "feedback_available",
                "feedback_priority_available", "practice_available",
                "exercise_attempted", "practice_evaluation_recorded"} <= types
        assert data["counts"]["practice_evaluations"] == 1

    def test_journey_unknown_learner_returns_404(self, client):
        r = client.get("/api/v1/students/S999/journey")
        assert r.status_code == 404
        assert r.json()["error"]["category"] == "resource_not_found"

    def test_attempt_route_persists_evaluation(self, journeyed_client):
        client, _, _, exercise, attempt = journeyed_client
        assert attempt["evaluation"] is not None
        assert attempt["evaluation"]["evaluation_id"].startswith("PE")
        r = client.get(f"/api/v1/exercises/{exercise['exercise_id']}/attempts")
        assert r.status_code == 200
        assert len(r.json()) == 1
        r = client.get(f"/api/v1/practice-targets/{exercise['practice_target_id']}/exercises")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_empty_attempt_not_saved(self, journeyed_client):
        client, _, _, exercise, _ = journeyed_client
        r = client.post(
            f"/api/v1/exercises/{exercise['exercise_id']}/attempts",
            json={"student_id": "JAPI", "response_text": "   "},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "invalid_input"
        attempts = client.get(f"/api/v1/exercises/{exercise['exercise_id']}/attempts").json()
        assert len(attempts) == 1


def load_settings():
    from app.config import load_settings as _load

    return _load()
