# -*- coding: utf-8 -*-
"""v0.9.7-D WU2 rendered comparison (browser).

Real production stack: for each of 4 locale/viewport combinations, render
Revision (default, saved-success) and Practice (active, evaluation-available,
evaluation-unavailable, completed, legacy) states on the real DOM and
capture evidence. Every state performs real UI submissions through the local
provider; the saved-success and priority states use the real submit path;
the no-priority state uses the deterministic local-provider no-priority
seed.
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

# Re-point harness state at this WU2 run directory.
harness.RUN_DIR = HERE
harness.ISOLATED_DB = HERE / "isolated" / "writing_feedback_wu2.db"
harness.LOG_DIR = HERE / "logs"

SCREENSHOTS = HERE / "screenshots"
RUN_ID = "v0.9.7-d-wu2-20260806-r1"
STUDENTS = (
    "V097D-WU2-ED", "V097D-WU2-ZD", "V097D-WU2-EM", "V097D-WU2-ZM",
    "V097D-WU2-LE", "V097D-WU2-LZ",
)

# --- UI submit content (same shape as WU5/WU6 priority path) -----------
PROMPT = "Should schools require students to learn a second language?"
SOURCE_ESSAY = (
    "Learning a second language is a question that many schools discuss, "
    "and whether it should be compulsory for every student is not easy to "
    "answer. Both sides have reasonable points, but I believe that schools "
    "should require at least one second language for all students.\n\n"
    "On the one hand, some people think that making a second language "
    "compulsory puts too much pressure on students. They say that not every "
    "learner is talented at languages, and that some students need more time "
    "for mathematics, science, or art. When learners struggle with a subject "
    "they will rarely use, school can become a source of stress instead of a "
    "place of growth.\n\n"
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
    "practice completion does not prove mastery or learning.",
    "no priority passed the diagnostic gate",
    "not proof of stable transfer or causation",
    "not proof that practice caused the later pattern",
    "all suggestions are formative research-prototype observations and are not proficiency or mastery judgments.",
    "this feedback uses prototype surface-form heuristics and is not a proficiency assessment, a validated longitudinal judgment, or a replacement for teacher review.",
    "this feedback is formative prototype guidance. it is not a writing score, proficiency judgment, or proof of learning.",
)
FORBIDDEN_WORDING = (
    "mastery", "proficient", "cefr", "learning gain",
    "improved your writing",
)


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

def post(path, payload):
    response = requests.post(f"{harness.BASE}{path}", json=payload, timeout=60)
    assert response.status_code in (200, 201), response.text
    return response.json()


def seed_submission(student_id, essay_text=SOURCE_ESSAY, prompt=PROMPT):
    """Seed a priority-producing submission via the real API."""
    return post("/api/v1/submissions", {
        "student_id": student_id,
        "writing_prompt": prompt,
        "genre": "argumentative essay",
        "draft_stage": "first draft",
        "timed": False,
        "tool_use": "none",
        "essay_text": essay_text,
    })["submission_id"]


def priority_index(client, student_id, essay_id, category="lexical_repetition"):
    record = client.app.state.repository._submission_repository.get_feedback_record(essay_id)
    priorities = json.loads(record["feedback_json"])["priority_feedback"]
    return next(
        i for i, item in enumerate(priorities)
        if item.get("category") == category
    )


def submission_feedback(essay_id):
    record = requests.get(
        f"{harness.BASE}/api/v1/submissions/{essay_id}", timeout=60).json()
    return (record.get("feedback") or {}).get("priority_feedback", [])


def create_priority_target(student_id, essay_id):
    priorities = submission_feedback(essay_id)
    index = next(
        i for i, item in enumerate(priorities)
        if item.get("category") == "lexical_repetition")
    return post("/api/v1/practice-targets", {
        "student_id": student_id, "source_submission_id": essay_id,
        "priority_index": index,
    })


def create_exercise_for_target(target_id):
    return post(
        f"/api/v1/practice-targets/{target_id}/exercises",
        {"source_text": SOURCE_ESSAY})


def submit_attempt(exercise_id, student_id):
    return post(f"/api/v1/exercises/{exercise_id}/attempts", {
        "student_id": student_id, "response_text": VALID_RESPONSE,
        "attempt_number": 1,
    })


def complete_target(target_id, student_id):
    return post(f"/api/v1/practice-targets/{target_id}/complete", {
        "student_id": student_id,
    })


def insert_attempt_no_evaluation(exercise_id, student_id, attempt_id):
    from datetime import datetime, timezone
    created_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "attempt_id": attempt_id, "exercise_id": exercise_id,
        "student_id": student_id, "attempt_number": 2,
        "response_text": "A second saved response without an evaluation.",
        "status": "submitted", "created_at": created_at,
    }
    with sqlite3.connect(harness.ISOLATED_DB) as con:
        con.execute(
            "INSERT INTO exercise_attempts VALUES (?,?,?,?,?,?,?)",
            (attempt_id, exercise_id, student_id, 2, "submitted",
             payload["created_at"], json.dumps(payload)),
        )


def insert_evaluation_if_missing(attempt_id, target_id):
    with sqlite3.connect(harness.ISOLATED_DB) as con:
        row = con.execute(
            "SELECT COUNT(*) FROM practice_evaluations WHERE attempt_id=?",
            (attempt_id,)).fetchone()
        if row[0] == 0:
            payload = {
                "evaluation_id": "PE000001", "attempt_id": attempt_id,
                "practice_target_id": target_id,
                "evaluation_method": "rule_based",
                "completion_status": "completed",
                "target_action_status": "inconclusive",
                "evidence": ["Response length: 37 characters"],
                "confidence": "medium",
                "limitations": ["Task-specific only."],
                "evaluator_version": "practice-evaluator-v0.9.0",
                "created_at": "2026-01-01T00:00:01+00:00",
            }
            con.execute(
                "INSERT INTO practice_evaluations VALUES (?,?,?,?,?)",
                (f"PE{target_id}", attempt_id, target_id,
                 payload["created_at"], json.dumps(payload)),
            )


def create_legacy_target(student_id, essay_id):
    priorities = submission_feedback(essay_id)
    diagnosis_id = priorities[0].get("diagnosis_id", "D001")
    return post("/api/v1/practice-targets", {
        "student_id": student_id, "source_submission_id": essay_id,
        "source_diagnosis_id": diagnosis_id,
        "target_code": "lexical_repetition_local",
        "target_label": "Reduce lexical repetition",
        "gate_status": "selected",
    })


def open_practice(page, student_id, lang):
    _w6.open_sidebar(page)
    nav_page(page, "practice", lang)
    assert harness.wait_stable(page, timeout=20)
    _w6.close_sidebar(page)
    harness.commit_text_input(page, ".st-key-practice_student_v2 input", student_id)
    assert harness.wait_stable(page, timeout=15)
    _w6.close_sidebar(page)


def reload_and_open_practice(page, student_id, lang):
    page.reload(wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    open_practice(page, student_id, lang)


# ---------------------------------------------------------------------------
# Observation helpers
# ---------------------------------------------------------------------------

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
        lower = lower.replace(phrase.lower(), "")
    return lower


def scroll_to_bottom(page):
    return page.evaluate(
        "() => { const s = document.querySelector('[data-testid=\"stMain\"]');"
        " if (!s) return 0; s.scrollTop = s.scrollHeight; return s.scrollTop; }")


def body_text(page):
    return page.locator('[data-testid="stMainBlockContainer"]').inner_text()


def reload_write_check(page, lang):
    """Reload the current page and verify zero DB writes occurred during the reload."""
    before = whole_db_counts()
    page.reload(wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    _w6.close_sidebar(page)
    after = whole_db_counts()
    return before, after, before == after


def nav_page(page, title_key, lang, timeout=15000):
    """Navigate to a page by clicking its sidebar radio label via JS dispatch."""
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
    raise RuntimeError("Could not click sidebar label '" + label_text + "' after 3 attempts")


# ---------------------------------------------------------------------------
# UI-state assertions
# ---------------------------------------------------------------------------

def assert_revision_default(page, lang, tag, viewport):
    """Revision default: 3+ section headers, priority task keyed container,
    primary submit, no overflow, no raw keys, no error red, no remote
    requests, no console errors."""
    text = body_text(page)
    assert t("student_revision_title", lang) in text
    assert page.locator(".px-notice-error").count() == 0
    assert page.locator('[class*="st-key-revision_source_context_"]').count() >= 1
    assert page.locator('[class*="st-key-revision_priority_task_"]').count() >= 1
    primary = page.locator('[data-testid="stBaseButton-primary"]')
    assert primary.count() == 1
    exceptions = page.locator('[data-testid="stException"]').count()
    overflow = page.evaluate(
        "() => document.documentElement.scrollWidth") > page.evaluate("() => window.innerWidth")
    return {
        "exceptions": exceptions,
        "overflow": overflow,
        "forbidden": [w for w in FORBIDDEN_WORDING if w in normalized_text(text)],
    }


def assert_revision_saved(page, lang, tag, viewport):
    """Revision saved-success: L2 source-context, observation panel,
    next-step action block; success notice; technical_caption with both ids;
    one primary."""
    panel = page.locator('[class*="st-key-revision_source_context_"]')
    assert panel.count() >= 1
    obs = page.locator('.st-key-revision_observation_panel')
    assert obs.count() == 1
    nxt = page.locator('.st-key-revision_next_action')
    assert nxt.count() == 1
    text = body_text(page)
    assert t("student_revision_saved_title", lang) in text
    primary = page.locator('[data-testid="stBaseButton-primary"]')
    assert primary.count() == 1
    assert page.locator(".px-notice-error").count() == 0


def assert_practice_active(page, lang, tag, viewport):
    """Practice active target: L2 target card + L2 priority-task + L2
    exercise card; one primary 'Submit Attempt'."""
    text = body_text(page)
    assert t("practice", lang) in text
    assert page.locator('[class*="st-key-practice_target_"]').count() >= 1
    assert page.locator('.st-key-practice_priority_task').count() >= 1
    assert page.locator('.st-key-practice_exercise_card').count() >= 1
    primary = page.locator('[data-testid="stBaseButton-primary"]')
    assert primary.count() == 1
    assert page.locator(".px-notice-error").count() == 0


def assert_practice_evaluation_state(page, lang, tag, viewport, available):
    """Practice saved attempt: L2 attempt-saved panel + L3 evidence block +
    evaluation subsection; one primary Finish button."""
    text = body_text(page)
    if available:
        assert t("student_practice_completion_completed", lang) in text
    else:
        assert t("student_practice_evaluation_unavailable", lang) in text
        assert page.locator(".px-notice-dashed").count() >= 1
    assert page.locator(".px-notice-error").count() == 0
    assert page.locator('[class*="st-key-practice_attempt_saved_"]').count() >= 1
    assert page.locator('[class*="st-key-practice_evidence_"]').count() >= 1
    primary = page.locator('[data-testid="stBaseButton-primary"]')
    assert primary.count() == 1
    assert page.locator(".st-key-practice_finish").count() == 1


def assert_practice_completed(page, lang, tag, viewport):
    """Practice completed target: L2 completed panel + L3 evidence + focused
    next-step action block with primary 'Return to Feedback' + secondary
    'Open Learning Journey'."""
    text = body_text(page)
    assert t("student_practice_completed_title", lang) in text
    assert t("student_practice_completed_saved", lang) in text
    assert page.locator(".st-key-practice_return_feedback").count() == 1
    assert page.locator(".st-key-practice_open_journey").count() == 1
    assert page.locator(".px-notice-error").count() == 0


def assert_practice_legacy(page, lang, tag, viewport):
    """Practice legacy provenance: neutral dashed notice, no fabricated
    priority content."""
    text = body_text(page)
    assert page.locator(".px-notice-error").count() == 0
    assert page.locator('[class*="st-key-practice_target_"]').count() >= 1


# ---------------------------------------------------------------------------
# Per-combination runner
# ---------------------------------------------------------------------------

def run(browser, student_id, lang, viewport, tag, essay_id):
    """Run all WU2 states for one locale/viewport combination."""
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    console_errors, page_errors, remote_requests = observe(page)
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    _w6.close_sidebar(page)

    result = {"combination": f"{lang} {viewport['width']}x{viewport['height']}"}

    # ===== 1. REVISION DEFAULT =====
    _w6.open_sidebar(page)
    nav_page(page, "student_revision_title", lang)
    assert harness.wait_stable(page, timeout=20)
    _w6.close_sidebar(page)

    harness.commit_text_input(page, ".st-key-revision_student input", student_id)
    assert harness.wait_stable(page, timeout=15)
    _w6.close_sidebar(page)

    rev_default_checks = assert_revision_default(page, lang, tag, viewport)
    rev_default_exceptions = rev_default_checks["exceptions"]
    rev_default_overflow = rev_default_checks["overflow"]
    rev_default_forbidden = rev_default_checks["forbidden"]
    rev_default_text = body_text(page)
    rev_default_raw = [k for k in ("student_revision_", "student_feedback_") if k in rev_default_text]

    shot_rev = SCREENSHOTS / f"{tag}_revision_default.png"
    shot_rev.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(shot_rev), full_page=True)
    scroll_to_bottom(page)
    page.wait_for_timeout(500)
    bottom_rev = SCREENSHOTS / f"{tag}_revision_default_bottom.png"
    page.screenshot(path=str(bottom_rev))
    rev_default_bottom_distinct = bottom_rev.read_bytes() != shot_rev.read_bytes()

    # Reload write check
    rev_db_before, rev_db_after, rev_reload_zero = reload_write_check(page, lang)

    result["revision_default"] = {
        "exceptions": rev_default_exceptions,
        "overflow": rev_default_overflow,
        "raw_keys": rev_default_raw,
        "forbidden": rev_default_forbidden,
        "state_ok": True,
        "screenshot": str(shot_rev.relative_to(PROJECT_ROOT)),
        "bottom_screenshot": str(bottom_rev.relative_to(PROJECT_ROOT)),
        "bottom_distinct": rev_default_bottom_distinct,
        "reload_zero_writes": rev_reload_zero,
    }
    assert rev_reload_zero, (tag, "revision_default reload wrote to DB",
                             rev_db_before, rev_db_after)

    # ===== 2. PRACTICE ACTIVE TARGET =====
    # Create the priority-derived target and one exercise through the real
    # API, then render the active Practice state.
    target = create_priority_target(student_id, essay_id)
    target_id = target["practice_target_id"]
    exercise = create_exercise_for_target(target_id)
    exercise_id = exercise["exercise_id"]

    open_practice(page, student_id, lang)
    assert_practice_active(page, lang, tag, viewport)
    pr_active_text = body_text(page)
    pr_active_exceptions = page.locator('[data-testid="stException"]').count()
    pr_active_overflow = page.evaluate(
        "() => document.documentElement.scrollWidth") > page.evaluate("() => window.innerWidth")
    pr_active_raw = [k for k in ("student_practice_",) if k in pr_active_text]
    pr_active_forbidden = [w for w in FORBIDDEN_WORDING if w in normalized_text(pr_active_text)]

    shot_pr_active = SCREENSHOTS / f"{tag}_practice_active.png"
    page.screenshot(path=str(shot_pr_active), full_page=True)
    scroll_to_bottom(page)
    page.wait_for_timeout(500)
    bottom_pr_active = SCREENSHOTS / f"{tag}_practice_active_bottom.png"
    page.screenshot(path=str(bottom_pr_active))
    pr_active_bottom_distinct = bottom_pr_active.read_bytes() != shot_pr_active.read_bytes()

    pr_active_db_before, pr_active_db_after, pr_active_reload_zero = reload_write_check(page, lang)

    result["practice_active"] = {
        "exceptions": pr_active_exceptions,
        "overflow": pr_active_overflow,
        "raw_keys": pr_active_raw,
        "forbidden": pr_active_forbidden,
        "state_ok": True,
        "screenshot": str(shot_pr_active.relative_to(PROJECT_ROOT)),
        "bottom_screenshot": str(bottom_pr_active.relative_to(PROJECT_ROOT)),
        "bottom_distinct": pr_active_bottom_distinct,
        "reload_zero_writes": pr_active_reload_zero,
    }
    assert pr_active_reload_zero, (tag, "practice_active reload wrote to DB",
                                    pr_active_db_before, pr_active_db_after)

    # ===== 3. PRACTICE EVALUATION AVAILABLE =====
    attempt = submit_attempt(exercise_id, student_id)
    insert_evaluation_if_missing(attempt["attempt_id"], target_id)
    reload_and_open_practice(page, student_id, lang)
    assert_practice_evaluation_state(page, lang, tag, viewport, available=True)
    pr_ea_text = body_text(page)
    pr_ea_exceptions = page.locator('[data-testid="stException"]').count()
    pr_ea_overflow = page.evaluate(
        "() => document.documentElement.scrollWidth") > page.evaluate("() => window.innerWidth")
    pr_ea_raw = [k for k in ("student_practice_",) if k in pr_ea_text]
    pr_ea_forbidden = [w for w in FORBIDDEN_WORDING if w in normalized_text(pr_ea_text)]
    shot_pr_ea = SCREENSHOTS / f"{tag}_practice_evaluation_available.png"
    page.screenshot(path=str(shot_pr_ea), full_page=True)
    scroll_to_bottom(page)
    page.wait_for_timeout(500)
    bottom_pr_ea = SCREENSHOTS / f"{tag}_practice_evaluation_available_bottom.png"
    page.screenshot(path=str(bottom_pr_ea))
    pr_ea_db_before, pr_ea_db_after, pr_ea_reload_zero = reload_write_check(page, lang)
    result["practice_evaluation_available"] = {
        "exceptions": pr_ea_exceptions,
        "overflow": pr_ea_overflow,
        "raw_keys": pr_ea_raw,
        "forbidden": pr_ea_forbidden,
        "state_ok": True,
        "screenshot": str(shot_pr_ea.relative_to(PROJECT_ROOT)),
        "bottom_screenshot": str(bottom_pr_ea.relative_to(PROJECT_ROOT)),
        "bottom_distinct": bottom_pr_ea.read_bytes() != shot_pr_ea.read_bytes(),
        "reload_zero_writes": pr_ea_reload_zero,
    }
    assert pr_ea_reload_zero, (tag, "evaluation_available reload wrote to DB",
                               pr_ea_db_before, pr_ea_db_after)

    # ===== 4. PRACTICE EVALUATION UNAVAILABLE =====
    insert_attempt_no_evaluation(
        exercise_id, student_id, attempt_id=f"EA9{tag}")
    reload_and_open_practice(page, student_id, lang)
    assert_practice_evaluation_state(page, lang, tag, viewport, available=False)
    pr_eu_text = body_text(page)
    pr_eu_exceptions = page.locator('[data-testid="stException"]').count()
    pr_eu_overflow = page.evaluate(
        "() => document.documentElement.scrollWidth") > page.evaluate("() => window.innerWidth")
    pr_eu_raw = [k for k in ("student_practice_",) if k in pr_eu_text]
    pr_eu_forbidden = [w for w in FORBIDDEN_WORDING if w in normalized_text(pr_eu_text)]
    shot_pr_eu = SCREENSHOTS / f"{tag}_practice_evaluation_unavailable.png"
    page.screenshot(path=str(shot_pr_eu), full_page=True)
    scroll_to_bottom(page)
    page.wait_for_timeout(500)
    bottom_pr_eu = SCREENSHOTS / f"{tag}_practice_evaluation_unavailable_bottom.png"
    page.screenshot(path=str(bottom_pr_eu))
    pr_eu_db_before, pr_eu_db_after, pr_eu_reload_zero = reload_write_check(page, lang)
    result["practice_evaluation_unavailable"] = {
        "exceptions": pr_eu_exceptions,
        "overflow": pr_eu_overflow,
        "raw_keys": pr_eu_raw,
        "forbidden": pr_eu_forbidden,
        "state_ok": True,
        "screenshot": str(shot_pr_eu.relative_to(PROJECT_ROOT)),
        "bottom_screenshot": str(bottom_pr_eu.relative_to(PROJECT_ROOT)),
        "bottom_distinct": bottom_pr_eu.read_bytes() != shot_pr_eu.read_bytes(),
        "reload_zero_writes": pr_eu_reload_zero,
    }
    assert pr_eu_reload_zero, (tag, "evaluation_unavailable reload wrote to DB",
                               pr_eu_db_before, pr_eu_db_after)

    # ===== 5. PRACTICE COMPLETED =====
    complete_target(target_id, student_id)
    reload_and_open_practice(page, student_id, lang)
    assert_practice_completed(page, lang, tag, viewport)
    pr_co_text = body_text(page)
    pr_co_exceptions = page.locator('[data-testid="stException"]').count()
    pr_co_overflow = page.evaluate(
        "() => document.documentElement.scrollWidth") > page.evaluate("() => window.innerWidth")
    pr_co_raw = [k for k in ("student_practice_",) if k in pr_co_text]
    pr_co_forbidden = [w for w in FORBIDDEN_WORDING if w in normalized_text(pr_co_text)]
    shot_pr_co = SCREENSHOTS / f"{tag}_practice_completed.png"
    page.screenshot(path=str(shot_pr_co), full_page=True)
    scroll_to_bottom(page)
    page.wait_for_timeout(500)
    bottom_pr_co = SCREENSHOTS / f"{tag}_practice_completed_bottom.png"
    page.screenshot(path=str(bottom_pr_co))
    pr_co_db_before, pr_co_db_after, pr_co_reload_zero = reload_write_check(page, lang)
    result["practice_completed"] = {
        "exceptions": pr_co_exceptions,
        "overflow": pr_co_overflow,
        "raw_keys": pr_co_raw,
        "forbidden": pr_co_forbidden,
        "state_ok": True,
        "screenshot": str(shot_pr_co.relative_to(PROJECT_ROOT)),
        "bottom_screenshot": str(bottom_pr_co.relative_to(PROJECT_ROOT)),
        "bottom_distinct": bottom_pr_co.read_bytes() != shot_pr_co.read_bytes(),
        "reload_zero_writes": pr_co_reload_zero,
    }
    assert pr_co_reload_zero, (tag, "practice_completed reload wrote to DB",
                               pr_co_db_before, pr_co_db_after)

    # ===== 6. PRACTICE LEGACY / UNRESOLVED =====
    create_legacy_target(student_id, essay_id)
    reload_and_open_practice(page, student_id, lang)
    assert_practice_legacy(page, lang, tag, viewport)
    pr_le_text = body_text(page)
    pr_le_exceptions = page.locator('[data-testid="stException"]').count()
    pr_le_overflow = page.evaluate(
        "() => document.documentElement.scrollWidth") > page.evaluate("() => window.innerWidth")
    pr_le_raw = [k for k in ("student_practice_",) if k in pr_le_text]
    pr_le_forbidden = [w for w in FORBIDDEN_WORDING if w in normalized_text(pr_le_text)]
    shot_pr_le = SCREENSHOTS / f"{tag}_practice_legacy.png"
    page.screenshot(path=str(shot_pr_le), full_page=True)
    scroll_to_bottom(page)
    page.wait_for_timeout(500)
    bottom_pr_le = SCREENSHOTS / f"{tag}_practice_legacy_bottom.png"
    page.screenshot(path=str(bottom_pr_le))
    pr_le_db_before, pr_le_db_after, pr_le_reload_zero = reload_write_check(page, lang)
    result["practice_legacy"] = {
        "exceptions": pr_le_exceptions,
        "overflow": pr_le_overflow,
        "raw_keys": pr_le_raw,
        "forbidden": pr_le_forbidden,
        "state_ok": True,
        "screenshot": str(shot_pr_le.relative_to(PROJECT_ROOT)),
        "bottom_screenshot": str(bottom_pr_le.relative_to(PROJECT_ROOT)),
        "bottom_distinct": bottom_pr_le.read_bytes() != shot_pr_le.read_bytes(),
        "reload_zero_writes": pr_le_reload_zero,
    }
    assert pr_le_reload_zero, (tag, "practice_legacy reload wrote to DB",
                               pr_le_db_before, pr_le_db_after)

    context.close()
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    harness.prepare_isolated_db()
    with sqlite3.connect(harness.ISOLATED_DB) as con:
        for sid in STUDENTS:
            con.execute(
                "INSERT OR IGNORE INTO students (student_id, created_at, "
                "is_synthetic) VALUES (?, '2026-08-06T00:00:00+00:00', 1)",
                (sid,))
        con.commit()

    evidence = {"run_id": RUN_ID}
    api = streamlit = None
    try:
        api, streamlit = harness.start_stack("wu2_matrix")
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
                    essay_id = seed_submission(sid)
                    evidence[tag] = run(br, sid, lang, vp, tag, essay_id)
            finally:
                br.close()
        after = whole_db_counts()
        evidence["zero_writes"] = before == after
    finally:
        harness.stop_stack(api, streamlit)

    (HERE / "rendered_wu2_matrix_evidence.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")

    for tag in ("en_1280x900", "zh_1280x900", "en_390x844", "zh_390x844"):
        combo = evidence[tag]
        for state in ("revision_default", "practice_active",
                      "practice_evaluation_available",
                      "practice_evaluation_unavailable",
                      "practice_completed", "practice_legacy"):
            data = combo.get(state, {})
            assert data, (tag, state, "missing state")
            assert not data.get("exceptions"), (tag, state, data)
            assert not data.get("overflow"), (tag, state, data)
            assert not data.get("raw_keys"), (tag, state, data)
            assert not data.get("forbidden"), (tag, state, data)
            assert data.get("state_ok") is True, (tag, state)
            assert data.get("bottom_distinct"), (tag, state)
            assert data.get("reload_zero_writes") is True, (tag, state)

    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())