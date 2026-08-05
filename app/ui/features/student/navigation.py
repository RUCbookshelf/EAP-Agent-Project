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


def _finish_feedback_cycle(submission_id: int, lang: str) -> None:
    """Acknowledge a no-priority feedback cycle and return to a fresh Writing state.

    v0.9.6-C1: clears the stale Writing-submitted success state (session-scoped),
    records the acknowledgement for the exact finished submission for the
    current session, and navigates to a fresh Writing form. Never deletes
    submissions, never creates revisions or practice targets, and never
    submits or generates anything.
    """
    st.session_state["no_priority_reviewed"] = int(submission_id)
    st.session_state["cycle_finished_notice"] = True
    st.session_state.pop("submission_result", None)
    st.session_state["sidebar_page"] = t("student_writing_title", lang)


def _navigate_priority_revision(source_submission_id: int, lang: str) -> None:
    """Enter the Revision page with a specific source draft as the priority-guided task.

    v0.9.7-A: carries only the source reference in session state; the active
    priority itself is always re-read from the source's persisted structured
    feedback by the Revision page. The in-session feedback result is preserved
    so Feedback can still render when the student returns. The preset is
    validated against the current learner's candidates on the Revision page.
    """
    st.session_state["revision_source_preset"] = int(source_submission_id)
    st.session_state.pop("revision_priority_selection", None)
    st.session_state["sidebar_page"] = t("student_revision_title", lang)


def _navigate_priority_practice(source_submission_id: int, priority_index: int, lang: str) -> None:
    """Transfer an explicit Priority-to-Practice intent (v0.9.7-B WU4).

    Carries only persisted-reference components in session state: the source
    submission id and the zero-based priority index. The Practice page
    revalidates them against persisted records through the server before any
    target creation or reuse; no priority content is copied into session
    state.
    """
    st.session_state["practice_source_submission_id"] = int(source_submission_id)
    st.session_state["practice_priority_index"] = int(priority_index)
    st.session_state.pop("practice_target_preset", None)
    st.session_state.pop("practice_intent_invalid", None)
    st.session_state["sidebar_page"] = t("practice", lang)


def _navigate_journey_revision(source_submission_id: int, lang: str) -> None:
    """Open the Revision page for one persisted source (v0.9.7-C WU2).

    Journey navigation carries only the stable submission reference; the
    Revision page re-reads the source from persistence and validates the
    reference against the current learner's candidates. A stale or
    cross-learner reference renders an honest note instead of silently
    opening another record. Navigation never writes and never creates a
    revision.
    """
    st.session_state["revision_source_preset"] = int(source_submission_id)
    st.session_state["sidebar_page"] = t("student_revision_title", lang)


def _navigate_journey_practice(practice_target_id: str, lang: str) -> None:
    """Open an existing learner-owned Practice target (v0.9.7-C WU2).

    Journey navigation carries only the stable target reference; the
    Practice page validates it against the learner's persisted targets
    (active or completed) and renders the saved state. A stale or
    cross-learner reference renders an honest note. Navigation never
    creates a target, exercise, attempt, or evaluation.
    """
    st.session_state["practice_target_preset"] = str(practice_target_id)
    st.session_state.pop("practice_source_submission_id", None)
    st.session_state.pop("practice_priority_index", None)
    st.session_state.pop("practice_intent_invalid", None)
    st.session_state["sidebar_page"] = t("practice", lang)


def _finish_revision_cycle(lang: str) -> None:
    """Acknowledge a finished priority-guided revision cycle and return to Home.

    v0.9.7-A: clears the session-scoped saved panel and revision presets so a
    later re-entry is never mistaken for an unsubmitted revision. Never
    deletes submissions, never resubmits, and never generates anything; Home
    derives the next step from the durable journey state.
    """
    st.session_state["revision_cycle_finished"] = True
    st.session_state.pop("submission_result", None)
    st.session_state.pop("revision_source_preset", None)
    st.session_state.pop("revision_priority_selection", None)
    st.session_state["sidebar_page"] = t("student_home_title", lang)
