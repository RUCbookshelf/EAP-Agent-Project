"""v0.9.7-B WU5 focused tests: evaluation semantics, target completion,
and post-Practice next steps.

Covers the persistence-backed evaluation read path (available / unavailable /
malformed), the learner-owned idempotent ACTIVE -> COMPLETED transition,
completion eligibility and ownership rules, completed-target re-entry, and
the bounded post-Practice actions. All persistence runs on isolated
databases with the local provider only.
"""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
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
        database_path=tmp_path / "wu5.db", llm_provider="local",
        deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com",
        deepseek_model="deepseek-chat",
    )


def _seed_api(client, student_id: str = "WU5-S") -> tuple[int, dict, int]:
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


def _seed_target(client, student_id: str = "WU5-S") -> tuple[int, dict]:
    essay_id, record, index = _seed_api(client, student_id)
    target = client.post("/api/v1/practice-targets", json={
        "student_id": student_id, "source_submission_id": essay_id,
        "priority_index": index,
    }).json()
    return essay_id, target


def _seed_exercise(client, target: dict, student_id: str = "WU5-S") -> dict:
    exercise = client.post(
        f"/api/v1/practice-targets/{target['practice_target_id']}/exercises",
        json={"source_text": REPETITION_ESSAY},
    ).json()
    assert exercise.get("status") != "practice_not_available"
    return exercise


def _submit_attempt(client, exercise: dict, student_id: str = "WU5-S") -> dict:
    response = client.post(
        f"/api/v1/exercises/{exercise['exercise_id']}/attempts",
        json={"student_id": student_id,
              "response_text": "A valid response reducing repetition."},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _insert_attempt(client, exercise_id: str, student_id: str = "WU5-S",
                    status: str = "submitted", attempt_id: str = "EA999999",
                    response_text: str = "A persisted response.") -> None:
    payload = {
        "attempt_id": attempt_id, "exercise_id": exercise_id,
        "student_id": student_id, "attempt_number": 1,
        "response_text": response_text, "status": status,
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    with client.app.state.repository.connect() as conn:
        conn.execute(
            "INSERT INTO exercise_attempts VALUES (?,?,?,?,?,?,?)",
            (attempt_id, exercise_id, student_id, 1, status,
             payload["created_at"], json.dumps(payload)),
        )


def _insert_evaluation(client, attempt_id: str, target_id: str,
                       evaluation_id: str = "PE999999", raw: str | None = None) -> None:
    payload = {
        "evaluation_id": evaluation_id, "attempt_id": attempt_id,
        "practice_target_id": target_id, "evaluation_method": "rule_based",
        "completion_status": "completed",
        "target_action_status": "inconclusive",
        "evidence": ["Response length: 30 characters"], "confidence": "medium",
        "limitations": ["Task-specific only."], "evaluator_version": "practice-evaluator-v0.9.0",
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    stored = raw if raw is not None else json.dumps(payload)
    with client.app.state.repository.connect() as conn:
        conn.execute(
            "INSERT INTO practice_evaluations VALUES (?,?,?,?,?)",
            (evaluation_id, attempt_id, target_id, payload["created_at"], stored),
        )


def _stored_target(client, target_id: str) -> tuple[str, dict]:
    with client.app.state.repository.connect() as conn:
        row = conn.execute(
            "SELECT status, target_json FROM practice_targets "
            "WHERE practice_target_id=?",
            (target_id,),
        ).fetchone()
    return row[0], json.loads(row[1])


def _counts(client) -> tuple[int, int, int, int]:
    with client.app.state.repository.connect() as conn:
        targets = conn.execute("SELECT COUNT(*) FROM practice_targets").fetchone()[0]
        exercises = conn.execute("SELECT COUNT(*) FROM exercise_instances").fetchone()[0]
        attempts = conn.execute("SELECT COUNT(*) FROM exercise_attempts").fetchone()[0]
        evaluations = conn.execute(
            "SELECT COUNT(*) FROM practice_evaluations").fetchone()[0]
    return targets, exercises, attempts, evaluations


class TestEvaluationReadApi:
    """MCU 5.1: persistence-backed evaluation availability states."""

    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def test_available_evaluation_is_returned_for_the_attempt(self, client):
        _, target = _seed_target(client)
        exercise = _seed_exercise(client, target)
        attempt = _submit_attempt(client, exercise)
        response = client.get(
            f"/api/v1/students/WU5-S/practice-targets/{target['practice_target_id']}/evaluations")
        assert response.status_code == 200, response.text
        evaluations = response.json()
        assert len(evaluations) == 1
        assert evaluations[0]["attempt_id"] == attempt["attempt_id"]
        assert evaluations[0]["practice_target_id"] == target["practice_target_id"]
        assert evaluations[0]["evaluation_method"] == "rule_based"

    def test_missing_evaluation_returns_empty_list(self, client):
        _, target = _seed_target(client)
        exercise = _seed_exercise(client, target)
        _insert_attempt(client, exercise["exercise_id"])
        response = client.get(
            f"/api/v1/students/WU5-S/practice-targets/{target['practice_target_id']}/evaluations")
        assert response.status_code == 200
        assert response.json() == []

    def test_malformed_evaluation_row_is_controlled_unavailable(self, client):
        _, target = _seed_target(client)
        exercise = _seed_exercise(client, target)
        _insert_attempt(client, exercise["exercise_id"])
        _insert_evaluation(client, "EA999999", target["practice_target_id"],
                           raw="{not valid json")
        response = client.get(
            f"/api/v1/students/WU5-S/practice-targets/{target['practice_target_id']}/evaluations")
        assert response.status_code == 200
        assert response.json() == []

    def test_evaluation_linked_to_other_target_is_excluded(self, client):
        _, target = _seed_target(client)
        other_id = "PT999999"
        _insert_evaluation(client, "EA999998", other_id,
                           evaluation_id="PE999998")
        response = client.get(
            f"/api/v1/students/WU5-S/practice-targets/{target['practice_target_id']}/evaluations")
        assert response.status_code == 200
        assert response.json() == []

    def test_evaluation_linked_to_other_attempt_is_excluded(self, client):
        _, target = _seed_target(client)
        exercise = _seed_exercise(client, target)
        _insert_attempt(client, exercise["exercise_id"])
        _insert_evaluation(client, "EA999998", target["practice_target_id"],
                           evaluation_id="PE999998")
        response = client.get(
            f"/api/v1/students/WU5-S/practice-targets/{target['practice_target_id']}/evaluations")
        assert response.status_code == 200
        assert response.json() == []

    def test_cross_student_attempt_evaluation_is_not_returned(self, client):
        _, target = _seed_target(client)
        exercise = _seed_exercise(client, target)
        _insert_attempt(client, exercise["exercise_id"], student_id="INTRUDER")
        _insert_evaluation(client, "EA999999", target["practice_target_id"])
        response = client.get(
            f"/api/v1/students/WU5-S/practice-targets/{target['practice_target_id']}/evaluations")
        assert response.status_code == 200
        assert response.json() == []

    def test_cross_student_access_returns_403(self, client):
        _seed_api(client, "INTRUDER")
        _, target = _seed_target(client)
        response = client.get(
            f"/api/v1/students/INTRUDER/practice-targets/{target['practice_target_id']}/evaluations")
        assert response.status_code == 403

    def test_unknown_target_returns_404(self, client):
        _seed_api(client)
        response = client.get(
            "/api/v1/students/WU5-S/practice-targets/PT999999/evaluations")
        assert response.status_code == 404

    def test_unknown_learner_returns_404(self, client):
        _, target = _seed_target(client)
        response = client.get(
            f"/api/v1/students/NOPE/practice-targets/{target['practice_target_id']}/evaluations")
        assert response.status_code == 404

    def test_read_performs_zero_writes(self, client):
        _, target = _seed_target(client)
        exercise = _seed_exercise(client, target)
        _submit_attempt(client, exercise)
        before = _counts(client)
        client.get(
            f"/api/v1/students/WU5-S/practice-targets/{target['practice_target_id']}/evaluations")
        assert _counts(client) == before


class TestCompletionApi:
    """MCU 5.2: eligibility, atomic transition, idempotency."""

    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def _complete(self, client, target_id, student_id="WU5-S"):
        return client.post(
            f"/api/v1/practice-targets/{target_id}/complete",
            json={"student_id": student_id},
        )

    def test_active_target_with_attempt_completes_atomically(self, client):
        _, target = _seed_target(client)
        exercise = _seed_exercise(client, target)
        _submit_attempt(client, exercise)
        response = self._complete(client, target["practice_target_id"])
        assert response.status_code == 200, response.text
        completed = response.json()
        assert completed["status"] == "completed"
        column_status, stored = _stored_target(client, target["practice_target_id"])
        assert column_status == "completed"
        assert stored["status"] == "completed"
        assert stored["updated_at"]
        assert stored["practice_target_id"] == target["practice_target_id"]

    def test_target_without_attempt_is_rejected_with_zero_writes(self, client):
        _, target = _seed_target(client)
        _seed_exercise(client, target)
        before = _counts(client)
        response = self._complete(client, target["practice_target_id"])
        assert response.status_code == 422
        assert _counts(client) == before

    def test_cross_student_completion_is_rejected(self, client):
        _seed_api(client, "INTRUDER")
        _, target = _seed_target(client)
        exercise = _seed_exercise(client, target)
        _submit_attempt(client, exercise)
        before = _counts(client)
        response = self._complete(client, target["practice_target_id"], "INTRUDER")
        assert response.status_code == 403
        assert _counts(client) == before

    def test_unknown_target_returns_404(self, client):
        _seed_api(client)
        response = self._complete(client, "PT999999")
        assert response.status_code == 404

    def test_unknown_learner_returns_404(self, client):
        _, target = _seed_target(client)
        response = self._complete(client, target["practice_target_id"], "NOPE")
        assert response.status_code == 404

    def test_unrelated_attempt_cannot_complete_target(self, client):
        essay_id, target = _seed_target(client)
        exercise = _seed_exercise(client, target)
        diagnosis = client.get(
            f"/api/v1/students/WU5-S/practice-targets/{target['practice_target_id']}/context"
        ).json()
        other = client.post("/api/v1/practice-targets", json={
            "student_id": "WU5-S", "source_submission_id": essay_id,
            "source_diagnosis_id": diagnosis["source_diagnosis_id"],
            "target_code": "connective_overuse",
            "target_label": "Review connective use",
            "gate_status": "selected",
        }).json()
        other_exercise = _seed_exercise(client, other)
        _submit_attempt(client, other_exercise)
        before = _counts(client)
        response = self._complete(client, target["practice_target_id"])
        assert response.status_code == 422
        assert _counts(client) == before

    def test_cross_student_attempt_is_not_eligible(self, client):
        _, target = _seed_target(client)
        exercise = _seed_exercise(client, target)
        _insert_attempt(client, exercise["exercise_id"], student_id="INTRUDER")
        response = self._complete(client, target["practice_target_id"])
        assert response.status_code == 422

    def test_invalid_input_attempt_is_not_eligible(self, client):
        _, target = _seed_target(client)
        exercise = _seed_exercise(client, target)
        _insert_attempt(client, exercise["exercise_id"], status="invalid_input")
        response = self._complete(client, target["practice_target_id"])
        assert response.status_code == 422

    def test_unsupported_status_is_rejected_safely(self, client):
        _, target = _seed_target(client)
        exercise = _seed_exercise(client, target)
        _submit_attempt(client, exercise)
        stored = dict(target, status="inactive")
        with client.app.state.repository.connect() as conn:
            conn.execute(
                "UPDATE practice_targets SET status='inactive', target_json=? "
                "WHERE practice_target_id=?",
                (json.dumps(stored), target["practice_target_id"]),
            )
        before = _counts(client)
        response = self._complete(client, target["practice_target_id"])
        assert response.status_code == 422
        assert _counts(client) == before

    def test_repeated_completion_is_idempotent(self, client):
        _, target = _seed_target(client)
        exercise = _seed_exercise(client, target)
        _submit_attempt(client, exercise)
        first = self._complete(client, target["practice_target_id"])
        second = self._complete(client, target["practice_target_id"])
        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()
        column_status, stored = _stored_target(client, target["practice_target_id"])
        assert column_status == "completed"
        assert stored["updated_at"] == first.json()["updated_at"]
        assert _counts(client)[0] == 1

    def test_concurrent_completion_produces_one_stable_result(self, client):
        _, target = _seed_target(client)
        exercise = _seed_exercise(client, target)
        _submit_attempt(client, exercise)
        service = client.app.state.practice_target_completion_service
        results = []

        def worker():
            results.append(service.complete_target(
                student_id="WU5-S",
                practice_target_id=target["practice_target_id"],
            ))

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker) for _ in range(2)]
            for future in futures:
                future.result()
        assert len(results) == 2
        assert all(item["status"] == "completed" for item in results)
        assert results[0]["updated_at"] == results[1]["updated_at"]
        column_status, stored = _stored_target(client, target["practice_target_id"])
        assert column_status == "completed"
        assert stored["status"] == "completed"

    def test_completion_creates_no_duplicate_rows(self, client):
        _, target = _seed_target(client)
        exercise = _seed_exercise(client, target)
        _submit_attempt(client, exercise)
        before = _counts(client)
        self._complete(client, target["practice_target_id"])
        self._complete(client, target["practice_target_id"])
        assert _counts(client) == before

    def test_legacy_target_with_attempt_completes(self, client):
        essay_id, record, index = _seed_api(client)
        priorities = json.loads(record["feedback_json"])["priority_feedback"]
        diagnosis_id = priorities[index]["diagnosis_id"]
        legacy = client.post("/api/v1/practice-targets", json={
            "student_id": "WU5-S", "source_submission_id": essay_id,
            "source_diagnosis_id": diagnosis_id,
            "target_code": "lexical_repetition_local",
            "target_label": "Reduce lexical repetition",
            "gate_status": "selected",
        })
        assert legacy.status_code == 200, legacy.text
        legacy_target = legacy.json()
        exercise = _seed_exercise(client, legacy_target)
        _submit_attempt(client, exercise)
        response = self._complete(client, legacy_target["practice_target_id"])
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "completed"

    def test_reopening_priority_reuses_completed_target(self, client):
        essay_id, record, index = _seed_api(client)
        payload = {
            "student_id": "WU5-S", "source_submission_id": essay_id,
            "priority_index": index,
        }
        target = client.post("/api/v1/practice-targets", json=payload).json()
        exercise = _seed_exercise(client, target)
        _submit_attempt(client, exercise)
        self._complete(client, target["practice_target_id"])
        reopened = client.post("/api/v1/practice-targets", json=payload)
        assert reopened.status_code == 200
        assert reopened.json()["practice_target_id"] == target["practice_target_id"]
        assert reopened.json()["status"] == "completed"
        assert _counts(client)[0] == 1


def _run_harness(**config):
    at = AppTest.from_file(str(HARNESS), default_timeout=90)
    for key, value in config.items():
        # Deep copy: the page mutates loaded dicts in place, so shared
        # module-level fixtures must never leak across AppTest sessions.
        at.session_state[key] = json.loads(json.dumps(value))
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
    return at


def _markdown_text(at) -> str:
    return " ".join(m.value for m in at.markdown)


def _button_labels(at) -> dict:
    return {button.key: button.label for button in at.button}


def _fake_client(at):
    return at.session_state["fake_client"]


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

COMPLETED_TARGET = dict(PRIORITY_TARGET, status="completed",
                        updated_at="2026-01-02T00:00:00+00:00")

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
    "source_writing_text": "Parks support public health.",
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

ATTEMPT = {
    "attempt_id": "EA000001",
    "exercise_id": "EX000001",
    "student_id": "S02",
    "attempt_number": 1,
    "response_text": "Communities can protect public health.",
    "status": "submitted",
}

EVALUATION = {
    "evaluation_id": "PE000001",
    "attempt_id": "EA000001",
    "practice_target_id": "PT000001",
    "evaluation_method": "rule_based",
    "completion_status": "completed",
    "target_action_status": "inconclusive",
    "evidence": ["Response length: 37 characters"],
    "confidence": "medium",
    "limitations": ["Task-specific only."],
    "evaluator_version": "practice-evaluator-v0.9.0",
    "created_at": "2026-01-01T00:00:01+00:00",
}


class TestPracticePageEvaluation:
    """MCU 5.1 page states: available and unavailable evaluation."""

    def test_available_evaluation_renders_from_persisted_read(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
            harness_attempts=[ATTEMPT],
            harness_evaluations=[EVALUATION],
        )
        text = _markdown_text(at)
        assert t("student_practice_completion_completed", "en") in text

    def test_missing_evaluation_renders_honest_unavailable_notice(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
            harness_attempts=[ATTEMPT],
        )
        assert t("student_practice_evaluation_unavailable", "en") in _markdown_text(at)


class TestPracticePageCompletion:
    """MCU 5.3/5.4 page states: finish action, completed state, next steps."""

    def test_finish_action_appears_only_after_saved_attempt(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
        )
        labels = _button_labels(at)
        assert "practice_finish" not in labels

    def test_finish_click_completes_and_renders_completed_state(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
            harness_attempts=[ATTEMPT],
        )
        assert _button_labels(at).get("practice_finish") == t(
            "student_practice_finish_cycle", "en")
        at.button(key="practice_finish").click().run()
        assert not at.exception, at.exception
        assert _fake_client(at).complete_count == 1
        text = _markdown_text(at)
        assert t("student_practice_completed_title", "en") in text
        assert t("student_practice_completed_saved", "en") in text
        assert "Reduce lexical repetition" in text
        assert "EA000001" in text
        assert "practice_finish" not in _button_labels(at)
        assert not [ta for ta in at.text_area if ta.key == "practice_response_v2"]

    def test_completion_failure_shows_error_and_keeps_finish_action(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
            harness_attempts=[ATTEMPT],
            harness_fail_complete=True,
        )
        at.button(key="practice_finish").click().run()
        assert not at.exception, at.exception
        text = _markdown_text(at)
        assert t("student_practice_completed_title", "en") not in text
        assert t("error_backend_processing_error", "en") in text
        assert "practice_finish" in _button_labels(at)

    def test_completed_target_reentry_shows_terminal_state(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            harness_targets=[COMPLETED_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
            harness_attempts=[ATTEMPT],
            harness_evaluations=[EVALUATION],
        )
        text = _markdown_text(at)
        assert t("student_practice_completed_title", "en") in text
        assert t("student_practice_completed_saved", "en") in text
        assert "EA000001" in text
        assert "practice_finish" not in _button_labels(at)
        assert not [ta for ta in at.text_area if ta.key == "practice_response_v2"]

    def test_completed_target_reentry_through_preset(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            practice_target_preset="PT000001",
            harness_targets=[COMPLETED_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
            harness_attempts=[ATTEMPT],
        )
        assert t("student_practice_completed_title", "en") in _markdown_text(at)
        assert "practice_target_preset" not in at.session_state

    def test_completed_target_does_not_override_active_selection(self):
        active = dict(PRIORITY_TARGET, practice_target_id="PT000002",
                      target_label="Vary sentence length")
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            harness_targets=[COMPLETED_TARGET, active],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
            harness_attempts=[ATTEMPT],
        )
        text = _markdown_text(at)
        assert "Vary sentence length" in text
        assert t("student_practice_completed_title", "en") not in text

    def test_rerun_keeps_selected_target_with_another_active_present(self):
        other = dict(PRIORITY_TARGET, practice_target_id="PT000002",
                     source_submission_id=29, source_priority_id="PRIO-2-0",
                     target_label="Vary sentence length")
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            practice_target_preset="PT000001",
            harness_targets=[other, PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
        )
        # The harness runs twice: the preset is consumed on the first run and
        # the learner-scoped selection must keep the same target on reruns.
        text = _markdown_text(at)
        assert "Reduce lexical repetition" in text
        assert "Vary sentence length" not in text
        assert [ta for ta in at.text_area if ta.key == "practice_response_v2"]

    def test_pending_marker_consumes_duplicate_completion(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
            harness_attempts=[ATTEMPT],
            practice_submit_pending=True,
        )
        assert t("student_practice_finish_pending", "en") in _markdown_text(at)
        assert _fake_client(at).complete_count == 0

    def test_completed_state_shows_return_and_journey_actions(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            harness_targets=[COMPLETED_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
            harness_attempts=[ATTEMPT],
        )
        labels = _button_labels(at)
        assert labels.get("practice_return_feedback") == t(
            "student_practice_return_feedback", "en")
        assert labels.get("practice_open_journey") == t(
            "student_practice_open_journey", "en")

    def test_other_active_target_action_opens_it_explicitly(self):
        other = dict(PRIORITY_TARGET, practice_target_id="PT000002",
                     source_submission_id=29, source_priority_id="PRIO-2-0",
                     target_label="Vary sentence length")
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            harness_targets=[COMPLETED_TARGET, other],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
            harness_attempts=[ATTEMPT],
        )
        at.session_state["practice_target_preset"] = "PT000001"
        at.run()
        assert not at.exception, at.exception
        labels = _button_labels(at)
        assert labels.get("practice_open_other_target") == t(
            "student_practice_open_other_target", "en")
        at.button(key="practice_open_other_target").click().run()
        assert not at.exception, at.exception
        assert "Vary sentence length" in _markdown_text(at)
        assert t("student_practice_completed_title", "en") not in _markdown_text(at)

    def test_no_other_active_target_means_no_auto_selection_button(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            harness_targets=[COMPLETED_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
            harness_attempts=[ATTEMPT],
        )
        assert "practice_open_other_target" not in _button_labels(at)

    def test_completed_state_has_no_mastery_wording(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            harness_targets=[COMPLETED_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
            harness_attempts=[ATTEMPT],
        )
        text = _markdown_text(at).lower()
        for forbidden in ("mastered", "improved", "proficient", "passed"):
            assert forbidden not in text
