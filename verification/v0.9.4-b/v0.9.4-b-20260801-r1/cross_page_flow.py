"""One-learner v0.9.4-B cross-page Student flow in both render modes."""

from __future__ import annotations

import json
import pathlib
import sqlite3
import sys

import requests
from playwright.sync_api import sync_playwright


HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

import v094b_harness as harness  # noqa: E402
from app.database import Database  # noqa: E402
from app.practice.service import PracticeService  # noqa: E402
from app.ui.locale import t  # noqa: E402
from practice_slice import seed_target_via_existing_api  # noqa: E402


SCREENSHOTS = HERE / "screenshots" / "cross_page"
STUDENT = "V094B-CROSS-PAGE"
PROMPT = "How can writers make an argument clear and specific?"
SOURCE_ESSAY = (
    "Writers repeat vague claims, repeat vague claims, and repeat vague claims in one short passage. "
    "Specific evidence can clarify a reason because readers can inspect the support. " * 5
)
SOURCE_SPAN = "Writers repeat vague claims, repeat vague claims, and repeat vague claims."
PRACTICE_RESPONSE = "Writers state one specific claim and support it with evidence readers can inspect."
REVISED_ESSAY = (
    "Writers can make an argument clear by stating one specific claim and supporting it with evidence. "
    "Readers can inspect that evidence, compare it with the reason, and decide whether the conclusion follows. "
    "This revision is one linked record and does not prove learning, mastery, or transfer."
)


def prepare_learner() -> None:
    harness.prepare_isolated_db()
    with sqlite3.connect(harness.ISOLATED_DB) as connection:
        connection.execute(
            "INSERT OR IGNORE INTO students(student_id, created_at, is_synthetic) VALUES(?,?,1)",
            (STUDENT, "2026-08-01T00:00:00+00:00"),
        )
        removed = connection.execute(
            "DELETE FROM within_task_response_candidates WHERE student_id='DEMO-001'"
        ).rowcount
        assert removed == 1
        connection.commit()


def table_counts() -> dict[str, int]:
    with sqlite3.connect(harness.ISOLATED_DB) as connection:
        tables = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()]
        return {
            table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            for table in tables
        }


def learner_summary() -> dict[str, int]:
    with sqlite3.connect(harness.ISOLATED_DB) as connection:
        essays = connection.execute(
            "SELECT essay_id, revision_of_submission_id FROM essays WHERE student_id=? "
            "ORDER BY essay_id", (STUDENT,)
        ).fetchall()
        priorities = 0
        for row in connection.execute(
            "SELECT f.feedback_json FROM feedback_records f JOIN essays e "
            "ON e.essay_id=f.essay_id WHERE e.student_id=?", (STUDENT,)
        ):
            priorities += len(json.loads(row[0]).get("priority_feedback", []))
        return {
            "essays": len(essays),
            "initial_submissions": sum(1 for row in essays if row[1] is None),
            "revisions": sum(1 for row in essays if row[1] is not None),
            "selected_priorities": priorities,
            "targets": int(connection.execute(
                "SELECT COUNT(*) FROM practice_targets WHERE student_id=?", (STUDENT,)
            ).fetchone()[0]),
            "exercises": int(connection.execute(
                "SELECT COUNT(*) FROM exercise_instances WHERE student_id=?", (STUDENT,)
            ).fetchone()[0]),
            "attempts": int(connection.execute(
                "SELECT COUNT(*) FROM exercise_attempts WHERE student_id=?", (STUDENT,)
            ).fetchone()[0]),
            "evaluations": int(connection.execute(
                "SELECT COUNT(*) FROM practice_evaluations pe JOIN exercise_attempts ea "
                "ON ea.attempt_id=pe.attempt_id WHERE ea.student_id=?", (STUDENT,)
            ).fetchone()[0]),
            "revision_groups": int(connection.execute(
                "SELECT COUNT(DISTINCT revision_group_id) FROM essays WHERE student_id=? "
                "AND revision_group_id IS NOT NULL", (STUDENT,)
            ).fetchone()[0]),
            "revision_snapshots": int(connection.execute(
                "SELECT COUNT(*) FROM revision_snapshots rs JOIN essays e "
                "ON e.essay_id=rs.target_submission_id WHERE e.student_id=?", (STUDENT,)
            ).fetchone()[0]),
            "response_observations": int(connection.execute(
                "SELECT COUNT(*) FROM within_task_response_candidates WHERE student_id=?",
                (STUDENT,),
            ).fetchone()[0]),
            "engagement_traces": int(connection.execute(
                "SELECT COUNT(*) FROM feedback_engagement_traces WHERE student_id=?",
                (STUDENT,),
            ).fetchone()[0]),
        }


def persist_authoritative_response_observation() -> dict:
    repository = Database(harness.ISOLATED_DB)
    essays = repository.list_essays_by_student(STUDENT)
    source = next(item for item in essays if item.get("revision_of_submission_id") is None)
    revised = next(item for item in essays if item.get("revision_of_submission_id") is not None)
    target = repository.list_practice_targets(STUDENT)[0]
    group_id = revised.get("revision_group_id")
    snapshot = repository.get_latest_revision_snapshot(group_id)
    assert snapshot is not None
    candidate = PracticeService(repository).evaluate_within_task_response(
        STUDENT,
        target,
        int(source["essay_id"]),
        int(revised["essay_id"]),
        revision_group_id=group_id,
        major_rewrite=bool(snapshot.get("major_rewrite")),
    )
    return repository.save_within_task_response_candidate(candidate)


def api_journey() -> dict:
    response = requests.get(
        f"{harness.BASE}/api/v1/students/{STUDENT}/journey", timeout=20
    )
    assert response.status_code == 200, response.text
    return response.json()


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


def input_value(page, selector: str) -> str:
    locator = page.locator(selector)
    assert locator.count() == 1
    return locator.input_value().strip()


def page_health(page) -> dict[str, object]:
    width = page.evaluate("() => window.innerWidth")
    return {
        "exceptions": page.locator('[data-testid="stException"]').count(),
        "overflow": page.evaluate("() => document.documentElement.scrollWidth") > width,
        "main_max_width": page.locator('[data-testid="stMainBlockContainer"]').first.evaluate(
            "el => getComputedStyle(el).maxWidth"
        ),
    }


def bilingual_checkpoint(
    page,
    title_key: str,
    learner_selector: str,
    expected_selector: str,
    slug: str,
) -> dict[str, object]:
    before = table_counts()
    page.set_viewport_size({"width": 390, "height": 844})
    assert harness.select_locale(page, "zh_CN")
    open_page(page, title_key, "zh_CN")
    assert harness.wait_stable(page, expected=expected_selector)
    assert input_value(page, learner_selector) == STUDENT
    health = page_health(page)
    assert health == {"exceptions": 0, "overflow": False, "main_max_width": "720px"}
    primary = page.locator('[data-testid="stBaseButton-primary"]')
    primary_size = None
    if primary.count():
        primary_size = primary.first.evaluate(
            "el => { const r=el.getBoundingClientRect(); return {width:r.width,height:r.height}; }"
        )
        assert primary_size["width"] >= 44 and primary_size["height"] >= 44
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    shot = SCREENSHOTS / f"{slug}_zh_CN_390x844.png"
    page.screenshot(path=str(shot), full_page=True)
    assert table_counts() == before

    assert harness.select_locale(page, "en")
    page.set_viewport_size({"width": 1280, "height": 900})
    open_page(page, title_key, "en")
    assert harness.wait_stable(page, expected=expected_selector)
    assert input_value(page, learner_selector) == STUDENT
    assert table_counts() == before
    return {
        "health": health,
        "primary_size": primary_size,
        "screenshot": str(shot.relative_to(ROOT)),
        "counts_stable": table_counts() == before,
    }


def run_flow(browser) -> tuple[dict, list[str], list[str]]:
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    console_errors, page_errors = observe_errors(page)
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    evidence: dict[str, object] = {"bilingual_pages": {}}

    open_page(page, "student_home_title", "en")
    harness.commit_text_input(page, '.st-key-home_student input', STUDENT)
    assert harness.wait_stable(page, expected='[data-testid="px-student-steps"]')
    assert t("student_home_no_submissions", "en") in page.locator("body").inner_text()
    assert page.locator('[data-testid="stBaseButton-primary"]').count() == 1
    evidence["bilingual_pages"]["home_initial"] = bilingual_checkpoint(
        page, "student_home_title", '.st-key-home_student input',
        '[data-testid="px-student-steps"]', "home_initial",
    )

    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='.st-key-writing_essay textarea')
    assert input_value(page, '.st-key-writing_student input') == STUDENT
    harness.commit_text_input(page, '.st-key-writing_prompt_input textarea', PROMPT)
    harness.commit_text_input(page, '.st-key-writing_essay textarea', SOURCE_ESSAY)
    before_source = table_counts()
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-state="complete"]', timeout=60)
    assert learner_summary()["initial_submissions"] == 1
    assert table_counts()["essays"] - before_source["essays"] == 1
    evidence["bilingual_pages"]["writing_saved"] = bilingual_checkpoint(
        page, "student_writing_title", '.st-key-writing_student input',
        '[data-state="complete"]', "writing_saved",
    )

    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-testid="px-feedback-priority"]')
    assert input_value(page, '.st-key-feedback_student input') == STUDENT
    assert page.locator('[data-testid="px-feedback-priority"]').count() == 1
    assert learner_summary()["selected_priorities"] == 1
    evidence["bilingual_pages"]["feedback_priority"] = bilingual_checkpoint(
        page, "student_feedback_title", '.st-key-feedback_student input',
        '[data-testid="px-feedback-priority"]', "feedback_priority",
    )

    before_target = table_counts()
    target = seed_target_via_existing_api(STUDENT)
    assert target.get("status") == "active"
    assert table_counts()["practice_targets"] - before_target["practice_targets"] == 1
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='.st-key-practice_source_v2 textarea')
    assert input_value(page, '.st-key-practice_student_v2 input') == STUDENT
    harness.commit_text_input(page, '.st-key-practice_source_v2 textarea', SOURCE_SPAN)
    before_exercise = table_counts()
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='.st-key-practice_response_v2 textarea')
    assert table_counts()["exercise_instances"] - before_exercise["exercise_instances"] == 1
    harness.commit_text_input(page, '.st-key-practice_response_v2 textarea', PRACTICE_RESPONSE)
    before_attempt = table_counts()
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='.px-notice-success[data-testid="px-notice"]')
    after_attempt = table_counts()
    assert after_attempt["exercise_attempts"] - before_attempt["exercise_attempts"] == 1
    assert after_attempt["practice_evaluations"] - before_attempt["practice_evaluations"] == 1
    evidence["bilingual_pages"]["practice_completed"] = bilingual_checkpoint(
        page, "practice", '.st-key-practice_student_v2 input',
        '.px-notice-success[data-testid="px-notice"]', "practice_completed",
    )

    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='.st-key-revision_text_input textarea')
    assert input_value(page, '.st-key-revision_student input') == STUDENT
    assert t("student_revision_feedback_focus", "en") in page.locator("body").inner_text()
    harness.commit_text_input(page, '.st-key-revision_text_input textarea', REVISED_ESSAY)
    before_revision = table_counts()
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-state="complete"]', timeout=60)
    after_revision = table_counts()
    assert after_revision["essays"] - before_revision["essays"] == 1
    assert after_revision["revision_groups"] - before_revision["revision_groups"] == 1
    assert after_revision["revision_snapshots"] - before_revision["revision_snapshots"] == 1
    evidence["bilingual_pages"]["revision_saved"] = bilingual_checkpoint(
        page, "student_revision_title", '.st-key-revision_student input',
        '[data-state="complete"]', "revision_saved",
    )

    before_observation = table_counts()
    observation = persist_authoritative_response_observation()
    assert observation.get("response_id")
    assert table_counts()["within_task_response_candidates"] - before_observation[
        "within_task_response_candidates"
    ] == 1
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-testid="px-timeline-event"]')
    assert input_value(page, '.st-key-journey_student_v2 input') == STUDENT
    first_journey = api_journey()
    second_journey = api_journey()
    first_keys = [item["deduplication_key"] for item in first_journey["events"]]
    second_keys = [item["deduplication_key"] for item in second_journey["events"]]
    assert first_keys == second_keys and len(first_keys) == len(set(first_keys))
    assert any(item["event_type"] == "within_task_response_observed" for item in first_journey["events"])
    journey_counts = table_counts()
    evidence["bilingual_pages"]["journey_complete"] = bilingual_checkpoint(
        page, "learning_journey", '.st-key-journey_student_v2 input',
        '[data-testid="px-timeline-event"]', "journey_complete",
    )
    assert table_counts() == journey_counts

    open_page(page, "student_home_title", "en")
    assert input_value(page, '.st-key-home_student input') == STUDENT
    assert t("student_home_latest_status", "en") in page.locator("body").inner_text()
    evidence["home_final_oriented"] = True

    before_switch = table_counts()
    open_page(page, "student_feedback_title", "en")
    assert input_value(page, '.st-key-feedback_student input') == STUDENT
    assert page.locator('[data-testid="px-mono"]').count() >= 1
    harness.commit_text_input(page, '.st-key-feedback_student input', "EMPTY01")
    assert harness.wait_stable(page, expected='[data-testid="px-empty-state"]')
    assert page.locator('[data-testid="px-feedback-priority"]').count() == 0
    assert page.locator('[data-testid="px-mono"]').count() == 0
    assert STUDENT not in page.locator('[data-testid="stMainBlockContainer"]').inner_text()
    assert table_counts() == before_switch
    evidence["learner_switch_cleared_stale_state"] = True

    final = learner_summary()
    expected = {
        "essays": 2,
        "initial_submissions": 1,
        "revisions": 1,
        "selected_priorities": 1,
        "targets": 1,
        "exercises": 1,
        "attempts": 1,
        "evaluations": 1,
        "revision_groups": 1,
        "revision_snapshots": 1,
        "response_observations": 1,
        "engagement_traces": 0,
    }
    assert final == expected
    evidence["final_counts"] = final
    evidence["journey_event_count"] = len(first_keys)
    evidence["journey_dedup_keys_stable"] = first_keys == second_keys
    evidence["no_duplicate_writes"] = table_counts() == before_switch
    body = page.locator("body").inner_text().lower()
    for forbidden in (
        "has mastered", "proficiency increased", "learning gain achieved",
        "transfer achieved", "feedback caused improvement",
    ):
        assert forbidden not in body
    evidence["unsupported_claims"] = []

    unexpected = [item for item in console_errors if not harness.is_allowed_console(item)]
    context.close()
    return evidence, unexpected, page_errors


def main() -> int:
    prepare_learner()
    api = streamlit = None
    evidence: dict[str, object] = {"run_id": "v0.9.4-b-20260801-r1"}
    try:
        api, streamlit = harness.start_stack("cross_page_flow")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            flow, console_errors, page_errors = run_flow(browser)
            evidence.update(flow)
            evidence["console_errors"] = console_errors
            evidence["page_errors"] = page_errors
            browser.close()
    finally:
        harness.stop_stack(api, streamlit)
    evidence["ports_cleaned"] = True
    (HERE / "cross_page_flow_evidence.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    assert not evidence["console_errors"] and not evidence["page_errors"]
    assert evidence["learner_switch_cleared_stale_state"]
    assert evidence["final_counts"]["engagement_traces"] == 0
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
