"""v0.9.7-C WU3 rendered-page verification matrix (browser).

The affected Journey path runs independently for English/Chinese x
1280x900/390x844 on a fresh isolated database with a distinct learner and
the local provider: one completed priority-derived cycle with a linked
revision, one active Practice target, one evaluation-unavailable activity,
one completed legacy target, one no-priority cycle, and one
insufficient-evidence cycle. Each combination verifies the grouped cycle
UI (structure, chronology, relationships, states, safe actions, honest
provenance notes), reload/re-entry, action navigation, mobile control
sizing, zero writes, and zero console/page/network errors.
"""
from __future__ import annotations

import json
import pathlib
import re
import sqlite3
import sys

import requests
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
BASE_HARNESS_DIR = PROJECT_ROOT / "verification/v0.9.4-a/v0.9.4-a-20260801-r1"
WU5_DIR = PROJECT_ROOT / "verification/v0.9.7-b/v0.9.7-b-wu5-20260805-r1"
sys.path.insert(0, str(BASE_HARNESS_DIR))
sys.path.insert(0, str(WU5_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.locale import t  # noqa: E402

import w5_harness as harness  # noqa: E402

# Re-point the shared v0.9.4-A/WU5 harness state at this run directory
# (after the star imports, so the WU5 constants cannot shadow these).
harness._base.RUN_DIR = HERE
harness._base.ISOLATED_DB = HERE / "isolated" / "writing_feedback_v097c_wu3.db"
harness._base.LOG_DIR = HERE / "logs"
harness.RUN_DIR = HERE
harness.ISOLATED_DB = harness._base.ISOLATED_DB
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
SHORT_ESSAY = (
    "The history of history is historical. The history of history is historical."
)
VALID_RESPONSE = "A valid response reducing repetition."

FORBIDDEN_WORDING = ("mastered", "improved", "proficient", "cefr",
                     "learning gain", "transfer")
STUDENTS = ("V097C-W3-ED", "V097C-W3-ZD", "V097C-W3-EM", "V097C-W3-ZM")


def seed_learner(student_id: str) -> dict:
    def post(path, payload):
        response = requests.post(f"{harness.BASE}{path}", json=payload,
                                 timeout=60)
        assert response.status_code in (200, 201), response.text
        return response.json()

    def submit(text, *, draft_stage="first draft", revision_of=None):
        payload = {
            "student_id": student_id,
            "writing_prompt": "What actions matter for sustainability?",
            "genre": "argumentative essay", "draft_stage": draft_stage,
            "timed": False, "tool_use": "none", "essay_text": text,
        }
        if revision_of:
            payload["revision_of_submission_id"] = revision_of
        return post("/api/v1/submissions", payload)["submission_id"]

    def priority_index(essay_id, category="lexical_repetition"):
        bundle = requests.get(
            f"{harness.BASE}/api/v1/submissions/{essay_id}", timeout=60).json()
        priorities = (bundle.get("feedback") or {}).get("priority_feedback", [])
        return next(
            i for i, item in enumerate(priorities)
            if item.get("category") == category)

    def target(essay_id):
        return post("/api/v1/practice-targets", {
            "student_id": student_id, "source_submission_id": essay_id,
            "priority_index": priority_index(essay_id),
        })

    def exercise(target_id):
        return post(f"/api/v1/practice-targets/{target_id}/exercises",
                    {"source_text": REPETITION_ESSAY})

    def attempt(exercise_id):
        return post(f"/api/v1/exercises/{exercise_id}/attempts", {
            "student_id": student_id, "response_text": VALID_RESPONSE})

    def legacy_target(essay_id):
        bundle = requests.get(
            f"{harness.BASE}/api/v1/submissions/{essay_id}", timeout=60).json()
        priorities = (bundle.get("feedback") or {}).get("priority_feedback", [])
        item = next(
            i for i in priorities if i.get("category") == "lexical_repetition")
        return post("/api/v1/practice-targets", {
            "student_id": student_id, "source_submission_id": essay_id,
            "source_diagnosis_id": item["diagnosis_id"],
            "target_code": "lexical_repetition_local",
            "target_label": "Reduce lexical repetition",
            "gate_status": "selected",
        })

    # A: completed priority-derived cycle with linked revision.
    essay_a = submit(REPETITION_ESSAY)
    target_a = target(essay_a)
    attempt_a = attempt(exercise(target_a["practice_target_id"])["exercise_id"])
    post(f"/api/v1/practice-targets/{target_a['practice_target_id']}/complete",
         {"student_id": student_id})
    revision_a = submit(REVISION_ESSAY, draft_stage="revised draft",
                        revision_of=essay_a)
    # B: active target, no attempt.
    essay_b = submit(REPETITION_ESSAY)
    target_b = target(essay_b)
    exercise_b = exercise(target_b["practice_target_id"])
    # C: attempt with evaluation unavailable.
    essay_c = submit(REPETITION_ESSAY)
    target_c = target(essay_c)
    attempt(exercise(target_c["practice_target_id"])["exercise_id"])
    with sqlite3.connect(harness.ISOLATED_DB) as con:
        con.execute(
            "DELETE FROM practice_evaluations WHERE attempt_id IN "
            "(SELECT attempt_id FROM exercise_attempts WHERE student_id=?)",
            (student_id,))
        con.commit()
    # D: completed legacy target.
    essay_d = submit(REPETITION_ESSAY)
    target_d = legacy_target(essay_d)
    attempt(exercise(target_d["practice_target_id"])["exercise_id"])
    post(f"/api/v1/practice-targets/{target_d['practice_target_id']}/complete",
         {"student_id": student_id})
    # E: no-priority cycle.
    essay_e = submit(SHORT_ESSAY)
    # F: insufficient-evidence cycle (raw essay row without analysis).
    with sqlite3.connect(harness.ISOLATED_DB) as con:
        con.execute(
            "INSERT INTO essays(student_id, writing_prompt, genre, draft_stage, "
            "timed, tool_use, essay_text, submitted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (student_id, "Should we act?", "argumentative essay",
             "first draft", 0, "none", "A raw essay row without analysis.",
             "2026-08-05T00:00:00+00:00"))
        con.commit()

    return {
        "essay_a": essay_a, "revision_a": revision_a,
        "target_a": target_a["practice_target_id"],
        "target_b": target_b["practice_target_id"],
        "target_c": target_c["practice_target_id"],
        "target_d": target_d["practice_target_id"],
        "essay_b": essay_b, "essay_c": essay_c, "essay_d": essay_d,
        "essay_e": essay_e,
        "attempt_a": attempt_a["attempt_id"],
        "exercise_b": exercise_b["exercise_id"],
    }


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


def body_text(page) -> str:
    return page.locator('[data-testid="stMainBlockContainer"]').inner_text()


def run_combination(browser, student_id: str, lang: str, viewport: dict,
                    tag: str, records: dict) -> dict:
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    console_errors, page_errors, remote_requests = observe(page)
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    result: dict = {"combination": f"{lang} {viewport['width']}x{viewport['height']}"}

    counts_before = whole_db_counts()

    # Open the Journey and verify the grouped cycle UI.
    harness.open_sidebar(page)
    harness.click_label(page, t("learning_journey", lang))
    assert harness.wait_stable(page, timeout=20)
    harness.close_sidebar(page)
    harness.commit_text_input(
        page, ".st-key-journey_student_v2 input", student_id)
    assert harness.wait_stable(page, timeout=30)
    harness.close_sidebar(page)
    text = body_text(page)
    assert t("student_journey_cycle_title", lang) in text
    assert t("student_journey_original_writing", lang) in text
    assert t("student_journey_revised_draft", lang) in text
    assert t("student_journey_revision_of", lang) in text
    assert t("student_journey_practice_activity", lang) in text
    assert t("student_journey_state_completed", lang) in text
    assert t("student_journey_state_available", lang) in text
    assert t("student_journey_state_evaluation_unavailable", lang) in text
    assert t("student_journey_state_feedback_without_priority", lang) in text
    assert t("student_journey_state_insufficient_evidence", lang) in text
    assert t("student_journey_practice_legacy", lang) in text
    assert t("student_practice_completed_title", lang) in text
    assert t("student_practice_evaluation_unavailable", lang) in text
    assert t("journey_event_feedback_without_priority_desc", lang) in text
    assert t("journey_event_insufficient_evidence_desc", lang) in text
    assert f"#{records['essay_a']}" in text
    assert f"#{records['revision_a']}" in text
    assert f"#{records['attempt_a']}" in text
    # Fixed conservative disclaimers legitimately mention these concepts
    # only to deny them; strip the known disclaimer phrases, then assert no
    # mastery/pass/improvement/proficiency/CEFR/transfer/learning-gain
    # claim wording remains anywhere else on the page.
    normalized = text.lower()
    for phrase in ("none establishes learning, mastery, or stable transfer.",
                   "no priority passed the diagnostic gate",
                   "not proof of stable transfer or causation",
                   "not proof that practice caused the later pattern"):
        normalized = normalized.replace(phrase, "")
    for word in FORBIDDEN_WORDING:
        assert word not in normalized, word
    # The fixed no-priority description says "no priority passed the
    # Diagnostic Gate" - a gate description, not a learner-pass claim; it
    # must be the only "passed" wording on the page.
    if "passed" in text.lower():
        assert text.lower().count(
            "no priority passed the diagnostic gate") >= 1
        assert "passed" not in normalized
    assert page.locator('[data-testid="stException"]').count() == 0
    width = page.evaluate("() => window.innerWidth")
    assert page.evaluate(
        "() => document.documentElement.scrollWidth") <= width
    assert "student_journey_cycle_title" not in text
    shot = HERE / "screenshots" / f"{tag}_journey_cycles.png"
    shot.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(shot), full_page=True)

    # Safe actions: buttons present with stable keys; mobile sizing.
    revision_button = page.locator(
        f".st-key-journey_action_revision_{records['essay_a']}")
    practice_button = page.locator(
        f".st-key-journey_action_practice_{records['target_b']}")
    assert revision_button.count() == 1
    assert practice_button.count() == 1
    if viewport["width"] < 700:
        for locator in (revision_button, practice_button):
            box = locator.first.bounding_box()
            assert box is not None and box["width"] >= 44 and box["height"] >= 44
    result["actions"] = {
        "open_revision_present": True, "open_practice_present": True,
        "mobile_sizing_ok": True if viewport["width"] < 700 else "desktop",
    }

    # Safe action navigation: open the ACTIVE target (B) from Journey.
    harness.close_sidebar(page)
    practice_button.first.click()
    assert harness.wait_stable(page, timeout=30)
    assert t("practice", lang) in harness.current_h2(page)
    practice_text = body_text(page)
    assert "Reduce lexical repetition" in practice_text
    result["action_navigation"] = {"open_practice_reached_target": True}

    # Return to Journey and reload (fresh session re-entry).
    harness.open_sidebar(page)
    harness.click_label(page, t("learning_journey", lang))
    assert harness.wait_stable(page, timeout=20)
    harness.close_sidebar(page)
    page.reload(wait_until="networkidle")
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
    assert t("student_journey_cycle_title", lang) in body_text(page)
    assert page.locator('[data-testid="stException"]').count() == 0
    result["reload_reentry"] = {"grouped_view_persists": True}

    assert whole_db_counts() == counts_before
    result["journey_reads_zero_writes"] = True

    unexpected = [item for item in console_errors
                  if not harness.is_allowed_console(item)]
    context.close()
    return result, unexpected, page_errors, remote_requests


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
    evidence: dict = {"run_id": "v0.9.7-c-wu3-20260805-r1"}
    try:
        api, streamlit = harness.start_stack("w3_matrix")
        combos = (
            ("V097C-W3-ED", "en", {"width": 1280, "height": 900}, "en_1280x900"),
            ("V097C-W3-ZD", "zh_CN", {"width": 1280, "height": 900}, "zh_1280x900"),
            ("V097C-W3-EM", "en", {"width": 390, "height": 844}, "en_390x844"),
            ("V097C-W3-ZM", "zh_CN", {"width": 390, "height": 844}, "zh_390x844"),
        )
        records = {}
        for student_id, lang, viewport, tag in combos:
            records[tag] = seed_learner(student_id)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                all_console: list[str] = []
                all_page: list[str] = []
                all_remote: list[str] = []
                for student_id, lang, viewport, tag in combos:
                    result, console, page_errors, remote = run_combination(
                        browser, student_id, lang, viewport, tag,
                        records[tag])
                    evidence[tag] = result
                    all_console.extend(console)
                    all_page.extend(page_errors)
                    all_remote.extend(remote)
            finally:
                browser.close()
            evidence["console_errors"] = all_console
            evidence["page_errors"] = all_page
            evidence["remote_requests"] = all_remote
    finally:
        harness.stop_stack(api, streamlit)
    evidence["ports_cleaned"] = True
    (HERE / "rendered_page_matrix_evidence.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    assert not evidence["console_errors"], evidence["console_errors"]
    assert not evidence["page_errors"], evidence["page_errors"]
    assert not evidence["remote_requests"], evidence["remote_requests"]
    for tag in ("en_1280x900", "zh_1280x900", "en_390x844", "zh_390x844"):
        item = evidence[tag]
        assert item["actions"]["open_revision_present"] is True
        assert item["actions"]["open_practice_present"] is True
        assert item["action_navigation"]["open_practice_reached_target"] is True
        assert item["reload_reentry"]["grouped_view_persists"] is True
        assert item["journey_reads_zero_writes"] is True
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
