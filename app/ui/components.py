"""Reusable Hybrid Pixel System 2.0 UI components (v0.9.4-A).

All components follow the canonical token contract in
`app/ui/pixel_art.py` (`DESIGN_TOKENS`) and reference tokens only — no
literal colors, font stacks, spacing values, border rules, or shadow rules
are duplicated here.

Rules:
- Solid colors, square corners, hard shadows; no gradients, blur, soft
  shadows, or motion.
- Body prose is sans; technical values (IDs, versions, status codes,
  metrics) use the shared monospace role class.
- Components own stable `data-testid` attributes for browser verification.
- All components accept a `lang` parameter for i18n support.
"""

from __future__ import annotations

import streamlit as st

from app.ui.locale import t
from app.ui.pixel_art import icon


# ── Page & section headers ──────────────────────────────────────────────────

def page_header(title: str, subtitle: str = "", lang: str = "en") -> None:
    """Render a pixel-art page header with thick bottom border."""
    display_title = t(title, lang) if not title.startswith(" ") else title.strip()
    st.markdown(
        f'<h2 class="px-page-heading">'
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
        f'<h3 class="px-section-heading">'
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
        f'<h3 class="px-section-heading">{display_title}</h3>',
        unsafe_allow_html=True,
    )


# ── Student page structure ───────────────────────────────────────────────

def student_page_intro(title: str, purpose: str, lang: str = "en") -> None:
    """Mark a Student page and place its single purpose directly below the title."""
    import html as _html

    page_header(title, lang=lang)
    display = t(purpose, lang) if not purpose.startswith(" ") else purpose.strip()
    st.markdown(
        f'<div class="px-student-purpose" data-testid="px-student-page" '
        f'data-role="student"><p>{_html.escape(display)}</p></div>',
        unsafe_allow_html=True,
    )


def student_task_steps(steps: list[str], current: int, lang: str = "en") -> None:
    """Render a compact, text-labelled Student task sequence."""
    import html as _html

    items = []
    for index, step in enumerate(steps):
        state = "complete" if index < current else "current" if index == current else "upcoming"
        state_label = t(f"student_step_{state}", lang)
        display = t(step, lang) if not step.startswith(" ") else step.strip()
        items.append(
            f'<li data-state="{state}"><span class="px-student-step-number">{index + 1}</span>'
            f'<span class="px-student-step-copy"><strong>{_html.escape(display)}</strong>'
            f'<span>{_html.escape(state_label)}</span></span></li>'
        )
    st.markdown(
        f'<ol class="px-student-steps" data-testid="px-student-steps">{"".join(items)}</ol>',
        unsafe_allow_html=True,
    )


def student_action_block(
    title: str,
    description: str,
    lang: str = "en",
    *,
    state: str = "ready",
) -> None:
    """Introduce the page's one primary action or accurate no-action state."""
    import html as _html

    display_title = t(title, lang) if not title.startswith(" ") else title.strip()
    display_description = (
        t(description, lang) if not description.startswith(" ") else description.strip()
    )
    st.markdown(
        f'<div class="px-student-action" data-testid="px-student-primary-action" '
        f'data-state="{_html.escape(state)}"><strong>{_html.escape(display_title)}</strong>'
        f'<p>{_html.escape(display_description)}</p></div>',
        unsafe_allow_html=True,
    )


def student_context_block(items: list[tuple[str, object]], lang: str = "en") -> None:
    """Render compact learner/task context with safe, readable values."""
    import html as _html

    rows = []
    for label, value in items:
        display_label = t(label, lang) if not label.startswith(" ") else label.strip()
        rows.append(
            f'<div><dt>{_html.escape(display_label)}</dt>'
            f'<dd>{_html.escape(str(value))}</dd></div>'
        )
    st.markdown(
        f'<dl class="px-student-context" data-testid="px-student-context">'
        f'{"".join(rows)}</dl>',
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
    neutral_states: tuple = ("insufficient", "legacy", "unlinked", "unresolved"),
    icon_name: str | None = None,
) -> None:
    """Render a quiet state badge with icon and localized label (v0.9.7-D).

    Never color-alone: the badge always pairs a local SVG icon with the
    localized status label. ``status`` may be a locale key (``status_*``)
    or a raw label prefixed with a space (existing convention).
    """
    st.markdown(
        status_badge_html(
            status,
            lang,
            success_states=success_states,
            warning_states=warning_states,
            error_states=error_states,
            neutral_states=neutral_states,
            icon_name=icon_name,
        ),
        unsafe_allow_html=True,
    )


def status_badge_html(
    status: str,
    lang: str = "en",
    *,
    success_states: tuple = ("passed", "active", "completed", "success"),
    warning_states: tuple = ("partial", "pending", "candidate", "provisional"),
    error_states: tuple = ("failed", "unavailable", "blocked", "error"),
    neutral_states: tuple = ("insufficient", "legacy", "unlinked", "unresolved"),
    icon_name: str | None = None,
    state: str | None = None,
) -> str:
    """Return the status-badge HTML fragment (shared by ``status_badge``
    and composite components that embed badges inside their own markup)."""
    import html as _html

    label = t(f"status_{status}", lang) if not status.startswith(" ") else status
    if state is None:
        if status in success_states:
            state = "success"
        elif status in warning_states:
            state = "warning"
        elif status in error_states:
            state = "error"
        elif status in neutral_states:
            state = "neutral"
        else:
            state = "info"
    icon_name = icon_name or {
        "success": "check",
        "warning": "warning",
        "error": "error",
        "neutral": "info",
        "info": "info",
    }[state]
    return (
        f'<span class="px-status-badge" data-testid="px-status-badge" '
        f'data-state="{state}">{icon(icon_name, size=14, label=str(label))}'
        f'{_html.escape(str(label))}</span>'
    )


# ── Notices ────────────────────────────────────────────────────────────────

def limitation_notice(text: str, lang: str = "en") -> None:
    """Render a pixel-art limitation notice."""
    notice(text, lang, state="limitation", icon_name="info",
           icon_label_key="notice_limitation_icon")


def warning_box(text: str, lang: str = "en") -> None:
    """Render a pixel-art warning box."""
    notice(text, lang, state="warning", icon_name="warning",
           icon_label_key="notice_warning_icon")


def info_box(text: str, lang: str = "en") -> None:
    """Render a pixel-art info box."""
    notice(text, lang, state="info", icon_name="info",
           icon_label_key="notice_info_icon")


def success_box(text: str, lang: str = "en") -> None:
    """Render a pixel-art success notice."""
    notice(text, lang, state="success", icon_name="check",
           icon_label_key="notice_success_icon")


def error_box(text: str, lang: str = "en") -> None:
    """Render a pixel-art error notice."""
    notice(text, lang, state="error", icon_name="error",
           icon_label_key="notice_error_icon")


def neutral_box(text: str, lang: str = "en", *, dashed: bool = False) -> None:
    """Render a quiet neutral state box (unavailable/legacy outcomes)."""
    display = t(text, lang) if not text.startswith(" ") else text
    cls = "px-notice px-notice-limitation"
    if dashed:
        cls = "px-notice px-notice-dashed"
    st.markdown(
        f'<div class="{cls}" data-testid="px-notice">'
        f'{icon("info", size=18, label=t("notice_info_icon", lang))}{display}</div>',
        unsafe_allow_html=True,
    )


def notice(
    text: str,
    lang: str = "en",
    *,
    state: str = "info",
    icon_name: str = "info",
    icon_label_key: str = "notice_info_icon",
) -> None:
    """Shared quiet notice core (v0.9.7-D): tint + accent bar + icon + text."""
    import html as _html

    display = t(text, lang) if not text.startswith(" ") else text
    variant = {
        "success": "px-notice-success",
        "warning": "px-notice-warning",
        "error": "px-notice-error",
        "limitation": "px-notice-limitation",
    }.get(state, "px-notice-info")
    st.markdown(
        f'<div class="px-notice {variant}" data-testid="px-notice">'
        f'{icon(icon_name, size=18, label=t(icon_label_key, lang))}{display}</div>',
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
        badge_style = f"background:var(--px-status-unavailable);color:var(--px-status-on-unavailable);"
    elif status in ("research_metric", "descriptive_proxy"):
        badge_style = f"background:var(--px-status-success);color:var(--px-status-on-success);"
    else:
        badge_style = f"background:var(--px-status-candidate);color:var(--px-status-on-warning);"

    lim_html = ""
    if limitations:
        lim_text = "; ".join(limitations) if isinstance(limitations, list) else str(limitations)
        lim_html = f'<div style="font-size:0.85rem;margin-top:8px;color:var(--px-muted);">{t("metric_limitations", lang)}: {lim_text}</div>'

    st.markdown(
        f'<div class="px-card">'
        f'<div style="font-weight:700;margin-bottom:4px;">{metric_id}</div>'
        f'<span class="px-badge" data-testid="px-status-badge" style="{badge_style}">{status_label}</span>'
        f'<div style="margin-top:8px;">{t("metric_value", lang)}: '
        f'<strong class="px-mono" data-testid="px-mono">{display}</strong></div>'
        f'<div class="px-mono" data-testid="px-mono" style="font-size:0.85rem;color:var(--px-muted);margin-top:4px;">'
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
    evidence_html = (
        f'<div class="px-quote">{evidence_quote_text}</div>'
        if evidence_quote_text
        else ""
    )

    st.markdown(
        f'<div class="px-card" data-testid="px-feedback-priority">'
        f'<div style="font-weight:900;font-size:1.1rem;margin-bottom:8px;color:var(--px-action);">'
        f'{category.replace("_", " ").title()}</div>'
        f'{evidence_html}'
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
        f'<div class="px-empty" data-testid="px-empty-state">'
        f'{icon("empty", size=24, label=t("empty_state_icon", lang))}'
        f'<strong>{display_title}</strong>{expl_html}</div>',
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
    source_label: str = "",
    evidence_status: str = "",
) -> None:
    """Render one Journey event with distinct activity, evidence, source, and limit."""
    import html as _html

    source = source_label or target_code
    time_html = (
        f'<div data-testid="px-journey-time"><strong>{_html.escape(t("student_journey_event_time", lang))}:</strong> '
        f'{_html.escape(timestamp)}</div>' if timestamp else ""
    )
    evidence_html = (
        f'<div data-testid="px-journey-evidence"><strong>{_html.escape(t("student_journey_event_evidence", lang))}:</strong> '
        f'{_html.escape(evidence_status)}</div>' if evidence_status else ""
    )
    source_html = (
        f'<div class="px-mono" data-testid="px-journey-source"><strong>{_html.escape(t("student_journey_event_source", lang))}:</strong> '
        f'{_html.escape(source)}</div>' if source else ""
    )
    detail_html = (
        f'<div data-testid="px-journey-detail" style="font-size:0.9rem;color:var(--px-muted);">'
        f'{_html.escape(detail)}</div>' if detail else ""
    )
    boundary_html = (
        f'<div class="px-notice px-notice-warning" data-testid="px-journey-limitation" '
        f'style="margin-top:8px;">{_html.escape(boundary)}</div>' if boundary else ""
    )
    st.markdown(
        f'<div class="px-timeline-node" data-testid="px-timeline-event">'
        f'<div class="px-timeline-marker"></div>'
        f'<div class="px-timeline-content">'
        f'<div data-testid="px-journey-label" style="font-weight:700;">{_html.escape(event_label)}</div>'
        f'{time_html}{detail_html}{evidence_html}{source_html}{boundary_html}'
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
        f'<div class="px-table-wrap" data-testid="px-table-wrap">{content_html}</div>',
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
            f'<div class="px-notice px-notice-error" data-testid="px-notice">'
            f'<strong>{message}</strong><br>'
            f'<span class="px-mono" data-testid="px-mono" style="font-size:0.85rem;color:var(--px-white);">'
            f'{"<br>".join(detail_lines)}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="px-notice px-notice-error" data-testid="px-notice"><strong>{message}</strong></div>',
            unsafe_allow_html=True,
        )

    if exc.retryable:
        if st.button(t("error_retry_action", lang), key=f"retry_{exc.operation or 'action'}_{lang}"):
            st.rerun()


# ── v0.9.4-A shared primitives ─────────────────────────────────────────

def field_error(message: str, lang: str = "en") -> None:
    """Render a localized inline field-validation error."""
    display = t(message, lang) if not message.startswith(" ") else message
    st.markdown(
        f'<div class="px-field-error" data-testid="px-field-error" role="alert">'
        f'{icon("error", size=16, label=t("field_error_icon", lang))}{display}</div>',
        unsafe_allow_html=True,
    )


def loading_box(text: str, lang: str = "en") -> None:
    """Render a localized loading state (no animation; text + icon)."""
    display = t(text, lang) if not text.startswith(" ") else text
    st.markdown(
        f'<div class="px-loading" data-testid="px-loading" role="status" '
        f'aria-live="polite">{icon("clock", size=18, label=t("loading_icon", lang))}{display}</div>',
        unsafe_allow_html=True,
    )


def data_table(
    headers: list[str],
    rows: list[list[object]],
    *,
    density: str = "research",
) -> None:
    """Render a compact pixel-art table with stable testids.

    Headers and cell values are rendered as text; HTML is escaped so data
    values can never inject markup. `density` is reserved for the role
    density tokens (research = default; student variant deferred).
    """
    import html as _html

    thead = "".join(f"<th>{_html.escape(str(h))}</th>" for h in headers)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{_html.escape(str(c))}</td>" for c in row)
        body_rows.append(f"<tr>{cells}</tr>")
    table_html = (
        f'<table data-testid="px-table">'
        f'<thead><tr>{thead}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>'
        f'</table>'
    )
    st.markdown(
        f'<div class="px-table-wrap" data-testid="px-table-wrap" '
        f'data-density="{density}">{table_html}</div>',
        unsafe_allow_html=True,
    )


def technical_caption(text: str) -> None:
    """Render a technical caption (IDs, versions, status codes) in mono."""
    st.markdown(
        f'<div class="px-mono" data-testid="px-mono" '
        f'style="font-size:var(--px-font-size-label);color:var(--px-muted);">{text}</div>',
        unsafe_allow_html=True,
    )


def validate_writing_form(
    student_id: str,
    writing_prompt: str,
    essay_text: str,
    *,
    is_revision: bool = False,
    revision_of_submission_id: int | None = None,
) -> list[str]:
    """Pure Writing-form validation; returns locale message keys.

    Keeps server-side validation and API schemas unchanged: this helper
    only blocks clearly invalid UI submissions before the API call.
    """
    errors: list[str] = []
    if not student_id.strip():
        errors.append("student_writing_need_id")
    if not writing_prompt.strip():
        errors.append("student_writing_need_prompt")
    if not essay_text.strip():
        errors.append("student_writing_need_text")
    if is_revision and revision_of_submission_id is None:
        errors.append("submission_choose_revision")
    return errors
