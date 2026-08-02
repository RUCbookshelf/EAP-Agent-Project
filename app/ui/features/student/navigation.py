"""Shared Student navigation helper (v0.9.5-C).

Ownership: `_navigate_student_page` is used by all six Student features and
lives here once. Behavior is unchanged from the pre-extraction module.
"""

from __future__ import annotations

import streamlit as st

from app.ui.locale import t


def _navigate_student_page(title_key: str, lang: str) -> None:
    """Move to an existing localized Student sidebar page on the next rerun."""
    st.session_state["sidebar_page"] = t(title_key, lang)
