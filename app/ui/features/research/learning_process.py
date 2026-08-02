"""Research Learning Process feature (v0.9.5-C)."""

from __future__ import annotations

import streamlit as st

from app.ui.api_client import ApiClientError
from app.ui.ports.research import ResearchLearningProcessApiPort
from app.ui.components import (
    audit_record,
    data_table,
    info_box,
    limitation_notice,
    page_header,
    render_api_error,
    section_header,
)
from app.ui.locale import t
from app.ui.student_context import set_selected_learner, student_id_input


def render_research_learning_process(api_client: ResearchLearningProcessApiPort, lang: str) -> None:
    """Research Learning Process: complete evidence chain inspection."""
    page_header("research_learning_title", "research_learning_subtitle", lang)

    student_id = student_id_input("student_id", "learning_student", lang, placeholder_key="student_id_placeholder")
    set_selected_learner(student_id)

    if not student_id.strip():
        info_box("enter_student_id", lang)
        return

    if not st.button(t("load_records", lang), key="learning_load"):
        return

    try:
        targets = api_client.get_practice_targets(student_id.strip())
        traces = api_client.get_engagement_traces(student_id.strip())
        transfer = api_client.get_transfer_evidence(student_id.strip())
    except ApiClientError as exc:
        render_api_error(exc, lang, research=True)
        return

    section_header("practice_target", lang)
    if targets:
        for t_item in targets:
            source = "system" if t_item.get("source") == "system_generated" else "human_review"
            audit_record(
                record_id=t_item.get("practice_target_id", ""),
                label=f"{t_item.get('target_code', '')} [{source}]",
                data=t_item,
                lang=lang,
            )
    else:
        info_box("empty_audit", lang)

    section_header("feedback_engagement_trace", lang)
    if traces:
        for tr in traces:
            audit_record(
                record_id=tr.get("trace_id", ""),
                label=tr.get("status", ""),
                data=tr,
                lang=lang,
            )
    else:
        info_box("empty_audit_traces", lang)

    section_header("transfer_evidence", lang)
    if transfer:
        for te in transfer:
            audit_record(
                record_id=te.get("transfer_evidence_id", ""),
                label=te.get("observed_status", ""),
                data=te,
                lang=lang,
            )
    else:
        info_box("research_learning_no_transfer", lang)

    section_header("journey_timeline", lang)
    try:
        journey = api_client.get_journey(student_id.strip())
    except ApiClientError as exc:
        render_api_error(exc, lang, research=True)
        journey = None
    if journey:
        counts = journey.get("counts") or {}
        data_table(
            headers=[t("journey_counts_label", lang), t("journey_counts_value", lang)],
            rows=[
                [t("journey_known_submissions", lang), counts.get("submissions", 0)],
                [t("journey_known_analyses", lang), counts.get("analysis_runs", 0)],
                [t("journey_known_feedback", lang), counts.get("feedback_records", 0)],
                [t("journey_known_priorities", lang), counts.get("selected_priorities", 0)],
                [t("journey_known_targets", lang), counts.get("practice_targets", 0)],
                [t("journey_known_attempts", lang), counts.get("exercise_attempts", 0)],
            ],
        )
        events = journey.get("events", [])
        if events:
            rows = "".join(
                f'<div class="px-timeline-node">'
                f'<div class="px-timeline-marker"></div>'
                f'<div class="px-timeline-content">'
                f'<strong>{ev.get("event_type", "")}</strong>'
                f'<span style="font-size:0.85rem;color:var(--px-muted);"> {ev.get("occurred_at", "")}</span><br>'
                f'<span style="font-size:0.85rem;color:var(--px-muted);">'
                f'source: {ev.get("source_record_type", "")} {ev.get("source_record_id", "")} &middot; '
                f'task: {ev.get("task_id") or "-"} &middot; version: {ev.get("event_version", "")}</span>'
                f'</div></div>'
                for ev in events
            )
            st.markdown(rows, unsafe_allow_html=True)
        else:
            info_box("empty_audit", lang)

    limitation_notice("all_descriptive", lang)
