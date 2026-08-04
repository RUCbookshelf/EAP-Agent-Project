"""v0.9.7-A rendered-page verification matrix (browser).

Runs the full priority-guided cycle through the real production UI path with
LLM_PROVIDER=local on an isolated database copy:
  Writing -> Feedback (priority) -> Open Revision -> priority task ->
  empty validation -> submit revision -> completion state -> Practice entry
  (accurate no-target) -> Finish cycle -> Home -> reload re-entry (completed
  state, no duplicate form) in English/Chinese x desktop/mobile combinations.

Every affected Student page is reported per locale/viewport combination with
exceptions, overflow, raw locale keys, remote-resource requests, control
clickability, and database write counts. No live provider call is made.
"""
from __future__ import annotations

import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

import v097a_harness as harness  # noqa: E402
from app.ui.locale import t  # noqa: E402

RUN_ID = "v0.9.7-a-20260804-r1"
SCREENSHOTS = HERE / "screenshots"
PROMPT = "Should schools require students to learn a second language?"

SOURCE_ESSAY = (
    "Learning a second language is a question that many schools discuss, and whether it should be compulsory "
    "for every student is not easy to answer. Both sides have reasonable points, but I believe that schools "
    "should require at least one second language for all students.\n\n"
    "On the one hand, some people think that making a second language compulsory puts too much pressure on "
    "students. They say that not every learner is talented at languages, and that some students need more time "
    "for mathematics, science, or art. When learners struggle with a subject they will rarely use, school can "
    "become a source of stress instead of a place of growth. For these reasons, some parents argue that "
    "children should choose their own subjects.\n\n"
    "On the other hand, the benefits of a second language are really clear. A second language is really useful "
    "and really practical for work and travel, and people who speak another language are really welcome in "
    "many companies. In my city, businesses now need workers who can talk with foreign customers, and "
    "bilingual employees often receive better opportunities. It is also interesting to read books or watch "
    "films in the original language, because you understand the culture in a deeper way. Learning a language "
    "also trains the brain, and studies show that bilingual people switch between tasks more quickly. When I "
    "started learning English, I found it really hard at first, but after two years I could talk with tourists "
    "and make friends online. That experience changed my view, and I think every young person should have the "
    "same chance.\n\n"
    "In conclusion, although compulsory language learning is not perfect, its advantages are stronger than its "
    "disadvantages. Schools should keep foreign languages as a required subject and offer extra support to "
    "students who find it difficult."
)

REVISED_ESSAY = (
    "Learning a second language is a question that many schools discuss, and whether it should be compulsory "
    "for every student is not easy to answer. Both sides have reasonable points, but I believe that schools "
    "should require at least one second language for all students.\n\n"
    "On the one hand, some people think that making a second language compulsory puts too much pressure on "
    "students. They say that not every learner is talented at languages, and that some students need more time "
    "for mathematics, science, or art. When learners struggle with a subject they will rarely use, school can "
    "become a source of stress instead of a place of growth. For these reasons, some parents argue that "
    "children should choose their own subjects.\n\n"
    "On the other hand, the benefits of a second language are genuinely clear. Such a language is genuinely "
    "useful and genuinely practical for work and travel, and people who speak another language are genuinely "
    "welcome in many companies. In my city, businesses now need workers who can talk with foreign customers, "
    "and bilingual employees often receive better opportunities. It is also interesting to read books or watch "
    "films in the original language, because you understand the culture in a deeper way. Learning a language "
    "also trains the brain, and studies show that bilingual people switch between tasks more quickly. When I "
    "started learning English, I found it genuinely hard at first, but after two years I could talk with "
    "tourists and make friends online. That experience changed my view, and I think every young person should "
    "have the same chance.\n\n"
    "In conclusion, although compulsory language learning is not perfect, its advantages are stronger than its "
    "disadvantages. Schools should keep foreign languages as a required subject and offer extra support to "
    "students who find it difficult."
)


def observe(page):
    console_errors: list[str] = []
    page_errors: list[str] = []
    remote_requests: list[str] = []
    page.on(
        "console",
        lambda message: console_errors.append(message.text)
        if message.type == "error" else None,
    )
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.on(
        "request",
        lambda request: remote_requests.append(request.url)
        if not request.url.startswith(("http://127.0.0.1", "http://localhost"))
        else None,
    )
    return console_errors, page_errors, remote_requests


def health(page, raw_keys: tuple[str, ...]) -> dict[str, object]:
    width = page.evaluate("() => window.innerWidth")
    text = page.locator("body").inner_text()
    main = page.locator('[data-testid="stMainBlockContainer"]').first
    return {
        "exceptions": page.locator('[data-testid="stException"]').count(),
        "overflow": page.evaluate("() => document.documentElement.scrollWidth") > width,
        "raw_keys": [key for key in raw_keys if key in text],
        "main_max_width": main.evaluate("el => getComputedStyle(el).maxWidth"),
    }


def click_key(page, key: str) -> None:
    harness.close_sidebar(page)
    locator = page.locator(f".st-key-{key}")
    assert locator.count() == 1, f"expected one button for key {key}"
    locator.click()


def button_rect(page, key: str) -> dict[str, float]:
    locator = page.locator(f".st-key-{key}")
    assert locator.count() == 1, f"expected one button for key {key}"
    return locator.first.evaluate(
        "el => { const r = el.getBoundingClientRect(); "
        "return {width: r.width, height: r.height}; }"
    )



def select_oldest_source_option(page) -> None:
    """Open the Revision source selectbox and choose the oldest candidate.

    Streamlit 1.60 renders the selectbox with React Aria ComboBox: the popup
    opens on ArrowDown and options are ordered newest-first, so the oldest
    (original source) candidate is the last option. Confirmed by a DOM probe.
    """
    combobox = page.locator('.st-key-revision_source_select [role="combobox"]')
    assert combobox.count() == 1
    combobox.click()
    page.wait_for_timeout(600)
    page.keyboard.press("ArrowDown")
    page.wait_for_timeout(900)
    count = page.locator('[role="option"]').count()
    assert count >= 2, f"expected at least 2 candidates, got {count}"
    for _ in range(count - 1):
        page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)


def submit_writing(page, student_id: str, lang: str, essay: str) -> None:
    harness.open_page(page, "student_writing_title", lang)
    harness.commit_text_input(page, ".st-key-writing_student input", student_id)
    harness.commit_text_input(page, ".st-key-writing_prompt_input textarea", PROMPT)
    harness.commit_text_input(page, ".st-key-writing_essay textarea", essay)
    harness.close_sidebar(page)
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-state="complete"]', timeout=90)


def run_cycle(
    browser, student_id: str, lang: str, viewport: dict, tag: str
) -> tuple[dict, list[str], list[str], list[str]]:
    """One complete priority-guided cycle in one locale/viewport combination."""
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    console_errors, page_errors, remote_requests = observe(page)
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    harness.close_sidebar(page)

    result: dict[str, object] = {"combination": f"{lang} {viewport['width']}x{viewport['height']}"}
    before = harness.learner_counts(student_id)
    assert before == {"essays": 0, "linked_revisions": 0, "revision_groups": 0,
                      "revision_snapshots": 0}

    # Writing -> Feedback with a real generated priority (LocalDemo path).
    submit_writing(page, student_id, lang, SOURCE_ESSAY)
    after_write = harness.learner_counts(student_id)
    assert after_write["essays"] == 1
    harness.close_sidebar(page)
    page.locator(".st-key-writing_review_feedback").click()
    assert harness.wait_stable(page, expected=".st-key-feedback_primary_action")
    text = page.locator('[data-testid="stMainBlockContainer"]').inner_text()
    assert t("student_feedback_priorities", lang) in text
    assert t("student_feedback_category_lexical_repetition", lang) in text
    assert t("student_feedback_open_revision", lang) in text
    assert t("student_feedback_open_practice", lang) in text
    assert t("student_feedback_practice_note", lang) in text
    fb_health = health(page, ("student_feedback_next_practice",))
    assert fb_health["exceptions"] == 0 and not fb_health["overflow"]
    assert not fb_health["raw_keys"]
    shot = SCREENSHOTS / f"{tag}_feedback_priority.png"
    page.screenshot(path=str(shot), full_page=True)
    result["feedback_priority"] = {"health": fb_health, "priority_visible": True,
                                   "screenshot": str(shot.relative_to(ROOT))}

    # Open Revision -> priority task renders from persisted feedback.
    click_key(page, "feedback_primary_action")
    assert harness.wait_stable(page, expected=".st-key-revision_submit_primary")
    assert harness.wait_stable(page, expected='[class*="st-key-revision_original_"] textarea')
    text = page.locator('[data-testid="stMainBlockContainer"]').inner_text()
    assert t("student_revision_priority_task", lang) in text
    assert t("student_revision_priority_reason", lang) in text
    assert t("student_revision_priority_direction", lang) in text
    assert t("student_revision_instruction", lang) in text
    assert t("student_feedback_evidence", lang) in text
    assert harness.learner_counts(student_id) == after_write  # render is zero-write
    original_value = page.locator('[class*="st-key-revision_original_"] textarea').first.input_value()
    assert original_value == SOURCE_ESSAY.strip()
    task_health = health(page, ("student_revision_priority_task",))
    assert task_health["exceptions"] == 0 and not task_health["overflow"]
    assert not task_health["raw_keys"]
    shot = SCREENSHOTS / f"{tag}_revision_priority_task.png"
    page.screenshot(path=str(shot), full_page=True)
    result["revision_priority_task"] = {"health": task_health, "screenshot": str(shot.relative_to(ROOT))}

    # Empty revision text -> field error, zero writes.
    click_key(page, "revision_submit_primary")
    assert harness.wait_stable(page, expected='[data-testid="px-field-error"]')
    assert harness.learner_counts(student_id) == after_write
    assert page.locator('[data-testid="stException"]').count() == 0
    result["empty_validation_zero_write"] = True

    # Submit a real revision -> completion state.
    harness.commit_text_input(page, ".st-key-revision_text_input textarea", REVISED_ESSAY)
    click_key(page, "revision_submit_primary")
    assert harness.wait_stable(page, expected='[data-state="complete"]', timeout=90)
    saved = harness.learner_counts(student_id)
    assert saved == {"essays": 2, "linked_revisions": 1, "revision_groups": 1,
                     "revision_snapshots": 1}, saved
    text = page.locator('[data-testid="stMainBlockContainer"]').inner_text()
    assert t("student_revision_saved_title", lang) in text
    assert t("student_revision_priority_addressed", lang) in text
    assert t("student_revision_step_complete", lang) in text
    assert t("student_revision_finish_cycle", lang) in text
    assert t("student_revision_open_practice", lang) in text
    assert t("student_revision_open_journey", lang) in text
    assert t("student_revision_practice_note", lang) in text
    assert page.locator(".st-key-revision_text_input textarea").count() == 0
    assert page.locator('[data-testid="stException"]').count() == 0
    complete_health = health(page, ("student_revision_saved_title",))
    assert not complete_health["overflow"] and not complete_health["raw_keys"]
    primary_size = button_rect(page, "revision_finish_cycle")
    shot = SCREENSHOTS / f"{tag}_revision_completed.png"
    page.screenshot(path=str(shot), full_page=True)
    result["revision_completed"] = {
        "health": complete_health, "primary_size": primary_size,
        "persisted": saved, "screenshot": str(shot.relative_to(ROOT)),
    }
    if viewport["width"] < 700:
        assert primary_size["width"] >= 44 and primary_size["height"] >= 44

    # Practice entry point: accurate no-target continuation, no fabrication.
    click_key(page, "revision_open_practice")
    assert harness.wait_stable(page, expected=".st-key-practice_primary_action")
    text = page.locator('[data-testid="stMainBlockContainer"]').inner_text()
    assert t("student_practice_no_target_action", lang) in text
    practice_health = health(page, ("student_practice_no_target_action",))
    assert practice_health["exceptions"] == 0 and not practice_health["overflow"]
    shot = SCREENSHOTS / f"{tag}_practice_no_target.png"
    page.screenshot(path=str(shot), full_page=True)
    result["practice_entry"] = {"health": practice_health,
                                "screenshot": str(shot.relative_to(ROOT))}

    # Reload (new session) -> re-entry shows the completed state, no form,
    # no duplicate submission possible. Sidebar navigation happens only right
    # after a fresh page load so the mobile overlay is never mid-session.
    page.reload(wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    harness.open_page(page, "student_revision_title", lang)
    harness.commit_text_input(page, ".st-key-revision_student input", student_id)
    assert harness.wait_stable(page, expected='[data-testid="px-student-context"]')
    select_oldest_source_option(page)
    assert harness.wait_stable(page, expected='[data-testid="px-student-context"]')
    text = page.locator('[data-testid="stMainBlockContainer"]').inner_text()
    assert t("student_revision_already_submitted_title", lang) in text
    assert t("student_revision_priority_addressed", lang) in text
    assert page.locator(".st-key-revision_submit_primary").count() == 0
    assert harness.learner_counts(student_id) == saved
    reentry_health = health(page, ("student_revision_already_submitted_title",))
    assert reentry_health["exceptions"] == 0 and not reentry_health["overflow"]
    shot = SCREENSHOTS / f"{tag}_reentry_completed.png"
    page.screenshot(path=str(shot), full_page=True)
    result["reentry"] = {"health": reentry_health, "no_form": True,
                         "persisted_stable": harness.learner_counts(student_id) == saved,
                         "screenshot": str(shot.relative_to(ROOT))}

    # Finish the cycle from the completed re-entry state -> Home.
    click_key(page, "revision_finish_cycle")
    assert harness.wait_stable(page, expected=".st-key-home_student")
    text = page.locator('[data-testid="stMainBlockContainer"]').inner_text()
    assert t("student_home_title", lang) in text
    home_health = health(page, ("student_home_current_task",))
    assert home_health["exceptions"] == 0 and not home_health["overflow"]
    shot = SCREENSHOTS / f"{tag}_home_after_finish.png"
    page.screenshot(path=str(shot), full_page=True)
    result["end_cycle_home"] = {"health": home_health,
                                "screenshot": str(shot.relative_to(ROOT))}
    assert harness.learner_counts(student_id) == saved

    unexpected_console = [item for item in console_errors
                          if not harness.is_allowed_console(item)]
    context.close()
    return result, unexpected_console, page_errors, remote_requests



def research_smoke(browser, tag: str) -> dict:
    """Established Research smoke subset: Overview, Data, System Audit.

    Mirrors the v0.9.4-B established smoke (3 pages x English desktop /
    Chinese mobile = 6 renders); Research code is untouched in v0.9.7-A and
    this confirms no regression in the running stack.
    """
    result: dict[str, object] = {}
    pages = (
        ("research_overview_title", "research_overview_title"),
        ("nav_research_data", "nav_research_data"),
        ("research_audit_title", "research_audit_title"),
    )
    for lang, viewport in (("en", {"width": 1280, "height": 900}),
                           ("zh_CN", {"width": 390, "height": 844})):
        context = browser.new_context(viewport=viewport)
        page = context.new_page()
        console_errors, page_errors, remote_requests = observe(page)
        page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
        assert harness.wait_stable(page)
        if lang == "zh_CN":
            assert harness.select_locale(page, lang)
        assert harness.select_role(page, "research", lang)
        for key, h2 in pages:
            assert harness.select_page(page, t(key, lang), t(h2, lang))
            h = health(page, (key,))
            assert h["exceptions"] == 0 and not h["overflow"], (key, h)
            assert not h["raw_keys"]
            result[f"{lang}_{viewport['width']}x{viewport['height']}_{key}"] = h
        unexpected = [item for item in console_errors if not harness.is_allowed_console(item)]
        assert not unexpected, unexpected
        assert not page_errors, page_errors
        assert not remote_requests, remote_requests
        context.close()
    return result


def main() -> int:
    harness.prepare_isolated_db()
    api = streamlit = None
    evidence: dict[str, object] = {"run_id": RUN_ID}
    try:
        api, streamlit = harness.start_stack("v097a_matrix")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                en_desktop, c1, e1, r1 = run_cycle(
                    browser, "V097A-P1", "en", {"width": 1280, "height": 900}, "en_1280x900"
                )
                zh_desktop, c2, e2, r2 = run_cycle(
                    browser, "V097A-P2", "zh_CN", {"width": 1280, "height": 900}, "zh_1280x900"
                )
                en_mobile, c3, e3, r3 = run_cycle(
                    browser, "V097A-P3", "en", {"width": 390, "height": 844}, "en_390x844"
                )
                zh_mobile, c4, e4, r4 = run_cycle(
                    browser, "V097A-P4", "zh_CN", {"width": 390, "height": 844}, "zh_390x844"
                )
                research = research_smoke(browser, "research")
            finally:
                browser.close()
            evidence["en_1280x900"] = en_desktop
            evidence["zh_1280x900"] = zh_desktop
            evidence["en_390x844"] = en_mobile
            evidence["zh_390x844"] = zh_mobile
            evidence["research_smoke"] = research
            evidence["console_errors"] = c1 + c2 + c3 + c4
            evidence["page_errors"] = e1 + e2 + e3 + e4
            evidence["remote_requests"] = r1 + r2 + r3 + r4
    finally:
        harness.stop_stack(api, streamlit)

    evidence["ports_cleaned"] = True
    (HERE / "rendered_page_matrix_evidence.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    assert not evidence["console_errors"], evidence["console_errors"]
    assert not evidence["page_errors"], evidence["page_errors"]
    assert not evidence["remote_requests"], evidence["remote_requests"]
    for combo in ("en_1280x900", "zh_1280x900", "en_390x844", "zh_390x844"):
        assert evidence[combo]["revision_completed"]["persisted"] == {
            "essays": 2, "linked_revisions": 1, "revision_groups": 1,
            "revision_snapshots": 1,
        }
        assert evidence[combo]["empty_validation_zero_write"] is True
        assert evidence[combo]["reentry"]["no_form"] is True
        assert evidence[combo]["reentry"]["persisted_stable"] is True
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())