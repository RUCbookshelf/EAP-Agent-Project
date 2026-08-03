"""Shared Student navigation helper (v0.9.5-C).

Ownership: `_navigate_student_page` is used by all six Student features and
lives here once. Behavior is unchanged from the pre-extraction module.
"""

from __future__ import annotations

import streamlit as st

from app.ui.locale import t


def _navigate_student_page(title_key: str, lang: str) -> None:
    """Move to an existing localized Student sidebar page on the next rerun."""
    st.session_state["sidebar_page"] = t(title_key, lang)


def _navigate_writing_revision(source_submission_id: int, lang: str) -> None:
    """Enter the existing Writing revision mode for a specific source draft.

    Used by the no-priority workflow 'Revise This Draft' choice (v0.9.6-C1):
    the current submission is preserved as the revision source and no
    automatic priority is fabricated. The Writing page consumes the preset
    on its next rerun.
    """
    st.session_state["writing_task_relationship"] = t("task_revision_within", lang)
    st.session_state["writing_revision_source_preset"] = int(source_submission_id)
    # The revise decision supersedes the saved-submission panel: the user is
    # starting a new revision action, so the stale saved panel must not block
    # the revision form.
    st.session_state.pop("submission_result", None)
    st.session_state["sidebar_page"] = t("student_writing_title", lang)


def _finish_feedback_cycle(lang: str) -> None:
    """Acknowledge a no-priority feedback cycle and return to a fresh Writing state.

    v0.9.6-C1: clears the stale Writing-submitted success state (session-scoped),
    records the acknowledgement for the current session, and navigates to a
    fresh Writing form. Never deletes submissions, never creates revisions or
    practice targets, and never submits or generates anything.
    """
    st.session_state["no_priority_reviewed"] = True
    st.session_state["cycle_finished_notice"] = True
    st.session_state.pop("submission_result", None)
    st.session_state["sidebar_page"] = t("student_writing_title", lang)
