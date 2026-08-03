"""v0.9.6-C2 focused tests: sidebar collapse control repair.

Source-level checks prove the CSS fix, and browser/DOM checks (Playwright
against the real app on a fresh isolated database) prove rendering behavior:
icon font restored, exactly one control, mouse and keyboard collapse/expand,
five student pages, and a narrow viewport.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
PIXEL_CSS = (ROOT / "app/ui/pixel_art.py").read_text(encoding="utf-8")

OVER_BROAD_SIDEBAR_FONT = 'div[data-testid="stSidebar"] * {\n    font-family: var(--px-font-body) !important;\n}'
NARROWED_RULE = 'div[data-testid="stSidebar"] *:not(button *)'
RESTORATION_RULE = 'div[data-testid="stSidebarCollapseButton"] span'
BANNED_FIXES = (
    "font-size: 0;",
    "font-size:0",
    "color: transparent",
    "color:transparent",
)


def test_over_broad_sidebar_font_selector_removed():
    assert OVER_BROAD_SIDEBAR_FONT not in PIXEL_CSS


def test_sidebar_font_rule_narrowed_to_exclude_button_content():
    assert NARROWED_RULE in PIXEL_CSS


def test_icon_font_restoration_rule_present_and_no_hiding_tricks():
    assert RESTORATION_RULE in PIXEL_CSS
    assert 'font-family: "Material Symbols Rounded" !important' in PIXEL_CSS
    assert 'font-feature-settings: "liga" !important' in PIXEL_CSS
    for banned in BANNED_FIXES:
        assert banned not in PIXEL_CSS


def test_locale_parity_unchanged():
    def leaf_keys(obj, prefix=""):
        keys = set()
        for k, v in obj.items():
            p = prefix + "/" + k
            if isinstance(v, dict):
                keys |= leaf_keys(v, p)
            else:
                keys.add(p)
        return keys

    en = json.loads((ROOT / "locales/en.json").read_text(encoding="utf-8"))
    zh = json.loads((ROOT / "locales/zh_CN.json").read_text(encoding="utf-8"))
    assert leaf_keys(en) == leaf_keys(zh)


# ---------------------------------------------------------------------------
# Browser/DOM verification against the real app
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app_env(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("v096c2")
    db = tmp / "c2.db"
    env = dict(os.environ)
    env["PYTHON_DOTENV_DISABLED"] = "1"
    env.pop("DATABASE_URL", None)
    env["DATABASE_PATH"] = str(db)
    env["LLM_PROVIDER"] = "local"
    venv_py = ROOT / ".venv" / "Scripts" / "python.exe"
    api = subprocess.Popen(
        [str(venv_py), "-m", "uvicorn", "app.api.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    st = subprocess.Popen(
        [str(venv_py), "-m", "streamlit", "run", "streamlit_app.py",
         "--server.headless", "true", "--server.port", "8501",
         "--browser.gatherUsageStats", "false"],
        cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        ready = False
        for _ in range(120):
            try:
                if requests.get("http://127.0.0.1:8000/api/v1/system/health", timeout=1).status_code == 200 \
                        and requests.get("http://127.0.0.1:8501", timeout=1).status_code == 200:
                    ready = True
                    break
            except Exception:
                pass
            time.sleep(0.5)
        assert ready, "app did not become ready"
        yield {"db": db}
    finally:
        for proc in (st, api):
            proc.terminate()
        for proc in (st, api):
            try:
                proc.wait(timeout=15)
            except Exception:
                proc.kill()


@pytest.fixture()
def page(app_env):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto("http://127.0.0.1:8501", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3500)
        yield page
        browser.close()


def _icon_font(page) -> str:
    return page.evaluate(
        """() => {
            const icon = document.querySelector('[data-testid="stSidebarCollapseButton"] span');
            return icon ? getComputedStyle(icon).fontFamily : null;
        }"""
    )


def _sidebar_width(page) -> float:
    return page.evaluate(
        """() => {
            const sb = document.querySelector('[data-testid="stSidebar"]');
            return sb ? sb.getBoundingClientRect().width : null;
        }"""
    )


def _control_count(page) -> int:
    return page.evaluate(
        """() => document.querySelectorAll('[data-testid="stSidebarCollapseButton"]').length"""
    )


def _click_expand(page) -> None:
    page.evaluate(
        """() => {
            const spans = Array.from(document.querySelectorAll('span'));
            const el = spans.find(s => (s.textContent || '').includes('keyboard_double_arrow_right'));
            const btn = el ? el.closest('button') : null;
            if (btn) btn.click();
        }"""
    )
    page.wait_for_timeout(1500)


def _collapse_with_button(page) -> None:
    page.evaluate(
        """() => {
            const btn = document.querySelector('[data-testid="stSidebarCollapseButton"] button');
            if (btn) btn.click();
        }"""
    )
    page.wait_for_timeout(1500)


def test_browser_icon_font_restored(page):
    font = _icon_font(page)
    assert "Material Symbols Rounded" in (font or "")
    assert "Material" in (font or "")
    feature = page.evaluate(
        """() => {
            const icon = document.querySelector('[data-testid="stSidebarCollapseButton"] span');
            return icon ? getComputedStyle(icon).fontFeatureSettings : null;
        }"""
    )
    assert "liga" in (feature or "")


def test_browser_exactly_one_control(page):
    assert _control_count(page) == 1
    assert _sidebar_width(page) == 300


def test_browser_expanded_to_collapsed_mouse(page):
    _collapse_with_button(page)
    assert _sidebar_width(page) == 0
    # exactly one visible expand control with the right-arrow ligature
    expand = page.evaluate(
        """() => {
            const spans = Array.from(document.querySelectorAll('span'));
            const el = spans.find(s => (s.textContent || '').includes('keyboard_double_arrow_right'));
            if (!el) return null;
            const r = el.getBoundingClientRect();
            const btn = el.closest('button');
            return {x: r.x, w: r.width, testid: btn ? btn.getAttribute('data-testid') : null};
        }"""
    )
    assert expand is not None and expand["w"] > 0 and expand["testid"] == "stExpandSidebarButton"


def test_browser_collapsed_to_expanded_mouse(page):
    _collapse_with_button(page)
    assert _sidebar_width(page) == 0
    _click_expand(page)
    assert _sidebar_width(page) == 300
    assert _control_count(page) == 1
    assert "Material Symbols Rounded" in (_icon_font(page) or "")


def test_browser_keyboard_activation(page):
    # Streamlit reveals the native collapse button while the sidebar is
    # hovered (the button starts visibility:hidden). Reveal it the same way
    # a user does, assert the reveal, then drive it with the keyboard.
    page.locator('[data-testid="stSidebar"]').hover()
    page.wait_for_timeout(500)
    revealed = page.evaluate(
        """() => {
            const btn = document.querySelector('[data-testid="stSidebarCollapseButton"] button');
            return btn ? getComputedStyle(btn).visibility : null;
        }"""
    )
    assert revealed == "visible"
    page.evaluate(
        """() => document.querySelector('[data-testid="stSidebarCollapseButton"] button').focus()"""
    )
    page.keyboard.press("Enter")
    page.wait_for_timeout(1500)
    assert _sidebar_width(page) == 0
    page.evaluate(
        """() => {
            const spans = Array.from(document.querySelectorAll('span'));
            const el = spans.find(s => (s.textContent || '').includes('keyboard_double_arrow_right'));
            const btn = el ? el.closest('button') : null;
            if (btn) btn.focus();
        }"""
    )
    page.keyboard.press("Enter")
    page.wait_for_timeout(1500)
    assert _sidebar_width(page) == 300


def test_browser_accessible_name_present(page):
    info = page.evaluate(
        """() => {
            const ctl = document.querySelector('[data-testid="stSidebarCollapseButton"]');
            const btn = ctl ? ctl.querySelector('button') : null;
            return {
                control_exists: !!ctl,
                button_exists: !!btn,
                button_role: btn ? (btn.getAttribute('role') || 'button') : null,
                aria_label_attr_present: btn ? (btn.hasAttribute('aria-label')) : false,
            };
        }"""
    )
    assert info["control_exists"] and info["button_exists"]
    assert info["button_role"] == "button"
    assert info["aria_label_attr_present"]


def test_browser_five_pages_consistent(page):
    for label in ("Home", "Writing", "Feedback", "Revision", "Practice"):
        page.locator('[data-testid="stSidebar"]').get_by_text(label, exact=True).first.click()
        page.wait_for_timeout(1400)
        assert _control_count(page) == 1, label
        assert "Material Symbols Rounded" in (_icon_font(page) or ""), label
        assert _sidebar_width(page) == 300, label


def test_browser_narrow_viewport_toggle(page):
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(1200)
    if _sidebar_width(page) == 0:
        _click_expand(page)
    _collapse_with_button(page)
    assert _sidebar_width(page) == 0
    _click_expand(page)
    assert _sidebar_width(page) == 300
    assert "Material Symbols Rounded" in (_icon_font(page) or "")