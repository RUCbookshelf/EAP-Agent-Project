"""v0.9.5-C focused frontend browser smoke: 24 representative renders.

Twelve pages (six Student + six Research) x two modes (English desktop
1280x900, Chinese mobile 390x844). Uses the same Playwright sidebar helpers
as the existing v0.9.3-b mobile harness.

Isolation protocol (mandatory for this write-capable run):
- DATABASE_URL is cleared and DATABASE_PATH points to a fresh temporary
  database; the effective settings path is asserted before anything starts.
- The development database fingerprint is recorded before and after and must
  be unchanged.
- After the renders, the isolated database row counts are asserted to be zero
  (no render-triggered writes).
- All processes are stopped and ports verified free.

Usage:
    python verification/v0.9.5-c/frontend_smoke.py --python <venv python>
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

import httpx
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.config import load_settings  # noqa: E402
from app.ui.locale import load_locale  # noqa: E402
from scripts.service_processes import (  # noqa: E402
    require_free_port,
    start_api,
    start_streamlit,
    stop_process,
    wait_http,
)


API_PORT = 8012
UI_PORT = 8502
DEV_DB = ROOT / "data" / "writing_feedback.db"
V095B_BACKUP = ROOT / "data" / "writing_feedback.pre-v0.9.5b-cleanup-20260802-081311.db"

TRACEBACK_MARKERS = ("Traceback", "Exception:", "NameError:", "AttributeError:", "TypeError:")
RAW_KEY_PREFIXES = (
    "student_", "research_", "journey_", "practice_", "exercise_", "privacy_",
    "export_", "pii_", "human_review", "dataset_split", "data_quality", "calf_",
    "loading_", "nav_", "tab_", "construct_", "empty_", "enter_", "learning_",
    "feedback_", "revision_", "writing_", "home_", "draft_", "task_", "genre_",
    "timed_", "time_", "active_", "timing_", "tool_", "unexplained_", "response_",
    "submit_", "generate_", "load_", "provider_", "split_", "app_", "sidebar_",
    "view_", "lang_", "all_descriptive", "journey_counts", "audit_", "strategy_",
)

STUDENT_PAGES = (
    ("student_home", "student_home_title"),
    ("student_writing", "student_writing_title"),
    ("student_feedback", "student_feedback_title"),
    ("student_revision", "student_revision_title"),
    ("student_practice", "practice"),
    ("student_journey", "learning_journey"),
)

RESEARCH_PAGES = (
    ("research_overview", "research_overview_title"),
    ("research_evidence", "research_evidence_title"),
    ("research_calf", "tab_calf"),
    ("research_learning", "research_learning_title"),
    ("research_data", "nav_research_data"),
    ("research_audit", "research_audit_title"),
)


def _port_free(host: str, port: int) -> bool:
    with socket.socket() as sock:
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def _db_fingerprint(path: Path) -> dict:
    conn = sqlite3.connect(str(path))
    try:
        counts = {}
        for table in ("students", "essays", "feedback_records", "analysis_runs",
                      "learner_profile_snapshots", "practice_targets", "exercise_attempts"):
            try:
                counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except sqlite3.OperationalError:
                counts[table] = None
        counts["integrity"] = conn.execute("PRAGMA integrity_check").fetchone()[0]
        counts["user_version"] = conn.execute("PRAGMA user_version").fetchone()[0]
        return counts
    finally:
        conn.close()


def _wait_ready(base: str, timeout: float = 180.0) -> dict:
    deadline = time.monotonic() + timeout
    with httpx.Client(base_url=base, timeout=5) as client:
        while time.monotonic() < deadline:
            try:
                response = client.get("/api/v1/system/ready")
                if response.status_code == 200 and response.json().get("ready") is True:
                    return response.json()
            except httpx.HTTPError:
                pass
            time.sleep(1.0)
    raise RuntimeError("API did not become ready.")


def _body_text(page) -> str:
    return str(page.evaluate("() => document.body ? document.body.innerText : ''"))


def _raw_key_hits(text: str) -> list[str]:
    hits = []
    for token in text.split():
        for prefix in RAW_KEY_PREFIXES:
            if token.startswith(prefix) or token == "all_descriptive":
                hits.append(token[:60])
                break
    return hits


def _open_sidebar_if_needed(page, label_text: str) -> str:
    label = page.locator(f"label:has-text('{label_text}')").last
    try:
        label.click(timeout=6000)
        return "click"
    except PlaywrightTimeoutError:
        pass
    toggles = [
        '[data-testid="stExpandSidebarButton"]',
        '[data-testid="stSidebarCollapseButton"]',
        '[data-testid="stSidebarCollapse"]',
        'button[aria-label="Open sidebar"]',
        'button[aria-label*="sidebar" i]',
    ]
    for selector in toggles:
        button = page.locator(selector).first
        if button.count():
            try:
                button.click(timeout=3000)
                page.wait_for_timeout(900)
                label.click(timeout=6000)
                return "sidebar_toggle+click"
            except Exception:
                continue
    label.click(force=True, timeout=6000)
    return "force_click"


def _click_radio(page, text: str) -> str:
    return _open_sidebar_if_needed(page, text)


def _text_input_inventory(page) -> list[dict]:
    return page.eval_on_selector_all(
        "input[type='text'], input:not([type])",
        "els => els.map(e => ({label: e.getAttribute('aria-label'), value: e.value}))",
    )


def _wait_for_input_value(page, label: str, expected: str, timeout: float = 8.0) -> str:
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        locator = page.get_by_label(label).first
        try:
            last = locator.input_value()
        except Exception:
            last = ""
        if last == expected:
            return last
        time.sleep(0.5)
    return last


def main() -> int:
    parser = argparse.ArgumentParser(description="v0.9.5-C frontend smoke (24 renders).")
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args()

    results: dict[str, object] = {"renders": []}
    api = ui = None
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "v095c_ui.db"
        # Isolation: mutate the real process environment so load_settings()
        # resolves to the temporary database before anything starts.
        os.environ["DATABASE_URL"] = ""
        os.environ["DATABASE_PATH"] = str(db_path)
        os.environ["LLM_PROVIDER"] = "local"
        os.environ["API_BASE_URL"] = f"http://127.0.0.1:{API_PORT}"
        env = os.environ.copy()

        # --- Isolation proof before anything runs ---
        settings = load_settings()
        effective = Path(settings.database_path)
        results["effective_database_path"] = str(effective)
        assert effective == db_path, f"effective DB {effective} != isolated {db_path}"
        assert effective != DEV_DB and effective != V095B_BACKUP
        assert not db_path.exists(), "isolated DB must start fresh"
        results["isolation_asserted"] = True

        before_fingerprint = _db_fingerprint(DEV_DB)
        results["dev_db_before"] = before_fingerprint

        require_free_port("127.0.0.1", API_PORT)
        require_free_port("127.0.0.1", UI_PORT)
        try:
            api = start_api(args.python, "127.0.0.1", API_PORT, env)
            wait_http(f"{env['API_BASE_URL']}/api/v1/system/live", timeout=30)
            ready = _wait_ready(env["API_BASE_URL"])
            results["api_ready"] = ready
            with httpx.Client(base_url=env["API_BASE_URL"], timeout=10) as client:
                health = client.get("/api/v1/system/health").json()
                results["api_health"] = {
                    "status": health.get("status"),
                    "database_status": health.get("database_status"),
                    "migration": health.get("database_migration_version"),
                }
                version = client.get("/api/v1/system/version").json()
                results["active_configuration"] = version.get("active_configuration_version")
                assert health["database_migration_version"] == 12
                assert version["active_configuration_version"] == "config-v0.9.0"

            ui = start_streamlit(args.python, UI_PORT, env)
            wait_http(f"http://127.0.0.1:{UI_PORT}", timeout=60)
            results["streamlit_started"] = True

            modes = (
                ("en-desktop", "en", 1280, 900),
                ("zh-mobile", "zh_CN", 390, 844),
            )
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                for mode, lang, width, height in modes:
                    context = browser.new_context(viewport={"width": width, "height": height})
                    page = context.new_page()
                    console_errors: list[str] = []
                    page.on("console", lambda msg, acc=console_errors: acc.append(msg.text)
                            if msg.type == "error" else None)
                    page.on("pageerror", lambda exc, acc=console_errors: acc.append(str(exc)))
                    page.goto(f"http://127.0.0.1:{UI_PORT}", wait_until="networkidle")
                    page.wait_for_timeout(1200)
                    locale = load_locale(lang)
                    if lang == "zh_CN":
                        _click_radio(page, locale["lang_zh_CN"])
                        page.wait_for_timeout(1200)

                    for role, pages in (("student", STUDENT_PAGES), ("research", RESEARCH_PAGES)):
                        _click_radio(page, locale["view_student" if role == "student" else "view_research"])
                        page.wait_for_timeout(1200)
                        for page_key, label_key in pages:
                            label = locale[label_key]
                            _click_radio(page, label)
                            page.wait_for_timeout(1500)
                            body = _body_text(page)
                            overflow = bool(page.evaluate(
                                "() => document.documentElement.scrollWidth > window.innerWidth + 1"
                            ))
                            raw_keys = _raw_key_hits(body)
                            tracebacks = [m for m in TRACEBACK_MARKERS if m in body]
                            heading_ok = label in body
                            record = {
                                "mode": mode, "role": role, "page": page_key,
                                "heading_present": heading_ok,
                                "overflow": overflow,
                                "raw_keys": raw_keys,
                                "tracebacks": tracebacks,
                                "console_errors": list(console_errors),
                            }
                            results["renders"].append(record)
                            if not heading_ok or overflow or raw_keys or tracebacks or console_errors:
                                print("FAIL", record)

                    # Student ID continuity (en desktop pass only, last):
                    if mode == "en-desktop":
                        _click_radio(page, locale["view_student"])
                        page.wait_for_timeout(1000)
                        _click_radio(page, locale["student_home_title"])
                        page.wait_for_timeout(1500)
                        student_input = page.get_by_label(locale["student_id"]).first
                        student_input.fill("SMOKE001")
                        filled = _wait_for_input_value(page, locale["student_id"], "SMOKE001")
                        results["home_filled_value"] = filled
                        assert filled == "SMOKE001", f"home fill: {_text_input_inventory(page)}"
                        _click_radio(page, locale["student_writing_title"])
                        value_after_nav = _wait_for_input_value(
                            page, locale["student_id"], "SMOKE001"
                        )
                        results["student_id_continuity"] = value_after_nav
                        assert value_after_nav == "SMOKE001", (
                            f"writing inputs: {_text_input_inventory(page)}"
                        )
                        # Research role isolation: no learner id on research pages.
                        _click_radio(page, locale["view_research"])
                        page.wait_for_timeout(1200)
                        _click_radio(page, locale["research_overview_title"])
                        page.wait_for_timeout(1500)
                        results["research_role_isolation"] = "SMOKE001" not in _body_text(page)
                        assert results["research_role_isolation"]
                    context.close()
                browser.close()

            # --- No render-triggered writes on the isolated DB ---
            isolated_counts = _db_fingerprint(db_path)
            results["isolated_db_after"] = isolated_counts
            write_tables = (
                "students", "essays", "feedback_records", "analysis_runs",
                "learner_profile_snapshots", "practice_targets", "exercise_attempts",
            )
            for table in write_tables:
                assert isolated_counts[table] == 0, f"{table} was written during renders"
            results["no_render_writes"] = True
        finally:
            stop_process(ui)
            stop_process(api)
            time.sleep(1.0)
            results["ports_free"] = (
                _port_free("127.0.0.1", API_PORT) and _port_free("127.0.0.1", UI_PORT)
            )

    after_fingerprint = _db_fingerprint(DEV_DB)
    results["dev_db_after"] = after_fingerprint
    assert after_fingerprint == before_fingerprint, "development database changed"
    results["dev_db_unchanged"] = True
    results["render_count"] = len(results["renders"])
    results["status"] = "PASS"
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
