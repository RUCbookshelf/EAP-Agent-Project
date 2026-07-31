"""Reusable Pixel Art UI components for the writing-feedback-mvp Streamlit interface.

All components follow the v0.9.2 Pixel Art design system:
- Solid colors, square corners, hard shadows, monospace typography
- No rounded corners, no gradients, no soft shadows, no blur, no transitions
- Immediate state changes; nested cards replaced with flat regions

All components accept a `lang` parameter for i18n support.
"""

from __future__ import annotations

import streamlit as st

from app.ui.locale import t


# ── Page & section headers ──────────────────────────────────────────────────

def page_header(title: str, subtitle: str = "", lang: str = "en") -> None:
    """Render a pixel-art page header with thick bottom border."""
    display_title = t(title, lang) if not title.startswith(" ") else title.strip()
    st.markdown(
        f'<h2 style="font-family:var(--px-font-mono);font-weight:900;color:var(--px-dark);'
        f'border-bottom:4px solid var(--px-dark);padding-bottom:8px;margin-bottom:4px;">'
        f'{display_title}</h2>',
        unsafe_allow_html=True,
    )
    if subtitle:
        display_sub = t(subtitle, lang) if not subtitle.startswith(" ") else subtitle.strip()
        st.caption(display_sub)


def section_header(title: str, description: str = "", lang: str = "en") -> None:
    """Render a pixel-art section header."""
    display_title = t(title, lang) if not title.startswith(" ") else title
    st.markdown(
        f'<h3 style="font-family:var(--px-font-mono);font-weight:700;color:var(--px-dark);'
        f'border-bottom:2px solid var(--px-dark);padding-bottom:4px;margin-top:20px;margin-bottom:8px;">'
        f'{display_title}</h3>',
        unsafe_allow_html=True,
    )
    if description:
        display_desc = t(description, lang) if not description.startswith(" ") else description
        st.caption(display_desc)


def card_group_header(title: str, lang: str = "en") -> None:
    """Render a card group header for metric/construct grouping."""
    display_title = t(title, lang) if not title.startswith(" ") else title
    st.markdown(
        f'<h3 style="font-family:var(--px-font-mono);font-weight:700;color:var(--px-dark);'
        f'margin-top:24px;margin-bottom:8px;">{display_title}</h3>',
        unsafe_allow_html=True,
    )


# ── Status badges ──────────────────────────────────────────────────────────

def status_badge(
    status: str,
    lang: str = "en",
    *,
    success_states: tuple = ("passed", "active", "completed", "success"),
    warning_states: tuple = ("partial", "pending", "candidate", "provisional"),
    error_states: tuple = ("failed", "unavailable", "blocked", "error"),
) -> None:
    """Render a pixel-art status badge with hard border and solid background."""
    label = t(f"status_{status}", lang) if not status.startswith(" ") else status
    if status in success_states:
        color = "var(--px-green)"
        text_color = "var(--px-dark)"
    elif status in warning_states:
        color = "var(--px-yellow)"
        text_color = "var(--px-dark)"
    elif status in error_states:
        color = "var(--px-red)"
        text_color = "var(--px-white)"
    else:
        color = "var(--px-blue)"
        text_color = "var(--px-dark)"
    st.markdown(
        f'<span class="px-badge" style="background:{color};color:{text_color};">{label}</span>',
        unsafe_allow_html=True,
    )


# ── Notices ────────────────────────────────────────────────────────────────

def limitation_notice(text: str, lang: str = "en") -> None:
    """Render a pixel-art limitation notice."""
    display = t(text, lang) if not text.startswith(" ") else text
    st.markdown(
        f'<div class="px-notice px-notice-limitation">{display}</div>',
        unsafe_allow_html=True,
    )


def warning_box(text: str, lang: str = "en") -> None:
    """Render a pixel-art warning box."""
    display = t(text, lang) if not text.startswith(" ") else text
    st.markdown(
        f'<div class="px-notice px-notice-warning">{display}</div>',
        unsafe_allow_html=True,
    )


def info_box(text: str, lang: str = "en") -> None:
    """Render a pixel-art info box."""
    display = t(text, lang) if not text.startswith(" ") else text
    st.markdown(
        f'<div class="px-notice px-notice-info">{display}</div>',
        unsafe_allow_html=True,
    )


def success_box(text: str, lang: str = "en") -> None:
    """Render a pixel-art success notice."""
    display = t(text, lang) if not text.startswith(" ") else text
    st.markdown(
        f'<div class="px-notice px-notice-success">{display}</div>',
        unsafe_allow_html=True,
    )


def error_box(text: str, lang: str = "en") -> None:
    """Render a pixel-art error notice."""
    display = t(text, lang) if not text.startswith(" ") else text
    st.markdown(
        f'<div class="px-notice px-notice-error">{display}</div>',
        unsafe_allow_html=True,
    )


# ── Cards ──────────────────────────────────────────────────────────────────

def pixel_card(content: str, *, interactive: bool = False) -> str:
    """Return HTML for a single pixel-art card.

    Use with st.markdown(..., unsafe_allow_html=True).
    """
    cls = "px-card px-card-interactive" if interactive else "px-card"
    return f'<div class="{cls}">{content}</div>'


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
    """Render a pixel-art CALF metric card."""
    display = value if value is not None else t("metric_unavailable", lang)

    status_map = {
        "research_metric": "status_research_metric",
        "descriptive_proxy": "status_descriptive_proxy",
        "automatic_candidate": "status_automatic_candidate",
        "manual_annotation_required": "status_manual_annotation_required",
        "unavailable": "status_unavailable",
    }
    status_label = t(status_map.get(status, "status_unavailable"), lang)

    # Determine status color
    if status == "unavailable":
        badge_style = f"background:var(--px-surface);color:var(--px-muted);"
    elif status in ("research_metric", "descriptive_proxy"):
        badge_style = f"background:var(--px-green);color:var(--px-dark);"
    else:
        badge_style = f"background:var(--px-yellow);color:var(--px-dark);"

    lim_html = ""
    if limitations:
        lim_text = "; ".join(limitations) if isinstance(limitations, list) else str(limitations)
        lim_html = f'<div style="font-size:0.85rem;margin-top:8px;color:var(--px-muted);">{t("metric_limitations", lang)}: {lim_text}</div>'

    st.markdown(
        f'<div class="px-card">'
        f'<div style="font-weight:700;margin-bottom:4px;">{metric_id}</div>'
        f'<span class="px-badge" style="{badge_style}">{status_label}</span>'
        f'<div style="margin-top:8px;">{t("metric_value", lang)}: <strong>{display}</strong></div>'
        f'<div style="font-size:0.85rem;color:var(--px-muted);margin-top:4px;">'
        f'{t("metric_confidence", lang)}: {confidence} &middot; '
        f'{t("metric_unit", lang)}: {unit} &middot; '
        f'{t("metric_version_tag", lang)}: {version}'
        f'</div>'
        f'{lim_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def feedback_priority_card(
    category: str,
    evidence_quote_text: str,
    explanation: str,
    revision_guidance: str,
    practice_link: str | None = None,
    lang: str = "en",
) -> None:
    """Render a student-facing pixel-art feedback priority card."""
    practice_html = ""
    if practice_link:
        practice_html = f'<div style="font-size:0.85rem;margin-top:8px;">{t("related_practice", lang)}: {practice_link}</div>'

    st.markdown(
        f'<div class="px-card">'
        f'<div style="font-weight:900;font-size:1.1rem;margin-bottom:8px;color:var(--px-red);">'
        f'{category.replace("_", " ").title()}</div>'
        f'<div class="px-quote">{evidence_quote_text}</div>'
        f'<div style="margin-top:8px;">{explanation}</div>'
        f'<div style="margin-top:8px;"><strong>{t("revision_guidance", lang)}:</strong> {revision_guidance}</div>'
        f'{practice_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Evidence & quotes ─────────────────────────────────────────────────────

def evidence_quote(text: str, lang: str = "en") -> None:
    """Display a pixel-art quoted evidence span."""
    st.markdown(
        f'<div class="px-quote">{text}</div>',
        unsafe_allow_html=True,
    )


# ── Empty states ──────────────────────────────────────────────────────────

def empty_state(title: str, explanation: str = "", lang: str = "en") -> None:
    """Render a pixel-art empty state message."""
    display_title = t(title, lang) if not title.startswith(" ") else title
    display_explanation = t(explanation, lang) if explanation and not explanation.startswith(" ") else explanation

    expl_html = f"<br><br>{display_explanation}" if display_explanation else ""
    st.markdown(
        f'<div class="px-empty"><strong>{display_title}</strong>{expl_html}</div>',
        unsafe_allow_html=True,
    )


# ── Timeline ──────────────────────────────────────────────────────────────

def timeline_event(
    event_label: str,
    timestamp: str = "",
    target_code: str = "",
    detail: str = "",
    boundary: str = "",
    lang: str = "en",
) -> None:
    """Render a single pixel-art timeline event."""
    parts = []
    if target_code:
        parts.append(f"{t('practice_target', lang)}: {target_code}")
    if timestamp:
        parts.append(timestamp)
    meta = " &middot; ".join(parts) if parts else ""

    boundary_html = ""
    if boundary:
        boundary_html = f'<div class="px-notice px-notice-warning" style="margin-top:4px;">{boundary}</div>'

    detail_html = f'<div style="font-size:0.85rem;color:var(--px-muted);">{detail}</div>' if detail else ""

    st.markdown(
        f'<div class="px-timeline-node">'
        f'<div class="px-timeline-marker"></div>'
        f'<div class="px-timeline-content">'
        f'<div style="font-weight:700;">{event_label}</div>'
        f'<div style="font-size:0.85rem;color:var(--px-muted);">{meta}</div>'
        f'{detail_html}'
        f'{boundary_html}'
        f'</div></div>',
        unsafe_allow_html=True,
    )


# ── Audit ─────────────────────────────────────────────────────────────────

def audit_record(record_id: str, label: str, data: dict, lang: str = "en") -> None:
    """Render a pixel-art expandable audit record."""
    with st.expander(f"{record_id} \u2014 {label}"):
        st.json(data)


# ── Table wrapper ─────────────────────────────────────────────────────────

def table_container(content_html: str) -> None:
    """Wrap table content in a pixel-art scrollable container."""
    st.markdown(
        f'<div class="px-table-wrap">{content_html}</div>',
        unsafe_allow_html=True,
    )


# ── Divider ───────────────────────────────────────────────────────────────

def divider() -> None:
    """Render a pixel-art divider."""
    st.markdown('<hr class="px-divider">', unsafe_allow_html=True)
def render_api_error(exc, lang: str = "en", *, research: bool = False) -> None:
    """Role-appropriate error presentation for classified API errors."""
    from app.ui.api_client import ApiClientError

    if not isinstance(exc, ApiClientError):
        st.error(t("error_unknown", lang))
        return

    message = t(exc.message_key, lang)
    if exc.operation:
        message += " " + t("error_operation_suffix", lang, operation=exc.operation.replace("_", " "))

    if research:
        detail_lines = [
            f"{t('error_category_label', lang)}: {exc.category.value}",
            f"{t('error_operation_label', lang)}: {exc.operation or '-'}",
            f"{t('error_request_id_label', lang)}: {exc.request_id or '-'}",
            f"{t('error_http_status_label', lang)}: {exc.http_status or '-'}",
            f"{t('error_retryable_label', lang)}: {'Yes' if exc.retryable else 'No'}",
        ]
        if exc.detail:
            detail_lines.append(f"{t('error_detail_label', lang)}: {exc.detail}")
        st.markdown(
            f'<div class="px-notice px-notice-error">'
            f'<strong>{message}</strong><br>'
            f'<span style="font-size:0.85rem;color:var(--px-white);">{"<br>".join(detail_lines)}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="px-notice px-notice-error"><strong>{message}</strong></div>',
            unsafe_allow_html=True,
        )

    if exc.retryable:
        if st.button(t("error_retry_action", lang), key=f"retry_{exc.operation or 'action'}_{lang}"):
            st.rerun()
