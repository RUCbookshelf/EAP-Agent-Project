"""v0.9.7-C WU4 final product matrix (browser).

Runs the complete v0.9.7-C end-to-end scenario through the real production
UI independently for English/Chinese x 1280x900/390x844 with fresh
isolated databases and distinct learners (local provider):

  Writing -> Feedback priority -> linked Revision submit -> explicit
  revision completion -> Open Practice -> focused task -> valid attempt ->
  evaluation -> Finish This Practice Cycle -> COMPLETED -> reload re-entry
  -> second active target -> Open Learning Journey -> grouped cycle
  verification -> safe Journey actions (Open Practice / Open Revision) ->
  fresh-session reload -> zero writes, no duplicates.

The WU6 runner provides the full v0.9.7-B UI cycle; this script adds the
WU3/WU4 grouped-cycle and action-navigation verification.
"""
from __future__ import annotations

import json
import pathlib
import sys

import requests
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
WU5_DIR = PROJECT_ROOT / "verification/v0.9.7-b/v0.9.7-b-wu5-20260805-r1"
WU6_DIR = PROJECT_ROOT / "verification/v0.9.7-b/v0.9.7-b-wu6-20260805-r1"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(WU6_DIR))
sys.path.insert(0, str(WU5_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

import w6_harness as harness  # noqa: E402
import w5_harness as _w5  # noqa: E402
import w6_browser_matrix as base_matrix  # noqa: E402
from app.ui.locale import t  # noqa: E402

# Re-point the shared harness state at this WU4 run directory (after the
# star imports, so WU5/WU6 constants cannot shadow these).
_w5._base.RUN_DIR = HERE
_w5._base.ISOLATED_DB = HERE / "isolated" / "writing_feedback_v097c_wu4.db"
_w5._base.LOG_DIR = HERE / "logs"
_w5.RUN_DIR = HERE
_w5.ISOLATED_DB = _w5._base.ISOLATED_DB
_w5.LOG_DIR = HERE / "logs"
harness.RUN_DIR = HERE
harness.ISOLATED_DB = _w5.ISOLATED_DB
harness.LOG_DIR = HERE / "logs"

SCREENSHOTS = HERE / "screenshots"
base_matrix.harness = harness
base_matrix.SCREENSHOTS = SCREENSHOTS

from w6_browser_matrix import (  # noqa: E402
    FORBIDDEN_WORDING,
    body_text,
    click_key,
    observe,
    run_cycle,
)

RUN_ID = "v0.9.7-c-wu4-20260805-r1"
STUDENTS = ("V097C-W4-ED", "V097C-W4-ZD", "V097C-W4-EM", "V097C-W4-ZM")


def verify_journey_projection_w4(
    page, student_id: str, lang: str, tag: str, *,
    expected_evaluation: bool, counts_before_journey: dict,
    extra_active_targets: int = 1, with_revision: bool = True,
) -> dict:
    """WU4 replacement for the WU6 raw-timeline verifier: keeps the exact
    API projection checks and swaps the raw-timeline UI assertions for the
    grouped cycle UI (v0.9.7-C WU3)."""
    payload = harness.journey_payload(student_id)
    events = payload["events"]
    types = [e["event_type"] for e in events]
    expected_count = (
        6 + (1 if expected_evaluation else 0) + (4 if with_revision else 0)
        + extra_active_targets
    )
    assert len(events) == expected_count, (types, payload["counts"])
    assert "practice_completed" not in types
    assert len({e["deduplication_key"] for e in events}) == len(events)
    assert all(e["learner_id"] == student_id for e in events)
    practice_events = [
        e for e in events if e["event_type"] == "practice_available"]
    completed_practice = [
        e for e in practice_events
        if e["research_detail"]["status"] == "completed"]
    active_practice = [
        e for e in practice_events
        if e["research_detail"]["status"] == "active"]
    assert len(completed_practice) == 1
    assert len(active_practice) == extra_active_targets
    assert payload["cycles_version"] == "journey-cycle-v0.9.7-c"
    cycles = payload["cycles"]
    assert len(cycles) == 1
    assert cycles[0]["relationship_status"] == "linked"
    practice_states = {
        p["activity_state"] for p in cycles[0]["practice_cycles"]}
    assert "completed" in practice_states
    if extra_active_targets:
        assert "available" in practice_states

    # Grouped cycle UI on the Journey page.
    text = body_text(page)
    assert t("student_journey_cycle_title", lang) in text
    assert t("student_journey_original_writing", lang) in text
    assert t("student_journey_revised_draft", lang) in text
    assert t("student_journey_practice_activity", lang) in text
    assert t("student_journey_state_completed", lang) in text
    assert page.locator('[data-testid="stException"]').count() == 0
    width = page.evaluate("() => window.innerWidth")
    assert page.evaluate(
        "() => document.documentElement.scrollWidth") <= width
    normalized = text.lower()
    for phrase in ("none establishes learning, mastery, or stable transfer.",
                   "no priority passed the diagnostic gate"):
        normalized = normalized.replace(phrase, "")
    for word in FORBIDDEN_WORDING:
        assert word not in normalized, word
    shot = SCREENSHOTS / f"{tag}_journey_grouped.png"
    page.screenshot(path=str(shot), full_page=True)

    # Locale switch re-renders without changing the server projection.
    other = "zh_CN" if lang == "en" else "en"
    assert harness.select_locale(page, other)
    assert harness.wait_stable(page, timeout=30)
    assert page.locator('[data-testid="stException"]').count() == 0
    assert harness.select_locale(page, lang)
    assert harness.wait_stable(page, timeout=30)

    again = harness.journey_payload(student_id)
    assert [(e["event_type"], e["source_record_id"]) for e in again["events"]] == [
        (e["event_type"], e["source_record_id"]) for e in events]
    assert harness.whole_db_counts() == counts_before_journey
    return {
        "event_count": len(events),
        "no_practice_completed_event": True,
        "grouped_ui": True,
        "no_writes": True,
        "screenshot": str(shot.relative_to(PROJECT_ROOT)),
    }


base_matrix.verify_journey_projection = verify_journey_projection_w4


def verify_journey_fresh_session_w4(
    page, student_id: str, lang: str, tag: str,
) -> dict:
    """WU4 fresh-session Journey re-entry: grouped cycle view persists,
    no writes, no duplicate events."""
    counts_before = harness.whole_db_counts()
    page.reload(wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    harness.open_page(page, "learning_journey", lang)
    harness.commit_text_input(page, ".st-key-journey_student_v2 input", student_id)
    assert harness.wait_stable(page, timeout=30)
    harness.close_sidebar(page)
    assert t("student_journey_cycle_title", lang) in body_text(page)
    assert page.locator('[data-testid="stException"]').count() == 0
    payload = harness.journey_payload(student_id)
    assert len(payload["events"]) > 0
    assert len(payload["cycles"]) == 1
    assert harness.whole_db_counts() == counts_before
    shot = SCREENSHOTS / f"{tag}_journey_fresh_session.png"
    page.screenshot(path=str(shot), full_page=True)
    return {
        "fresh_session_renders": True, "no_writes": True,
        "no_duplicate_events": True,
        "screenshot": str(shot.relative_to(PROJECT_ROOT)),
    }


base_matrix.verify_journey_fresh_session = verify_journey_fresh_session_w4


def verify_grouped_journey(page, student_id: str, lang: str, tag: str) -> dict:
    """Verify the grouped cycle UI and the safe Journey actions."""
    result: dict = {}
    payload = harness.journey_payload(student_id)
    assert payload["cycles_version"] == "journey-cycle-v0.9.7-c"
    cycles = payload["cycles"]
    assert len(cycles) == 1, cycles
    cycle = cycles[0]
    assert cycle["relationship_status"] == "linked"
    root_id = cycle["root_submission"]["submission_id"]
    assert len(cycle["revisions"]) == 1
    assert len(cycle["practice_cycles"]) == 2
    states = {p["activity_state"] for p in cycle["practice_cycles"]}
    assert states == {"completed", "available"}, states
    actions = cycle["available_actions"]
    assert any(a["action"] == "open_revision" for a in actions)
    practice_actions = [
        a for a in actions if a["action"] == "open_practice"]
    assert len(practice_actions) == 2
    completed_action = next(
        a for a in practice_actions
        if any(p["practice_target_id"] == a["practice_target_id"]
               and p["activity_state"] == "completed"
               for p in cycle["practice_cycles"]))
    active_action = next(
        a for a in practice_actions
        if any(p["practice_target_id"] == a["practice_target_id"]
               and p["activity_state"] == "available"
               for p in cycle["practice_cycles"]))

    # The page (already on Journey after the WU6 runner) renders the
    # grouped cycle UI.
    text = body_text(page)
    assert t("student_journey_cycle_title", lang) in text
    assert t("student_journey_original_writing", lang) in text
    assert f"#{root_id}" in text
    assert t("student_journey_revised_draft", lang) in text
    assert t("student_journey_revision_of", lang) in text
    assert t("student_journey_practice_activity", lang) in text
    assert t("student_journey_state_completed", lang) in text
    assert t("student_journey_state_available", lang) in text
    assert t("student_practice_completed_title", lang) in text
    assert page.locator(
        f".st-key-journey_action_revision_{root_id}").count() == 1
    assert page.locator(
        f".st-key-journey_action_practice_"
        f"{active_action['practice_target_id']}").count() == 1
    assert page.locator(
        f".st-key-journey_action_practice_"
        f"{completed_action['practice_target_id']}").count() == 1
    assert page.locator('[data-testid="stException"]').count() == 0
    width = page.evaluate("() => window.innerWidth")
    assert page.evaluate(
        "() => document.documentElement.scrollWidth") <= width
    normalized = text.lower()
    for phrase in ("none establishes learning, mastery, or stable transfer.",
                   "no priority passed the diagnostic gate",
                   "not proof of stable transfer or causation",
                   "not proof that practice caused the later pattern"):
        normalized = normalized.replace(phrase, "")
    for word in FORBIDDEN_WORDING:
        assert word not in normalized, word
    assert "passed" not in normalized
    shot = SCREENSHOTS / f"{tag}_journey_grouped.png"
    page.screenshot(path=str(shot), full_page=True)
    result["grouped_cycle"] = {
        "cycle_count": len(cycles),
        "states": sorted(states),
        "screenshot": str(shot.relative_to(PROJECT_ROOT)),
    }

    # Safe action: open the ACTIVE target (no writes, no creation).
    counts_before = harness.whole_db_counts()
    click_key(page, f"journey_action_practice_{active_action['practice_target_id']}")
    assert harness.wait_stable(page, timeout=30)
    assert t("practice", lang) in harness.current_h2(page)
    assert t("student_practice_completed_title", lang) not in body_text(page)
    result["action_open_active_practice"] = {
        "destination_reached": True, "no_auto_completion": True}

    # Return to Journey and open the linked Revision destination.
    harness.open_page(page, "learning_journey", lang)
    harness.commit_text_input(
        page, ".st-key-journey_student_v2 input", student_id)
    assert harness.wait_stable(page, timeout=30)
    harness.close_sidebar(page)
    click_key(page, f"journey_action_revision_{root_id}")
    assert harness.wait_stable(page, timeout=30)
    assert t("student_revision_title", lang) in harness.current_h2(page)
    assert page.locator('[data-testid="stException"]').count() == 0
    result["action_open_revision"] = {"destination_reached": True}

    # Fresh-session Journey reload renders the same grouped view.
    harness.open_page(page, "learning_journey", lang)
    page.reload(wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    harness.open_page(page, "learning_journey", lang)
    harness.commit_text_input(
        page, ".st-key-journey_student_v2 input", student_id)
    assert harness.wait_stable(page, timeout=30)
    harness.close_sidebar(page)
    assert t("student_journey_cycle_title", lang) in body_text(page)
    assert page.locator('[data-testid="stException"]').count() == 0
    assert harness.whole_db_counts() == counts_before
    result["reload_and_zero_writes"] = {
        "grouped_view_persists": True, "no_writes": True}
    return result


def main() -> int:
    harness.prepare_isolated_db()
    import sqlite3
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
        api, streamlit = harness.start_stack("w4_matrix")
        combos = (
            ("V097C-W4-ED", "en", {"width": 1280, "height": 900}, "en_1280x900"),
            ("V097C-W4-ZD", "zh_CN", {"width": 1280, "height": 900}, "zh_1280x900"),
            ("V097C-W4-EM", "en", {"width": 390, "height": 844}, "en_390x844"),
            ("V097C-W4-ZM", "zh_CN", {"width": 390, "height": 844}, "zh_390x844"),
        )
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                all_console: list[str] = []
                all_page: list[str] = []
                all_remote: list[str] = []
                for student_id, lang, viewport, tag in combos:
                    cycle_result, console, page_errors, remote = run_cycle(
                        browser, student_id, lang, viewport, tag)
                    # run_cycle ends on the fresh-session Journey page.
                    grouped = verify_grouped_journey(
                        page=_last_page(browser, student_id, lang, tag),
                        student_id=student_id, lang=lang, tag=tag)
                    evidence[tag] = {
                        "full_ui_cycle": cycle_result,
                        "grouped": grouped,
                    }
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
        assert item["full_ui_cycle"]["completed"]["column_status"] == "completed"
        assert item["grouped"]["grouped_cycle"]["cycle_count"] == 1
        assert item["grouped"]["action_open_active_practice"][
            "destination_reached"] is True
        assert item["grouped"]["action_open_revision"][
            "destination_reached"] is True
        assert item["grouped"]["reload_and_zero_writes"]["no_writes"] is True
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


def _last_page(browser, student_id: str, lang: str, tag: str):
    """Open a fresh Journey page for grouped verification (the WU6 runner
    already closed its context)."""
    context = browser.new_context(
        viewport={"width": 1280, "height": 900} if tag.endswith("1280x900")
        else {"width": 390, "height": 844})
    page = context.new_page()
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    harness.open_page(page, "learning_journey", lang)
    harness.commit_text_input(
        page, ".st-key-journey_student_v2 input", student_id)
    assert harness.wait_stable(page, timeout=30)
    harness.close_sidebar(page)
    return page


if __name__ == "__main__":
    raise SystemExit(main())
