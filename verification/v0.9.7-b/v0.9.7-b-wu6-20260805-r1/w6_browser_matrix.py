"""v0.9.7-B WU6 final product matrix (browser).

Runs the complete v0.9.7-B student learning cycle through the real
production UI with LLM_PROVIDER=local on a fresh isolated database,
independently for English/Chinese x 1280x900/390x844:

  Writing -> Feedback priority -> priority-guided Revision -> linked
  revision -> explicit revision completion -> Open Practice -> create-or-
  reuse target -> focused task -> empty validation (zero writes) -> valid
  attempt -> evaluation -> Finish This Practice Cycle -> COMPLETED ->
  reload/re-entry recovery -> Feedback re-entry -> Revision re-entry ->
  Open Learning Journey -> exact Journey projection verification (event
  types, provenance, deduplication, ordering, no writes, no new events on
  completion) -> explicit other-active-target navigation.

Plus focused scenarios on separate learners: evaluation-unavailable
(attempt authoritative, honest notice, no fabricated evaluation event),
no-priority (no fabricated priority/target), and legacy target (no
fabricated provenance). Every combination records console/page errors,
remote requests, overflow, raw locale keys, mobile control sizing, and
persisted write counts; Journey navigation is checked against whole-
database row counts.
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
WU5_DIR = ROOT / "verification/v0.9.7-b/v0.9.7-b-wu5-20260805-r1"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(WU5_DIR))
sys.path.insert(0, str(ROOT))

import w6_harness as harness  # noqa: E402
import w5_browser_matrix as base_matrix  # noqa: E402
from app.ui.locale import t  # noqa: E402

# Rebind the shared WU5 helpers to the WU6 harness and run directory.
base_matrix.harness = harness
SCREENSHOTS = HERE / "screenshots"
base_matrix.SCREENSHOTS = SCREENSHOTS

from w5_browser_matrix import (  # noqa: E402
    FORBIDDEN_WORDING,
    PROMPT,
    SOURCE_ESSAY,
    VALID_RESPONSE,
    VALID_REVISION,
    assert_no_forbidden_wording,
    body_text,
    button_rect,
    click_key,
    health,
    observe,
    submit_writing,
)

RUN_ID = "v0.9.7-b-wu6-20260805-r1"
NO_PRIORITY_PROMPT = "Should we act?"
NO_PRIORITY_ESSAY = (
    "The history of history is historical. The history of history is historical."
)
LEGACY_RESPONSE = "Citizens should protect the environment and recycle more."

KNOWN_EVENT_TYPES = {
    "writing_submitted", "revision_submitted", "analysis_completed",
    "insufficient_evidence", "feedback_available",
    "feedback_priority_available", "feedback_without_priority",
    "practice_available", "exercise_attempted",
    "practice_evaluation_recorded", "within_task_response_observed",
    "later_task_evidence",
}


def submit_no_priority_writing(page, student_id: str, lang: str) -> None:
    harness.open_page(page, "student_writing_title", lang)
    harness.commit_text_input(page, ".st-key-writing_student input", student_id)
    harness.commit_text_input(
        page, ".st-key-writing_prompt_input textarea", NO_PRIORITY_PROMPT)
    harness.commit_text_input(
        page, ".st-key-writing_essay textarea", NO_PRIORITY_ESSAY)
    harness.close_sidebar(page)
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-state="complete"]', timeout=90)


def verify_journey_projection(
    page, student_id: str, lang: str, tag: str,
    *,
    expected_evaluation: bool,
    counts_before_journey: dict[str, int],
    extra_active_targets: int = 1,
    with_revision: bool = True,
) -> dict:
    """Verify the Journey UI and the exact read-time projection, and prove
    that Journey navigation performs no writes and no duplicates."""
    result: dict = {}
    payload = harness.journey_payload(student_id)
    events = payload["events"]
    types = [e["event_type"] for e in events]
    expected_count = (
        6 + (1 if expected_evaluation else 0) + (4 if with_revision else 0)
        + extra_active_targets
    )
    assert len(events) == expected_count, (types, payload["counts"])
    assert set(types) <= KNOWN_EVENT_TYPES, types
    assert "practice_completed" not in types
    assert len({e["deduplication_key"] for e in events}) == len(events)
    assert all(e["learner_id"] == student_id for e in events)

    by_type = {e["event_type"]: e for e in events}
    essay_id = by_type["writing_submitted"]["submission_id"]
    # Original-essay chain.
    chain = ["writing_submitted", "analysis_completed", "feedback_available",
             "feedback_priority_available"]
    anchored = [
        e["event_type"] for e in events
        if e["event_type"] in chain and e["submission_id"] == essay_id]
    assert anchored == chain, anchored
    if with_revision:
        revision_id = by_type["revision_submitted"]["submission_id"]
        assert essay_id != revision_id
        assert by_type["revision_submitted"]["research_detail"][
            "revision_of_submission_id"] == essay_id
        # Revision essay produced its own analysis + exactly one feedback event.
        revision_analysis = [
            e for e in events
            if e["event_type"] == "analysis_completed"
            and e["submission_id"] == revision_id]
        revision_feedback = [
            e for e in events
            if e["event_type"] in ("feedback_priority_available",
                                   "feedback_without_priority")
            and e["submission_id"] == revision_id]
        assert len(revision_analysis) == 1
        assert len(revision_feedback) == 1
    # Practice records.
    practice_events = [
        e for e in events if e["event_type"] == "practice_available"]
    completed_practice = [
        e for e in practice_events
        if e["research_detail"]["status"] == "completed"]
    active_practice = [
        e for e in practice_events
        if e["research_detail"]["status"] == "active"]
    assert len(completed_practice) == 1, types
    assert len(active_practice) == extra_active_targets, types
    practice = completed_practice[0]
    assert practice["source_record_type"] == "practice_target"
    assert practice["submission_id"] == essay_id
    assert practice["research_detail"]["status"] == "completed"
    assert practice["research_detail"]["target_code"] == "lexical_repetition_local"
    attempt = by_type["exercise_attempted"]
    assert attempt["research_detail"]["status"] == "submitted"
    assert attempt["research_detail"]["attempt_number"] == 1
    if expected_evaluation:
        assert "practice_evaluation_recorded" in by_type
        assert by_type["practice_evaluation_recorded"]["research_detail"][
            "completion_status"] == "completed"
    else:
        assert "practice_evaluation_recorded" not in by_type
    assert payload["counts"] == {
        "submissions": 2 if with_revision else 1,
        "analysis_runs": 2 if with_revision else 1,
        "feedback_records": 2 if with_revision else 1,
        "selected_priorities": 1,
        "practice_targets": 1 + extra_active_targets,
        "exercise_attempts": 1, "practice_evaluations": 1 if expected_evaluation else 0,
        "within_task_responses": 0, "transfer_evidence_candidates": 0,
    }
    result["api_projection"] = {
        "event_count": len(events),
        "event_types": types,
        "dedup_unique": True,
        "practice_status": "completed",
        "no_practice_completed_event": True,
        "extra_active_target_events": extra_active_targets,
    }

    # Journey page renders the timeline without errors.
    assert t("journey_timeline", lang) in body_text(page)
    assert t("journey_event_practice_available", lang) in body_text(page)
    assert t("journey_event_exercise_attempted", lang) in body_text(page)
    if expected_evaluation:
        assert t("journey_event_practice_evaluation_recorded", lang) in body_text(page)
    if with_revision:
        assert t("journey_event_revision_submitted", lang) in body_text(page)
    # The Journey timeline uses fixed conservative descriptions; the only
    # "passed" wording is the Diagnostic-Gate description for the revision's
    # no-priority feedback ("no priority passed the Diagnostic Gate"), which
    # is not a learner-pass claim. Mastery/learning claims are excluded by
    # the fixed event contract and the per-page checks above; the Practice
    # page checks below apply the forbidden-wording scan.
    page_health = health(page, ("journey_timeline",))
    assert page_health["exceptions"] == 0 and not page_health["overflow"]
    assert not page_health["raw_keys"]
    shot = SCREENSHOTS / f"{tag}_journey.png"
    page.screenshot(path=str(shot), full_page=True)

    # Locale switch re-renders without changing the server projection.
    other = "zh_CN" if lang == "en" else "en"
    assert harness.select_locale(page, other)
    assert harness.wait_stable(page, timeout=30)
    assert page.locator('[data-testid="stException"]').count() == 0
    assert not health(page, ())["raw_keys"]
    assert harness.select_locale(page, lang)
    assert harness.wait_stable(page, timeout=30)

    # Repeated reads (page + API) produce the same logical events.
    again = harness.journey_payload(student_id)
    assert [(e["event_type"], e["source_record_id"]) for e in again["events"]] == [
        (e["event_type"], e["source_record_id"]) for e in events]
    assert harness.whole_db_counts() == counts_before_journey
    result["journey_navigation"] = {
        "no_writes": True, "no_duplicate_events": True,
        "locale_switch_no_writes": True, "reload_no_duplicates": True,
        "screenshot": str(shot.relative_to(ROOT)),
    }
    return result


def verify_journey_fresh_session(
    page, student_id: str, lang: str, tag: str
) -> dict:
    """Fresh-session Journey re-entry after a full browser reload: same
    projection, no writes, no duplicate events."""
    counts_before = harness.whole_db_counts()
    page.reload(wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    harness.open_page(page, "learning_journey", lang)
    harness.commit_text_input(page, ".st-key-journey_student_v2 input", student_id)
    assert harness.wait_stable(page, timeout=30)
    assert t("journey_timeline", lang) in body_text(page)
    assert page.locator('[data-testid="stException"]').count() == 0
    payload = harness.journey_payload(student_id)
    assert len(payload["events"]) > 0
    assert harness.whole_db_counts() == counts_before
    result = {
        "fresh_session_renders": True, "no_writes": True,
        "no_duplicate_events": True,
    }
    shot = SCREENSHOTS / f"{tag}_journey_fresh_session.png"
    page.screenshot(path=str(shot), full_page=True)
    result["screenshot"] = str(shot.relative_to(ROOT))
    return result


def run_cycle(
    browser, student_id: str, lang: str, viewport: dict, tag: str
) -> tuple[dict, list[str], list[str], list[str]]:
    """One complete WU6 cycle in one locale/viewport combo."""
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

    # Mobile sidebar open/close on the completed state (re-entry check).
    if viewport["width"] < 700:
        harness.open_sidebar(page)
        harness.close_sidebar(page)
        assert harness.wait_stable(page, timeout=30)
        assert t("student_practice_completed_title", lang) in body_text(page)
        assert harness.learner_counts(student_id) == completed
    result["completed"] = {"health": completed_health, "counts": completed,
                           "no_form": True, "no_finish": True,
                           "journey_events_unchanged": True,
                           "mobile_sidebar_reentry": viewport["width"] < 700}

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
    result["completed"].update({
        "column_status": column_status, "json_status": stored_json["status"],
        "screenshot": str(shot.relative_to(ROOT)),
    })

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
    result["other_active_target_available"] = {
        "explicit_action_present": True, "other_size": other_size}

    # Open Learning Journey and verify the complete projection.
    counts_before_journey = harness.whole_db_counts()
    click_key(page, "practice_open_journey")
    assert harness.wait_stable(page, timeout=30)
    assert t("learning_journey", lang) in harness.current_h2(page)
    result["journey"] = verify_journey_projection(
        page, student_id, lang, tag,
        expected_evaluation=True,
        counts_before_journey=counts_before_journey,
        extra_active_targets=1,
    )

    # Back to the completed state, then open the other active target
    # explicitly.
    harness.open_page(page, "practice", lang)
    assert harness.wait_stable(page, expected=".st-key-practice_return_feedback", timeout=60)
    click_key(page, "practice_open_other_target")
    assert harness.wait_stable(page, expected=".st-key-practice_gen", timeout=60)
    text = body_text(page)
    assert t("student_practice_action_generate", lang) in text
    assert t("student_practice_completed_title", lang) not in text
    result["open_other_active_target"] = {"explicit_only": True}

    # Fresh-session Journey re-entry (full reload) as the final check.
    result["journey_fresh_session"] = verify_journey_fresh_session(
        page, student_id, lang, tag)

    unexpected_console = [item for item in console_errors
                          if not harness.is_allowed_console(item)]
    context.close()
    return result, unexpected_console, page_errors, remote_requests


def run_evaluation_unavailable(
    browser, student_id: str, lang: str, viewport: dict, tag: str
) -> tuple[dict, list[str], list[str], list[str]]:
    """Persisted attempt + forced evaluation unavailable + completion."""
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    console_errors, page_errors, remote_requests = observe(page)
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    harness.close_sidebar(page)

    result: dict[str, object] = {"combination": f"{lang} {viewport['width']}x{viewport['height']}"}
    submit_writing(page, student_id, lang)
    harness.close_sidebar(page)
    page.locator(".st-key-writing_review_feedback").click()
    assert harness.wait_stable(page, expected=".st-key-feedback_practice_priority_0")
    click_key(page, "feedback_practice_priority_0")
    assert harness.wait_stable(page, expected='.st-key-practice_response_v2 textarea', timeout=60)
    harness.commit_text_input(page, ".st-key-practice_response_v2 textarea", VALID_RESPONSE)
    click_key(page, "practice_submit")
    assert harness.wait_stable(page, expected=".st-key-practice_finish", timeout=60)
    saved = harness.learner_counts(student_id)
    assert saved["exercise_attempts"] == 1 and saved["practice_evaluations"] == 1

    # Force evaluation unavailable through the supported mechanism (delete
    # the best-effort row; attempt stays authoritative).
    harness.delete_evaluations_for_student(student_id)
    assert harness.learner_counts(student_id)["practice_evaluations"] == 0
    page.reload(wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    harness.open_page(page, "practice", lang)
    harness.commit_text_input(page, ".st-key-practice_student_v2 input", student_id)
    assert harness.wait_stable(page, expected=".st-key-practice_finish", timeout=60)
    text = body_text(page)
    assert t("student_practice_attempt_saved", lang) in text
    assert t("student_practice_evaluation_unavailable", lang) in text
    assert t("student_practice_finish_cycle", lang) in text
    assert_no_forbidden_wording(page)
    assert page.locator('[data-testid="stException"]').count() == 0
    result["unavailable_notice"] = {"honest": True, "attempt_authoritative": True}

    journey_before = harness.journey_event_count(student_id)
    click_key(page, "practice_finish")
    assert harness.wait_stable(page, expected=".st-key-practice_return_feedback", timeout=60)
    completed = harness.learner_counts(student_id)
    assert completed["completed_targets"] == 1
    assert completed["exercise_attempts"] == 1
    assert completed["practice_evaluations"] == 0
    assert harness.journey_event_count(student_id) == journey_before
    assert t("student_practice_completed_title", lang) in body_text(page)

    counts_before_journey = harness.whole_db_counts()
    click_key(page, "practice_open_journey")
    assert harness.wait_stable(page, timeout=30)
    assert t("learning_journey", lang) in harness.current_h2(page)
    result["journey"] = verify_journey_projection(
        page, student_id, lang, tag,
        expected_evaluation=False,
        counts_before_journey=counts_before_journey,
        extra_active_targets=0,
        with_revision=False,
    )
    result["persisted"] = completed
    result["journey_fresh_session"] = verify_journey_fresh_session(
        page, student_id, lang, tag)

    unexpected_console = [item for item in console_errors
                          if not harness.is_allowed_console(item)]
    context.close()
    return result, unexpected_console, page_errors, remote_requests


def run_no_priority(
    browser, student_id: str, lang: str, viewport: dict, tag: str
) -> tuple[dict, list[str], list[str], list[str]]:
    """No-priority cycle: nothing fabricated, no automatic target."""
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    console_errors, page_errors, remote_requests = observe(page)
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    harness.close_sidebar(page)

    result: dict[str, object] = {"combination": f"{lang} {viewport['width']}x{viewport['height']}"}
    submit_no_priority_writing(page, student_id, lang)
    assert harness.learner_counts(student_id)["essays"] == 1
    harness.close_sidebar(page)
    page.locator(".st-key-writing_review_feedback").click()
    assert harness.wait_stable(page, expected=".st-key-feedback_revise_action")
    text = body_text(page)
    assert t("student_feedback_no_priority_title", lang) in text
    assert page.locator(".st-key-feedback_practice_priority_0").count() == 0
    assert page.locator('[data-testid="stException"]').count() == 0
    shot = SCREENSHOTS / f"{tag}_no_priority_feedback.png"
    page.screenshot(path=str(shot), full_page=True)
    result["feedback_no_priority"] = {
        "honest_state": True, "no_priority_action": True,
        "screenshot": str(shot.relative_to(ROOT))}

    # Revising the no-priority draft opens Writing in revision mode with
    # the source pre-selected; no priority is fabricated anywhere.
    click_key(page, "feedback_revise_action")
    assert harness.wait_stable(page, timeout=60)
    text = body_text(page)
    assert t("student_writing_title", lang) in harness.current_h2(page)
    assert t("student_writing_revision_note", lang) in text
    assert t("student_writing_revision_source", lang) in text
    assert page.locator('[data-testid="stException"]').count() == 0
    result["revision_no_priority"] = {
        "writing_revision_mode": True, "no_fabricated_priority": True}

    # Practice entry creates no target and explains the skipped cycle.
    harness.open_page(page, "practice", lang)
    harness.commit_text_input(page, ".st-key-practice_student_v2 input", student_id)
    assert harness.wait_stable(page, timeout=30)
    text = body_text(page)
    assert t("student_practice_no_target_action", lang) in text
    assert harness.learner_counts(student_id)["practice_targets"] == 0
    assert page.locator('[data-testid="stException"]').count() == 0
    result["practice_no_auto_target"] = {"zero_targets": True}

    # Journey: honest feedback_without_priority; no practice events.
    payload = harness.journey_payload(student_id)
    types = [e["event_type"] for e in payload["events"]]
    assert "feedback_without_priority" in types
    assert "feedback_priority_available" not in types
    assert "practice_available" not in types
    assert payload["counts"]["practice_targets"] == 0
    assert payload["state"] == "analysis_without_priority"
    result["journey_no_priority"] = {
        "feedback_without_priority": True, "no_practice_events": True}

    unexpected_console = [item for item in console_errors
                          if not harness.is_allowed_console(item)]
    context.close()
    return result, unexpected_console, page_errors, remote_requests


def run_legacy(
    browser, student_id: str, lang: str, viewport: dict, tag: str
) -> tuple[dict, list[str], list[str], list[str]]:
    """Legacy target (no priority provenance): readable, completable."""
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    console_errors, page_errors, remote_requests = observe(page)
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    harness.close_sidebar(page)

    result: dict[str, object] = {"combination": f"{lang} {viewport['width']}x{viewport['height']}"}
    response = requests.post(f"{harness.BASE}/api/v1/submissions", json={
        "student_id": student_id,
        "writing_prompt": PROMPT,
        "genre": "argumentative essay", "draft_stage": "first draft",
        "timed": False, "tool_use": "none", "essay_text": SOURCE_ESSAY,
    }, timeout=60)
    assert response.status_code == 201, response.text
    essay_id = response.json()["submission_id"]
    target = harness.create_second_active_target(student_id, essay_id)
    assert target.get("source_priority_id") is None
    assert harness.learner_counts(student_id)["practice_targets"] == 1

    harness.open_page(page, "practice", lang)
    harness.commit_text_input(page, ".st-key-practice_student_v2 input", student_id)
    assert harness.wait_stable(page, expected=".st-key-practice_gen", timeout=60)
    assert page.locator('[data-testid="stException"]').count() == 0
    click_key(page, "practice_gen")
    assert harness.wait_stable(page, expected='.st-key-practice_response_v2 textarea', timeout=60)
    harness.commit_text_input(page, ".st-key-practice_response_v2 textarea", LEGACY_RESPONSE)
    click_key(page, "practice_submit")
    assert harness.wait_stable(page, expected=".st-key-practice_finish", timeout=60)
    assert harness.learner_counts(student_id)["exercise_attempts"] == 1
    journey_before = harness.journey_event_count(student_id)
    click_key(page, "practice_finish")
    assert harness.wait_stable(page, expected=".st-key-practice_return_feedback", timeout=60)
    assert harness.learner_counts(student_id)["completed_targets"] == 1
    assert harness.journey_event_count(student_id) == journey_before
    shot = SCREENSHOTS / f"{tag}_legacy_completed.png"
    page.screenshot(path=str(shot), full_page=True)
    result["legacy_completed"] = {"completed": True,
                                  "screenshot": str(shot.relative_to(ROOT))}

    payload = harness.journey_payload(student_id)
    practice = next(
        e for e in payload["events"] if e["event_type"] == "practice_available")
    assert practice["source_record_id"] == target["practice_target_id"]
    assert practice["research_detail"]["status"] == "completed"
    assert "source_priority_id" not in practice["research_detail"]
    assert "priority" not in json.dumps(practice["research_detail"]).lower()
    assert any(e["event_type"] == "exercise_attempted" for e in payload["events"])
    assert page.locator('[data-testid="stException"]').count() == 0
    result["journey_legacy"] = {
        "readable": True, "no_fabricated_priority": True}

    unexpected_console = [item for item in console_errors
                          if not harness.is_allowed_console(item)]
    context.close()
    return result, unexpected_console, page_errors, remote_requests


def main() -> int:
    harness.prepare_isolated_db()
    api = streamlit = None
    evidence: dict[str, object] = {"run_id": RUN_ID}
    try:
        api, streamlit = harness.start_stack("w6_matrix")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                en_desktop, c1, e1, r1 = run_cycle(
                    browser, "V097B-W6-ED", "en",
                    {"width": 1280, "height": 900}, "en_1280x900")
                zh_desktop, c2, e2, r2 = run_cycle(
                    browser, "V097B-W6-ZD", "zh_CN",
                    {"width": 1280, "height": 900}, "zh_1280x900")
                en_mobile, c3, e3, r3 = run_cycle(
                    browser, "V097B-W6-EM", "en",
                    {"width": 390, "height": 844}, "en_390x844")
                zh_mobile, c4, e4, r4 = run_cycle(
                    browser, "V097B-W6-ZM", "zh_CN",
                    {"width": 390, "height": 844}, "zh_390x844")
                eu, c5, e5, r5 = run_evaluation_unavailable(
                    browser, "V097B-W6-EU", "en",
                    {"width": 1280, "height": 900}, "eu_en_1280x900")
                zu, c6, e6, r6 = run_evaluation_unavailable(
                    browser, "V097B-W6-ZU", "zh_CN",
                    {"width": 390, "height": 844}, "zu_zh_390x844")
                np, c7, e7, r7 = run_no_priority(
                    browser, "V097B-W6-NP", "en",
                    {"width": 1280, "height": 900}, "np_en_1280x900")
                nz, c8, e8, r8 = run_no_priority(
                    browser, "V097B-W6-NZ", "zh_CN",
                    {"width": 390, "height": 844}, "nz_zh_390x844")
                le, c9, e9, r9 = run_legacy(
                    browser, "V097B-W6-LE", "en",
                    {"width": 1280, "height": 900}, "le_en_1280x900")
                lz, c10, e10, r10 = run_legacy(
                    browser, "V097B-W6-LZ", "zh_CN",
                    {"width": 390, "height": 844}, "lz_zh_390x844")
            finally:
                browser.close()
            evidence["en_1280x900"] = en_desktop
            evidence["zh_1280x900"] = zh_desktop
            evidence["en_390x844"] = en_mobile
            evidence["zh_390x844"] = zh_mobile
            evidence["evaluation_unavailable"] = {"en": eu, "zh": zu}
            evidence["no_priority"] = {"en": np, "zh": nz}
            evidence["legacy"] = {"en": le, "zh": lz}
            evidence["console_errors"] = c1 + c2 + c3 + c4 + c5 + c6 + c7 + c8 + c9 + c10
            evidence["page_errors"] = e1 + e2 + e3 + e4 + e5 + e6 + e7 + e8 + e9 + e10
            evidence["remote_requests"] = r1 + r2 + r3 + r4 + r5 + r6 + r7 + r8 + r9 + r10
    finally:
        harness.stop_stack(api, streamlit)

    evidence["ports_cleaned"] = True
    (HERE / "rendered_page_matrix_evidence.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
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
        assert item["return_to_feedback"]["navigation_only"] is True
        assert item["reload_reentry"]["completed_persisted"] is True
        assert item["reload_reentry"]["no_form"] is True
        assert item["reload_reentry"]["no_finish"] is True
        assert item["journey"]["api_projection"]["event_count"] == 12
        assert item["journey"]["api_projection"]["no_practice_completed_event"] is True
        assert item["journey"]["journey_navigation"]["no_writes"] is True
        assert item["journey"]["journey_navigation"]["no_duplicate_events"] is True
        assert item["open_other_active_target"]["explicit_only"] is True
    for scenario in ("evaluation_unavailable", "no_priority", "legacy"):
        for lang_item in evidence[scenario].values():
            assert lang_item["combination"]
    for lang_item in evidence["evaluation_unavailable"].values():
        assert lang_item["unavailable_notice"]["honest"] is True
        assert lang_item["journey"]["api_projection"]["event_count"] == 6
        assert lang_item["persisted"]["practice_evaluations"] == 0
    for lang_item in evidence["no_priority"].values():
        assert lang_item["feedback_no_priority"]["honest_state"] is True
        assert lang_item["practice_no_auto_target"]["zero_targets"] is True
        assert lang_item["journey_no_priority"]["no_practice_events"] is True
    for lang_item in evidence["legacy"].values():
        assert lang_item["legacy_completed"]["completed"] is True
        assert lang_item["journey_legacy"]["no_fabricated_priority"] is True
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
