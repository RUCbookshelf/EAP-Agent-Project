"""Focused v0.9.4-B Writing verification with isolated persistence."""

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
API_LOG = HERE / "logs" / "writing_slice_api.log"
PROMPT = "Explain how a school can reduce unnecessary waste while keeping student activities practical."
ESSAY = (
    "Schools can reduce unnecessary waste by making small routines clear and practical. "
    "Students can use refill stations, sort reusable materials, and plan events before buying supplies. "
    "Teachers can model these routines and explain why each choice matters. "
    "These actions do not prove broad learning, but they give the school a workable starting point."
)


def table_counts() -> dict[str, int]:
    with sqlite3.connect(harness.ISOLATED_DB) as connection:
        tables = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()]
        return {table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]) for table in tables}


def essay_count(student_id: str) -> int:
    with sqlite3.connect(harness.ISOLATED_DB) as connection:
        return int(connection.execute(
            "SELECT COUNT(*) FROM essays WHERE student_id=?", (student_id,)
        ).fetchone()[0])


def submission_record(student_id: str) -> tuple | None:
    with sqlite3.connect(harness.ISOLATED_DB) as connection:
        return connection.execute(
            "SELECT writing_prompt, essay_text, revision_of_submission_id "
            "FROM essays WHERE student_id=?", (student_id,)
        ).fetchone()


def submission_request_count() -> int:
    if not API_LOG.exists():
        return 0
    return API_LOG.read_text(encoding="utf-8", errors="replace").count(
        '"POST /api/v1/submissions HTTP/1.1" 201 Created'
    )


def open_writing(page, lang: str) -> None:
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    assert harness.select_page(
        page, t("student_writing_title", lang), t("student_writing_title", lang)
    )
    harness.close_sidebar(page)


def health(page) -> dict[str, object]:
    width = page.evaluate("() => window.innerWidth")
    text = page.locator("body").inner_text()
    return {
        "exceptions": page.locator('[data-testid="stException"]').count(),
        "overflow": page.evaluate("() => document.documentElement.scrollWidth") > width,
        "raw_keys": [key for key in (
            "student_writing_task_section", "student_writing_prompt_section",
            "student_writing_draft_section", "student_writing_saved_title"
        ) if key in text],
    }


def run_valid_context(browser, lang: str, viewport: tuple[int, int], student_id: str) -> tuple[dict, list[str], list[str]]:
    context = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
    page = context.new_page()
    console_errors: list[str] = []
    page_errors: list[str] = []
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    open_writing(page, lang)
    request_before = submission_request_count()
    before_render = table_counts()
    harness.commit_text_input(page, '[data-testid="stTextInput"] input', student_id)
    assert table_counts() == before_render

    prompt = page.locator('.st-key-writing_prompt_input textarea')
    essay = page.locator('.st-key-writing_essay textarea')
    harness.commit_text_input(page, '.st-key-writing_essay textarea', ESSAY)
    harness.close_sidebar(page)
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-testid="px-field-error"]')
    empty_prompt = {
        "field_errors": page.locator('[data-testid="px-field-error"]').count(),
        "post_requests": submission_request_count() - request_before,
        "essays": essay_count(student_id),
    }
    assert empty_prompt == {"field_errors": 1, "post_requests": 0, "essays": 0}

    harness.commit_text_input(page, '.st-key-writing_prompt_input textarea', PROMPT)
    harness.commit_text_input(page, '.st-key-writing_essay textarea', "")
    harness.close_sidebar(page)
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-testid="px-field-error"]')
    empty_essay = {
        "field_errors": page.locator('[data-testid="px-field-error"]').count(),
        "post_requests": submission_request_count() - request_before,
        "essays": essay_count(student_id),
    }
    assert empty_essay == {"field_errors": 1, "post_requests": 0, "essays": 0}

    harness.commit_text_input(page, '.st-key-writing_essay textarea', ESSAY)
    before_submit = table_counts()
    harness.close_sidebar(page)
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='[data-state="complete"]', timeout=60)
    after_submit = table_counts()
    assert submission_request_count() == request_before + 1
    assert essay_count(student_id) == 1
    persisted = submission_record(student_id)
    assert persisted == (PROMPT, ESSAY, None)

    saved = health(page)
    saved.update(
        {
            "complete_state": page.locator('[data-state="complete"]').count(),
            "primary_buttons": page.locator('[data-testid="stBaseButton-primary"]').count(),
            "submit_label_present": t("submit_button", lang) in page.locator("body").inner_text(),
            "technical_caption": page.locator('[data-testid="px-mono"]').count(),
        }
    )
    primary_size = page.locator('[data-testid="stBaseButton-primary"]').first.evaluate(
        "el => { const r=el.getBoundingClientRect(); return {width:r.width,height:r.height}; }"
    )
    saved["primary_size"] = primary_size
    assert saved["complete_state"] == 1
    assert saved["primary_buttons"] == 1
    assert not saved["submit_label_present"]
    if viewport[0] < 700:
        assert primary_size["height"] >= 44 and primary_size["width"] >= 44

    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    shot = SCREENSHOTS / f"writing_{lang}_{viewport[0]}x{viewport[1]}_saved.png"
    page.screenshot(path=str(shot), full_page=True)
    if lang == "en":
        assert harness.select_locale(page, "zh_CN")
        assert harness.select_page(
            page, t("student_writing_title", "zh_CN"), t("student_writing_title", "zh_CN")
        )
        harness.close_sidebar(page)
        assert page.locator('[data-testid="stException"]').count() == 0
        assert table_counts() == after_submit
        assert submission_request_count() == request_before + 1

    page.reload(wait_until="networkidle")
    assert harness.wait_stable(page, expected='[data-testid="stAppViewContainer"]')
    after_refresh = table_counts()
    assert after_refresh == after_submit
    assert submission_request_count() == request_before + 1

    unexpected = [item for item in console_errors if not harness.is_allowed_console(item)]
    result = {
        "combo": f"{lang}_{viewport[0]}x{viewport[1]}",
        "empty_prompt": empty_prompt,
        "empty_essay": empty_essay,
        "post_request_count": submission_request_count() - request_before,
        "essay_count": essay_count(student_id),
        "saved": saved,
        "refresh_and_locale_counts_stable": table_counts() == after_submit,
        "write_delta_after_valid_submit": {
            key: after_submit[key] - before_submit[key] for key in after_submit if after_submit[key] != before_submit[key]
        },
        "screenshot": str(shot.relative_to(ROOT)),
    }
    context.close()
    return result, unexpected, page_errors


def outage(browser, api_process) -> tuple[dict, list[str], list[str]]:
    student_id = "V094B-WRITING-OUTAGE"
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    console_errors: list[str] = []
    page_errors: list[str] = []
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    open_writing(page, "en")
    harness.commit_text_input(page, '[data-testid="stTextInput"] input', student_id)
    harness.commit_text_input(page, '.st-key-writing_prompt_input textarea', PROMPT)
    harness.commit_text_input(page, '.st-key-writing_essay textarea', ESSAY)
    before = table_counts()
    harness.stop_process(api_process)
    harness.close_sidebar(page)
    page.locator('[data-testid="stBaseButton-primary"]').click()
    assert harness.wait_stable(page, expected='.px-notice-error[data-testid="px-notice"]')
    result = {
        "error_notice": page.locator('.px-notice-error[data-testid="px-notice"]').count(),
        "success_notice": page.locator('.px-notice-success').count(),
        "empty_state": page.locator('[data-testid="px-empty-state"]').count(),
        "essay_count": essay_count(student_id),
        "counts_unchanged": before == table_counts(),
        "exceptions": page.locator('[data-testid="stException"]').count(),
    }
    expected_network = ("ERR_CONNECTION_REFUSED", "Failed to fetch")
    unexpected = [item for item in console_errors if not harness.is_allowed_console(item) and not any(x in item for x in expected_network)]
    context.close()
    return result, unexpected, page_errors


def main() -> int:
    harness.prepare_isolated_db()
    api = streamlit = None
    evidence: dict[str, object] = {"run_id": "v0.9.4-b-20260801-r1", "contexts": []}
    try:
        api, streamlit = harness.start_stack("writing_slice")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            console_errors: list[str] = []
            page_errors: list[str] = []
            for lang, viewport, student in (
                ("en", (1280, 900), "V094B-WRITING-EN"),
                ("zh_CN", (390, 844), "V094B-WRITING-ZH"),
            ):
                result, console, errors = run_valid_context(browser, lang, viewport, student)
                evidence["contexts"].append(result)
                console_errors.extend(console)
                page_errors.extend(errors)

            outage_result, outage_console, outage_errors = outage(browser, api)
            api = None
            evidence["outage"] = outage_result
            console_errors.extend(outage_console)
            page_errors.extend(outage_errors)
            api = harness.start_api_process("writing_recovery")
            evidence["console_errors"] = console_errors
            evidence["page_errors"] = page_errors
            browser.close()
    finally:
        harness.stop_stack(api, streamlit)

    evidence["ports_cleaned"] = True
    (HERE / "writing_slice_evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    assert all(item["post_request_count"] == 1 and item["essay_count"] == 1 for item in evidence["contexts"])
    assert all(item["refresh_and_locale_counts_stable"] for item in evidence["contexts"])
    assert evidence["outage"] == {
        "error_notice": 1, "success_notice": 0, "empty_state": 0,
        "essay_count": 0, "counts_unchanged": True, "exceptions": 0,
    }
    assert not evidence["console_errors"]
    assert not evidence["page_errors"]
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
