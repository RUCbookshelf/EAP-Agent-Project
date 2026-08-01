"""Minimal v0.9.4-B extension of the stable v0.9.4-A browser harness."""

from __future__ import annotations

import pathlib
import sys


HERE = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
BASE_HARNESS_DIR = PROJECT_ROOT / "verification/v0.9.4-a/v0.9.4-a-20260801-r1"
sys.path.insert(0, str(BASE_HARNESS_DIR))

import v094a_harness as _base  # noqa: E402
from v094a_harness import *  # noqa: E402,F403


_base.RUN_DIR = HERE
_base.ISOLATED_DB = HERE / "isolated" / "writing_feedback_v094b.db"
_base.LOG_DIR = HERE / "logs"

RUN_DIR = _base.RUN_DIR
ISOLATED_DB = _base.ISOLATED_DB
LOG_DIR = _base.LOG_DIR


def close_sidebar(page) -> None:
    """Close Streamlit 1.60's unlabeled mobile sidebar control reliably."""
    if page.viewport_size and page.viewport_size["width"] >= 700:
        return
    _base.close_sidebar(page)
    sidebar = page.locator('[data-testid="stSidebar"]')
    if sidebar.count() == 0 or sidebar.first.get_attribute("aria-expanded") != "true":
        return

    control = sidebar.locator('[data-testid="stBaseButton-headerNoPadding"]').first
    if control.count() and "keyboard_double_arrow_left" in control.inner_text():
        control.click(timeout=4_000)
        page.wait_for_timeout(500)
    if sidebar.first.get_attribute("aria-expanded") == "true":
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
    if sidebar.first.get_attribute("aria-expanded") == "true":
        raise RuntimeError("Mobile sidebar remained open after the v0.9.4-B close helper")
