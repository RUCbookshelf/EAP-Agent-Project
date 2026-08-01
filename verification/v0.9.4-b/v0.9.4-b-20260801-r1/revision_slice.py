"""Focused v0.9.4-B Revision verification with isolated persistence."""

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
from practice_slice import seed_target_via_existing_api  # noqa: E402


SCREENSHOTS = HERE / "screenshots"
STUDENT = "V094B-REVISION-ACTIVE"
PROMPT = "How can writers make an argument clear and specific?"
SOURCE_ESSAY = (
    "Writers repeat vague claims, repeat vague claims, and repeat vague claims in one short passage. "
    "Specific evidence can clarify a reason because readers can inspect the support. " * 5
)
REVISED_ESSAY = (
    "Writers can make an argument clear by stating one specific claim and supporting it with evidence. "
    "Readers can inspect that evidence, compare it with the reason, and decide whether the conclusion follows. "
    "This approach narrows the point without claiming that one revision proves learning."
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


def learner_revision_counts(student_id: str) -> dict[str, int]:
    with sqlite3.connect(harness.ISOLATED_DB) as connection:
        return {
            "essays": int(connection.execute(
                "SELECT COUNT(*) FROM essays WHERE student_id=?", (student_id,)
            ).fetchone()[0]),
            "linked_revisions": int(connection.execute(
                "SELECT COUNT(*) FROM essays WHERE student_id=? "
                "AND revision_of_submission_id IS NOT NULL", (student_id,)
            ).fetchone()[0]),
            "revision_groups": int(connection.execute(
                "SELECT COUNT(DISTINCT revision_group_id) FROM essays WHERE student_id=? "
                "AND revision_group_id IS NOT NULL", (student_id,)
            ).fetchone()[0]),
            "revision_snapshots": int(connection.execute(
                "SELECT COUNT(*) FROM revision_snapshots rs JOIN essays e "
                "ON e.essay_id=rs.target_submission_id WHERE e.student_id=?", (student_id,)
            ).fetchone()[0]),
        }


def latest_uptake_count(student_id: str) -> int:
    with sqlite3.connect(harness.ISOLATED_DB) as connection:
        row = connection.execute(
            "SELECT rs.snapshot_json FROM revision_snapshots rs JOIN essays e "
            "ON e.essay_id=rs.target_submission_id WHERE e.student_id=? "
            "ORDER BY rs.revision_snapshot_row_id DESC LIMIT 1", (student_id,)
        ).fetchone()
    assert row is not None
    return len(json.loads(row[0]).get("uptake_candidates", []))


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


def create_source(page) -> None:
    open_page(page, "student_writing_title", "en")
    harness.commit_text_input(page, '.st-key-writing_student input', STUDENT)
    harness.commit_text_input(page, '.st-key-writing_prompt_input textarea', PROMPT)
    harness.commit_text_input(page, '.st-key-writing_essay textarea', SOURCE_ESSAY)
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-state="complete"]', timeout=60)
    seed_target_via_existing_api(STUDENT)


def valid_workflow(browser) -> tuple[dict, list[str], list[str]]:
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    console_errors, page_errors = observe_errors(page)
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    create_source(page)
    before_page = table_counts()
    before_revision = learner_revision_counts(STUDENT)
    assert before_revision == {
        "essays": 1, "linked_revisions": 0, "revision_groups": 0, "revision_snapshots": 0,
    }

    open_page(page, "student_revision_title", "en")
    assert harness.wait_stable(page, expected='.st-key-revision_text_input textarea')
    main_text = page.locator('[data-testid="stMainBlockContainer"]').inner_text()
    original_value = page.locator('textarea[disabled]').first.input_value()
    assert PROMPT in main_text and original_value == SOURCE_ESSAY.strip()
    assert "lexical_repetition_local" not in main_text
    assert t("student_revision_feedback_focus", "en") in main_text
    assert table_counts() == before_page
    assert page.locator('[data-testid="stBaseButton-primary"]').count() == 1

    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-testid="px-field-error"]')
    assert table_counts() == before_page
    assert learner_revision_counts(STUDENT) == before_revision

    harness.commit_text_input(page, '.st-key-revision_text_input textarea', REVISED_ESSAY)
    before_submit = table_counts()
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-state="complete"]', timeout=60)
    after_submit = table_counts()
    saved = learner_revision_counts(STUDENT)
    assert saved == {
        "essays": 2, "linked_revisions": 1, "revision_groups": 1, "revision_snapshots": 1,
    }
    assert latest_uptake_count(STUDENT) == 1
    assert after_submit["essays"] - before_submit["essays"] == 1
    assert after_submit["revision_groups"] - before_submit["revision_groups"] == 1
    assert after_submit["revision_snapshots"] - before_submit["revision_snapshots"] == 1
    assert page.locator('.st-key-revision_text_input textarea').count() == 0
    main_text = page.locator('[data-testid="stMainBlockContainer"]').inner_text()
    assert t("student_revision_observation", "en") in main_text
    assert t("student_revision_boundary", "en") in main_text
    for forbidden in (
        "has mastered", "proficiency increased", "transfer achieved", "learning gain",
    ):
        assert forbidden not in main_text.lower()
    assert "do not establish that feedback caused" in main_text.lower()
    assert "partially_supported" not in main_text and "not_assessable" not in main_text
    primary = page.locator('[data-testid="stBaseButton-primary"]')
    assert primary.count() == 1 and t("student_revision_open_journey", "en") in primary.inner_text()

    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    desktop_shot = SCREENSHOTS / "revision_en_1280x900_saved.png"
    page.screenshot(path=str(desktop_shot), full_page=True)
    assert harness.select_locale(page, "zh_CN")
    open_page(page, "student_revision_title", "zh_CN")
    page.set_viewport_size({"width": 390, "height": 844})
    harness.close_sidebar(page)
    assert harness.wait_stable(page, expected='[data-state="complete"]')
    assert learner_revision_counts(STUDENT) == saved
    primary = page.locator('[data-testid="stBaseButton-primary"]')
    size = primary.first.evaluate(
        "el => { const r=el.getBoundingClientRect(); return {width:r.width,height:r.height}; }"
    )
    assert size["width"] >= 44 and size["height"] >= 44
    assert t("student_revision_observation", "zh_CN") in page.locator("body").inner_text()
    mobile_health = health(
        page,
        (
            "student_revision_purpose", "student_revision_saved_title",
            "student_revision_observation", "student_revision_boundary",
        ),
    )
    assert mobile_health["exceptions"] == 0
    assert not mobile_health["overflow"] and not mobile_health["raw_keys"]
    assert mobile_health["main_max_width"] == "720px"
    mobile_shot = SCREENSHOTS / "revision_zh_CN_390x844_saved.png"
    page.screenshot(path=str(mobile_shot), full_page=True)

    page.reload(wait_until="networkidle")
    assert harness.wait_stable(page)
    assert learner_revision_counts(STUDENT) == saved
    assert table_counts() == after_submit

    result = {
        "before_revision": before_revision,
        "after_revision": saved,
        "response_observations": latest_uptake_count(STUDENT),
        "empty_input_writes_zero": True,
        "locale_and_refresh_counts_stable": table_counts() == after_submit,
        "mobile_primary_size": size,
        "mobile_health": mobile_health,
        "desktop_screenshot": str(desktop_shot.relative_to(ROOT)),
        "mobile_screenshot": str(mobile_shot.relative_to(ROOT)),
    }
    unexpected = [item for item in console_errors if not harness.is_allowed_console(item)]
    context.close()
    return result, unexpected, page_errors


def no_eligible(browser) -> tuple[dict, list[str], list[str]]:
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    console_errors, page_errors = observe_errors(page)
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    assert harness.select_locale(page, "zh_CN")
    open_page(page, "student_revision_title", "zh_CN")
    before = table_counts()
    harness.commit_text_input(page, '.st-key-revision_student input', "EMPTY01")
    assert harness.wait_stable(page, expected='[data-testid="px-empty-state"]')
    primary = page.locator('[data-testid="stBaseButton-primary"]')
    size = primary.first.evaluate(
        "el => { const r=el.getBoundingClientRect(); return {width:r.width,height:r.height}; }"
    )
    result = {
        "empty_states": page.locator('[data-testid="px-empty-state"]').count(),
        "primary_buttons": primary.count(),
        "primary_size": size,
        "counts_stable": table_counts() == before,
        "health": health(page, ("student_revision_no_eligible_title",)),
    }
    assert result["empty_states"] == 1 and result["primary_buttons"] == 1
    assert size["width"] >= 44 and size["height"] >= 44 and result["counts_stable"]
    assert result["health"]["exceptions"] == 0 and not result["health"]["overflow"]
    unexpected = [item for item in console_errors if not harness.is_allowed_console(item)]
    context.close()
    return result, unexpected, page_errors


def outage(browser, api_process) -> tuple[dict, list[str], list[str]]:
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    console_errors, page_errors = observe_errors(page)
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    open_page(page, "student_revision_title", "en")
    before = table_counts()
    harness.stop_process(api_process)
    harness.commit_text_input(page, '.st-key-revision_student input', "S02")
    assert harness.wait_stable(page, expected='.px-notice-error[data-testid="px-notice"]')
    result = {
        "error_notices": page.locator('.px-notice-error[data-testid="px-notice"]').count(),
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
    evidence: dict[str, object] = {"run_id": "v0.9.4-b-20260801-r1"}
    try:
        api, streamlit = harness.start_stack("revision_slice")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            valid, console_a, errors_a = valid_workflow(browser)
            empty, console_b, errors_b = no_eligible(browser)
            outage_result, console_c, errors_c = outage(browser, api)
            api = None
            evidence["valid_workflow"] = valid
            evidence["no_eligible"] = empty
            evidence["outage"] = outage_result
            evidence["console_errors"] = console_a + console_b + console_c
            evidence["page_errors"] = errors_a + errors_b + errors_c
            browser.close()
            api = harness.start_api_process("revision_recovery")
    finally:
        harness.stop_stack(api, streamlit)

    evidence["ports_cleaned"] = True
    (HERE / "revision_slice_evidence.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    assert evidence["valid_workflow"]["after_revision"]["linked_revisions"] == 1
    assert evidence["valid_workflow"]["response_observations"] == 1
    assert evidence["outage"] == {
        "error_notices": 1, "primary_buttons": 0, "counts_stable": True, "exceptions": 0,
    }
    assert not evidence["console_errors"] and not evidence["page_errors"]
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
