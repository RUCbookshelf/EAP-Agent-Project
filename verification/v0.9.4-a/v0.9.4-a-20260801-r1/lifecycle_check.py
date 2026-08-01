"""v0.9.4-A lifecycle/recovery verification (log-file stack, isolated DB).

Checks: /live, /ready, /health, /docs, /openapi, Streamlit; cold start; API
warm restart; API-down classified UI state (browser); recovery; process
cleanup.

Run: python verification/v0.9.4-a/v0.9.4-a-20260801-r1/lifecycle_check.py
"""

from __future__ import annotations

import json
import pathlib
import sys
import time

import requests
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from v094a_harness import (  # noqa: E402
    BASE,
    UI,
    prepare_isolated_db,
    select_page,
    select_role,
    start_api_process,
    start_stack,
    stop_process,
    stop_stack,
    wait_stable,
)


def wait_ready(timeout_s: float = 60) -> dict:
    deadline = time.monotonic() + timeout_s
    last = {}
    while time.monotonic() < deadline:
        last = requests.get(f"{BASE}/api/v1/system/ready", timeout=5).json()
        if last.get("ready"):
            return last
        time.sleep(0.5)
    return last


def main() -> int:
    prepare_isolated_db()
    api = streamlit = None
    results: dict = {}
    try:
        t0 = time.monotonic()
        api, streamlit = start_stack("lifecycle")
        results["cold_start_s"] = round(time.monotonic() - t0, 2)
        results["ready"] = wait_ready()["ready"]
        results["live"] = requests.get(f"{BASE}/api/v1/system/live", timeout=5).status_code
        results["ready_status"] = requests.get(f"{BASE}/api/v1/system/ready", timeout=5).status_code
        health = requests.get(f"{BASE}/api/v1/system/health", timeout=5)
        results["health_status"] = health.status_code
        results["health_migration"] = health.json().get("database_migration_version")
        results["docs"] = requests.get(f"{BASE}/docs", timeout=5).status_code
        results["openapi"] = requests.get(f"{BASE}/openapi.json", timeout=5).status_code
        results["streamlit"] = requests.get(UI, timeout=5).status_code

        # Warm restart: stop the API, restart it, wait for ready:true.
        stop_process(api)
        api = None
        time.sleep(1.0)
        api = start_api_process("lifecycle_warm")
        results["warm_restart_ready"] = wait_ready(60)

        # API-down classified UI state + recovery (browser).
        stop_process(api)
        api = None
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(UI, timeout=30000, wait_until="networkidle")
            wait_stable(page, expected="[data-testid='stAppViewContainer']")
            select_role(page, "research", "en")
            select_page(page, "Research Overview", "Research Overview")
            page.wait_for_timeout(8000)
            results["api_down"] = {
                "stException_count": page.locator('[data-testid="stException"]').count(),
                "classified_error_present": page.locator('[data-testid="px-notice"]').count() > 0,
            }
            api = start_api_process("lifecycle_recovery")
            results["recovery_ready"] = wait_ready(60)
            page.reload(wait_until="networkidle")
            wait_stable(page, expected="[data-testid='stAppViewContainer']")
            page.wait_for_timeout(4000)
            results["recovery"] = {
                "stException_count": page.locator('[data-testid="stException"]').count(),
            }
            browser.close()
    finally:
        stop_process(api)
        stop_stack(None, streamlit)

    evidence = HERE / "lifecycle_evidence.json"
    evidence.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    ok = (
        results.get("ready") is True
        and results.get("live") == 200
        and results.get("ready_status") == 200
        and results.get("health_status") == 200
        and results.get("health_migration") == 12
        and results.get("docs") == 200
        and results.get("streamlit") == 200
        and results.get("warm_restart_ready", {}).get("ready") is True
        and results.get("recovery_ready", {}).get("ready") is True
        and results.get("api_down", {}).get("stException_count", -1) == 0
        and results.get("api_down", {}).get("classified_error_present") is True
        and results.get("recovery", {}).get("stException_count", -1) == 0
    )
    print(f"LIFECYCLE CHECK: {'PASS' if ok else 'FAIL'} -> {evidence}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
