"""Shared student essay-submission reliability mechanics (v0.9.6-B).

Pending-state guard, outcome storage/consumption, and outcome message
rendering shared by the Writing page (first drafts and writing-page
revisions) and the Revision page (linked revisions). Mode-specific
reconciliation stays in each feature module; this module contains
reliability state/logic only and introduces no backend dependency.
"""
from __future__ import annotations

import streamlit as st

from app.ui.components import info_box, success_box, warning_box

# Session-state keys are per page so the two pages can never collide.
_PENDING_KEY = "{}_submit_pending"
_OUTCOME_KEY = "{}_submit_outcome"

# Outcome message keys per submission mode.
_OUTCOME_MESSAGES = {
    "FIRST_DRAFT": {
        "CONFIRMED_SUCCESS": "student_writing_timeout_confirmed_success",
        "STILL_PROCESSING": "student_writing_timeout_still_processing",
        "UNCONFIRMED": "student_writing_timeout_unconfirmed",
        "PENDING": "student_writing_submit_pending",
    },
    "LINKED_REVISION": {
        "CONFIRMED_SUCCESS": "student_revision_timeout_confirmed_success",
        "STILL_PROCESSING": "student_revision_timeout_still_processing",
        "UNCONFIRMED": "student_revision_timeout_unconfirmed",
        "PENDING": "student_revision_submit_pending",
    },
    "PRACTICE_ATTEMPT": {
        "CONFIRMED_SUCCESS": "student_practice_submit_pending",
        "STILL_PROCESSING": "student_practice_submit_pending",
        "UNCONFIRMED": "student_practice_submit_pending",
        "PENDING": "student_practice_submit_pending",
    },
}


def enter_pending(page: str) -> None:
    """Mark a long-running essay submission as in flight (page: writing|revision)."""
    st.session_state[_PENDING_KEY.format(page)] = True


def release_pending(page: str) -> None:
    """Clear the in-flight marker and any pending outcome after a terminal state."""
    st.session_state.pop(_PENDING_KEY.format(page), None)
    st.session_state.pop(_OUTCOME_KEY.format(page), None)


def is_pending(page: str) -> bool:
    """True while a submit is in flight or its terminal outcome awaits display."""
    return bool(st.session_state.get(_PENDING_KEY.format(page)))


def store_outcome(page: str, state: str) -> None:
    """Store a terminal outcome for display and queued-click consumption."""
    st.session_state[_OUTCOME_KEY.format(page)] = state


def render_outcome(mode: str, state: str, lang: str) -> None:
    """Render an accurate post-timeout outcome without a blind retry action."""
    messages = _OUTCOME_MESSAGES[mode]
    message = messages.get(state, messages["UNCONFIRMED"])
    if state == "CONFIRMED_SUCCESS":
        success_box(message, lang)
    elif state == "STILL_PROCESSING":
        warning_box(message, lang)
    else:
        info_box(message, lang)


def consume_pending(page: str, mode: str, lang: str) -> bool:
    """Consume a queued click while a submit is in flight or its outcome is
    pending display. Returns True when consumed (no second POST is issued).
    """
    if not is_pending(page):
        return False
    outcome = st.session_state.pop(_OUTCOME_KEY.format(page), None)
    render_outcome(mode, outcome or "PENDING", lang)
    st.session_state.pop(_PENDING_KEY.format(page), None)
    return True
