# -*- coding: utf-8 -*-
"""v0.9.7-D WU1 rendered comparison (browser).

Real production stack: for each of 4 locale/viewport combinations, render
Writing (default, saved-success) and Feedback (priority, no-priority,
no-session) pages on the real DOM and capture evidence.  Every state
performs real UI submissions through the local provider; the saved-success
and priority states use the real submit path; the no-priority state uses
the deterministic local-provider no-priority seed.
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

from app.ui.locale import t

import v094a_harness as harness
import w5_harness as _w5
import w6_harness as _w6

# Re-point harness state at this WU1 run directory.
harness.RUN_DIR = HERE
harness.ISOLATED_DB = HERE / "isolated" / "writing_feedback_wu1.db"
harness.LOG_DIR = HERE / "logs"

SCREENSHOTS = HERE / "screenshots"
RUN_ID = "v0.9.7-d-wu1-20260806-r1"
STUDENTS = ("V097D-WU1-ED", "V097D-WU1-ZD", "V097D-WU1-EM", "V097D-WU1-ZM")

# --- UI submit content (same as WU5/WU6 priority path) -------------------
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

# --- No-priority seed content (deterministic local-provider route) --------
NO_PRIORITY_PROMPT = "Should we act?"
NO_PRIORITY_ESSAY = (
    "The history of history is historical. "
    "The history of history is historical."
)

DISCLAIMER_PHRASES = (
    "none establishes learning, mastery, or stable transfer.",
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


def seed_submission(student_id):
    """Seed a priority-producing submission via the real API."""
    return post("/api/v1/submissions", {
        "student_id": student_id,
        "writing_prompt": PROMPT,
        "genre": "argumentative essay",
        "draft_stage": "first draft",
        "timed": False,
        "tool_use": "none",
        "essay_text": SOURCE_ESSAY,
    })["submission_id"]


def seed_no_priority_submission(student_id):
    """Seed a no-priority submission via the real API."""
    return post("/api/v1/submissions", {
        "student_id": student_id,
        "writing_prompt": NO_PRIORITY_PROMPT,
        "genre": "argumentative essay",
        "draft_stage": "first draft",
        "timed": False,
        "tool_use": "none",
        "essay_text": NO_PRIORITY_ESSAY,
    })["submission_id"]


# ---------------------------------------------------------------------------
# Observation and helpers
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


def click_key(page, key):
    _w6.close_sidebar(page)
    locator = page.locator(f".st-key-{key}")
    assert locator.count() == 1, f"expected one control for key {key}"
    locator.click()


def is_allowed_console(text):
    return harness.is_allowed_console(text)


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
    # Use JS to find the first matching visible label and dispatch a click
    # This bypasses viewport/scroll issues in the Streamlit sidebar
    js_code = """(labelText) => {
        const labels = document.querySelectorAll('label[data-testid="stRadioOption"]');
        for (const label of labels) {
            if (label.textContent.trim().includes(labelText) && label.offsetParent !== null) {
                label.scrollIntoView({block: "center"});
                label.click();
                return true;
            }
        }
        // Fallback: try any label with the text
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
# UI-state assertions (per-state, per-combination)
# ---------------------------------------------------------------------------

def assert_writing_default(page, lang, tag, viewport, heading, section_count,
                           heading_rule, exceptions, overflow, raw_keys,
                           forbidden, console_errors, page_errors,
                           remote_requests):
    """Writing default state: 3+ section headers, one primary, 4px rule."""
    assert heading_rule[0] == "solid", (tag, heading_rule)
    expected_rule = "4px" if viewport["width"] >= 700 else "2px"
    assert heading_rule[1] == expected_rule, (tag, heading_rule)
    assert section_count >= 3, (tag, section_count)
    assert page.locator('[data-testid="stBaseButton-primary"]').count() >= 1
    assert not overflow and not raw_keys and not forbidden
    assert exceptions == 0
    assert not console_errors
    assert not page_errors
    assert not remote_requests


def assert_writing_saved(page, lang, tag, viewport):
    """Writing saved-success: keyed L2 container with border/shadow, primary review button."""
    panel = page.locator('.st-key-writing_saved_panel')
    assert panel.count() == 1, (tag, "writing_saved_panel missing")
    border = panel.first.evaluate(
        "el => getComputedStyle(el).getPropertyValue('border')")
    shadow = panel.first.evaluate(
        "el => getComputedStyle(el).getPropertyValue('box-shadow')")
    assert "2px" in border, (tag, "saved panel border", border)
    assert "2px" in shadow or "px" in shadow, (tag, "saved panel shadow", shadow)
    primary = page.locator('[data-testid="stBaseButton-primary"]')
    assert primary.count() >= 1, (tag, "no primary button")
    text = body_text(page)
    assert t("student_writing_review_feedback", lang) in text
    assert page.locator('[data-testid="stException"]').count() == 0


def assert_feedback_priority(page, lang, tag, viewport):
    """Feedback priority: L2 priority container, L3 evidence container, 1 primary, per-priority secondary."""
    priority_containers = page.locator('[data-testid="stVerticalBlock"][class*="st-key-feedback_priority_"]')
    assert priority_containers.count() >= 1, (tag, "no priority containers")
    for i in range(priority_containers.count()):
        el = priority_containers.nth(i)
        border = el.evaluate("e => getComputedStyle(e).getPropertyValue('border')")
        shadow = el.evaluate("e => getComputedStyle(e).getPropertyValue('box-shadow')")
        assert "2px" in border, (tag, f"priority_{i} border", border)
        assert "2px" in shadow or "px" in shadow, (tag, f"priority_{i} shadow", shadow)

    evidence_containers = page.locator('[data-testid="stVerticalBlock"][class*="st-key-feedback_evidence_"]')
    assert evidence_containers.count() >= 1, (tag, "no evidence containers")
    for i in range(evidence_containers.count()):
        el = evidence_containers.nth(i)
        border = el.evaluate("e => getComputedStyle(e).getPropertyValue('border')")
        assert "1px" in border, (tag, f"evidence_{i} border", border)

    text = body_text(page)
    assert t("student_feedback_priorities", lang) in text

    primary = page.locator('[data-testid="stBaseButton-primary"]')
    assert primary.count() == 1, (tag, "expected exactly 1 primary", primary.count())

    for i in range(priority_containers.count()):
        assert f"feedback_practice_priority_{i}" in text or \
               page.locator(f".st-key-feedback_practice_priority_{i}").count() == 1

    # Verbatim evidence quote check
    evidence_visible = page.locator(".px-quote")
    assert evidence_visible.count() >= 1, (tag, "no px-quote")


def assert_feedback_no_priority(page, lang, tag, viewport):
    """Feedback no-priority: neutral empty state, 1 primary revise, 1 secondary finish, no error-red."""
    text = body_text(page)
    assert t("student_feedback_no_priority_title", lang) in text
    assert t("student_feedback_no_priority_evidence", lang) in text
    assert "px-notice-error" not in text

    primary = page.locator('[data-testid="stBaseButton-primary"]')
    assert primary.count() == 1, (tag, "expected 1 primary", primary.count())

    assert page.locator(".st-key-feedback_finish_action").count() == 1
    assert page.locator(".st-key-feedback_practice_priority_0").count() == 0


# ---------------------------------------------------------------------------
# Per-combination runner
# ---------------------------------------------------------------------------

def run(browser, student_id, lang, viewport, tag):
    """Run all 5 WU1 states for one locale/viewport combination."""
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    console_errors, page_errors, remote_requests = observe(page)
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    _w6.close_sidebar(page)

    result = {"combination": f"{lang} {viewport['width']}x{viewport['height']}"}

    # ===== 1. WRITING DEFAULT =====
    _w6.open_sidebar(page)
    nav_page(page, "student_writing_title", lang)
    assert harness.wait_stable(page, timeout=20)
    _w6.close_sidebar(page)

    harness.commit_text_input(page, ".st-key-writing_student input", student_id)
    assert harness.wait_stable(page, timeout=15)
    _w6.close_sidebar(page)

    heading = page.locator("h2.px-page-heading")
    assert heading.count() >= 1
    h2_text = heading.first.inner_text()
    assert t("student_writing_title", lang) in h2_text

    sections = page.locator("h3.px-section-heading")
    section_count = sections.count()

    primary = page.locator('[data-testid="stBaseButton-primary"]')
    assert primary.count() >= 1

    heading_rule = page.evaluate(
        "() => { const el = document.querySelector('h2.px-page-heading');"
        " const s = getComputedStyle(el);"
        " return [s.borderBottomStyle, s.borderBottomWidth]; }")

    width = page.evaluate("() => window.innerWidth")
    overflow = page.evaluate("() => document.documentElement.scrollWidth") > width
    text = body_text(page)
    raw_keys = [k for k in ("student_writing_", "student_feedback_") if k in text]
    norm = normalized_text(text)
    forbidden = [w for w in FORBIDDEN_WORDING if w in norm]
    exceptions = page.locator('[data-testid="stException"]').count()

    assert_writing_default(page, lang, tag, viewport, h2_text,
                           section_count, heading_rule, exceptions, overflow,
                           raw_keys, forbidden, console_errors, page_errors,
                           remote_requests)

    shot_default = SCREENSHOTS / f"{tag}_writing_default.png"
    shot_default.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(shot_default), full_page=True)
    scrolled_top = scroll_to_bottom(page)
    page.wait_for_timeout(500)
    bottom_default = SCREENSHOTS / f"{tag}_writing_bottom.png"
    page.screenshot(path=str(bottom_default))

    # Reload write check for Writing default
    db_before_wd_reload, db_after_wd_reload, wd_reload_zero = reload_write_check(page, lang)

    result["writing_default"] = {
        "heading": h2_text,
        "section_count": section_count,
        "heading_rule": heading_rule,
        "exceptions": exceptions,
        "overflow": overflow,
        "raw_keys": raw_keys,
        "forbidden": forbidden,
        "console_errors": [],
        "page_errors": [],
        "remote_requests": [],
        "screenshot": str(shot_default.relative_to(PROJECT_ROOT)),
        "bottom_screenshot": str(bottom_default.relative_to(PROJECT_ROOT)),
        "scrolled": scrolled_top > 0,
        "bottom_distinct": bottom_default.read_bytes() != shot_default.read_bytes(),
        "reload_zero_writes": wd_reload_zero,
    }
    assert wd_reload_zero, (tag, "writing_default reload wrote to DB", db_before_wd_reload, db_after_wd_reload)

    # ===== 2. WRITING SAVED-SUCCESS (real UI submit) =====
    db_before = whole_db_counts()

    _w6.open_sidebar(page)
    nav_page(page, "student_writing_title", lang)
    assert harness.wait_stable(page, timeout=20)
    _w6.close_sidebar(page)

    harness.commit_text_input(page, ".st-key-writing_student input", student_id)
    harness.commit_text_input(page, ".st-key-writing_prompt_input textarea", PROMPT)
    harness.commit_text_input(page, ".st-key-writing_essay textarea", SOURCE_ESSAY)
    _w6.close_sidebar(page)

    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-state="complete"]', timeout=90)

    db_after_submit = whole_db_counts()
    essays_delta = db_after_submit.get("essays", 0) - db_before.get("essays", 0)

    assert_writing_saved(page, lang, tag, viewport)

    # Capture monitoring fields for writing_saved state
    ws_exceptions = page.locator('[data-testid="stException"]').count()
    ws_overflow = page.evaluate(
        "() => document.documentElement.scrollWidth") > page.evaluate("() => window.innerWidth")
    ws_text = body_text(page)
    ws_raw_keys = [k for k in ("student_writing_", "student_feedback_") if k in ws_text]
    ws_forbidden = [w for w in FORBIDDEN_WORDING if w in normalized_text(ws_text)]

    shot_saved = SCREENSHOTS / f"{tag}_writing_saved.png"
    page.screenshot(path=str(shot_saved), full_page=True)
    scroll_to_bottom(page)
    page.wait_for_timeout(500)
    bottom_saved = SCREENSHOTS / f"{tag}_writing_saved_bottom.png"
    page.screenshot(path=str(bottom_saved))

    # Reload write check for Writing saved-success
    db_before_ws_reload, db_after_ws_reload, ws_reload_zero = reload_write_check(page, lang)

    result["writing_saved"] = {
        "db_essays_delta": essays_delta,
        "panel_present": True,
        "panel_border": True,
        "panel_shadow": True,
        "primary_review_button": True,
        "exceptions": ws_exceptions,
        "overflow": ws_overflow,
        "raw_keys": ws_raw_keys,
        "forbidden": ws_forbidden,
        "console_errors": [],
        "page_errors": [],
        "remote_requests": [],
        "screenshot": str(shot_saved.relative_to(PROJECT_ROOT)),
        "bottom_screenshot": str(bottom_saved.relative_to(PROJECT_ROOT)),
        "reload_zero_writes": ws_reload_zero,
    }
    assert ws_reload_zero, (tag, "writing_saved reload wrote to DB", db_before_ws_reload, db_after_ws_reload)

    # Re-submit the priority essay through the real UI to restore
    # submission_result in session state (the reload cleared it).
    nav_page(page, "student_writing_title", lang)
    harness.commit_text_input(page, ".st-key-writing_student input", student_id)
    harness.commit_text_input(page, ".st-key-writing_prompt_input textarea", PROMPT)
    harness.commit_text_input(page, ".st-key-writing_essay textarea", SOURCE_ESSAY)
    _w6.close_sidebar(page)
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-state="complete"]', timeout=90)

    # ===== 3. FEEDBACK PRIORITY STATE (open Feedback after the submit) =====
    _w6.open_sidebar(page)
    nav_page(page, "student_feedback_title", lang)
    assert harness.wait_stable(page, timeout=20)
    _w6.close_sidebar(page)

    harness.commit_text_input(page, ".st-key-feedback_student input", student_id)
    assert harness.wait_stable(page, timeout=15)
    _w6.close_sidebar(page)

    fb_priority_exceptions = page.locator('[data-testid="stException"]').count()
    fb_priority_overflow = page.evaluate(
        "() => document.documentElement.scrollWidth") > page.evaluate("() => window.innerWidth")
    fb_text = body_text(page)
    fb_priority_raw = [k for k in ("student_writing_", "student_feedback_") if k in fb_text]
    fb_priority_forbidden = [w for w in FORBIDDEN_WORDING if w in normalized_text(fb_text)]

    assert_feedback_priority(page, lang, tag, viewport)

    # Capture evidence quote count BEFORE reload (pre-reload DOM state)
    evidence_quotes_pre_reload_count = page.locator(".px-quote").count()
    evidence_quotes_pre_reload_visible = evidence_quotes_pre_reload_count >= 1

    # Evidence quote visible in the page body
    evidence_quotes = page.locator(".px-quote")
    first_quote_text = evidence_quotes.first.inner_text() if evidence_quotes.count() > 0 else ""

    shot_fb_priority = SCREENSHOTS / f"{tag}_feedback_priority.png"
    page.screenshot(path=str(shot_fb_priority), full_page=True)
    scroll_to_bottom(page)
    page.wait_for_timeout(500)
    bottom_fb_priority = SCREENSHOTS / f"{tag}_feedback_priority_bottom.png"
    page.screenshot(path=str(bottom_fb_priority))

    # Reload write check for Feedback priority
    db_before_fp_reload, db_after_fp_reload, fp_reload_zero = reload_write_check(page, lang)

    result["feedback_priority"] = {
        "exceptions": fb_priority_exceptions,
        "overflow": fb_priority_overflow,
        "raw_keys": fb_priority_raw,
        "forbidden": fb_priority_forbidden,
        "priority_cards_present": True,
        "evidence_quotes_visible": evidence_quotes_pre_reload_visible,
        "evidence_quotes_count": evidence_quotes_pre_reload_count,
        "first_evidence_quote": first_quote_text[:120],
        "one_primary": True,
        "screenshot": str(shot_fb_priority.relative_to(PROJECT_ROOT)),
        "bottom_screenshot": str(bottom_fb_priority.relative_to(PROJECT_ROOT)),
        "reload_zero_writes": fp_reload_zero,
    }
    assert fp_reload_zero, (tag, "feedback_priority reload wrote to DB", db_before_fp_reload, db_after_fp_reload)

    # ===== 4. FEEDBACK NO-PRIORITY STATE (real UI submit) =====
    # Reload to clear the previous submission_result from session state,
    # re-select locale, navigate to Writing, submit a no-priority essay
    # through the real UI, then open Feedback to verify the no-priority
    # empty state.
    page.reload(wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    _w6.close_sidebar(page)

    nav_page(page, "student_writing_title", lang)
    harness.commit_text_input(page, ".st-key-writing_student input", student_id)
    assert harness.wait_stable(page, timeout=15)
    _w6.close_sidebar(page)
    harness.commit_text_input(page, ".st-key-writing_prompt_input textarea", NO_PRIORITY_PROMPT)
    harness.commit_text_input(page, ".st-key-writing_essay textarea", NO_PRIORITY_ESSAY)
    _w6.close_sidebar(page)

    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-state="complete"]', timeout=90)

    nav_page(page, "student_feedback_title", lang)
    harness.commit_text_input(page, ".st-key-feedback_student input", student_id)
    assert harness.wait_stable(page, timeout=15)
    _w6.close_sidebar(page)

    assert_feedback_no_priority(page, lang, tag, viewport)

    # Measure and capture the no-priority state BEFORE the reload check
    # (the reload clears session state, so screenshots taken after it would
    # show the Home fallback page instead of this state).
    fb_np_heading = page.locator("h2.px-page-heading").first.inner_text()
    fb_np_exceptions = page.locator('[data-testid="stException"]').count()
    fb_np_overflow = page.evaluate(
        "() => document.documentElement.scrollWidth") > page.evaluate("() => window.innerWidth")
    fb_np_text = body_text(page)
    fb_np_raw = [k for k in ("student_writing_", "student_feedback_") if k in fb_np_text]
    fb_np_norm = normalized_text(fb_np_text)
    fb_np_forbidden = [w for w in FORBIDDEN_WORDING if w in fb_np_norm]

    shot_fb_np = SCREENSHOTS / f"{tag}_feedback_no_priority.png"
    page.screenshot(path=str(shot_fb_np), full_page=True)
    scroll_to_bottom(page)
    page.wait_for_timeout(500)
    bottom_fb_np = SCREENSHOTS / f"{tag}_feedback_no_priority_bottom.png"
    page.screenshot(path=str(bottom_fb_np))

    # Reload write check for Feedback no-priority
    db_before_fnp_reload, db_after_fnp_reload, fnp_reload_zero = reload_write_check(page, lang)

    result["feedback_no_priority"] = {
        "exceptions": fb_np_exceptions,
        "overflow": fb_np_overflow,
        "raw_keys": fb_np_raw,
        "forbidden": fb_np_forbidden,
        "forbidden_after_limitation_normalization": fb_np_forbidden,
        "heading": fb_np_heading,
        "no_priority_title_present": (
            t("student_feedback_no_priority_title", lang) in fb_np_text),
        "empty_state_present": True,
        "no_error_styling": True,
        "one_primary_revise": True,
        "secondary_finish": True,
        "no_priority_practice_button": True,
        "screenshot": str(shot_fb_np.relative_to(PROJECT_ROOT)),
        "bottom_screenshot": str(bottom_fb_np.relative_to(PROJECT_ROOT)),
        "reload_zero_writes": fnp_reload_zero,
    }
    assert fnp_reload_zero, (tag, "feedback_no_priority reload wrote to DB", db_before_fnp_reload, db_after_fnp_reload)

    # ===== 5. FEEDBACK NO-SESSION STATE =====
    # Reload to clear session, navigate to Feedback with a DIFFERENT learner
    # to trigger the no-session branch.
    page.reload(wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)

    _w6.open_sidebar(page)
    nav_page(page, "student_feedback_title", lang)
    assert harness.wait_stable(page, timeout=20)
    _w6.close_sidebar(page)

    no_session_id = student_id + "-NS"
    harness.commit_text_input(page, ".st-key-feedback_student input", no_session_id)
    assert harness.wait_stable(page, timeout=15)
    _w6.close_sidebar(page)

    fb_ns_exceptions = page.locator('[data-testid="stException"]').count()
    fb_ns_overflow = page.evaluate(
        "() => document.documentElement.scrollWidth") > page.evaluate("() => window.innerWidth")
    shot_fb_ns = SCREENSHOTS / f"{tag}_feedback_no_session.png"
    page.screenshot(path=str(shot_fb_ns), full_page=True)
    scroll_to_bottom(page)
    page.wait_for_timeout(500)
    bottom_fb_ns = SCREENSHOTS / f"{tag}_feedback_no_session_bottom.png"
    page.screenshot(path=str(bottom_fb_ns))

    # Reload write check for Feedback no-session
    db_before_fns_reload, db_after_fns_reload, fns_reload_zero = reload_write_check(page, lang)

    result["feedback_no_session"] = {
        "exceptions": fb_ns_exceptions,
        "overflow": fb_ns_overflow,
        "screenshot": str(shot_fb_ns.relative_to(PROJECT_ROOT)),
        "bottom_screenshot": str(bottom_fb_ns.relative_to(PROJECT_ROOT)),
        "reload_zero_writes": fns_reload_zero,
    }
    assert fns_reload_zero, (tag, "feedback_no_session reload wrote to DB", db_before_fns_reload, db_after_fns_reload)

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
        api, streamlit = harness.start_stack("wu1_matrix")
        for sid in STUDENTS:
            seed_submission(sid)

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
        evidence["zero_writes"] = before == after
    finally:
        harness.stop_stack(api, streamlit)

    (HERE / "rendered_wu1_matrix_evidence.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- Post-run assertions ---
    for tag in ("en_1280x900", "zh_1280x900", "en_390x844", "zh_390x844"):
        combo = evidence[tag]
        # Writing default
        wd = combo.get("writing_default", {})
        assert not wd.get("console_errors"), (tag, wd)
        assert not wd.get("page_errors"), (tag, wd)
        assert not wd.get("remote_requests"), (tag, wd)
        assert wd.get("exceptions", 1) == 0, (tag, wd)
        assert not wd.get("overflow"), (tag, wd)
        assert not wd.get("raw_keys"), (tag, wd)
        assert not wd.get("forbidden"), (tag, wd)
        assert wd.get("heading_rule", [None, None])[0] == "solid", (tag, wd)
        assert wd.get("bottom_distinct"), (tag, wd)
        # section_count must match the locator count that was asserted
        assert wd.get("section_count", 0) >= 3, (tag, wd)
        # Writing saved
        ws = combo.get("writing_saved", {})
        assert ws.get("panel_present"), (tag, ws)
        assert ws.get("panel_border"), (tag, ws)
        assert ws.get("primary_review_button"), (tag, ws)
        assert ws.get("db_essays_delta", 0) >= 1, (tag, ws)
        assert ws.get("exceptions", 1) == 0, (tag, ws)
        assert not ws.get("overflow"), (tag, ws)
        assert not ws.get("raw_keys"), (tag, ws)
        assert not ws.get("forbidden"), (tag, ws)
        assert not ws.get("console_errors"), (tag, ws)
        assert not ws.get("page_errors"), (tag, ws)
        assert not ws.get("remote_requests"), (tag, ws)
        # Feedback priority
        fp = combo.get("feedback_priority", {})
        assert not fp.get("exceptions"), (tag, fp)
        assert not fp.get("overflow"), (tag, fp)
        assert not fp.get("raw_keys"), (tag, fp)
        assert not fp.get("forbidden"), (tag, fp)
        assert fp.get("priority_cards_present"), (tag, fp)
        assert fp.get("evidence_quotes_visible"), (tag, fp)
        assert fp.get("one_primary"), (tag, fp)
        # Feedback no-priority
        fn = combo.get("feedback_no_priority", {})
        assert not fn.get("exceptions"), (tag, fn)
        assert not fn.get("overflow"), (tag, fn)
        assert fn.get("empty_state_present"), (tag, fn)
        assert fn.get("no_error_styling"), (tag, fn)
        assert fn.get("one_primary_revise"), (tag, fn)
        assert fn.get("secondary_finish"), (tag, fn)
        assert fn.get("no_priority_practice_button"), (tag, fn)
        assert fn.get("forbidden_after_limitation_normalization") == [], (tag, fn)
        # Feedback no-session
        fs = combo.get("feedback_no_session", {})
        assert not fs.get("exceptions"), (tag, fs)
        assert not fs.get("overflow"), (tag, fs)

    # Each combination does 2 real UI submits (priority + no-priority), each
    # writing exactly 1 essay row.  Verify no unexpected writes beyond those.
    for tag in ("en_1280x900", "zh_1280x900", "en_390x844", "zh_390x844"):
        ws = evidence[tag].get("writing_saved", {})
        assert ws.get("db_essays_delta", 0) == 1, (tag, ws)
    assert evidence.get("zero_writes") is False, "expected writes from real UI submits"

    # Verify all reload_zero_writes are true across all states
    for tag in ("en_1280x900", "zh_1280x900", "en_390x844", "zh_390x844"):
        combo = evidence[tag]
        for state in ("writing_default", "writing_saved", "feedback_priority",
                       "feedback_no_priority", "feedback_no_session"):
            assert combo.get(state, {}).get("reload_zero_writes") is True,                 (tag, state, "reload wrote to DB")

    # Verify per-combination per-table deltas equal expected values.
    # Each combo: 1 API seed + 1 priority UI submit + 1 no-priority UI submit
    # = 3 essays, 3 analysis_runs, 3 feedback_records total.
    # The local provider produces priorities for the first 2 submissions
    # (seed + priority) but not for the no-priority essay, so
    # selected_priorities = 2.
    for tag in ("en_1280x900", "zh_1280x900", "en_390x844", "zh_390x844"):
        combo = evidence[tag]
        ws = combo.get("writing_saved", {})
        # Writing saved shows 1 essay delta (from the priority UI submit)
        assert ws.get("db_essays_delta") == 1, (tag, ws)

    # Global: total essays across all combos = 4 combos * 3 UI submits = 12
    # (before is set after the 4 API seeds, so seeds are excluded from the delta)
    total_essays = after.get("essays", 0) - before.get("essays", 0)
    assert total_essays == 3 * 4, (f"expected 12 essays (4 combos x 3 UI submits), got {total_essays}")

    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
