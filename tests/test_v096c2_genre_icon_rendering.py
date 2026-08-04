"""v0.9.6-C2 focused tests: Genre-area native icon rendering (follow-up 2).

Proves the common source-level fix (native Streamlit icon spans excluded from
the pixel body-font rule) restores Material Symbols ligature rendering on the
two Writing-page expander chevrons (Timing / Tools Used) in normal, hover,
focus, open, Enter and Space states, at desktop and narrow viewports, while
the Genre selectbox (SVG comparison control) stays unchanged.
"""
from __future__ import annotations

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

COMMON_EXCLUSION = '.stApp span:not([data-testid="stIconMaterial"])'
BANNED_HIDING = (
    "font-size: 0;",
    "font-size:0",
    "color: transparent",
    "color:transparent",
    "visibility: hidden",
)

LIGATURE_SCAN = """() => {
    const out = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
        if (node.parentElement && ['STYLE','SCRIPT'].includes(node.parentElement.tagName)) continue;
        const txt = (node.textContent || '').trim();
        if (txt.includes('_') && txt.length < 60) {
            out.push({text: txt, font_family: getComputedStyle(node.parentElement).fontFamily});
        }
    }
    return out;
}"""


def test_common_font_rule_excludes_native_icon_spans():
    assert COMMON_EXCLUSION in PIXEL_CSS
    # No other rule may target the native icon testid.
    assert 'span[data-testid="stIconMaterial"]' not in PIXEL_CSS.replace(COMMON_EXCLUSION, "")


def test_no_per_control_icon_patch_added():
    # The common exclusion is the fix; no per-expander patches or hiding tricks.
    assert 'stExpander"] summary span' not in PIXEL_CSS
    for banned in BANNED_HIDING:
        assert banned not in PIXEL_CSS


# ---------------------------------------------------------------------------
# Browser/DOM verification against the real app
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app_env(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("v096c2genre")
    db = tmp / "c2genre.db"
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
        page.locator('[data-testid="stSidebar"]').get_by_text("Writing", exact=True).first.click()
        page.wait_for_timeout(1800)
        yield page
        browser.close()


def _chevrons(page):
    return page.locator('div[data-testid="stExpander"] summary span[data-testid="stIconMaterial"]')


def _font(page, locator) -> str:
    return locator.evaluate("(el) => getComputedStyle(el).fontFamily") or ""


def _icon_state(page, locator) -> dict:
    return locator.evaluate(
        """(el) => {
            const cs = getComputedStyle(el);
            const r = el.getBoundingClientRect();
            return {
                font: cs.fontFamily, visibility: cs.visibility, opacity: cs.opacity,
                w: r.width, h: r.height, text: (el.textContent || '').trim(),
            };
        }"""
    )


def test_browser_two_genre_expander_chevrons_use_icon_font(page):
    chevrons = _chevrons(page)
    assert chevrons.count() == 2
    for i in range(2):
        state = _icon_state(page, chevrons.nth(i))
        assert state["text"] == "keyboard_arrow_right"
        assert "Material Symbols Rounded" in state["font"]
        assert state["visibility"] == "visible"
        assert state["opacity"] == "1"
        assert state["w"] == 16 and state["h"] == 16


def test_browser_chevron_normal_hover_focus_states(page):
    chevrons = _chevrons(page)
    for i in range(2):
        summary = page.locator('div[data-testid="stExpander"]').nth(i).locator("summary").first
        assert "Material Symbols Rounded" in _font(page, chevrons.nth(i))
        summary.hover()
        page.wait_for_timeout(300)
        assert "Material Symbols Rounded" in _font(page, chevrons.nth(i))
        summary.focus()
        page.wait_for_timeout(200)
        assert "Material Symbols Rounded" in _font(page, chevrons.nth(i))


def test_browser_chevron_open_enter_space_preserve_icon(page):
    exp = page.locator('div[data-testid="stExpander"]').first
    summary = exp.locator("summary").first
    chevron = exp.locator('summary span[data-testid="stIconMaterial"]').first
    summary.click()
    page.wait_for_timeout(400)
    assert _icon_state(page, chevron)["text"] == "keyboard_arrow_down"
    assert "Material Symbols Rounded" in _font(page, chevron)
    summary.focus()
    page.keyboard.press("Enter")
    page.wait_for_timeout(400)
    assert _icon_state(page, chevron)["text"] == "keyboard_arrow_right"
    assert "Material Symbols Rounded" in _font(page, chevron)
    page.keyboard.press("Space")
    page.wait_for_timeout(400)
    assert _icon_state(page, chevron)["text"] == "keyboard_arrow_down"
    assert "Material Symbols Rounded" in _font(page, chevron)
    summary.click()
    page.wait_for_timeout(300)


def test_browser_no_literal_ligature_text_on_writing_page(page):
    items = page.evaluate(LIGATURE_SCAN)
    assert items, "expected at least the sidebar/expander ligature nodes"
    for item in items:
        assert "Material Symbols Rounded" in item["font_family"], item


def test_browser_genre_selectbox_comparison_unchanged(page):
    sel = page.locator('[data-testid="stSelectbox"]').filter(has_text="Genre").first
    info = sel.evaluate(
        """(el) => {
            const svg = el.querySelector('svg');
            const body = el.querySelector('[data-baseweb="select"]');
            return {
                svg: !!svg,
                material_spans: el.querySelectorAll('span[data-testid="stIconMaterial"]').length,
                body_font: body ? getComputedStyle(body).fontFamily : null,
            };
        }"""
    )
    assert info["svg"]
    assert info["material_spans"] == 0
    assert "Material Symbols Rounded" not in (info["body_font"] or "")


def test_browser_timed_and_tool_use_values_retained(page):
    exp0 = page.locator('div[data-testid="stExpander"]').nth(0)
    exp0.locator("summary").first.click()
    page.wait_for_timeout(400)
    label = exp0.locator("label").filter(has_text="Timed writing").first
    label.click(force=True)
    page.wait_for_timeout(1800)
    cb = exp0.locator('input[type="checkbox"]').first
    assert cb.is_checked()
    exp1 = page.locator('div[data-testid="stExpander"]').nth(1)
    exp1.locator("summary").first.click()
    page.wait_for_timeout(400)
    inp = exp1.locator('input[type="text"]').first
    inp.click(force=True)
    page.keyboard.press("Control+A")
    page.keyboard.type("dictionary")
    page.wait_for_timeout(1800)
    assert inp.input_value() == "dictionary"


def test_browser_accessible_names_present(page):
    for i, expected in ((0, "Timing"), (1, "Tools")):
        summary = page.locator('div[data-testid="stExpander"]').nth(i).locator("summary").first
        assert expected in (summary.text_content() or "")
    cb = page.locator('div[data-testid="stExpander"]').nth(0).locator('input[type="checkbox"]').first
    assert cb.get_attribute("aria-label") == "Timed writing"


def test_browser_narrow_viewport_icons_and_toggle(page):
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(1200)
    chevrons = _chevrons(page)
    assert chevrons.count() == 2
    for i in range(2):
        assert "Material Symbols Rounded" in _font(page, chevrons.nth(i))
    exp = page.locator('div[data-testid="stExpander"]').first
    summary = exp.locator("summary").first
    summary.click()
    page.wait_for_timeout(400)
    assert "Material Symbols Rounded" in _font(page, exp.locator('summary span[data-testid="stIconMaterial"]').first)
    summary.click()
    page.wait_for_timeout(300)


def test_browser_five_pages_no_body_font_ligatures(page):
    for label in ("Home", "Writing", "Feedback", "Revision", "Practice"):
        page.locator('[data-testid="stSidebar"]').get_by_text(label, exact=True).first.click()
        page.wait_for_timeout(1400)
        items = page.evaluate(LIGATURE_SCAN)
        for item in items:
            assert "Material Symbols Rounded" in item["font_family"], (label, item)