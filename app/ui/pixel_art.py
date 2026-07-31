"""
Pixel Art design system for the writing-feedback-mvp Streamlit interface.

Provides CSS custom property injection and reusable styled HTML components.
All tokens follow the v0.9.2 Pixel Art specification:
- Solid colors, no gradients, no blur, no soft shadows
- Square corners (border-radius: 0)
- Hard offset shadows (no blur radius)
- Monospace typography stack
- Immediate state changes (transition: none)
"""

from __future__ import annotations

import streamlit as st

# ── Canonical color palette ──────────────────────────────────────────────
PIXEL_COLORS = {
    "dark": "#1a1c2c",
    "white": "#ffffff",
    "surface": "#f4f4f4",
    "red": "#ff004d",
    "green": "#00e436",
    "blue": "#29adff",
    "yellow": "#ffec27",
    "text": "#1a1c2c",
    "muted": "#6b6b7b",
    "disabled_bg": "#e8e8ec",
}

# ── CSS custom properties block ──────────────────────────────────────────
PIXEL_CSS = """
<style>
:root {
    /* ── Colors ─────────────────────────── */
    --px-dark: #1a1c2c;
    --px-white: #ffffff;
    --px-surface: #f4f4f4;
    --px-red: #ff004d;
    --px-green: #00e436;
    --px-blue: #29adff;
    --px-yellow: #ffec27;
    --px-text: #1a1c2c;
    --px-muted: #6b6b7b;
    --px-disabled-bg: #e8e8ec;

    /* ── Borders ────────────────────────── */
    --px-border-thick: 4px solid #1a1c2c;
    --px-border-thin: 2px solid #1a1c2c;
    --px-border-hairline: 1px solid #1a1c2c;

    /* ── Hard shadows ───────────────────── */
    --px-shadow-sm: 2px 2px 0 #1a1c2c;
    --px-shadow-md: 4px 4px 0 #1a1c2c;
    --px-shadow-lg: 8px 8px 0 #1a1c2c;

    /* ── Spacing ────────────────────────── */
    --px-space-1: 4px;
    --px-space-2: 8px;
    --px-space-3: 12px;
    --px-space-4: 16px;
    --px-space-5: 20px;
    --px-space-6: 24px;
    --px-space-8: 32px;
    --px-space-10: 40px;
    --px-space-12: 48px;

    /* ── Typography ─────────────────────── */
    --px-font-mono: ui-monospace, 'Cascadia Mono', 'Cascadia Code', Consolas,
                    SFMono-Regular, Menlo, Monaco, 'Liberation Mono',
                    'Courier New', monospace;
    --px-font-weight-heavy: 900;
    --px-font-weight-bold: 700;
    --px-font-weight-normal: 400;
    --px-line-height: 1.6;

    /* ── Immutable rules ────────────────── */
    --px-radius: 0px;
    --px-transition: none;
}

/* ── Global overrides ─────────────────────────────────────────────────── */
.stApp {
    background-color: var(--px-white);
    font-family: var(--px-font-mono);
}

.stApp * {
    border-radius: 0 !important;
}

.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp h5,.stApp h6 {
    font-family: var(--px-font-mono);
    color: var(--px-dark);
}

.stApp h1 { font-weight: var(--px-font-weight-heavy); }
.stApp h2 { font-weight: var(--px-font-weight-bold); }
.stApp h3 { font-weight: var(--px-font-weight-bold); }

.stApp p, .stApp li, .stApp label, .stApp caption {
    font-family: var(--px-font-mono);
    color: var(--px-text);
    line-height: var(--px-line-height);
}

/* ── Remove all Streamlit rounded corners ─────────────────────────────── */
div[data-testid="stVerticalBlock"] > div,
div[data-testid="stHorizontalBlock"] > div,
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div,
.stMultiSelect > div > div,
.stNumberInput > div > div > input,
.stButton > button,
.stDownloadButton > button,
.stCheckbox > label > div,
.stRadio > div,
div[data-testid="stSidebar"],
div[data-testid="stExpander"],
div[data-testid="stTabs"],
div[data-testid="stNotification"],
.stAlert,
div[data-baseweb="select"] > div,
div[data-baseweb="popover"],
div[data-baseweb="menu"],
div[data-baseweb="modal"],
div[data-baseweb="tooltip"] {
    border-radius: 0 !important;
}

/* ── Remove transitions and animations ────────────────────────────────── */
.stApp *, .stApp *::before, .stApp *::after {
    transition: none !important;
    animation: none !important;
}

/* ── Remove soft shadows; replace with hard pixel shadows ─────────────── */
.stApp button,
div[data-testid="stExpander"],
.stAlert,
div[data-testid="stSidebar"],
div[data-testid="stTabs"] {
    box-shadow: none !important;
}

/* ── Borders on key elements ──────────────────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > div,
.stNumberInput > div > div > input {
    border: var(--px-border-thick) !important;
    background-color: var(--px-white) !important;
    color: var(--px-text) !important;
    font-family: var(--px-font-mono) !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus,
.stSelectbox > div > div > div:focus,
.stNumberInput > div > div > input:focus {
    outline: 3px solid var(--px-blue) !important;
    outline-offset: 2px !important;
    box-shadow: none !important;
}

/* ── Expanders ───────────────────────────────────────────────────────── */
div[data-testid="stExpander"] {
    border: var(--px-border-thick) !important;
    background-color: var(--px-white) !important;
}

/* ── Tabs ─────────────────────────────────────────────────────────────── */
div[data-testid="stTabs"] {
    font-family: var(--px-font-mono);
}

button[data-baseweb="tab"] {
    font-family: var(--px-font-mono) !important;
    border: none !important;
    border-bottom: var(--px-border-thick) !important;
    background: var(--px-surface) !important;
    color: var(--px-dark) !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    background: var(--px-white) !important;
    border-bottom: 4px solid var(--px-red) !important;
    font-weight: var(--px-font-weight-bold) !important;
}

/* ── Sidebar ──────────────────────────────────────────────────────────── */
div[data-testid="stSidebar"] {
    background-color: var(--px-surface) !important;
    border-right: var(--px-border-thick) !important;
}

div[data-testid="stSidebar"] * {
    font-family: var(--px-font-mono) !important;
}

/* ── Radio buttons ────────────────────────────────────────────────────── */
.stRadio > div[role="radiogroup"] > label {
    border: var(--px-border-thick) !important;
    background: var(--px-white) !important;
    padding: var(--px-space-2) var(--px-space-4) !important;
    margin-bottom: var(--px-space-2) !important;
}

.stRadio > div[role="radiogroup"] > label > div:first-child {
    border-radius: 0 !important;
}

/* ── Alert / notification overrides ───────────────────────────────────── */
.stAlert {
    border: var(--px-border-thick) !important;
}

div[data-testid="stNotification"] {
    border: var(--px-border-thick) !important;
}

/* ── Remove gradients everywhere ──────────────────────────────────────── */
.stApp * {
    background-image: none !important;
}

/* ── Responsive: smaller borders on mobile ────────────────────────────── */
@media (max-width: 640px) {
    :root {
        --px-border-thick: 2px solid #1a1c2c;
        --px-shadow-md: 2px 2px 0 #1a1c2c;
        --px-shadow-lg: 4px 4px 0 #1a1c2c;
    }

    .stApp h1 { font-size: 1.4rem; }
    .stApp h2 { font-size: 1.1rem; }
    .stApp h3 { font-size: 0.95rem; }
    .stTextArea textarea { font-size: 0.9rem; }
}

/* ── prefers-reduced-motion ───────────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
    .stApp *, .stApp *::before, .stApp *::after {
        transition: none !important;
        animation: none !important;
    }
}
</style>
"""

# ── Reusable pixel-art HTML components ────────────────────────────────────

def pixel_card(content: str, interactive: bool = False) -> str:
    """Wrap content in a pixel-art card with hard shadow."""
    classes = "px-card"
    if interactive:
        classes += " px-card-interactive"
    return f'<div class="{classes}">{content}</div>'


# Smaller companion CSS for pixel-art component classes
PIXEL_COMPONENT_CSS = """
<style>
.px-card {
    background: var(--px-white);
    border: var(--px-border-thick);
    box-shadow: var(--px-shadow-md);
    padding: var(--px-space-4);
    margin-bottom: var(--px-space-4);
}

.px-card-interactive:hover {
    box-shadow: var(--px-shadow-sm);
    transform: translate(2px, 2px);
}

.px-btn {
    display: inline-block;
    background: var(--px-red);
    color: var(--px-white);
    font-family: var(--px-font-mono);
    font-weight: var(--px-font-weight-bold);
    border: var(--px-border-thick);
    box-shadow: var(--px-shadow-md);
    padding: var(--px-space-2) var(--px-space-4);
    cursor: pointer;
    text-align: center;
}

.px-btn:hover {
    box-shadow: var(--px-shadow-sm);
    transform: translate(2px, 2px);
}

.px-btn:active {
    box-shadow: none;
    transform: translate(4px, 4px);
}

.px-btn:focus-visible {
    outline: 3px solid var(--px-blue);
    outline-offset: 2px;
}

.px-btn:disabled {
    background: var(--px-disabled-bg);
    color: var(--px-muted);
    box-shadow: none;
    cursor: not-allowed;
}

.px-btn-secondary {
    background: var(--px-surface);
    color: var(--px-dark);
}

.px-btn-destructive {
    background: var(--px-dark);
    color: var(--px-white);
}

.px-section {
    border-top: var(--px-border-thick);
    border-bottom: var(--px-border-thin);
    padding: var(--px-space-4) 0;
    margin: var(--px-space-4) 0;
}

.px-divider {
    border: none;
    border-top: var(--px-border-thick);
    margin: var(--px-space-4) 0;
}

.px-badge {
    display: inline-block;
    padding: var(--px-space-1) var(--px-space-3);
    border: var(--px-border-thin);
    font-family: var(--px-font-mono);
    font-size: 0.85rem;
    font-weight: var(--px-font-weight-bold);
}

.px-badge-red { background: var(--px-red); color: var(--px-white); }
.px-badge-green { background: var(--px-green); color: var(--px-dark); }
.px-badge-blue { background: var(--px-blue); color: var(--px-dark); }
.px-badge-yellow { background: var(--px-yellow); color: var(--px-dark); }

.px-notice {
    border: var(--px-border-thick);
    padding: var(--px-space-3) var(--px-space-4);
    margin-bottom: var(--px-space-4);
    font-family: var(--px-font-mono);
}

.px-notice-warning {
    background: var(--px-yellow);
    color: var(--px-dark);
    border-color: var(--px-dark);
}

.px-notice-error {
    background: var(--px-red);
    color: var(--px-white);
    border-color: var(--px-dark);
}

.px-notice-success {
    background: var(--px-green);
    color: var(--px-dark);
    border-color: var(--px-dark);
}

.px-notice-info {
    background: var(--px-blue);
    color: var(--px-dark);
    border-color: var(--px-dark);
}

.px-notice-limitation {
    background: var(--px-surface);
    color: var(--px-text);
    border-color: var(--px-dark);
}

.px-empty {
    border: var(--px-border-thick);
    padding: var(--px-space-6) var(--px-space-4);
    text-align: center;
    color: var(--px-muted);
    font-family: var(--px-font-mono);
    background: var(--px-surface);
}

.px-timeline-node {
    display: flex;
    align-items: flex-start;
    gap: var(--px-space-3);
    margin-bottom: var(--px-space-3);
}

.px-timeline-marker {
    width: 12px;
    height: 12px;
    background: var(--px-dark);
    border: var(--px-border-thin);
    flex-shrink: 0;
    margin-top: 4px;
}

.px-timeline-content {
    flex: 1;
}

.px-quote {
    border: var(--px-border-thick);
    background: var(--px-surface);
    padding-left: var(--px-space-4);
    color: var(--px-muted);
    font-style: italic;
}

.px-metric-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: var(--px-space-4);
}

.px-table-wrap {
    overflow-x: auto;
    border: var(--px-border-thick);
}

.px-table-wrap table {
    width: 100%;
    border-collapse: collapse;
    font-family: var(--px-font-mono);
    font-size: 0.85rem;
}

.px-table-wrap th {
    background: var(--px-dark);
    color: var(--px-white);
    padding: var(--px-space-2) var(--px-space-3);
    border: 1px solid var(--px-dark);
    text-align: left;
}

.px-table-wrap td {
    padding: var(--px-space-2) var(--px-space-3);
    border: 1px solid var(--px-dark);
    background: var(--px-white);
}

.px-table-wrap tr:nth-child(even) td {
    background: var(--px-surface);
}

.px-status-row {
    display: flex;
    align-items: center;
    gap: var(--px-space-2);
    margin-bottom: var(--px-space-1);
}

@media (max-width: 640px) {
    .px-metric-grid {
        grid-template-columns: 1fr;
    }
}
</style>
"""


def inject_pixel_art() -> None:
    """Inject the complete Pixel Art CSS system into the Streamlit page."""
    st.markdown(PIXEL_CSS + PIXEL_COMPONENT_CSS, unsafe_allow_html=True)
