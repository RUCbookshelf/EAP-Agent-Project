"""Focused v0.9.4-B Practice verification with isolated persistence."""

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
from app.ui.locale import t  # noqa: E402


SCREENSHOTS = HERE / "screenshots"
STUDENT = "V094B-PRACTICE-ACTIVE"
PROMPT = "How can writers make an argument clear and specific?"
PRIORITY_ESSAY = (
    "Writers repeat vague claims, repeat vague claims, and repeat vague claims in one short passage. "
    "Specific evidence can clarify a reason because readers can inspect the support. " * 5
)
SOURCE_TEXT = "Writers repeat vague claims, repeat vague claims, and repeat vague claims."
RESPONSE = "Writers state one specific claim and support it with evidence readers can inspect."


def table_counts() -> dict[str, int]:
    with sqlite3.connect(harness.ISOLATED_DB) as connection:
        tables = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()]
        return {
            table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            for table in tables
        }


def learner_counts(student_id: str) -> dict[str, int]:
    with sqlite3.connect(harness.ISOLATED_DB) as connection:
        return {
            "targets": int(connection.execute(
                "SELECT COUNT(*) FROM practice_targets WHERE student_id=?", (student_id,)
            ).fetchone()[0]),
            "exercises": int(connection.execute(
                "SELECT COUNT(*) FROM exercise_instances WHERE student_id=?", (student_id,)
            ).fetchone()[0]),
            "attempts": int(connection.execute(
                "SELECT COUNT(*) FROM exercise_attempts WHERE student_id=?", (student_id,)
            ).fetchone()[0]),
            "evaluations": int(connection.execute(
                "SELECT COUNT(*) FROM practice_evaluations pe "
                "JOIN exercise_attempts ea ON ea.attempt_id=pe.attempt_id "
                "WHERE ea.student_id=?", (student_id,)
            ).fetchone()[0]),
        }


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


def submit_priority(page) -> None:
    open_page(page, "student_writing_title", "en")
    harness.commit_text_input(page, '.st-key-writing_student input', STUDENT)
    harness.commit_text_input(page, '.st-key-writing_prompt_input textarea', PROMPT)
    harness.commit_text_input(page, '.st-key-writing_essay textarea', PRIORITY_ESSAY)
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-state="complete"]', timeout=60)
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-testid="px-feedback-priority"]')


def seed_target_via_existing_api(student_id: str) -> dict:
    """Create the isolated target fixture through the frozen v0.9 endpoint."""
    from scripts.demo_journey import TARGET_CODE_MAP

    with sqlite3.connect(harness.ISOLATED_DB) as connection:
        row = connection.execute(
            "SELECT e.essay_id, d.diagnosis_json FROM essays e "
            "JOIN diagnoses d ON d.essay_id=e.essay_id WHERE e.student_id=? "
            "ORDER BY e.essay_id DESC LIMIT 1",
            (student_id,),
        ).fetchone()
    assert row is not None
    diagnosis = json.loads(row[1])
    priority = next(
        item for item in diagnosis.get("improvement_priorities", [])
        if item.get("category") == "lexical_repetition"
    )
    payload = {
        "student_id": student_id,
        "source_submission_id": row[0],
        "source_diagnosis_id": priority["diagnosis_id"],
        "target_code": TARGET_CODE_MAP[priority["category"]],
        "target_label": priority["interpretation"],
        "source_priority_id": f"PRIO-{row[0]}",
        "evidence_ids": priority.get("source_metrics", []),
        "gate_status": "selected",
    }
    response = requests.post(f"{harness.BASE}/api/v1/practice-targets", json=payload, timeout=20)
    assert response.status_code == 200, response.text
    return response.json()


def active_workflow(browser) -> tuple[dict, list[str], list[str]]:
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    console_errors, page_errors = observe_errors(page)
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    submit_priority(page)
    seeded_target = seed_target_via_existing_api(STUDENT)
    assert seeded_target.get("status") == "active"
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-testid="px-student-steps"]')
    assert t("practice", "en") in page.locator("h2").all_inner_texts()

    initial = learner_counts(STUDENT)
    assert initial == {"targets": 1, "exercises": 0, "attempts": 0, "evaluations": 0}
    main_text = page.locator('[data-testid="stMainBlockContainer"]').inner_text()
    assert "lexical_repetition_local" not in main_text
    assert t("load_practice", "en") not in main_text
    assert page.locator('[data-testid="stBaseButton-primary"]').count() == 1
    assert t("generate_exercise", "en") in page.locator('[data-testid="stBaseButton-primary"]').inner_text()

    harness.commit_text_input(page, '.st-key-practice_source_v2 textarea', SOURCE_TEXT)
    before_generate = table_counts()
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='.st-key-practice_response_v2 textarea')
    after_generate = table_counts()
    generated = learner_counts(STUDENT)
    assert generated == {"targets": 1, "exercises": 1, "attempts": 0, "evaluations": 0}
    assert after_generate["exercise_instances"] - before_generate["exercise_instances"] == 1
    assert "guided_sentence_rewrite" not in page.locator('[data-testid="stMainBlockContainer"]').inner_text()

    assert harness.select_locale(page, "zh_CN")
    open_page(page, "practice", "zh_CN")
    assert learner_counts(STUDENT)["exercises"] == 1
    assert t("student_practice_constraint_retain", "zh_CN") in page.locator("body").inner_text()
    assert t("student_practice_constraint_no_unsupported", "zh_CN") in page.locator("body").inner_text()
    assert "Rewrite the following sentence" not in page.locator('[data-testid="stMainBlockContainer"]').inner_text()

    before_invalid = table_counts()
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-testid="px-field-error"]')
    assert table_counts() == before_invalid
    assert learner_counts(STUDENT)["attempts"] == 0

    harness.commit_text_input(page, '.st-key-practice_response_v2 textarea', RESPONSE)
    before_valid = table_counts()
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='.px-notice-success[data-testid="px-notice"]')
    after_valid = table_counts()
    completed = learner_counts(STUDENT)
    assert completed == {"targets": 1, "exercises": 1, "attempts": 1, "evaluations": 1}
    assert after_valid["exercise_attempts"] - before_valid["exercise_attempts"] == 1
    assert after_valid["practice_evaluations"] - before_valid["practice_evaluations"] == 1
    assert page.locator('.st-key-practice_response_v2 textarea').count() == 0
    primary = page.locator('[data-testid="stBaseButton-primary"]')
    assert primary.count() == 1 and t("student_home_go_revision", "zh_CN") in primary.inner_text()
    body = page.locator('[data-testid="stMainBlockContainer"]').inner_text()
    assert RESPONSE in body
    assert "candidate_detected" not in body and "guided_sentence_rewrite" not in body
    assert t("student_practice_completion_completed", "zh_CN") in body

    assert harness.select_locale(page, "en")
    open_page(page, "practice", "en")
    assert learner_counts(STUDENT) == completed
    page.reload(wait_until="networkidle")
    assert harness.wait_stable(page)
    open_page(page, "practice", "en")
    harness.commit_text_input(page, '.st-key-practice_student_v2 input', STUDENT)
    assert harness.wait_stable(page, expected='.px-notice-success[data-testid="px-notice"]')
    assert learner_counts(STUDENT) == completed
    assert page.locator('.st-key-practice_response_v2 textarea').count() == 0

    page_health = health(
        page,
        (
            "student_practice_purpose", "student_practice_step_target",
            "student_practice_current_action", "student_practice_action_revision",
        ),
    )
    assert page_health["exceptions"] == 0
    assert not page_health["overflow"] and not page_health["raw_keys"]
    assert page_health["main_max_width"] == "720px"
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    shot = SCREENSHOTS / "practice_en_1280x900_completed.png"
    page.screenshot(path=str(shot), full_page=True)

    result = {
        "initial": initial,
        "after_generate": generated,
        "after_valid": completed,
        "invalid_writes_zero": table_counts()["exercise_attempts"] == after_valid["exercise_attempts"],
        "locale_and_refresh_counts_stable": learner_counts(STUDENT) == completed,
        "primary_actions_per_state": 1,
        "health": page_health,
        "screenshot": str(shot.relative_to(ROOT)),
    }
    unexpected = [item for item in console_errors if not harness.is_allowed_console(item)]
    context.close()
    return result, unexpected, page_errors


def no_target_mobile(browser) -> tuple[dict, list[str], list[str]]:
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    console_errors, page_errors = observe_errors(page)
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    assert harness.select_locale(page, "zh_CN")
    open_page(page, "practice", "zh_CN")
    before = table_counts()
    harness.commit_text_input(page, '.st-key-practice_student_v2 input', "EMPTY01")
    assert harness.wait_stable(page, expected='[data-state="blocked"]')
    primary = page.locator('[data-testid="stBaseButton-primary"]')
    assert primary.count() == 1
    size = primary.first.evaluate(
        "el => { const r=el.getBoundingClientRect(); return {width:r.width,height:r.height}; }"
    )
    assert size["width"] >= 44 and size["height"] >= 44
    result = {
        "blocked_actions": page.locator('[data-state="blocked"]').count(),
        "primary_buttons": primary.count(),
        "primary_size": size,
        "counts_stable": table_counts() == before,
        "health": health(page, ("student_practice_no_target_action",)),
    }
    assert result["health"]["exceptions"] == 0
    assert not result["health"]["overflow"] and not result["health"]["raw_keys"]
    shot = SCREENSHOTS / "practice_zh_CN_390x844_no_target.png"
    page.screenshot(path=str(shot), full_page=True)
    result["screenshot"] = str(shot.relative_to(ROOT))
    unexpected = [item for item in console_errors if not harness.is_allowed_console(item)]
    context.close()
    return result, unexpected, page_errors


def restart_locked(browser) -> tuple[dict, list[str], list[str]]:
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    console_errors, page_errors = observe_errors(page)
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    assert harness.select_locale(page, "zh_CN")
    open_page(page, "practice", "zh_CN")
    before = learner_counts(STUDENT)
    harness.commit_text_input(page, '.st-key-practice_student_v2 input', STUDENT)
    assert harness.wait_stable(page, expected='.px-notice-success[data-testid="px-notice"]')
    primary = page.locator('[data-testid="stBaseButton-primary"]')
    size = primary.first.evaluate(
        "el => { const r=el.getBoundingClientRect(); return {width:r.width,height:r.height}; }"
    )
    result = {
        "response_input": page.locator('.st-key-practice_response_v2 textarea').count(),
        "submit_label": t("submit_attempt", "zh_CN") in page.locator("body").inner_text(),
        "primary_buttons": primary.count(),
        "primary_size": size,
        "counts_stable": learner_counts(STUDENT) == before,
        "health": health(page, ("student_practice_action_revision",)),
    }
    assert result["response_input"] == 0 and not result["submit_label"]
    assert result["primary_buttons"] == 1 and size["width"] >= 44 and size["height"] >= 44
    assert result["counts_stable"] and result["health"]["exceptions"] == 0
    shot = SCREENSHOTS / "practice_zh_CN_390x844_completed_restart.png"
    page.screenshot(path=str(shot), full_page=True)
    result["screenshot"] = str(shot.relative_to(ROOT))
    unexpected = [item for item in console_errors if not harness.is_allowed_console(item)]
    context.close()
    return result, unexpected, page_errors


def main() -> int:
    harness.prepare_isolated_db()
    api = streamlit = None
    evidence: dict[str, object] = {"run_id": "v0.9.4-b-20260801-r1"}
    try:
        api, streamlit = harness.start_stack("practice_slice")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            active, console_a, errors_a = active_workflow(browser)
            no_target, console_b, errors_b = no_target_mobile(browser)
            evidence["active_workflow"] = active
            evidence["no_target_mobile"] = no_target
            browser.close()

            harness.stop_stack(api, streamlit)
            api = streamlit = None
            api, streamlit = harness.start_stack("practice_restart")
            browser = playwright.chromium.launch(headless=True)
            restarted, console_c, errors_c = restart_locked(browser)
            evidence["restart_locked"] = restarted
            evidence["console_errors"] = console_a + console_b + console_c
            evidence["page_errors"] = errors_a + errors_b + errors_c
            browser.close()
    finally:
        harness.stop_stack(api, streamlit)

    evidence["ports_cleaned"] = True
    (HERE / "practice_slice_evidence.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    assert evidence["active_workflow"]["after_valid"] == {
        "targets": 1, "exercises": 1, "attempts": 1, "evaluations": 1,
    }
    assert evidence["restart_locked"]["counts_stable"]
    assert not evidence["console_errors"] and not evidence["page_errors"]
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
