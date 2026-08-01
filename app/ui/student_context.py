"""Shared Student learner context (v0.9.3-C).

Normalizes the Student ID (trim surrounding whitespace, preserve case, reject
blank) and keeps the selected learner consistent across Student pages.
Switching learners clears learner-scoped session state so no stale data from
the previous learner is shown. No learner is auto-created and there is no
silent fallback to another learner.
"""

from __future__ import annotations

import streamlit as st

from app.ui.locale import t

SELECTED_LEARNER_KEY = "selected_student_id"

# Session-state keys that hold learner-scoped content and must never leak
# across learners.
LEARNER_SCOPED_KEYS = (
    "practice_targets_v2",
    "current_exercise_v2",
    "exercise_attempts_v2",
    "submission_result",
    "learner_model_audit_v2",
    "practice_targets",
    "home_journey",
)


def normalize_student_id(raw: str) -> str:
    """Trim surrounding whitespace; preserve case; no auto-creation."""
    return (raw or "").strip()


def _clear_learner_scoped_state() -> None:
    for key in LEARNER_SCOPED_KEYS:
        st.session_state.pop(key, None)


def selected_learner() -> str:
    return str(st.session_state.get(SELECTED_LEARNER_KEY, "")).strip()


def set_selected_learner(value: str) -> str:
    normalized = normalize_student_id(value)
    if normalized and normalized != selected_learner():
        st.session_state[SELECTED_LEARNER_KEY] = normalized
        _clear_learner_scoped_state()
    return normalized


def student_id_input(label_key: str, widget_key: str, lang: str, *, placeholder_key: str | None = None) -> str:
    """Render the shared Student ID input and keep the learner context in sync."""
    placeholder = t(placeholder_key, lang) if placeholder_key else None
    value = st.text_input(
        t(label_key, lang), key=widget_key, placeholder=placeholder,
    )
    set_selected_learner(value)
    return value
