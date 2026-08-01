"""Focused v0.9.4-B Feedback verification with isolated persistence."""

from __future__ import annotations

import json
import pathlib
import sqlite3
import sys

from playwright.sync_api import sync_playwright


HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

import v094b_harness as harness  # noqa: E402
from app.ui.locale import t  # noqa: E402


SCREENSHOTS = HERE / "screenshots"
PROMPT = "How can writers make an argument clear and specific?"
PRIORITY_ESSAY = (
    "Writers repeat vague claims, repeat vague claims, and repeat vague claims in one short passage. "
    "Specific evidence can clarify a reason because readers can inspect the support. " * 5
)
ZERO_PRIORITY_ESSAY = (
    "A clear school policy can reduce unnecessary waste while keeping activities practical. "
    "Students can use refill stations and sort reusable materials before events. "
    "Teachers can explain why each choice matters and invite suggestions. "
    "These steps offer a practical starting point for the school community."
)


def table_counts() -> dict[str, int]:
    with sqlite3.connect(harness.ISOLATED_DB) as connection:
        tables = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()]
        return {
            table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            for table in tables
        }


def latest_feedback(student_id: str) -> dict:
    with sqlite3.connect(harness.ISOLATED_DB) as connection:
        row = connection.execute(
            "SELECT f.feedback_json FROM feedback_records f "
            "JOIN essays e ON e.essay_id=f.essay_id WHERE e.student_id=? "
            "ORDER BY e.essay_id DESC LIMIT 1",
            (student_id,),
        ).fetchone()
    assert row is not None
    return json.loads(row[0])


def observe_errors(page):
    console_errors: list[str] = []
    page_errors: list[str] = []
    page.on(
        "console",
        lambda message: console_errors.append(message.text) if message.type == "error" else None,
    )
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    return console_errors, page_errors


def open_page(page, title_key: str, lang: str) -> None:
    assert harness.select_page(page, t(title_key, lang), t(title_key, lang))
    harness.close_sidebar(page)


def submit_in_session(page, lang: str, student_id: str, essay: str) -> None:
    open_page(page, "student_writing_title", lang)
    harness.commit_text_input(page, '.st-key-writing_student input', student_id)
    harness.commit_text_input(page, '.st-key-writing_prompt_input textarea', PROMPT)
    harness.commit_text_input(page, '.st-key-writing_essay textarea', essay)
    harness.close_sidebar(page)
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-state="complete"]', timeout=60)
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-testid="px-student-page"]')
    assert t("student_feedback_title", lang) in page.locator("h2").all_inner_texts()


def page_health(page, raw_keys: tuple[str, ...]) -> dict[str, object]:
    width = page.evaluate("() => window.innerWidth")
    text = page.locator("body").inner_text()
    main = page.locator('[data-testid="stMainBlockContainer"]').first
    return {
        "exceptions": page.locator('[data-testid="stException"]').count(),
        "overflow": page.evaluate("() => document.documentElement.scrollWidth") > width,
        "raw_keys": [key for key in raw_keys if key in text],
        "main_max_width": main.evaluate("el => getComputedStyle(el).maxWidth"),
    }


def feedback_result_context(
    browser, lang: str, viewport: tuple[int, int], student_id: str, essay: str, expect_priority: bool
) -> tuple[dict, list[str], list[str]]:
    context = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
    page = context.new_page()
    console_errors, page_errors = observe_errors(page)
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)

    submit_in_session(page, lang, student_id, essay)
    before_feedback = table_counts()
    feedback = latest_feedback(student_id)
    priority_items = feedback.get("priority_feedback", [])
    assert bool(priority_items) is expect_priority

    priority_cards = page.locator('[data-testid="px-feedback-priority"]').count()
    empty_states = page.locator('[data-testid="px-empty-state"]').count()
    evidence_quotes = page.locator('.px-quote').count()
    limitation = page.locator('.px-notice-limitation[data-testid="px-notice"]').count()
    primary = page.locator('[data-testid="stBaseButton-primary"]')
    main_text = page.locator('[data-testid="stMainBlockContainer"]').inner_text()
    expected_action = t(
        "student_feedback_open_practice" if expect_priority else "student_feedback_open_writing",
        lang,
    )
    assert primary.count() == 1 and expected_action in primary.first.inner_text()
    assert priority_cards == (len(priority_items[:2]) if expect_priority else 0)
    assert empty_states == (0 if expect_priority else 1)
    assert limitation >= 1
    assert t("provider_label", lang) not in main_text
    if expect_priority:
        expected_quotes = [item["evidence_quote"] for item in priority_items[:2] if item.get("evidence_quote")]
        assert expected_quotes and all(quote in main_text for quote in expected_quotes)
        assert evidence_quotes >= len(expected_quotes)
    else:
        assert t("student_feedback_category_lexical_repetition", lang) not in main_text
        assert t("student_feedback_no_priority_title", lang) in main_text

    ordered_section_keys = (
        "student_feedback_priorities",
        "student_feedback_next",
        "student_feedback_evidence",
        "student_feedback_strengths",
    )
    heading_positions = page.evaluate(
        "() => Object.fromEntries([...document.querySelectorAll('h3')]"
        ".map(el => [el.innerText.trim(), el.getBoundingClientRect().y]))"
    )
    section_positions = {
        key: heading_positions[t(key, lang)] for key in ordered_section_keys
    }
    assert list(section_positions.values()) == sorted(section_positions.values())
    action_size = primary.first.evaluate(
        "el => { const r=el.getBoundingClientRect(); return {width:r.width,height:r.height}; }"
    )
    primary.first.focus()
    focus = primary.first.evaluate("el => getComputedStyle(el).outlineColor")
    if viewport[0] < 700:
        assert action_size["height"] >= 44 and action_size["width"] >= 44

    health = page_health(
        page,
        (
            "student_feedback_priorities",
            "student_feedback_next_practice",
            "student_feedback_no_priority_evidence",
            "student_feedback_boundary",
        ),
    )
    assert health["exceptions"] == 0 and not health["overflow"] and not health["raw_keys"]
    assert health["main_max_width"] == "720px"

    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    state = "priority" if expect_priority else "zero_priority"
    shot = SCREENSHOTS / f"feedback_{lang}_{viewport[0]}x{viewport[1]}_{state}.png"
    page.screenshot(path=str(shot), full_page=True)

    alternate = "zh_CN" if lang == "en" else "en"
    assert harness.select_locale(page, alternate)
    open_page(page, "student_feedback_title", alternate)
    assert table_counts() == before_feedback
    assert page.locator('[data-testid="px-feedback-priority"]').count() == priority_cards

    result = {
        "combo": f"{lang}_{viewport[0]}x{viewport[1]}_{state}",
        "priority_cards": priority_cards,
        "empty_states": empty_states,
        "evidence_quotes": evidence_quotes,
        "limitation_notices": limitation,
        "primary_action": expected_action,
        "primary_size": action_size,
        "focus_color": focus,
        "section_positions": section_positions,
        "health": health,
        "render_and_locale_counts_stable": table_counts() == before_feedback,
        "feedback_engagement_trace_delta": table_counts()["feedback_engagement_traces"]
        - before_feedback["feedback_engagement_traces"],
        "screenshot": str(shot.relative_to(ROOT)),
    }
    unexpected = [item for item in console_errors if not harness.is_allowed_console(item)]
    context.close()
    return result, unexpected, page_errors


def absent_states(browser) -> tuple[dict, list[str], list[str]]:
    results: dict[str, object] = {}
    all_console: list[str] = []
    all_page_errors: list[str] = []

    for name, student_id in (("blank", ""), ("known_no_result", "S02"), ("not_found", "V094B-NOT-FOUND")):
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        console_errors, page_errors = observe_errors(page)
        page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
        assert harness.wait_stable(page)
        open_page(page, "student_feedback_title", "en")
        before = table_counts()
        if student_id:
            harness.commit_text_input(page, '.st-key-feedback_student input', student_id)
            assert harness.wait_stable(page)
        results[name] = {
            "empty_states": page.locator('[data-testid="px-empty-state"]').count(),
            "error_notices": page.locator('.px-notice-error[data-testid="px-notice"]').count(),
            "blocked_actions": page.locator('[data-state="blocked"]').count(),
            "primary_buttons": page.locator('[data-testid="stBaseButton-primary"]').count(),
            "counts_stable": table_counts() == before,
            "exceptions": page.locator('[data-testid="stException"]').count(),
        }
        all_console.extend(item for item in console_errors if not harness.is_allowed_console(item))
        all_page_errors.extend(page_errors)
        context.close()

    assert results["blank"] == {
        "empty_states": 0, "error_notices": 0, "blocked_actions": 1,
        "primary_buttons": 0, "counts_stable": True, "exceptions": 0,
    }
    assert results["known_no_result"] == {
        "empty_states": 1, "error_notices": 0, "blocked_actions": 0,
        "primary_buttons": 1, "counts_stable": True, "exceptions": 0,
    }
    assert results["not_found"] == {
        "empty_states": 0, "error_notices": 1, "blocked_actions": 0,
        "primary_buttons": 0, "counts_stable": True, "exceptions": 0,
    }
    return results, all_console, all_page_errors


def outage(browser, api_process) -> tuple[dict, list[str], list[str]]:
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    console_errors, page_errors = observe_errors(page)
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    open_page(page, "student_feedback_title", "en")
    before = table_counts()
    harness.stop_process(api_process)
    harness.commit_text_input(page, '.st-key-feedback_student input', "S02")
    assert harness.wait_stable(page, expected='.px-notice-error[data-testid="px-notice"]')
    result = {
        "error_notices": page.locator('.px-notice-error[data-testid="px-notice"]').count(),
        "empty_states": page.locator('[data-testid="px-empty-state"]').count(),
        "primary_buttons": page.locator('[data-testid="stBaseButton-primary"]').count(),
        "counts_stable": table_counts() == before,
        "exceptions": page.locator('[data-testid="stException"]').count(),
    }
    expected_network = ("ERR_CONNECTION_REFUSED", "Failed to fetch")
    unexpected = [
        item for item in console_errors
        if not harness.is_allowed_console(item) and not any(marker in item for marker in expected_network)
    ]
    context.close()
    return result, unexpected, page_errors


def main() -> int:
    harness.prepare_isolated_db()
    api = streamlit = None
    evidence: dict[str, object] = {"run_id": "v0.9.4-b-20260801-r1", "contexts": []}
    try:
        api, streamlit = harness.start_stack("feedback_slice")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            console_errors: list[str] = []
            page_errors: list[str] = []
            for lang, viewport, student, essay, priority in (
                ("en", (1280, 900), "V094B-FEEDBACK-PRIORITY", PRIORITY_ESSAY, True),
                ("zh_CN", (390, 844), "S02", ZERO_PRIORITY_ESSAY, False),
            ):
                result, console, errors = feedback_result_context(
                    browser, lang, viewport, student, essay, priority
                )
                evidence["contexts"].append(result)
                console_errors.extend(console)
                page_errors.extend(errors)

            states, state_console, state_errors = absent_states(browser)
            evidence["absent_states"] = states
            console_errors.extend(state_console)
            page_errors.extend(state_errors)

            outage_result, outage_console, outage_errors = outage(browser, api)
            api = None
            evidence["outage"] = outage_result
            console_errors.extend(outage_console)
            page_errors.extend(outage_errors)
            api = harness.start_api_process("feedback_recovery")
            evidence["console_errors"] = console_errors
            evidence["page_errors"] = page_errors
            browser.close()
    finally:
        harness.stop_stack(api, streamlit)

    evidence["ports_cleaned"] = True
    (HERE / "feedback_slice_evidence.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    assert all(item["render_and_locale_counts_stable"] for item in evidence["contexts"])
    assert all(item["feedback_engagement_trace_delta"] == 0 for item in evidence["contexts"])
    assert evidence["outage"] == {
        "error_notices": 1, "empty_states": 0, "primary_buttons": 0,
        "counts_stable": True, "exceptions": 0,
    }
    assert not evidence["console_errors"]
    assert not evidence["page_errors"]
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
