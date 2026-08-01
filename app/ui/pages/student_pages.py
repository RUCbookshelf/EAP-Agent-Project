"""Student View pages for the writing-feedback-mvp Pixel Art interface.

All pages use progressive disclosure: students see only what they need
to understand feedback and take action. Internal IDs, analyzer versions,
and raw metrics are hidden.

Pixel Art v0.9.2: square corners, hard shadows, solid colors, monospace.
"""

from __future__ import annotations

import streamlit as st

from app.ui.api_client import ApiClientError, WritingFeedbackApiClient
from app.ui.components import (
    render_api_error,
    card_group_header,
    empty_state,
    error_box,
    evidence_quote,
    feedback_priority_card,
    field_error,
    info_box,
    limitation_notice,
    loading_box,
    page_header,
    section_header,
    success_box,
    student_action_block,
    student_context_block,
    student_page_intro,
    student_task_steps,
    technical_caption,
    timeline_event,
    validate_writing_form,
    warning_box,
)
from app.ui.locale import t


def _navigate_student_page(title_key: str, lang: str) -> None:
    """Move to an existing localized Student sidebar page on the next rerun."""
    st.session_state["sidebar_page"] = t(title_key, lang)


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


def render_student_home(api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Student Home: orient the learner and expose one relevant next action."""
    student_page_intro("student_home_title", "student_home_subtitle", lang)

    from app.ui.student_context import set_selected_learner, student_id_input

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
    student_task_steps(workflow, step, lang)
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


# ---------------------------------------------------------------------------
# Writing page
# ---------------------------------------------------------------------------

def _writing_saved_for_learner(result: dict | None, student_id: str) -> bool:
    """A saved UI result locks only the learner who created that submission."""
    if not result or not student_id.strip():
        return False
    return result.get("ui_submission", {}).get("student_id") == student_id.strip()


def render_writing_page(api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Student Writing page: one required drafting task and one submit action."""
    student_page_intro("student_writing_title", "student_writing_subtitle", lang)

    from app.ui.student_context import set_selected_learner, student_id_input

    student_id = student_id_input(
        "student_id", "writing_student", lang, placeholder_key="student_id_placeholder"
    )
    set_selected_learner(student_id)
    learner_id = student_id.strip()

    validation_state = st.session_state.get("writing_validation_state") or {}
    validation_errors = set(
        validation_state.get("errors", [])
        if validation_state.get("student_id", "") == learner_id
        else []
    )
    if "student_writing_need_id" in validation_errors:
        field_error("student_writing_need_id", lang)

    saved = st.session_state.get("submission_result")
    if _writing_saved_for_learner(saved, learner_id):
        student_context_block(
            [
                ("student_context_learner", learner_id),
                ("writing_prompt", saved.get("ui_submission", {}).get("writing_prompt", "")),
            ],
            lang,
        )
        success_box("student_writing_saved_title", lang)
        student_action_block(
            "student_writing_saved_title", "student_writing_saved_desc", lang, state="complete"
        )
        technical_caption(
            f"{t('student_writing_submission_reference', lang)}: #{saved.get('submission_id', '?')}"
        )
        st.button(
            t("student_writing_review_feedback", lang),
            type="primary",
            use_container_width=True,
            key="writing_review_feedback",
            on_click=_navigate_student_page,
            args=("student_feedback_title", lang),
        )
        return

    section_header("student_writing_task_section", "student_writing_task_section_help", lang)
    st.radio(
        t("task_relationship", lang),
        [t("task_new_independent", lang), t("task_revision_within", lang)],
        key="writing_task_relationship",
        help=t("task_revision_help", lang),
    )
    is_revision = st.session_state.get("writing_task_relationship") == t("task_revision_within", lang)

    if is_revision:
        draft_stage = st.selectbox(
            t("draft_stage", lang), [t("draft_revised", lang), t("draft_final", lang)]
        )
    else:
        draft_stage = st.selectbox(
            t("draft_stage", lang), [t("draft_first", lang), t("draft_independent", lang)]
        )

    revision_of_submission_id = None
    if is_revision:
        if not learner_id:
            warning_box("student_writing_need_id", lang)
            return
        try:
            candidates = api_client.get_student_revision_candidates(learner_id).get("candidates", [])
        except ApiClientError as exc:
            render_api_error(exc, lang)
            return
        labels = {
            f"{item['writing_prompt'][:80]} · {item['draft_stage']} · #{item['essay_id']}": item["essay_id"]
            for item in candidates
        }
        if not labels:
            warning_box("student_writing_no_candidates", lang)
            return
        selected = st.selectbox(t("student_writing_select_revision", lang), list(labels))
        revision_of_submission_id = labels[selected]
        technical_caption(
            f"{t('student_writing_revision_source', lang)}: #{revision_of_submission_id}"
        )
        info_box("student_writing_revision_note", lang)
        if "submission_choose_revision" in validation_errors:
            field_error("submission_choose_revision", lang)

    section_header("student_writing_prompt_section", "student_writing_prompt_help", lang)
    writing_prompt = st.text_area(
        t("writing_prompt", lang), height=120, key="writing_prompt_input",
        help=t("student_writing_required_help", lang),
    )
    if "student_writing_need_prompt" in validation_errors:
        field_error("student_writing_need_prompt", lang)
    genre = st.selectbox(
        t("genre", lang),
        [t("genre_argumentative", lang), t("genre_expository", lang), t("genre_narrative", lang)],
    )

    with st.expander(t("student_writing_timing", lang), expanded=False):
        timed = st.checkbox(t("timed_writing", lang))
        time_limit_minutes = None
        active_duration_seconds = None
        if timed:
            time_limit_minutes = st.number_input(
                t("time_limit_minutes", lang), min_value=1, max_value=1440, value=30,
                help=t("time_limit_help", lang),
            )
            active_duration_seconds = st.number_input(
                t("active_duration_seconds", lang), min_value=0, max_value=86400, value=0,
                help=t("active_duration_help", lang),
            )
        timing_source = st.selectbox(
            t("timing_source", lang),
            ["unknown", "client_timer", "server_timestamp", "manual_report", "imported"],
            disabled=not timed,
        )
        timing_quality = st.selectbox(
            t("timing_quality", lang),
            ["unavailable", "verified", "estimated", "self_reported", "incomplete"],
            disabled=not timed,
        )
        unexplained_interruption = st.checkbox(
            t("unexplained_interruption", lang), disabled=not timed
        )

    with st.expander(t("student_writing_tools", lang), expanded=False):
        tool_use = st.text_input(
            t("tool_use", lang), value="none", help=t("tool_use_placeholder", lang)
        )

    section_header("student_writing_draft_section", "student_writing_draft_help", lang)
    essay_text = st.text_area(
        t("essay_text", lang), height=360, key="writing_essay",
        help=t("student_writing_required_help", lang),
    )
    if "student_writing_need_text" in validation_errors:
        field_error("student_writing_need_text", lang)

    student_action_block(
        "student_writing_submit_title", "student_writing_submit_desc", lang
    )
    submitted = st.button(
        t("submit_button", lang), type="primary", use_container_width=True,
        key="writing_submit_primary",
    )
    if not submitted:
        return

    errors = validate_writing_form(
        student_id,
        writing_prompt,
        essay_text,
        is_revision=is_revision,
        revision_of_submission_id=revision_of_submission_id,
    )
    if errors:
        st.session_state["writing_validation_state"] = {
            "student_id": learner_id,
            "errors": errors,
        }
        st.rerun()

    st.session_state.pop("writing_validation_state", None)
    submission = {
        "student_id": student_id,
        "writing_prompt": writing_prompt,
        "genre": genre,
        "draft_stage": draft_stage,
        "timed": timed,
        "time_limit_minutes": int(time_limit_minutes) if timed and time_limit_minutes else None,
        "active_writing_duration_seconds": (
            float(active_duration_seconds)
            if timed and active_duration_seconds and active_duration_seconds > 0
            else None
        ),
        "timing_source": timing_source if timed else "unknown",
        "timing_quality": timing_quality if timed else "unavailable",
        "unexplained_interruption": bool(unexplained_interruption) if timed else False,
        "tool_use": tool_use,
        "essay_text": essay_text,
        "revision_of_submission_id": revision_of_submission_id,
    }
    try:
        loading_box("student_writing_submitting", lang)
        result = api_client.submit(submission)
    except ApiClientError as exc:
        render_api_error(exc, lang)
        return
    except Exception:
        error_box("submission_error", lang)
        return

    result["ui_submission"] = {
        "student_id": learner_id,
        "writing_prompt": writing_prompt,
        "genre": genre,
        "draft_stage": draft_stage,
    }
    st.session_state["submission_result"] = result
    st.rerun()


# ---------------------------------------------------------------------------
# Feedback content (shared, student-safe)
# ---------------------------------------------------------------------------

def _feedback_category_label(category: str, lang: str) -> str:
    """Use an approved learner-facing label when one exists."""
    key = f"student_feedback_category_{category}"
    localized = t(key, lang)
    return localized if localized != key else category.replace("_", " ").title()


def render_feedback_content(result: dict, api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Render gate-selected feedback in priority, action, evidence order."""
    del api_client  # Kept in the public renderer signature for caller compatibility.
    provider = result.get("feedback_result", {})
    feedback = provider.get("feedback", {})
    empty_states = set(result.get("ui_empty_states") or [])
    priorities = feedback.get("priority_feedback", [])
    has_priority = bool(priorities) and "NO_SELECTED_PRIORITY" not in empty_states

    section_header("student_feedback_priorities", lang=lang)
    if has_priority:
        for item in priorities[:2]:
            feedback_priority_card(
                category=_feedback_category_label(item.get("category", ""), lang),
                evidence_quote_text="",
                explanation=item.get("explanation", ""),
                revision_guidance=item.get("revision_guidance", ""),
                lang=lang,
            )
    else:
        empty_state(
            "student_feedback_no_priority_title",
            "student_feedback_no_priority_desc",
            lang,
        )

    section_header("student_feedback_next", lang=lang)
    if has_priority:
        student_action_block(
            "student_feedback_next",
            "student_feedback_next_practice",
            lang,
        )
        st.button(
            t("student_feedback_open_practice", lang),
            type="primary",
            use_container_width=True,
            key="feedback_primary_action",
            on_click=_navigate_student_page,
            args=("practice", lang),
        )
    else:
        student_action_block(
            "student_feedback_next",
            "student_feedback_next_continue",
            lang,
        )
        st.button(
            t("student_feedback_open_writing", lang),
            type="primary",
            use_container_width=True,
            key="feedback_primary_action",
            on_click=_navigate_student_page,
            args=("student_writing_title", lang),
        )

    section_header("student_feedback_evidence", lang=lang)
    evidence_items = [
        (
            _feedback_category_label(item.get("category", ""), lang),
            item.get("evidence_quote", ""),
        )
        for item in priorities[:2]
        if has_priority and item.get("evidence_quote")
    ]
    if evidence_items:
        for label, quote in evidence_items:
            st.markdown(f"**{label}**")
            evidence_quote(quote, lang)
    else:
        info_box("student_feedback_no_priority_evidence", lang)

    section_header("student_feedback_strengths", lang=lang)
    positive_finding = feedback.get("positive_finding", {})
    if positive_finding:
        st.write(positive_finding.get("explanation", ""))
        if positive_finding.get("evidence_quote"):
            evidence_quote(positive_finding["evidence_quote"], lang)
    else:
        info_box("student_feedback_no_strengths", lang)

    uncertainty = feedback.get("uncertainty_note", "")
    limitation_notice(
        f" {uncertainty}" if uncertainty else "student_feedback_boundary",
        lang,
    )
    technical_caption(
        f"{t('student_feedback_submission_reference', lang)}: "
        f"#{result.get('submission_id', '?')}"
    )


# ---------------------------------------------------------------------------
# Feedback page (standalone)
# ---------------------------------------------------------------------------

def render_feedback_page(api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Student Feedback page: selected priority, action, evidence, limitation."""
    student_page_intro("student_feedback_title", "student_feedback_subtitle", lang)

    from app.ui.student_context import set_selected_learner, student_id_input

    student_id = student_id_input(
        "student_id", "feedback_student", lang, placeholder_key="student_id_placeholder"
    )
    set_selected_learner(student_id)
    learner_id = student_id.strip()
    if not learner_id:
        student_action_block(
            "student_feedback_priorities", "student_feedback_enter_id", lang, state="blocked"
        )
        limitation_notice("student_feedback_boundary", lang)
        return

    student_context_block([("student_context_learner", learner_id)], lang)
    result = st.session_state.get("submission_result")
    if not _writing_saved_for_learner(result, learner_id):
        try:
            api_client.get_student_revision_candidates(learner_id)
        except ApiClientError as exc:
            render_api_error(exc, lang)
            return
        empty_state(
            "student_feedback_no_session_title",
            "student_feedback_no_session_desc",
            lang,
        )
        st.button(
            t("student_feedback_open_writing", lang),
            type="primary",
            use_container_width=True,
            key="feedback_primary_action",
            on_click=_navigate_student_page,
            args=("student_writing_title", lang),
        )
        limitation_notice("student_feedback_boundary", lang)
        return

    render_feedback_content(result, api_client, lang)


# ---------------------------------------------------------------------------
# Revision page
# ---------------------------------------------------------------------------

def _revision_saved_for_source(
    result: dict | None, learner_id: str, source_submission_id: int | None = None
) -> bool:
    """Lock only a revision saved for this learner and, when given, source."""
    if not _writing_saved_for_learner(result, learner_id):
        return False
    saved_source = result.get("ui_submission", {}).get("revision_of_submission_id")
    return saved_source is not None and (
        source_submission_id is None or saved_source == source_submission_id
    )


def _revision_status_label(prefix: str, value: str, lang: str) -> str:
    """Localize frozen revision observation and confidence values."""
    key = f"student_revision_{prefix}_{value}"
    localized = t(key, lang)
    return localized if localized != key else value.replace("_", " ").title()


def _revision_observation_text(value: str, lang: str) -> str:
    """Translate the finite set of service-authored conservative observations."""
    key = {
        "The revision evidence is not sufficiently comparable.": "student_revision_observed_not_comparable",
        "The prior signal is not currently observed in the linked draft.": "student_revision_observed_not_current",
        "The signal or its evidence changed in the linked draft.": "student_revision_observed_changed",
        "The prior diagnosis category is still observed.": "student_revision_observed_still_present",
        "No comparable trajectory is available.": "student_revision_observed_unavailable",
    }.get(value)
    return t(key, lang) if key else value


def _render_revision_observation(result: dict, lang: str) -> None:
    """Separate conservative system observations from learner-facing claims."""
    trajectory = result.get("within_task_revision_trajectory") or {}
    empty_states = set(result.get("ui_empty_states") or [])
    section_header("student_revision_observation", lang=lang)
    if not trajectory:
        info_box("student_revision_no_uptake", lang)
        limitation_notice("student_revision_boundary", lang)
        return

    if "MAJOR_REWRITE_LIMITS_ATTRIBUTION" in empty_states:
        warning_box("student_revision_major_rewrite", lang)

    observations = trajectory.get("feedback_uptake_candidates", [])
    if observations:
        for item in observations[:2]:
            student_context_block(
                [
                    (
                        "student_revision_observation_status",
                        _revision_status_label("status", item.get("status", ""), lang),
                    ),
                    (
                        "student_revision_observed_change",
                        _revision_observation_text(item.get("observed_change", ""), lang),
                    ),
                    (
                        "student_revision_attribution",
                        _revision_status_label(
                            "confidence", trajectory.get("attribution_confidence", ""), lang
                        ),
                    ),
                ],
                lang,
            )
    else:
        info_box("student_revision_no_uptake", lang)

    previous = trajectory.get("previous_selected_priorities", [])
    if previous:
        section_header("student_revision_priorities", lang=lang)
        for item in previous[:2]:
            student_context_block(
                [
                    (
                        "student_revision_feedback_focus",
                        _feedback_category_label(item.get("category", ""), lang),
                    ),
                    ("revision_guidance", item.get("revision_guidance", "")),
                ],
                lang,
            )
    elif "NO_PREVIOUS_PRIORITY" in empty_states:
        info_box("student_revision_no_previous", lang)

    first_latest = trajectory.get("first_to_latest_comparison") or {}
    if first_latest:
        changes = first_latest.get("token_changes", {})
        section_header("student_revision_changes", lang=lang)
        student_context_block(
            [
                (
                    "student_revision_inserted",
                    f"{float(changes.get('inserted_ratio', 0)):.1%}",
                ),
                (
                    "student_revision_deleted",
                    f"{float(changes.get('deleted_ratio', 0)):.1%}",
                ),
                (
                    "student_revision_modified",
                    f"{float(changes.get('modified_ratio', 0)):.1%}",
                ),
            ],
            lang,
        )
        info_box("student_revision_edit_note", lang)
    limitation_notice("student_revision_boundary", lang)


def render_revision_page(api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Student Revision page: original context, revised-text task, observation."""
    student_page_intro("student_revision_title", "student_revision_purpose", lang)

    from app.ui.student_context import set_selected_learner, student_id_input

    student_id = student_id_input(
        "student_id", "revision_student", lang, placeholder_key="student_id_placeholder"
    )
    set_selected_learner(student_id)
    learner_id = student_id.strip()
    if not learner_id:
        student_action_block(
            "student_revision_current_action",
            "student_revision_enter_id",
            lang,
            state="blocked",
        )
        limitation_notice("student_revision_boundary", lang)
        return

    student_context_block([("student_context_learner", learner_id)], lang)
    saved = st.session_state.get("submission_result")
    if _revision_saved_for_source(saved, learner_id):
        source = saved.get("ui_submission", {}).get("revision_source", {})
        section_header("student_revision_original_context", lang=lang)
        student_context_block(
            [
                ("writing_prompt", source.get("writing_prompt", "")),
                ("student_revision_source_stage", source.get("draft_stage", "")),
            ],
            lang,
        )
        if source.get("essay_text"):
            evidence_quote(source["essay_text"], lang)
        success_box("student_revision_saved_title", lang)
        student_action_block(
            "student_revision_saved_title",
            "student_revision_saved_desc",
            lang,
            state="complete",
        )
        technical_caption(
            f"{t('student_revision_source_reference', lang)}: "
            f"#{saved.get('ui_submission', {}).get('revision_of_submission_id', '?')} · "
            f"{t('student_revision_saved_reference', lang)}: #{saved.get('submission_id', '?')}"
        )
        _render_revision_observation(saved, lang)
        st.button(
            t("student_revision_open_journey", lang),
            type="primary",
            use_container_width=True,
            key="revision_primary_action",
            on_click=_navigate_student_page,
            args=("learning_journey", lang),
        )
        return

    try:
        with st.spinner(t("student_revision_loading", lang)):
            candidates = api_client.get_student_revision_candidates(learner_id).get(
                "candidates", []
            )
    except ApiClientError as exc:
        render_api_error(exc, lang)
        return
    if not candidates:
        empty_state(
            "student_revision_no_eligible_title",
            "student_revision_no_eligible_desc",
            lang,
        )
        st.button(
            t("student_feedback_open_writing", lang),
            type="primary",
            use_container_width=True,
            key="revision_primary_action",
            on_click=_navigate_student_page,
            args=("student_writing_title", lang),
        )
        limitation_notice("student_revision_boundary", lang)
        return

    labels = {
        f"{item.get('writing_prompt', '')[:80]} · {item.get('draft_stage', '')} · #{item.get('essay_id', '?')}": item
        for item in candidates
    }
    selected_label = st.selectbox(
        t("student_revision_select_source", lang), list(labels), key="revision_source_select"
    )
    selected = labels[selected_label]
    source_id = int(selected["essay_id"])
    try:
        source = api_client.get_submission(source_id)
        targets = api_client.get_practice_targets(learner_id)
    except ApiClientError as exc:
        render_api_error(exc, lang)
        return

    section_header("student_revision_original_context", lang=lang)
    student_context_block(
        [
            ("writing_prompt", source.get("writing_prompt", "")),
            ("student_revision_source_stage", source.get("draft_stage", "")),
        ],
        lang,
    )
    st.text_area(
        t("student_revision_original_text", lang),
        value=source.get("essay_text", ""),
        height=220,
        disabled=True,
        key=f"revision_original_{source_id}",
    )
    matching_targets = [
        item for item in targets
        if int(item.get("source_submission_id") or 0) == source_id
        and item.get("status") == "active"
    ]
    if matching_targets:
        student_context_block(
            [("student_revision_feedback_focus", matching_targets[0].get("target_label", ""))],
            lang,
        )
    else:
        info_box("student_revision_no_target_context", lang)
    technical_caption(f"{t('student_revision_source_reference', lang)}: #{source_id}")

    validation_state = st.session_state.get("revision_validation_state") or {}
    invalid = (
        validation_state.get("student_id") == learner_id
        and validation_state.get("source_submission_id") == source_id
    )
    section_header("student_revision_revised_text", lang=lang)
    revised_text = st.text_area(
        t("student_revision_revised_text", lang),
        height=360,
        key="revision_text_input",
        help=t("student_writing_required_help", lang),
    )
    if invalid:
        field_error("student_revision_empty_text", lang)
    student_action_block(
        "student_revision_current_action", "student_revision_submit_desc", lang
    )
    if not st.button(
        t("student_revision_submit", lang),
        type="primary",
        use_container_width=True,
        key="revision_submit_primary",
    ):
        limitation_notice("student_revision_boundary", lang)
        return
    if not revised_text.strip():
        st.session_state["revision_validation_state"] = {
            "student_id": learner_id,
            "source_submission_id": source_id,
        }
        st.rerun()

    st.session_state.pop("revision_validation_state", None)
    submission = {
        "student_id": learner_id,
        "writing_prompt": source.get("writing_prompt", ""),
        "genre": source.get("genre", "argumentative essay"),
        "draft_stage": "revised draft",
        "timed": False,
        "time_limit_minutes": None,
        "active_writing_duration_seconds": None,
        "timing_source": "unknown",
        "timing_quality": "unavailable",
        "unexplained_interruption": False,
        "tool_use": source.get("tool_use", "none"),
        "essay_text": revised_text,
        "revision_of_submission_id": source_id,
    }
    try:
        loading_box("student_revision_submitting", lang)
        result = api_client.submit(submission)
    except ApiClientError as exc:
        render_api_error(exc, lang)
        return
    except Exception:
        error_box("submission_error", lang)
        return
    result["ui_submission"] = {
        "student_id": learner_id,
        "writing_prompt": source.get("writing_prompt", ""),
        "genre": source.get("genre", "argumentative essay"),
        "draft_stage": "revised draft",
        "revision_of_submission_id": source_id,
        "revision_source": {
            "writing_prompt": source.get("writing_prompt", ""),
            "draft_stage": source.get("draft_stage", ""),
            "essay_text": source.get("essay_text", ""),
        },
    }
    st.session_state["submission_result"] = result
    st.rerun()


# ---------------------------------------------------------------------------
# Practice page
# ---------------------------------------------------------------------------

def _practice_instruction(exercise: dict, lang: str) -> str:
    """Read the learner instruction from the authoritative exercise specification."""
    from app.practice.schemas import default_exercise_specifications

    specification = default_exercise_specifications().get(exercise.get("exercise_type", ""))
    if specification is None:
        return exercise.get("instructions", "")
    return specification.learner_instructions.get(
        lang, specification.learner_instructions.get("en", exercise.get("instructions", ""))
    )


def _practice_constraint_label(constraint: str, lang: str) -> str:
    """Localize the two frozen deterministic-template constraints."""
    key = {
        "Retain original meaning.": "student_practice_constraint_retain",
        "Do not add unsupported content.": "student_practice_constraint_no_unsupported",
    }.get(constraint)
    return t(key, lang) if key else constraint


def _practice_status_label(prefix: str, value: str, lang: str) -> str:
    """Localize known conservative evaluation values without changing them."""
    key = f"student_practice_{prefix}_{value}"
    localized = t(key, lang)
    return localized if localized != key else value.replace("_", " ").title()


def _practice_attempt_with_cached_evaluation(loaded: list[dict]) -> list[dict]:
    """Keep a just-returned evaluation visible across the immediate rerun."""
    cached = {
        item.get("attempt_id"): item.get("evaluation")
        for item in st.session_state.get("exercise_attempts_v2", [])
        if item.get("attempt_id") and item.get("evaluation")
    }
    for item in loaded:
        if item.get("attempt_id") in cached:
            item["evaluation"] = cached[item["attempt_id"]]
    return loaded


def render_practice_page(api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Student Practice page: one explicit target-to-evaluation sequence."""
    student_page_intro("practice", "student_practice_purpose", lang)

    from app.ui.student_context import set_selected_learner, student_id_input

    student_id = student_id_input(
        "student_id", "practice_student_v2", lang, placeholder_key="student_id_placeholder"
    )
    set_selected_learner(student_id)
    learner_id = student_id.strip()
    steps = (
        "student_practice_step_target",
        "student_practice_step_exercise",
        "student_practice_step_response",
        "student_practice_step_evaluation",
    )
    if not learner_id:
        student_task_steps(list(steps), 0, lang)
        student_action_block(
            "student_practice_current_action",
            "student_practice_enter_id",
            lang,
            state="blocked",
        )
        limitation_notice("practice_boundary", lang)
        return

    student_context_block([("student_context_learner", learner_id)], lang)
    try:
        with st.spinner(t("practice_loading", lang)):
            targets = api_client.get_practice_targets(learner_id)
            active_targets = [item for item in targets if item.get("status") == "active"]
            exercise = None
            attempts: list[dict] = []
            if active_targets:
                instances = api_client.get_exercise_instances(
                    active_targets[0].get("practice_target_id", "")
                )
                if instances:
                    exercise = instances[-1]
                    loaded_attempts = api_client.get_exercise_attempts(
                        exercise.get("exercise_id", "")
                    )
                    attempts = _practice_attempt_with_cached_evaluation(loaded_attempts)
    except ApiClientError as exc:
        render_api_error(exc, lang)
        return

    st.session_state["practice_targets_v2"] = targets
    if exercise:
        st.session_state["current_exercise_v2"] = exercise
    else:
        st.session_state.pop("current_exercise_v2", None)
    st.session_state["exercise_attempts_v2"] = attempts

    if not active_targets:
        student_task_steps(list(steps), 0, lang)
        student_action_block(
            "student_practice_current_action",
            "student_practice_no_target_action",
            lang,
            state="blocked",
        )
        st.button(
            t("student_feedback_open_writing", lang),
            type="primary",
            use_container_width=True,
            key="practice_primary_action",
            on_click=_navigate_student_page,
            args=("student_writing_title", lang),
        )
        limitation_notice("practice_boundary", lang)
        return

    selected = active_targets[0]
    section_header("practice_target", lang=lang)
    student_context_block(
        [("student_practice_focus", selected.get("target_label", ""))], lang
    )
    technical_caption(
        f"{t('student_practice_source_submission', lang)}: "
        f"#{selected.get('source_submission_id', '?')}"
    )

    if not exercise:
        student_task_steps(list(steps), 1, lang)
        student_action_block(
            "student_practice_current_action",
            "student_practice_action_generate",
            lang,
        )
        source_text = st.text_area(
            t("student_practice_source_text", lang),
            key="practice_source_v2",
            height=120,
            placeholder=t("student_practice_source_placeholder", lang),
        )
        if st.button(
            t("generate_exercise", lang),
            key="practice_gen",
            type="primary",
            use_container_width=True,
        ):
            payload = {"practice_target": selected, "source_text": source_text}
            try:
                created = api_client.create_exercise(
                    selected.get("practice_target_id", ""), payload
                )
            except ApiClientError as exc:
                render_api_error(exc, lang)
                return
            if created.get("status") == "practice_not_available":
                warning_box("practice_not_available", lang)
                return
            st.session_state["current_exercise_v2"] = created
            st.session_state["exercise_attempts_v2"] = []
            st.rerun()
        limitation_notice("practice_boundary", lang)
        return

    section_header("exercise_instructions", lang=lang)
    student_context_block(
        [("exercise_instructions", _practice_instruction(exercise, lang))], lang
    )
    if exercise.get("source_text"):
        evidence_quote(exercise["source_text"], lang)
    constraints = exercise.get("constraints", [])
    if constraints:
        st.markdown(
            "**" + t("exercise_constraints", lang) + "**" + chr(10)
            + chr(10).join(
                f"- {_practice_constraint_label(item, lang)}" for item in constraints
            )
        )

    if attempts:
        student_task_steps(list(steps), 4, lang)
        latest = attempts[-1]
        success_box("student_practice_attempt_saved", lang)
        section_header("student_practice_saved_response", lang=lang)
        student_context_block(
            [("student_practice_saved_response", latest.get("response_text", ""))], lang
        )
        section_header("practice_evaluation_label", lang=lang)
        evaluation = latest.get("evaluation")
        if evaluation:
            student_context_block(
                [
                    (
                        "practice_evaluation_completion",
                        _practice_status_label(
                            "completion", evaluation.get("completion_status", ""), lang
                        ),
                    ),
                    (
                        "practice_evaluation_action",
                        _practice_status_label(
                            "action", evaluation.get("target_action_status", ""), lang
                        ),
                    ),
                ],
                lang,
            )
        else:
            info_box("student_practice_evaluation_unavailable", lang)
        student_action_block(
            "student_practice_current_action",
            "student_practice_action_revision",
            lang,
        )
        st.button(
            t("student_home_go_revision", lang),
            type="primary",
            use_container_width=True,
            key="practice_primary_action",
            on_click=_navigate_student_page,
            args=("student_revision_title", lang),
        )
        limitation_notice("practice_boundary", lang)
        return

    student_task_steps(list(steps), 2, lang)
    student_action_block(
        "student_practice_current_action",
        "student_practice_action_respond",
        lang,
    )
    response_text = st.text_area(
        t("response_field", lang),
        key="practice_response_v2",
        height=160,
        placeholder=t("student_practice_response_placeholder", lang),
    )
    if st.button(
        t("submit_attempt", lang),
        key="practice_submit",
        type="primary",
        use_container_width=True,
    ):
        if not response_text.strip():
            field_error("student_practice_empty_response", lang)
        else:
            payload = {
                "student_id": learner_id,
                "response_text": response_text,
                "attempt_number": 1,
            }
            try:
                attempt = api_client.submit_exercise_attempt(
                    exercise.get("exercise_id", ""), payload
                )
            except ApiClientError as exc:
                render_api_error(exc, lang)
                return
            st.session_state["exercise_attempts_v2"] = [attempt]
            st.rerun()
    limitation_notice("practice_boundary", lang)


# ---------------------------------------------------------------------------
# Learning Journey page
# ---------------------------------------------------------------------------

def _journey_evidence_label(value: str, lang: str) -> str:
    key = f"student_journey_evidence_{value}"
    localized = t(key, lang)
    return localized if localized != key else value.replace("_", " ").title()


def _journey_source_label(event: dict, lang: str) -> str:
    source_type = event.get("source_record_type", "")
    key = f"student_journey_source_{source_type}"
    localized = t(key, lang)
    label = localized if localized != key else source_type.replace("_", " ").title()
    source_id = event.get("source_record_id", "")
    return f"{label} #{source_id}" if source_id else label


def _journey_description_params(event: dict, lang: str) -> dict:
    params = dict(event.get("description_params") or {})
    target_key = {
        "lexical_repetition_local": "student_journey_target_lexical_repetition",
        "connective_overuse": "student_journey_target_connective_overuse",
        "long_sentence": "student_journey_target_long_sentence",
        "vague_organization": "student_journey_target_vague_organization",
    }.get(str(params.get("target", "")))
    if target_key:
        params["target"] = t(target_key, lang)
    status = str(params.get("status", ""))
    if status:
        status_key = f"student_journey_status_{status}"
        localized = t(status_key, lang)
        params["status"] = localized if localized != status_key else status.replace("_", " ").title()
    return params


def _journey_limitation(event: dict, lang: str) -> str:
    key = f"student_journey_limit_{event.get('event_type', '')}"
    localized = t(key, lang)
    if localized != key:
        return localized
    limitations = event.get("limitations") or []
    return limitations[0] if limitations else t("journey_empty_boundary", lang)


def _journey_action_contract(state: str) -> tuple[str, str, str]:
    return {
        "no_submissions": (
            "journey_empty_no_submissions_next", "student_writing_title", "student_home_go_writing"
        ),
        "submission_without_analysis": (
            "journey_empty_no_analysis_next", "student_feedback_title", "student_home_go_feedback"
        ),
        "analysis_without_priority": (
            "journey_empty_no_priority_next", "student_writing_title", "student_home_go_writing"
        ),
        "feedback_no_practice_target": (
            "journey_empty_no_target_next", "student_feedback_title", "student_home_go_feedback"
        ),
        "target_no_attempt": (
            "journey_empty_no_attempt_next", "practice", "student_home_go_practice"
        ),
        "attempt_no_evaluation": (
            "journey_empty_no_evaluation_next", "practice", "student_home_go_practice"
        ),
        "revision_no_response": (
            "journey_empty_no_revision_next", "student_revision_title", "student_home_go_revision"
        ),
        "later_task_evidence_none": (
            "journey_empty_no_transfer_next", "student_writing_title", "student_home_go_writing"
        ),
        "journey_events": (
            "student_journey_continue", "student_writing_title", "student_home_go_writing"
        ),
    }.get(
        state,
        ("student_journey_continue", "student_writing_title", "student_home_go_writing"),
    )


def _render_journey_action(state: str, lang: str) -> None:
    description_key, page_key, button_key = _journey_action_contract(state)
    student_action_block("student_journey_next_action", description_key, lang)
    st.button(
        t(button_key, lang),
        type="primary",
        use_container_width=True,
        key="journey_primary_action",
        on_click=_navigate_student_page,
        args=(page_key, lang),
    )


def render_learning_journey_page(api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Render the authoritative read-time Journey projection without writes."""
    student_page_intro("learning_journey", "student_journey_purpose", lang)

    from app.ui.student_context import set_selected_learner, student_id_input

    student_id = student_id_input(
        "student_id", "journey_student_v2", lang, placeholder_key="student_id_placeholder"
    )
    set_selected_learner(student_id)
    learner_id = student_id.strip()
    if not learner_id:
        student_action_block(
            "student_journey_next_action", "journey_enter_student_id", lang, state="blocked"
        )
        limitation_notice("all_descriptive", lang)
        return

    student_context_block([("student_context_learner", learner_id)], lang)
    try:
        with st.spinner(t("journey_loading", lang)):
            journey = api_client.get_journey(learner_id)
    except ApiClientError as exc:
        render_api_error(exc, lang)
        return

    events = journey.get("events", [])
    if not events:
        _render_journey_empty_state(journey, lang)
        return

    section_header("journey_timeline", lang=lang)
    for event in events:
        params = _journey_description_params(event, lang)
        timeline_event(
            event_label=t(event.get("title_key", ""), lang),
            timestamp=_short_timestamp(event.get("occurred_at", "")),
            detail=t(event.get("description_key", ""), lang, **params),
            boundary=_journey_limitation(event, lang),
            lang=lang,
            source_label=_journey_source_label(event, lang),
            evidence_status=_journey_evidence_label(
                event.get("evidence_status", ""), lang
            ),
        )

    for state in journey.get("derived_states", []):
        message_key = state.get("message_key") or ""
        if message_key:
            warning_box(message_key, lang)
    _render_journey_action(journey.get("state") or "journey_events", lang)
    limitation_notice("all_descriptive", lang)


def _short_timestamp(value: str) -> str:
    """Compact UTC timestamp for display (e.g., 2026-08-01 12:34)."""
    try:
        dt = __import__("datetime").datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(__import__("datetime").timezone.utc).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return str(value)[:16]


def _render_journey_empty_state(journey: dict, lang: str) -> None:
    """Render an accurate classified state and one relevant next action."""
    state = journey.get("state") or "no_submissions"
    counts = journey.get("counts") or {}
    known_text = "; ".join(
        f"{t(label, lang)}: {counts[key]}" for key, label in (
            ("submissions", "journey_known_submissions"),
            ("analysis_runs", "journey_known_analyses"),
            ("feedback_records", "journey_known_feedback"),
            ("selected_priorities", "journey_known_priorities"),
            ("practice_targets", "journey_known_targets"),
            ("exercise_attempts", "journey_known_attempts"),
        ) if int(counts.get(key) or 0) > 0
    )
    if known_text:
        technical_caption(f"{t('journey_known_label', lang)} {known_text}")

    mapping = {
        "no_submissions": (
            "journey_empty_no_submissions_title", "journey_empty_no_submissions_desc"
        ),
        "submission_without_analysis": (
            "journey_empty_no_analysis_title", "journey_empty_no_analysis_desc"
        ),
        "analysis_without_priority": (
            "journey_empty_no_priority_title", "journey_empty_no_priority_desc"
        ),
        "feedback_no_practice_target": (
            "journey_empty_no_target_title", "journey_empty_no_target_desc"
        ),
        "target_no_attempt": (
            "journey_empty_no_attempt_title", "journey_empty_no_attempt_desc"
        ),
        "attempt_no_evaluation": (
            "journey_empty_no_evaluation_title", "journey_empty_no_evaluation_desc"
        ),
        "revision_no_response": (
            "journey_empty_no_revision_title", "journey_empty_no_revision_desc"
        ),
        "later_task_evidence_none": (
            "journey_empty_no_transfer_title", "journey_empty_no_transfer_desc"
        ),
    }
    title_key, desc_key = mapping.get(state, mapping["no_submissions"])
    empty_state(title_key, desc_key, lang)
    _render_journey_action(state, lang)
    limitation_notice("journey_empty_boundary", lang)
