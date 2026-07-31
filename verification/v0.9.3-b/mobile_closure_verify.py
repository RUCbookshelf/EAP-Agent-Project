"""v0.9.3-B mobile closure verification.

Exercises all eight Research Data subsections at 390x844 in English and
Simplified Chinese against a real FastAPI + Streamlit stack, capturing:
console messages, page exceptions, viewport/body widths, server-side request
IDs, per-endpoint request counts, duplicate-write checks, and screenshots.

Run (from the project root):
    .venv\\Scripts\\python.exe verification/v0.9.3-b/mobile_closure_verify.py

Exit code 0 = all subsections passed; 1 = at least one failure.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
API_PORT = 8001
STREAMLIT_PORT = 8502
BASE_URL = f"http://127.0.0.1:{STREAMLIT_PORT}"
API_BASE = f"http://127.0.0.1:{API_PORT}"
OUT_DIR = PROJECT_ROOT / "verification" / "v0.9.3-b" / "mobile-closure"
SHOT_DIR = OUT_DIR / "screenshots"
DEV_DB = PROJECT_ROOT / "data" / "writing_feedback.db"
VIEWPORT = {"width": 390, "height": 844}

REQUEST_LOG_RE = re.compile(
    r"request_id=(\S+) method=(\S+) path=(\S+) status=(\S+) elapsed_ms=([\d.]+) lifecycle=(\S+)"
)
TRACEBACK_MARKERS = [
    "Traceback (most recent call last)",
    "streamlit.error",
    "Internal Python error",
    "Uncaught app exception",
    "AttributeError:",
    "TypeError:",
    "NameError:",
    "KeyError:",
    "ValueError:",
]

SUBSECTIONS = [
    {
        "key": "export_preview",
        "tab": "export_preview",
        "content": ["export_preview", "export_privacy_mode", "export_formats"],
        "buttons": [
            {"label": "export_preview", "method": "POST", "path": "/api/v1/research/export/preview"},
            {"label": "export_run", "method": "POST", "path": "/api/v1/research/export/run"},
        ],
    },
    {
        "key": "privacy_mode",
        "tab": "research_data_privacy",
        "content": ["research_data_privacy", "privacy_internal", "privacy_pseudonymized", "privacy_minimal", "privacy_warning"],
        "buttons": [],
    },
    {
        "key": "dataset_filters",
        "tab": "research_data_filters",
        "content": ["research_data_filters", "research_data_filters_placeholder"],
        "buttons": [],
    },
    {
        "key": "pii_review",
        "tab": "pii_scan",
        "content": ["pii_scan", "research_evidence_submission_id"],
        "buttons": [
            {"label": "pii_scan", "method": "GET", "path": "/api/v1/submissions/1/pii-candidates"},
        ],
    },
    {
        "key": "human_review",
        "tab": "human_review",
        "content": ["human_review", "human_review_target", "human_review_decision", "human_review_comment", "human_review_create"],
        "buttons": [
            {"label": "human_review_create", "method": "POST", "path": "/api/v1/research/reviews"},
        ],
    },
    {
        "key": "dataset_split",
        "tab": "dataset_split",
        "content": ["dataset_split", "split_boundary"],
        "buttons": [
            {"label": "dataset_split", "method": "POST", "path": "/api/v1/research/dataset-split"},
        ],
    },
    {
        "key": "data_quality",
        "tab": "data_quality",
        "content": ["data_quality_report"],
        "buttons": [
            {"label": "data_quality_report", "method": "GET", "path": "/api/v1/research/data-quality"},
        ],
    },
    {
        "key": "export_history",
        "tab": "export_history",
        "content": ["export_history"],
        "buttons": [
            {"label": "export_history", "method": "GET", "path": "/api/v1/research/export/history"},
        ],
    },
]


def load_locales() -> dict[str, dict]:
    out = {}
    for lang in ("en", "zh_CN"):
        with open(PROJECT_ROOT / "locales" / f"{lang}.json", encoding="utf-8") as fh:
            out[lang] = json.load(fh)
    return out


def t(locales: dict, lang: str, key: str) -> str:
    return locales[lang].get(key, key)


def read_api_log(path: pathlib.Path) -> list[dict]:
    rows = []
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = REQUEST_LOG_RE.search(line)
                if m:
                    rows.append(
                        {
                            "request_id": m.group(1),
                            "method": m.group(2),
                            "path": m.group(3),
                            "status": m.group(4),
                            "elapsed_ms": float(m.group(5)),
                            "lifecycle": m.group(6),
                        }
                    )
    except FileNotFoundError:
        pass
    return rows


def snapshot_db(src: pathlib.Path, dst: pathlib.Path) -> None:
    con_src = sqlite3.connect(src)
    con_dst = sqlite3.connect(dst)
    try:
        con_src.backup(con_dst)
    finally:
        con_dst.close()
        con_src.close()


def start_stack(work_dir: pathlib.Path) -> tuple[subprocess.Popen, subprocess.Popen, pathlib.Path]:
    db_copy = work_dir / "closure.db"
    if DEV_DB.exists():
        snapshot_db(DEV_DB, db_copy)
    api_log = work_dir / "api_requests.log"
    log_config = work_dir / "logging_config.json"
    log_config.write_text(
        json.dumps(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {"plain": {"format": "%(message)s"}},
                "handlers": {
                    "stderr": {"class": "logging.StreamHandler", "formatter": "plain", "stream": "ext://sys.stderr"}
                },
                "root": {"handlers": ["stderr"], "level": "INFO"},
            }
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["API_PORT"] = str(API_PORT)
    env["STREAMLIT_PORT"] = str(STREAMLIT_PORT)
    env["API_BASE_URL"] = API_BASE
    env["DATABASE_PATH"] = str(db_copy)
    env["LLM_PROVIDER"] = "local"
    env.pop("DEEPSEEK_API_KEY", None)
    with open(api_log, "w", encoding="utf-8") as log_fh:
        api = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(API_PORT),
                "--log-config",
                str(log_config),
            ],
            env=env,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            cwd=str(PROJECT_ROOT),
        )
        ui = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "app/ui/streamlit_app.py",
                "--server.port",
                str(STREAMLIT_PORT),
                "--server.headless",
                "true",
                "--browser.gatherUsageStats",
                "false",
            ],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(PROJECT_ROOT),
        )
    return api, ui, api_log


def wait_http(url: str, timeout: float = 90.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def stop_process(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def page_metrics(page) -> dict:
    return page.evaluate(
        """() => {
            return {
                inner_width: window.innerWidth,
                inner_height: window.innerHeight,
                doc_scroll_width: document.documentElement.scrollWidth,
                body_scroll_width: document.body.scrollWidth,
            };
        }"""
    )


def tab_bar_scroll_info(page) -> dict | None:
    return page.evaluate(
        """() => {
            const tabs = document.querySelector('[data-testid="stTabs"]');
            if (!tabs) return null;
            let best = null;
            for (const el of tabs.querySelectorAll('*')) {
                if (el.scrollWidth > el.clientWidth + 1) {
                    const cs = getComputedStyle(el);
                    if (['auto', 'scroll', 'hidden'].includes(cs.overflowX)) {
                        const overflow = el.scrollWidth - el.clientWidth;
                        if (!best || overflow > best.overflow) {
                            best = {overflow, scrollWidth: el.scrollWidth, clientWidth: el.clientWidth};
                        }
                    }
                }
            }
            return best;
        }"""
    )


def body_text(page) -> str:
    return page.evaluate("() => document.body.innerText")


def raw_key_check(page, locales: dict) -> list[str]:
    text = body_text(page)
    keys = set(locales["en"]) | set(locales["zh_CN"])
    return sorted(k for k in keys if "_" in k and k in text)


def traceback_check(page) -> list[str]:
    text = body_text(page)
    return [m for m in TRACEBACK_MARKERS if m in text]


def open_sidebar_if_needed(page, label_text: str) -> str:
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
    for sel in toggles:
        btn = page.locator(sel).first
        if btn.count():
            try:
                btn.click(timeout=3000)
                page.wait_for_timeout(900)
                label.click(timeout=6000)
                return "sidebar_toggle+click"
            except Exception:
                continue
    label.click(force=True, timeout=6000)
    return "force_click"


def close_sidebar(page) -> None:
    collapse = page.locator('[data-testid="stSidebarCollapseButton"]').first
    if collapse.count():
        try:
            collapse.click(timeout=3000)
            page.wait_for_timeout(700)
            return
        except Exception:
            pass
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(700)
    except Exception:
        pass


def click_radio(page, text: str) -> str:
    return open_sidebar_if_needed(page, text)


def click_tab(page, label: str) -> None:
    tab = page.locator("[role='tab']", has_text=label).last
    tab.scroll_into_view_if_needed(timeout=8000)
    tab.click(timeout=10000)


def click_button(page, label: str) -> None:
    btn = page.get_by_role("button", name=label, exact=True).last
    btn.scroll_into_view_if_needed(timeout=8000)
    btn.click(timeout=10000)


def wait_tab_active(page, label: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        active = page.locator("[role='tab'][aria-selected='true']", has_text=label)
        if active.count() and active.first.is_visible():
            return
        page.wait_for_timeout(500)
    raise RuntimeError(f"tab never became active: {label}")


def wait_text(page, text: str, timeout: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if text in body_text(page):
            return True
        page.wait_for_timeout(500)
    return False


def api_get(path: str) -> requests.Response:
    return requests.get(f"{API_BASE}{path}", timeout=30)


def count_log_rows(rows: list[dict], method: str, path: str) -> list[dict]:
    return [r for r in rows if r["method"] == method and r["path"] == path]


def run_locale(
    lang: str,
    locales: dict,
    api_log_path: pathlib.Path,
    run_token: str,
) -> dict:
    evidence = {
        "locale": lang,
        "viewport": f"{VIEWPORT['width']}x{VIEWPORT['height']}",
        "run_token": run_token,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "console": [],
        "pageerrors": [],
        "requests": [],
        "subsections": [],
        "duplicate_writes": {},
        "summary": {},
    }
    created_export_id = None
    unique_hr_target = f"mbl-{lang}-{run_token}"

    history_before = api_get("/api/v1/research/export/history").json()
    reviews_before = api_get("/api/v1/research/reviews").json()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport=VIEWPORT)
        console_msgs: list[dict] = []
        page_errors: list[dict] = []

        def on_console(msg) -> None:
            console_msgs.append({"type": msg.type, "text": msg.text})

        def on_pageerror(exc) -> None:
            page_errors.append({"error": str(exc)})

        page.on("console", on_console)
        page.on("pageerror", on_pageerror)

        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector("[data-testid='stAppViewContainer']", timeout=30000)
        page.wait_for_timeout(4000)

        if lang == "zh_CN":
            click_radio(page, t(locales, lang, "lang_zh_CN"))
            page.wait_for_timeout(2500)
            if not wait_text(page, t(locales, lang, "view_research"), timeout=20):
                raise RuntimeError("Chinese locale did not activate")

        click_radio(page, t(locales, lang, "view_research"))
        page.wait_for_timeout(2500)
        nav_label = t(locales, lang, "nav_research_data")
        if not wait_text(page, nav_label, timeout=25):
            raise RuntimeError(f"Research Data navigation not found for {lang}")
        click_radio(page, nav_label)
        page.wait_for_timeout(3000)
        close_sidebar(page)
        page.wait_for_selector("[role='tab']", timeout=30000)

        tab_bar = tab_bar_scroll_info(page)
        evidence["tab_bar_scroll"] = tab_bar

        for spec in SUBSECTIONS:
            key = spec["key"]
            tab_label = t(locales, lang, spec["tab"])
            result = {
                "subsection": key,
                "locale": lang,
                "viewport": evidence["viewport"],
                "tab_label": tab_label,
                "rendered": False,
                "tab_reachable": False,
                "controls_reachable": False,
                "localized_labels": True,
                "localization_notes": [],
                "raw_keys_found": [],
                "traceback_found": [],
                "console_errors": [],
                "page_exceptions": [],
                "overflow_ok": True,
                "body_width": None,
                "viewport_width": VIEWPORT["width"],
                "actions": [],
                "screenshot": "",
                "result": "FAIL",
            }
            try:
                click_tab(page, tab_label)
                wait_tab_active(page, tab_label)
                page.wait_for_timeout(2200)
                result["tab_reachable"] = True

                content_ok = True
                for ckey in spec["content"]:
                    if not wait_text(page, t(locales, lang, ckey), timeout=15):
                        content_ok = False
                        result["localization_notes"].append(f"missing content: {ckey}")
                result["rendered"] = content_ok

                result["raw_keys_found"] = raw_key_check(page, locales)
                result["traceback_found"] = traceback_check(page)

                for bspec in spec["buttons"]:
                    label = t(locales, lang, bspec["label"])
                    btn = page.get_by_role("button", name=label, exact=True)
                    if btn.count() == 0 or not btn.last.is_visible():
                        result["localization_notes"].append(f"button missing: {bspec['label']}")
                        continue
                    log_pos = len(read_api_log(api_log_path))
                    if key == "human_review":
                        target_input = page.get_by_label("Target ID")
                        target_input.fill(unique_hr_target, timeout=8000)
                    click_button(page, label)
                    page.wait_for_timeout(2800)
                    new_rows = read_api_log(api_log_path)[log_pos:]
                    matched = count_log_rows(new_rows, bspec["method"], bspec["path"])
                    action = {
                        "label_key": bspec["label"],
                        "method": bspec["method"],
                        "path": bspec["path"],
                        "request_count": len(matched),
                        "statuses": [r["status"] for r in matched],
                        "request_ids": [r["request_id"] for r in matched],
                    }
                    if len(matched) != 1:
                        action["ok"] = False
                        result["localization_notes"].append(
                            f"expected exactly 1 request to {bspec['path']}, saw {len(matched)}"
                        )
                    else:
                        action["ok"] = True
                    result["actions"].append(action)

                    if key == "export_preview" and bspec["label"] == "export_run":
                        after = api_get("/api/v1/research/export/history").json()
                        after_ids = [str(j.get("export_id")) for j in after]
                        if after_ids:
                            created_export_id = after_ids[0]
                        result["actions"][-1]["created_export_id"] = created_export_id
                        result["actions"][-1]["export_jobs_total"] = len(after)
                        result["actions"][-1]["export_id_counts"] = {
                            eid: after_ids.count(eid) for eid in sorted(set(after_ids))
                        }

                    if key == "human_review" and bspec["label"] == "human_review_create":
                        reviews_after = api_get("/api/v1/research/reviews").json()
                        matches = [r for r in reviews_after if r.get("target_id") == unique_hr_target]
                        result["actions"][-1]["created_hr_ids"] = [r.get("review_id") for r in matches]
                        result["actions"][-1]["matching_records"] = len(matches)

                if spec["buttons"]:
                    result["controls_reachable"] = all(a.get("ok") is not None for a in result["actions"])
                else:
                    result["controls_reachable"] = result["rendered"]

                if lang == "zh_CN" and key == "human_review":
                    if "Target ID" in body_text(page):
                        result["localized_labels"] = False
                        result["localization_notes"].append(
                            "hardcoded English label 'Target ID' (app/ui/pages/research_pages.py:351)"
                        )
                if lang == "zh_CN" and key == "export_preview":
                    text = body_text(page)
                    if re.search(r"Export:\s*EXP", text):
                        result["localized_labels"] = False
                        result["localization_notes"].append(
                            "hardcoded English success prefix 'Export:' (app/ui/pages/research_pages.py:314)"
                        )

                metrics = page_metrics(page)
                result["body_width"] = metrics["body_scroll_width"]
                result["doc_width"] = metrics["doc_scroll_width"]
                result["viewport_width"] = metrics["inner_width"]
                overflow_ok = (
                    metrics["body_scroll_width"] <= metrics["inner_width"] + 10
                    and metrics["doc_scroll_width"] <= metrics["inner_width"] + 10
                )
                result["overflow_ok"] = bool(overflow_ok)

                err_msgs = [m for m in console_msgs if m["type"] == "error"]
                result["console_errors"] = err_msgs
                result["page_exceptions"] = list(page_errors)

                shot = SHOT_DIR / f"{lang}_{key}.png"
                page.screenshot(path=str(shot), full_page=False)
                result["screenshot"] = str(shot.relative_to(PROJECT_ROOT))

                passed = (
                    result["tab_reachable"]
                    and result["rendered"]
                    and result["controls_reachable"]
                    and not result["raw_keys_found"]
                    and not result["traceback_found"]
                    and not err_msgs
                    and not page_errors
                    and result["overflow_ok"]
                    and all(a.get("ok") for a in result["actions"])
                )
                result["result"] = "PASS" if passed else "FAIL"
            except Exception as exc:  # noqa: BLE001 - record and continue
                result["localization_notes"].append(f"exception: {type(exc).__name__}: {exc}")
                result["result"] = "FAIL"

            evidence["subsections"].append(result)

        if lang == "zh_CN" and key == "export_history":
            pass
        evidence["console"] = console_msgs
        evidence["pageerrors"] = page_errors
        browser.close()

    history_after = api_get("/api/v1/research/export/history").json()
    reviews_after = api_get("/api/v1/research/reviews").json()
    evidence["duplicate_writes"] = {
        "export_jobs_before": len(history_before),
        "export_jobs_after": len(history_after),
        "export_jobs_delta": len(history_after) - len(history_before),
        "created_export_id": created_export_id,
        "export_id_present_once": (
            created_export_id is not None
            and sum(1 for j in history_after if str(j.get("export_id")) == created_export_id) == 1
        ),
        "human_reviews_before": len(reviews_before),
        "human_reviews_after": len(reviews_after),
        "human_reviews_delta": len(reviews_after) - len(reviews_before),
        "unique_hr_target": unique_hr_target,
        "hr_matching_records": len([r for r in reviews_after if r.get("target_id") == unique_hr_target]),
    }
    evidence["requests"] = read_api_log(api_log_path)
    subs = evidence["subsections"]
    evidence["summary"] = {
        "total": len(subs),
        "passed": sum(1 for s in subs if s["result"] == "PASS"),
        "failed": sum(1 for s in subs if s["result"] != "PASS"),
        "console_errors_total": len(evidence["console"]),
        "page_exceptions_total": len(evidence["pageerrors"]),
        "all_overflow_ok": all(s["overflow_ok"] for s in subs),
        "all_raw_keys_clean": all(not s["raw_keys_found"] for s in subs),
        "all_traceback_clean": all(not s["traceback_found"] for s in subs),
        "duplicate_writes": evidence["duplicate_writes"],
    }
    return evidence


def main() -> int:
    locales = load_locales()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    work_dir = pathlib.Path(tempfile.mkdtemp(prefix="v093b_mobile_closure_"))
    print(f"Work dir: {work_dir}")
    api_proc, ui_proc, api_log = start_stack(work_dir)
    exit_code = 1
    try:
        if not wait_http(f"{API_BASE}/api/v1/system/health", timeout=90):
            print("FAIL: FastAPI did not become healthy")
            return 1
        if not wait_http(BASE_URL, timeout=90):
            print("FAIL: Streamlit did not start")
            return 1
        print("Stack ready; running locale passes...")
        run_token = uuid.uuid4().hex[:8]
        all_evidence = {}
        for lang in ("en", "zh_CN"):
            print(f"--- {lang} ---")
            ev = run_locale(lang, locales, api_log, run_token)
            all_evidence[lang] = ev
            out_file = OUT_DIR / f"evidence_{lang}.json"
            with open(out_file, "w", encoding="utf-8") as fh:
                json.dump(ev, fh, ensure_ascii=False, indent=2)
            print(json.dumps(ev["summary"], ensure_ascii=False, indent=2))

        shutil.copy2(api_log, OUT_DIR / "api_request_log.txt")
        summary = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "viewport": f"{VIEWPORT['width']}x{VIEWPORT['height']}",
            "locales": {
                lang: {
                    "passed": all_evidence[lang]["summary"]["passed"],
                    "failed": all_evidence[lang]["summary"]["failed"],
                    "total": all_evidence[lang]["summary"]["total"],
                }
                for lang in all_evidence
            },
            "overall": "PASS",
        }
        if any(all_evidence[lang]["summary"]["failed"] for lang in all_evidence):
            summary["overall"] = "FAIL"
            exit_code = 1
        else:
            exit_code = 0
        with open(OUT_DIR / "summary.json", "w", encoding="utf-8") as fh:
            json.dump(summary, fh, ensure_ascii=False, indent=2)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return exit_code
    finally:
        stop_process(ui_proc)
        stop_process(api_proc)


if __name__ == "__main__":
    raise SystemExit(main())
