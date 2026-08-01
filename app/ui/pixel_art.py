"""Hybrid Pixel System 2.0 design foundation for the writing-feedback-mvp UI.

This module is the SINGLE canonical design-token source for v0.9.4-A.

- `DESIGN_TOKENS` is the one canonical token contract (colors, semantic
  states, typography, spacing, geometry, density, responsive, motion).
- `PIXEL_CSS` and `PIXEL_COMPONENT_CSS` are generated from that contract,
  so resolved values exist in exactly one Python location.
- `.streamlit/config.toml` repeats only the Streamlit-required theme keys;
  a parity test keeps those values aligned with `DESIGN_TOKENS`.

Identity rules (preserved from Pixel Art v0.9.2):
- Solid colors only: no gradients, no blur, no glassmorphism, no soft
  shadows, no decorative depth effects.
- Square corners (radius 0), hard offset shadows, immediate states.
- Motion is disabled: zero-duration transitions, no animation, and the
  `prefers-reduced-motion` protection is preserved.

Approved v0.9.4-A changes:
- Body prose, navigation, forms, feedback, evidence descriptions, and
  Chinese text use a readable local/system sans stack.
- Monospace is constrained to technical/brand roles (IDs, versions, status
  codes, metrics, code-like values, selected headings).
- The primary action red is darkened to `#e00047` (measured 4.93:1 on
  white); `#ff004d` remains only as a decorative non-text accent.
"""

from __future__ import annotations

import html

import streamlit as st


# ══════════════════════════════════════════════════════════════════════
# 1. Canonical design-token contract (single source of truth)
# ══════════════════════════════════════════════════════════════════════

DESIGN_TOKENS = {
    "version": "hybrid-pixel-system-2.0-v0.9.4-a",
    # ── Foundational colors ────────────────────────────────────────────
    "colors": {
        "dark": "#1a1c2c",          # borders, headings, structural
        "white": "#ffffff",         # application background, cards
        "bg": "#ffffff",            # application background alias
        "surface": "#f4f4f4",       # secondary surface, sidebar
        "text": "#1a1c2c",          # primary text
        "text-secondary": "#4a4a58",
        "muted": "#6b6b7b",
        "border": "#1a1c2c",
        "focus": "#29adff",         # focus outline (non-text indicator)
        "action": "#e00047",        # primary action red (AA measured)
        "action-hover": "#e00047",
        "action-active": "#e00047",
        "action-disabled": "#e8e8ec",
        "action-text": "#ffffff",
        "action-text-disabled": "#5a5a68",
        "secondary-action": "#f4f4f4",
        "link": "#0f6dbd",
        "pixel-red": "#ff004d",     # decorative accent only (non-text)
    },
    # ── Semantic status states (never color-alone) ─────────────────────
    "semantic": {
        "success": "#00e436",
        "warning": "#ffec27",
        "error": "#e00047",
        "info": "#29adff",
        "unavailable": "#f4f4f4",
        "candidate": "#ffec27",
        "insufficient": "#f4f4f4",
        "selected": "#29adff",
        "neutral": "#f4f4f4",
        "on-success": "#1a1c2c",
        "on-warning": "#1a1c2c",
        "on-error": "#ffffff",
        "on-info": "#1a1c2c",
        "on-unavailable": "#6b6b7b",
        "on-insufficient": "#6b6b7b",
        "on-neutral": "#1a1c2c",
    },
    # ── Typography ─────────────────────────────────────────────────────
    "typography": {
        "font-body": (
            "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', "
            "'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', "
            "'Helvetica Neue', Arial, sans-serif"
        ),
        "font-mono": (
            "ui-monospace, 'Cascadia Mono', 'Cascadia Code', Consolas, "
            "SFMono-Regular, Menlo, Monaco, 'Liberation Mono', "
            "'Courier New', monospace"
        ),
        "size-h1": "2rem",
        "size-h2": "1.625rem",
        "size-h3": "1.25rem",
        "size-body": "1rem",
        "size-compact": "0.875rem",
        "size-label": "0.8125rem",
        "size-metric": "1.125rem",
        "weight-heavy": "900",
        "weight-bold": "700",
        "weight-normal": "400",
        "line-height-body": "1.6",
        "line-height-compact": "1.5",
    },
    # ── Spacing scale ──────────────────────────────────────────────────
    "spacing": {
        "1": "4px", "2": "8px", "3": "12px", "4": "16px", "5": "20px",
        "6": "24px", "8": "32px", "10": "40px", "12": "48px",
        "inline-gap": "8px",
        "control-gap": "8px",
        "card-pad": "16px",
        "section-space": "32px",
        "page-space": "40px",
    },
    # ── Geometry ───────────────────────────────────────────────────────
    "geometry": {
        "border-thick": "4px",
        "border-thin": "2px",
        "border-hairline": "1px",
        "radius": "0px",
        "focus-width": "3px",
        "focus-offset": "2px",
        "shadow-sm-offset": "2px",
        "shadow-md-offset": "4px",
        "shadow-lg-offset": "8px",
        "control-height": "40px",
        "control-height-mobile": "44px",
        "touch-target": "44px",
        "content-width-student": "720px",
        "content-width-research": "1200px",
        "table-font-size": "0.8125rem",
        "table-cell-pad": "6px",
    },
    # ── Role density aliases ───────────────────────────────────────────
    "density": {
        "student-section": "var(--px-space-8)",
        "research-section": "var(--px-space-4)",
        "student-card-pad": "var(--px-space-5)",
        "research-card-pad": "var(--px-space-3)",
    },
    # ── Responsive foundation (reuse validated breakpoints) ───────────
    "responsive": {
        "bp-mobile": "640px",
        "bp-tablet": "1024px",
    },
    # ── Motion (deferred / disabled) ───────────────────────────────────
    "motion": {
        "transition": "none",
        "animation": "none",
    },
}


def _v(path: str) -> str:
    """Resolve a dotted path inside DESIGN_TOKENS."""
    node: object = DESIGN_TOKENS
    for part in path.split("."):
        node = node[part]  # type: ignore[index]
    return str(node)


def build_css_vars() -> dict[str, str]:
    """Flatten DESIGN_TOKENS into `--px-*` custom properties."""
    c = DESIGN_TOKENS["colors"]
    s = DESIGN_TOKENS["semantic"]
    t = DESIGN_TOKENS["typography"]
    sp = DESIGN_TOKENS["spacing"]
    g = DESIGN_TOKENS["geometry"]
    d = DESIGN_TOKENS["density"]
    r = DESIGN_TOKENS["responsive"]
    m = DESIGN_TOKENS["motion"]
    dark = c["dark"]
    return {
        # Colors
        "--px-dark": c["dark"],
        "--px-white": c["white"],
        "--px-bg": c["bg"],
        "--px-surface": c["surface"],
        "--px-surface-elevated": c["white"],
        "--px-text": c["text"],
        "--px-text-secondary": c["text-secondary"],
        "--px-muted": c["muted"],
        "--px-border": c["border"],
        "--px-focus": c["focus"],
        "--px-action": c["action"],
        "--px-action-hover": c["action-hover"],
        "--px-action-active": c["action-active"],
        "--px-action-disabled": c["action-disabled"],
        "--px-action-text": c["action-text"],
        "--px-action-text-disabled": c["action-text-disabled"],
        "--px-secondary-action": c["secondary-action"],
        "--px-link": c["link"],
        "--px-red": c["pixel-red"],          # decorative accent only
        # Semantic states
        "--px-status-success": s["success"],
        "--px-status-warning": s["warning"],
        "--px-status-error": s["error"],
        "--px-status-info": s["info"],
        "--px-status-unavailable": s["unavailable"],
        "--px-status-candidate": s["candidate"],
        "--px-status-insufficient": s["insufficient"],
        "--px-status-selected": s["selected"],
        "--px-status-neutral": s["neutral"],
        "--px-status-on-success": s["on-success"],
        "--px-status-on-warning": s["on-warning"],
        "--px-status-on-error": s["on-error"],
        "--px-status-on-info": s["on-info"],
        "--px-status-on-unavailable": s["on-unavailable"],
        "--px-status-on-insufficient": s["on-insufficient"],
        "--px-status-on-neutral": s["on-neutral"],
        # Typography
        "--px-font-body": t["font-body"],
        "--px-font-mono": t["font-mono"],
        "--px-font-heading": f"var(--px-font-mono)",
        "--px-font-size-h1": t["size-h1"],
        "--px-font-size-h2": t["size-h2"],
        "--px-font-size-h3": t["size-h3"],
        "--px-font-size-body": t["size-body"],
        "--px-font-size-compact": t["size-compact"],
        "--px-font-size-label": t["size-label"],
        "--px-font-size-metric": t["size-metric"],
        "--px-font-weight-heavy": t["weight-heavy"],
        "--px-font-weight-bold": t["weight-bold"],
        "--px-font-weight-normal": t["weight-normal"],
        "--px-line-height": t["line-height-body"],
        "--px-line-height-body": t["line-height-body"],
        "--px-line-height-compact": t["line-height-compact"],
        # Spacing
        "--px-space-1": sp["1"],
        "--px-space-2": sp["2"],
        "--px-space-3": sp["3"],
        "--px-space-4": sp["4"],
        "--px-space-5": sp["5"],
        "--px-space-6": sp["6"],
        "--px-space-8": sp["8"],
        "--px-space-10": sp["10"],
        "--px-space-12": sp["12"],
        "--px-inline-gap": sp["inline-gap"],
        "--px-control-gap": sp["control-gap"],
        "--px-card-pad": sp["card-pad"],
        "--px-section-space": sp["section-space"],
        "--px-page-space": sp["page-space"],
        # Geometry
        "--px-border-thick": f"{g['border-thick']} solid {dark}",
        "--px-border-thin": f"{g['border-thin']} solid {dark}",
        "--px-border-hairline": f"{g['border-hairline']} solid {dark}",
        "--px-radius": g["radius"],
        "--px-transition": m["transition"],
        "--px-animation": m["animation"],
        "--px-focus-width": g["focus-width"],
        "--px-focus-offset": g["focus-offset"],
        "--px-shadow-sm": f"{g['shadow-sm-offset']} {g['shadow-sm-offset']} 0 {dark}",
        "--px-shadow-md": f"{g['shadow-md-offset']} {g['shadow-md-offset']} 0 {dark}",
        "--px-shadow-lg": f"{g['shadow-lg-offset']} {g['shadow-lg-offset']} 0 {dark}",
        "--px-control-height": g["control-height"],
        "--px-control-height-mobile": g["control-height-mobile"],
        "--px-touch-target": g["touch-target"],
        "--px-content-width-student": g["content-width-student"],
        "--px-content-width-research": g["content-width-research"],
        "--px-table-font-size": g["table-font-size"],
        "--px-table-cell-pad": g["table-cell-pad"],
        # Role density aliases
        "--px-density-student-section": d["student-section"],
        "--px-density-research-section": d["research-section"],
        "--px-density-student-card-pad": d["student-card-pad"],
        "--px-density-research-card-pad": d["research-card-pad"],
        # Responsive aliases
        "--px-bp-mobile": r["bp-mobile"],
        "--px-bp-tablet": r["bp-tablet"],
    }


def build_root_css() -> str:
    """Generate the :root custom-property block from the canonical tokens."""
    pairs = [f"    {name}: {value};" for name, value in build_css_vars().items()]
    return ":root {\n" + "\n".join(pairs) + "\n}"


# Backward-compatible color map (decorative red remains #ff004d).
PIXEL_COLORS = {
    "dark": _v("colors.dark"),
    "white": _v("colors.white"),
    "surface": _v("colors.surface"),
    "red": _v("colors.pixel-red"),
    "green": _v("semantic.success"),
    "blue": _v("semantic.info"),
    "yellow": _v("semantic.warning"),
    "text": _v("colors.text"),
    "muted": _v("colors.muted"),
    "disabled_bg": _v("colors.action-disabled"),
    "action": _v("colors.action"),
}


# ══════════════════════════════════════════════════════════════════════
# 2. Global CSS (generated tokens + documented stable selectors)
# ══════════════════════════════════════════════════════════════════════

def build_pixel_css() -> str:
    """Global Hybrid Pixel System CSS.

    Selector policy: only stable Streamlit `data-testid` selectors and the
    documented stable `.st*` classes; never generated hashed classes.
    Every `!important` is scoped to the pixel-identity override layer and
    is covered by the style audit and browser computed-style checks.
    """
    return f"""
<style>
{build_root_css()}

/* ── Application shell ─────────────────────────────────────────────── */
.stApp {{
    background-color: var(--px-bg);
    font-family: var(--px-font-body);
    color: var(--px-text);
}}

/* Square corners everywhere (pixel identity; scoped !important) */
.stApp * {{
    border-radius: 0 !important;
}}

/* ── Typography roles ──────────────────────────────────────────────── */
/* Body prose, navigation, forms, feedback, evidence, Chinese text: sans */
.stApp p, .stApp li, .stApp label, .stApp caption, .stApp span,
.stApp div, .stApp a {{
    font-family: var(--px-font-body);
    color: var(--px-text);
    line-height: var(--px-line-height-body);
}}

/* Headings keep the pixel/mono brand accent */
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {{
    font-family: var(--px-font-heading);
    color: var(--px-dark);
    line-height: 1.25;
}}
.stApp h1 {{ font-size: var(--px-font-size-h1); font-weight: var(--px-font-weight-heavy); }}
.stApp h2 {{ font-size: var(--px-font-size-h2); font-weight: var(--px-font-weight-bold); }}
.stApp h3 {{ font-size: var(--px-font-size-h3); font-weight: var(--px-font-weight-bold); }}

/* Technical roles stay monospace: code-like values, IDs, metrics,
   status codes, badges, tables, and .px-mono / [data-testid="px-mono"] */
.stApp code, .stApp kbd, .stApp samp, .stApp pre,
.px-badge, .px-table-wrap table,
div[data-testid="stMetricValue"],
.px-mono, [data-testid="px-mono"] {{
    font-family: var(--px-font-mono) !important;
}}

/* ── Remove Streamlit rounded corners (scoped !important) ──────────── */
div[data-testid="stVerticalBlock"] > div,
div[data-testid="stHorizontalBlock"] > div,
.stTextInput > div > div > input,
[data-testid="stTextArea"] textarea,
.stSelectbox > div > div,
.stMultiSelect > div > div,
.stNumberInput > div > div > input,
[data-testid^="stBaseButton"],
[data-testid="stDownloadButton"],
.stCheckbox > label > div,
[data-testid="stRadioGroup"],
[role="tab"],
div[data-testid="stSidebar"],
div[data-testid="stExpander"],
div[data-testid="stTabs"],
div[data-testid="stNotification"],
.stAlert,
div[data-baseweb="select"] > div,
div[data-baseweb="popover"],
div[data-baseweb="menu"],
div[data-baseweb="modal"],
div[data-baseweb="tooltip"] {{
    border-radius: 0 !important;
}}

/* ── Motion is disabled (v0.9.4-A: no decorative animation, no
   non-zero transition; reduced-motion block preserved below) ──────── */
.stApp *, .stApp *::before, .stApp *::after {{
    transition: none !important;
    animation: none !important;
}}

/* ── Remove soft shadows; hard pixel shadows only (scoped !important) */
.stApp button,
div[data-testid="stExpander"],
.stAlert,
div[data-testid="stSidebar"],
div[data-testid="stTabs"] {{
    box-shadow: none !important;
}}

/* ── Buttons: primary = AA action red; secondary = surface ─────────── */
[data-testid="stBaseButton-primary"],
button[kind="primary"] {{
    background-color: var(--px-action) !important;
    color: var(--px-action-text) !important;
    border: var(--px-border-thick) !important;
    box-shadow: var(--px-shadow-md) !important;
    min-height: var(--px-control-height) !important;
    font-family: var(--px-font-body) !important;
    font-weight: var(--px-font-weight-bold) !important;
}}
[data-testid="stBaseButton-primary"]:hover,
button[kind="primary"]:hover {{
    background-color: var(--px-action-hover) !important;
    box-shadow: var(--px-shadow-sm) !important;
    transform: translate(2px, 2px) !important;
}}
[data-testid="stBaseButton-primary"]:active,
button[kind="primary"]:active {{
    background-color: var(--px-action-active) !important;
    box-shadow: none !important;
    transform: translate(4px, 4px) !important;
}}
[data-testid="stBaseButton-primary"]:disabled,
button[kind="primary"]:disabled {{
    background-color: var(--px-action-disabled) !important;
    color: var(--px-action-text-disabled) !important;
    box-shadow: none !important;
}}

[data-testid="stBaseButton-secondary"],
button[kind="secondary"],
[data-testid="stDownloadButton"] {{
    background-color: var(--px-secondary-action) !important;
    color: var(--px-text) !important;
    border: var(--px-border-thick) !important;
    box-shadow: var(--px-shadow-md) !important;
    min-height: var(--px-control-height) !important;
    font-family: var(--px-font-body) !important;
}}
[data-testid="stBaseButton-secondary"]:hover,
button[kind="secondary"]:hover {{
    box-shadow: var(--px-shadow-sm) !important;
    transform: translate(2px, 2px) !important;
}}
[data-testid="stBaseButton-secondary"]:active,
button[kind="secondary"]:active {{
    box-shadow: none !important;
    transform: translate(4px, 4px) !important;
}}
[data-testid="stBaseButton-secondary"]:disabled,
button[kind="secondary"]:disabled {{
    background-color: var(--px-action-disabled) !important;
    color: var(--px-action-text-disabled) !important;
    box-shadow: none !important;
}}

/* Visible keyboard focus (3px blue, 2px offset) */
[data-testid^="stBaseButton"]:focus-visible,
[data-testid="stDownloadButton"]:focus-visible,
.stTextInput > div > div > input:focus-visible,
[data-testid="stTextArea"] textarea:focus-visible,
.stSelectbox > div > div:focus-within,
.stNumberInput > div > div > input:focus-visible,
[data-testid="stRadioGroup"] label:focus-within,
.stCheckbox > label:focus-within {{
    outline: var(--px-focus-width) solid var(--px-focus) !important;
    outline-offset: var(--px-focus-offset) !important;
    box-shadow: none !important;
}}

/* ── Form controls: square, 4px borders, readable sans ─────────────── */
.stTextInput > div > div > input,
[data-testid="stTextArea"] textarea,
.stSelectbox > div > div > div,
.stNumberInput > div > div > input {{
    border: var(--px-border-thick) !important;
    background-color: var(--px-white) !important;
    color: var(--px-text) !important;
    font-family: var(--px-font-body) !important;
    min-height: var(--px-control-height) !important;
}}
.stTextInput > div > div > input:focus,
[data-testid="stTextArea"] textarea:focus,
.stSelectbox > div > div > div:focus,
.stNumberInput > div > div > input:focus {{
    outline: var(--px-focus-width) solid var(--px-focus) !important;
    outline-offset: var(--px-focus-offset) !important;
    box-shadow: none !important;
}}

/* ── Expanders / tabs / sidebar ────────────────────────────────────── */
div[data-testid="stExpander"] {{
    border: var(--px-border-thick) !important;
    background-color: var(--px-white) !important;
}}
div[data-testid="stTabs"] {{
    font-family: var(--px-font-body);
}}
[role="tab"] {{
    font-family: var(--px-font-body) !important;
    border: none !important;
    border-bottom: var(--px-border-thick) !important;
    background: var(--px-surface) !important;
    color: var(--px-dark) !important;
    min-height: var(--px-control-height) !important;
}}
[role="tab"][aria-selected="true"] {{
    background: var(--px-white) !important;
    border-bottom: 4px solid var(--px-red) !important;
    font-weight: var(--px-font-weight-bold) !important;
}}
div[data-testid="stSidebar"] {{
    background-color: var(--px-surface) !important;
    border-right: var(--px-border-thick) !important;
}}
div[data-testid="stSidebar"] * {{
    font-family: var(--px-font-body) !important;
}}
[data-testid="stRadioGroup"] label[data-testid="stRadioOption"] {{
    border: var(--px-border-thick) !important;
    background: var(--px-white) !important;
    padding: var(--px-space-2) var(--px-space-4) !important;
    margin-bottom: var(--px-space-2) !important;
    min-height: var(--px-control-height) !important;
}}

/* ── Notices ───────────────────────────────────────────────────────── */
.stAlert {{
    border: var(--px-border-thick) !important;
    font-family: var(--px-font-body) !important;
}}
div[data-testid="stNotification"] {{
    border: var(--px-border-thick) !important;
}}

/* ── Remove gradients everywhere (scoped !important) ───────────────── */
.stApp * {{
    background-image: none !important;
}}

/* ── Responsive: smaller borders/shadows, 44px touch targets on mobile */
@media (max-width: 640px) {{
    :root {{
        --px-border-thick: 2px solid var(--px-dark);
        --px-shadow-md: 2px 2px 0 var(--px-dark);
        --px-shadow-lg: 4px 4px 0 var(--px-dark);
        --px-control-height: var(--px-control-height-mobile);
    }}
    .stApp h1 {{ font-size: 1.4rem; }}
    .stApp h2 {{ font-size: 1.1rem; }}
    .stApp h3 {{ font-size: 0.95rem; }}
    .stTextArea textarea {{ font-size: 0.9rem; }}
    [data-testid^="stBaseButton"],
    [data-testid="stDownloadButton"],
    [data-testid="stRadioGroup"] label[data-testid="stRadioOption"],
    [role="tab"],
    .stTextInput > div > div > input,
    [data-testid="stTextArea"] textarea {{
        min-height: var(--px-touch-target) !important;
    }}
}}

/* ── prefers-reduced-motion ────────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {{
    .stApp *, .stApp *::before, .stApp *::after {{
        transition: none !important;
        animation: none !important;
    }}
}}
</style>
"""


# ══════════════════════════════════════════════════════════════════════
# 3. Shared component CSS (token-driven primitives)
# ══════════════════════════════════════════════════════════════════════

def build_component_css() -> str:
    return f"""
<style>
.px-card {{
    background: var(--px-white);
    border: var(--px-border-thick);
    box-shadow: var(--px-shadow-md);
    padding: var(--px-card-pad);
    margin-bottom: var(--px-space-4);
    font-family: var(--px-font-body);
}}

.px-card-interactive:hover {{
    box-shadow: var(--px-shadow-sm);
    transform: translate(2px, 2px);
}}

.px-btn {{
    display: inline-block;
    background: var(--px-action);
    color: var(--px-action-text);
    font-family: var(--px-font-body);
    font-weight: var(--px-font-weight-bold);
    border: var(--px-border-thick);
    box-shadow: var(--px-shadow-md);
    padding: var(--px-space-2) var(--px-space-4);
    cursor: pointer;
    text-align: center;
    min-height: var(--px-control-height);
}}

.px-btn:hover {{
    box-shadow: var(--px-shadow-sm);
    transform: translate(2px, 2px);
}}

.px-btn:active {{
    box-shadow: none;
    transform: translate(4px, 4px);
}}

.px-btn:focus-visible {{
    outline: var(--px-focus-width) solid var(--px-focus);
    outline-offset: var(--px-focus-offset);
}}

.px-btn:disabled {{
    background: var(--px-action-disabled);
    color: var(--px-action-text-disabled);
    box-shadow: none;
    cursor: not-allowed;
}}

.px-btn-primary {{
    background: var(--px-action);
    color: var(--px-action-text);
}}

.px-btn-secondary {{
    background: var(--px-secondary-action);
    color: var(--px-dark);
}}

.px-btn-destructive {{
    background: var(--px-dark);
    color: var(--px-white);
}}

.px-section {{
    border-top: var(--px-border-thick);
    border-bottom: var(--px-border-thin);
    padding: var(--px-space-4) 0;
    margin: var(--px-space-4) 0;
}}

.px-divider {{
    border: none;
    border-top: var(--px-border-thick);
    margin: var(--px-space-4) 0;
}}

.px-badge {{
    display: inline-block;
    padding: var(--px-space-1) var(--px-space-3);
    border: var(--px-border-thin);
    font-size: var(--px-font-size-label);
    font-weight: var(--px-font-weight-bold);
    vertical-align: middle;
}}

.px-badge-red {{
    background: var(--px-status-error);
    color: var(--px-status-on-error);
}}
.px-badge-green {{
    background: var(--px-status-success);
    color: var(--px-status-on-success);
}}
.px-badge-blue {{
    background: var(--px-status-info);
    color: var(--px-status-on-info);
}}
.px-badge-yellow {{
    background: var(--px-status-warning);
    color: var(--px-status-on-warning);
}}

.px-notice {{
    border: var(--px-border-thick);
    padding: var(--px-space-3) var(--px-space-4);
    margin-bottom: var(--px-space-4);
    font-family: var(--px-font-body);
    display: flex;
    align-items: flex-start;
    gap: var(--px-inline-gap);
}}

.px-notice-warning {{
    background: var(--px-status-warning);
    color: var(--px-status-on-warning);
    border-color: var(--px-dark);
}}

.px-notice-error {{
    background: var(--px-status-error);
    color: var(--px-status-on-error);
    border-color: var(--px-dark);
}}

.px-notice-success {{
    background: var(--px-status-success);
    color: var(--px-status-on-success);
    border-color: var(--px-dark);
}}

.px-notice-info {{
    background: var(--px-status-info);
    color: var(--px-status-on-info);
    border-color: var(--px-dark);
}}

.px-notice-limitation {{
    background: var(--px-surface);
    color: var(--px-text);
    border-color: var(--px-dark);
}}

.px-empty {{
    border: var(--px-border-thick);
    padding: var(--px-space-6) var(--px-space-4);
    text-align: center;
    color: var(--px-muted);
    font-family: var(--px-font-body);
    background: var(--px-surface);
}}

.px-timeline-node {{
    display: flex;
    align-items: flex-start;
    gap: var(--px-space-3);
    margin-bottom: var(--px-space-3);
}}

.px-timeline-marker {{
    width: 12px;
    height: 12px;
    background: var(--px-dark);
    border: var(--px-border-thin);
    flex-shrink: 0;
    margin-top: 4px;
}}

.px-timeline-content {{
    flex: 1;
}}

.px-quote {{
    border: var(--px-border-thick);
    background: var(--px-surface);
    padding-left: var(--px-space-4);
    color: var(--px-text-secondary);
    font-style: italic;
}}

.px-metric-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: var(--px-space-4);
}}

.px-table-wrap {{
    overflow-x: auto;
    border: var(--px-border-thick);
}}

.px-table-wrap table {{
    width: 100%;
    border-collapse: collapse;
    font-size: var(--px-table-font-size);
}}

.px-table-wrap th {{
    background: var(--px-dark);
    color: var(--px-white);
    padding: var(--px-space-2) var(--px-space-3);
    border: 1px solid var(--px-dark);
    text-align: left;
    font-family: var(--px-font-body);
}}

.px-table-wrap td {{
    padding: var(--px-space-2) var(--px-space-3);
    border: 1px solid var(--px-dark);
    background: var(--px-white);
    font-family: var(--px-font-body);
}}

.px-table-wrap tr:nth-child(even) td {{
    background: var(--px-surface);
}}

.px-status-row {{
    display: flex;
    align-items: center;
    gap: var(--px-space-2);
    margin-bottom: var(--px-space-1);
}}

/* ── v0.9.4-A primitives ───────────────────────────────────────────── */
.px-icon {{
    display: inline-flex;
    vertical-align: middle;
    flex-shrink: 0;
    margin-right: var(--px-space-1);
}}

.px-field-error {{
    border: var(--px-border-thin);
    border-left: var(--px-border-thick);
    background: var(--px-white);
    color: var(--px-status-error);
    padding: var(--px-space-2) var(--px-space-3);
    margin-bottom: var(--px-space-3);
    font-family: var(--px-font-body);
    font-weight: var(--px-font-weight-bold);
    display: flex;
    align-items: flex-start;
    gap: var(--px-inline-gap);
}}

.px-loading {{
    border: var(--px-border-thick);
    background: var(--px-surface);
    color: var(--px-dark);
    padding: var(--px-space-3) var(--px-space-4);
    margin-bottom: var(--px-space-4);
    font-family: var(--px-font-body);
    display: flex;
    align-items: center;
    gap: var(--px-inline-gap);
}}

@media (max-width: 640px) {{
    .px-metric-grid {{
        grid-template-columns: 1fr;
    }}
}}
</style>
"""


PIXEL_CSS = build_pixel_css()
PIXEL_COMPONENT_CSS = build_component_css()


# ══════════════════════════════════════════════════════════════════════
# 4. Local accessible icon primitive (icon policy)
# ══════════════════════════════════════════════════════════════════════

# Pixel-style 16x16 outline glyphs (square caps, no curves). All icons are
# local inline SVG: no remote icon fonts or icon services are allowed.
ICON_PATHS = {
    "check": '<path d="M3 8.5 L6.5 12 L13 4"/>',
    "warning": '<path d="M8 2.5 L14.5 13.5 H1.5 Z"/><path d="M8 6.5 V9.5"/><path d="M8 11 V11.2"/>',
    "info": '<path d="M8 2.5 L13.5 8 L8 13.5 L2.5 8 Z"/><path d="M8 6.2 V6.4"/><path d="M8 7.5 V10.5"/>',
    "error": '<path d="M8 2 L14 8 L8 14 L2 8 Z"/><path d="M5.5 5.5 L10.5 10.5"/><path d="M10.5 5.5 L5.5 10.5"/>',
    "arrow_right": '<path d="M2 8 H13"/><path d="M9 4 L13 8 L9 12"/>',
    "empty": '<path d="M3 3 H13 V13 H3 Z"/><path d="M5.5 5.5 H10.5 V10.5 H5.5 Z"/>',
    "clock": '<path d="M8 2 L14 8 L8 14 L2 8 Z"/><path d="M8 5 V8 L10.5 9.5"/>',
}


def icon(
    name: str,
    *,
    size: int = 16,
    label: str | None = None,
    color: str = "currentColor",
) -> str:
    """Return a local pixel-style inline SVG icon.

    Accessibility policy:
    - decorative icons: ``aria-hidden="true"`` (no label);
    - meaningful icons: pass ``label`` → ``role="img"`` + ``aria-label``.
    Icons never carry text meaning on their own in this system; status
    always has a visible text channel.
    """
    path = ICON_PATHS.get(name, ICON_PATHS["empty"])
    if label:
        aria = f'role="img" aria-label="{html.escape(label, quote=True)}"'
    else:
        aria = 'aria-hidden="true"'
    return (
        f'<svg class="px-icon" data-testid="px-icon" width="{size}" '
        f'height="{size}" viewBox="0 0 16 16" fill="none" '
        f'stroke="{color}" stroke-width="2" stroke-linecap="square" '
        f'stroke-linejoin="miter" {aria}>{path}</svg>'
    )


# ══════════════════════════════════════════════════════════════════════
# 5. Reusable pixel-art HTML components (compatibility layer)
# ══════════════════════════════════════════════════════════════════════

def pixel_card(content: str, interactive: bool = False) -> str:
    """Wrap content in a pixel-art card with hard shadow."""
    classes = "px-card"
    if interactive:
        classes += " px-card-interactive"
    return f'<div class="{classes}">{content}</div>'


def inject_pixel_art() -> None:
    """Inject the complete Hybrid Pixel System CSS into the Streamlit page."""
    st.markdown(PIXEL_CSS + PIXEL_COMPONENT_CSS, unsafe_allow_html=True)
