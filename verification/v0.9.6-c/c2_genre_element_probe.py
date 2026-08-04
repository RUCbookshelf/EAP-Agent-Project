"""v0.9.6-C2 follow-up 2: element-level screenshots of the Genre-area controls.

Usage: python c2_genre_element_probe.py <prefix>
Saves {prefix}_genre_selectbox.png, {prefix}_timing_expander.png,
{prefix}_tools_expander.png, {prefix}_writing_expanders_view.png and the
chevron client rects into {prefix}_rects.json.
"""
from __future__ import annotations

import json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
import requests

ROOT = Path(r"A:\EAP Agent Project\writing-feedback-mvp")
OUT = ROOT / "verification" / "v0.9.6-c"
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
TMP = Path(tempfile.mkdtemp(prefix="v096c2-elem-"))
env = dict(os.environ)
env["PYTHON_DOTENV_DISABLED"] = "1"
env.pop("DATABASE_URL", None)
env["DATABASE_PATH"] = str(TMP / "elem.db")
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


def main():
    prefix = sys.argv[1] if len(sys.argv) > 1 else "c2_genre_after_elements"
    rects = {}
    try:
        if not wait_ready():
            return 2
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto("http://127.0.0.1:8501", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3500)
            page.locator('[data-testid="stSidebar"]').get_by_text("Writing", exact=True).first.click()
            page.wait_for_timeout(1800)

            sel = page.locator('[data-testid="stSelectbox"]').filter(has_text="Genre").first
            sel.screenshot(path=str(OUT / f"{prefix}_genre_selectbox.png"))
            rects["genre_selectbox"] = sel.bounding_box()

            expanders = page.locator('div[data-testid="stExpander"]')
            for idx, label in ((0, "timing"), (1, "tools")):
                exp = expanders.nth(idx)
                exp.screenshot(path=str(OUT / f"{prefix}_{label}_expander.png"))
                rects[label] = {"expander": exp.bounding_box()}
                chevron = exp.locator('summary span[data-testid="stIconMaterial"]').first
                rects[label]["chevron"] = chevron.bounding_box()
                rects[label]["summary"] = exp.locator("summary").first.bounding_box()
                rects[label]["chevron_font"] = chevron.evaluate("(el) => getComputedStyle(el).fontFamily")

            expanders.nth(0).scroll_into_view_if_needed()
            page.wait_for_timeout(600)
            page.screenshot(path=str(OUT / f"{prefix}_writing_expanders_view.png"))
            browser.close()

        with open(OUT / f"{prefix}_rects.json", "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(rects, indent=2, sort_keys=True) + "\n")
        print(json.dumps(rects, indent=2, sort_keys=True))
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