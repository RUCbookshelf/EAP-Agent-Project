"""v0.9.6-A pre-fix UI harness: linked-revision page with a scripted client.

AppTest executes this file; session state persists across runs. The fake
client counts POSTs and raises one REQUEST_TIMEOUT on the first submit.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.ui.api_client import ApiClientError, ErrorCategory
from app.ui.features.student.revision import render_revision_page

CANDIDATE = {
    "essay_id": 1,
    "student_id": "S96B",
    "writing_prompt": "Should cities add more parks?",
    "genre": "argumentative essay",
    "draft_stage": "first draft",
    "timed": False,
    "time_limit_minutes": None,
    "tool_use": "none",
    "submitted_at": "2026-08-03T08:00:00+00:00",
    "revision_of_submission_id": None,
    "revision_group_id": None,
    "revision_sequence": None,
    "revision_stage": None,
    "original_draft_stage": None,
    "writing_started_at": None,
    "writing_submitted_at": None,
    "active_writing_duration_seconds": None,
    "timing_source": "unknown",
    "timing_quality": "unavailable",
    "unexplained_interruption": False,
}


class FakeClient:
    def __init__(self):
        self.post_count = 0
        self.timeout_next = True

    def get_practice_targets(self, student_id):
        return []

    def get_student_revision_candidates(self, student_id):
        return {"candidates": [dict(CANDIDATE)]}

    def get_submission(self, submission_id):
        row = dict(CANDIDATE)
        row["essay_text"] = "Parks support public health. Cities should protect accessible parks."
        return row

    def submit(self, submission):
        self.post_count += 1
        if self.timeout_next:
            self.timeout_next = False
            raise ApiClientError(ErrorCategory.REQUEST_TIMEOUT, "read timed out", operation="submit")
        return {
            "submission_id": 99, "analysis": {}, "diagnosis": {}, "feedback_result": {},
            "history": {}, "revision_snapshot": {}, "diagnostic_calibration": {},
            "feedback_provider_status": {}, "longitudinal_assessment": None,
            "revision_group_summary": {}, "within_task_revision_trajectory": {}, "ui_empty_states": [],
        }


if "fake_client" not in st.session_state:
    st.session_state["fake_client"] = FakeClient()
client = st.session_state["fake_client"]
if "student_id" not in st.session_state:
    st.session_state["student_id"] = "S96B"
render_revision_page(client, "en")