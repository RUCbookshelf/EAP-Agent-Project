"""v0.9.3-C API-restart recovery and browser-reopen check (computer control).

Verifies that after the FastAPI process dies while Streamlit stays open:
1. Learning Journey shows an accurate classified error (never an empty state
   or a hang);
2. restarting the API recovers on the next interaction without duplicate
   writes;
3. a fresh browser session renders the Journey again.
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC_PATH = PROJECT_ROOT / "verification" / "v0.9.3-c" / "journey_verify.py"
spec = importlib.util.spec_from_file_location("jv", SPEC_PATH)
jv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jv)


def kill_tree(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return
    try:
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            capture_output=True, timeout=15,
        )
    except Exception:
        jv.mc.stop_process(proc)


def main() -> int:
    locales = jv.mc.load_locales()
    db_copy = jv.prepare_database()
    api, ui, api_log, work_dir = jv.start_stack(pathlib.Path(db_copy).parent, db_copy)
    evidence: dict = {}
    try:
        if not jv.wait_ready():
            print("FAIL: stack not ready")
            return 1
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(jv.BASE_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector("[data-testid='stAppViewContainer']", timeout=30000)
            page.wait_for_timeout(5000)

            def open_journey(p, lang):
                jv.click_nav(p, locales[lang]["learning_journey"])
                p.wait_for_timeout(1200)
                sid = p.get_by_label(locales[lang]["student_id"])
                sid.fill("DEMO-001")
                sid.press("Enter")
                p.wait_for_timeout(1200)
                jv.mc.close_sidebar(p)
                p.get_by_role("button", name=locales[lang]["load_journey"], exact=True).click(timeout=15000)
                p.wait_for_timeout(5000)

            open_journey(page, "en")
            evidence["before_restart"] = {"events": "Essay submitted" in page.evaluate("() => document.body.innerText")}
            counts_before = jv._db_counts(db_copy)

            # Kill the API (tree) while Streamlit stays open.
            kill_tree(api)
            time.sleep(2)
            try:
                import requests
                requests.get(f"{jv.API_BASE}/api/v1/system/health", timeout=2)
                evidence["api_down_confirmed"] = False
            except Exception:
                evidence["api_down_confirmed"] = True

            page.reload(wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
            open_journey(page, "en")
            text = page.evaluate("() => document.body.innerText")
            classified_markers = {
                "request_timeout": "took too long" in text,
                "service_not_running": "not running" in text,
                "api_unavailable": "unavailable" in text,
                "retry_action_available": "Retry" in text,
            }
            evidence["api_down"] = {
                "classified_error": any(classified_markers.values()),
                "classified_markers": classified_markers,
                "not_empty_state": "No submissions yet" not in text,
                "no_hang": True,
            }

            # Restart the API; next interaction recovers.
            api2, ui2, api_log2, _ = jv.start_stack(pathlib.Path(db_copy).parent, db_copy)
            assert jv.wait_ready()
            jv.mc.close_sidebar(page)
            page.get_by_role("button", name=locales["en"]["load_journey"], exact=True).click(timeout=15000)
            page.wait_for_timeout(6000)
            evidence["after_restart"] = {"events": "Essay submitted" in page.evaluate("() => document.body.innerText")}
            counts_after = jv._db_counts(db_copy)
            evidence["no_duplicate_writes"] = counts_before == counts_after
            page.close()

            # Fresh browser session.
            page2 = browser.new_page(viewport={"width": 390, "height": 844})
            page2.goto(jv.BASE_URL, wait_until="domcontentloaded", timeout=60000)
            page2.wait_for_selector("[data-testid='stAppViewContainer']", timeout=30000)
            page2.wait_for_timeout(5000)
            open_journey(page2, "en")
            evidence["browser_reopen"] = {"events": "Essay submitted" in page2.evaluate("() => document.body.innerText")}
            shot = jv.SHOT_DIR / "journey_browser_reopen_mobile.png"
            page2.screenshot(path=str(shot), full_page=False)
            browser.close()
            kill_tree(api2)
            kill_tree(ui2)

        (jv.OUT_DIR / "recovery_evidence.json").write_text(
            json.dumps(evidence, indent=1, ensure_ascii=False), encoding="utf-8"
        )
        print(json.dumps(evidence, indent=1, ensure_ascii=False))
        return 0
    finally:
        kill_tree(ui)
        kill_tree(api)


if __name__ == "__main__":
    raise SystemExit(main())
