"""v0.9.6-C2 Phase 0 probe: rendered sidebar collapse control inspection.

Starts the real API + Streamlit app against a fresh isolated database, drives
the browser with Playwright, and records the sidebar collapse control DOM and
computed styles in expanded/collapsed/hover/focus states.
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

TMP = Path(tempfile.mkdtemp(prefix="v096c2-probe-"))
DB = TMP / "probe.db"

env = dict(os.environ)
env["PYTHON_DOTENV_DISABLED"] = "1"
env.pop("DATABASE_URL", None)
env["DATABASE_PATH"] = str(DB)
env["LLM_PROVIDER"] = "local"

api_log = TMP / "api.log"
st_log = TMP / "streamlit.log"

api = subprocess.Popen(
    [str(VENV_PY), "-m", "uvicorn", "app.api.main:app", "--host", "127.0.0.1", "--port", "8000"],
    cwd=str(ROOT), env=env, stdout=open(api_log, "wb"), stderr=subprocess.STDOUT,
)
st = subprocess.Popen(
    [str(VENV_PY), "-m", "streamlit", "run", "streamlit_app.py",
     "--server.headless", "true", "--server.port", "8501",
     "--browser.gatherUsageStats", "false"],
    cwd=str(ROOT), env=env, stdout=open(st_log, "wb"), stderr=subprocess.STDOUT,
)


def wait_ready() -> bool:
    for _ in range(120):
        try:
            r = requests.get("http://127.0.0.1:8000/api/v1/system/health", timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def wait_streamlit() -> bool:
    for _ in range(120):
        try:
            r = requests.get("http://127.0.0.1:8501", timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main() -> int:
    evidence = {"stage": "v0.9.6-C2", "kind": "c2_sidebar_before", "app_started": False}
    try:
        if not wait_ready():
            print("API NOT READY")
            evidence["api_ready"] = False
            return 2
        if not wait_streamlit():
            print("STREAMLIT NOT READY")
            evidence["streamlit_ready"] = False
            return 2
        evidence["api_ready"] = True
        evidence["streamlit_ready"] = True

        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto("http://127.0.0.1:8501", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)
            page.screenshot(path=str(OUT / "c2_before_expanded.png"))

            def icon_info():
                """Collect every element containing the literal ligature text."""
                rows = page.evaluate("""() => {
                    const out = [];
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                    let node;
                    while ((node = walker.nextNode())) {
                        const t = (node.textContent || "").trim();
                        if (t.includes("keyboard_double_arrow")) {
                            const el = node.parentElement;
                            const r = el.getBoundingClientRect();
                            const cs = getComputedStyle(el);
                            out.push({
                                tag: el.tagName,
                                role: el.getAttribute("role"),
                                aria_label: el.getAttribute("aria-label"),
                                text: t,
                                class_list: Array.from(el.classList),
                                parent: el.parentElement ? el.parentElement.tagName + "." + Array.from(el.parentElement.classList).join(".") : null,
                                parent_testid: el.parentElement ? el.parentElement.getAttribute("data-testid") : null,
                                visible: r.width > 0 && r.height > 0,
                                rect: {x: r.x, y: r.y, w: r.width, h: r.height},
                                font_family: cs.fontFamily,
                                font_feature_settings: cs.fontFeatureSettings,
                                display: cs.display,
                                overflow: cs.overflow,
                                color: cs.color,
                                cursor: cs.cursor,
                            });
                        }
                    }
                    return out;
                }""")
                return rows

            # Expanded-state inspection
            expanded = icon_info()
            evidence["expanded"] = {"ligature_elements": expanded, "count": len(expanded)}

            # Sidebar and control attributes
            sidebar = page.evaluate("""() => {
                const sb = document.querySelector('[data-testid="stSidebar"]');
                const buttons = Array.from(document.querySelectorAll('button')).map(b => ({
                    aria: b.getAttribute('aria-label'),
                    testid: b.getAttribute('data-testid'),
                    title: b.getAttribute('title'),
                    text: (b.textContent || '').trim().slice(0, 80),
                }));
                return {sidebar_present: !!sb, buttons: buttons};
            }""")
            evidence["expanded"]["sidebar_and_buttons"] = sidebar

            # Collapse via the native control if identifiable
            collapsed_via = None
            for try_selector in (
                '[data-testid="stSidebarCollapseButton"]',
                'button[aria-label*="Close sidebar" i]',
                'button[aria-label*="close sidebar" i]',
            ):
                el = page.query_selector(try_selector)
                if el:
                    collapsed_via = try_selector
                    break
            evidence["expanded"]["collapse_control_selector"] = collapsed_via
            if collapsed_via:
                el = page.query_selector(collapsed_via)
                control = page.evaluate("""(sel) => {
                    const el = document.querySelector(sel);
                    if (!el) return null;
                    const r = el.getBoundingClientRect();
                    const cs = getComputedStyle(el);
                    const icon = el.querySelector('span');
                    const ics = icon ? getComputedStyle(icon) : null;
                    const ir = icon ? icon.getBoundingClientRect() : null;
                    return {
                        tag: el.tagName, role: el.getAttribute('role'),
                        aria_label: el.getAttribute('aria-label'),
                        title: el.getAttribute('title'),
                        class_list: Array.from(el.classList),
                        text: (el.textContent || '').trim(),
                        rect: {x: r.x, y: r.y, w: r.width, h: r.height},
                        display: cs.display, visibility: cs.visibility,
                        font_family: cs.fontFamily,
                        font_feature_settings: cs.fontFeatureSettings,
                        cursor: cs.cursor, color: cs.color,
                        icon: icon ? {
                            class_list: Array.from(icon.classList),
                            text: (icon.textContent || '').trim(),
                            rect: {x: ir.x, y: ir.y, w: ir.width, h: ir.height},
                            display: ics.display,
                            font_family: ics.fontFamily,
                            font_feature_settings: ics.fontFeatureSettings,
                        } : null,
                    };
                }""", collapsed_via)
                evidence["expanded"]["collapse_control"] = control
                el.scroll_into_view_if_needed()
                page.wait_for_timeout(300)
                page.screenshot(path=str(OUT / "c2_before_expanded_hover.png"))
                try:
                    el.click(force=True, timeout=5000)
                except Exception as exc:
                    evidence["expanded"]["click_error"] = str(exc).splitlines()[0][:200]
                page.wait_for_timeout(1500)

            # Collapsed-state inspection
            collapsed = icon_info()
            evidence["collapsed"] = {"ligature_elements": collapsed, "count": len(collapsed)}
            sidebar_after = page.evaluate("""() => {
                const sb = document.querySelector('[data-testid="stSidebar"]');
                if (!sb) return {sidebar_present: false};
                const r = sb.getBoundingClientRect();
                return {sidebar_present: true, rect: {x: r.x, y: r.y, w: r.width, h: r.height}, aria_hidden: sb.getAttribute('aria-hidden')};
            }""")
            evidence["collapsed"]["sidebar_state"] = sidebar_after
            page.screenshot(path=str(OUT / "c2_before_collapsed.png"))

            # Expand again if a control exists
            expand_selector = None
            for try_selector in (
                '[data-testid="stSidebarCollapseButton"]',
                'button[aria-label*="Open sidebar" i]',
                'button[aria-label*="open sidebar" i]',
            ):
                if page.query_selector(try_selector):
                    expand_selector = try_selector
                    break
            evidence["collapsed"]["expand_control_selector"] = expand_selector
            if expand_selector:
                try:
                    page.query_selector(expand_selector).click(force=True, timeout=5000)
                    page.wait_for_timeout(1500)
                    evidence["expanded_again"] = icon_info()
                except Exception as exc:
                    evidence["collapsed"]["expand_click_error"] = str(exc).splitlines()[0][:200]
            browser.close()

        with open(OUT / "c2_sidebar_before.json", "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
        print(json.dumps(evidence, indent=2, sort_keys=True))
        return 0
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