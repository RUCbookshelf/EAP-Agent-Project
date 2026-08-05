"""v0.9.7-A AppTest harness: priority-guided student cycle with scripted clients.

Mirrors tests/harness_v096c1_student.py: reads the localized sidebar_page
label and renders the matching student page; the scripted client is configured
through session-state keys set by the test driver before the first run.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from app.ui.features.student.feedback import render_feedback_page
from app.ui.features.student.home import render_student_home
from app.ui.features.student.practice import render_practice_page
from app.ui.features.student.revision import render_revision_page
from app.ui.features.student.writing import render_writing_page
from app.ui.locale import t

RENDERERS = {
    "student_home_title": render_student_home,
    "student_writing_title": render_writing_page,
    "student_feedback_title": render_feedback_page,
    "student_revision_title": render_revision_page,
    "practice": render_practice_page,
}

PROMPT = "Should cities add more parks?"

PRIORITIES = [
    {
        "diagnosis_id": "D001",
        "category": "lexical_repetition",
        "evidence_quote": "Parks support public health.",
        "explanation": "The phrase 'public health' is repeated closely in the draft.",
        "revision_guidance": "Replace one repetition with a synonym.",
    },
    {
        "diagnosis_id": "D002",
        "category": "connective_use",
        "evidence_quote": "Cities should protect accessible parks.",
        "explanation": "The draft lacks a linking phrase between the two ideas.",
        "revision_guidance": "Add a connective that links the two ideas.",
    },
]


class FakeClient:
    """Scripted Student API client driven by session-state harness keys."""

    def __init__(self):
        self.post_count = 0
        self.revision_post_count = 0
        self.target_create_count = 0
        self.attempt_post_count = 0
        self.journey = dict(
            st.session_state.get("harness_journey")
            or {"state": "feedback_no_practice_target", "events": []}
        )
        self.targets = list(st.session_state.get("harness_targets") or [])
        self.exercises = list(st.session_state.get("harness_exercises") or [])
        self.attempts = list(st.session_state.get("harness_attempts") or [])
        self.candidates = list(st.session_state.get("harness_candidates") or [])
        self.source_bundle = dict(st.session_state.get("harness_source_bundle") or {})
        self.submit_response = dict(st.session_state.get("harness_submit_response") or {})
        self.fail_submit = bool(st.session_state.get("harness_fail_submit", False))

    def get_journey(self, student_id):
        return dict(self.journey)

    def get_practice_targets(self, student_id):
        return list(self.targets)

    def get_student_revision_candidates(self, student_id):
        return {"candidates": list(self.candidates)}

    def get_submission(self, submission_id):
        if self.source_bundle:
            return dict(self.source_bundle)
        return {
            "essay_id": submission_id,
            "student_id": "S02",
            "writing_prompt": PROMPT,
            "genre": "argumentative essay",
            "draft_stage": "final draft",
            "essay_text": "Parks support public health. Cities should protect accessible parks.",
            "feedback": {"priority_feedback": PRIORITIES},
        }

    def submit(self, submission):
        self.post_count += 1
        return self._response()

    def submit_linked_revision(self, submission):
        self.revision_post_count += 1
        if self.fail_submit:
            raise RuntimeError("probe submit failure")
        return self._response()

    def _response(self):
        if self.submit_response:
            return dict(self.submit_response)
        return {
            "submission_id": 99,
            "within_task_revision_trajectory": {
                "previous_selected_priorities": PRIORITIES,
            },
        }

    def create_exercise(self, practice_target_id, payload):
        return {"status": "practice_not_available"}

    def create_practice_target(self, payload):
        self.target_create_count += 1
        response = st.session_state.get("harness_target_create_response")
        if response is not None:
            return dict(response)
        return {"status": "practice_not_available", "reason": "harness default"}

    def get_practice_target_context(self, student_id, practice_target_id):
        response = st.session_state.get("harness_target_context")
        if response is not None:
            return dict(response)
        return {
            "context_status": "legacy",
            "practice_target_id": practice_target_id,
            "student_id": student_id,
            "source_submission_id": 0,
            "source_priority_id": None,
            "target_code": "lexical_repetition_local",
            "target_label": "Label",
            "status": "active",
            "priority_context": None,
            "source_writing_text": "",
        }

    def get_exercise_attempts(self, exercise_id):
        return list(self.attempts)

    def get_exercise_instances(self, practice_target_id):
        return list(self.exercises)

    def submit_exercise_attempt(self, exercise_id, payload):
        self.attempt_post_count += 1
        response = st.session_state.get("harness_attempt_response")
        if response is not None:
            attempt = dict(response)
        else:
            attempt = {
            "attempt_id": "EA000001",
            "exercise_id": exercise_id,
            "student_id": payload.get("student_id", ""),
            "attempt_number": 1,
            "response_text": payload.get("response_text", ""),
            "status": "submitted",
            "evaluation": None,
            }
        self.attempts.append(attempt)
        return attempt


if "fake_client" not in st.session_state:
    st.session_state["fake_client"] = FakeClient()

lang = st.session_state.get("harness_lang", "en")
current = st.session_state.get("sidebar_page") or t("student_feedback_title", lang)
renderer = None
for key, render in RENDERERS.items():
    if t(key, lang) == current:
        renderer = render
        break
if renderer is None:
    renderer = render_feedback_page
renderer(st.session_state["fake_client"], lang)
