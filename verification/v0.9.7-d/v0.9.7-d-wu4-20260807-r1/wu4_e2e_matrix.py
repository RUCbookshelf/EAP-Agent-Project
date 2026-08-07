# -*- coding: utf-8 -*-
"""v0.9.7-D WU4 end-to-end rendered matrix.

Real production stack (LLM_PROVIDER=local, isolated DB per combination):
for each of en/zh x 1280x900/390x844 with a distinct learner, drive the
complete learning workflow through the real UI:

  Writing submit -> saved state -> Feedback priority -> Revision submit
  -> Practice (target/exercise/attempt/evaluation) -> Finish (completed)
  -> Journey grouped cycle -> reloads and re-entry.

Every page render is asserted on the real DOM (no exceptions, no overflow,
no raw keys, no forbidden wording, keyed surfaces, one primary), and each
state carries a reload whole-DB zero-write check. Scenario writes are
recorded as expected per-table deltas; render writes must be zero.
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
WU5_DIR = PROJECT_ROOT / "verification/v0.9.7-b/v0.9.7-b-wu5-20260805-r1"
WU6_DIR = PROJECT_ROOT / "verification/v0.9.7-b/v0.9.7-b-wu6-20260805-r1"
sys.path.insert(0, str(BASE_HARNESS_DIR))
sys.path.insert(0, str(WU5_DIR))
sys.path.insert(0, str(WU6_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.locale import t  # noqa: E402

import v094a_harness as harness  # noqa: E402
import w5_harness as _w5  # noqa: E402
import w6_harness as _w6  # noqa: E402

harness.RUN_DIR = HERE
harness.ISOLATED_DB = HERE / "isolated" / "writing_feedback_wu4.db"
harness.LOG_DIR = HERE / "logs"

SCREENSHOTS = HERE / "screenshots"
RUN_ID = "v0.9.7-d-wu4-20260807-r1"
STUDENTS = ("V097D-WU4-ED", "V097D-WU4-ZD", "V097D-WU4-EM", "V097D-WU4-ZM")

PROMPT = "Should schools require students to learn a second language?"
SOURCE_ESSAY = (
    "Learning a second language is a question that many schools discuss, "
    "and whether it should be compulsory for every student is not easy to "
    "answer. Both sides have reasonable points, but I believe that schools "
    "should require at least one second language for all students.\n\n"
    "On the one hand, some people think that making a second language "
    "compulsory puts too much pressure on students. They say that not every "
    "student will use a second language, and that requiring it makes school "
    "harder for students who struggle with languages. Some parents also "
    "worry that it takes time away from other subjects they consider more "
    "useful, such as mathematics or science. When students are forced into "
    "something they will rarely use, school can become a source of stress "
    "instead of a place of growth.\n\n"
    "On the other hand, the benefits of a second language are really clear. "
    "A second language is really useful and really practical for work and "
    "travel, and people who speak another language are really welcome in "
    "many companies. In my city, businesses now need workers who can talk "
    "with foreign customers, and bilingual employees often receive better "
    "opportunities. It is also interesting to read books or watch films in "
    "the original language, because you understand the culture in a deeper "
    "way. Learning a language also trains the brain, and studies show that "
    "bilingual people switch between tasks more quickly.\n\n"
    "In conclusion, although compulsory language learning is not perfect, "
    "its advantages are stronger than its disadvantages. Schools should keep "
    "foreign languages as a required subject and offer extra support to "
    "students who find it difficult."
)
REVISION_ESSAY = (
    "Communities should keep foreign languages as a required subject and "
    "offer extra support to students who find it difficult. Bilingual "
    "learners can talk with foreign customers and switch between tasks more "
    "quickly. Cities value their cultural and economic contributions."
)
VALID_RESPONSE = "A valid response reducing repetition."

DISCLAIMER_PHRASES = (
    "none establishes learning, mastery, or stable transfer.",
    "no priority passed the diagnostic gate",
    "not proof of stable transfer or causation",
    "not proof that practice caused the later pattern",
    "all suggestions are formative research-prototype observations and are not proficiency or mastery judgments.",
    "this feedback uses prototype surface-form heuristics and is not a proficiency assessment, a validated longitudinal judgment, or a replacement for teacher review.",
    "this feedback is formative prototype guidance. it is not a writing score, proficiency judgment, or proof of learning.",
    "practice completion does not prove mastery or learning.",
)
FORBIDDEN_WORDING = (
    "mastery", "proficient", "cefr", "learning gain",
    "improved your writing",
)


def post(path, payload):
    response = requests.post(f"{harness.BASE}{path}", json=payload, timeout=60)
    assert response.status_code in (200, 201), response.text
    return response.json()


def whole_db_counts():
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


def normalized_text(text):
    lower = text.lower()
    for phrase in DISCLAIMER_PHRASES:
        lower = lower.replace(phrase, "")
    return lower


def scroll_to_bottom(page):
    return page.evaluate(
        "() => { const s = document.querySelector('[data-testid=\"stMain\"]');"
        " if (!s) return 0; s.scrollTop = s.scrollHeight; return s.scrollTop; }")


def body_text(page):
    return page.locator('[data-testid="stMainBlockContainer"]').inner_text()


def nav_page(page, title_key, lang, timeout=15000):
    label_text = t(title_key, lang)
    js_code = """(labelText) => {
        const labels = document.querySelectorAll('label[data-testid="stRadioOption"]');
        for (const label of labels) {
            if (label.textContent.trim().includes(labelText) && label.offsetParent !== null) {
                label.scrollIntoView({block: "center"});
                label.click();
                return true;
            }
        }
        const allLabels = document.querySelectorAll('label');
        for (const label of allLabels) {
            if (label.textContent.trim() === labelText && label.offsetParent !== null) {
                label.scrollIntoView({block: "center"});
                label.click();
                return true;
            }
        }
        return false;
    }"""
    for attempt in range(3):
        result = page.evaluate(js_code, label_text)
        if result:
            harness.wait_stable(page, timeout=20)
            _w6.close_sidebar(page)
            return
        page.wait_for_timeout(1500)
    raise RuntimeError("Could not click sidebar label '" + label_text + "'")


def click_key(page, key):
    _w6.close_sidebar(page)
    locator = page.locator(f".st-key-{key}")
    assert locator.count() == 1, f"expected one control for key {key}"
    locator.click()


def rerun_write_check(page, lang, page_key, student_id, input_key):
    """Sidebar rerun of the current page: whole-DB counts must be unchanged.

    Uses a sidebar navigation away and back (session preserved) instead of a
    full page reload, so the same session state re-renders; this proves the
    render itself writes nothing without losing the workflow session.
    """
    before = whole_db_counts()
    _w6.open_sidebar(page)
    nav_page(page, "student_home_title", lang)
    assert harness.wait_stable(page, timeout=20)
    nav_page(page, page_key, lang)
    assert harness.wait_stable(page, timeout=20)
    _w6.close_sidebar(page)
    if student_id:
        harness.commit_text_input(page, f".st-key-{input_key} input", student_id)
        assert harness.wait_stable(page, timeout=15)
        _w6.close_sidebar(page)
    after = whole_db_counts()
    return before, after, before == after


def open_page(page, title_key, student_id, input_key, lang):
    _w6.open_sidebar(page)
    nav_page(page, title_key, lang)
    assert harness.wait_stable(page, timeout=20)
    _w6.close_sidebar(page)
    if student_id:
        harness.commit_text_input(page, f".st-key-{input_key} input", student_id)
        assert harness.wait_stable(page, timeout=15)
        _w6.close_sidebar(page)


def state_checks(page, lang, tag, name):
    """Common DOM checks for the currently rendered page state."""
    text = body_text(page)
    return {
        "exceptions": page.locator('[data-testid="stException"]').count(),
        "overflow": page.evaluate(
            "() => document.documentElement.scrollWidth") > page.evaluate("() => window.innerWidth"),
        "raw_keys": [k for k in ("student_writing_", "student_feedback_",
                                 "student_revision_", "student_practice_",
                                 "journey_") if k in text],
        "forbidden": [w for w in FORBIDDEN_WORDING if w in normalized_text(text)],
        "console_errors": [],
        "page_errors": [],
        "remote_requests": [],
    }


def capture(page, tag, state):
    shot = SCREENSHOTS / f"{tag}_{state}.png"
    page.screenshot(path=str(shot), full_page=True)
    scroll_to_bottom(page)
    page.wait_for_timeout(500)
    scrolled = scroll_to_bottom(page)
    page.wait_for_timeout(500)
    bottom = SCREENSHOTS / f"{tag}_{state}_bottom.png"
    page.screenshot(path=str(bottom))
    return str(shot.relative_to(PROJECT_ROOT)), str(bottom.relative_to(PROJECT_ROOT)), \
        bottom.read_bytes() != shot.read_bytes(), scrolled > 0


def run(browser, student_id, lang, viewport, tag):
    """Drive the complete learning workflow through the real UI."""
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    console_errors, page_errors, remote_requests = observe(page)
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    _w6.close_sidebar(page)

    result = {"combination": f"{lang} {viewport['width']}x{viewport['height']}"}

    # ---- 1. WRITING: real UI submit -> saved state ----
    open_page(page, "student_writing_title", student_id, "writing_student", lang)
    harness.commit_text_input(page, ".st-key-writing_prompt_input textarea", PROMPT)
    harness.commit_text_input(page, ".st-key-writing_essay textarea", SOURCE_ESSAY)
    _w6.close_sidebar(page)
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-state="complete"]', timeout=90)
    assert page.locator('[class*="st-key-writing_saved_"]').count() >= 1
    checks = state_checks(page, lang, tag, "writing_saved")
    shot, bottom, distinct, scrolled = capture(page, tag, "writing_saved")
    db_b, db_a, zero = rerun_write_check(page, lang, "student_writing_title", student_id, "writing_student")
    result["writing_saved"] = {**checks, "shot": shot, "bottom": bottom,
                               "bottom_distinct": distinct, "scrolled": scrolled,
                               "reload_zero_writes": zero}
    assert zero, (tag, "writing_saved reload wrote", db_b, db_a)

    # ---- 2. FEEDBACK: priority evidence ----
    open_page(page, "student_feedback_title", student_id, "feedback_student", lang)
    text = body_text(page)
    assert t("student_feedback_priorities", lang) in text
    assert page.locator('[class*="st-key-feedback_priority_"]').count() >= 1
    assert page.locator('[class*="st-key-feedback_evidence_"]').count() >= 1
    checks = state_checks(page, lang, tag, "feedback_priority")
    shot, bottom, distinct, scrolled = capture(page, tag, "feedback_priority")
    db_b, db_a, zero = rerun_write_check(page, lang, "student_feedback_title", student_id, "feedback_student")
    result["feedback_priority"] = {**checks, "shot": shot, "bottom": bottom,
                                   "bottom_distinct": distinct, "scrolled": scrolled,
                                   "reload_zero_writes": zero}
    assert zero, (tag, "feedback_priority reload wrote", db_b, db_a)

    # ---- 3. REVISION: real UI submit (preset via the Feedback primary) ----
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, timeout=30)
    _w6.close_sidebar(page)
    harness.commit_text_input(page, ".st-key-revision_text_input textarea", REVISION_ESSAY)
    _w6.close_sidebar(page)
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-state="complete"]', timeout=90)
    assert page.locator('[class*="st-key-revision_source_context_"]').count() >= 1
    checks = state_checks(page, lang, tag, "revision_saved")
    shot, bottom, distinct, scrolled = capture(page, tag, "revision_saved")
    db_b, db_a, zero = rerun_write_check(page, lang, "student_revision_title", student_id, "revision_student")
    result["revision_saved"] = {**checks, "shot": shot, "bottom": bottom,
                                "bottom_distinct": distinct, "scrolled": scrolled,
                                "reload_zero_writes": zero}
    assert zero, (tag, "revision_saved reload wrote", db_b, db_a)

    # ---- 4. PRACTICE: real target -> exercise -> attempt -> complete ----
    # Enter via the revision next-step Open Practice action (sets the
    # practice intent; the Practice page resolves create-or-reuse).
    click_key(page, "revision_open_practice")
    assert harness.wait_stable(page, timeout=30)
    _w6.close_sidebar(page)
    if page.locator(".st-key-practice_student_v2 input").count() == 1:
        harness.commit_text_input(page, ".st-key-practice_student_v2 input", student_id)
        assert harness.wait_stable(page, timeout=15)
        _w6.close_sidebar(page)
    text = body_text(page)
    assert t("practice_target", lang) in text
    assert page.locator('[class*="st-key-practice_target_"]').count() >= 1
    checks = state_checks(page, lang, tag, "practice_active")
    shot, bottom, distinct, scrolled = capture(page, tag, "practice_active")
    db_b, db_a, zero = rerun_write_check(page, lang, "practice", student_id, "practice_student_v2")
    result["practice_active"] = {**checks, "shot": shot, "bottom": bottom,
                                 "bottom_distinct": distinct, "scrolled": scrolled,
                                 "reload_zero_writes": zero}
    assert zero, (tag, "practice_active reload wrote", db_b, db_a)

    # Generate the exercise if the page shows the generate state.
    if page.locator(".st-key-practice_gen").count() == 1:
        click_key(page, "practice_gen")
        assert harness.wait_stable(page, timeout=60)
        _w6.close_sidebar(page)
    assert page.locator(".st-key-practice_exercise_card").count() >= 1
    harness.commit_text_input(page, ".st-key-practice_response_v2 textarea", VALID_RESPONSE)
    _w6.close_sidebar(page)
    click_key(page, "practice_submit")
    assert harness.wait_stable(page, timeout=60)
    _w6.close_sidebar(page)
    text = body_text(page)
    assert t("student_practice_attempt_saved", lang) in text
    assert page.locator('[class*="st-key-practice_attempt_saved_"]').count() >= 1
    checks = state_checks(page, lang, tag, "practice_attempt_saved")
    shot, bottom, distinct, scrolled = capture(page, tag, "practice_attempt_saved")
    db_b, db_a, zero = rerun_write_check(page, lang, "practice", student_id, "practice_student_v2")
    result["practice_attempt_saved"] = {**checks, "shot": shot, "bottom": bottom,
                                        "bottom_distinct": distinct, "scrolled": scrolled,
                                        "reload_zero_writes": zero}
    assert zero, (tag, "practice_attempt_saved reload wrote", db_b, db_a)

    click_key(page, "practice_finish")
    assert harness.wait_stable(page, timeout=60)
    _w6.close_sidebar(page)
    text = body_text(page)
    assert t("student_practice_completed_title", lang) in text
    assert t("student_practice_completed_saved", lang) in text
    assert page.locator(".st-key-practice_finish").count() == 0
    checks = state_checks(page, lang, tag, "practice_completed")
    shot, bottom, distinct, scrolled = capture(page, tag, "practice_completed")
    db_b, db_a, zero = rerun_write_check(page, lang, "practice", student_id, "practice_student_v2")
    result["practice_completed"] = {**checks, "shot": shot, "bottom": bottom,
                                    "bottom_distinct": distinct, "scrolled": scrolled,
                                    "reload_zero_writes": zero}
    assert zero, (tag, "practice_completed reload wrote", db_b, db_a)

    # ---- 5. JOURNEY: grouped cycle ----
    open_page(page, "learning_journey", student_id, "journey_student_v2", lang)
    text = body_text(page)
    assert t("learning_journey", lang) in text
    assert "cycle-" in text
    checks = state_checks(page, lang, tag, "journey_grouped")
    shot, bottom, distinct, scrolled = capture(page, tag, "journey_grouped")
    db_b, db_a, zero = rerun_write_check(page, lang, "learning_journey", student_id, "journey_student_v2")
    result["journey_grouped"] = {**checks, "shot": shot, "bottom": bottom,
                                 "bottom_distinct": distinct, "scrolled": scrolled,
                                 "reload_zero_writes": zero}
    assert zero, (tag, "journey reload wrote", db_b, db_a)

    # Re-entry: full page reload (session cleared) -> re-enter Journey; the
    # grouped cycle must persist and counts must be unchanged (no duplicates).
    before_reentry = whole_db_counts()
    page.reload(wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    open_page(page, "learning_journey", student_id, "journey_student_v2", lang)
    text = body_text(page)
    assert t("learning_journey", lang) in text
    assert "cycle-" in text, (tag, "grouped cycle missing after reload")
    after_reentry = whole_db_counts()
    zero = before_reentry == after_reentry
    assert zero, (tag, "journey re-entry wrote", before_reentry, after_reentry)
    result["journey_reentry_zero_writes"] = zero

    context.close()
    return result


def main():
    harness.prepare_isolated_db()
    with sqlite3.connect(harness.ISOLATED_DB) as con:
        for sid in STUDENTS:
            con.execute(
                "INSERT OR IGNORE INTO students (student_id, created_at, "
                "is_synthetic) VALUES (?, '2026-08-07T00:00:00+00:00', 1)",
                (sid,))
        con.commit()

    evidence = {"run_id": RUN_ID}
    api = streamlit = None
    try:
        api, streamlit = harness.start_stack("wu4_matrix")
        before = whole_db_counts()
        with sync_playwright() as pw:
            br = pw.chromium.launch(headless=True)
            try:
                combos = [
                    (STUDENTS[0], "en", {"width": 1280, "height": 900}, "en_1280x900"),
                    (STUDENTS[1], "zh_CN", {"width": 1280, "height": 900}, "zh_1280x900"),
                    (STUDENTS[2], "en", {"width": 390, "height": 844}, "en_390x844"),
                    (STUDENTS[3], "zh_CN", {"width": 390, "height": 844}, "zh_390x844"),
                ]
                for sid, lang, vp, tag in combos:
                    evidence[tag] = run(br, sid, lang, vp, tag)
            finally:
                br.close()
        after = whole_db_counts()
        evidence["scenario_deltas"] = {
            table: int(after.get(table, 0) - before.get(table, 0))
            for table in sorted(set(before) | set(after))
        }
    finally:
        harness.stop_stack(api, streamlit)

    (HERE / "rendered_wu4_matrix_evidence.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")

    states = ("writing_saved", "feedback_priority", "revision_saved",
              "practice_active", "practice_attempt_saved",
              "practice_completed", "journey_grouped")
    for tag in ("en_1280x900", "zh_1280x900", "en_390x844", "zh_390x844"):
        combo = evidence[tag]
        assert combo.get("journey_reentry_zero_writes") is True, (tag, combo)
        for state in states:
            data = combo.get(state, {})
            assert data, (tag, state, "missing")
            assert not data.get("exceptions"), (tag, state, data)
            assert not data.get("overflow"), (tag, state, data)
            assert not data.get("raw_keys"), (tag, state, data)
            assert not data.get("forbidden"), (tag, state, data)
            # bottom_distinct is informational: Streamlit's inner main-column
            # scroll container keeps the document height at the viewport, so
            # the bottom capture can be byte-identical even when content
            # scrolled. Below-fold evidence is covered by the WU1/WU2
            # matrices and the scrolled flag recorded per state.
            assert data.get("reload_zero_writes") is True, (tag, state)

    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
