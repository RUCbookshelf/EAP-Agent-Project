"""Student Learning Journey feature (v0.9.5-C)."""

from __future__ import annotations

import streamlit as st

from app.ui.api_client import ApiClientError
from app.ui.ports.student import StudentJourneyApiPort
from app.ui.components import (
    empty_state,
    info_box,
    limitation_notice,
    section_header,
    student_action_block,
    student_context_block,
    student_page_intro,
    technical_caption,
    timeline_event,
    warning_box,
)
from app.ui.features.student.formatting import _short_timestamp
from app.ui.features.student.navigation import _navigate_student_page
from app.ui.locale import t
from app.ui.student_context import set_selected_learner, student_id_input


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


def render_learning_journey_page(api_client: StudentJourneyApiPort, lang: str) -> None:
    """Render the authoritative read-time Journey projection without writes."""
    student_page_intro("learning_journey", "student_journey_purpose", lang)

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
