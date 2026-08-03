"""v0.9.6-C2 Phase post-fix probe: sidebar collapse control verification.

Starts the real API + Streamlit app against a fresh isolated database and
verifies the collapse/expand control in the rendered browser: visible icon
font, collapse/expand via mouse and keyboard, hover, five student pages, and
two viewports. Writes c2_sidebar_after.json and screenshots.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests

ROOT = Path(r"A:\EAP Agent Project\writing-feedback-mvp")
OUT = ROOT / "verification" / "v0.9.6-c"
OUT.mkdir(parents=True, exist_ok=True)
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
TMP = Path(tempfile.mkdtemp(prefix="v096c2-after-"))

env = dict(os.environ)
env["PYTHON_DOTENV_DISABLED"] = "1"
env.pop("DATABASE_URL", None)
env["DATABASE_PATH"] = str(TMP / "probe.db")
env["LLM_PROVIDER"] = "local"

api = subprocess.Popen(
    [str(VENV_PY), "-m", "uvicorn", "app.api.main:app", "--host", "127.0.0.1", "--port", "8000"],
    cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
st = subprocess.Popen(
    [str(VENV_PY), "-m", "streamlit", "run", "streamlit_app.py",
     "--server.headless", "true", "--server.port", "8501",
     "--browser.gatherUsageStats", "false"],
    cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)


def wait_ready() -> bool:
    for _ in range(120):
        try:
            if requests.get("http://127.0.0.1:8000/api/v1/system/health", timeout=1).status_code == 200 \
                    and requests.get("http://127.0.0.1:8501", timeout=1).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main() -> int:
    evidence = {"stage": "v0.9.6-C2", "kind": "c2_sidebar_after"}

    def save_evidence():
        with open(OUT / "c2_sidebar_after.json", "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    try:
        if not wait_ready():
            print("APP NOT READY")
            return 2

        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto("http://127.0.0.1:8501", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)
            page.screenshot(path=str(OUT / "c2_after_expanded.png"))

            control_sel = '[data-testid="stSidebarCollapseButton"]'
            button_sel = control_sel + " button"

            def ligature_elements():
                return page.evaluate("""() => {
                    const out = [];
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                    let node;
                    while ((node = walker.nextNode())) {
                        if (node.parentElement && ['STYLE','SCRIPT'].includes(node.parentElement.tagName)) continue;
                        const txt = (node.textContent || '').trim();
                        if (txt.includes('keyboard_double_arrow')) {
                            const el = node.parentElement;
                            const btn = el.closest('button');
                            const r = el.getBoundingClientRect();
                            out.push({text: txt, x: r.x, y: r.y, w: r.width, h: r.height, button_testid: btn ? btn.getAttribute('data-testid') : null});
                        }
                    }
                    return out;
                }""")

            def control_state():
                return page.evaluate("""() => {
                    const ctl = document.querySelector('[data-testid="stSidebarCollapseButton"]');
                    const btn = ctl ? ctl.querySelector('button') : null;
                    const icon = ctl ? ctl.querySelector('span') : null;
                    const cr = ctl ? ctl.getBoundingClientRect() : null;
                    const br = btn ? btn.getBoundingClientRect() : null;
                    const ir = icon ? icon.getBoundingClientRect() : null;
                    const sidebar = document.querySelector('[data-testid="stSidebar"]');
                    const sr = sidebar ? sidebar.getBoundingClientRect() : null;
                    return {
                        control_count: document.querySelectorAll('[data-testid="stSidebarCollapseButton"]').length,
                        control_visible: ctl ? (cr.width > 0 && cr.height > 0 && getComputedStyle(ctl).visibility !== 'hidden') : false,
                        control_rect: cr ? {x: cr.x, y: cr.y, w: cr.width, h: cr.height} : null,
                        button_exists: !!btn,
                        button_rect: br ? {x: br.x, y: br.y, w: br.width, h: br.height} : null,
                        icon_text: icon ? (icon.textContent || '').trim() : null,
                        icon_font_family: icon ? getComputedStyle(icon).fontFamily : null,
                        icon_feature: icon ? getComputedStyle(icon).fontFeatureSettings : null,
                        sidebar_width: sr ? sr.width : null,
                        literal_ligature_text_rendered_as_plain_font: icon ? (getComputedStyle(icon).fontFamily.includes('Material') === false) : null,
                    };
                }""")

            expanded = control_state()
            expanded["button_computed"] = page.evaluate("""() => {
                const btn = document.querySelector('[data-testid="stSidebarCollapseButton"] button');
                if (!btn) return null;
                const cs = getComputedStyle(btn);
                return {visibility: cs.visibility, opacity: cs.opacity, display: cs.display, pointer: cs.cursor};
            }""")
            evidence["expanded"] = expanded
            evidence["expanded"]["px_font_body_check"] = "-apple-system" in (expanded.get("icon_font_family") or "")
            page.screenshot(path=str(OUT / "c2_after_expanded.png"))

            def hover_then_click():
                # Hover the native control itself (the sidebar may be
                # collapsed, in which case the expand control sits outside
                # the visible sidebar section).
                try:
                    page.locator(button_sel).hover(timeout=3000)
                except Exception:
                    pass
                page.wait_for_timeout(400)
                try:
                    page.locator(button_sel).click(timeout=5000)
                except Exception:
                    page.locator(button_sel).click(force=True, timeout=5000)
                page.wait_for_timeout(1500)

            # Collapse via the native button (mouse click, hover-revealed)
            hover_then_click()
            collapsed = control_state()
            evidence["collapsed"] = collapsed
            page.screenshot(path=str(OUT / "c2_after_collapsed.png"))

            # Expand via the native button (mouse click)
            hover_then_click()
            evidence["expanded_again"] = control_state()

            # Keyboard activation: collapse then expand with Enter
            try:
                page.locator(button_sel).hover(timeout=3000)
            except Exception:
                pass
            page.wait_for_timeout(400)
            page.evaluate("""() => document.querySelector('[data-testid="stSidebarCollapseButton"] button').focus()""")
            page.keyboard.press("Enter")
            page.wait_for_timeout(1500)
            evidence["keyboard_collapse"] = control_state()
            evidence["collapsed_ligatures"] = ligature_elements()
            # The collapsed state exposes a separate visible expand control
            # (right-arrow ligature). Focus it via JS and activate with Enter.
            page.evaluate("""() => {
                const spans = Array.from(document.querySelectorAll('span'));
                const el = spans.find(s => (s.textContent || '').includes('keyboard_double_arrow_right'));
                const btn = el ? el.closest('button') : null;
                if (btn) btn.focus();
            }""")
            page.keyboard.press("Enter")
            page.wait_for_timeout(1500)
            evidence["keyboard_expand"] = control_state()
            evidence["expanded_ligatures"] = ligature_elements()
            # Ensure expanded before page navigation tests
            if (evidence["keyboard_expand"] or {}).get("sidebar_width") == 0:
                expand = page.evaluate("""() => {
                    const spans = Array.from(document.querySelectorAll('span'));
                    const el = spans.find(s => (s.textContent || '').includes('keyboard_double_arrow_right'));
                    const btn = el ? el.closest('button') : null;
                    if (btn) { btn.click(); return true; }
                    return false;
                }""")
                page.wait_for_timeout(1500)

            # Five student pages: sidebar behavior consistent
            pages = {}
            for label in ("Home", "Writing", "Feedback", "Revision", "Practice"):
                try:
                    page.locator('[data-testid="stSidebar"]').get_by_text(label, exact=True).first.click()
                    page.wait_for_timeout(1400)
                except Exception as exc:
                    pages[label] = {"error": str(exc).splitlines()[0][:120]}
                    continue
                state = control_state()
                state["navigated_to"] = label
                pages[label] = state
            evidence["pages"] = pages

            # Narrow viewport: verify the control and a full toggle
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(1200)
            narrow_expanded = control_state()
            evidence["narrow_viewport_390x844"] = {"expanded": narrow_expanded}
            # ensure expanded before the toggle test
            if narrow_expanded.get("sidebar_width") == 0:
                page.evaluate("""() => {
                    const spans = Array.from(document.querySelectorAll('span'));
                    const el = spans.find(s => (s.textContent || '').includes('keyboard_double_arrow_right'));
                    const btn = el ? el.closest('button') : null;
                    if (btn) btn.click();
                }""")
                page.wait_for_timeout(1500)
            try:
                page.locator(button_sel).hover(timeout=3000)
            except Exception:
                pass
            try:
                page.locator(button_sel).click(timeout=5000)
            except Exception:
                page.locator(button_sel).click(force=True, timeout=5000)
            page.wait_for_timeout(1500)
            evidence["narrow_viewport_390x844"]["collapsed"] = control_state()
            page.evaluate("""() => {
                const spans = Array.from(document.querySelectorAll('span'));
                const el = spans.find(s => (s.textContent || '').includes('keyboard_double_arrow_right'));
                const btn = el ? el.closest('button') : null;
                if (btn) btn.click();
            }""")
            page.wait_for_timeout(1500)
            evidence["narrow_viewport_390x844"]["expanded_again"] = control_state()
            page.screenshot(path=str(OUT / "c2_after_narrow.png"))
            browser.close()

        save_evidence()
        print(json.dumps(evidence, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        evidence["error"] = str(exc).splitlines()[0][:300]
        save_evidence()
        raise
    finally:
        for proc in (st, api):
            proc.terminate()
        for proc in (st, api):
            try:
                proc.wait(timeout=15)
            except Exception:
                proc.kill()
        shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())