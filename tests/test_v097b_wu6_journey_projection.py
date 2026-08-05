"""v0.9.7-B WU6 focused tests: Journey projection of the complete
priority-derived Practice cycle.

Covers the read-time projector contract for the full product path (essay ->
analysis -> feedback priority -> practice target -> exercise -> attempt ->
evaluation -> completed target status -> linked revision -> Journey
projection): exact event types and counts, source/provenance association,
deterministic ordering, deduplication under repeated reads/re-entry/reuse/
completion, side-effect-free reads, evaluation-unavailable honesty, legacy
targets without fabricated provenance, learner isolation, and the
documented malformed-row boundary. All persistence runs on isolated
databases with the local provider only; no live provider call.
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

PROJECTION_TABLES = (
    "essays", "analysis_runs", "feedback_records", "practice_targets",
    "exercise_instances", "exercise_attempts", "practice_evaluations",
    "within_task_response_candidates", "transfer_evidence_candidates",
    "feedback_engagement_traces",
)

EXPECTED_FULL_CYCLE_TYPES = (
    "writing_submitted", "analysis_completed", "feedback_available",
    "feedback_priority_available", "practice_available",
    "exercise_attempted", "practice_evaluation_recorded",
    "revision_submitted", "analysis_completed", "feedback_available",
    "feedback_without_priority",
)


def _settings(tmp_path) -> Settings:
    return Settings(
        database_path=tmp_path / "wu6.db", llm_provider="local",
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
            for table in PROJECTION_TABLES
        }


def _delete_evaluation(client) -> None:
    with client.app.state.repository.connect() as conn:
        conn.execute("DELETE FROM practice_evaluations")


def _insert_raw_evaluation(client, raw: str, attempt_id: str) -> None:
    with client.app.state.repository.connect() as conn:
        conn.execute(
            "INSERT INTO practice_evaluations VALUES (?,?,?,?,?)",
            ("PE999999", attempt_id, "PT999999",
             "2026-01-01T00:00:00+00:00", raw),
        )


def _seed_full_cycle(client, student_id: str) -> dict:
    """One complete product-path cycle with a linked revision."""
    essay_id = _submit_essay(client, student_id, REPETITION_ESSAY)
    target = _create_target(client, student_id, essay_id)
    exercise = _create_exercise(client, target)
    attempt = _submit_attempt(client, exercise, student_id)
    evaluation = client.get(
        f"/api/v1/students/{student_id}/practice-targets/"
        f"{target['practice_target_id']}/evaluations"
    ).json()
    assert len(evaluation) == 1
    revision_id = _submit_essay(
        client, student_id, REVISION_ESSAY, draft_stage="revised draft",
        revision_of=essay_id,
    )
    return {
        "essay_id": essay_id, "revision_id": revision_id, "target": target,
        "exercise": exercise, "attempt": attempt,
        "evaluation": evaluation[0],
    }


class TestFullCycleProjection:
    """MCU 6.1.1-6.1.3: exact projection and provenance."""

    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def test_full_cycle_projects_exact_event_set(self, client):
        records = _seed_full_cycle(client, "W6-FULL")
        data = _journey(client, "W6-FULL")
        types = [e["event_type"] for e in data["events"]]
        assert types == list(EXPECTED_FULL_CYCLE_TYPES)
        assert len(data["events"]) == len(EXPECTED_FULL_CYCLE_TYPES)
        keys = [e["deduplication_key"] for e in data["events"]]
        assert len(keys) == len(set(keys)), keys
        assert all(e["learner_id"] == "W6-FULL" for e in data["events"])
        assert data["state"] == "revision_no_response"

    def test_source_associations_are_exact(self, client):
        records = _seed_full_cycle(client, "W6-ASOC")
        data = _journey(client, "W6-ASOC")
        by_type = {e["event_type"]: e for e in data["events"]}
        practice = by_type["practice_available"]
        assert practice["source_record_type"] == "practice_target"
        assert practice["source_record_id"] == records["target"]["practice_target_id"]
        assert practice["submission_id"] == records["essay_id"]
        assert practice["research_detail"]["target_code"] == "lexical_repetition_local"
        assert practice["research_detail"]["status"] == "active"
        attempt = by_type["exercise_attempted"]
        assert attempt["source_record_id"] == records["attempt"]["attempt_id"]
        assert attempt["research_detail"] == {"attempt_number": 1, "status": "submitted"}
        evaluation = by_type["practice_evaluation_recorded"]
        assert evaluation["source_record_id"] == records["evaluation"]["evaluation_id"]
        revision = by_type["revision_submitted"]
        assert revision["source_record_id"] == str(records["revision_id"])
        assert revision["submission_id"] == records["revision_id"]
        assert revision["research_detail"]["revision_of_submission_id"] == records["essay_id"]
        feedbacks = [e for e in data["events"] if e["event_type"] == "feedback_available"]
        assert len(feedbacks) == 2
        assert {e["submission_id"] for e in feedbacks} == {
            records["essay_id"], records["revision_id"]}

    def test_ordering_is_deterministic_and_stage_aware(self, client):
        records = _seed_full_cycle(client, "W6-ORD")
        first = _journey(client, "W6-ORD")
        second = _journey(client, "W6-ORD")
        first_types = [e["event_type"] for e in first["events"]]
        assert first_types == [e["event_type"] for e in second["events"]]
        assert [e["source_record_id"] for e in first["events"]] == [
            e["source_record_id"] for e in second["events"]]
        # Essay-1 events follow the natural stage chain.
        chain = ["writing_submitted", "analysis_completed", "feedback_available",
                 "feedback_priority_available", "practice_available"]
        essay1_sequence = [
            e["event_type"] for e in first["events"]
            if e["event_type"] in chain
            and e["submission_id"] == records["essay_id"]
        ]
        assert essay1_sequence == chain

    def test_counts_match_persisted_records(self, client):
        _seed_full_cycle(client, "W6-CNT")
        data = _journey(client, "W6-CNT")
        assert data["counts"] == {
            "submissions": 2, "analysis_runs": 2, "feedback_records": 2,
            "selected_priorities": 1, "practice_targets": 1,
            "exercise_attempts": 1, "practice_evaluations": 1,
            "within_task_responses": 0, "transfer_evidence_candidates": 0,
        }


class TestCompletionProjection:
    """MCU 6.1.1/6.1.5: completed status flows through without new events."""

    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def _events(self, data):
        return [(e["event_type"], e["source_record_id"]) for e in data["events"]]

    def test_completion_creates_no_new_event(self, client):
        records = _seed_full_cycle(client, "W6-COMP")
        before = _journey(client, "W6-COMP")
        _complete(client, records["target"]["practice_target_id"], "W6-COMP")
        after = _journey(client, "W6-COMP")
        assert self._events(before) == self._events(after)
        assert len(after["events"]) == len(before["events"])
        practice = next(
            e for e in after["events"] if e["event_type"] == "practice_available")
        assert practice["research_detail"]["status"] == "completed"

    def test_repeated_completion_keeps_journey_stable(self, client):
        records = _seed_full_cycle(client, "W6-REPC")
        before_counts = _table_counts(client)
        _complete(client, records["target"]["practice_target_id"], "W6-REPC")
        _complete(client, records["target"]["practice_target_id"], "W6-REPC")
        data = _journey(client, "W6-REPC")
        assert len(data["events"]) == len(EXPECTED_FULL_CYCLE_TYPES)
        assert _table_counts(client) == before_counts
        practice = next(
            e for e in data["events"] if e["event_type"] == "practice_available")
        assert practice["research_detail"]["status"] == "completed"

    def test_completed_reentry_via_create_or_reuse_does_not_duplicate(self, client):
        records = _seed_full_cycle(client, "W6-REUSE")
        _complete(client, records["target"]["practice_target_id"], "W6-REUSE")
        again = _create_target(client, "W6-REUSE", records["essay_id"])
        assert again["practice_target_id"] == records["target"]["practice_target_id"]
        data = _journey(client, "W6-REUSE")
        practice = [e for e in data["events"] if e["event_type"] == "practice_available"]
        assert len(practice) == 1
        assert practice[0]["source_record_id"] == records["target"]["practice_target_id"]
        assert practice[0]["research_detail"]["status"] == "completed"


class TestReadIdempotency:
    """MCU 6.1.4: repeated reads and re-entry are side-effect free."""

    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def test_repeated_reads_are_identical_and_write_nothing(self, client):
        _seed_full_cycle(client, "W6-READ")
        before = _table_counts(client)
        snapshots = [_journey(client, "W6-READ") for _ in range(3)]
        assert all(
            [e["deduplication_key"] for e in s["events"]]
            == [e["deduplication_key"] for e in snapshots[0]["events"]]
            for s in snapshots[1:]
        )
        assert _table_counts(client) == before

    def test_reentry_actions_do_not_append_events(self, client):
        records = _seed_full_cycle(client, "W6-RENT")
        _complete(client, records["target"]["practice_target_id"], "W6-RENT")
        _create_target(client, "W6-RENT", records["essay_id"])
        _journey(client, "W6-RENT")
        _journey(client, "W6-RENT")
        data = _journey(client, "W6-RENT")
        keys = [e["deduplication_key"] for e in data["events"]]
        assert len(keys) == len(set(keys))
        assert len(data["events"]) == len(EXPECTED_FULL_CYCLE_TYPES)


class TestEvaluationUnavailable:
    """MCU 6.1.6: attempts remain authoritative; nothing is fabricated."""

    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def test_attempt_without_evaluation_projects_honestly(self, client):
        records = _seed_full_cycle(client, "W6-NOEVA")
        _delete_evaluation(client)
        data = _journey(client, "W6-NOEVA")
        types = [e["event_type"] for e in data["events"]]
        assert "practice_evaluation_recorded" not in types
        assert len(data["events"]) == len(EXPECTED_FULL_CYCLE_TYPES) - 1
        assert any(e["event_type"] == "exercise_attempted" for e in data["events"])
        assert data["counts"]["practice_evaluations"] == 0
        assert data["state"] == "attempt_no_evaluation"

    def test_completed_target_without_evaluation_projects_honestly(self, client):
        records = _seed_full_cycle(client, "W6-NOEVC")
        _delete_evaluation(client)
        completed = _complete(client, records["target"]["practice_target_id"], "W6-NOEVC")
        assert completed["status"] == "completed"
        data = _journey(client, "W6-NOEVC")
        types = [e["event_type"] for e in data["events"]]
        assert "practice_evaluation_recorded" not in types
        practice = next(
            e for e in data["events"] if e["event_type"] == "practice_available")
        assert practice["research_detail"]["status"] == "completed"
        assert practice["limitations"] == [
            "Practice availability is not evidence of completed practice."]
        attempt = next(
            e for e in data["events"] if e["event_type"] == "exercise_attempted")
        assert attempt["research_detail"]["status"] == "submitted"
        # The attempt event carries the fixed conservative limitation that
        # denies mastery; no failure or pass claim exists anywhere.
        assert attempt["limitations"] == [
            "An attempt record exists; it does not demonstrate mastery."]
        assert all("evaluation" not in e["event_type"] for e in data["events"])


class TestLearnerIsolation:
    """MCU 6.1.3: no event may cross learner boundaries."""

    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def test_other_learners_records_never_appear(self, client):
        first = _seed_full_cycle(client, "W6-ISO-A")
        second = _seed_full_cycle(client, "W6-ISO-B")
        data_a = _journey(client, "W6-ISO-A")
        data_b = _journey(client, "W6-ISO-B")
        assert all(e["learner_id"] == "W6-ISO-A" for e in data_a["events"])
        assert all(e["learner_id"] == "W6-ISO-B" for e in data_b["events"])
        ids_a = {e["source_record_id"] for e in data_a["events"]}
        ids_b = {e["source_record_id"] for e in data_b["events"]}
        assert not (ids_a & ids_b)
        practice_a = next(
            e for e in data_a["events"] if e["event_type"] == "practice_available")
        assert practice_a["source_record_id"] == first["target"]["practice_target_id"]
        practice_b = next(
            e for e in data_b["events"] if e["event_type"] == "practice_available")
        assert practice_b["source_record_id"] == second["target"]["practice_target_id"]


class TestTargetReuse:
    """MCU 6.1.4: create-or-reuse never duplicates Journey events."""

    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def test_repeated_creation_projects_one_practice_available_event(self, client):
        essay_id = _submit_essay(client, "W6-REP", REPETITION_ESSAY)
        first = _create_target(client, "W6-REP", essay_id)
        second = _create_target(client, "W6-REP", essay_id)
        third = _create_target(client, "W6-REP", essay_id)
        assert first["practice_target_id"] == second["practice_target_id"]
        assert first["practice_target_id"] == third["practice_target_id"]
        data = _journey(client, "W6-REP")
        practice = [e for e in data["events"] if e["event_type"] == "practice_available"]
        assert len(practice) == 1

    def test_two_targets_project_two_distinct_events(self, client):
        essay_a = _submit_essay(client, "W6-TWO", REPETITION_ESSAY)
        essay_b = _submit_essay(client, "W6-TWO", REPETITION_ESSAY)
        target_a = _create_target(client, "W6-TWO", essay_a)
        target_b = _create_target(client, "W6-TWO", essay_b)
        assert target_a["practice_target_id"] != target_b["practice_target_id"]
        data = _journey(client, "W6-TWO")
        practice = [e for e in data["events"] if e["event_type"] == "practice_available"]
        assert len(practice) == 2
        assert {e["source_record_id"] for e in practice} == {
            target_a["practice_target_id"], target_b["practice_target_id"]}


class TestLegacyCompatibility:
    """MCU 6.1.7: legacy targets project without fabricated provenance."""

    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def test_legacy_target_projects_without_fabricated_provenance(self, client):
        essay_id = _submit_essay(client, "W6-LEG", REPETITION_ESSAY)
        record = client.app.state.repository._submission_repository.get_feedback_record(essay_id)
        priorities = json.loads(record["feedback_json"])["priority_feedback"]
        item = next(
            i for i in priorities if i.get("category") == "lexical_repetition")
        response = client.post("/api/v1/practice-targets", json={
            "student_id": "W6-LEG", "source_submission_id": essay_id,
            "source_diagnosis_id": item["diagnosis_id"],
            "target_code": "lexical_repetition_local",
            "target_label": "Reduce lexical repetition",
            "gate_status": "selected",
        })
        assert response.status_code == 200, response.text
        target = response.json()
        assert target.get("source_priority_id") is None
        exercise = _create_exercise(client, target)
        _submit_attempt(client, exercise, "W6-LEG")
        data = _journey(client, "W6-LEG")
        practice = next(
            e for e in data["events"] if e["event_type"] == "practice_available")
        assert practice["source_record_id"] == target["practice_target_id"]
        assert "source_priority_id" not in practice["research_detail"]
        assert "priority" not in json.dumps(practice["research_detail"]).lower()
        assert any(e["event_type"] == "exercise_attempted" for e in data["events"])

    def test_legacy_target_completion_creates_no_new_event(self, client):
        essay_id = _submit_essay(client, "W6-LEGC", REPETITION_ESSAY)
        record = client.app.state.repository._submission_repository.get_feedback_record(essay_id)
        priorities = json.loads(record["feedback_json"])["priority_feedback"]
        item = next(
            i for i in priorities if i.get("category") == "lexical_repetition")
        target = client.post("/api/v1/practice-targets", json={
            "student_id": "W6-LEGC", "source_submission_id": essay_id,
            "source_diagnosis_id": item["diagnosis_id"],
            "target_code": "lexical_repetition_local",
            "target_label": "Reduce lexical repetition",
            "gate_status": "selected",
        }).json()
        exercise = _create_exercise(client, target)
        _submit_attempt(client, exercise, "W6-LEGC")
        before = _journey(client, "W6-LEGC")
        _complete(client, target["practice_target_id"], "W6-LEGC")
        after = _journey(client, "W6-LEGC")
        assert [(e["event_type"], e["source_record_id"]) for e in before["events"]] == [
            (e["event_type"], e["source_record_id"]) for e in after["events"]]


class TestMalformedDataBoundary:
    """MCU 6.1.1: documented malformed-row boundary (audit G9).

    The verified product path writes schema-validated JSON, so malformed
    rows only exist on a tampered database. On that boundary the Journey
    read fails with a stable error before emitting any event (no partial
    projection, no fabrication, no cross-association, no writes); the
    repository-wide malformed-row repair remains a documented deferred
    limitation (docs/KNOWN_LIMITATIONS.md G9).
    """

    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path)),
                        raise_server_exceptions=False) as client:
            yield client

    def test_malformed_evaluation_row_is_stable_error_not_fabrication(self, client):
        records = _seed_full_cycle(client, "W6-MAL")
        _insert_raw_evaluation(client, "{not valid json",
                               records["attempt"]["attempt_id"])
        before = _table_counts(client)
        response = client.get("/api/v1/students/W6-MAL/journey")
        assert response.status_code == 500
        assert _table_counts(client) == before
        # The malformed row never produced a partial or fabricated event
        # (the read failed before derivation completed).
        assert response.text

    def test_stale_priority_reference_does_not_break_projection(self, client):
        essay_id = _submit_essay(client, "W6-STALE", REPETITION_ESSAY)
        target = _create_target(client, "W6-STALE", essay_id)
        with client.app.state.repository.connect() as conn:
            row = conn.execute(
                "SELECT target_json FROM practice_targets "
                "WHERE practice_target_id=?",
                (target["practice_target_id"],),
            ).fetchone()
            payload = json.loads(row[0])
            payload["source_priority_id"] = "PRIO-999999-99"
            conn.execute(
                "UPDATE practice_targets SET target_json=? "
                "WHERE practice_target_id=?",
                (json.dumps(payload), target["practice_target_id"]),
            )
        data = _journey(client, "W6-STALE")
        practice = next(
            e for e in data["events"] if e["event_type"] == "practice_available")
        assert practice["source_record_id"] == target["practice_target_id"]
        assert practice["research_detail"]["status"] == "active"
