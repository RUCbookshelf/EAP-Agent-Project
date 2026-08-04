"""v0.9.6-C2 follow-up after-state evidence: both controls, all states."""
from __future__ import annotations

import json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
import requests

ROOT = Path(r"A:\EAP Agent Project\writing-feedback-mvp")
OUT = ROOT / "verification" / "v0.9.6-c"
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
TMP = Path(tempfile.mkdtemp(prefix="v096c2-after2-"))
env = dict(os.environ)
env["PYTHON_DOTENV_DISABLED"] = "1"
env.pop("DATABASE_URL", None)
env["DATABASE_PATH"] = str(TMP / "after.db")
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


CAP = """(sels) => {
    const btn = document.querySelector(sels[0]);
    const icon = document.querySelector(sels[1]);
    if (!btn) return null;
    const bcs = getComputedStyle(btn);
    const br = btn.getBoundingClientRect();
    const ics = icon ? getComputedStyle(icon) : null;
    const ir = icon ? icon.getBoundingClientRect() : null;
    return {
        visibility: bcs.visibility, opacity: bcs.opacity, display: bcs.display,
        rect: {x: br.x, y: br.y, w: br.width, h: br.height},
        icon_font: ics ? ics.fontFamily : null,
        icon_feature: ics ? ics.fontFeatureSettings : null,
        icon_text: icon ? (icon.textContent || '').trim() : null,
        icon_rect: ir ? {x: ir.x, y: ir.y, w: ir.width, h: ir.height} : null,
    };
}"""

LEFT_BTN = '[data-testid="stSidebarCollapseButton"] button'
LEFT_ICON = '[data-testid="stSidebarCollapseButton"] span[data-testid="stIconMaterial"]'
RIGHT_BTN = 'button[data-testid="stExpandSidebarButton"]'
RIGHT_ICON = 'button[data-testid="stExpandSidebarButton"] span[data-testid="stIconMaterial"]'


def cap(page, btn, icon):
    return page.evaluate(CAP, [btn, icon])


def main():
    evidence = {"stage": "v0.9.6-C2", "kind": "c2_followup_after"}
    try:
        if not wait_ready():
            return 2
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto("http://127.0.0.1:8501", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3500)

            evidence["expanded_normal_left"] = cap(page, LEFT_BTN, LEFT_ICON)
            page.screenshot(path=str(OUT / "c2_fu_after_expanded_normal.png"))
            page.locator('[data-testid="stSidebar"]').hover()
            page.wait_for_timeout(500)
            evidence["expanded_hover_left"] = cap(page, LEFT_BTN, LEFT_ICON)
            page.screenshot(path=str(OUT / "c2_fu_after_expanded_hover.png"))

            page.evaluate("""() => { const b = document.querySelector('[data-testid="stSidebarCollapseButton"] button'); if (b) b.click(); }""")
            page.wait_for_timeout(1500)
            evidence["collapsed_normal_right"] = cap(page, RIGHT_BTN, RIGHT_ICON)
            page.screenshot(path=str(OUT / "c2_fu_after_collapsed_normal.png"))
            try:
                page.locator(RIGHT_BTN).hover(timeout=3000)
            except Exception:
                pass
            page.wait_for_timeout(500)
            evidence["collapsed_hover_right"] = cap(page, RIGHT_BTN, RIGHT_ICON)
            page.screenshot(path=str(OUT / "c2_fu_after_collapsed_hover.png"))

            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(1200)
            page.evaluate("""() => { const b = document.querySelector('button[data-testid="stExpandSidebarButton"]'); if (b) b.click(); }""")
            page.wait_for_timeout(1500)
            evidence["narrow_expanded_left"] = cap(page, LEFT_BTN, LEFT_ICON)
            page.screenshot(path=str(OUT / "c2_fu_after_narrow_expanded.png"))
            browser.close()

        with open(OUT / "c2_followup_after.json", "w", encoding="utf-8", newline="\n") as fh:
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