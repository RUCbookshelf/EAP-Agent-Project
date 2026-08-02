"""Research CALF Measures feature (v0.9.5-C)."""

from __future__ import annotations

import streamlit as st

from app.ui.api_client import WritingFeedbackApiClient
from app.ui.components import (
    card_group_header,
    info_box,
    limitation_notice,
    metric_card,
    page_header,
)
from app.ui.locale import t


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
        st.markdown('<div class="px-metric-grid">', unsafe_allow_html=True)
        for item in items:
            value = item.get("value")
            display_value = f"{value:.4f}" if isinstance(value, float) else (str(value) if value is not None else None)
            limitations = item.get("limitations") or item.get("known_limitations", [])
            status_key = item.get("measurement_status") or item.get("status") or "unavailable"
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
        st.markdown('</div>', unsafe_allow_html=True)

    card_group_header("accuracy_section", lang)
    info_box("calf_accuracy_unavailable", lang)

    card_group_header("sophistication_section", lang)
    info_box("calf_sophistication_unavailable", lang)

    limitation_notice("calf_candidate_note", lang)
