"""Reusable v0.9.4-A verification harness.

Design rules (execution-correction instructions):
- The API/Streamlit stack always writes logs to files (never unread pipes,
  which can fill and block a long session).
- Browser helpers act on stable roles/labels/data-testids and VERIFY the
  resulting semantic state after each action, with bounded retries.
- Streamlit stabilization uses semantic evidence (no running indicator,
  expected selector present, DOM signature stable for a short interval),
  not bare sleeps.
- Chinese text is never passed through PowerShell pipelines; all Chinese in
  this module is stored as UTF-8 by apply_patch.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import time

import requests

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
RUN_DIR = pathlib.Path(__file__).resolve().parent
ISOLATED_DB = RUN_DIR / "isolated" / "writing_feedback_v094a.db"
LOG_DIR = RUN_DIR / "logs"

API_PORT = 8000
STREAMLIT_PORT = 8501
BASE = f"http://127.0.0.1:{API_PORT}"
UI = f"http://127.0.0.1:{STREAMLIT_PORT}"

ALLOWED_CONSOLE = [
    "Download the React DevTools",
    "is not accessed",
    "Autofill processing",
]


def prepare_isolated_db() -> pathlib.Path:
    """Copy the development DB to the isolated run copy (idempotent)."""
    source = PROJECT_ROOT / "data" / "writing_feedback.db"
    ISOLATED_DB.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, ISOLATED_DB)
    con = sqlite3.connect(ISOLATED_DB)
    con.execute(
        "INSERT OR IGNORE INTO students (student_id, created_at, is_synthetic) "
        "VALUES ('EMPTY01', '2026-08-01T00:00:00+00:00', 1)"
    )
    con.commit()
    con.close()
    return ISOLATED_DB


def stack_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["LLM_PROVIDER"] = "local"
    env["DATABASE_PATH"] = str(ISOLATED_DB)
    env["DATABASE_URL"] = f"sqlite:///{ISOLATED_DB.as_posix()}"
    env["API_BASE_URL"] = BASE
    return env


def _log_handle(label: str, suffix: str):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return (LOG_DIR / f"{label}_{suffix}.log").open("w", encoding="utf-8", errors="replace")


def start_api_process(label: str):
    """Start only the API with a log file; returns the Popen handle."""
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.service_processes import require_free_port, wait_http

    require_free_port("127.0.0.1", API_PORT)
    api_log = _log_handle(label, "api")
    api = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.api.main:app", "--host", "127.0.0.1", "--port", str(API_PORT)],
        cwd=str(PROJECT_ROOT), env=stack_env(), stdout=api_log, stderr=subprocess.STDOUT,
    )
    api._v094a_log = api_log
    wait_http(f"{BASE}/api/v1/system/ready", timeout=60)
    return api


def start_streamlit_process(label: str):
    """Start only Streamlit with a log file; returns the Popen handle."""
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.service_processes import require_free_port, wait_http

    require_free_port("127.0.0.1", STREAMLIT_PORT)
    ui_log = _log_handle(label, "streamlit")
    streamlit = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
         "--server.headless", "true", "--server.port", str(STREAMLIT_PORT),
         "--browser.gatherUsageStats", "false"],
        cwd=str(PROJECT_ROOT), env=stack_env(), stdout=ui_log, stderr=subprocess.STDOUT,
    )
    streamlit._v094a_log = ui_log
    wait_http(UI, timeout=60)
    return streamlit


def start_stack(label: str):
    """Start API + Streamlit with log files. Returns (api, streamlit)."""
    api = start_api_process(label)
    streamlit = start_streamlit_process(label)
    return api, streamlit


def stop_stack(api, streamlit) -> None:
    """Stop processes and assert the ports are free again."""
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.service_processes import require_free_port, stop_process

    for proc in (streamlit, api):
        if proc is not None:
            stop_process(proc)
            handle = getattr(proc, "_v094a_log", None)
            if handle is not None:
                try:
                    handle.close()
                except Exception:
                    pass
    time.sleep(0.5)
    require_free_port("127.0.0.1", API_PORT)
    require_free_port("127.0.0.1", STREAMLIT_PORT)


def stop_process(proc) -> None:
    """Stop one process and close its log handle."""
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.service_processes import stop_process as _stop

    if proc is not None:
        _stop(proc)
        handle = getattr(proc, "_v094a_log", None)
        if handle is not None:
            try:
                handle.close()
            except Exception:
                pass


# ── Semantic browser helpers ───────────────────────────────────────────

def running_indicators(page) -> int:
    """Count active Streamlit running indicators (semantic sync evidence)."""
    return page.evaluate(
        "() => ['stStatusWidget', 'stSpinner', 'stProgress']"
        ".reduce((n, id) => n + document.querySelectorAll(`[data-testid='${id}']`).length, 0)"
    )


def dom_signature(page) -> str:
    return page.evaluate(
        "() => { const h = [...document.querySelectorAll('h1,h2,h3')].map(e => e.innerText.trim()).join('|'); "
        "const b = document.querySelectorAll('button').length; return h + '#' + b; }"
    )


def wait_stable(
    page,
    *,
    expected: str | None = None,
    timeout: float = 20.0,
) -> bool:
    """Wait until Streamlit is stable: no running indicator, expected
    selector present (optional), and the DOM signature unchanged across two
    consecutive bounded polls."""
    deadline = time.monotonic() + timeout
    last_sig = None
    stable_count = 0
    while time.monotonic() < deadline:
        if expected is not None and page.locator(expected).count() == 0:
            last_sig = None
            stable_count = 0
            time.sleep(0.3)
            continue
        if running_indicators(page) > 0:
            last_sig = None
            stable_count = 0
            time.sleep(0.3)
            continue
        sig = dom_signature(page)
        if sig == last_sig:
            stable_count += 1
            if stable_count >= 2:
                return True
        else:
            stable_count = 0
        last_sig = sig
        time.sleep(0.3)
    return False


def open_sidebar(page) -> None:
    """Open the collapsed sidebar on narrow viewports; no-op on desktop."""
    if page.viewport_size and page.viewport_size["width"] < 700:
        for selector in (
            '[data-testid="stExpandSidebarButton"]',
            '[data-testid="stSidebarCollapsedControl"]',
        ):
            toggle = page.locator(selector)
            if toggle.count() > 0:
                try:
                    toggle.first.click(timeout=4000)
                    page.wait_for_timeout(800)
                    return
                except Exception:
                    continue


def close_sidebar(page) -> None:
    """Close the mobile sidebar overlay so it cannot intercept content."""
    if page.viewport_size and page.viewport_size["width"] >= 700:
        return
    section = page.locator('[data-testid="stSidebar"]')
    for _ in range(3):
        if section.count() == 0 or section.first.get_attribute("aria-expanded") != "true":
            return
        for selector in (
            '[data-testid="stSidebarCollapsedControl"]',
            '[data-testid="stExpandSidebarButton"]',
            'button[aria-label="Close sidebar"]',
        ):
            toggle = page.locator(selector).first
            if toggle.count() > 0:
                try:
                    toggle.click(timeout=4000)
                    page.wait_for_timeout(800)
                    break
                except Exception:
                    continue
        else:
            page.keyboard.press("Escape")
            page.wait_for_timeout(800)


def radio_indices(page) -> list[int]:
    """Checked index per [role=radiogroup] (language, role, pages)."""
    return page.evaluate(
        "() => [...document.querySelectorAll('[role=radiogroup]')].map(g => "
        "[...g.querySelectorAll('input')].findIndex(i => i.checked))"
    )


def radio_option_labels(page) -> list[list[str]]:
    return page.evaluate(
        "() => [...document.querySelectorAll('[role=radiogroup]')].map(g => "
        "[...g.querySelectorAll('label')].map(l => l.innerText.trim().slice(0, 24)))"
    )


def current_h2(page) -> list[str]:
    return page.evaluate("() => [...document.querySelectorAll('h2')].map(h => h.innerText.trim())")


def click_label(page, label: str, timeout: int = 8000) -> None:
    open_sidebar(page)
    loc = page.locator(f"label:has-text('{label}')").last
    loc.wait_for(state="visible", timeout=timeout)
    loc.click(timeout=timeout)


def select_locale(page, lang: str, *, attempts: int = 3) -> bool:
    target = "简体中文" if lang == "zh_CN" else "English"
    want = 1 if lang == "zh_CN" else 0
    for _ in range(attempts):
        click_label(page, target)
        wait_stable(page, timeout=15)
        indices = radio_indices(page)
        if indices and indices[0] == want:
            return True
    return False


def select_role(page, role: str, lang: str, *, attempts: int = 3) -> bool:
    target = "研究视图" if role == "research" and lang == "zh_CN" else (
        "Research View" if role == "research" else "学生视图" if lang == "zh_CN" else "Student View"
    )
    want = 1 if role == "research" else 0
    for _ in range(attempts):
        click_label(page, target)
        wait_stable(page, timeout=15)
        indices = radio_indices(page)
        if indices and indices[1] == want:
            return True
    return False


def select_page(page, label: str, expected_h2: str, *, attempts: int = 3) -> bool:
    for _ in range(attempts):
        click_label(page, label)
        wait_stable(page, timeout=15)
        close_sidebar(page)
        if any(expected_h2 in h for h in current_h2(page)):
            return True
    return False


def activate_tab(page, index: int, *, attempts: int = 3) -> bool:
    tabs = page.locator("[role='tab']")
    for _ in range(attempts):
        if tabs.count() <= index:
            wait_stable(page, timeout=10)
            continue
        tabs.nth(index).click(timeout=8000, force=True)
        wait_stable(page, timeout=10)
        selected = page.evaluate(
            "() => [...document.querySelectorAll('[role=tab]')].map(t => t.getAttribute('aria-selected'))"
        )
        if len(selected) > index and selected[index] == "true":
            return True
    return False


def commit_text_input(page, selector: str, value: str) -> None:
    field = page.locator(selector).first
    field.fill(value)
    page.keyboard.press("Tab")
    wait_stable(page, timeout=15)


def is_allowed_console(text: str) -> bool:
    return any(item in text for item in ALLOWED_CONSOLE)


def db_counts() -> dict:
    con = sqlite3.connect(ISOLATED_DB)
    try:
        return {
            "essays": con.execute("SELECT COUNT(*) FROM essays").fetchone()[0],
            "exports": con.execute("SELECT COUNT(*) FROM export_jobs").fetchone()[0],
        }
    finally:
        con.close()


def dump_diagnostics(page, path: pathlib.Path, tag: str) -> None:
    """Write focused DOM diagnostics (no screenshots of unrelated pages)."""
    payload = {
        "tag": tag,
        "h2": current_h2(page),
        "radios": radio_option_labels(page),
        "radio_indices": radio_indices(page),
        "exception": (
            page.locator('[data-testid="stException"]').first.inner_text()[:300]
            if page.locator('[data-testid="stException"]').count()
            else None
        ),
        "tablist_count": page.locator("[role='tablist']").count(),
        "tab_count": page.locator("[role='tab']").count(),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
