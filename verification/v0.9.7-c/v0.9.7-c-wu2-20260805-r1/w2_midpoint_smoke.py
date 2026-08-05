"""v0.9.7-C WU2 midpoint rendered smoke (lightweight checkpoint).

Real production stack (LLM_PROVIDER=local, isolated DB): seed one complete
priority-derived cycle through the API, then open the Student Journey page
in English desktop and Chinese mobile. Verifies the additive cycle response
renders without console/page errors, remote requests, overflow, or raw
keys, that Journey reads perform zero writes (whole-database counts), and
that the cycle view carries the WU2 safe actions.
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import sys

import requests
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
BASE_HARNESS_DIR = PROJECT_ROOT / "verification/v0.9.4-a/v0.9.4-a-20260801-r1"
sys.path.insert(0, str(BASE_HARNESS_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.locale import t  # noqa: E402

import v094a_harness as harness  # noqa: E402

harness.RUN_DIR = HERE
harness.ISOLATED_DB = HERE / "isolated" / "writing_feedback_v097c_wu2.db"
harness.LOG_DIR = HERE / "logs"

REPETITION_ESSAY = (
    "People should protect the environment. People should recycle more. "
    "People should save water. People should plant trees. People should reduce waste. "
    "People should use public transport. People should teach children about nature. "
    "People should value clean air."
)
REVISION_ESSAY = (
    "Citizens should protect the environment. Communities can recycle more."
)
VALID_RESPONSE = "A valid response reducing repetition."


def seed_cycle(student_id: str) -> None:
    def post(path, payload):
        response = requests.post(f"{harness.BASE}{path}", json=payload,
                                 timeout=60)
        assert response.status_code in (200, 201), response.text
        return response.json()

    essay_id = post("/api/v1/submissions", {
        "student_id": student_id,
        "writing_prompt": "What actions matter for sustainability?",
        "genre": "argumentative essay", "draft_stage": "first draft",
        "timed": False, "tool_use": "none", "essay_text": REPETITION_ESSAY,
    })["submission_id"]
    record = requests.get(
        f"{harness.BASE}/api/v1/submissions/{essay_id}", timeout=60).json()
    priorities = (record.get("feedback") or {}).get("priority_feedback", [])
    index = next(
        i for i, item in enumerate(priorities)
        if item.get("category") == "lexical_repetition")
    target = post("/api/v1/practice-targets", {
        "student_id": student_id, "source_submission_id": essay_id,
        "priority_index": index,
    })
    exercise = post(
        f"/api/v1/practice-targets/{target['practice_target_id']}/exercises",
        {"source_text": REPETITION_ESSAY})
    post(f"/api/v1/exercises/{exercise['exercise_id']}/attempts", {
        "student_id": student_id, "response_text": VALID_RESPONSE,
    })
    post("/api/v1/submissions", {
        "student_id": student_id,
        "writing_prompt": "What actions matter for sustainability?",
        "genre": "argumentative essay", "draft_stage": "revised draft",
        "timed": False, "tool_use": "none", "essay_text": REVISION_ESSAY,
        "revision_of_submission_id": essay_id,
    })


def whole_db_counts() -> dict[str, int]:
    with sqlite3.connect(harness.ISOLATED_DB) as con:
        tables = [
            row[0] for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        ]
        return {table: int(con.execute(
            f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]) for table in tables}


def observe(page):
    console_errors, page_errors, remote_requests = [], [], []
    page.on("console", lambda m: console_errors.append(m.text)
            if m.type == "error" else None)
    page.on("pageerror", lambda e: page_errors.append(str(e)))
    page.on("request", lambda r: remote_requests.append(r.url)
            if not r.url.startswith(("http://127.0.0.1", "http://localhost"))
            else None)
    return console_errors, page_errors, remote_requests


def run(browser, student_id: str, lang: str, viewport: dict, tag: str) -> dict:
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    console_errors, page_errors, remote_requests = observe(page)
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    harness.open_sidebar(page)
    harness.click_label(page, t("learning_journey", lang))
    assert harness.wait_stable(page, timeout=20)
    harness.close_sidebar(page)
    harness.commit_text_input(
        page, ".st-key-journey_student_v2 input", student_id)
    assert harness.wait_stable(page, timeout=20)
    text = page.locator('[data-testid="stMainBlockContainer"]').inner_text()
    assert t("journey_timeline", lang) in text
    assert t("journey_event_practice_available", lang) in text
    assert t("journey_event_revision_submitted", lang) in text
    exceptions = page.locator('[data-testid="stException"]').count()
    width = page.evaluate("() => window.innerWidth")
    overflow = page.evaluate(
        "() => document.documentElement.scrollWidth") > width
    raw_keys = [key for key in ("journey_timeline",)
                if key in text]
    assert exceptions == 0 and not overflow and not raw_keys
    shot = HERE / "screenshots" / f"{tag}_journey.png"
    shot.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(shot), full_page=True)
    unexpected = [item for item in console_errors
                  if not harness.is_allowed_console(item)]
    result = {
        "combination": f"{lang} {viewport['width']}x{viewport['height']}",
        "exceptions": exceptions, "overflow": overflow,
        "raw_keys": raw_keys, "console_errors": unexpected,
        "page_errors": page_errors, "remote_requests": remote_requests,
        "screenshot": str(shot.relative_to(PROJECT_ROOT)),
    }
    context.close()
    return result


def main() -> int:
    harness.prepare_isolated_db()
    with sqlite3.connect(harness.ISOLATED_DB) as con:
        for student_id in ("V097C-W2-ED", "V097C-W2-ZM"):
            con.execute(
                "INSERT OR IGNORE INTO students (student_id, created_at, "
                "is_synthetic) VALUES (?, '2026-08-05T00:00:00+00:00', 1)",
                (student_id,))
        con.commit()
    api = streamlit = None
    evidence: dict = {"run_id": "v0.9.7-c-wu2-midpoint"}
    try:
        api, streamlit = harness.start_stack("w2_smoke")
        seed_cycle("V097C-W2-ED")
        seed_cycle("V097C-W2-ZM")
        payload = requests.get(
            f"{harness.BASE}/api/v1/students/V097C-W2-ED/journey",
            timeout=30).json()
        assert payload["cycles_version"] == "journey-cycle-v0.9.7-c"
        assert len(payload["cycles"]) == 1
        actions = payload["cycles"][0]["available_actions"]
        assert any(a["action"] == "open_revision" for a in actions)
        assert any(a["action"] == "open_practice" for a in actions)
        evidence["cycle_view"] = {
            "version": payload["cycles_version"],
            "cycle_count": len(payload["cycles"]),
            "actions": actions,
        }
        before = whole_db_counts()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                evidence["en_desktop"] = run(
                    browser, "V097C-W2-ED", "en",
                    {"width": 1280, "height": 900}, "en_1280x900")
                evidence["zh_mobile"] = run(
                    browser, "V097C-W2-ZM", "zh_CN",
                    {"width": 390, "height": 844}, "zh_390x844")
            finally:
                browser.close()
        after = whole_db_counts()
        assert before == after
        evidence["journey_reads_zero_writes"] = True
    finally:
        harness.stop_stack(api, streamlit)
    (HERE / "midpoint_smoke_evidence.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    for combo in ("en_desktop", "zh_mobile"):
        item = evidence[combo]
        assert not item["console_errors"], item
        assert not item["page_errors"], item
        assert not item["remote_requests"], item
        assert item["exceptions"] == 0 and not item["overflow"]
        assert not item["raw_keys"]
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
