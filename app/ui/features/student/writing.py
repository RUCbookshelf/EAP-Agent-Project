"""Student Writing feature (v0.9.5-C)."""

from __future__ import annotations

import streamlit as st

from app.ui.api_client import ApiClientError, WritingFeedbackApiClient
from app.ui.components import (
    error_box,
    field_error,
    info_box,
    limitation_notice,
    loading_box,
    render_api_error,
    section_header,
    student_action_block,
    student_context_block,
    student_page_intro,
    success_box,
    technical_caption,
    validate_writing_form,
    warning_box,
)
from app.ui.features.student.navigation import _navigate_student_page
from app.ui.features.student.session import _writing_saved_for_learner
from app.ui.locale import t
from app.ui.student_context import set_selected_learner, student_id_input


def render_writing_page(api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Student Writing page: one required drafting task and one submit action."""
    student_page_intro("student_writing_title", "student_writing_subtitle", lang)

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
