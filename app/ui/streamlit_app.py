"""Streamlit application entry point for v0.9.1 role-based UI.

Two primary modes:
1. Student View - progressive disclosure for feedback and action
2. Research View - auditable metrics, evidence, and system data
"""

from __future__ import annotations

import streamlit as st

from app.config import load_settings
from app.ui.api_client import ApiClientError, WritingFeedbackApiClient
from app.ui.components import page_header, warning_box
from app.ui.locale import t
from app.ui.pages.student_pages import (
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

# Role-based page definitions
STUDENT_PAGES = {
    "student_home": "Home",
    "student_writing": "Writing",
    "student_feedback": "Feedback",
    "student_revision": "Revision",
    "student_practice": "Practice",
    "student_journey": "Learning Journey",
}

RESEARCH_PAGES = {
    "research_overview": "Overview",
    "research_evidence": "Evidence",
    "research_calf": "CALF Measures",
    "research_learning": "Learning Process",
    "research_data": "Research Data",
    "research_audit": "System Audit",
}


@st.cache_resource
def get_api_client(base_url: str) -> WritingFeedbackApiClient:
    return WritingFeedbackApiClient(base_url)


def _render_header(api_client: WritingFeedbackApiClient, lang: str) -> None:
    st.set_page_config(
        page_title="English Writing Feedback Prototype",
        page_icon="\u270d\ufe0f",
        layout="wide",
    )
    st.title(t("app_title", lang))
    st.caption(t("app_subtitle", lang))
    st.warning(t("app_prototype_warning", lang))
    try:
        health = api_client.health()
        st.caption(
            f"{t('app_analyzer_label', lang)}: {health.get('active_analyzer')} "
            f"| {health.get('active_analyzer_version')} "
            f"| NLP: {health.get('nlp_model_name') or 'N/A'} "
            f"{health.get('nlp_model_version') or ''}"
        )
        requested = health.get("llm_provider")
        if requested == "deepseek" and health.get("llm_api_configured"):
            st.caption(t("app_deepseek_configured", lang))
        elif requested == "deepseek":
            st.warning(t("app_deepseek_no_key", lang))
        elif requested:
            st.caption(t("app_provider_local_demo", lang))
        if health.get("analyzer_fallback_active"):
            st.warning(t("app_analyzer_fallback", lang))
    except ApiClientError:
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
        )
        new_lang = "en" if t("lang_en", lang) in lang_choice else "zh_CN"
        if new_lang != lang:
            st.session_state["ui_language"] = new_lang
            st.rerun()

        st.markdown("---")
        st.markdown(f"### {t('view_mode', lang)}")
        role = st.radio(
            t("view_mode", lang),
            [t("view_student", lang), t("view_research", lang)],
            horizontal=False,
            key="sidebar_role",
        )
        current_role = "student" if t("view_student", lang) in role else "research"

        st.markdown("---")
        st.markdown(f"### {t('nav_pages', lang)}")
        if current_role == "student":
            page_map = STUDENT_PAGES
        else:
            page_map = RESEARCH_PAGES
        page_labels = {v: k for k, v in page_map.items()}
        selected_label = st.radio(
            t("nav_pages", lang),
            list(page_map.values()),
            key="sidebar_page",
        )
        page_key = page_labels[selected_label]

    return current_role, page_key


def run() -> None:
    api_client = get_api_client(load_settings().api_base_url)
    lang = st.session_state.get("ui_language", "en")

    st.markdown("""
    <style>
        .stApp { max-width: 100%; }
        @media (max-width: 640px) {
            .stApp h1 { font-size: 1.5rem; }
            .stApp h2 { font-size: 1.2rem; }
            .stApp h3 { font-size: 1rem; }
            .stTextArea textarea { font-size: 0.9rem; }
        }
        .stAlert { word-wrap: break-word; overflow-wrap: break-word; }
        .stMarkdown blockquote {
            border-left: 3px solid #4a90d9;
            padding-left: 1rem;
            color: #555;
            font-style: italic;
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            gap: 0.5rem;
        }
    </style>
    """, unsafe_allow_html=True)

    _render_header(api_client, lang)
    role, page_key = _render_sidebar(lang)

    st.markdown("---")

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
