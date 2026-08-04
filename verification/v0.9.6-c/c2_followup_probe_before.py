"""v0.9.6-C2 follow-up investigation: both sidebar controls, all states.

Captures computed styles and the exact matching CSS rules for the left
(collapse) and right (expand) controls in normal/hover/focus states,
expanded and collapsed sidebars.
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
TMP = Path(tempfile.mkdtemp(prefix="v096c2-inv-"))

env = dict(os.environ)
env["PYTHON_DOTENV_DISABLED"] = "1"
env.pop("DATABASE_URL", None)
env["DATABASE_PATH"] = str(TMP / "inv.db")
env["LLM_PROVIDER"] = "local"

api = subprocess.Popen([str(VENV_PY), "-m", "uvicorn", "app.api.main:app", "--host", "127.0.0.1", "--port", "8000"], cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
st = subprocess.Popen([str(VENV_PY), "-m", "streamlit", "run", "streamlit_app.py", "--server.headless", "true", "--server.port", "8501", "--browser.gatherUsageStats", "false"], cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_ready():
    for _ in range(120):
        try:
            if requests.get("http://127.0.0.1:8000/api/v1/system/health", timeout=1).status_code == 200 and requests.get("http://127.0.0.1:8501", timeout=1).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


CAPTURE_JS = """(sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    const pseudo_before = getComputedStyle(el, '::before');
    const pseudo_after = getComputedStyle(el, '::after');
    const matches = [];
    for (const sheet of document.styleSheets) {
        let rules;
        try { rules = sheet.cssRules; } catch (e) { continue; }
        for (const rule of rules) {
            if (!rule.selectorText) continue;
            let hit = false;
            try { hit = el.matches(rule.selectorText); } catch (e) { continue; }
            if (hit && rule.style.length > 0) {
                const props = {};
                for (let i = 0; i < rule.style.length; i++) {
                    const p = rule.style[i];
                    props[p] = rule.style.getPropertyValue(p);
                }
                if (props['font-family'] || props['visibility'] || props['opacity'] || props['font-feature-settings'] || props['font-variation-settings'] || props['color'] || props['font-size'] || props['display']) {
                    matches.push({selector: rule.selectorText, props: props});
                }
            }
        }
    }
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_ELEMENT);
    const descendants = [];
    let node;
    while ((node = walker.nextNode())) {
        descendants.push({tag: node.tagName, class_list: Array.from(node.classList), testid: node.getAttribute('data-testid'), text: (node.childNodes.length === 1 && node.firstChild.nodeType === 3) ? node.textContent.trim() : null});
    }
    return {
        tag: el.tagName, class_list: Array.from(el.classList),
        testid: el.getAttribute('data-testid'),
        text: (el.textContent || '').trim().slice(0, 60),
        rect: {x: r.x, y: r.y, w: r.width, h: r.height},
        visibility: cs.visibility, opacity: cs.opacity, display: cs.display,
        font_family: cs.fontFamily, font_feature: cs.fontFeatureSettings,
        font_variation: cs.fontVariationSettings, font_size: cs.fontSize,
        color: cs.color, cursor: cs.cursor,
        pseudo_before: {content: pseudo_before.content, font_family: pseudo_before.fontFamily},
        pseudo_after: {content: pseudo_after.content, font_family: pseudo_after.fontFamily},
        inherited_font_family: getComputedStyle(el.parentElement).fontFamily,
        matching_rules: matches,
        descendants: descendants,
    };
}"""


def capture(page, label, selector):
    return page.evaluate(CAPTURE_JS, selector)


def main():
    evidence = {"stage": "v0.9.6-C2", "kind": "c2_followup_before"}
    try:
        if not wait_ready():
            print("APP NOT READY")
            return 2
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto("http://127.0.0.1:8501", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3500)

            left_sel = '[data-testid="stSidebarCollapseButton"] button'
            right_sel = 'button[data-testid="stExpandSidebarButton"]'

            # Expanded: normal and hover
            evidence["expanded_normal_left"] = capture(page, "expanded-normal-left", left_sel)
            page.screenshot(path=str(OUT / "c2_fu_before_expanded_normal.png"))
            page.locator('[data-testid="stSidebar"]').hover()
            page.wait_for_timeout(500)
            evidence["expanded_hover_left"] = capture(page, "expanded-hover-left", left_sel)
            page.screenshot(path=str(OUT / "c2_fu_before_expanded_hover.png"))

            # Collapse
            page.evaluate("""() => { const b = document.querySelector('[data-testid="stSidebarCollapseButton"] button'); if (b) b.click(); }""")
            page.wait_for_timeout(1500)
            evidence["collapsed_normal_right"] = capture(page, "collapsed-normal-right", right_sel)
            page.screenshot(path=str(OUT / "c2_fu_before_collapsed_normal.png"))
            # hover the expand control position
            try:
                page.locator(right_sel).hover(timeout=3000)
            except Exception:
                pass
            page.wait_for_timeout(500)
            evidence["collapsed_hover_right"] = capture(page, "collapsed-hover-right", right_sel)
            page.screenshot(path=str(OUT / "c2_fu_before_collapsed_hover.png"))
            # focus state
            page.evaluate("""(sel) => { const b = document.querySelector(sel); if (b) b.focus(); }""", right_sel)
            page.keyboard.press("Tab")
            page.wait_for_timeout(300)
            evidence["collapsed_focus_right"] = capture(page, "collapsed-focus-right", right_sel)
            browser.close()

        with open(OUT / "c2_followup_before.json", "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
        print("BEFORE_EVIDENCE_WRITTEN")
        print(json.dumps({k: (v or {}).get("font_family") for k, v in evidence.items()}, indent=2))
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