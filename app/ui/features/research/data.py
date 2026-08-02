"""Research Data feature (v0.9.5-C).

Export, privacy, filters, PII, human review, splits, and quality workflows.
The export payload is built by the UI-safe contract in
app.ui.contracts.research (plain dictionaries with the exact backend
serialization shape); no backend Pydantic models are constructed here.
"""

from __future__ import annotations

import streamlit as st

from app.ui.api_client import ApiClientError, WritingFeedbackApiClient
from app.ui.components import (
    info_box,
    loading_box,
    page_header,
    render_api_error,
    section_header,
    warning_box,
)
from app.ui.contracts.research import build_export_job_payload
from app.ui.locale import t


def render_research_data(api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Research Data: export, privacy, filters, PII, human review, splits, quality."""
    page_header("nav_research_data", "", lang)

    sub_tab1, sub_tab2, sub_tab3, sub_tab4, sub_tab5, sub_tab6, sub_tab7, sub_tab8 = st.tabs([
        t("export_preview", lang),
        t("research_data_privacy", lang),
        t("research_data_filters", lang),
        t("pii_scan", lang),
        t("human_review", lang),
        t("dataset_split", lang),
        t("data_quality", lang),
        t("export_history", lang),
    ])

    with sub_tab1:
        section_header("export_preview", lang)
        privacy = st.selectbox(
            t("export_privacy_mode", lang),
            ["pseudonymized", "internal_research", "minimal_anonymous"],
        )
        fmt = st.multiselect(t("export_formats", lang), ["jsonl", "csv"], default=["jsonl"])
        if st.button(t("export_preview", lang), key="export_preview_btn"):
            try:
                result = api_client.research_export_preview(build_export_job_payload(privacy, fmt))
                st.json(result)
            except Exception as exc:
                render_api_error(exc, lang, research=True)
        if st.button(t("export_run", lang), type="primary", key="export_run_btn"):
            try:
                loading_box("loading_research_export", lang)
                result = api_client.research_export_run(build_export_job_payload(privacy, fmt))
                st.success(t("export_run_success", lang, id=result.get("export_id", "unknown")))
                st.json(result.get("manifest", {}))
            except Exception as exc:
                render_api_error(exc, lang, research=True)

    with sub_tab2:
        section_header("research_data_privacy", lang)
        st.markdown(
            f'<div class="px-card">'
            f'<strong>{t("privacy_internal", lang)}</strong><br>'
            f'{t("privacy_pseudonymized", lang)}<br>'
            f'{t("privacy_minimal", lang)}'
            f'</div>',
            unsafe_allow_html=True,
        )
        warning_box("privacy_warning", lang)

    with sub_tab3:
        section_header("research_data_filters", lang)
        info_box("research_data_filters_placeholder", lang)

    with sub_tab4:
        section_header("pii_scan", lang)
        sub_id = st.number_input(t("research_evidence_submission_id", lang), min_value=1, value=1, step=1, key="pii_sub")
        if st.button(t("pii_scan", lang), key="pii_scan_btn"):
            try:
                pii = api_client.get_pii_candidates(int(sub_id))
                st.json(pii)
            except ApiClientError as exc:
                render_api_error(exc, lang, research=True)

    with sub_tab5:
        section_header("human_review", lang)
        target_type = st.selectbox(
            t("human_review_target", lang),
            ["diagnosis", "evidence", "feedback", "revision"],
        )
        target_id = st.text_input(t("human_review_target_id", lang), key="hr_target")
        decision = st.selectbox(
            t("human_review_decision", lang),
            ["correct", "partially_correct", "incorrect", "uncertain"],
        )
        comment = st.text_area(t("human_review_comment", lang), key="hr_comment")
        if st.button(t("human_review_create", lang), key="hr_create"):
            try:
                result = api_client.create_human_review({
                    "target_type": target_type,
                    "target_id": target_id,
                    "reviewer_id": "R001",
                    "decision": decision,
                    "confidence": "medium",
                    "comment": comment,
                    "guideline_version": "human-review-v0.1",
                })
                st.json(result)
            except Exception as exc:
                render_api_error(exc, lang, research=True)

    with sub_tab6:
        section_header("dataset_split", lang)
        if st.button(t("dataset_split", lang), key="ds_split_btn"):
            try:
                result = api_client.create_dataset_split({
                    "split_name": "research-v0.9.1",
                    "train_ratio": 0.7,
                    "val_ratio": 0.15,
                    "test_ratio": 0.15,
                    "strategy": "random",
                    "seed": 42,
                })
                st.json(result)
            except Exception as exc:
                render_api_error(exc, lang, research=True)
        warning_box("split_boundary", lang)

    with sub_tab7:
        section_header("data_quality_report", lang)
        if st.button(t("data_quality_report", lang), key="dq_report_btn"):
            try:
                result = api_client.research_data_quality()
                st.json(result)
            except Exception as exc:
                render_api_error(exc, lang, research=True)

    with sub_tab8:
        section_header("export_history", lang)
        if st.button(t("export_history", lang), key="export_hist_btn"):
            try:
                history = api_client.research_export_history()
                st.json(history)
            except Exception as exc:
                render_api_error(exc, lang, research=True)
