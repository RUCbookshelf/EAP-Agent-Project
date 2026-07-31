"""Reusable UI components for the writing-feedback-mvp Streamlit interface.

All components accept a `lang` parameter for i18n support and use
neutral research language consistent with the project's measurement
boundaries.
"""

from __future__ import annotations

import streamlit as st

from app.ui.locale import t


def page_header(title: str, subtitle: str = "", lang: str = "en") -> None:
    """Render a consistent page header with optional subtitle."""
    st.title(t(title, lang) if not title.startswith(" ") else title.strip())
    if subtitle:
        st.caption(t(subtitle, lang) if not subtitle.startswith(" ") else subtitle.strip())


def status_badge(
    status: str,
    lang: str = "en",
    *,
    success_states: tuple = ("passed", "active", "completed", "success"),
    warning_states: tuple = ("partial", "pending", "candidate", "provisional"),
    error_states: tuple = ("failed", "unavailable", "blocked", "error"),
) -> None:
    """Render a colored status badge with i18n label."""
    label = t(f"status_{status}", lang) if not status.startswith(" ") else status
    if status in success_states:
        st.success(label)
    elif status in warning_states:
        st.warning(label)
    elif status in error_states:
        st.error(label)
    else:
        st.info(label)


def metric_card(
    metric_id: str,
    value: str | None,
    status: str = "unavailable",
    confidence: str = "insufficient",
    unit: str = "legacy",
    version: str = "legacy",
    limitations: list[str] | None = None,
    lang: str = "en",
) -> None:
    """Render a CALF metric card with status, confidence, and limitations."""
    with st.container(border=True):
        st.markdown(f"**{metric_id}**")
        display = value if value is not None else t("metric_unavailable", lang)
        st.write(f"{t('metric_value', lang)}: {display}")

        status_map = {
            "research_metric": "status_research_metric",
            "descriptive_proxy": "status_descriptive_proxy",
            "automatic_candidate": "status_automatic_candidate",
            "manual_annotation_required": "status_manual_annotation_required",
            "unavailable": "status_unavailable",
        }
        status_label = t(status_map.get(status, "status_unavailable"), lang)
        st.caption(
            f"{t('metric_status', lang)}: {status_label}  ·  "
            f"{t('metric_confidence', lang)}: {confidence}  ·  "
            f"{t('metric_unit', lang)}: {unit}  ·  "
            f"{t('metric_version_tag', lang)}: {version}"
        )

        if limitations:
            lim_text = "; ".join(limitations) if isinstance(limitations, list) else str(limitations)
            st.caption(f"{t('metric_limitations', lang)}: {lim_text}")


def evidence_quote(text: str, lang: str = "en") -> None:
    """Display a quoted evidence span from student writing."""
    st.markdown(f"> {text}")


def limitation_notice(text: str, lang: str = "en") -> None:
    """Render a consistent limitation/warning notice."""
    st.warning(f"⚠ {text}")


def empty_state(title: str, explanation: str = "", lang: str = "en") -> None:
    """Render a consistent empty state message."""
    display_title = t(title, lang) if not title.startswith(" ") else title
    display_explanation = t(explanation, lang) if explanation and not explanation.startswith(" ") else explanation
    if display_explanation:
        st.info(f"**{display_title}**\n\n{display_explanation}")
    else:
        st.info(display_title)


def timeline_event(
    event_label: str,
    timestamp: str = "",
    target_code: str = "",
    detail: str = "",
    boundary: str = "",
    lang: str = "en",
) -> None:
    """Render a single timeline event in the Learning Journey."""
    with st.container(border=True):
        st.markdown(f"**{event_label}**")
        parts = []
        if target_code:
            parts.append(f"{t('practice_target', lang)}: {target_code}")
        if timestamp:
            parts.append(timestamp)
        if parts:
            st.caption(" · ".join(parts))
        if detail:
            st.caption(detail)
        if boundary:
            st.warning(boundary)


def audit_record(record_id: str, label: str, data: dict, lang: str = "en") -> None:
    """Render an expandable audit record for research view."""
    with st.expander(f"{record_id} — {label}"):
        st.json(data)


def feedback_priority_card(
    category: str,
    evidence_quote_text: str,
    explanation: str,
    revision_guidance: str,
    practice_link: str | None = None,
    lang: str = "en",
) -> None:
    """Render a student-facing feedback priority card."""
    with st.container(border=True):
        st.markdown(f"**{category.replace('_', ' ').title()}**")
        st.markdown(f"> {evidence_quote_text}")
        st.write(explanation)
        st.write(f"**{t('revision_guidance', lang)}:** {revision_guidance}")
        if practice_link:
            st.caption(f"{t('related_practice', lang)}: {practice_link}")


def section_header(title: str, description: str = "", lang: str = "en") -> None:
    """Render a section header with description."""
    st.subheader(t(title, lang) if not title.startswith(" ") else title)
    if description:
        st.caption(t(description, lang) if not description.startswith(" ") else description)


def card_group_header(title: str, lang: str = "en") -> None:
    """Render a card group header for metric/construct grouping."""
    st.markdown(f"### {t(title, lang) if not title.startswith(' ') else title}")


def warning_box(text: str, lang: str = "en") -> None:
    """Render a consistent warning box for research limitations."""
    st.warning(t(text, lang) if not text.startswith(" ") else text)


def info_box(text: str, lang: str = "en") -> None:
    """Render a consistent info box."""
    st.info(t(text, lang) if not text.startswith(" ") else text)
