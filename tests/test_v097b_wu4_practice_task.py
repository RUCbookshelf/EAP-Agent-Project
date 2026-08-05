"""v0.9.7-B WU4 focused tests: focused Practice task and attempt loop.

Covers the explicit entry transfer (intent -> create-or-reuse), the
learner-owned read-only task-context resolver, current-exercise behavior,
attempt ownership validation, and the focused task page states (rendering,
pending guard, saved-attempt recovery). All persistence runs on isolated
databases with the local provider only.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("LLM_PROVIDER", "local")

from fastapi.testclient import TestClient  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

from app.api.main import create_app  # noqa: E402
from app.config import Settings  # noqa: E402
from app.ui.locale import t  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "harness_v097a_student.py"

REPETITION_ESSAY = (
    "People should protect the environment. People should recycle more. "
    "People should save water. People should plant trees. People should reduce waste. "
    "People should use public transport. People should teach children about nature. "
    "People should value clean air."
)


def _settings(tmp_path) -> Settings:
    return Settings(
        database_path=tmp_path / "wu4.db", llm_provider="local", deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com", deepseek_model="deepseek-chat",
    )


def _seed_api(client, student_id: str = "WU4-S") -> tuple[int, dict, int]:
    response = client.post("/api/v1/submissions", json={
        "student_id": student_id,
        "writing_prompt": "What actions matter for sustainability?",
        "genre": "argumentative essay", "draft_stage": "first draft", "timed": False,
        "tool_use": "none", "essay_text": REPETITION_ESSAY,
    })
    assert response.status_code == 201, response.text
    essay_id = response.json()["submission_id"]
    record = client.app.state.repository._submission_repository.get_feedback_record(essay_id)
    priorities = json.loads(record["feedback_json"])["priority_feedback"]
    index = next(
        i for i, item in enumerate(priorities)
        if item.get("category") == "lexical_repetition"
    )
    return essay_id, record, index


def _target_count(client) -> int:
    with client.app.state.repository.connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM practice_targets").fetchone()[0]


class TestEntryIntentApi:
    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def test_intent_creates_target_with_resolved_reference(self, client):
        essay_id, record, index = _seed_api(client)
        response = client.post("/api/v1/practice-targets", json={
            "student_id": "WU4-S", "source_submission_id": essay_id,
            "priority_index": index,
        })
        assert response.status_code == 200, response.text
        target = response.json()
        assert target["source_priority_id"] == f"PRIO-{record['feedback_id']}-{index}"
        assert target["source_submission_id"] == essay_id
        assert target["target_code"] == "lexical_repetition_local"
        assert target["evidence_ids"] == [str(record["feedback_id"])]

    def test_intent_repeated_requests_reuse_same_target(self, client):
        essay_id, record, index = _seed_api(client)
        payload = {
            "student_id": "WU4-S", "source_submission_id": essay_id,
            "priority_index": index,
        }
        first = client.post("/api/v1/practice-targets", json=payload)
        second = client.post("/api/v1/practice-targets", json=payload)
        assert first.status_code == second.status_code == 200
        assert first.json()["practice_target_id"] == second.json()["practice_target_id"]
        assert _target_count(client) == 1

    def test_intent_cross_student_returns_403(self, client):
        essay_id, _, index = _seed_api(client)
        response = client.post("/api/v1/practice-targets", json={
            "student_id": "INTRUDER", "source_submission_id": essay_id,
            "priority_index": index,
        })
        assert response.status_code == 403
        assert _target_count(client) == 0

    def test_intent_missing_submission_returns_404(self, client):
        response = client.post("/api/v1/practice-targets", json={
            "student_id": "WU4-S", "source_submission_id": 999999,
            "priority_index": 0,
        })
        assert response.status_code == 404
        assert _target_count(client) == 0

    def test_intent_out_of_range_index_returns_422(self, client):
        essay_id, _, _ = _seed_api(client)
        response = client.post("/api/v1/practice-targets", json={
            "student_id": "WU4-S", "source_submission_id": essay_id,
            "priority_index": 99,
        })
        assert response.status_code == 422
        assert _target_count(client) == 0

    def test_intent_negative_index_returns_422(self, client):
        essay_id, _, _ = _seed_api(client)
        response = client.post("/api/v1/practice-targets", json={
            "student_id": "WU4-S", "source_submission_id": essay_id,
            "priority_index": -1,
        })
        assert response.status_code == 422
        assert _target_count(client) == 0

    def test_intent_malformed_index_returns_422(self, client):
        essay_id, _, _ = _seed_api(client)
        response = client.post("/api/v1/practice-targets", json={
            "student_id": "WU4-S", "source_submission_id": essay_id,
            "priority_index": "not-an-index",
        })
        assert response.status_code == 422
        assert _target_count(client) == 0

    def test_source_priority_id_form_takes_precedence_over_intent(self, client):
        essay_id, record, index = _seed_api(client)
        response = client.post("/api/v1/practice-targets", json={
            "student_id": "WU4-S", "source_submission_id": essay_id,
            "source_priority_id": f"PRIO-{record['feedback_id']}-{index}",
            "priority_index": 99,
        })
        assert response.status_code == 200, response.text
        assert response.json()["source_priority_id"] == (
            f"PRIO-{record['feedback_id']}-{index}")


class TestTaskContextApi:
    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def _seed_target(self, client) -> tuple[str, dict, int, dict]:
        essay_id, record, index = _seed_api(client)
        target = client.post("/api/v1/practice-targets", json={
            "student_id": "WU4-S", "source_submission_id": essay_id,
            "priority_index": index,
        }).json()
        return target["practice_target_id"], record, index, target

    def test_priority_target_resolves_exact_context(self, client):
        target_id, record, index, _ = self._seed_target(client)
        response = client.get(
            f"/api/v1/students/WU4-S/practice-targets/{target_id}/context")
        assert response.status_code == 200, response.text
        context = response.json()
        assert context["context_status"] == "priority"
        assert context["source_priority_id"] == f"PRIO-{record['feedback_id']}-{index}"
        assert context["target_code"] == "lexical_repetition_local"
        priority = context["priority_context"]
        assert priority["feedback_id"] == record["feedback_id"]
        assert priority["priority_index"] == index
        assert priority["category"] == "lexical_repetition"
        assert priority["evidence_quote"]
        assert priority["explanation"]
        assert priority["revision_guidance"]
        assert context["source_writing_text"] == REPETITION_ESSAY

    def test_context_cross_student_returns_403(self, client):
        _seed_api(client, "INTRUDER")
        target_id, _, _, _ = self._seed_target(client)
        response = client.get(
            f"/api/v1/students/INTRUDER/practice-targets/{target_id}/context")
        assert response.status_code == 403

    def test_context_missing_target_returns_404(self, client):
        _seed_api(client)
        response = client.get(
            "/api/v1/students/WU4-S/practice-targets/PT999999/context")
        assert response.status_code == 404

    def test_context_unknown_learner_returns_404(self, client):
        target_id, _, _, _ = self._seed_target(client)
        response = client.get(
            f"/api/v1/students/NOPE/practice-targets/{target_id}/context")
        assert response.status_code == 404

    def test_context_stale_priority_index_is_unavailable(self, client):
        essay_id, record, index = _seed_api(client)
        target = client.post("/api/v1/practice-targets", json={
            "student_id": "WU4-S", "source_submission_id": essay_id,
            "priority_index": index,
        }).json()
        target_id = target["practice_target_id"]
        repository = client.app.state.repository
        feedback = json.loads(record["feedback_json"])
        feedback["priority_feedback"] = []
        with repository.connect() as conn:
            conn.execute(
                "UPDATE feedback_records SET feedback_json=? WHERE feedback_id=?",
                (json.dumps(feedback), record["feedback_id"]),
            )
        response = client.get(
            f"/api/v1/students/WU4-S/practice-targets/{target_id}/context")
        assert response.status_code == 200
        context = response.json()
        assert context["context_status"] == "unavailable"
        assert context["reason"] == "unresolved_priority"

    def test_context_malformed_reference_is_unavailable(self, client):
        target_id, _, _, target = self._seed_target(client)
        stored = dict(target)
        stored["source_priority_id"] = "PRIO-18"
        with client.app.state.repository.connect() as conn:
            conn.execute(
                "UPDATE practice_targets SET target_json=? WHERE practice_target_id=?",
                (json.dumps(stored), target_id),
            )
        response = client.get(
            f"/api/v1/students/WU4-S/practice-targets/{target_id}/context")
        assert response.status_code == 200
        assert response.json()["context_status"] == "unavailable"
        assert response.json()["reason"] == "malformed_provenance"

    def test_context_legacy_target_returns_legacy_context(self, client):
        essay_id, _, _ = _seed_api(client)
        response = client.post("/api/v1/submissions", json={
            "student_id": "WU4-S", "writing_prompt": "What actions matter for sustainability?",
            "genre": "argumentative essay", "draft_stage": "first draft", "timed": False,
            "tool_use": "none", "essay_text": REPETITION_ESSAY,
        })
        diagnosis = response.json()["diagnosis"]
        priority = next(
            item for item in diagnosis.get("improvement_priorities", [])
            if item.get("selection_status") == "selected_priority"
        )
        target = client.post("/api/v1/practice-targets", json={
            "student_id": "WU4-S", "source_submission_id": essay_id,
            "source_diagnosis_id": priority["diagnosis_id"],
            "target_code": "lexical_repetition_local",
            "target_label": priority["interpretation"],
            "gate_status": "selected",
        }).json()
        context_response = client.get(
            f"/api/v1/students/WU4-S/practice-targets/{target['practice_target_id']}/context")
        assert context_response.status_code == 200
        context = context_response.json()
        assert context["context_status"] == "legacy"
        assert context["priority_context"] is None
        assert context["source_writing_text"] == REPETITION_ESSAY

    def test_context_read_performs_zero_writes(self, client):
        target_id, _, _, _ = self._seed_target(client)
        with client.app.state.repository.connect() as conn:
            before = conn.execute(
                "SELECT COUNT(*) FROM practice_targets").fetchone()[0]
            attempts = conn.execute(
                "SELECT COUNT(*) FROM exercise_attempts").fetchone()[0]
        response = client.get(
            f"/api/v1/students/WU4-S/practice-targets/{target_id}/context")
        assert response.status_code == 200
        with client.app.state.repository.connect() as conn:
            after_targets = conn.execute(
                "SELECT COUNT(*) FROM practice_targets").fetchone()[0]
            after_attempts = conn.execute(
                "SELECT COUNT(*) FROM exercise_attempts").fetchone()[0]
        assert (before, attempts) == (after_targets, after_attempts)


class TestAttemptOwnershipApi:
    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def _seed_exercise(self, client) -> tuple[int, dict]:
        response = client.post("/api/v1/submissions", json={
            "student_id": "WU4-S", "writing_prompt": "What actions matter for sustainability?",
            "genre": "argumentative essay", "draft_stage": "first draft", "timed": False,
            "tool_use": "none", "essay_text": REPETITION_ESSAY,
        })
        essay_id = response.json()["submission_id"]
        diagnosis = response.json()["diagnosis"]
        priority = next(
            item for item in diagnosis.get("improvement_priorities", [])
            if item.get("selection_status") == "selected_priority"
        )
        target = client.post("/api/v1/practice-targets", json={
            "student_id": "WU4-S", "source_submission_id": essay_id,
            "source_diagnosis_id": priority["diagnosis_id"],
            "target_code": "lexical_repetition_local",
            "target_label": priority["interpretation"],
            "gate_status": "selected",
        }).json()
        exercise = client.post(
            f"/api/v1/practice-targets/{target['practice_target_id']}/exercises",
            json={"source_text": REPETITION_ESSAY},
        ).json()
        return essay_id, exercise

    def test_cross_student_attempt_returns_403_with_zero_writes(self, client):
        _, exercise = self._seed_exercise(client)
        with client.app.state.repository.connect() as conn:
            before = conn.execute("SELECT COUNT(*) FROM exercise_attempts").fetchone()[0]
        response = client.post(
            f"/api/v1/exercises/{exercise['exercise_id']}/attempts",
            json={"student_id": "INTRUDER", "response_text": "A valid response here."},
        )
        assert response.status_code == 403
        with client.app.state.repository.connect() as conn:
            after = conn.execute("SELECT COUNT(*) FROM exercise_attempts").fetchone()[0]
        assert before == after

    def test_attempt_without_target_row_returns_404(self, client):
        _, exercise = self._seed_exercise(client)
        with client.app.state.repository.connect() as conn:
            conn.execute("DELETE FROM exercise_instances WHERE exercise_id=?",
                         (exercise["exercise_id"],))
        response = client.post(
            f"/api/v1/exercises/{exercise['exercise_id']}/attempts",
            json={"student_id": "WU4-S", "response_text": "A valid response here."},
        )
        assert response.status_code == 404

    def test_valid_attempt_still_persists(self, client):
        _, exercise = self._seed_exercise(client)
        response = client.post(
            f"/api/v1/exercises/{exercise['exercise_id']}/attempts",
            json={"student_id": "WU4-S",
                  "response_text": "A valid response reducing repetition."},
        )
        assert response.status_code == 200
        attempt = response.json()
        assert attempt["status"] == "submitted"
        assert attempt["attempt_id"].startswith("EA")
        with client.app.state.repository.connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM exercise_attempts").fetchone()[0]
        assert count == 1


def _run_harness(**config):
    at = AppTest.from_file(str(HARNESS), default_timeout=90)
    configured_result = config.pop("submission_result", None)
    for key, value in config.items():
        at.session_state[key] = value
    at.run()
    assert not at.exception, at.exception
    student_input = next(
        ti for ti in at.text_input
        if ti.key
        in {"home_student", "writing_student", "feedback_student",
            "revision_student", "practice_student_v2"}
    )
    student_input.set_value("S02").run()
    assert not at.exception, at.exception
    if configured_result is not None:
        at.session_state["submission_result"] = json.loads(json.dumps(configured_result))
        at.run()
        assert not at.exception, at.exception
    return at


def _markdown_text(at) -> str:
    import re
    return " ".join(m.value for m in at.markdown)


def _button_labels(at) -> dict:
    return {button.key: button.label for button in at.button}


def _fake_client(at):
    return at.session_state["fake_client"]


PRIORITY_RESULT = {
    "submission_id": 28,
    "ui_submission": {"student_id": "S02", "writing_prompt": "Should cities add more parks?"},
    "ui_empty_states": [],
    "diagnosis": {"strengths": [{"category": "lexical_repetition"}]},
    "feedback_result": {
        "feedback": {
            "priority_feedback": [
                {
                    "diagnosis_id": "D001",
                    "category": "lexical_repetition",
                    "evidence_quote": "Parks support public health.",
                    "explanation": "The phrase 'public health' is repeated closely.",
                    "revision_guidance": "Replace one repetition with a synonym.",
                },
                {
                    "diagnosis_id": "D002",
                    "category": "connective_use",
                    "evidence_quote": "Cities should protect accessible parks.",
                    "explanation": "The draft lacks a linking phrase.",
                    "revision_guidance": "Add a connective that links the two ideas.",
                },
            ]
        }
    },
}

PRIORITY_TARGET = {
    "practice_target_id": "PT000001",
    "student_id": "S02",
    "source_submission_id": 28,
    "source_diagnosis_id": "D001",
    "source_priority_id": "PRIO-1-0",
    "target_code": "lexical_repetition_local",
    "target_label": "Reduce lexical repetition",
    "evidence_ids": ["1"],
    "status": "active",
    "created_at": "2026-01-01T00:00:00+00:00",
}

PRIORITY_CONTEXT = {
    "context_status": "priority",
    "practice_target_id": "PT000001",
    "student_id": "S02",
    "source_submission_id": 28,
    "source_diagnosis_id": "D001",
    "source_priority_id": "PRIO-1-0",
    "target_code": "lexical_repetition_local",
    "target_label": "Reduce lexical repetition",
    "status": "active",
    "priority_context": {
        "feedback_id": 1,
        "priority_index": 0,
        "category": "lexical_repetition",
        "evidence_quote": "Parks support public health.",
        "explanation": "The phrase 'public health' is repeated closely.",
        "revision_guidance": "Replace one repetition with a synonym.",
        "prompt_version": "feedback-prompt-v0.7.1",
        "schema_version": "feedback-schema-v0.7.1",
        "diagnosis_version": "prototype-diagnosis-v0.1.1",
        "label_key": "student_feedback_category_lexical_repetition",
    },
    "source_writing_text": "Parks support public health. Cities should protect accessible parks.",
}

EXERCISE = {
    "exercise_id": "EX000001",
    "practice_target_id": "PT000001",
    "student_id": "S02",
    "source_submission_id": 28,
    "exercise_type": "guided_sentence_rewrite",
    "instructions": "Rewrite the following sentence to address the selected priority.",
    "source_text": "Parks support public health.",
    "constraints": ["Retain original meaning.", "Do not add unsupported content."],
    "status": "active",
}

REVISION_SAVED_RESULT = {
    "submission_id": 99,
    "ui_submission": {
        "student_id": "S02",
        "writing_prompt": "Should cities add more parks?",
        "genre": "argumentative essay",
        "draft_stage": "revised draft",
        "revision_of_submission_id": 28,
        "revision_priority_index": 1,
        "revision_source": {
            "writing_prompt": "Should cities add more parks?",
            "draft_stage": "final draft",
            "essay_text": "Parks support public health. Cities should protect accessible parks.",
        },
    },
    "within_task_revision_trajectory": {
        "previous_selected_priorities": PRIORITY_RESULT["feedback_result"]["feedback"][
            "priority_feedback"
        ],
        "feedback_uptake_candidates": [],
        "first_to_latest_comparison": {},
    },
}


class TestPracticePage:
    def test_feedback_practice_button_transfers_intent(self):
        at = _run_harness(
            submission_result=PRIORITY_RESULT,
            sidebar_page=t("student_feedback_title", "en"),
            harness_target_create_response=PRIORITY_TARGET,
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
        )
        labels = _button_labels(at)
        assert labels.get("feedback_practice_priority_0") == t(
            "student_feedback_practice_priority", "en")
        at.button(key="feedback_practice_priority_1").click().run()
        assert not at.exception, at.exception
        assert at.session_state["sidebar_page"] == t("practice", "en")
        assert _fake_client(at).target_create_count == 1
        assert "practice_source_submission_id" not in at.session_state

    def test_revision_completion_transfers_addressed_priority(self):
        at = _run_harness(
            submission_result=REVISION_SAVED_RESULT,
            sidebar_page=t("student_revision_title", "en"),
            harness_target_create_response=PRIORITY_TARGET,
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
        )
        labels = _button_labels(at)
        assert labels.get("revision_open_practice") == t(
            "student_revision_open_practice", "en")
        at.button(key="revision_open_practice").click().run()
        assert not at.exception, at.exception
        assert at.session_state["sidebar_page"] == t("practice", "en")
        assert _fake_client(at).target_create_count == 1
        assert "practice_source_submission_id" not in at.session_state

    def test_practice_page_consumes_intent_and_opens_target_once(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            practice_source_submission_id=28,
            practice_priority_index=0,
            harness_target_create_response=PRIORITY_TARGET,
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
        )
        assert _fake_client(at).target_create_count == 1
        assert "practice_source_submission_id" not in at.session_state
        assert "practice_target_preset" not in at.session_state
        text = _markdown_text(at)
        assert "Reduce lexical repetition" in text

    def test_repeated_entry_reuses_the_same_target(self):
        first = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            practice_source_submission_id=28,
            practice_priority_index=0,
            harness_target_create_response=PRIORITY_TARGET,
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
        )
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            practice_source_submission_id=28,
            practice_priority_index=0,
            harness_target_create_response=PRIORITY_TARGET,
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
        )
        assert _fake_client(first).target_create_count == 1
        assert _fake_client(at).target_create_count == 1
        text = _markdown_text(at)
        assert "Reduce lexical repetition" in text

    def test_direct_navigation_does_not_create_a_target(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            harness_targets=[],
        )
        assert _fake_client(at).target_create_count == 0
        text = _markdown_text(at)
        assert t("student_practice_no_target_action", "en") in text

    def test_invalid_intent_shows_note_without_creation(self):
        at = AppTest.from_file(str(HARNESS), default_timeout=90)
        at.session_state["sidebar_page"] = t("practice", "en")
        at.session_state["selected_student_id"] = "S02"
        at.session_state["practice_student_v2"] = "S02"
        at.session_state["practice_source_submission_id"] = 28
        at.session_state["practice_priority_index"] = 0
        at.session_state["harness_targets"] = []
        at.run()
        assert not at.exception, at.exception
        assert _fake_client(at).target_create_count == 1
        assert "practice_source_submission_id" not in at.session_state
        assert t("student_practice_intent_invalid", "en") in _markdown_text(at)

    def test_stale_preset_falls_back_to_oldest_active(self):
        other = dict(PRIORITY_TARGET, practice_target_id="PT000002",
                     source_submission_id=29, source_priority_id="PRIO-2-0",
                     target_label="Vary sentence length")
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            practice_target_preset="PT999999",
            harness_targets=[other, PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
        )
        text = _markdown_text(at)
        assert "Vary sentence length" in text
        assert "practice_target_preset" not in at.session_state

    def test_focused_task_renders_priority_context(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
        )
        import html as _html
        text = _markdown_text(at)
        assert _html.escape("The phrase 'public health' is repeated closely.") in text
        assert _html.escape("Replace one repetition with a synonym.") in text
        assert "Parks support public health." in text

    def test_context_unavailable_renders_note_without_task_claims(self):
        unavailable = dict(PRIORITY_CONTEXT, context_status="unavailable",
                           reason="unresolved_priority", priority_context=None)
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=unavailable,
            harness_exercises=[EXERCISE],
        )
        text = _markdown_text(at)
        assert t("student_practice_context_unavailable", "en") in text

    def test_saved_attempt_shows_saved_state_with_reference(self):
        attempt = {
            "attempt_id": "EA000001",
            "exercise_id": "EX000001",
            "student_id": "S02",
            "attempt_number": 1,
            "response_text": "Communities can protect public health.",
            "status": "submitted",
            "evaluation": None,
        }
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
            harness_attempts=[attempt],
        )
        text = _markdown_text(at)
        assert t("student_practice_attempt_saved", "en") in text
        assert "EA000001" in text
        assert "Communities can protect public health." in text

    def test_pending_marker_consumes_duplicate_submission(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
            practice_submit_pending=True,
        )
        assert t("student_practice_submit_pending", "en") in _markdown_text(at)
        assert _fake_client(at).attempt_post_count == 0

    def test_empty_response_produces_no_attempt_write(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
        )
        assert t("student_practice_empty_response", "en") not in _markdown_text(at)
        at.text_area(key="practice_response_v2").set_value("   ").run()
        at.button(key="practice_submit").click().run()
        assert not at.exception, at.exception
        assert t("student_practice_empty_response", "en") in _markdown_text(at)
        assert _fake_client(at).attempt_post_count == 0

    def test_valid_submission_persists_and_rerun_shows_saved_state(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
            harness_attempt_response={
                "attempt_id": "EA000001",
                "exercise_id": "EX000001",
                "student_id": "S02",
                "attempt_number": 1,
                "response_text": "Communities can protect public health.",
                "status": "submitted",
                "evaluation": None,
            },
        )
        at.text_area(key="practice_response_v2").set_value(
            "Communities can protect public health.").run()
        at.button(key="practice_submit").click().run()
        assert not at.exception, at.exception
        assert _fake_client(at).attempt_post_count == 1
        assert t("student_practice_attempt_saved", "en") in _markdown_text(at)
