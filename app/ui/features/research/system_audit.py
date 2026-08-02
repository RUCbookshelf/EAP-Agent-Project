"""Research System Audit feature (v0.9.5-C)."""

from __future__ import annotations

import streamlit as st

from app.ui.api_client import ApiClientError
from app.ui.ports.research import ResearchSystemAuditApiPort
from app.ui.components import (
    info_box,
    page_header,
    render_api_error,
    section_header,
)
from app.ui.locale import t


def render_research_system_audit(api_client: ResearchSystemAuditApiPort, lang: str) -> None:
    """Research System Audit: diagnostic audit, learner model, reanalysis, admin."""
    page_header("research_audit_title", "research_audit_subtitle", lang)

    audit_tab1, audit_tab2, audit_tab3, audit_tab4 = st.tabs([
        t("nav_diagnostic_audit", lang),
        t("nav_learner_model_audit", lang),
        t("research_audit_reanalysis", lang),
        t("nav_local_administration", lang),
    ])

    with audit_tab1:
        section_header("nav_diagnostic_audit", lang)
        sub_id = st.number_input(
            t("research_evidence_submission_id", lang), min_value=1, value=1, step=1,
            key="diag_sub",
        )
        if st.button(t("load_records", lang), key="diag_load"):
            try:
                audit = api_client.get_diagnostic_audit(int(sub_id))
                st.json(audit)
            except ApiClientError as exc:
                render_api_error(exc, lang, research=True)

    with audit_tab2:
        section_header("nav_learner_model_audit", lang)
        student_id = st.text_input(
            t("student_id", lang), key="lm_student",
            placeholder=t("student_id_placeholder", lang),
        )
        strategy = st.selectbox(
            t("research_audit_strategy", lang),
            ["final_or_latest", "first_draft_only", "latest_draft_only", "all_drafts_research_mode"],
        )
        col1, col2 = st.columns(2)
        try:
            if col1.button(t("research_audit_preview", lang)):
                st.session_state["learner_model_audit_v2"] = api_client.preview_learner_model(
                    student_id.strip(), strategy,
                )
            if col2.button(t("research_audit_rebuild", lang)):
                st.session_state["learner_model_audit_v2"] = api_client.rebuild_learner_model(
                    student_id.strip(), strategy,
                )
        except ApiClientError as exc:
            render_api_error(exc, lang, research=True)

        profile = st.session_state.get("learner_model_audit_v2")
        if profile:
            st.json(profile)

    with audit_tab3:
        section_header("research_audit_reanalysis", lang)
        info_box("research_audit_reanalysis_note", lang)

    with audit_tab4:
        section_header("nav_local_administration", lang)
        try:
            configs = api_client.get_configurations()
            st.json(configs)
        except ApiClientError as exc:
            render_api_error(exc, lang, research=True)
