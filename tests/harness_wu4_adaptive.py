"""Wave-3 WU4 AppTest harness: Today/adaptive learning page.

Renders ``render_adaptive_learning_page`` with a scripted gateway driven by
session-state keys (mirrors harness_v097a_student.py). Session controls:

- ``harness_page``          "adaptive" (default) | "home" | "journey" | "practice"
- ``harness_lang``          "en" (default) | "zh_CN"
- ``harness_learner``       learner id value (default "S02")
- ``harness_adaptive_*``    scripted WU3-shaped gateway payloads
- ``harness_gateway_available``  False simulates the Wave-2 namespace being
  unavailable so the gateway degrades honestly.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from app.ui.features.student.adaptive import render_adaptive_learning_page
from app.ui.features.student.home import render_student_home
from app.ui.features.student.journey import render_learning_journey_page
from app.ui.features.student.practice import render_practice_page
from app.ui.wave2.gateway import (
    _build_adaptive_evaluation_view,
    _build_adaptive_recommendation_view,
    _build_adaptive_selection_view,
    _build_mini_writing_view,
    _build_tutor_decision_view,
    _build_tutor_observation_view,
    _build_tutor_recommendation_view,
)


class HarnessAdaptiveGateway:
    """Scripted Wave2Gateway stand-in driven by session-state harness keys."""

    def __init__(self) -> None:
        self.adaptive_recommend_calls: list[str] = []
        self.adaptive_select_calls: list[tuple[str, str, str]] = []
        self.adaptive_evaluate_calls: list[tuple[str, str, str]] = []
        self.tutor_recommend_calls: list[str] = []
        self.tutor_accept_calls: list[tuple[str, str, dict]] = []
        self.tutor_decline_calls: list[tuple[str, str]] = []
        self.tutor_observation_calls: list[tuple[str, str]] = []
        self.mini_writing_calls: list[tuple[str, str, str]] = []
        self._available = bool(st.session_state.get("harness_gateway_available", True))

    def available(self) -> bool:
        return self._available

    def mode(self) -> str:
        return "guided" if self._available else "standard"

    # -- WU3 adaptive practice ------------------------------------------------

    def adaptive_recommend(self, learner_id: str) -> dict:
        self.adaptive_recommend_calls.append(learner_id)
        if not self._available:
            return {"available": False, "state": "unavailable"}
        payload = dict(st.session_state.get(
            "harness_adaptive_recommend",
            {"state": "unavailable", "reasons": [],
             "qualified_activities": [], "limitations": []},
        ))
        return _build_adaptive_recommendation_view(payload)

    def adaptive_select(self, learner_id, recommendation_id, activity_id) -> dict:
        self.adaptive_select_calls.append((learner_id, recommendation_id, activity_id))
        if not self._available:
            return {"available": False}
        payload = dict(st.session_state.get(
            "harness_adaptive_select",
            {"selection_id": "AS-1", "recommendation_id": recommendation_id,
             "activity": {}, "choice_kind": "explicit", "limitations": []},
        ))
        return _build_adaptive_selection_view(payload)

    def adaptive_evaluate(self, learner_id, activity_id, response_text) -> dict:
        self.adaptive_evaluate_calls.append((learner_id, activity_id, response_text))
        if not self._available:
            return {"available": False}
        payload = dict(st.session_state.get(
            "harness_adaptive_evaluate",
            {"completion_status": "completed",
             "target_action_status": "candidate_detected",
             "evidence": ["The targeted feature is reduced in the response."],
             "evaluation_method": "rule_based",
             "limitations": ["Observable evidence is task-specific; descriptive only."]},
        ))
        return _build_adaptive_evaluation_view(payload)

    # -- WU3 tutor ------------------------------------------------------------

    def tutor_recommend(self, learner_id: str) -> dict:
        self.tutor_recommend_calls.append(learner_id)
        if not self._available:
            return {"available": False, "state": "unavailable"}
        payload = dict(st.session_state.get(
            "harness_tutor_recommend",
            {"state": "insufficient_history", "suggestion": "",
             "categories": [], "positive_observations": [], "limitations": []},
        ))
        return _build_tutor_recommendation_view(payload)

    def tutor_accept(self, learner_id, recommendation_id, consent) -> dict:
        self.tutor_accept_calls.append((learner_id, recommendation_id, consent))
        if not self._available:
            return {"available": False}
        payload = dict(st.session_state.get(
            "harness_tutor_accept",
            {"decision": "accept", "consent_applied": True,
             "executed": True, "action": "presented the suggestion after explicit consent",
             "limitations": []},
        ))
        return _build_tutor_decision_view(payload)

    def tutor_decline(self, learner_id, recommendation_id) -> dict:
        self.tutor_decline_calls.append((learner_id, recommendation_id))
        if not self._available:
            return {"available": False}
        payload = dict(st.session_state.get(
            "harness_tutor_decline",
            {"decision": "decline", "consent_applied": False,
             "executed": False, "action": None, "limitations": []},
        ))
        return _build_tutor_decision_view(payload)

    def tutor_observation(self, learner_id, category) -> dict:
        self.tutor_observation_calls.append((learner_id, category))
        if not self._available:
            return {"available": False}
        payload = dict(st.session_state.get(
            "harness_tutor_observation",
            {"observation": None},
        ))
        return _build_tutor_observation_view(payload)

    # -- WU3 mini-writing -----------------------------------------------------

    def mini_writing(self, learner_id, task_id, text) -> dict:
        self.mini_writing_calls.append((learner_id, task_id, text))
        if not self._available:
            return {"available": False}
        payload = dict(st.session_state.get(
            "harness_mini_writing",
            {"submission_id": 2001, "word_count": 12,
             "bounded": True, "limitations": []},
        ))
        return _build_mini_writing_view(payload)


RENDERERS = {
    "adaptive": render_adaptive_learning_page,
    "student_home_title": render_student_home,
    "learning_journey": render_learning_journey_page,
    "practice": render_practice_page,
}


if "wu4_adaptive_gateway" not in st.session_state:
    st.session_state["wu4_adaptive_gateway"] = HarnessAdaptiveGateway()

lang = st.session_state.get("harness_lang", "en")
page = st.session_state.get("harness_page", "adaptive")
learner = st.session_state.get("harness_learner", "S02")

if page == "adaptive":
    renderer = render_adaptive_learning_page
elif page == "student_home_title":
    renderer = render_student_home
elif page == "learning_journey":
    renderer = render_learning_journey_page
elif page == "practice":
    renderer = render_practice_page
else:
    renderer = render_adaptive_learning_page

renderer(st.session_state["wu4_adaptive_gateway"], lang)
