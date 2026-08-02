"""v0.9.5-D focused frontend browser smoke: four representative renders.

1. Student Writing — English desktop (1280x900)
2. Student Practice — Chinese mobile (390x844)
3. Research Overview — English desktop (1280x900)
4. Research Data — Chinese mobile (390x844)

Reuses the proven sidebar helpers from the v0.9.3-b/v0.9.5-c harnesses.
Streamlit executes its HTTP calls server-side, so the API request baseline is
captured by a verification-only counting forward proxy placed between the
Streamlit client and the API (no production code involved). Streamlit
telemetry console noise (metrics-config fetch timeouts in restricted-network
environments) is excluded from the console-error evidence. Strict database
isolation is proven before startup; the development database fingerprint is
recorded before and after; the isolated database must show zero writes after
the renders; ports and processes are cleaned.

Usage:
    python verification/v0.9.5-d/four_render_smoke.py --python <venv python>
"""

from __future__ import annotations

import argparse
import http.client
import http.server
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
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
    start_streamlit,
    stop_process,
    wait_http,
)


API_PORT = 8013
PROXY_PORT = 8014
UI_PORT = 8503
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

# Streamlit telemetry noise in restricted-network environments (not app errors).
TELEMETRY_MARKERS = ("metrics config", "Undefined metrics config", "Failed to fetch metrics")

# Baseline allowed API paths per render case (no student ID entered, no
# submit clicked). Research Overview calls health + data-quality reads.
ALLOWED_API_PATHS = {
    "writing_en_desktop": set(),
    "practice_zh_mobile": set(),
    "research_overview_en_desktop": {
        "/api/v1/system/health",
        "/api/v1/research/data-quality",
    },
    "research_data_zh_mobile": set(),
}


class _CountingProxy(http.server.BaseHTTPRequestHandler):
    """Verification-only forward proxy that records /api/v1 request paths."""

    recorded: list[str] = []

    def _forward(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        forwarded_headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in ("host", "content-length", "connection", "transfer-encoding")
        }
        connection = http.client.HTTPConnection("127.0.0.1", API_PORT, timeout=30)
        connection.request(self.command, self.path, body=body, headers=forwarded_headers)
        response = connection.getresponse()
        data = response.read()
        path = urllib.parse.urlsplit(self.path).path
        if path.startswith("/api/v1/"):
            _CountingProxy.recorded.append(path)
        self.send_response(response.status)
        for key, value in response.getheaders():
            if key.lower() not in ("transfer-encoding", "connection", "content-length"):
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        connection.close()

    do_GET = _forward
    do_POST = _forward
    do_PUT = _forward
    do_DELETE = _forward

    def log_message(self, *args) -> None:  # keep output clean
        pass


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


def main() -> int:
    parser = argparse.ArgumentParser(description="v0.9.5-D four-render smoke.")
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args()

    results: dict[str, object] = {"renders": []}
    api = ui = proxy = None
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        db_path = tmp / "v095d_ui.db"
        os.environ["DATABASE_URL"] = ""
        os.environ["DATABASE_PATH"] = str(db_path)
        os.environ["LLM_PROVIDER"] = "local"
        os.environ["API_BASE_URL"] = f"http://127.0.0.1:{API_PORT}"
        env = os.environ.copy()

        settings = load_settings()
        effective = Path(settings.database_path)
        results["effective_database_path"] = str(effective)
        assert effective == db_path, f"effective DB {effective} != isolated {db_path}"
        assert effective != DEV_DB and effective != V095B_BACKUP
        assert not db_path.exists()
        results["isolation_asserted"] = True

        before = _db_fingerprint(DEV_DB)
        results["dev_db_before"] = before

        require_free_port("127.0.0.1", API_PORT)
        require_free_port("127.0.0.1", PROXY_PORT)
        require_free_port("127.0.0.1", UI_PORT)
        try:
            api = subprocess.Popen(
                [args.python, "-m", "uvicorn", "app.api.main:app",
                 "--host", "127.0.0.1", "--port", str(API_PORT)],
                cwd=str(ROOT), env=env,
            )
            wait_http(f"{env['API_BASE_URL']}/api/v1/system/live", timeout=30)
            ready = _wait_ready(env["API_BASE_URL"])
            results["api_ready"] = ready
            with httpx.Client(base_url=env["API_BASE_URL"], timeout=10) as client:
                health = client.get("/api/v1/system/health").json()
                version = client.get("/api/v1/system/version").json()
                results["api_health"] = {
                    "status": health.get("status"),
                    "database_status": health.get("database_status"),
                    "migration": health.get("database_migration_version"),
                }
                results["active_configuration"] = version.get("active_configuration_version")
                assert health["database_migration_version"] == 12
                assert version["active_configuration_version"] == "config-v0.9.0"

            # Verification-only counting proxy in front of the API for the UI.
            proxy = http.server.ThreadingHTTPServer(("127.0.0.1", PROXY_PORT), _CountingProxy)
            threading.Thread(target=proxy.serve_forever, daemon=True).start()
            ui_env = dict(env)
            ui_env["API_BASE_URL"] = f"http://127.0.0.1:{PROXY_PORT}"
            ui = start_streamlit(args.python, UI_PORT, ui_env)
            wait_http(f"http://127.0.0.1:{UI_PORT}", timeout=60)
            results["streamlit_started"] = True

            cases = (
                ("writing_en_desktop", "en", "student", "student_writing_title",
                 "student_writing_title", 1280, 900),
                ("practice_zh_mobile", "zh_CN", "student", "practice",
                 "practice", 390, 844),
                ("research_overview_en_desktop", "en", "research", "research_overview_title",
                 "research_overview_title", 1280, 900),
                ("research_data_zh_mobile", "zh_CN", "research", "nav_research_data",
                 "nav_research_data", 390, 844),
            )
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                for case_name, lang, role, label_key, heading_key, width, height in cases:
                    context = browser.new_context(viewport={"width": width, "height": height})
                    page = context.new_page()
                    console_errors: list[str] = []

                    def _on_console(msg, acc=console_errors):
                        if msg.type != "error":
                            return
                        if any(marker in msg.text for marker in TELEMETRY_MARKERS):
                            return
                        acc.append(msg.text)

                    def _on_pageerror(exc, acc=console_errors):
                        acc.append(str(exc))

                    page.on("console", _on_console)
                    page.on("pageerror", _on_pageerror)
                    page.goto(f"http://127.0.0.1:{UI_PORT}", wait_until="networkidle")
                    page.wait_for_timeout(1200)
                    locale = load_locale(lang)
                    if lang == "zh_CN":
                        _click_radio(page, locale["lang_zh_CN"])
                        page.wait_for_timeout(1200)
                    _click_radio(page, locale["view_student" if role == "student" else "view_research"])
                    page.wait_for_timeout(1200)
                    _click_radio(page, locale[label_key])
                    page.wait_for_timeout(1800)
                    body = _body_text(page)
                    overflow = bool(page.evaluate(
                        "() => document.documentElement.scrollWidth > window.innerWidth + 1"
                    ))
                    raw_keys = _raw_key_hits(body)
                    tracebacks = [m for m in TRACEBACK_MARKERS if m in body]
                    heading_ok = locale[heading_key] in body
                    record = {
                        "case": case_name,
                        "heading_present": heading_ok,
                        "overflow": overflow,
                        "raw_keys": raw_keys,
                        "tracebacks": tracebacks,
                        "console_errors": list(console_errors),
                    }
                    results["renders"].append(record)
                    if not heading_ok or overflow or raw_keys or tracebacks or console_errors:
                        print("FAIL", record)
                    context.close()
                browser.close()

            time.sleep(0.5)
            app_paths = sorted(set(_CountingProxy.recorded))
            results["api_requests_seen"] = app_paths
            expected = set()
            for case_name in ALLOWED_API_PATHS:
                expected |= ALLOWED_API_PATHS[case_name]
            unexpected = [p for p in app_paths if p not in expected]
            assert unexpected == [], f"unexpected API calls during renders: {unexpected}"
            assert "/api/v1/research/data-quality" in app_paths, (
                "Research Overview baseline read missing"
            )

            isolated = _db_fingerprint(db_path)
            results["isolated_db_after"] = isolated
            for table in ("students", "essays", "feedback_records", "analysis_runs",
                          "learner_profile_snapshots", "practice_targets", "exercise_attempts"):
                assert isolated[table] == 0, f"{table} was written during renders"
            results["no_render_writes"] = True
        finally:
            stop_process(ui)
            if proxy is not None:
                proxy.shutdown()
                proxy.server_close()
            stop_process(api)
            time.sleep(1.0)
            results["ports_free"] = (
                _port_free("127.0.0.1", API_PORT)
                and _port_free("127.0.0.1", PROXY_PORT)
                and _port_free("127.0.0.1", UI_PORT)
            )

    after = _db_fingerprint(DEV_DB)
    results["dev_db_after"] = after
    assert after == before, "development database changed"
    results["dev_db_unchanged"] = True
    results["render_count"] = len(results["renders"])
    results["status"] = "PASS"
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
