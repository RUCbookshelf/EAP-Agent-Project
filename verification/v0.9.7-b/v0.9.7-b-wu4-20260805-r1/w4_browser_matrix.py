"""v0.9.7-B WU4 rendered-page verification matrix (browser).

Runs the WU4 focused task-and-attempt path through the real production UI
with LLM_PROVIDER=local on an isolated database:

  Writing -> Feedback (priority) -> Open Practice (explicit intent)
  -> create-or-reuse target -> focused task renders (priority context,
  evidence, direction, instruction) -> empty validation (zero writes)
  -> valid response persisted as one attempt -> saved state with reference
  -> reload/re-entry restores the saved state (no duplicates, no completion
  claim, no WU5 actions)

Reported independently for English/Chinese x desktop/mobile with console,
page-error, remote-request, overflow, raw-key, and write-count checks.
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

import w4_harness as harness  # noqa: E402
from app.ui.locale import t  # noqa: E402

RUN_ID = "v0.9.7-b-wu4-20260805-r1"
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

VALID_RESPONSE = (
    "A second language is genuinely useful for work and travel, and people who speak one are welcome in "
    "many companies."
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
    }


def click_key(page, key: str) -> None:
    harness.close_sidebar(page)
    locator = page.locator(f".st-key-{key}")
    assert locator.count() == 1, f"expected one control for key {key}"
    locator.click()


def button_rect(page, key: str) -> dict[str, float]:
    locator = page.locator(f".st-key-{key}")
    assert locator.count() == 1, f"expected one control for key {key}"
    return locator.first.evaluate(
        "el => { const r = el.getBoundingClientRect(); "
        "return {width: r.width, height: r.height}; }"
    )


def submit_writing(page, student_id: str, lang: str) -> None:
    harness.open_page(page, "student_writing_title", lang)
    harness.commit_text_input(page, ".st-key-writing_student input", student_id)
    harness.commit_text_input(page, ".st-key-writing_prompt_input textarea", PROMPT)
    harness.commit_text_input(page, ".st-key-writing_essay textarea", SOURCE_ESSAY)
    harness.close_sidebar(page)
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-state="complete"]', timeout=90)


def run_cycle(
    browser, student_id: str, lang: str, viewport: dict, tag: str
) -> tuple[dict, list[str], list[str], list[str]]:
    """One WU4 focused task-and-attempt cycle in one locale/viewport combo."""
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
    assert before == {
        "essays": 0, "practice_targets": 0, "exercise_instances": 0,
        "exercise_attempts": 0, "practice_evaluations": 0,
    }, before

    # Writing -> Feedback with a real generated priority (LocalDemo path).
    submit_writing(page, student_id, lang)
    after_write = harness.learner_counts(student_id)
    assert after_write["essays"] == 1
    harness.close_sidebar(page)
    page.locator(".st-key-writing_review_feedback").click()
    assert harness.wait_stable(page, expected=".st-key-feedback_practice_priority_0")
    text = page.locator('[data-testid="stMainBlockContainer"]').inner_text()
    assert t("student_feedback_priorities", lang) in text
    assert t("student_feedback_practice_priority", lang) in text
    assert t("student_feedback_practice_note", lang) in text
    fb_health = health(page, ("student_feedback_practice_priority",))
    assert fb_health["exceptions"] == 0 and not fb_health["overflow"]
    assert not fb_health["raw_keys"]
    shot = SCREENSHOTS / f"{tag}_feedback_priority.png"
    page.screenshot(path=str(shot), full_page=True)
    result["feedback_priority"] = {"health": fb_health,
                                   "screenshot": str(shot.relative_to(ROOT))}

    # Open Practice: explicit intent -> create-or-reuse -> focused task.
    click_key(page, "feedback_practice_priority_0")
    assert harness.wait_stable(page, expected='.st-key-practice_response_v2 textarea', timeout=60)
    counts = harness.learner_counts(student_id)
    assert counts == {
        "essays": 1, "practice_targets": 1, "exercise_instances": 1,
        "exercise_attempts": 0, "practice_evaluations": 0,
    }, counts
    text = page.locator('[data-testid="stMainBlockContainer"]').inner_text()
    assert t("student_practice_priority_task", lang) in text
    assert t("student_practice_why_selected", lang) in text
    assert t("student_practice_direction", lang) in text
    assert t("student_feedback_evidence", lang) in text
    assert t("exercise_instructions", lang) in text
    assert t("submit_attempt", lang) in text
    assert "completely mastered" not in text.lower()
    assert page.locator(".st-key-practice_finish").count() == 0
    assert page.locator(".st-key-practice_continue").count() == 0
    task_health = health(page, ("student_practice_priority_task",))
    assert task_health["exceptions"] == 0 and not task_health["overflow"]
    assert not task_health["raw_keys"]
    submit_size = button_rect(page, "practice_submit")
    if viewport["width"] < 700:
        assert submit_size["width"] >= 44 and submit_size["height"] >= 44
    shot = SCREENSHOTS / f"{tag}_practice_task.png"
    page.screenshot(path=str(shot), full_page=True)
    result["focused_task"] = {"health": task_health, "counts": counts,
                              "submit_size": submit_size,
                              "screenshot": str(shot.relative_to(ROOT))}

    # Empty response -> field error, zero writes.
    click_key(page, "practice_submit")
    assert harness.wait_stable(page, expected='[data-testid="px-field-error"]')
    assert harness.learner_counts(student_id) == counts
    assert page.locator('[data-testid="stException"]').count() == 0
    result["empty_validation_zero_write"] = True

    # Valid response -> one persisted attempt + saved state.
    harness.commit_text_input(page, ".st-key-practice_response_v2 textarea", VALID_RESPONSE)
    click_key(page, "practice_submit")
    assert harness.wait_stable(page, expected=".st-key-practice_primary_action", timeout=60)
    saved = harness.learner_counts(student_id)
    assert saved == {
        "essays": 1, "practice_targets": 1, "exercise_instances": 1,
        "exercise_attempts": 1, "practice_evaluations": 1,
    }, saved
    text = page.locator('[data-testid="stMainBlockContainer"]').inner_text()
    assert t("student_practice_attempt_saved", lang) in text
    import re
    assert re.search(r"#EA\d{6}", text), "attempt reference caption missing"
    assert "completed this priority" not in text.lower()
    assert page.locator(".st-key-practice_finish").count() == 0
    assert page.locator(".st-key-practice_continue").count() == 0
    saved_health = health(page, ("student_practice_attempt_saved",))
    assert saved_health["exceptions"] == 0 and not saved_health["overflow"]
    assert not saved_health["raw_keys"]
    shot = SCREENSHOTS / f"{tag}_practice_saved.png"
    page.screenshot(path=str(shot), full_page=True)
    result["attempt_saved"] = {"health": saved_health, "counts": saved,
                               "screenshot": str(shot.relative_to(ROOT))}

    # Reload (new session) -> re-entry restores the saved state.
    page.reload(wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    harness.open_page(page, "practice", lang)
    harness.commit_text_input(page, ".st-key-practice_student_v2 input", student_id)
    assert harness.wait_stable(page, expected=".st-key-practice_primary_action", timeout=60)
    assert harness.learner_counts(student_id) == saved
    text = page.locator('[data-testid="stMainBlockContainer"]').inner_text()
    assert t("student_practice_attempt_saved", lang) in text
    assert page.locator(".st-key-practice_response_v2 textarea").count() == 0
    reentry_health = health(page, ("student_practice_attempt_saved",))
    assert reentry_health["exceptions"] == 0 and not reentry_health["overflow"]
    assert not reentry_health["raw_keys"]
    shot = SCREENSHOTS / f"{tag}_practice_reentry.png"
    page.screenshot(path=str(shot), full_page=True)
    result["reentry"] = {"health": reentry_health, "counts_stable": True,
                         "no_form": True, "screenshot": str(shot.relative_to(ROOT))}

    unexpected_console = [item for item in console_errors
                          if not harness.is_allowed_console(item)]
    context.close()
    return result, unexpected_console, page_errors, remote_requests


def main() -> int:
    harness.prepare_isolated_db()
    api = streamlit = None
    evidence: dict[str, object] = {"run_id": RUN_ID}
    try:
        api, streamlit = harness.start_stack("w4_matrix")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                en_desktop, c1, e1, r1 = run_cycle(
                    browser, "V097B-W1", "en", {"width": 1280, "height": 900}, "en_1280x900"
                )
                zh_desktop, c2, e2, r2 = run_cycle(
                    browser, "V097B-W2", "zh_CN", {"width": 1280, "height": 900}, "zh_1280x900"
                )
                en_mobile, c3, e3, r3 = run_cycle(
                    browser, "V097B-W3", "en", {"width": 390, "height": 844}, "en_390x844"
                )
                zh_mobile, c4, e4, r4 = run_cycle(
                    browser, "V097B-W4", "zh_CN", {"width": 390, "height": 844}, "zh_390x844"
                )
            finally:
                browser.close()
            evidence["en_1280x900"] = en_desktop
            evidence["zh_1280x900"] = zh_desktop
            evidence["en_390x844"] = en_mobile
            evidence["zh_390x844"] = zh_mobile
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
        assert evidence[combo]["focused_task"]["counts"]["practice_targets"] == 1
        assert evidence[combo]["focused_task"]["counts"]["exercise_instances"] == 1
        assert evidence[combo]["empty_validation_zero_write"] is True
        assert evidence[combo]["attempt_saved"]["counts"]["exercise_attempts"] == 1
        assert evidence[combo]["attempt_saved"]["counts"]["practice_evaluations"] == 1
        assert evidence[combo]["reentry"]["counts_stable"] is True
        assert evidence[combo]["reentry"]["no_form"] is True
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
