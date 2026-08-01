"""v0.9.3-C computer-control journey verification.

Starts a real FastAPI + Streamlit stack against an isolated copy of the current
database (explicit DATABASE_URL so .env cannot redirect it), then executes the
complete deterministic Student journey, the S02 regression, the Researcher
journey, and four locale/viewport combinations with real browser interaction.

Run (from the project root):
    .venv\\Scripts\\python.exe verification/v0.9.3-c/journey_verify.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid

import requests
from playwright.sync_api import sync_playwright

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC_PATH = PROJECT_ROOT / "verification" / "v0.9.3-b" / "mobile_closure_verify.py"
spec = importlib.util.spec_from_file_location("mc", SPEC_PATH)
mc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mc)

API_PORT = 8001
STREAMLIT_PORT = 8502
BASE_URL = f"http://127.0.0.1:{STREAMLIT_PORT}"
API_BASE = f"http://127.0.0.1:{API_PORT}"
OUT_DIR = PROJECT_ROOT / "verification" / "v0.9.3-c"
SHOT_DIR = OUT_DIR / "screenshots"
DEV_DB = PROJECT_ROOT / "data" / "writing_feedback.db"

DEMO_LEARNER = "DEMO-001"
EMPTY_LEARNER = "EMPTY01"


def prepare_database() -> pathlib.Path:
    work_dir = pathlib.Path(tempfile.mkdtemp(prefix="v093c_journey_"))
    db_copy = work_dir / "journey.db"
    src = sqlite3.connect(DEV_DB)
    dst = sqlite3.connect(db_copy)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    # Add a learner with no journey records for the empty-state check.
    con = sqlite3.connect(db_copy)
    con.execute(
        "INSERT OR IGNORE INTO students (student_id, created_at, is_synthetic) VALUES (?, ?, 1)",
        (EMPTY_LEARNER, time.strftime("%Y-%m-%dT%H:%M:%S+00:00")),
    )
    con.commit()
    con.close()
    return db_copy


def start_stack(work_dir: pathlib.Path, db_copy: pathlib.Path):
    api_log = work_dir / "api_requests.log"
    log_config = work_dir / "logging_config.json"
    log_config.write_text(
        json.dumps({
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"plain": {"format": "%(message)s"}},
            "handlers": {"stderr": {"class": "logging.StreamHandler", "formatter": "plain", "stream": "ext://sys.stderr"}},
            "root": {"handlers": ["stderr"], "level": "INFO"},
        }),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["API_PORT"] = str(API_PORT)
    env["STREAMLIT_PORT"] = str(STREAMLIT_PORT)
    env["API_BASE_URL"] = API_BASE
    env["DATABASE_URL"] = f"sqlite:///{db_copy}"
    env["LLM_PROVIDER"] = "local"
    env.pop("DEEPSEEK_API_KEY", None)
    with open(api_log, "w", encoding="utf-8") as log_fh:
        api = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.api.main:app", "--host", "127.0.0.1",
             "--port", str(API_PORT), "--log-config", str(log_config)],
            env=env, stdout=log_fh, stderr=subprocess.STDOUT, cwd=str(PROJECT_ROOT),
        )
        ui = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "app/ui/streamlit_app.py",
             "--server.port", str(STREAMLIT_PORT), "--server.headless", "true",
             "--browser.gatherUsageStats", "false"],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(PROJECT_ROOT),
        )
    return api, ui, api_log, work_dir


def wait_ready() -> bool:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            if requests.get(f"{API_BASE}/api/v1/system/health", timeout=3).status_code == 200:
                return requests.get(BASE_URL, timeout=3).status_code == 200
        except Exception:
            pass
        time.sleep(0.5)
    return False


def read_api_log(path: pathlib.Path) -> list[dict]:
    return mc.read_api_log(path)


def click_nav(page, text: str) -> None:
    mc.open_sidebar_if_needed(page, text)
    page.wait_for_timeout(1500)


def body_text(page) -> str:
    return page.evaluate("() => document.body.innerText")


def page_metrics(page) -> dict:
    return page.evaluate(
        """() => ({inner: window.innerWidth, doc: document.documentElement.scrollWidth,
                  body: document.body.scrollWidth})"""
    )


def raw_keys(page, locales) -> list[str]:
    text = body_text(page)
    keys = set(locales["en"]) | set(locales["zh_CN"])
    return sorted(k for k in keys if "_" in k and k in text)


def count_rows(rows, method, path):
    return [r for r in rows if r["method"] == method and r["path"] == path]


def run_student_journey(page, locales, lang, api_log, evidence, run_token):
    """Complete deterministic Student journey (English desktop)."""
    interact = []

    # Home for DEMO-001
    click_nav(page, locales[lang]["student_home_title"])
    sid = page.get_by_label(locales[lang]["student_id"])
    sid.fill(DEMO_LEARNER)
    sid.press("Enter")
    page.wait_for_timeout(2500)
    interact.append({"step": "home_demo", "text": body_text(page)[:400]})

    # Writing: submit a new synthetic essay
    click_nav(page, locales[lang]["student_writing_title"])
    page.wait_for_timeout(1500)
    sid = page.get_by_label(locales[lang]["student_id"])
    sid.fill(DEMO_LEARNER)
    essay = (
        "Communities should invest in public transport. Commuters need reliable buses and trains. "
        "Reliable transport reduces traffic and pollution. Public transport also helps people without cars. "
        "Therefore, cities should expand transit networks and fund maintenance."
    )
    page.get_by_label(locales[lang]["writing_prompt"]).fill("Why is public transport important?")
    page.locator("textarea").last.fill(essay)
    btn = page.get_by_role("button", name=locales[lang]["submit_button"], exact=True)
    btn.scroll_into_view_if_needed()
    t0 = time.monotonic()
    btn.click()
    deadline = time.monotonic() + 90
    ok = False
    while time.monotonic() < deadline:
        page.wait_for_timeout(1000)
        if "Submission saved as essay" in body_text(page):
            ok = True
            break
    visible_ms = round((time.monotonic() - t0) * 1000)
    shot = SHOT_DIR / "en_desktop_writing_after_submit.png"
    page.screenshot(path=str(shot), full_page=False)
    interact.append({"step": "writing_submit", "success": ok, "visible_ms": visible_ms,
                     "screenshot": str(shot.relative_to(PROJECT_ROOT))})

    # Feedback
    click_nav(page, locales[lang]["student_feedback_title"])
    page.wait_for_timeout(2000)
    shot = SHOT_DIR / "en_desktop_feedback.png"
    page.screenshot(path=str(shot), full_page=False)
    fb_text = body_text(page)
    interact.append({"step": "feedback", "strengths_section": "Strengths" in fb_text,
                     "priorities_section": "Priorities" in fb_text,
                     "screenshot": str(shot.relative_to(PROJECT_ROOT))})

    # Practice: reuse existing exercise (idempotent), submit attempt
    click_nav(page, locales[lang]["practice"])
    page.wait_for_timeout(1500)
    sid = page.get_by_label(locales[lang]["student_id"])
    sid.fill(DEMO_LEARNER)
    sid.press("Enter")
    page.wait_for_timeout(1500)
    instances_before = len(requests.get(f"{API_BASE}/api/v1/practice-targets/PT000001/exercises", timeout=30).json())
    page.get_by_role("button", name=locales[lang]["load_practice"], exact=True).click(timeout=15000)
    page.wait_for_timeout(4000)
    instances_after = len(requests.get(f"{API_BASE}/api/v1/practice-targets/PT000001/exercises", timeout=30).json())
    shot = SHOT_DIR / "en_desktop_practice.png"
    page.screenshot(path=str(shot), full_page=False)
    interact.append({"step": "practice_existing_exercise", "instances_before": instances_before,
                     "instances_after": instances_after, "no_duplicate": instances_before == instances_after,
                     "screenshot": str(shot.relative_to(PROJECT_ROOT))})
    # Attempt the existing exercise if its text area is present
    ta = page.locator("textarea").last
    if ta.count():
        ta.fill("Public transport matters because it reduces traffic, lowers pollution, and helps people without cars.")
        btn = page.get_by_role("button", name=locales[lang]["submit_attempt"], exact=True)
        if btn.count():
            btn.scroll_into_view_if_needed()
            btn.click()
            page.wait_for_timeout(5000)
            shot = SHOT_DIR / "en_desktop_practice_attempted.png"
            page.screenshot(path=str(shot), full_page=False)
            interact.append({"step": "practice_attempt", "evaluation_shown": "Practice evaluation" in body_text(page),
                             "screenshot": str(shot.relative_to(PROJECT_ROOT))})

    # Revision: submit a revised draft of the new essay
    click_nav(page, locales[lang]["student_writing_title"])
    page.wait_for_timeout(1500)
    sid = page.get_by_label(locales[lang]["student_id"])
    sid.fill(DEMO_LEARNER)
    sid.press("Enter")
    page.wait_for_timeout(1500)
    page.get_by_label(locales[lang]["writing_prompt"]).fill("Why is public transport important?")
    page.locator("textarea").last.fill(
        "Public transport is important because it reduces traffic, lowers pollution, and serves people without cars. "
        "Cities should therefore expand transit networks and fund maintenance."
    )
    # Select "revision within an existing task"
    mc.open_sidebar_if_needed(page, locales[lang]["task_revision_within"])
    page.wait_for_timeout(2500)
    btn = page.get_by_role("button", name=locales[lang]["submit_button"], exact=True)
    btn.scroll_into_view_if_needed()
    btn.click()
    deadline = time.monotonic() + 90
    ok = False
    while time.monotonic() < deadline:
        page.wait_for_timeout(1000)
        if "Submission saved as essay" in body_text(page) or "could not be completed" in body_text(page):
            ok = True
            break
    interact.append({"step": "revision_submit", "settled": ok, "body_has_error": "could not be completed" in body_text(page)})

    # Learning Journey
    click_nav(page, locales[lang]["learning_journey"])
    page.wait_for_timeout(1500)
    sid = page.get_by_label(locales[lang]["student_id"])
    sid.fill(DEMO_LEARNER)
    sid.press("Enter")
    page.wait_for_timeout(1500)
    t0 = time.monotonic()
    page.get_by_role("button", name=locales[lang]["load_journey"], exact=True).click(timeout=15000)
    page.wait_for_timeout(4000)
    journey_ms = round((time.monotonic() - t0) * 1000)
    text = body_text(page)
    shot = SHOT_DIR / "en_desktop_journey_events.png"
    page.screenshot(path=str(shot), full_page=False)
    interact.append({"step": "journey_events", "visible_ms": journey_ms,
                     "has_timeline": "Journey timeline" in text or "Learning Journey" in text,
                     "has_writing_submitted": "Essay submitted" in text,
                     "has_practice_available": "Practice available" in text,
                     "screenshot": str(shot.relative_to(PROJECT_ROOT))})

    # Refresh and revisit
    page.reload(wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    click_nav(page, locales[lang]["learning_journey"])
    page.wait_for_timeout(1500)
    sid = page.get_by_label(locales[lang]["student_id"])
    sid.fill(DEMO_LEARNER)
    sid.press("Enter")
    page.wait_for_timeout(1500)
    page.get_by_role("button", name=locales[lang]["load_journey"], exact=True).click(timeout=15000)
    page.wait_for_timeout(4000)
    interact.append({"step": "journey_after_refresh", "rendered": "Journey timeline" in body_text(page) or "Essay submitted" in body_text(page)})

    # Locale switch and back (no side effects)
    counts_before = _record_counts(api_log)
    click_nav(page, locales["zh_CN"]["lang_zh_CN"])
    page.wait_for_timeout(2500)
    click_nav(page, locales["zh_CN"]["learning_journey"])
    page.wait_for_timeout(1500)
    sid = page.get_by_label(locales["zh_CN"]["student_id"])
    sid.fill(DEMO_LEARNER)
    sid.press("Enter")
    page.wait_for_timeout(1500)
    page.get_by_role("button", name=locales["zh_CN"]["load_journey"], exact=True).click(timeout=15000)
    page.wait_for_timeout(4000)
    shot = SHOT_DIR / "zh_desktop_journey_events.png"
    page.screenshot(path=str(shot), full_page=False)
    zh_text = body_text(page)
    interact.append({"step": "journey_zh", "has_chinese": "学习旅程" in zh_text or "作文已提交" in zh_text,
                     "raw_keys": raw_keys(page, locales), "screenshot": str(shot.relative_to(PROJECT_ROOT))})
    counts_after = _record_counts(api_log)
    interact.append({"step": "locale_switch_side_effects", "writes_before": counts_before, "writes_after": counts_after,
                     "no_write_side_effect": counts_before == counts_after})
    click_nav(page, locales["en"]["lang_en"])
    page.wait_for_timeout(2000)
    return interact


def _record_counts(api_log):
    rows = read_api_log(api_log)
    writes = [
        (r["method"], r["path"]) for r in rows
        if r["method"] in ("POST", "PUT", "PATCH", "DELETE")
        and "/system/" not in r["path"]
    ]
    return sorted(set(writes))


def run_s02_regression(page, locales, lang, api_log, evidence):
    click_nav(page, locales[lang]["learning_journey"])
    page.wait_for_timeout(1500)
    sid = page.get_by_label(locales[lang]["student_id"])
    sid.fill("S02")
    sid.press("Enter")
    page.wait_for_timeout(1500)
    log_pos = len(read_api_log(api_log))
    t0 = time.monotonic()
    page.get_by_role("button", name=locales[lang]["load_journey"], exact=True).click(timeout=15000)
    page.wait_for_timeout(5000)
    visible_ms = round((time.monotonic() - t0) * 1000)
    rows = read_api_log(api_log)[log_pos:]
    journey_reqs = count_rows(rows, "GET", "/api/v1/students/S02/journey")
    text = body_text(page)
    shot = SHOT_DIR / "s02_journey_regression.png"
    page.screenshot(path=str(shot), full_page=False)
    evidence["s02_regression"] = {
        "visible_ms": visible_ms,
        "journey_requests": len(journey_reqs),
        "statuses": [r["status"] for r in journey_reqs],
        "request_ids": [r["request_id"] for r in journey_reqs],
        "api_duration_ms": [r["elapsed_ms"] for r in journey_reqs],
        "generic_api_unavailable_shown": "API is unavailable" in text or "unavailable" in text.lower() and "generic" in text,
        "rendered_events": "Essay submitted" in text,
        "rendered_gate_note": "Diagnostic Gate" in text or "no eligible priority" in text.lower(),
        "screenshot": str(shot.relative_to(PROJECT_ROOT)),
    }
    # S01 / S999 (learner not found)
    for sid in ("S01", "S999"):
        click_nav(page, locales[lang]["learning_journey"])
        page.wait_for_timeout(1200)
        sid_input = page.get_by_label(locales[lang]["student_id"])
        sid_input.fill(sid)
        sid_input.press("Enter")
        page.wait_for_timeout(1200)
        page.get_by_role("button", name=locales[lang]["load_journey"], exact=True).click(timeout=15000)
        page.wait_for_timeout(4000)
        text = body_text(page)
        evidence[f"learner_{sid}"] = {
            "rendered_not_found": "not found" in text.lower() or "未找到" in text,
            "text_snippet": text[:200],
        }
    # Empty learner
    click_nav(page, locales[lang]["learning_journey"])
    page.wait_for_timeout(1200)
    sid_input = page.get_by_label(locales[lang]["student_id"])
    sid_input.fill(EMPTY_LEARNER)
    sid_input.press("Enter")
    page.wait_for_timeout(1200)
    page.get_by_role("button", name=locales[lang]["load_journey"], exact=True).click(timeout=15000)
    page.wait_for_timeout(4000)
    shot = SHOT_DIR / "journey_empty_state.png"
    page.screenshot(path=str(shot), full_page=False)
    evidence["empty_learner"] = {
        "rendered_empty_state": "No submissions yet" in body_text(page) or "尚无提交" in body_text(page),
        "screenshot": str(shot.relative_to(PROJECT_ROOT)),
    }


def run_researcher_journey(page, locales, lang, api_log, evidence):
    interact = []
    click_nav(page, locales[lang]["view_research"])
    page.wait_for_timeout(2000)
    click_nav(page, locales[lang]["research_overview_title"])
    page.wait_for_timeout(2000)
    shot = SHOT_DIR / "en_desktop_research_overview.png"
    page.screenshot(path=str(shot), full_page=False)
    interact.append({"step": "research_overview", "screenshot": str(shot.relative_to(PROJECT_ROOT))})

    click_nav(page, locales[lang]["research_evidence_title"])
    page.wait_for_timeout(1500)
    page.get_by_role("button", name=locales[lang]["load_records"], exact=True).click(timeout=15000)
    page.wait_for_timeout(5000)
    shot = SHOT_DIR / "en_desktop_research_evidence.png"
    page.screenshot(path=str(shot), full_page=False)
    interact.append({"step": "research_evidence", "screenshot": str(shot.relative_to(PROJECT_ROOT))})

    click_nav(page, locales[lang]["tab_calf"])
    page.wait_for_timeout(2000)
    shot = SHOT_DIR / "en_desktop_research_calf.png"
    page.screenshot(path=str(shot), full_page=False)
    interact.append({"step": "research_calf", "screenshot": str(shot.relative_to(PROJECT_ROOT))})

    click_nav(page, locales[lang]["research_learning_title"])
    page.wait_for_timeout(1500)
    sid = page.get_by_label(locales[lang]["student_id"])
    sid.fill(DEMO_LEARNER)
    sid.press("Enter")
    page.wait_for_timeout(1500)
    page.get_by_role("button", name=locales[lang]["load_records"], exact=True).click(timeout=15000)
    page.wait_for_timeout(6000)
    text = body_text(page)
    shot = SHOT_DIR / "en_desktop_research_learning_process.png"
    page.screenshot(path=str(shot), full_page=False)
    interact.append({"step": "research_learning_process",
                     "journey_trace_shown": "Journey timeline" in text,
                     "source_ids_shown": "source:" in text,
                     "screenshot": str(shot.relative_to(PROJECT_ROOT))})

    click_nav(page, locales[lang]["nav_research_data"])
    page.wait_for_timeout(2000)
    for tab_key in ("export_preview", "research_data_privacy", "research_data_filters", "pii_scan",
                    "human_review", "dataset_split", "data_quality", "export_history"):
        label = locales[lang][tab_key]
        mc.click_tab(page, label)
        mc.wait_tab_active(page, label)
        page.wait_for_timeout(1000)
    interact.append({"step": "research_data_8_tabs", "result": "PASS"})

    click_nav(page, locales[lang]["research_audit_title"])
    page.wait_for_timeout(2500)
    shot = SHOT_DIR / "en_desktop_research_system_audit.png"
    page.screenshot(path=str(shot), full_page=False)
    interact.append({"step": "research_system_audit", "screenshot": str(shot.relative_to(PROJECT_ROOT))})
    return interact


def run_combo_pages(page, locales, lang, width, height, api_log):
    """Snapshot the critical pages for one locale/viewport combination."""
    results = []
    console_msgs = []
    page_errors = []
    page.on("console", lambda m: console_msgs.append({"type": m.type, "text": m.text}))
    page.on("pageerror", lambda e: page_errors.append(str(e)))
    prefix = f"{lang}_{width}x{height}"

    def snap(label, pg):
        before = len(console_msgs)
        before_err = len(page_errors)
        m = page_metrics(page)
        shot = SHOT_DIR / f"{prefix}_{pg}.png"
        page.screenshot(path=str(shot), full_page=False)
        results.append({
            "page": pg, "rendered": True,
            "console_errors": [c for c in console_msgs[before:] if c["type"] == "error"],
            "page_exceptions": page_errors[before_err:],
            "overflow_ok": m["body"] <= m["inner"] + 10 and m["doc"] <= m["inner"] + 10,
            "raw_keys": raw_keys(page, locales),
            "screenshot": str(shot.relative_to(PROJECT_ROOT)),
        })

    click_nav(page, locales[lang]["view_student"])
    page.wait_for_timeout(1800)
    for key, label_key in (("home", "student_home_title"), ("writing", "student_writing_title"),
                           ("feedback", "student_feedback_title"), ("practice", "practice"),
                           ("revision", "student_revision_title"), ("journey", "learning_journey")):
        click_nav(page, locales[lang][label_key])
        page.wait_for_timeout(1800)
        snap(label_key, key)

    click_nav(page, locales[lang]["view_research"])
    page.wait_for_timeout(1800)
    for key, label_key in (("overview", "research_overview_title"), ("evidence", "research_evidence_title"),
                           ("learning", "research_learning_title"), ("audit", "research_audit_title")):
        click_nav(page, locales[lang][label_key])
        page.wait_for_timeout(1800)
        snap(label_key, key)
    return results


def main() -> int:
    locales = mc.load_locales()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    db_copy = prepare_database()
    api, ui, api_log, work_dir = start_stack(pathlib.Path(db_copy).parent, db_copy)
    evidence = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "database": str(db_copy), "run_token": uuid.uuid4().hex[:8]}
    try:
        if not wait_ready():
            print("FAIL: stack not ready")
            return 1
        print("Stack ready.")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            # ---- English desktop complete journeys ----
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector("[data-testid='stAppViewContainer']", timeout=30000)
            page.wait_for_timeout(5000)
            evidence["student_journey"] = run_student_journey(
                page, locales, "en", api_log, evidence, evidence["run_token"])
            run_s02_regression(page, locales, "en", api_log, evidence)
            evidence["researcher_journey"] = run_researcher_journey(page, locales, "en", api_log, evidence)
            page.close()

            # ---- Four locale/viewport combinations ----
            evidence["combos"] = {}
            for lang, w, h in (("en", 1280, 900), ("zh_CN", 1280, 900), ("en", 390, 844), ("zh_CN", 390, 844)):
                page = browser.new_page(viewport={"width": w, "height": h})
                page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_selector("[data-testid='stAppViewContainer']", timeout=30000)
                page.wait_for_timeout(4000)
                if lang == "zh_CN":
                    click_nav(page, locales[lang]["lang_zh_CN"])
                    page.wait_for_timeout(2000)
                evidence["combos"][f"{lang}_{w}x{h}"] = run_combo_pages(
                    page, locales, lang, w, h, api_log)
                page.close()
            browser.close()

        evidence["request_log"] = read_api_log(api_log)
        evidence["response_times"] = {
            "slowest_api_ms": max((r["elapsed_ms"] for r in evidence["request_log"]), default=0),
            "by_path": {}
        }
        for r in evidence["request_log"]:
            key = f"{r['method']} {r['path']}"
            evidence["response_times"]["by_path"].setdefault(key, []).append(r["elapsed_ms"])
        evidence["created_records"] = _db_counts(db_copy)
        shutil.copy2(api_log, OUT_DIR / "api_request_log.txt")
        with open(OUT_DIR / "journey_evidence.json", "w", encoding="utf-8") as fh:
            json.dump(evidence, fh, ensure_ascii=False, indent=2)
        print("Journey verification complete. Evidence:", OUT_DIR / "journey_evidence.json")
        return 0
    finally:
        mc.stop_process(ui)
        mc.stop_process(api)


def _db_counts(db_path) -> dict:
    con = sqlite3.connect(db_path)
    out = {}
    for table in ("students", "essays", "analysis_runs", "feedback_records", "practice_targets",
                  "exercise_instances", "exercise_attempts", "practice_evaluations",
                  "within_task_response_candidates", "transfer_evidence_candidates",
                  "feedback_engagement_traces", "revision_groups"):
        out[table] = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    con.close()
    return out


if __name__ == "__main__":
    raise SystemExit(main())
