# -*- coding: utf-8 -*-
"""Wave-3 WU4 focused tests: adaptive learning student experience.

Covers the accepted L2 WU3 API contract consumed through the existing Wave-2
frontend architecture:

- WU3 endpoint constants and the student-facing allowlist policy
  (contracts.py).
- WU3 client methods with exact paths/payloads and fail-closed
  classification (client.py).
- Student-safe gateway views over the WU3 payloads, graceful degradation,
  learner isolation, and no raw-internal leakage (gateway.py).
- The Today/adaptive page renderer (features/student/adaptive.py):
  deterministic recommendation + explicit learner choice + qualified
  activity + evaluation + bounded self-rating + next-step; Tutor consent
  accept/decline/unavailable; mini-writing handoff; Today/Journey/Practice
  navigation; en/zh locale parity; zero writes on read-only render; no
  unsupported claims or raw locale keys in rendered output.
"""

from __future__ import annotations

import json
import pathlib

import pytest
import requests

from streamlit.testing.v1 import AppTest

from app.ui.locale import t
from app.ui.wave2.client import (
    Wave2ApiClient,
    Wave2ApiClientError,
    Wave2ApiUnavailable,
)
from app.ui.wave2.contracts import (
    ADAPTIVE_PRACTICE_EVALUATE,
    ADAPTIVE_PRACTICE_RECOMMEND,
    ADAPTIVE_PRACTICE_SELECT,
    PERSONALIZED_MINI_WRITING,
    STUDENT_INTERNAL_KEYS,
    TUTOR_ACCEPT,
    TUTOR_DECLINE,
    TUTOR_OBSERVATION,
    TUTOR_RECOMMEND,
)
from app.ui.wave2.gateway import Wave2Gateway
from app.ui.wave2.views import FORBIDDEN_VIEW_KEYS


ROOT = pathlib.Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "harness_wu4_adaptive.py"

WU3_ENDPOINTS = {
    "recommend": ("POST", "/api/v1/wave2/personalized/adaptive-practice/recommend"),
    "select": ("POST", "/api/v1/wave2/personalized/adaptive-practice/select"),
    "evaluate": ("POST", "/api/v1/wave2/personalized/adaptive-practice/evaluate"),
    "mini_writing": ("POST", "/api/v1/wave2/personalized/mini-writing"),
    "tutor_recommend": ("POST", "/api/v1/wave2/personalized/tutor/recommend"),
    "tutor_accept": ("POST", "/api/v1/wave2/personalized/tutor/accept"),
    "tutor_decline": ("POST", "/api/v1/wave2/personalized/tutor/decline"),
    "tutor_observation": ("POST", "/api/v1/wave2/personalized/tutor/observation"),
}

# ---------------------------------------------------------------------------
# WU3-shaped payload fixtures (mirror the accepted L2 WU3 models)
# ---------------------------------------------------------------------------

QUALIFIED_ACTIVITY = {
    "activity_id": "QA-L-01-lexical_repetition-guided_sentence_rewrite",
    "learner_id": "S02",
    "target_code": "lexical_repetition_local",
    "target_label": "Reduce lexical repetition",
    "category": "lexical_repetition",
    "exercise_type": "guided_sentence_rewrite",
    "exercise_version": "exercise-v0.9.0",
    "source_submission_id": 1001,
    "source_priority_id": "PRIO-7-0",
    "evidence_ids": ["7"],
    "instructions": "Rewrite the sentence to address the selected priority.",
    "source_text": "Parks are good. Parks help health.",
    "evaluation_criteria": {
        "evaluation_method": "rule_based",
        "evaluator_version": "practice-evaluator-v0.9.0",
        "completion_criteria": "A non-empty rewritten sentence that addresses the target.",
        "observable_target_criteria": "The targeted feature is reduced or removed.",
    },
    "limitations": ["Activities are practice suggestions; descriptive only."],
    "claims_status": "observation_only",
}

RECOMMENDATION = {
    "recommendation_id": "AR-L-01-lexical_repetition",
    "learner_id": "S02",
    "state": "recommended",
    "default_activity_id": QUALIFIED_ACTIVITY["activity_id"],
    "qualified_activities": [QUALIFIED_ACTIVITY],
    "reasons": [
        "qualified subset selected from the existing practice capability",
        "deterministic default: stored plan order, then exercise-spec order",
    ],
    "learner_choice_allowed": True,
    "limitations": ["Activities are practice suggestions; descriptive only."],
    "claims_status": "observation_only",
}

SELECTION = {
    "selection_id": "AS-L-01-QA-L-01",
    "learner_id": "S02",
    "recommendation_id": RECOMMENDATION["recommendation_id"],
    "activity": QUALIFIED_ACTIVITY,
    "choice_kind": "explicit",
    "limitations": ["Selection is learner-owned; descriptive only."],
    "claims_status": "observation_only",
}

EVALUATION = {
    "evaluation_id": "AE-L-01-QA-L-01",
    "learner_id": "S02",
    "activity_id": QUALIFIED_ACTIVITY["activity_id"],
    "completion_status": "completed",
    "target_action_status": "candidate_detected",
    "evidence": ["The targeted feature is reduced in the response."],
    "evaluator_version": "practice-evaluator-v0.9.0",
    "evaluation_method": "rule_based",
    "limitations": ["Observable evidence is task-specific; descriptive only."],
    "claims_status": "observation_only",
}

MINI_WRITING = {
    "result_id": "MW-L-01-002001",
    "learner_id": "S02",
    "task_id": "WT000001",
    "submission_id": 2001,
    "analysis_run_id": "AR2001",
    "analysis_version": "spacy-analyzer-v0.8.0",
    "feedback_record_id": 3001,
    "essay_text_hash": "a" * 64,
    "word_count": 12,
    "pipeline_adapter": "writing-intelligence-pipeline-v0.9.7",
    "bounded": True,
    "limitations": ["Mini-writing is learner text; descriptive only."],
    "claims_status": "observation_only",
}

TUTOR_DUE = {
    "recommendation_id": "TR-L-01-due-LI000001",
    "learner_id": "S02",
    "state": "due_item",
    "learning_item_ids": ["LI000001"],
    "categories": ["lexical_repetition"],
    "suggestion": "1 due review item is available for practice; scheduling state is descriptive.",
    "history_reasons": ["due per the durable scheduler state"],
    "positive_observations": [],
    "limitations": ["Scheduling state is descriptive; not an outcome measure."],
    "claims_status": "observation_only",
}

TUTOR_HISTORY = {
    "recommendation_id": "TR-L-01-history-lexical_repetition",
    "learner_id": "S02",
    "state": "history_grounded",
    "learning_item_ids": [],
    "categories": ["lexical_repetition"],
    "suggestion": "Stored learner history is available to ground a practice suggestion.",
    "history_reasons": ["grounded in stored priority plans and learning items"],
    "positive_observations": [],
    "limitations": ["History-grounded suggestions are descriptive."],
    "claims_status": "observation_only",
}

TUTOR_POSITIVE = {
    "recommendation_id": "TR-L-01-positive-lexical_repetition",
    "learner_id": "S02",
    "state": "positive_observation",
    "learning_item_ids": [],
    "categories": ["lexical_repetition"],
    "suggestion": "The targeted feature is not observed in the latest writing sample.",
    "history_reasons": ["authentic writing observation"],
    "positive_observations": [{
        "observation_id": "PO-L-01-lexical_repetition",
        "learner_id": "S02",
        "category": "lexical_repetition",
        "target_code": "lexical_repetition_local",
        "later_submission_id": 2002,
        "statement": "The targeted feature is not observed in the latest sample.",
        "non_causal_note": "Observation only; not proof of learning, transfer, or ability change.",
        "evidence_kind": "authentic_writing",
        "limitations": ["Single-sample absence is descriptive only."],
        "claims_status": "observation_only",
    }],
    "limitations": ["Observations are non-causal."],
    "claims_status": "observation_only",
}

TUTOR_INSUFFICIENT = {
    "recommendation_id": "TR-L-NEVER-none-none",
    "learner_id": "S02",
    "state": "insufficient_history",
    "learning_item_ids": [],
    "categories": [],
    "suggestion": "No stored history is available for a grounded suggestion.",
    "history_reasons": ["no stored learning items, plans, or observations"],
    "positive_observations": [],
    "limitations": ["A Tutor suggestion requires stored learner evidence."],
    "claims_status": "observation_only",
}

DECISION_ACCEPT = {
    "decision_id": "TD-L-01-TR-1-accept",
    "learner_id": "S02",
    "recommendation_id": TUTOR_DUE["recommendation_id"],
    "decision": "accept",
    "consent_applied": True,
    "executed": True,
    "action": "presented the suggestion after explicit learner consent",
    "limitations": ["No unsupported personalized claim is recorded."],
    "claims_status": "observation_only",
}

DECISION_DECLINE = {
    "decision_id": "TD-L-01-TR-1-decline",
    "learner_id": "S02",
    "recommendation_id": TUTOR_DUE["recommendation_id"],
    "decision": "decline",
    "consent_applied": False,
    "executed": False,
    "action": None,
    "limitations": ["Decline performs no execution and records no practice evidence."],
    "claims_status": "observation_only",
}

OBSERVATION = {
    "learner_id": "S02",
    "observation": {
        "observation_id": "PO-L-01-lexical_repetition",
        "learner_id": "S02",
        "category": "lexical_repetition",
        "target_code": "lexical_repetition_local",
        "later_submission_id": 2002,
        "statement": "The targeted feature is not observed in the latest sample.",
        "non_causal_note": "Observation only; not proof of learning, transfer, or ability change.",
        "evidence_kind": "authentic_writing",
        "limitations": ["Single-sample absence is descriptive only."],
        "claims_status": "observation_only",
    },
}


# ---------------------------------------------------------------------------
# 1. Contracts: WU3 endpoint constants and allowlist policy
# ---------------------------------------------------------------------------

class TestWU3Contracts:
    def test_wu3_endpoint_constants_exact(self):
        assert ADAPTIVE_PRACTICE_RECOMMEND == (
            "/api/v1/wave2/personalized/adaptive-practice/recommend")
        assert ADAPTIVE_PRACTICE_SELECT == (
            "/api/v1/wave2/personalized/adaptive-practice/select")
        assert ADAPTIVE_PRACTICE_EVALUATE == (
            "/api/v1/wave2/personalized/adaptive-practice/evaluate")
        assert PERSONALIZED_MINI_WRITING == (
            "/api/v1/wave2/personalized/mini-writing")
        assert TUTOR_RECOMMEND == "/api/v1/wave2/personalized/tutor/recommend"
        assert TUTOR_ACCEPT == "/api/v1/wave2/personalized/tutor/accept"
        assert TUTOR_DECLINE == "/api/v1/wave2/personalized/tutor/decline"
        assert TUTOR_OBSERVATION == "/api/v1/wave2/personalized/tutor/observation"

    def test_eight_wu3_endpoints_exactly(self):
        constants = {
            "recommend": ADAPTIVE_PRACTICE_RECOMMEND,
            "select": ADAPTIVE_PRACTICE_SELECT,
            "evaluate": ADAPTIVE_PRACTICE_EVALUATE,
            "mini_writing": PERSONALIZED_MINI_WRITING,
            "tutor_recommend": TUTOR_RECOMMEND,
            "tutor_accept": TUTOR_ACCEPT,
            "tutor_decline": TUTOR_DECLINE,
            "tutor_observation": TUTOR_OBSERVATION,
        }
        assert len(constants) == 8
        for name, path in constants.items():
            expected_method, expected_path = WU3_ENDPOINTS[name]
            assert expected_path == path
            assert expected_method == "POST"

    def test_wu3_internal_keys_added_to_allowlist_policy(self):
        # Raw WU3 internals must never reach a student-facing view.
        for key in (
            "target_code", "source_priority_id", "evidence_ids",
            "exercise_version", "evaluator_version", "learning_item_ids",
            "later_submission_id", "pipeline_adapter", "positive_observations",
            "due",
        ):
            assert key in STUDENT_INTERNAL_KEYS, key
        # The guard set exported for views must contain them too.
        for key in ("target_code", "evidence_ids", "pipeline_adapter",
                    "positive_observations"):
            assert key in FORBIDDEN_VIEW_KEYS, key


# ---------------------------------------------------------------------------
# 2. Client: exact WU3 requests and fail-closed classification
# ---------------------------------------------------------------------------

class _RecordingSession:
    """requests.Session stand-in recording method/path/json calls."""

    def __init__(self, status: int = 200, payload: dict | None = None):
        self.status = status
        self.payload = payload or {}
        self.calls: list[tuple[str, str, dict | None]] = []

    def request(self, method, url, timeout=None, json=None):
        self.calls.append((method, url, json))
        response = _FakeResponse(self.status, self.payload)
        return response


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return dict(self._payload)


class TestWU3Client:
    def _client(self, status=200, payload=None):
        session = _RecordingSession(status=status, payload=payload)
        client = Wave2ApiClient("http://127.0.0.1:8000", session=session)
        return client, session

    def test_adaptive_recommend_posts_exact_path_and_payload(self):
        client, session = self._client(payload=RECOMMENDATION)
        result = client.adaptive_recommend("S02")
        assert result == RECOMMENDATION
        method, url, body = session.calls[0]
        assert method == "POST"
        assert url == "http://127.0.0.1:8000" + ADAPTIVE_PRACTICE_RECOMMEND
        assert body == {"learner_id": "S02"}

    def test_adaptive_select_posts_exact_path_and_payload(self):
        client, session = self._client(payload=SELECTION)
        result = client.adaptive_select("S02", "AR-1", "QA-1")
        assert result == SELECTION
        method, url, body = session.calls[0]
        assert url == "http://127.0.0.1:8000" + ADAPTIVE_PRACTICE_SELECT
        assert body == {
            "learner_id": "S02", "recommendation_id": "AR-1", "activity_id": "QA-1",
        }

    def test_adaptive_evaluate_posts_exact_path_and_payload(self):
        client, session = self._client(payload=EVALUATION)
        result = client.adaptive_evaluate("S02", "QA-1", "My response.")
        assert result == EVALUATION
        method, url, body = session.calls[0]
        assert url == "http://127.0.0.1:8000" + ADAPTIVE_PRACTICE_EVALUATE
        assert body == {"learner_id": "S02", "activity_id": "QA-1",
                        "response_text": "My response."}

    def test_mini_writing_posts_exact_path_and_payload(self):
        client, session = self._client(payload=MINI_WRITING)
        result = client.mini_writing("S02", "WT000001", "A short passage.")
        assert result == MINI_WRITING
        method, url, body = session.calls[0]
        assert url == "http://127.0.0.1:8000" + PERSONALIZED_MINI_WRITING
        assert body == {"learner_id": "S02", "task_id": "WT000001",
                        "text": "A short passage."}

    def test_tutor_recommend_posts_exact_path_and_payload(self):
        client, session = self._client(payload=TUTOR_DUE)
        result = client.tutor_recommend("S02")
        assert result == TUTOR_DUE
        method, url, body = session.calls[0]
        assert url == "http://127.0.0.1:8000" + TUTOR_RECOMMEND
        assert body == {"learner_id": "S02"}

    def test_tutor_accept_posts_consent_snapshot(self):
        client, session = self._client(payload=DECISION_ACCEPT)
        consent = {
            "learner_id": "S02", "granted": True, "revoked": False,
            "scope": "proactive_tutor_execution",
            "consent_version": "learner-consent-v0.1.0",
            "granted_at": "2026-08-12T10:00:00Z",
        }
        result = client.tutor_accept("S02", "TR-1", consent)
        assert result == DECISION_ACCEPT
        method, url, body = session.calls[0]
        assert url == "http://127.0.0.1:8000" + TUTOR_ACCEPT
        assert body == {"learner_id": "S02", "recommendation_id": "TR-1",
                        "consent": consent}

    def test_tutor_decline_posts_exact_path_and_payload(self):
        client, session = self._client(payload=DECISION_DECLINE)
        result = client.tutor_decline("S02", "TR-1")
        assert result == DECISION_DECLINE
        method, url, body = session.calls[0]
        assert url == "http://127.0.0.1:8000" + TUTOR_DECLINE
        assert body == {"learner_id": "S02", "recommendation_id": "TR-1"}

    def test_tutor_observation_posts_exact_path_and_payload(self):
        client, session = self._client(payload=OBSERVATION)
        result = client.tutor_observation("S02", "lexical_repetition")
        assert result == OBSERVATION
        method, url, body = session.calls[0]
        assert url == "http://127.0.0.1:8000" + TUTOR_OBSERVATION
        assert body == {"learner_id": "S02", "category": "lexical_repetition"}

    def test_unavailable_status_classifies_as_wave2_unavailable(self):
        for status in (404, 405, 503):
            client, _ = self._client(status=status)
            with pytest.raises(Wave2ApiUnavailable):
                client.adaptive_recommend("S02")

    def test_other_error_classifies_as_client_error(self):
        client, _ = self._client(status=422)
        with pytest.raises(Wave2ApiClientError) as excinfo:
            client.tutor_accept("S02", "TR-1", None)
        assert excinfo.value.http_status == 422


# ---------------------------------------------------------------------------
# 3. Gateway: student-safe WU3 views + graceful degradation
# ---------------------------------------------------------------------------

class _StubWave2Client:
    """In-memory Wave2 client stub returning scripted WU3 payloads."""

    def __init__(self, payloads: dict, *, available: bool = True):
        self._payloads = payloads
        self._available = available
        self.calls: list[tuple[str, tuple]] = []

    def probe(self) -> bool:
        return self._available

    def _call(self, name, *args):
        if not self._available:
            raise Wave2ApiUnavailable("stub unavailable", operation=name)
        self.calls.append((name, args))
        return dict(self._payloads[name])

    def adaptive_recommend(self, learner_id):
        return self._call("adaptive_recommend", learner_id)

    def adaptive_select(self, learner_id, recommendation_id, activity_id):
        return self._call("adaptive_select", learner_id, recommendation_id, activity_id)

    def adaptive_evaluate(self, learner_id, activity_id, response_text):
        return self._call("adaptive_evaluate", learner_id, activity_id, response_text)

    def mini_writing(self, learner_id, task_id, text):
        return self._call("mini_writing", learner_id, task_id, text)

    def tutor_recommend(self, learner_id):
        return self._call("tutor_recommend", learner_id)

    def tutor_accept(self, learner_id, recommendation_id, consent):
        return self._call("tutor_accept", learner_id, recommendation_id, consent)

    def tutor_decline(self, learner_id, recommendation_id):
        return self._call("tutor_decline", learner_id, recommendation_id)

    def tutor_observation(self, learner_id, category):
        return self._call("tutor_observation", learner_id, category)


def _make_gateway(payloads: dict, *, available: bool = True):
    stub = _StubWave2Client(payloads, available=available)
    return Wave2Gateway(wave2_client=stub, legacy_client=None, mode="wave2"), stub


class TestWU3GatewayViews:
    def _gateway(self, payloads: dict, *, available: bool = True):
        return _make_gateway(payloads, available=available)

    def _assert_no_internal_keys(self, view: dict, tag: str):
        """Recursively assert no STUDENT_INTERNAL_KEYS value appears."""
        if isinstance(view, dict):
            for key, value in view.items():
                assert key not in FORBIDDEN_VIEW_KEYS, (tag, key)
                self._assert_no_internal_keys(value, tag)
        elif isinstance(view, list):
            for item in view:
                self._assert_no_internal_keys(item, tag)

    def test_recommendation_view_is_student_safe(self):
        gateway, stub = self._gateway({"adaptive_recommend": RECOMMENDATION})
        view = gateway.adaptive_recommend("S02")
        assert view["available"] is True
        assert view["state"] == "recommended"
        assert view["default_activity_id"] == QUALIFIED_ACTIVITY["activity_id"]
        assert view["learner_choice_allowed"] is True
        assert view["reasons"] == RECOMMENDATION["reasons"]
        activity = view["qualified_activities"][0]
        assert activity["target_label"] == "Reduce lexical repetition"
        assert activity["instructions"]
        assert activity["source_text"]
        assert activity["evaluation_criteria"]["completion_criteria"]
        self._assert_no_internal_keys(view, "recommend")
        assert "target_code" not in activity
        assert "evidence_ids" not in activity

    def test_selection_view_keeps_activity_and_choice_kind(self):
        gateway, stub = self._gateway({
            "adaptive_recommend": RECOMMENDATION,
            "adaptive_select": SELECTION,
        })
        gateway.adaptive_recommend("S02")
        view = gateway.adaptive_select("S02", RECOMMENDATION["recommendation_id"],
                                       QUALIFIED_ACTIVITY["activity_id"])
        assert view["available"] is True
        assert view["choice_kind"] == "explicit"
        assert view["activity"]["target_label"] == "Reduce lexical repetition"
        self._assert_no_internal_keys(view, "select")

    def test_evaluation_view_drops_internal_versions(self):
        gateway, stub = self._gateway({"adaptive_evaluate": EVALUATION})
        view = gateway.adaptive_evaluate("S02", "QA-1", "My response.")
        assert view["completion_status"] == "completed"
        assert view["target_action_status"] == "candidate_detected"
        assert view["evidence_statements"] == EVALUATION["evidence"]
        assert "evaluator_version" not in view
        self._assert_no_internal_keys(view, "evaluate")

    def test_mini_writing_view_is_student_safe(self):
        gateway, stub = self._gateway({"mini_writing": MINI_WRITING})
        view = gateway.mini_writing("S02", "WT000001", "A short passage.")
        assert view["submission_id"] == 2001
        assert view["word_count"] == 12
        assert view["bounded"] is True
        assert "essay_text_hash" not in view
        assert "analysis_run_id" not in view
        self._assert_no_internal_keys(view, "mini_writing")

    def test_tutor_recommendation_view_states(self):
        for payload in (TUTOR_DUE, TUTOR_HISTORY, TUTOR_POSITIVE, TUTOR_INSUFFICIENT):
            gateway, stub = self._gateway({"tutor_recommend": payload})
            view = gateway.tutor_recommend("S02")
            assert view["state"] == payload["state"]
            assert view["suggestion"]
            assert "learning_item_ids" not in view
            assert "history_reasons" not in view
            self._assert_no_internal_keys(view, f"tutor_{payload['state']}")
        # positive observations carry only bounded statement + note
        gateway, stub = self._gateway({"tutor_recommend": TUTOR_POSITIVE})
        view = gateway.tutor_recommend("S02")
        observation = view["observations"][0]
        assert observation["statement"]
        assert observation["non_causal_note"]
        assert "observation_id" not in observation
        assert "later_submission_id" not in observation

    def test_tutor_decision_views_accept_and_decline(self):
        gateway, stub = self._gateway({"tutor_accept": DECISION_ACCEPT})
        view = gateway.tutor_accept("S02", TUTOR_DUE["recommendation_id"],
                                    {"learner_id": "S02", "granted": True})
        assert view["decision"] == "accept"
        assert view["consent_applied"] is True
        assert view["executed"] is True
        self._assert_no_internal_keys(view, "accept")
        gateway, stub = self._gateway({"tutor_decline": DECISION_DECLINE})
        view = gateway.tutor_decline("S02", TUTOR_DUE["recommendation_id"])
        assert view["decision"] == "decline"
        assert view["executed"] is False
        self._assert_no_internal_keys(view, "decline")

    def test_tutor_observation_view(self):
        gateway, stub = self._gateway({"tutor_observation": OBSERVATION})
        view = gateway.tutor_observation("S02", "lexical_repetition")
        assert view["observation"]["statement"]
        assert view["observation"]["non_causal_note"]
        assert "observation_id" not in view["observation"]
        self._assert_no_internal_keys(view, "observation")

    def test_insufficient_history_recommendation_view(self):
        insufficient = dict(RECOMMENDATION, state="insufficient_history",
                            qualified_activities=[], default_activity_id=None,
                            learner_choice_allowed=False)
        gateway, stub = self._gateway({"adaptive_recommend": insufficient})
        view = gateway.adaptive_recommend("S02")
        assert view["state"] == "insufficient_history"
        assert view["qualified_activities"] == []
        assert view["learner_choice_allowed"] is False


class TestWU3GatewayDegradation:
    def test_unavailable_wave2_degrades_recommend(self):
        gateway, stub = _make_gateway({"adaptive_recommend": RECOMMENDATION},
                                      available=False)
        view = gateway.adaptive_recommend("S02")
        assert view == {"available": False, "state": "unavailable"}

    def test_unavailable_wave2_degrades_all_wu3_methods(self):
        gateway, stub = _make_gateway({}, available=False)
        assert gateway.adaptive_recommend("S02")["available"] is False
        assert gateway.adaptive_select("S02", "R", "A")["available"] is False
        assert gateway.adaptive_evaluate("S02", "A", "x")["available"] is False
        assert gateway.mini_writing("S02", "T", "x")["available"] is False
        assert gateway.tutor_recommend("S02")["available"] is False
        assert gateway.tutor_accept("S02", "R", {})["available"] is False
        assert gateway.tutor_decline("S02", "R")["available"] is False
        assert gateway.tutor_observation("S02", "c")["available"] is False

    def test_legacy_mode_degrades(self):
        gateway = Wave2Gateway(wave2_client=None, legacy_client=None, mode="legacy")
        assert gateway.adaptive_recommend("S02") == {
            "available": False, "state": "unavailable",
        }
        assert gateway.tutor_recommend("S02")["available"] is False

    def test_learner_isolation_payloads_carry_requested_learner(self):
        gateway, stub = _make_gateway({
            "adaptive_recommend": RECOMMENDATION,
            "adaptive_select": SELECTION,
        })
        gateway.adaptive_recommend("OTHER")
        gateway.adaptive_recommend("S02")
        assert stub.calls[0][1][0] == "OTHER"
        assert stub.calls[1][1][0] == "S02"


# ---------------------------------------------------------------------------
# 4. Today/adaptive page rendering (AppTest)
# ---------------------------------------------------------------------------

def _run_harness(**config):
    at = AppTest.from_file(str(HARNESS), default_timeout=90)
    for key, value in config.items():
        at.session_state[key] = json.loads(json.dumps(value))
    at.run()
    assert not at.exception, at.exception
    return at


def _markdown_text(at):
    return " ".join(m.value for m in at.markdown)


def _button_keys(at):
    return {button.key: button.label for button in at.button}


def _enter_learner(at, learner_id: str = "S02"):
    student_input = next(
        (ti for ti in at.text_input if ti.key == "adaptive_student"), None)
    if student_input is not None and not student_input.value:
        student_input.set_value(learner_id).run()
        assert not at.exception, at.exception
    return at


def _gateway(at):
    return at.session_state["wu4_adaptive_gateway"]


class TestAdaptivePageStructure:
    def test_default_render_has_header_and_blocked_action(self):
        at = _run_harness()
        text = _markdown_text(at)
        assert "px-page-heading" in text
        assert t("student_adaptive_title", "en") in text
        assert 'data-state="blocked"' in text
        assert t("student_adaptive_boundary", "en") in text

    def test_no_learner_does_not_call_gateway(self):
        at = _run_harness(harness_learner="")
        gateway = _gateway(at)
        assert gateway.adaptive_recommend_calls == []


class TestAdaptiveRecommendation:
    def test_recommended_shows_reasons_and_choice(self):
        at = _run_harness(harness_adaptive_recommend=RECOMMENDATION)
        _enter_learner(at)
        text = _markdown_text(at)
        assert t("student_adaptive_recommend_section", "en") in text
        assert "deterministic default" in text
        radio_options = [
            option for radio in at.radio for option in radio.options
        ]
        assert "Reduce lexical repetition" in radio_options
        button_labels = [button.label for button in at.button]
        assert t("student_adaptive_use_activity", "en") in button_labels

    def test_insufficient_history_is_honest(self):
        insufficient = dict(RECOMMENDATION, state="insufficient_history",
                            qualified_activities=[], default_activity_id=None,
                            learner_choice_allowed=False)
        at = _run_harness(harness_adaptive_recommend=insufficient)
        _enter_learner(at)
        text = _markdown_text(at)
        assert t("student_adaptive_insufficient_history", "en") in text
        assert "px-notice-dashed" in text
        assert "px-notice-error" not in text

    def test_unavailable_is_honest(self):
        at = _run_harness(harness_adaptive_recommend={
            "available": False, "state": "unavailable", "reasons": [],
            "qualified_activities": [], "limitations": [],
        })
        _enter_learner(at)
        text = _markdown_text(at)
        assert t("student_adaptive_unavailable", "en") in text
        assert "px-notice-error" not in text

    def test_degraded_gateway_shows_honest_state(self):
        at = _run_harness(harness_gateway_available=False)
        _enter_learner(at)
        text = _markdown_text(at)
        assert t("student_adaptive_unavailable", "en") in text


class TestAdaptivePracticeEvaluation:
    def test_selection_and_evaluation_flow(self):
        at = _run_harness(
            harness_adaptive_recommend=RECOMMENDATION,
            harness_adaptive_select=SELECTION,
            harness_adaptive_evaluate=EVALUATION,
        )
        _enter_learner(at)
        # Choose the activity and run the practice section.
        use = next(b for b in at.button if b.key == "adaptive_use_activity")
        use.click().run()
        assert not at.exception, at.exception
        response = next(t for t in at.text_area if t.key == "adaptive_response")
        response.set_value("Parks help communities. Green space supports health.").run()
        assert not at.exception, at.exception
        submit = next(b for b in at.button if b.key == "adaptive_submit_attempt")
        submit.click().run()
        assert not at.exception, at.exception
        text = _markdown_text(at)
        assert t("student_adaptive_evaluation_section", "en") in text
        assert t("student_practice_completion_completed", "en") in text
        gateway = _gateway(at)
        assert gateway.adaptive_select_calls
        assert gateway.adaptive_evaluate_calls

    def test_evaluate_requires_response(self):
        at = _run_harness(
            harness_adaptive_recommend=RECOMMENDATION,
            harness_adaptive_select=SELECTION,
        )
        _enter_learner(at)
        use = next(b for b in at.button if b.key == "adaptive_use_activity")
        use.click().run()
        response = next(t for t in at.text_area if t.key == "adaptive_response")
        response.set_value("   ").run()
        submit = next(b for b in at.button if b.key == "adaptive_submit_attempt")
        submit.click().run()
        text = _markdown_text(at)
        assert t("student_adaptive_empty_response", "en") in text
        gateway = _gateway(at)
        assert gateway.adaptive_evaluate_calls == []


class TestAdaptiveTutor:
    def test_due_item_requires_consent_before_accept(self):
        at = _run_harness(
            harness_adaptive_recommend=RECOMMENDATION,
            harness_tutor_recommend=TUTOR_DUE,
            harness_tutor_accept=DECISION_ACCEPT,
        )
        _enter_learner(at)
        text = _markdown_text(at)
        assert t("student_adaptive_tutor_section", "en") in text
        assert t("student_adaptive_tutor_due", "en") in text
        # Accept without consent must be blocked (no decision call).
        accept = next(b for b in at.button if b.key == "adaptive_tutor_accept")
        accept.click().run()
        assert not at.exception, at.exception
        gateway = _gateway(at)
        assert gateway.tutor_accept_calls == []
        assert t("student_adaptive_tutor_consent_required", "en") in _markdown_text(at)

    def test_accept_with_consent_executes_bounded_action(self):
        at = _run_harness(
            harness_adaptive_recommend=RECOMMENDATION,
            harness_tutor_recommend=TUTOR_DUE,
            harness_tutor_accept=DECISION_ACCEPT,
        )
        _enter_learner(at)
        consent = next(c for c in at.checkbox if c.key == "adaptive_tutor_consent")
        consent.check().run()
        assert not at.exception, at.exception
        accept = next(b for b in at.button if b.key == "adaptive_tutor_accept")
        accept.click().run()
        assert not at.exception, at.exception
        gateway = _gateway(at)
        assert gateway.tutor_accept_calls
        _, _, consent_payload = gateway.tutor_accept_calls[0]
        assert consent_payload["granted"] is True
        assert consent_payload["scope"] == "proactive_tutor_execution"
        assert consent_payload["consent_version"] == "learner-consent-v0.1.0"
        text = _markdown_text(at)
        assert t("student_adaptive_tutor_accepted", "en") in text

    def test_decline_is_side_effect_safe(self):
        at = _run_harness(
            harness_adaptive_recommend=RECOMMENDATION,
            harness_tutor_recommend=TUTOR_HISTORY,
            harness_tutor_decline=DECISION_DECLINE,
        )
        _enter_learner(at)
        decline = next(b for b in at.button if b.key == "adaptive_tutor_decline")
        decline.click().run()
        assert not at.exception, at.exception
        gateway = _gateway(at)
        assert gateway.tutor_decline_calls
        assert gateway.tutor_accept_calls == []
        text = _markdown_text(at)
        assert t("student_adaptive_tutor_declined", "en") in text

    def test_insufficient_history_tutor_is_honest(self):
        at = _run_harness(
            harness_adaptive_recommend=RECOMMENDATION,
            harness_tutor_recommend=TUTOR_INSUFFICIENT,
        )
        _enter_learner(at)
        text = _markdown_text(at)
        assert t("student_adaptive_tutor_insufficient", "en") in text
        assert "adaptive_tutor_accept" not in _button_keys(at)

    def test_positive_observation_is_bounded_and_non_causal(self):
        at = _run_harness(
            harness_adaptive_recommend=RECOMMENDATION,
            harness_tutor_recommend=TUTOR_POSITIVE,
            harness_tutor_observation=OBSERVATION,
        )
        _enter_learner(at)
        text = _markdown_text(at)
        assert "not proof of learning" in text
        # The frozen page boundary disclaimer is an accepted limitation
        # sentence, not a learner claim; normalize it before checking.
        text = text.replace(t("student_adaptive_boundary", "en"), "")
        for forbidden in ("mastery", "proficient", "learning gain", "cefr"):
            assert forbidden not in text.lower()


class TestMiniWritingHandoff:
    def test_mini_writing_handoff_with_session_task(self):
        at = _run_harness(
            harness_adaptive_recommend=RECOMMENDATION,
            harness_mini_writing=MINI_WRITING,
            wave2_task={"task_id": "WT000001"},
        )
        _enter_learner(at)
        text = _markdown_text(at)
        assert t("student_adaptive_mini_section", "en") in text
        mini = next(t for t in at.text_area if t.key == "adaptive_mini_text")
        mini.set_value("A short continuation of the draft.").run()
        submit = next(b for b in at.button if b.key == "adaptive_mini_submit")
        submit.click().run()
        assert not at.exception, at.exception
        gateway = _gateway(at)
        assert gateway.mini_writing_calls
        learner_id, task_id, text_value = gateway.mini_writing_calls[0]
        assert learner_id == "S02"
        assert task_id == "WT000001"
        assert text_value == "A short continuation of the draft."
        rendered = _markdown_text(at)
        assert t("student_adaptive_mini_result", "en") in rendered

    def test_mini_writing_without_task_is_honest(self):
        at = _run_harness(harness_adaptive_recommend=RECOMMENDATION)
        _enter_learner(at)
        text = _markdown_text(at)
        assert t("student_adaptive_mini_no_task", "en") in text
        gateway = _gateway(at)
        assert gateway.mini_writing_calls == []


class TestAdaptiveNavigation:
    def test_today_navigates_to_journey(self):
        at = _run_harness(harness_adaptive_recommend=RECOMMENDATION)
        _enter_learner(at)
        button = next(b for b in at.button if b.key == "adaptive_open_journey")
        button.click().run()
        assert not at.exception, at.exception
        assert at.session_state["sidebar_page"] == t("learning_journey", "en")

    def test_today_navigates_to_practice(self):
        at = _run_harness(harness_adaptive_recommend=RECOMMENDATION)
        _enter_learner(at)
        button = next(b for b in at.button if b.key == "adaptive_open_practice")
        button.click().run()
        assert not at.exception, at.exception
        assert at.session_state["sidebar_page"] == t("practice", "en")


class TestAdaptiveZeroWrites:
    def test_read_only_render_makes_no_calls(self):
        at = _run_harness(harness_adaptive_recommend=RECOMMENDATION)
        _enter_learner(at)
        gateway = _gateway(at)
        # Read-only render: only recommend (GET-like read) is allowed.
        assert gateway.adaptive_select_calls == []
        assert gateway.adaptive_evaluate_calls == []
        assert gateway.tutor_accept_calls == []
        assert gateway.tutor_decline_calls == []
        assert gateway.mini_writing_calls == []


class TestAdaptiveLocaleParity:
    def test_en_renders_localized(self):
        at = _run_harness(harness_adaptive_recommend=RECOMMENDATION, harness_lang="en")
        _enter_learner(at)
        text = _markdown_text(at)
        assert t("student_adaptive_title", "en") in text

    def test_zh_renders_localized(self):
        at = _run_harness(harness_adaptive_recommend=RECOMMENDATION,
                          harness_lang="zh_CN")
        _enter_learner(at)
        text = _markdown_text(at)
        assert t("student_adaptive_title", "zh_CN") in text
        for raw in ("student_adaptive_",):
            assert raw not in text

    def test_locale_parity_holds(self):
        en = json.loads((ROOT / "locales/en.json").read_text(encoding="utf-8"))
        zh = json.loads((ROOT / "locales/zh_CN.json").read_text(encoding="utf-8"))
        assert set(en) == set(zh)
        for key in (
            "student_adaptive_title", "student_adaptive_recommend_section",
            "student_adaptive_use_activity", "student_adaptive_tutor_accept",
            "student_adaptive_tutor_decline", "student_adaptive_mini_section",
        ):
            assert key in en and key in zh

    def test_no_forbidden_wording(self):
        at = _run_harness(
            harness_adaptive_recommend=RECOMMENDATION,
            harness_adaptive_select=SELECTION,
            harness_adaptive_evaluate=EVALUATION,
            harness_tutor_recommend=TUTOR_POSITIVE,
            harness_tutor_observation=OBSERVATION,
        )
        _enter_learner(at)
        text = _markdown_text(at).lower()
        text = text.replace(t("student_adaptive_boundary", "en").lower(), "")
        for forbidden in ("mastery", "proficient", "cefr", "learning gain",
                          "improved your writing"):
            assert forbidden not in text
