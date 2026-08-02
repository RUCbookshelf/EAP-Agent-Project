"""Research Evidence feature (v0.9.5-C)."""

from __future__ import annotations

import streamlit as st

from app.ui.api_client import ApiClientError, WritingFeedbackApiClient
from app.ui.components import (
    info_box,
    page_header,
    render_api_error,
    section_header,
)
from app.ui.locale import t


def render_research_evidence(api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Research Evidence: submission, analysis, diagnosis, priority, evidence audit."""
    page_header("research_evidence_title", "research_evidence_subtitle", lang)

    submission_id = st.number_input(
        t("research_evidence_submission_id", lang), min_value=1, value=1, step=1,
    )

    if not st.button(t("load_records", lang), key="evidence_load"):
        info_box("research_evidence_prompt", lang)
        return

    try:
        submission = api_client.get_submission(int(submission_id))
        analysis = api_client.get_analyses(int(submission_id))
        audit = api_client.get_diagnostic_audit(int(submission_id))
    except ApiClientError as exc:
        render_api_error(exc, lang, research=True)
        return

    section_header("research_evidence_submission", lang)
    with st.expander(t("research_evidence_submission_details", lang), expanded=True):
        safe = {k: v for k, v in submission.items() if k not in ("essay_text",)}
        st.json(safe)

    section_header("research_evidence_analysis", lang)
    with st.expander(t("research_evidence_analysis_details", lang)):
        safe = {}
        for k, v in analysis.items():
            if k == "metric_results":
                safe[k] = [{mk: mv for mk, mv in m.items()} for m in v]
            else:
                safe[k] = v
        st.json(safe)

    section_header("research_evidence_diagnosis", lang)
    with st.expander(t("research_evidence_diagnosis_details", lang)):
        st.json(audit)
