"""v0.9.7-C WU4 release tests: final end-to-end Journey closure.

Release-level assertions over the complete priority-guided cycle through
the real API: one grouped cycle, exact raw-event compatibility, no
duplicate cycles/events, safe actions with stable references, learner
isolation, zero writes, and the honest evaluation-unavailable path.
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
REVISION_ESSAY = (
    "Citizens should protect the environment. Communities can recycle more."
)
VALID_RESPONSE = "A valid response reducing repetition."

RAW_EVENT_TYPES = {
    "writing_submitted", "revision_submitted", "analysis_completed",
    "insufficient_evidence", "feedback_available",
    "feedback_priority_available", "feedback_without_priority",
    "practice_available", "exercise_attempted",
    "practice_evaluation_recorded", "within_task_response_observed",
    "later_task_evidence",
}

CYCLE_TABLES = (
    "essays", "analysis_runs", "feedback_records", "practice_targets",
    "exercise_instances", "exercise_attempts", "practice_evaluations",
    "within_task_response_candidates", "transfer_evidence_candidates",
    "feedback_engagement_traces", "revision_groups", "revision_snapshots",
)


def _settings(tmp_path) -> Settings:
    return Settings(
        database_path=tmp_path / "wu4.db", llm_provider="local",
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


def _create_target(client, student_id: str, essay_id: int) -> dict:
    record = client.app.state.repository._submission_repository.get_feedback_record(essay_id)
    priorities = json.loads(record["feedback_json"])["priority_feedback"]
    index = next(
        i for i, item in enumerate(priorities)
        if item.get("category") == "lexical_repetition")
    response = client.post("/api/v1/practice-targets", json={
        "student_id": student_id, "source_submission_id": essay_id,
        "priority_index": index,
    })
    assert response.status_code == 200, response.text
    return response.json()


def _exercise(client, target: dict) -> dict:
    response = client.post(
        f"/api/v1/practice-targets/{target['practice_target_id']}/exercises",
        json={"source_text": REPETITION_ESSAY})
    assert response.status_code == 200, response.text
    return response.json()


def _attempt(client, exercise: dict, student_id: str) -> dict:
    response = client.post(
        f"/api/v1/exercises/{exercise['exercise_id']}/attempts",
        json={"student_id": student_id, "response_text": VALID_RESPONSE})
    assert response.status_code == 200, response.text
    return response.json()


def _complete(client, target_id: str, student_id: str) -> dict:
    response = client.post(
        f"/api/v1/practice-targets/{target_id}/complete",
        json={"student_id": student_id})
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
                     with_evaluation: bool = True) -> dict:
    essay_id = _submit_essay(client, student_id, REPETITION_ESSAY)
    target = _create_target(client, student_id, essay_id)
    exercise = _exercise(client, target)
    attempt = _attempt(client, exercise, student_id)
    if not with_evaluation:
        with client.app.state.repository.connect() as conn:
            conn.execute("DELETE FROM practice_evaluations")
    revision_id = _submit_essay(client, student_id, REVISION_ESSAY,
                                draft_stage="revised draft",
                                revision_of=essay_id)
    _complete(client, target["practice_target_id"], student_id)
    return {
        "essay_id": essay_id, "revision_id": revision_id, "target": target,
        "attempt": attempt,
    }


class TestReleaseEndToEnd:
    """WU4 acceptance 2-12: one complete cycle, no duplicates, no writes."""

    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def test_complete_cycle_groups_once_with_safe_actions(self, client):
        records = _seed_full_cycle(client, "W4-E2E")
        data = _journey(client, "W4-E2E")
        assert len(data["cycles"]) == 1
        cycle = data["cycles"][0]
        assert cycle["cycle_id"] == f"cycle-{records['essay_id']}"
        assert cycle["root_submission"]["submission_id"] == records["essay_id"]
        assert [r["submission_id"] for r in cycle["revisions"]] == [
            records["revision_id"]]
        practice = cycle["practice_cycles"][0]
        assert practice["practice_target_id"] == records["target"]["practice_target_id"]
        assert practice["activity_state"] == "completed"
        assert practice["priority_provenance"]["status"] == "valid"
        assert {"action": "open_revision",
                "submission_id": records["essay_id"]} in cycle["available_actions"]
        assert {"action": "open_practice",
                "practice_target_id": records["target"]["practice_target_id"]} in \
            cycle["available_actions"]
        # No duplicate cycles and no duplicate raw events.
        keys = [e["deduplication_key"] for e in data["events"]]
        assert len(keys) == len(set(keys))
        assert len(data["cycles"]) == 1

    def test_raw_event_contract_intact(self, client):
        _seed_full_cycle(client, "W4-RAW")
        data = _journey(client, "W4-RAW")
        types = [e["event_type"] for e in data["events"]]
        assert set(types) <= RAW_EVENT_TYPES
        assert "practice_completed" not in types
        assert data["cycles_version"] == "journey-cycle-v0.9.7-c"

    def test_completion_does_not_duplicate_or_write(self, client):
        records = _seed_full_cycle(client, "W4-COMP")
        before = _table_counts(client)
        _complete(client, records["target"]["practice_target_id"], "W4-COMP")
        data = _journey(client, "W4-COMP")
        assert len(data["cycles"]) == 1
        assert _table_counts(client) == before

    def test_evaluation_unavailable_remains_honest(self, client):
        records = _seed_full_cycle(client, "W4-NOEV", with_evaluation=False)
        data = _journey(client, "W4-NOEV")
        cycle = data["cycles"][0]
        practice = cycle["practice_cycles"][0]
        assert practice["activity_state"] == "completed"
        assert practice["evaluation_state"] == "unavailable"
        assert practice["evaluation"] is None
        assert "practice_evaluation_recorded" not in {
            e["event_type"] for e in data["events"]}

    def test_learner_isolation_in_release_path(self, client):
        first = _seed_full_cycle(client, "W4-ISO-A")
        second = _seed_full_cycle(client, "W4-ISO-B")
        data_a = _journey(client, "W4-ISO-A")
        data_b = _journey(client, "W4-ISO-B")
        assert data_a["cycles"][0]["cycle_id"] == f"cycle-{first['essay_id']}"
        assert data_b["cycles"][0]["cycle_id"] == f"cycle-{second['essay_id']}"
        assert all(e["learner_id"] == "W4-ISO-A" for e in data_a["events"])
        assert all(e["learner_id"] == "W4-ISO-B" for e in data_b["events"])

    def test_repeated_reads_and_reentry_no_duplicates(self, client):
        records = _seed_full_cycle(client, "W4-REPEAT")
        before = _table_counts(client)
        first = _journey(client, "W4-REPEAT")
        _create_target(client, "W4-REPEAT", records["essay_id"])  # reuse
        _complete(client, records["target"]["practice_target_id"], "W4-REPEAT")
        second = _journey(client, "W4-REPEAT")
        assert first["cycles"] == second["cycles"]
        assert first["events"] == second["events"]
        assert _table_counts(client) == before

    def test_two_independent_cycles_group_separately(self, client):
        first = _submit_essay(client, "W4-TWO", REPETITION_ESSAY)
        second = _submit_essay(client, "W4-TWO", REPETITION_ESSAY)
        data = _journey(client, "W4-TWO")
        assert len(data["cycles"]) == 2
        assert {c["cycle_id"] for c in data["cycles"]} == {
            f"cycle-{first}", f"cycle-{second}"}

    def test_multiple_practice_targets_one_completed_one_active(self, client):
        essay_a = _submit_essay(client, "W4-DUAL", REPETITION_ESSAY)
        target_a = _create_target(client, "W4-DUAL", essay_a)
        _attempt(client, _exercise(client, target_a), "W4-DUAL")
        _complete(client, target_a["practice_target_id"], "W4-DUAL")
        essay_b = _submit_essay(client, "W4-DUAL", REPETITION_ESSAY)
        target_b = _create_target(client, "W4-DUAL", essay_b)
        data = _journey(client, "W4-DUAL")
        cycles = {c["cycle_id"]: c for c in data["cycles"]}
        assert cycles[f"cycle-{essay_a}"]["practice_cycles"][0][
            "activity_state"] == "completed"
        assert cycles[f"cycle-{essay_b}"]["practice_cycles"][0][
            "activity_state"] == "available"
        assert target_a["practice_target_id"] != target_b["practice_target_id"]
