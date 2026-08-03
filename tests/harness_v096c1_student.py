"""v0.9.6-C1 AppTest harness: student pages with scripted clients and session navigation.

Mirrors the application's student role routing: the harness reads the
localized sidebar_page label and renders the matching student page. The
scripted client is configured through session-state keys set by the test
driver before the first run.
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


class FakeClient:
    def __init__(self):
        self.post_count = 0
        self.revision_post_count = 0
        self.journey = dict(st.session_state.get("harness_journey") or {"state": "feedback_no_practice_target", "events": []})
        self.targets = list(st.session_state.get("harness_targets") or [])
        self.candidates = list(st.session_state.get("harness_candidates") or [])
        self.source_bundle = dict(st.session_state.get("harness_source_bundle") or {})

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
            "feedback": {"priority_feedback": []},
        }

    def submit(self, submission):
        self.post_count += 1
        return {
            "submission_id": 99,
            "analysis": {},
            "diagnosis": {"strengths": []},
            "feedback_result": {"feedback": {"priority_feedback": [], "positive_finding": {}}},
            "history": {},
            "revision_snapshot": {},
            "diagnostic_calibration": {},
            "feedback_provider_status": {},
            "longitudinal_assessment": None,
            "revision_group_summary": {},
            "within_task_revision_trajectory": {},
            "ui_empty_states": [],
        }

    def submit_linked_revision(self, submission):
        self.revision_post_count += 1
        return self.submit(submission)

    def get_exercise_instances(self, practice_target_id):
        return []

    def get_exercise_attempts(self, exercise_id):
        return []


if "fake_client" not in st.session_state:
    st.session_state["fake_client"] = FakeClient()

lang = "en"
current = st.session_state.get("sidebar_page") or t("student_feedback_title", lang)
renderer = None
for key, render in RENDERERS.items():
    if t(key, lang) == current:
        renderer = render
        break
if renderer is None:
    renderer = render_feedback_page
renderer(st.session_state["fake_client"], lang)