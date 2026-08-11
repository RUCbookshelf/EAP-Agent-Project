"""Wave-2 AppTest harness: renders the studio/history renderers with a
scripted gateway driven by session-state keys (mirrors harness_v097a_student.py).

Session-state controls:
- ``harness_page``      "studio" (default) | "history"
- ``harness_mode``      "guided" (default) | "standard"
- ``harness_scenario``  "new_learner" (default) | "returning_learner"
- ``harness_lang``      "en" (default)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from app.ui.wave2.gateway import Wave2Gateway
from app.ui.wave2.history import render_wave2_history_page
from app.ui.wave2.journey import render_wave2_studio_page
from app.ui.wave2.mock import MockWave2Backend, MockWave2Client

PROMPT = "Should cities add more parks?"

PRIORITIES = [
    {
        "category": "lexical_repetition",
        "evidence_quote": "Parks support public health.",
        "explanation": "The word 'parks' is repeated closely in the draft.",
        "revision_guidance": "Replace one repetition with a synonym.",
    }
]


class HarnessLegacyClient:
    """Scripted stand-in for the existing WritingFeedbackApiClient."""

    def __init__(self):
        self.submits = []
        self.linked_revisions = []

    def submit(self, payload):
        self.submits.append(payload)
        return {
            "submission_id": 100,
            "student_id": payload["student_id"],
            "writing_prompt": payload["writing_prompt"],
            "genre": payload["genre"],
            "draft_stage": payload["draft_stage"],
            "essay_text": payload["essay_text"],
            "feedback_result": {
                "feedback": {
                    "priority_feedback": PRIORITIES,
                    "positive_finding": {
                        "explanation": "The draft answers the prompt directly.",
                        "evidence_quote": "",
                    },
                    "uncertainty_note": "Prototype feedback.",
                }
            },
            "history": {"comparability_status": "insufficient_history"},
        }

    def submit_linked_revision(self, payload):
        self.linked_revisions.append(payload)
        result = self.submit(payload)
        result["revision_of_submission_id"] = payload["revision_of_submission_id"]
        return result

    def get_journey(self, student_id):
        return {"state": "no_submissions", "events": []}

    def get_student_revision_candidates(self, student_id):
        return {"candidates": []}


page = st.session_state.get("harness_page", "studio")
mode = st.session_state.get("harness_mode", "guided")
scenario = st.session_state.get("harness_scenario", "new_learner")
lang = st.session_state.get("harness_lang", "en")

# The mock backend must survive reruns (the journey creates tasks and
# submits versions across steps), so it lives in session state per
# mode/scenario instead of being rebuilt on every script run.
if mode == "standard":
    legacy_key = f"harness_legacy_client_{mode}"
    if legacy_key not in st.session_state:
        st.session_state[legacy_key] = HarnessLegacyClient()
    gateway = Wave2Gateway(wave2_client=None, legacy_client=st.session_state[legacy_key], mode="legacy")
else:
    backend_key = f"harness_backend_{mode}_{scenario}"
    if backend_key not in st.session_state:
        st.session_state[backend_key] = MockWave2Backend(scenario=scenario)
    gateway = Wave2Gateway(
        wave2_client=MockWave2Client(st.session_state[backend_key], available=True),
        legacy_client=None,
        mode="wave2",
    )

if page == "history":
    render_wave2_history_page(gateway, lang)
else:
    render_wave2_studio_page(gateway, lang)