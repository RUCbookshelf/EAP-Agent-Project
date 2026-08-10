"""Wave-2 Student History & Learning page (Goal PDW2-D-UX-STUDENT).

Student-understandable history: task/context, submission/revision sequence,
prior feedback, longitudinal observations, and current LearningItems with
next-learning suggestions. Rendered from gateway views only; raw technical
internals never appear.
"""

from __future__ import annotations

import streamlit as st

from app.ui.components import (
    empty_state,
    info_box,
    limitation_notice,
    render_api_error,
    section_header,
    student_action_block,
    student_context_block,
    student_page_intro,
    technical_caption,
)
from app.ui.wave2.journey import (
    _category_label,
    _draft_stage_label,
    _item_status_label,
    _recurrence_label,
)
from app.ui.wave2.locale import wt
from app.ui.student_context import set_selected_learner, student_id_input
from app.ui.wave2.client import Wave2ApiClientError, Wave2ApiUnavailable
from app.ui.wave2.gateway import Wave2Gateway


def _short_date(value: str) -> str:
    return (value or "")[:10]


def _render_versions(versions: list[dict], lang: str) -> None:
    for version in versions:
        number = int(version.get("version_number") or 1)
        stage = _draft_stage_label(version.get("draft_stage", ""), lang)
        submitted = _short_date(version.get("submitted_at", ""))
        revision_of = version.get("revision_of_submission_id")
        marker = wt("wave2_history_version_initial", lang) if revision_of is None else (
            wt("wave2_history_version_revision", lang)
        )
        st.markdown(f"- {wt('wave2_history_version', lang)} {number} ({marker}) — {stage} — {submitted}")


def _render_task_card(entry: dict, lang: str) -> None:
    task = entry.get("task") or {}
    with st.container(border=True, key=f"wave2_history_task_{task.get('task_id') or 'legacy'}"):
        context_raw = task.get("writing_context", "")
        context_label = wt(f"wave2_context_{context_raw}", lang)
        if context_label.startswith("wave2_context_"):
            context_label = context_raw.replace("_", " ").title() or "-"
        st.markdown(f"**{context_label}** · {_short_date(task.get('created_at', ''))}")
        st.markdown(task.get("writing_prompt", ""))
        versions = entry.get("versions") or []
        if versions:
            section_header("wave2_history_versions", lang=lang)
            _render_versions(versions, lang)
        feedback_summary = entry.get("feedback_summary") or []
        if feedback_summary:
            section_header("wave2_history_feedback", lang=lang)
            for item in feedback_summary:
                st.markdown(
                    f"- {_category_label(item.get('category', ''), lang)} · "
                    f"{_recurrence_label(item.get('recurrence_status', 'insufficient_history'), lang)}"
                )


def _render_longitudinal(longitudinal: dict, lang: str) -> None:
    difficulties = longitudinal.get("difficulties") or []
    strengths = longitudinal.get("strengths") or []
    stable = longitudinal.get("stable") or []
    if not (difficulties or strengths or stable):
        info_box("wave2_history_empty_patterns", lang)
        return
    if difficulties:
        section_header("wave2_history_difficulties", lang=lang)
        for entry in difficulties:
            st.markdown(f"- {entry.get('label', '')}")
    if strengths:
        section_header("wave2_history_strengths", lang=lang)
        for entry in strengths:
            st.markdown(f"- {entry.get('label', '')}")
    if stable:
        section_header("wave2_history_stable", lang=lang)
        for entry in stable:
            st.markdown(f"- {entry.get('label', '')}")
    anchors = longitudinal.get("proficiency_anchors") or []
    if anchors:
        section_header("wave2_history_anchors", lang=lang)
        for anchor in anchors:
            st.markdown(
                f"- {anchor.get('system', '')}: {anchor.get('declared_value', '')}"
            )
        statement = longitudinal.get("statement", "")
        if statement:
            technical_caption(statement)


def _render_learning_items(items: list[dict], lang: str) -> None:
    if not items:
        info_box("wave2_history_empty_items", lang)
        return
    section_header("wave2_history_items", lang=lang)
    for item in items:
        st.markdown(
            f"- {_category_label(item.get('category', ''), lang)} · "
            f"{_item_status_label(item.get('status', 'proposed'), lang)} · "
            f"{_short_date(item.get('created_at', ''))}"
        )
    limitation_notice("wave2_items_note", lang)


def render_wave2_history_page(gateway: Wave2Gateway, lang: str) -> None:
    """Entry point: writing history + long-term patterns + learning items."""
    student_page_intro("student_wave2_history_title", "student_wave2_history_subtitle", lang)

    learner_id = student_id_input(
        "student_id", "wave2_history_student", lang, placeholder_key="student_id_placeholder"
    )
    set_selected_learner(learner_id)
    learner_id = learner_id.strip()
    if not learner_id:
        student_action_block(
            "student_home_enter_id", "wave2_history_enter_id", lang, state="blocked",
        )
        limitation_notice("wave2_boundary", lang)
        return
    student_context_block([("student_context_learner", learner_id)], lang)

    session_tasks = list(st.session_state.get("wave2_session_tasks") or [])
    try:
        history = gateway.history(learner_id, session_tasks=session_tasks)
    except (Wave2ApiClientError, Wave2ApiUnavailable) as exc:
        render_api_error(exc, lang)
        return

    mode = history.get("mode", gateway.mode())
    if mode == "standard":
        info_box("wave2_history_standard_note", lang)

    tasks = history.get("tasks") or []
    events = history.get("events") or []
    if not tasks and not events:
        empty_state("wave2_history_empty", "wave2_history_empty_desc", lang)
    else:
        section_header("wave2_history_tasks_section", lang=lang)
        for entry in tasks:
            _render_task_card(entry, lang)
        if events:
            section_header("wave2_history_events", lang=lang)
            for event in events:
                label = wt(event.get("title_key", ""), lang)
                st.markdown(f"- {label} — {_short_date(event.get('occurred_at', ''))}")

    section_header("wave2_history_patterns", lang=lang)
    _render_longitudinal(history.get("longitudinal") or {}, lang)

    _render_learning_items(history.get("learning_items") or [], lang)
    limitation_notice("wave2_boundary", lang)


__all__ = ["render_wave2_history_page"]