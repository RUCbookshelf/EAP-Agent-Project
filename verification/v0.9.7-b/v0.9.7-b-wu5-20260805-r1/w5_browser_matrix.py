"""v0.9.7-B WU5 rendered-page verification matrix (browser).

Runs the WU5 practice-cycle completion path through the real production UI
with LLM_PROVIDER=local on an isolated database:

  Writing -> Feedback (priority) -> Open Practice (explicit intent)
  -> create-or-reuse target -> focused task -> valid attempt persisted
  -> evaluation available -> Finish This Practice Cycle -> ACTIVE->COMPLETED
  -> persistence-backed completed state -> repeat completion idempotent
  -> reload / Feedback re-entry / Revision re-entry reuse the completed
  target -> bounded next steps (another active target, Return to Feedback,
  Open Learning Journey) -> no new Journey event, no mastery wording.

Reported independently for English/Chinese x desktop/mobile with console,
page-error, remote-request, overflow, raw-key, and write-count checks.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

import requests
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

import w5_harness as harness  # noqa: E402
from app.ui.locale import t  # noqa: E402

RUN_ID = "v0.9.7-b-wu5-20260805-r1"
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

VALID_REVISION = (
    "A second language is genuinely practical for work and travel, and people who speak one are welcome in "
    "many companies. Schools should keep foreign languages as a required subject."
)

FORBIDDEN_WORDING = ("mastered", "improved", "proficient", "passed", "cefr",
                     "learning gain", "transfer")


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


def body_text(page) -> str:
    return page.locator('[data-testid="stMainBlockContainer"]').inner_text()


def assert_no_forbidden_wording(page) -> None:
    text = body_text(page).lower()
    for word in FORBIDDEN_WORDING:
        assert word not in text, f"forbidden wording present: {word}"


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
    """One WU5 completion cycle in one locale/viewport combo."""
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
        "essays": 0, "practice_targets": 0, "completed_targets": 0,
        "exercise_instances": 0, "exercise_attempts": 0, "practice_evaluations": 0,
    }, before

    # Writing -> Feedback with a real generated priority (LocalDemo path).
    submit_writing(page, student_id, lang)
    assert harness.learner_counts(student_id)["essays"] == 1
    harness.close_sidebar(page)
    page.locator(".st-key-writing_review_feedback").click()
    assert harness.wait_stable(page, expected=".st-key-feedback_practice_priority_0")
    text = body_text(page)
    assert t("student_feedback_priorities", lang) in text
    assert t("student_feedback_practice_priority", lang) in text
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
        "essays": 1, "practice_targets": 1, "completed_targets": 0,
        "exercise_instances": 1, "exercise_attempts": 0, "practice_evaluations": 0,
    }, counts
    text = body_text(page)
    assert t("student_practice_priority_task", lang) in text
    assert t("student_practice_why_selected", lang) in text
    assert t("student_practice_direction", lang) in text
    assert t("student_feedback_evidence", lang) in text
    assert t("exercise_instructions", lang) in text
    assert t("submit_attempt", lang) in text
    assert page.locator(".st-key-practice_finish").count() == 0
    assert_no_forbidden_wording(page)
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

    # Valid response -> one persisted attempt + saved state + evaluation.
    harness.commit_text_input(page, ".st-key-practice_response_v2 textarea", VALID_RESPONSE)
    click_key(page, "practice_submit")
    assert harness.wait_stable(page, expected=".st-key-practice_finish", timeout=60)
    saved = harness.learner_counts(student_id)
    assert saved == {
        "essays": 1, "practice_targets": 1, "completed_targets": 0,
        "exercise_instances": 1, "exercise_attempts": 1, "practice_evaluations": 1,
    }, saved
    text = body_text(page)
    assert t("student_practice_attempt_saved", lang) in text
    assert re.search(r"#EA\d{6}", text), "attempt reference caption missing"
    assert t("student_practice_finish_cycle", lang) in text
    assert t("student_practice_action_finish", lang) in text
    assert_no_forbidden_wording(page)
    saved_health = health(page, ("student_practice_attempt_saved",))
    assert saved_health["exceptions"] == 0 and not saved_health["overflow"]
    assert not saved_health["raw_keys"]
    finish_size = button_rect(page, "practice_finish")
    if viewport["width"] < 700:
        assert finish_size["width"] >= 44 and finish_size["height"] >= 44
    shot = SCREENSHOTS / f"{tag}_practice_saved.png"
    page.screenshot(path=str(shot), full_page=True)
    result["attempt_saved"] = {"health": saved_health, "counts": saved,
                               "finish_size": finish_size,
                               "screenshot": str(shot.relative_to(ROOT))}

    # Finish -> explicit ACTIVE->COMPLETED -> completed state.
    journey_before = harness.journey_event_count(student_id)
    click_key(page, "practice_finish")
    assert harness.wait_stable(page, expected=".st-key-practice_return_feedback", timeout=60)
    assert page.locator(".st-key-practice_finish").count() == 0
    assert page.locator(".st-key-practice_response_v2 textarea").count() == 0
    completed = harness.learner_counts(student_id)
    assert completed["completed_targets"] == 1
    for key in ("essays", "practice_targets", "exercise_instances",
                "exercise_attempts", "practice_evaluations"):
        assert completed[key] == saved[key], (completed, saved)
    text = body_text(page)
    assert t("student_practice_completed_title", lang) in text
    assert t("student_practice_completed_saved", lang) in text
    assert t("student_practice_completed_next", lang) in text
    assert re.search(r"#EA\d{6}", text), "completed attempt reference missing"
    assert_no_forbidden_wording(page)
    completed_health = health(page, (
        "student_practice_completed_title", "student_practice_completed_saved"))
    assert completed_health["exceptions"] == 0 and not completed_health["overflow"]
    assert not completed_health["raw_keys"]
    assert harness.journey_event_count(student_id) == journey_before
    targets = requests.get(
        f"{harness.BASE}/api/v1/students/{student_id}/practice-targets",
        timeout=30).json()
    priority_targets = [
        item for item in targets if item.get("source_priority_id")
    ]
    assert len(priority_targets) == 1, targets
    target_id = priority_targets[0]["practice_target_id"]
    column_status, stored_json = harness.target_status(target_id)
    assert column_status == "completed"
    assert stored_json["status"] == "completed"
    assert stored_json.get("updated_at")
    completed_updated_at = stored_json["updated_at"]
    shot = SCREENSHOTS / f"{tag}_practice_completed.png"
    page.screenshot(path=str(shot), full_page=True)
    result["completed"] = {"health": completed_health, "counts": completed,
                           "no_form": True, "no_finish": True,
                           "journey_events_unchanged": True,
                           "column_status": column_status,
                           "json_status": stored_json["status"],
                           "screenshot": str(shot.relative_to(ROOT))}

    # Repeated completion via API: idempotent, no duplicate rows.
    status, repeated = harness.repeat_completion(student_id, target_id)
    assert status == 200
    assert repeated["practice_target_id"] == target_id
    assert repeated["status"] == "completed"
    assert harness.learner_counts(student_id) == completed
    column_status, stored_json = harness.target_status(target_id)
    assert column_status == "completed"
    assert stored_json["updated_at"] == completed_updated_at
    result["repeat_completion_idempotent"] = {
        "status": status, "same_target": True, "counts_stable": True,
    }

    # Re-entry through Feedback (same session): reuse the completed target.
    harness.open_page(page, "student_feedback_title", lang)
    assert harness.wait_stable(page, expected=".st-key-feedback_practice_priority_0")
    click_key(page, "feedback_practice_priority_0")
    assert harness.wait_stable(page, expected=".st-key-practice_return_feedback", timeout=60)
    assert t("student_practice_completed_title", lang) in body_text(page)
    assert harness.learner_counts(student_id) == completed
    result["feedback_reentry"] = {"reused_completed": True, "counts_stable": True}

    # Return to Feedback performs navigation only.
    click_key(page, "practice_return_feedback")
    assert harness.wait_stable(page, expected=".st-key-feedback_practice_priority_0", timeout=30)
    assert t("student_feedback_priorities", lang) in body_text(page)
    result["return_to_feedback"] = {"navigation_only": True}

    # Back to the completed target via Feedback.
    click_key(page, "feedback_practice_priority_0")
    assert harness.wait_stable(page, expected=".st-key-practice_return_feedback", timeout=60)

    # In-session Revision re-entry: submit a linked revision; the revision
    # completion state's Open Practice reuses the completed target.
    harness.open_page(page, "student_revision_title", lang)
    harness.commit_text_input(page, ".st-key-revision_student input", student_id)
    assert harness.wait_stable(page, expected=".st-key-revision_text_input textarea", timeout=60)
    harness.commit_text_input(page, ".st-key-revision_text_input textarea", VALID_REVISION)
    click_key(page, "revision_submit_primary")
    assert harness.wait_stable(page, expected=".st-key-revision_open_practice", timeout=90)
    click_key(page, "revision_open_practice")
    assert harness.wait_stable(page, expected=".st-key-practice_return_feedback", timeout=60)
    assert t("student_practice_completed_title", lang) in body_text(page)
    assert page.locator(".st-key-practice_response_v2 textarea").count() == 0
    result["revision_reentry_session"] = {"reused_completed": True}

    # Reload (new session) -> direct Practice re-entry restores the
    # completed state; no fresh response form; no new writes.
    page.reload(wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    harness.open_page(page, "practice", lang)
    harness.commit_text_input(page, ".st-key-practice_student_v2 input", student_id)
    assert harness.wait_stable(page, expected=".st-key-practice_return_feedback", timeout=60)
    assert harness.learner_counts(student_id)["completed_targets"] == 1
    text = body_text(page)
    assert t("student_practice_completed_title", lang) in text
    assert page.locator(".st-key-practice_response_v2 textarea").count() == 0
    assert page.locator(".st-key-practice_finish").count() == 0
    reentry_health = health(page, ("student_practice_completed_title",))
    assert reentry_health["exceptions"] == 0 and not reentry_health["overflow"]
    assert not reentry_health["raw_keys"]
    shot = SCREENSHOTS / f"{tag}_practice_reentry.png"
    page.screenshot(path=str(shot), full_page=True)
    result["reload_reentry"] = {"health": reentry_health,
                                "completed_persisted": True,
                                "no_form": True, "no_finish": True,
                                "screenshot": str(shot.relative_to(ROOT))}

    # One additional ACTIVE target (API) so the completed state can offer an
    # explicit "open another active target" action.
    resp = requests.get(
        f"{harness.BASE}/api/v1/students/{student_id}/revision-candidates",
        timeout=30)
    assert resp.status_code == 200, resp.text
    candidates = resp.json().get("candidates", [])
    assert candidates, resp.text
    essay_id = None
    for candidate in candidates:
        bundle = requests.get(
            f"{harness.BASE}/api/v1/submissions/{candidate['essay_id']}",
            timeout=30).json()
        if (bundle.get("feedback") or {}).get("priority_feedback"):
            essay_id = int(candidate["essay_id"])
            break
    assert essay_id is not None, "no priority source submission found"
    second = harness.create_second_active_target(student_id, essay_id)
    assert second["status"] == "active"
    assert harness.learner_counts(student_id)["practice_targets"] == 2
    # Navigate away and back so the page re-reads the target list.
    harness.open_page(page, "student_home_title", lang)
    harness.open_page(page, "practice", lang)
    assert harness.wait_stable(page, expected=".st-key-practice_return_feedback", timeout=60)
    assert page.locator(".st-key-practice_open_other_target").count() == 1
    other_size = button_rect(page, "practice_open_other_target")
    if viewport["width"] < 700:
        assert other_size["width"] >= 44 and other_size["height"] >= 44

    # Open Learning Journey performs navigation only.
    click_key(page, "practice_open_journey")
    assert harness.wait_stable(page, timeout=30)
    assert t("learning_journey", lang) in harness.current_h2(page)
    result["open_learning_journey"] = {"navigation_only": True}

    # Back to the completed state, then open the other active target
    # explicitly.
    harness.open_page(page, "practice", lang)
    assert harness.wait_stable(page, expected=".st-key-practice_return_feedback", timeout=60)
    click_key(page, "practice_open_other_target")
    assert harness.wait_stable(page, expected=".st-key-practice_gen", timeout=60)
    text = body_text(page)
    assert t("student_practice_action_generate", lang) in text
    assert t("student_practice_completed_title", lang) not in text
    result["open_other_active_target"] = {"explicit_only": True,
                                          "other_size": other_size}

    unexpected_console = [item for item in console_errors
                          if not harness.is_allowed_console(item)]
    context.close()
    return result, unexpected_console, page_errors, remote_requests


def main() -> int:
    harness.prepare_isolated_db()
    api = streamlit = None
    evidence: dict[str, object] = {"run_id": RUN_ID}
    try:
        api, streamlit = harness.start_stack("w5_matrix")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                en_desktop, c1, e1, r1 = run_cycle(
                    browser, "V097B-W5-ED", "en",
                    {"width": 1280, "height": 900}, "en_1280x900"
                )
                zh_desktop, c2, e2, r2 = run_cycle(
                    browser, "V097B-W5-ZD", "zh_CN",
                    {"width": 1280, "height": 900}, "zh_1280x900"
                )
                en_mobile, c3, e3, r3 = run_cycle(
                    browser, "V097B-W5-EM", "en",
                    {"width": 390, "height": 844}, "en_390x844"
                )
                zh_mobile, c4, e4, r4 = run_cycle(
                    browser, "V097B-W5-ZM", "zh_CN",
                    {"width": 390, "height": 844}, "zh_390x844"
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
        item = evidence[combo]
        assert item["focused_task"]["counts"]["practice_targets"] == 1
        assert item["focused_task"]["counts"]["exercise_instances"] == 1
        assert item["empty_validation_zero_write"] is True
        assert item["attempt_saved"]["counts"]["exercise_attempts"] == 1
        assert item["attempt_saved"]["counts"]["practice_evaluations"] == 1
        assert item["completed"]["no_form"] is True
        assert item["completed"]["no_finish"] is True
        assert item["completed"]["journey_events_unchanged"] is True
        assert item["completed"]["column_status"] == "completed"
        assert item["completed"]["json_status"] == "completed"
        assert item["repeat_completion_idempotent"]["same_target"] is True
        assert item["feedback_reentry"]["reused_completed"] is True
        assert item["revision_reentry_session"]["reused_completed"] is True
        assert item["open_other_active_target"]["explicit_only"] is True
        assert item["return_to_feedback"]["navigation_only"] is True
        assert item["open_learning_journey"]["navigation_only"] is True
        assert item["reload_reentry"]["completed_persisted"] is True
        assert item["reload_reentry"]["no_form"] is True
        assert item["reload_reentry"]["no_finish"] is True
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
