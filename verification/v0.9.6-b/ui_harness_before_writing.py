"""v0.9.6-B pre-fix UI harness: writing page with a scripted client.

AppTest executes this file; session state persists across runs. The fake
client counts POSTs and raises one REQUEST_TIMEOUT on the first submit.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.ui.api_client import ApiClientError, ErrorCategory
from app.ui.features.student.writing import render_writing_page


class FakeClient:
    def __init__(self):
        self.post_count = 0
        self.timeout_next = True

    def get_student_revision_candidates(self, student_id):
        return {"candidates": []}

    def submit(self, submission):
        self.post_count += 1
        if self.timeout_next:
            self.timeout_next = False
            raise ApiClientError(ErrorCategory.REQUEST_TIMEOUT, "read timed out", operation="submit")
        return {
            "submission_id": 88,
            "analysis": {},
            "diagnosis": {},
            "feedback_result": {},
            "history": {},
            "revision_snapshot": {},
            "diagnostic_calibration": {},
            "feedback_provider_status": {},
            "longitudinal_assessment": None,
            "revision_group_summary": {},
            "within_task_revision_trajectory": {},
            "ui_empty_states": [],
        }


if "fake_client" not in st.session_state:
    st.session_state["fake_client"] = FakeClient()
if "writing_student" not in st.session_state:
    st.session_state["writing_student"] = "S96W"
render_writing_page(st.session_state["fake_client"], "en")