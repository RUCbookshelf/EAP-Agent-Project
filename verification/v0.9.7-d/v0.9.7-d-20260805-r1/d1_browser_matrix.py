"""v0.9.7-D D1.2 representative rendered comparison (browser).

Real production stack (LLM_PROVIDER=local, isolated DB): seed one complete
priority-derived writing cycle (submission -> feedback priority -> practice
target -> exercise -> attempt -> evaluation -> completed target -> linked
revision) plus one additional active target, then render the redesigned
Student Journey page in English/Chinese x 1280x900/390x844.

Verifies the design-system structure on the real DOM (cycle card head,
stage items, status badges), the sans heading role, no exceptions/overflow/
remote requests/raw keys/unsupported claims, mobile touch targets >= 44px,
and zero writes across all Journey renders. Captures first-implementation
screenshots (before references: verification/v0.9.7-c/wu4 screenshots).
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
harness.ISOLATED_DB = HERE / "isolated" / "writing_feedback_v097d_d1.db"
harness.LOG_DIR = HERE / "logs"

SCREENSHOTS = HERE / "screenshots"
RUN_ID = "v0.9.7-d-20260805-r1"
STUDENTS = ("V097D-D1-ED", "V097D-D1-ZD", "V097D-D1-EM", "V097D-D1-ZM")

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

FORBIDDEN_WORDING = (
    "mastery", "proficient", "cefr", "learning gain", "improved your writing",
)


def post(path: str, payload: dict) -> dict:
    response = requests.post(f"{harness.BASE}{path}", json=payload, timeout=60)
    assert response.status_code in (200, 201), response.text
    return response.json()


def seed_cycle(student_id: str) -> None:
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
    post(f"/api/v1/practice-targets/{target['practice_target_id']}/complete", {
        "student_id": student_id,
    })
    post("/api/v1/submissions", {
        "student_id": student_id,
        "writing_prompt": "What actions matter for sustainability?",
        "genre": "argumentative essay", "draft_stage": "revised draft",
        "timed": False, "tool_use": "none", "essay_text": REVISION_ESSAY,
        "revision_of_submission_id": essay_id,
    })
    diagnosis_id = priorities[index]["diagnosis_id"]
    post("/api/v1/practice-targets", {
        "student_id": student_id, "source_submission_id": essay_id,
        "source_diagnosis_id": diagnosis_id,
        "target_code": "lexical_repetition_local",
        "target_label": "Reduce lexical repetition",
        "gate_status": "selected",
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
    assert harness.wait_stable(page, timeout=30)
    harness.close_sidebar(page)

    assert page.locator('[data-testid="px-cycle-head"]').count() == 1
    assert page.locator('[data-testid="px-stage-item"]').count() >= 3
    assert page.locator('[data-testid="px-status-badge"]').count() >= 3
    badges = page.locator('[data-testid="px-status-badge"]')
    states = set(badges.evaluate_all(
        "els => els.map(e => e.getAttribute('data-state'))"))
    assert "success" in states
    assert "neutral" in states or "info" in states
    family = page.evaluate(
        "() => getComputedStyle(document.querySelector('h2.px-page-heading')).fontFamily"
    )
    assert "monospace" not in family.lower()
    assert "cascadia" not in family.lower()
    assert "consolas" not in family.lower()

    exceptions = page.locator('[data-testid="stException"]').count()
    width = page.evaluate("() => window.innerWidth")
    overflow = page.evaluate(
        "() => document.documentElement.scrollWidth") > width
    text = page.locator('[data-testid="stMainBlockContainer"]').inner_text()
    raw_keys = [key for key in ("student_journey_", "journey_", "student_practice_")
                if key in text]
    normalized = text.lower()
    for phrase in ("none establishes learning, mastery, or stable transfer.",
                   "no priority passed the diagnostic gate",
                   "not proof of stable transfer or causation",
                   "not proof that practice caused the later pattern"):
        normalized = normalized.replace(phrase, "")
    forbidden = [word for word in FORBIDDEN_WORDING if word in normalized]
    assert exceptions == 0 and not overflow and not raw_keys and not forbidden

    if viewport["width"] < 700:
        target_selector = (
            '[data-testid="stBaseButton-primary"],'
            ' [data-testid="stBaseButton-secondary"],'
            ' .st-key-journey_student_v2 input'
        )
        targets = page.locator(target_selector)
        for index in range(targets.count()):
            box = targets.nth(index).bounding_box()
            assert box is not None and box["height"] >= 44, \
                (tag, index, box)

    shot = SCREENSHOTS / f"{tag}_journey_design_system.png"
    shot.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(shot), full_page=True)
    unexpected = [item for item in console_errors
                  if not harness.is_allowed_console(item)]
    result = {
        "combination": f"{lang} {viewport['width']}x{viewport['height']}",
        "cycle_cards": 1,
        "stage_items": page.locator('[data-testid="px-stage-item"]').count(),
        "badge_states": sorted(states),
        "heading_sans": True,
        "exceptions": exceptions, "overflow": overflow,
        "raw_keys": raw_keys, "forbidden": forbidden,
        "console_errors": unexpected, "page_errors": page_errors,
        "remote_requests": remote_requests,
        "screenshot": str(shot.relative_to(PROJECT_ROOT)),
    }
    context.close()
    return result


def main() -> int:
    harness.prepare_isolated_db()
    with sqlite3.connect(harness.ISOLATED_DB) as con:
        for student_id in STUDENTS:
            con.execute(
                "INSERT OR IGNORE INTO students (student_id, created_at, "
                "is_synthetic) VALUES (?, '2026-08-05T00:00:00+00:00', 1)",
                (student_id,))
        con.commit()
    api = streamlit = None
    evidence: dict = {"run_id": RUN_ID}
    try:
        api, streamlit = harness.start_stack("d1_matrix")
        for student_id in STUDENTS:
            seed_cycle(student_id)
        payload = requests.get(
            f"{harness.BASE}/api/v1/students/{STUDENTS[0]}/journey",
            timeout=30).json()
        assert payload["cycles_version"] == "journey-cycle-v0.9.7-c"
        assert len(payload["cycles"]) == 1
        states = {p["activity_state"]
                  for p in payload["cycles"][0]["practice_cycles"]}
        assert states == {"completed", "available"}, states
        evidence["cycle_view"] = {
            "version": payload["cycles_version"],
            "cycle_count": len(payload["cycles"]),
            "practice_states": sorted(states),
        }
        before = whole_db_counts()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                evidence["en_desktop"] = run(
                    browser, STUDENTS[0], "en",
                    {"width": 1280, "height": 900}, "en_1280x900")
                evidence["zh_desktop"] = run(
                    browser, STUDENTS[1], "zh_CN",
                    {"width": 1280, "height": 900}, "zh_1280x900")
                evidence["en_mobile"] = run(
                    browser, STUDENTS[2], "en",
                    {"width": 390, "height": 844}, "en_390x844")
                evidence["zh_mobile"] = run(
                    browser, STUDENTS[3], "zh_CN",
                    {"width": 390, "height": 844}, "zh_390x844")
            finally:
                browser.close()
        after = whole_db_counts()
        assert before == after
        evidence["journey_reads_zero_writes"] = True
    finally:
        harness.stop_stack(api, streamlit)
    (HERE / "rendered_page_matrix_evidence.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    for combo in ("en_desktop", "zh_desktop", "en_mobile", "zh_mobile"):
        item = evidence[combo]
        assert not item["console_errors"], item
        assert not item["page_errors"], item
        assert not item["remote_requests"], item
        assert item["exceptions"] == 0 and not item["overflow"]
        assert not item["raw_keys"] and not item["forbidden"]
        assert item["heading_sans"]
        assert item["cycle_cards"] == 1
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
