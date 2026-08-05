"""v0.9.7-C WU1 focused tests: Student Journey cycle view model.

Covers learner-owned writing-cycle grouping from persisted records,
revision-root resolution, feedback association, priority-provenance
validation, Practice activity states (available / attempted /
evaluation-available / evaluation-unavailable / completed), legacy and
unlinked handling, learner isolation, raw-event compatibility,
determinism, and zero-write reads. All persistence runs on isolated
databases with the local provider only.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("LLM_PROVIDER", "local")

from fastapi.testclient import TestClient  # noqa: E402

from app.api.main import create_app  # noqa: E402
from app.config import Settings  # noqa: E402


REPETITION_ESSAY = (
    "People should protect the environment. People should recycle more. "
    "People should save water. People should plant trees. People should reduce waste. "
    "People should use public transport. People should teach children about nature. "
    "People should value clean air."
)
SHORT_ESSAY = (
    "The history of history is historical. The history of history is historical."
)
REVISION_ESSAY = (
    "Citizens should protect the environment. Communities can recycle more."
)
VALID_RESPONSE = "A valid response reducing repetition."

CYCLE_TABLES = (
    "essays", "analysis_runs", "feedback_records", "practice_targets",
    "exercise_instances", "exercise_attempts", "practice_evaluations",
    "within_task_response_candidates", "transfer_evidence_candidates",
    "feedback_engagement_traces", "revision_groups", "revision_snapshots",
)


def _settings(tmp_path) -> Settings:
    return Settings(
        database_path=tmp_path / "wu1.db", llm_provider="local",
        deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com",
        deepseek_model="deepseek-chat",
    )


def _submit_essay(client, student_id: str, text: str,
                  draft_stage: str = "first draft",
                  revision_of: int | None = None) -> int:
    response = client.post("/api/v1/submissions", json={
        "student_id": student_id,
        "writing_prompt": "What actions matter for sustainability?",
        "genre": "argumentative essay", "draft_stage": draft_stage,
        "timed": False, "tool_use": "none", "essay_text": text,
        **({"revision_of_submission_id": revision_of} if revision_of else {}),
    })
    assert response.status_code == 201, response.text
    return response.json()["submission_id"]


def _priority_index(client, essay_id: int,
                    category: str = "lexical_repetition") -> int:
    record = client.app.state.repository._submission_repository.get_feedback_record(essay_id)
    priorities = json.loads(record["feedback_json"])["priority_feedback"]
    return next(
        i for i, item in enumerate(priorities) if item.get("category") == category
    )


def _create_target(client, student_id: str, essay_id: int,
                   category: str = "lexical_repetition") -> dict:
    response = client.post("/api/v1/practice-targets", json={
        "student_id": student_id, "source_submission_id": essay_id,
        "priority_index": _priority_index(client, essay_id, category),
    })
    assert response.status_code == 200, response.text
    return response.json()


def _create_exercise(client, target: dict) -> dict:
    response = client.post(
        f"/api/v1/practice-targets/{target['practice_target_id']}/exercises",
        json={"source_text": REPETITION_ESSAY},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _submit_attempt(client, exercise: dict, student_id: str) -> dict:
    response = client.post(
        f"/api/v1/exercises/{exercise['exercise_id']}/attempts",
        json={"student_id": student_id, "response_text": VALID_RESPONSE},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _complete(client, target_id: str, student_id: str) -> dict:
    response = client.post(
        f"/api/v1/practice-targets/{target_id}/complete",
        json={"student_id": student_id},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _journey(client, student_id: str) -> dict:
    response = client.get(f"/api/v1/students/{student_id}/journey")
    assert response.status_code == 200, response.text
    return response.json()


def _table_counts(client) -> dict[str, int]:
    with client.app.state.repository.connect() as conn:
        return {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in CYCLE_TABLES
        }


def _seed_full_cycle(client, student_id: str,
                     with_revision: bool = True,
                     with_evaluation: bool = True) -> dict:
    essay_id = _submit_essay(client, student_id, REPETITION_ESSAY)
    target = _create_target(client, student_id, essay_id)
    exercise = _create_exercise(client, target)
    attempt = _submit_attempt(client, exercise, student_id)
    if not with_evaluation:
        with client.app.state.repository.connect() as conn:
            conn.execute("DELETE FROM practice_evaluations")
    revision_id = None
    if with_revision:
        revision_id = _submit_essay(
            client, student_id, REVISION_ESSAY,
            draft_stage="revised draft", revision_of=essay_id)
    return {
        "essay_id": essay_id, "revision_id": revision_id, "target": target,
        "exercise": exercise, "attempt": attempt,
    }


def _insert_essay_row(client, student_id: str, *,
                      revision_of: int | None = None,
                      submitted_at: str = "2026-08-01T00:00:00+00:00") -> int:
    import sqlite3

    path = str(client.app.state.settings.database_path)
    with sqlite3.connect(path) as raw:
        if revision_of is not None:
            # The orphan-revision scenario intentionally has no resolvable
            # parent; FK enforcement is disabled for this one row only
            # (before any DML, so the pragma takes effect).
            raw.execute("PRAGMA foreign_keys=OFF")
        raw.execute(
            "INSERT OR IGNORE INTO students (student_id, created_at, "
            "is_synthetic) VALUES (?, '2026-08-01T00:00:00+00:00', 1)",
            (student_id,))
        cursor = raw.execute(
            """INSERT INTO essays(
                student_id, writing_prompt, genre, draft_stage, timed,
                tool_use, essay_text, submitted_at,
                revision_of_submission_id, revision_sequence, revision_stage
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (student_id, "Should we act?", "argumentative essay",
             "revised draft" if revision_of else "first draft", 0,
             "none", "A raw essay row.", submitted_at,
             revision_of, 2 if revision_of else None,
             "revised_draft" if revision_of else "independent_submission"),
        )
        raw.commit()
        return cursor.lastrowid


def _legacy_target(client, student_id: str, essay_id: int) -> dict:
    record = client.app.state.repository._submission_repository.get_feedback_record(essay_id)
    priorities = json.loads(record["feedback_json"])["priority_feedback"]
    item = next(
        i for i in priorities if i.get("category") == "lexical_repetition")
    response = client.post("/api/v1/practice-targets", json={
        "student_id": student_id, "source_submission_id": essay_id,
        "source_diagnosis_id": item["diagnosis_id"],
        "target_code": "lexical_repetition_local",
        "target_label": "Reduce lexical repetition",
        "gate_status": "selected",
    })
    assert response.status_code == 200, response.text
    return response.json()


class TestCycleGrouping:
    """WU1 acceptance 1-3, 9-10: grouping and revision attachment."""

    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def test_full_cycle_groups_into_one_cycle(self, client):
        records = _seed_full_cycle(client, "W1-GROUP")
        _complete(client, records["target"]["practice_target_id"], "W1-GROUP")
        data = _journey(client, "W1-GROUP")
        assert len(data["cycles"]) == 1
        cycle = data["cycles"][0]
        assert cycle["cycle_id"] == f"cycle-{records['essay_id']}"
        assert cycle["learner_id"] == "W1-GROUP"
        assert cycle["relationship_status"] == "linked"
        assert cycle["root_submission"]["submission_id"] == records["essay_id"]
        assert cycle["root_submission"]["is_revision"] is False
        assert [r["submission_id"] for r in cycle["revisions"]] == [
            records["revision_id"]]
        assert cycle["revisions"][0]["revision_of_submission_id"] == records["essay_id"]
        assert len(cycle["practice_cycles"]) == 1
        assert cycle["current_state"] == "completed"
        assert cycle["available_actions"] == []

    def test_independent_essays_remain_separate(self, client):
        _submit_essay(client, "W1-SEP", REPETITION_ESSAY)
        _submit_essay(client, "W1-SEP", REPETITION_ESSAY)
        data = _journey(client, "W1-SEP")
        assert len(data["cycles"]) == 2
        ids = [c["cycle_id"] for c in data["cycles"]]
        assert len(set(ids)) == 2
        assert all(c["relationship_status"] == "linked" for c in data["cycles"])

    def test_multi_level_revision_chain_attaches_to_root(self, client):
        first = _submit_essay(client, "W1-CHAIN", REPETITION_ESSAY)
        second = _submit_essay(client, "W1-CHAIN", REVISION_ESSAY,
                               draft_stage="revised draft", revision_of=first)
        third = _submit_essay(client, "W1-CHAIN",
                              "Communities should recycle more and plant trees.",
                              draft_stage="revised draft", revision_of=second)
        data = _journey(client, "W1-CHAIN")
        assert len(data["cycles"]) == 1
        cycle = data["cycles"][0]
        assert cycle["cycle_id"] == f"cycle-{first}"
        assert cycle["root_submission"]["submission_id"] == first
        assert [r["submission_id"] for r in cycle["revisions"]] == [second, third]

    def test_orphan_revision_is_controlled_unlinked(self, client):
        _submit_essay(client, "W1-ORPHAN", REPETITION_ESSAY)
        orphan = _insert_essay_row(client, "W1-ORPHAN", revision_of=999999)
        data = _journey(client, "W1-ORPHAN")
        cycles = {c["cycle_id"]: c for c in data["cycles"]}
        assert f"cycle-{orphan}" in cycles
        cycle = cycles[f"cycle-{orphan}"]
        assert cycle["relationship_status"] == "unlinked"
        assert cycle["root_submission"]["submission_id"] == orphan
        assert cycle["limitations"]
        # The orphan never attaches to the real essay's cycle.
        real = [c for cid, c in cycles.items() if cid != f"cycle-{orphan}"]
        assert len(real) == 1
        assert [r["submission_id"] for r in real[0]["revisions"]] == []

    def test_feedback_attaches_to_correct_submission(self, client):
        first = _submit_essay(client, "W1-FB", REPETITION_ESSAY)
        second = _submit_essay(client, "W1-FB", SHORT_ESSAY)
        data = _journey(client, "W1-FB")
        by_id = {c["cycle_id"]: c for c in data["cycles"]}
        first_stages = by_id[f"cycle-{first}"]["feedback_stages"]
        second_stages = by_id[f"cycle-{second}"]["feedback_stages"]
        assert [s["submission_id"] for s in first_stages] == [first]
        assert [s["submission_id"] for s in second_stages] == [second]
        assert first_stages[0]["priority_count"] >= 1
        assert second_stages[0]["priority_count"] == 0


class TestWritingStates:
    """WU1 acceptance 7: honest writing states."""

    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def test_feedback_available_state(self, client):
        essay_id = _submit_essay(client, "W1-ST", REPETITION_ESSAY)
        cycle = _journey(client, "W1-ST")["cycles"][0]
        assert cycle["root_submission"]["writing_state"] == "feedback_available"
        assert cycle["current_state"] == "feedback_available"

    def test_feedback_without_priority_state(self, client):
        essay_id = _submit_essay(client, "W1-ST", SHORT_ESSAY)
        cycle = _journey(client, "W1-ST")["cycles"][0]
        assert cycle["root_submission"]["writing_state"] == "feedback_without_priority"
        assert cycle["current_state"] == "feedback_without_priority"
        assert cycle["feedback_stages"][0]["priority_count"] == 0

    def test_insufficient_evidence_state(self, client):
        essay_id = _insert_essay_row(client, "W1-ST")
        cycle = _journey(client, "W1-ST")["cycles"][0]
        assert cycle["root_submission"]["writing_state"] == "insufficient_evidence"
        assert cycle["current_state"] == "insufficient_evidence"

    def test_analyzed_state(self, client):
        essay_id = _submit_essay(client, "W1-ST", REPETITION_ESSAY)
        with client.app.state.repository.connect() as conn:
            conn.execute(
                "DELETE FROM feedback_records WHERE essay_id=?", (essay_id,))
        cycle = _journey(client, "W1-ST")["cycles"][0]
        assert cycle["root_submission"]["writing_state"] == "analyzed"
        assert cycle["feedback_stages"] == []

    def test_revision_submitted_state(self, client):
        first = _submit_essay(client, "W1-ST", REPETITION_ESSAY)
        second = _submit_essay(client, "W1-ST", REVISION_ESSAY,
                               draft_stage="revised draft", revision_of=first)
        cycle = _journey(client, "W1-ST")["cycles"][0]
        assert cycle["root_submission"]["writing_state"] == "feedback_available"
        assert cycle["revisions"][0]["writing_state"] == "revision_submitted"
        assert cycle["current_state"] == "revision_submitted"


class TestPracticeAssociation:
    """WU1 acceptance 4-6, 8: practice attachment and activity states."""

    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def test_priority_target_has_valid_provenance(self, client):
        records = _seed_full_cycle(client, "W1-PROV")
        cycle = _journey(client, "W1-PROV")["cycles"][0]
        practice = cycle["practice_cycles"][0]
        assert practice["practice_target_id"] == records["target"]["practice_target_id"]
        assert practice["priority_provenance"]["status"] == "valid"
        assert practice["priority_provenance"]["category"] == "lexical_repetition"
        assert practice["priority_provenance"]["reference"].startswith("PRIO-")
        assert practice["activity_state"] == "evaluation_available"
        assert practice["evaluation_state"] == "available"
        assert practice["completion_state"] == "active"
        assert practice["attempt"]["attempt_id"] == records["attempt"]["attempt_id"]

    def test_legacy_target_without_fabricated_provenance(self, client):
        essay_id = _submit_essay(client, "W1-LEG", REPETITION_ESSAY)
        target = _legacy_target(client, "W1-LEG", essay_id)
        cycle = _journey(client, "W1-LEG")["cycles"][0]
        practice = cycle["practice_cycles"][0]
        assert practice["priority_provenance"]["status"] == "legacy"
        assert practice["priority_provenance"]["reference"] is None
        assert "category" not in practice["priority_provenance"]
        assert practice["activity_state"] == "available"

    def test_stale_priority_reference_is_unresolved(self, client):
        records = _seed_full_cycle(client, "W1-STALE", with_revision=False)
        target_id = records["target"]["practice_target_id"]
        with client.app.state.repository.connect() as conn:
            row = conn.execute(
                "SELECT target_json FROM practice_targets "
                "WHERE practice_target_id=?", (target_id,)).fetchone()
            payload = json.loads(row[0])
            payload["source_priority_id"] = "PRIO-999999-99"
            conn.execute(
                "UPDATE practice_targets SET target_json=? "
                "WHERE practice_target_id=?",
                (json.dumps(payload), target_id))
        cycle = _journey(client, "W1-STALE")["cycles"][0]
        practice = cycle["practice_cycles"][0]
        assert practice["priority_provenance"]["status"] == "unresolved"
        assert practice["priority_provenance"]["reason"] == "feedback_mismatch"

    def test_active_and_completed_targets_distinct(self, client):
        essay_id = _submit_essay(client, "W1-DUAL", REPETITION_ESSAY)
        completed_target = _create_target(client, "W1-DUAL", essay_id)
        exercise = _create_exercise(client, completed_target)
        _submit_attempt(client, exercise, "W1-DUAL")
        _complete(client, completed_target["practice_target_id"], "W1-DUAL")
        second_essay = _submit_essay(client, "W1-DUAL", REPETITION_ESSAY)
        active_target = _create_target(client, "W1-DUAL", second_essay)
        data = _journey(client, "W1-DUAL")
        completed_cycle = next(
            c for c in data["cycles"]
            if c["cycle_id"] == f"cycle-{essay_id}")
        active_cycle = next(
            c for c in data["cycles"]
            if c["cycle_id"] == f"cycle-{second_essay}")
        assert completed_cycle["practice_cycles"][0]["activity_state"] == "completed"
        assert completed_cycle["current_state"] == "completed"
        assert active_cycle["practice_cycles"][0]["activity_state"] == "available"

    def test_attempt_without_evaluation(self, client):
        records = _seed_full_cycle(client, "W1-NOEV",
                                   with_revision=False, with_evaluation=False)
        cycle = _journey(client, "W1-NOEV")["cycles"][0]
        practice = cycle["practice_cycles"][0]
        assert practice["activity_state"] == "evaluation_unavailable"
        assert practice["evaluation_state"] == "unavailable"
        assert practice["attempt"]["attempt_id"] == records["attempt"]["attempt_id"]
        assert practice["evaluation"] is None

    def test_completed_without_evaluation_stays_honest(self, client):
        records = _seed_full_cycle(client, "W1-NOEVC",
                                   with_revision=False, with_evaluation=False)
        _complete(client, records["target"]["practice_target_id"], "W1-NOEVC")
        cycle = _journey(client, "W1-NOEVC")["cycles"][0]
        practice = cycle["practice_cycles"][0]
        assert practice["activity_state"] == "completed"
        assert practice["evaluation_state"] == "unavailable"
        assert practice["completion_state"] == "completed"

    def test_inactive_target_with_attempt_is_attempted(self, client):
        essay_id = _submit_essay(client, "W1-INACT", REPETITION_ESSAY)
        target = _create_target(client, "W1-INACT", essay_id)
        exercise = _create_exercise(client, target)
        _submit_attempt(client, exercise, "W1-INACT")
        with client.app.state.repository.connect() as conn:
            conn.execute("DELETE FROM practice_evaluations")
        with client.app.state.repository.connect() as conn:
            row = conn.execute(
                "SELECT target_json FROM practice_targets "
                "WHERE practice_target_id=?", (target["practice_target_id"],)
            ).fetchone()
            payload = json.loads(row[0])
            payload["status"] = "inactive"
            conn.execute(
                "UPDATE practice_targets SET status='inactive', target_json=? "
                "WHERE practice_target_id=?",
                (json.dumps(payload), target["practice_target_id"]))
        cycle = _journey(client, "W1-INACT")["cycles"][0]
        practice = cycle["practice_cycles"][0]
        assert practice["activity_state"] == "attempted"
        assert practice["evaluation_state"] == "unavailable"

    def test_two_targets_same_cycle_stay_distinct(self, client):
        essay_id = _submit_essay(client, "W1-TWO", REPETITION_ESSAY)
        first = _create_target(client, "W1-TWO", essay_id)
        exercise = _create_exercise(client, first)
        _submit_attempt(client, exercise, "W1-TWO")
        second = _legacy_target(client, "W1-TWO", essay_id)
        cycle = _journey(client, "W1-TWO")["cycles"][0]
        practice = {p["practice_target_id"]: p for p in cycle["practice_cycles"]}
        assert set(practice) == {
            first["practice_target_id"], second["practice_target_id"]}
        assert practice[first["practice_target_id"]]["activity_state"] == \
            "evaluation_available"
        assert practice[second["practice_target_id"]]["activity_state"] == "available"

    def test_unlinked_practice_target_is_controlled(self, client):
        _submit_essay(client, "W1-UNL", REPETITION_ESSAY)
        essay_id = _submit_essay(client, "W1-UNL", REPETITION_ESSAY)
        target = _create_target(client, "W1-UNL", essay_id)
        with client.app.state.repository.connect() as conn:
            row = conn.execute(
                "SELECT target_json FROM practice_targets "
                "WHERE practice_target_id=?", (target["practice_target_id"],)
            ).fetchone()
            payload = json.loads(row[0])
            payload["source_submission_id"] = 999999
            conn.execute(
                "UPDATE practice_targets SET source_submission_id=999999, "
                "target_json=? WHERE practice_target_id=?",
                (json.dumps(payload), target["practice_target_id"]))
        data = _journey(client, "W1-UNL")
        unlinked = next(
            c for c in data["cycles"]
            if c["cycle_id"] == "cycle-unlinked-practice")
        assert unlinked["relationship_status"] == "unlinked"
        assert unlinked["root_submission"] is None
        assert unlinked["practice_cycles"][0]["practice_target_id"] == \
            target["practice_target_id"]
        assert unlinked["limitations"]
        # The real essay cycles never received the stale target.
        assert all(
            target["practice_target_id"] not in {
                p["practice_target_id"] for p in c["practice_cycles"]}
            for c in data["cycles"] if c["cycle_id"] != "cycle-unlinked-practice")


class TestNoPriorityAndInsufficient:
    """WU1 acceptance 7: honest no-priority and insufficient flows."""

    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def test_no_priority_flow(self, client):
        _submit_essay(client, "W1-NP", SHORT_ESSAY)
        data = _journey(client, "W1-NP")
        cycle = data["cycles"][0]
        assert cycle["root_submission"]["writing_state"] == "feedback_without_priority"
        assert cycle["practice_cycles"] == []
        assert cycle["current_state"] == "feedback_without_priority"
        assert "practice_available" not in {
            e["event_type"] for e in data["events"]}

    def test_insufficient_evidence_flow(self, client):
        _insert_essay_row(client, "W1-IE")
        data = _journey(client, "W1-IE")
        cycle = data["cycles"][0]
        assert cycle["root_submission"]["writing_state"] == "insufficient_evidence"
        assert cycle["current_state"] == "insufficient_evidence"
        assert "insufficient_evidence" in {
            e["event_type"] for e in data["events"]}


class TestLearnerIsolation:
    """WU1 acceptance 11: no cross-learner data."""

    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def test_learners_cycles_never_overlap(self, client):
        first = _seed_full_cycle(client, "W1-ISO-A", with_revision=False)
        second = _seed_full_cycle(client, "W1-ISO-B", with_revision=False)
        data_a = _journey(client, "W1-ISO-A")
        data_b = _journey(client, "W1-ISO-B")
        assert len(data_a["cycles"]) == 1 and len(data_b["cycles"]) == 1
        assert data_a["cycles"][0]["learner_id"] == "W1-ISO-A"
        assert data_b["cycles"][0]["learner_id"] == "W1-ISO-B"
        assert data_a["cycles"][0]["cycle_id"] == f"cycle-{first['essay_id']}"
        assert data_b["cycles"][0]["cycle_id"] == f"cycle-{second['essay_id']}"
        assert data_a["cycles"][0]["practice_cycles"][0]["practice_target_id"] == \
            first["target"]["practice_target_id"]
        assert data_b["cycles"][0]["practice_cycles"][0]["practice_target_id"] == \
            second["target"]["practice_target_id"]


class TestRawCompatibility:
    """WU1 acceptance 9-10: raw events and additive response."""

    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def test_raw_event_contract_unchanged(self, client):
        records = _seed_full_cycle(client, "W1-RAW")
        data = _journey(client, "W1-RAW")
        types = [e["event_type"] for e in data["events"]]
        assert len(types) == 11
        assert "practice_completed" not in types
        keys = [e["deduplication_key"] for e in data["events"]]
        assert len(keys) == len(set(keys))
        assert data["state"] == "revision_no_response"

    def test_response_is_additive(self, client):
        _seed_full_cycle(client, "W1-ADD", with_revision=False)
        data = _journey(client, "W1-ADD")
        assert data["cycles_version"] == "journey-cycle-v0.9.7-c"
        assert isinstance(data["cycles"], list)
        for key in ("student_id", "learner_found", "counts", "events",
                    "derived_states", "state"):
            assert key in data

    def test_chronology_contains_only_cycle_events_in_raw_order(self, client):
        records = _seed_full_cycle(client, "W1-CHRONO")
        cycle = _journey(client, "W1-CHRONO")["cycles"][0]
        chronology = cycle["chronology"]
        assert chronology
        raw_types = [e["event_type"] for e in chronology]
        assert "writing_submitted" in raw_types
        assert "practice_available" in raw_types
        assert "exercise_attempted" in raw_types
        assert "practice_evaluation_recorded" in raw_types
        assert "revision_submitted" in raw_types
        keys = [e["deduplication_key"] for e in chronology]
        assert len(keys) == len(set(keys))


class TestDeterminismAndNoWrites:
    """WU1 acceptance 12-13: deterministic, zero writes."""

    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def test_repeated_reads_are_identical(self, client):
        _seed_full_cycle(client, "W1-DET")
        first = _journey(client, "W1-DET")
        second = _journey(client, "W1-DET")
        assert first["cycles"] == second["cycles"]
        assert first["events"] == second["events"]

    def test_cycle_reads_perform_zero_writes(self, client):
        _seed_full_cycle(client, "W1-WRITE")
        before = _table_counts(client)
        for _ in range(2):
            _journey(client, "W1-WRITE")
        assert _table_counts(client) == before


class TestMalformedData:
    """WU1 acceptance 6: malformed records fail safely."""

    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def test_malformed_feedback_json_is_controlled(self, client):
        essay_id = _submit_essay(client, "W1-MALFB", REPETITION_ESSAY)
        with client.app.state.repository.connect() as conn:
            conn.execute(
                "UPDATE feedback_records SET feedback_json=? WHERE essay_id=?",
                ("{not valid json", essay_id))
        data = _journey(client, "W1-MALFB")
        cycle = data["cycles"][0]
        assert cycle["feedback_stages"][0]["priority_count"] == 0
        # Consistent with the raw projection's conservative parsing.
        assert "feedback_without_priority" in {
            e["event_type"] for e in data["events"]}

    def test_malformed_target_reference_does_not_crash(self, client):
        essay_id = _submit_essay(client, "W1-MALT", REPETITION_ESSAY)
        target = _create_target(client, "W1-MALT", essay_id)
        with client.app.state.repository.connect() as conn:
            row = conn.execute(
                "SELECT target_json FROM practice_targets "
                "WHERE practice_target_id=?", (target["practice_target_id"],)
            ).fetchone()
            payload = json.loads(row[0])
            payload["source_priority_id"] = "PRIO-not-a-reference"
            conn.execute(
                "UPDATE practice_targets SET target_json=? "
                "WHERE practice_target_id=?",
                (json.dumps(payload), target["practice_target_id"]))
        cycle = _journey(client, "W1-MALT")["cycles"][0]
        practice = cycle["practice_cycles"][0]
        assert practice["priority_provenance"]["status"] == "unresolved"
        assert practice["priority_provenance"]["reason"] == "invalid_reference"
