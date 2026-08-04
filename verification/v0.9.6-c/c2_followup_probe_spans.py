"""v0.9.6-C2 follow-up: icon spans + left container rules, all states."""
from __future__ import annotations

import json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
import requests

ROOT = Path(r"A:\EAP Agent Project\writing-feedback-mvp")
OUT = ROOT / "verification" / "v0.9.6-c"
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
TMP = Path(tempfile.mkdtemp(prefix="v096c2-inv2-"))
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


RULE_DUMP = """(sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const cs = getComputedStyle(el);
    const matches = [];
    for (const sheet of document.styleSheets) {
        let rules; try { rules = sheet.cssRules; } catch (e) { continue; }
        for (const rule of rules) {
            if (!rule.selectorText) continue;
            let hit = false;
            try { hit = el.matches(rule.selectorText); } catch (e) { continue; }
            if (hit && (rule.style.getPropertyValue('visibility') || rule.style.getPropertyValue('opacity') || rule.style.getPropertyValue('font-family') || rule.style.getPropertyValue('font-variation-settings') || rule.style.getPropertyValue('font-feature-settings'))) {
                matches.push(rule.cssText.slice(0, 260));
            }
        }
    }
    return {
        visibility: cs.visibility, opacity: cs.opacity, display: cs.display,
        font_family: cs.fontFamily, font_variation: cs.fontVariationSettings,
        font_feature: cs.fontFeatureSettings, font_size: cs.fontSize, color: cs.color,
        matching_rules: matches,
    };
}"""


def main():
    evidence = {}
    try:
        if not wait_ready():
            return 2
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto("http://127.0.0.1:8501", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3500)

            # Expanded normal: left container + left icon span
            evidence["expanded_normal_left_container"] = page.evaluate(RULE_DUMP, '[data-testid="stSidebarCollapseButton"]')
            evidence["expanded_normal_left_icon"] = page.evaluate(RULE_DUMP, 'span[data-testid="stIconMaterial"]')
            page.locator('[data-testid="stSidebar"]').hover()
            page.wait_for_timeout(500)
            evidence["expanded_hover_left_icon"] = page.evaluate(RULE_DUMP, 'span[data-testid="stIconMaterial"]')

            # Collapse
            page.evaluate("""() => { const b = document.querySelector('[data-testid="stSidebarCollapseButton"] button'); if (b) b.click(); }""")
            page.wait_for_timeout(1500)
            evidence["collapsed_normal_right_button"] = page.evaluate(RULE_DUMP, 'button[data-testid="stExpandSidebarButton"]')
            evidence["collapsed_normal_right_icon"] = page.evaluate(RULE_DUMP, 'button[data-testid="stExpandSidebarButton"] span[data-testid="stIconMaterial"]')
            try:
                page.locator('button[data-testid="stExpandSidebarButton"]').hover(timeout=3000)
            except Exception:
                pass
            page.wait_for_timeout(500)
            evidence["collapsed_hover_right_icon"] = page.evaluate(RULE_DUMP, 'button[data-testid="stExpandSidebarButton"] span[data-testid="stIconMaterial"]')
            browser.close()

        with open(OUT / "c2_followup_spans.json", "w", encoding="utf-8", newline="\n") as fh:
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