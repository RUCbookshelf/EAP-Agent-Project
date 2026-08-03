"""AppTest harness for v0.9.6-B writing-page submit flows.

Executed by AppTest; session state persists across runs. The fake client is
configured through session-state keys set by the test driver before the first
run: harness_behavior (success|timeout|error), harness_candidates_after,
harness_bundle_after.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from app.ui.api_client import ApiClientError, ErrorCategory
from app.ui.features.student.writing import render_writing_page


class FakeClient:
    def __init__(self):
        self.post_count = 0
        self.behavior = st.session_state.get("harness_behavior", "success")
        self.candidates_after = st.session_state.get("harness_candidates_after", None)
        self.bundle_after = st.session_state.get("harness_bundle_after", None)
        self._timed_out = False

    def get_student_revision_candidates(self, student_id):
        if self._timed_out and self.candidates_after is not None:
            return {"candidates": self.candidates_after}
        return {"candidates": []}

    def get_submission(self, submission_id):
        if self.bundle_after is not None:
            return dict(self.bundle_after)
        return {
            "essay_id": submission_id,
            "student_id": "S96D",
            "essay_text": "Parks support public health. Cities should protect accessible parks.",
            "feedback": {},
            "success_status": "success",
        }

    def submit(self, submission):
        self.post_count += 1
        if self.behavior == "timeout":
            self._timed_out = True
            raise ApiClientError(ErrorCategory.REQUEST_TIMEOUT, "read timed out", operation="submit")
        if self.behavior == "error":
            raise ApiClientError(
                ErrorCategory.BACKEND_PROCESSING_ERROR, "processing error", operation="submit"
            )
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
    st.session_state["writing_student"] = "S96D"
render_writing_page(st.session_state["fake_client"], "en")