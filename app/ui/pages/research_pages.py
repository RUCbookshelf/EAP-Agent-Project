"""Research View pages for the writing-feedback-mvp Streamlit interface.

Research view exposes internal IDs, metric details, provider diagnostics,
and audit records. It uses neutral research language and avoids simplistic
quality labels.
"""

from __future__ import annotations

import streamlit as st

from app.ui.api_client import ApiClientError, WritingFeedbackApiClient
from app.ui.components import (
    audit_record,
    card_group_header,
    empty_state,
    info_box,
    limitation_notice,
    metric_card,
    page_header,
    section_header,
    warning_box,
)
from app.ui.locale import t


# ---------------------------------------------------------------------------
# Research Overview
# ---------------------------------------------------------------------------

def render_research_overview(api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Research Overview: aggregate counts and data-quality warnings."""
    page_header("research_overview_title", "research_overview_subtitle", lang)

    try:
        health = api_client.health()
    except ApiClientError:
        st.error(t("api_unavailable", lang))
        return

    st.subheader(t("research_overview_counts", lang))

    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.metric(t("research_overview_analyzer", lang), health.get("active_analyzer", "?"))
    with col2:
        with st.container(border=True):
            st.metric(t("research_overview_analyzer_version", lang), health.get("active_analyzer_version", "?"))
    with col3:
        with st.container(border=True):
            st.metric(t("research_overview_nlp_model", lang), health.get("nlp_model_name", "?"))

    # Provider status
    st.subheader(t("research_overview_provider", lang))
    requested = health.get("llm_provider", "")
    configured = health.get("llm_api_configured", False)
    with st.container(border=True):
        st.write(f"{t('provider_label', lang)}: {requested}")
        st.write(f"{t('research_overview_api_configured', lang)}: {'Yes' if configured else 'No'}")
        if health.get("analyzer_fallback_active"):
            warning_box("research_overview_fallback", lang)

    # Data quality
    st.subheader(t("data_quality", lang))
    try:
        dq = api_client.research_data_quality()
    except ApiClientError:
        dq = {}
    if dq:
        with st.container(border=True):
            st.json(dq)
    else:
        info_box("research_overview_no_dq", lang)

    # Research prototype warning
    warning_box("app_prototype_warning", lang)


# ---------------------------------------------------------------------------
# Research Evidence
# ---------------------------------------------------------------------------

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
        st.error(str(exc))
        return

    # Submission info
    section_header("research_evidence_submission", lang)
    with st.expander(t("research_evidence_submission_details", lang), expanded=True):
        safe = {k: v for k, v in submission.items() if k not in ("essay_text",)}
        st.json(safe)

    # Analysis
    section_header("research_evidence_analysis", lang)
    with st.expander(t("research_evidence_analysis_details", lang)):
        safe = {}
        for k, v in analysis.items():
            if k == "metric_results":
                safe[k] = [{mk: mv for mk, mv in m.items()} for m in v]
            else:
                safe[k] = v
        st.json(safe)

    # Diagnosis + calibration
    section_header("research_evidence_diagnosis", lang)
    with st.expander(t("research_evidence_diagnosis_details", lang)):
        st.json(audit)


# ---------------------------------------------------------------------------
# Research CALF Measures
# ---------------------------------------------------------------------------

CALF_CLASSIFICATION = {
    "lexical_complexity": "construct_lexical",
    "syntactic_complexity": "construct_syntactic",
    "product_fluency": "construct_fluency",
}


def render_research_calf(api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Research CALF Measures: grouped metric cards."""
    page_header("tab_calf", "calf_student_boundary", lang)

    result = st.session_state.get("submission_result")
    if not result:
        info_box("research_calf_no_result", lang)
        return

    metric_results = result.get("analysis", {}).get("metric_results", [])

    for construct_id, label_key in CALF_CLASSIFICATION.items():
        card_group_header(label_key, lang)
        items = [m for m in metric_results if m.get("construct_id") == construct_id]
        if not items:
            info_box("calf_no_measures", lang)
            continue
        for item in items:
            value = item.get("value")
            status_key = item.get("measurement_status") or item.get("status") or "unavailable"
            display_value = f"{value:.4f}" if isinstance(value, float) else (str(value) if value is not None else None)
            limitations = item.get("limitations") or item.get("known_limitations", [])
            metric_card(
                metric_id=item.get("metric_id", ""),
                value=display_value,
                status=status_key,
                confidence=item.get("confidence", "insufficient"),
                unit=item.get("analysis_unit_version", "legacy"),
                version=item.get("metric_version", "legacy"),
                limitations=limitations,
                lang=lang,
            )

    # Accuracy
    card_group_header("accuracy_section", lang)
    info_box("calf_accuracy_unavailable", lang)

    # Sophistication
    card_group_header("sophistication_section", lang)
    info_box("calf_sophistication_unavailable", lang)

    limitation_notice("calf_candidate_note", lang)


# ---------------------------------------------------------------------------
# Research Learning Process
# ---------------------------------------------------------------------------

def render_research_learning_process(api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Research Learning Process: complete evidence chain inspection."""
    page_header("research_learning_title", "research_learning_subtitle", lang)

    student_id = st.text_input(
        t("student_id", lang), key="learning_student",
        placeholder=t("student_id_placeholder", lang),
    )

    if not student_id.strip():
        info_box("enter_student_id", lang)
        return

    if not st.button(t("load_records", lang), key="learning_load"):
        return

    # Load all evidence
    try:
        targets = api_client.get_practice_targets(student_id.strip())
        traces = api_client.get_engagement_traces(student_id.strip())
        transfer = api_client.get_transfer_evidence(student_id.strip())
    except ApiClientError as exc:
        st.error(str(exc))
        return

    # Practice Targets
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

    # Engagement Traces
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

    # Transfer Evidence
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

    limitation_notice("all_descriptive", lang)


# ---------------------------------------------------------------------------
# Research Data
# ---------------------------------------------------------------------------

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

    # Export Preview
    with sub_tab1:
        section_header("export_preview", lang)
        privacy = st.selectbox(
            t("export_privacy_mode", lang),
            ["pseudonymized", "internal_research", "minimal_anonymous"],
        )
        fmt = st.multiselect(t("export_formats", lang), ["jsonl", "csv"], default=["jsonl"])
        if st.button(t("export_preview", lang), key="export_preview_btn"):
            try:
                from app.research.schemas import ExportJob, ExportFilter, PrivacyMode, ExportFormat
                job = ExportJob(
                    filter_spec=ExportFilter(),
                    privacy_mode=PrivacyMode(privacy),
                    formats=[ExportFormat(f) for f in fmt],
                )
                result = api_client.research_export_preview(job.model_dump(mode="json"))
                st.json(result)
            except Exception as exc:
                st.error(str(exc))
        if st.button(t("export_run", lang), type="primary", key="export_run_btn"):
            try:
                from app.research.schemas import ExportJob, ExportFilter, PrivacyMode, ExportFormat
                job = ExportJob(
                    filter_spec=ExportFilter(),
                    privacy_mode=PrivacyMode(privacy),
                    formats=[ExportFormat(f) for f in fmt],
                )
                result = api_client.research_export_run(job.model_dump(mode="json"))
                st.success(f"Export: {result.get('export_id', 'unknown')}")
                st.json(result.get("manifest", {}))
            except Exception as exc:
                st.error(str(exc))

    # Privacy
    with sub_tab2:
        section_header("research_data_privacy", lang)
        st.write(t("privacy_internal", lang))
        st.write(t("privacy_pseudonymized", lang))
        st.write(t("privacy_minimal", lang))
        warning_box("privacy_warning", lang)

    # Filters
    with sub_tab3:
        section_header("research_data_filters", lang)
        info_box("research_data_filters_placeholder", lang)

    # PII
    with sub_tab4:
        section_header("pii_scan", lang)
        sub_id = st.number_input(t("research_evidence_submission_id", lang), min_value=1, value=1, step=1, key="pii_sub")
        if st.button(t("pii_scan", lang), key="pii_scan_btn"):
            try:
                pii = api_client.get_pii_candidates(int(sub_id))
                st.json(pii)
            except ApiClientError as exc:
                st.error(str(exc))

    # Human Review
    with sub_tab5:
        section_header("human_review", lang)
        target_type = st.selectbox(
            t("human_review_target", lang),
            ["diagnosis", "evidence", "feedback", "revision"],
        )
        target_id = st.text_input("Target ID", key="hr_target")
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
                st.error(str(exc))

    # Dataset Split
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
                st.error(str(exc))
        warning_box("split_boundary", lang)

    # Data Quality
    with sub_tab7:
        section_header("data_quality_report", lang)
        if st.button(t("data_quality_report", lang), key="dq_report_btn"):
            try:
                result = api_client.research_data_quality()
                st.json(result)
            except Exception as exc:
                st.error(str(exc))

    # Export History
    with sub_tab8:
        section_header("export_history", lang)
        if st.button(t("export_history", lang), key="export_hist_btn"):
            try:
                history = api_client.research_export_history()
                st.json(history)
            except Exception as exc:
                st.error(str(exc))


# ---------------------------------------------------------------------------
# Research System Audit
# ---------------------------------------------------------------------------

def render_research_system_audit(api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Research System Audit: diagnostic audit, learner model, reanalysis, admin."""
    page_header("research_audit_title", "research_audit_subtitle", lang)

    audit_tab1, audit_tab2, audit_tab3, audit_tab4 = st.tabs([
        t("nav_diagnostic_audit", lang),
        t("nav_learner_model_audit", lang),
        t("research_audit_reanalysis", lang),
        t("nav_local_administration", lang),
    ])

    # Diagnostic Audit
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
                st.error(str(exc))

    # Learner Model Audit
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
            st.error(str(exc))

        profile = st.session_state.get("learner_model_audit_v2")
        if profile:
            st.json(profile)

    # Reanalysis
    with audit_tab3:
        section_header("research_audit_reanalysis", lang)
        info_box("research_audit_reanalysis_note", lang)

    # Admin
    with audit_tab4:
        section_header("nav_local_administration", lang)
        try:
            configs = api_client.get_configurations()
            st.json(configs)
        except ApiClientError as exc:
            st.error(str(exc))
