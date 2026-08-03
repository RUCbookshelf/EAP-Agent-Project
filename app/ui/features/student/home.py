"""Student Home feature (v0.9.5-C)."""

from __future__ import annotations

import streamlit as st

from app.ui.api_client import ApiClientError
from app.ui.ports.student import StudentHomeApiPort
from app.ui.components import (
    info_box,
    limitation_notice,
    section_header,
    student_action_block,
    student_context_block,
    student_page_intro,
    student_task_steps,
)
from app.ui.features.student.formatting import _short_timestamp
from app.ui.features.student.navigation import (
    _finish_feedback_cycle,
    _navigate_student_page,
    _navigate_writing_revision,
)
from app.ui.features.student.session import _writing_saved_for_learner
from app.ui.locale import t
from app.ui.student_context import set_selected_learner, student_id_input


def _home_action_contract(state: str) -> tuple[int, str, str, str]:
    """Return workflow step, guidance, target page title, and CTA label keys."""
    return {
        "no_submissions": (0, "student_home_action_submit", "student_writing_title", "student_home_go_writing"),
        "submission_without_analysis": (1, "student_home_action_continue", "student_feedback_title", "student_home_go_feedback"),
        "analysis_without_priority": (0, "student_home_action_submit", "student_writing_title", "student_home_go_writing"),
        "feedback_no_practice_target": (1, "student_home_action_revise", "student_revision_title", "student_home_go_revision"),
        "target_no_attempt": (2, "student_home_action_practice", "practice", "student_home_go_practice"),
        "attempt_no_evaluation": (2, "student_home_action_practice", "practice", "student_home_go_practice"),
        "revision_no_response": (2, "student_home_action_revise", "student_revision_title", "student_home_go_revision"),
        "journey_events": (2, "student_home_action_continue", "student_writing_title", "student_home_go_writing"),
    }.get(state, (0, "student_home_action_continue", "student_writing_title", "student_home_go_writing"))


def _latest_no_priority_submission_id(journey: dict) -> int | None:
    """Latest durable no-priority submission id from the journey state.

    The journey classifier records every submission whose Diagnostic Gate
    selected no automatic priority under the analysis_without_priority
    derived state. Used to decide whether the session's finished-cycle
    acknowledgement still matches the newest no-priority submission.
    """
    for derived in journey.get("derived_states") or []:
        if derived.get("key") == "analysis_without_priority":
            ids = [int(item) for item in (derived.get("submission_ids") or [])]
            if ids:
                return max(ids)
    return None


def render_student_home(api_client: StudentHomeApiPort, lang: str) -> None:
    """Student Home: orient the learner and expose one relevant next action."""
    student_page_intro("student_home_title", "student_home_subtitle", lang)

    student_id = student_id_input(
        "student_id", "home_student", lang, placeholder_key="student_id_placeholder"
    )
    set_selected_learner(student_id)

    workflow = [
        "student_home_step_write",
        "student_home_step_feedback",
        "student_home_step_act",
    ]
    if not student_id.strip():
        student_task_steps(workflow, 0, lang)
        student_action_block(
            "student_home_next_action", "student_home_enter_id", lang, state="blocked"
        )
        limitation_notice("student_home_boundary", lang)
        return

    learner_id = student_id.strip()
    student_context_block([("student_context_learner", learner_id)], lang)
    try:
        with st.spinner(t("journey_loading", lang)):
            journey = api_client.get_journey(learner_id)
            targets = api_client.get_practice_targets(learner_id)
    except ApiClientError as exc:
        render_api_error(exc, lang)
        return

    state = journey.get("state") or "no_submissions"
    step, action_key, target_title_key, button_key = _home_action_contract(state)
    result = st.session_state.get("submission_result")
    unresolved_no_priority = (
        _writing_saved_for_learner(result, learner_id)
        and "NO_SELECTED_PRIORITY" in (result.get("ui_empty_states") or [])
    )
    if not unresolved_no_priority:
        # A finished no-priority cycle (session acknowledgement matching the
        # latest durable no-priority submission) resets the current step to
        # Writing (1 Write) and the next action to a fresh Writing action
        # (v0.9.6-C1 follow-up). A newer unresolved submission never matches.
        reviewed_id = st.session_state.get("no_priority_reviewed")
        latest_no_priority = _latest_no_priority_submission_id(journey)
        if (
            reviewed_id is not None
            and latest_no_priority is not None
            and int(reviewed_id) == latest_no_priority
        ):
            step = 0
            action_key = "student_home_action_continue"
            target_title_key = "student_writing_title"
            button_key = "student_home_go_writing"
    student_task_steps(workflow, step, lang)
    if unresolved_no_priority:
        # An unresolved no-priority result is an explicit decision point
        # (v0.9.6-C1): revise this draft or finish this feedback cycle.
        student_context_block(
            [
                ("student_home_latest_submission", f"#{result.get('submission_id', '?')}"),
                ("student_home_feedback_result", t("student_home_no_priority_selected", lang)),
                ("student_home_next_action", t("student_home_review_choose_desc", lang)),
            ],
            lang,
        )
        st.button(
            t("student_revision_revise", lang),
            type="primary",
            use_container_width=True,
            key="home_revise_action",
            on_click=_navigate_writing_revision,
            args=(int(result.get("submission_id") or 0), lang),
        )
        st.button(
            t("student_feedback_finish_cycle", lang),
            use_container_width=True,
            key="home_finish_action",
            on_click=_finish_feedback_cycle,
            args=(int(result.get("submission_id") or 0), lang),
        )
    else:
        student_action_block("student_home_next_action", action_key, lang)
        st.button(
            t(button_key, lang),
            type="primary",
            use_container_width=True,
            key="home_primary_action",
            on_click=_navigate_student_page,
            args=(target_title_key, lang),
        )

    section_header("student_home_current_task", lang=lang)
    active_targets = [item for item in targets if item.get("status") == "active"]
    if active_targets:
        student_context_block(
            [("student_home_active_target", active_targets[0].get("target_label", ""))], lang
        )
    elif state == "no_submissions":
        info_box("student_home_no_submissions", lang)
    else:
        state_messages = {
            "submission_without_analysis": "journey_empty_no_analysis_title",
            "analysis_without_priority": "journey_empty_no_priority_title",
            "feedback_no_practice_target": "journey_empty_no_target_title",
            "target_no_attempt": "journey_empty_no_attempt_title",
            "attempt_no_evaluation": "journey_empty_no_evaluation_title",
            "revision_no_response": "journey_empty_no_revision_title",
        }
        info_box(state_messages.get(state, "student_home_no_events"), lang)

    events = journey.get("events") or []
    if events:
        latest = events[-1]
        section_header("student_home_latest_status", lang=lang)
        student_context_block(
            [
                ("student_home_latest_activity", t(latest.get("title_key", ""), lang)),
                ("student_home_activity_time", _short_timestamp(latest.get("occurred_at", ""))),
            ],
            lang,
        )

    limitation_notice("student_home_boundary", lang)
