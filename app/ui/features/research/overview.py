"""Research Overview feature (v0.9.5-C)."""

from __future__ import annotations

import streamlit as st

from app.ui.api_client import ApiClientError, WritingFeedbackApiClient
from app.ui.components import (
    info_box,
    limitation_notice,
    page_header,
    render_api_error,
    section_header,
    warning_box,
)
from app.ui.locale import t


def render_research_overview(api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Research Overview: aggregate counts and data-quality warnings."""
    page_header("research_overview_title", "research_overview_subtitle", lang)

    try:
        health = api_client.health()
    except ApiClientError as exc:
        render_api_error(exc, lang, research=True)
        return

    section_header("research_overview_counts", lang)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f'<div class="px-card" style="text-align:center;">'
            f'<div style="font-weight:900;font-size:1.3rem;">{health.get("active_analyzer", "?")}</div>'
            f'<div style="font-size:0.85rem;color:var(--px-muted);">{t("research_overview_analyzer", lang)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f'<div class="px-card" style="text-align:center;">'
            f'<div style="font-weight:900;font-size:1.3rem;">{health.get("active_analyzer_version", "?")}</div>'
            f'<div style="font-size:0.85rem;color:var(--px-muted);">{t("research_overview_analyzer_version", lang)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f'<div class="px-card" style="text-align:center;">'
            f'<div style="font-weight:900;font-size:1.3rem;">{health.get("nlp_model_name", "?")}</div>'
            f'<div style="font-size:0.85rem;color:var(--px-muted);">{t("research_overview_nlp_model", lang)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    section_header("research_overview_provider", lang)
    requested = health.get("llm_provider", "")
    configured = health.get("llm_api_configured", False)
    st.markdown(
        f'<div class="px-card">'
        f'<strong>{t("provider_label", lang)}:</strong> {requested}<br>'
        f'{t("research_overview_api_configured", lang)}: {"Yes" if configured else "No"}'
        f'</div>',
        unsafe_allow_html=True,
    )
    if health.get("analyzer_fallback_active"):
        warning_box("research_overview_fallback", lang)

    section_header("data_quality", lang)
    try:
        dq = api_client.research_data_quality()
    except ApiClientError:
        dq = {}
    if dq:
        with st.container(border=True):
            st.json(dq)
    else:
        info_box("research_overview_no_dq", lang)

    warning_box("app_prototype_warning", lang)
