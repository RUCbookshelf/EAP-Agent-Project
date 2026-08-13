"""Streamlit application entry point for v0.9.2 Pixel Art UI.

Two primary modes:
1. Student View - progressive disclosure for feedback and action
2. Research View - auditable metrics, evidence, and system data
"""

from __future__ import annotations

import streamlit as st

from app.config import load_settings
from app.ui.api_client import ApiClientError, WritingFeedbackApiClient
from app.ui.components import page_header, technical_caption, warning_box
from app.ui.locale import t
from app.ui.pixel_art import inject_pixel_art
from app.ui.wave2.client import Wave2ApiClient
from app.ui.wave2.gateway import Wave2Gateway
from app.ui.wave2.history import render_wave2_history_page
from app.ui.wave2.journey import render_wave2_studio_page
from app.ui.pages.student_pages import (
    render_adaptive_learning_page,
    render_feedback_page,
    render_learning_journey_page,
    render_practice_page,
    render_revision_page,
    render_student_home,
    render_writing_page,
)
from app.ui.pages.research_pages import (
    render_research_calf,
    render_research_data,
    render_research_evidence,
    render_research_learning_process,
    render_research_overview,
    render_research_system_audit,
)


# Backward-compatible utility exports for existing tests
def grouped_connectives(analysis):
    detected = analysis.get("artifacts", {}).get("connective_features", {}).get("detected_connectives", [])
    grouped = {}
    for item in detected:
        class_name = item.get("expression_class", "discourse_connective")
        expression = item.get("normalized_form") or item.get("text")
        bucket = grouped.setdefault(class_name, {})
        if expression not in bucket:
            bucket[expression] = {
                "expression": item.get("text") or expression,
                "count": int(item.get("same_form_count") or 1),
                "function": item.get("function_category", "unspecified"),
            }
    return {name: list(items.values()) for name, items in grouped.items()}

# Role-based page definitions (values are locale keys; labels are translated
# at render time so navigation is fully localized in English and Chinese)
STUDENT_PAGES = {
    "student_home": "student_home_title",
    "student_writing": "student_writing_title",
    "student_feedback": "student_feedback_title",
    "student_revision": "student_revision_title",
    "student_practice": "practice",
    "student_journey": "learning_journey",
    "student_adaptive": "student_adaptive_title",
    "student_wave2_studio": "student_wave2_studio_title",
    "student_wave2_history": "student_wave2_history_title",
}

RESEARCH_PAGES = {
    "research_overview": "research_overview_title",
    "research_evidence": "research_evidence_title",
    "research_calf": "tab_calf",
    "research_learning": "research_learning_title",
    "research_data": "nav_research_data",
    "research_audit": "research_audit_title",
}


@st.cache_resource
def get_api_client(base_url: str) -> WritingFeedbackApiClient:
    return WritingFeedbackApiClient(base_url)


@st.cache_resource
def get_wave2_gateway(base_url: str) -> Wave2Gateway:
    """Build the Wave-2 gateway once per app (mode=auto).

    ``auto`` probes the Wave-2 namespace once and caches the result: guided
    mode when the Wave-2 endpoints are available at integration, graceful
    degradation to the existing writing/feedback flow otherwise. The legacy
    client is the same cached WritingFeedbackApiClient the rest of the app
    uses.
    """
    return Wave2Gateway(
        Wave2ApiClient(base_url),
        get_api_client(base_url),
        mode="auto",
    )


def _render_header(api_client: WritingFeedbackApiClient, lang: str) -> None:
    st.set_page_config(
        page_title="English Writing Feedback Prototype",
        page_icon="\u270d\ufe0f",
        layout="wide",
    )
    st.title(t("app_title", lang))
    st.caption(t("app_subtitle", lang))
    warning_box("app_prototype_warning", lang)


def _render_system_status(api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Show analyzer/provider status for Research View only.

    Student View must not expose analyzer versions, provider details, or
    configuration versions (v0.9.2 role-separation requirement).
    """
    try:
        health = api_client.health()
        analyzer_info = f"{health.get('active_analyzer','?')} {health.get('active_analyzer_version','')}"
        lifecycle = health.get("lifecycle_state", "unknown")
        technical_caption(
            f"[System] {t('app_analyzer_label', lang)}: {analyzer_info} | "
            f"NLP: {health.get('nlp_model_name','N/A')} | State: {lifecycle}"
        )
        requested = health.get("llm_provider")
        if requested == "deepseek" and health.get("llm_api_configured"):
            technical_caption(t("app_deepseek_configured", lang))
        elif requested:
            technical_caption(t("app_provider_local_demo", lang))
    except ApiClientError:
        # Try to get lifecycle state for a better message
        try:
            live_data = api_client.live()
            state = live_data.get("lifecycle_state", "unknown")
            if state == "starting":
                st.info(t("app_api_starting", lang))
            elif state == "failed":
                st.error(t("app_api_failed", lang))
            else:
                st.info(t("app_api_unavailable", lang))
        except Exception:
            st.info(t("app_api_unavailable", lang))


def _render_sidebar(lang: str) -> tuple[str, str]:
    with st.sidebar:
        st.markdown(f"### {t('language', lang)}")
        lang_choice = st.radio(
            t("language", lang),
            [t("lang_en", lang), t("lang_zh_CN", lang)],
            index=0 if lang == "en" else 1,
            horizontal=True,
            key="sidebar_lang",
            label_visibility="collapsed",
        )
        st.caption(f"[{lang_choice}]")
        new_lang = "en" if t("lang_en", lang) in lang_choice else "zh_CN"
        if new_lang != lang:
            st.session_state["ui_language"] = new_lang
            st.rerun()

        st.markdown('<hr class="px-divider">', unsafe_allow_html=True)
        st.markdown(f"### {t('view_mode', lang)}")
        role = st.radio(
            t("view_mode", lang),
            [t("view_student", lang), t("view_research", lang)],
            horizontal=False,
            key="sidebar_role",
            label_visibility="collapsed",
        )
        current_role = "student" if t("view_student", lang) in role else "research"

        st.markdown('<hr class="px-divider">', unsafe_allow_html=True)
        st.markdown(f"### {t('nav_pages', lang)}")
        if current_role == "student":
            page_map = STUDENT_PAGES
        else:
            page_map = RESEARCH_PAGES
        # Translate page labels through the locale system so navigation is
        # fully localized (no English leakage in Chinese mode).
        page_labels = {t(v, lang): k for k, v in page_map.items()}
        selected_label = st.radio(
            t("nav_pages", lang),
            list(page_labels.keys()),
            key="sidebar_page",
            label_visibility="collapsed",
        )
        page_key = page_labels[selected_label]

    return current_role, page_key


def run() -> None:
    api_client = get_api_client(load_settings().api_base_url)
    wave2_gateway = get_wave2_gateway(load_settings().api_base_url)
    lang = st.session_state.get("ui_language", "en")

    # Inject Pixel Art CSS system
    inject_pixel_art()
    # Skip navigation link for keyboard accessibility
    st.markdown('<a href="#main-content" class="px-skip-link">Skip to main content</a>', unsafe_allow_html=True)
    # Main content anchor for skip navigation target
    st.markdown('<div id="main-content"></div>', unsafe_allow_html=True)

    _render_header(api_client, lang)
    role, page_key = _render_sidebar(lang)
    if role == "research":
        _render_system_status(api_client, lang)

    st.markdown('<hr class="px-divider">', unsafe_allow_html=True)

    if role == "student":
        if page_key == "student_home":
            render_student_home(api_client, lang)
        elif page_key == "student_writing":
            render_writing_page(api_client, lang)
        elif page_key == "student_feedback":
            render_feedback_page(api_client, lang)
        elif page_key == "student_revision":
            render_revision_page(api_client, lang)
        elif page_key == "student_practice":
            render_practice_page(api_client, lang)
        elif page_key == "student_journey":
            render_learning_journey_page(api_client, lang)
        elif page_key == "student_adaptive":
            render_adaptive_learning_page(wave2_gateway, lang)
        elif page_key == "student_wave2_studio":
            render_wave2_studio_page(wave2_gateway, lang)
        elif page_key == "student_wave2_history":
            render_wave2_history_page(wave2_gateway, lang)
    else:
        if page_key == "research_overview":
            render_research_overview(api_client, lang)
        elif page_key == "research_evidence":
            render_research_evidence(api_client, lang)
        elif page_key == "research_calf":
            render_research_calf(api_client, lang)
        elif page_key == "research_learning":
            render_research_learning_process(api_client, lang)
        elif page_key == "research_data":
            render_research_data(api_client, lang)
        elif page_key == "research_audit":
            render_research_system_audit(api_client, lang)


if __name__ == "__main__":
    run()
