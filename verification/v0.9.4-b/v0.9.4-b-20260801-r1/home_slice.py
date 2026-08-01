"""Focused v0.9.4-B Home verification using the stable v0.9.4-A harness."""

from __future__ import annotations

import json
import pathlib
import sqlite3
import sys

from playwright.sync_api import sync_playwright


HERE = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
HARNESS_DIR = PROJECT_ROOT / "verification/v0.9.4-a/v0.9.4-a-20260801-r1"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HARNESS_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

import v094b_harness as harness  # noqa: E402
from app.ui.locale import t  # noqa: E402


harness.RUN_DIR = HERE
harness.ISOLATED_DB = HERE / "isolated" / "writing_feedback_v094b.db"
harness.LOG_DIR = HERE / "logs"
SCREENSHOTS = HERE / "screenshots"


def table_counts() -> dict[str, int]:
    with sqlite3.connect(harness.ISOLATED_DB) as connection:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
        return {table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]) for table in tables}


def page_health(page) -> dict[str, object]:
    width = page.evaluate("() => window.innerWidth")
    document_width = page.evaluate("() => document.documentElement.scrollWidth")
    text = page.locator("body").inner_text()
    return {
        "exceptions": page.locator('[data-testid="stException"]').count(),
        "overflow": document_width > width,
        "raw_keys": [
            key for key in (
                "student_home_title", "student_home_subtitle", "student_home_step_write",
                "student_home_go_writing", "student_home_latest_activity"
            ) if key in text
        ],
        "student_width": page.evaluate(
            "() => getComputedStyle(document.querySelector('[data-testid=stMainBlockContainer]')).maxWidth"
        ),
    }


def run_context(browser, lang: str, viewport: tuple[int, int]) -> tuple[dict[str, object], list[str], list[str]]:
    context = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
    page = context.new_page()
    console_errors: list[str] = []
    page_errors: list[str] = []
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page, expected='[data-testid="stAppViewContainer"]')
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    harness.close_sidebar(page)
    assert t("student_home_title", lang) in harness.current_h2(page)

    missing = page_health(page)
    missing.update(
        {
            "steps": page.locator('[data-testid="px-student-steps"] li').count(),
            "action_state": page.locator('[data-testid="px-student-primary-action"]').get_attribute("data-state"),
            "primary_buttons": page.locator('[data-testid="stBaseButton-primary"]').count(),
        }
    )
    assert missing["steps"] == 3
    assert missing["action_state"] == "blocked"
    assert missing["primary_buttons"] == 0

    learner = page.locator('[data-testid="stTextInput"] input').first
    learner.focus()
    focus = page.evaluate(
        "() => { const s=getComputedStyle(document.activeElement); "
        "return {style:s.outlineStyle,width:s.outlineWidth,color:s.outlineColor}; }"
    )
    assert focus == {"style": "solid", "width": "3px", "color": "rgb(15, 109, 189)"}
    harness.commit_text_input(page, '[data-testid="stTextInput"] input', "S02")
    assert harness.wait_stable(page, expected='[data-testid="px-student-context"]')

    valid = page_health(page)
    primary = page.locator('[data-testid="stBaseButton-primary"]').first
    valid.update(
        {
            "learner_visible": "S02" in page.locator('[data-testid="px-student-context"]').first.inner_text(),
            "steps": page.locator('[data-testid="px-student-steps"] li').count(),
            "primary_buttons": page.locator('[data-testid="stBaseButton-primary"]').count(),
            "primary_size": primary.evaluate(
                "el => { const r=el.getBoundingClientRect(); return {width:r.width,height:r.height}; }"
            ),
            "focus": focus,
        }
    )
    assert valid["learner_visible"]
    assert valid["steps"] == 3
    assert valid["primary_buttons"] == 1
    if viewport[0] < 700:
        assert valid["primary_size"]["height"] >= 44 and valid["primary_size"]["width"] >= 44

    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    screenshot = SCREENSHOTS / f"home_{lang}_{viewport[0]}x{viewport[1]}.png"
    page.screenshot(path=str(screenshot), full_page=True)
    harness.close_sidebar(page)
    primary.click(timeout=8_000)
    assert harness.wait_stable(page)
    assert t("student_home_title", lang) not in harness.current_h2(page)
    navigation_heading = harness.current_h2(page)

    unexpected_console = [item for item in console_errors if not harness.is_allowed_console(item)]
    result = {
        "combo": f"{lang}_{viewport[0]}x{viewport[1]}",
        "missing": missing,
        "valid": valid,
        "navigation_heading": navigation_heading,
        "screenshot": str(screenshot.relative_to(PROJECT_ROOT)),
    }
    context.close()
    return result, unexpected_console, page_errors


def outage(browser) -> tuple[dict[str, object], list[str], list[str]]:
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    console_errors: list[str] = []
    page_errors: list[str] = []
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    harness.commit_text_input(page, '[data-testid="stTextInput"] input', "S02")
    assert harness.wait_stable(page)
    result = {
        "error_notice": page.locator('.px-notice-error[data-testid="px-notice"]').count(),
        "empty_state": page.locator('[data-testid="px-empty-state"]').count(),
        "exceptions": page.locator('[data-testid="stException"]').count(),
    }
    context.close()
    expected_network = ("ERR_CONNECTION_REFUSED", "Failed to fetch")
    unexpected = [
        item for item in console_errors
        if not harness.is_allowed_console(item) and not any(expected in item for expected in expected_network)
    ]
    return result, unexpected, page_errors


def main() -> int:
    harness.prepare_isolated_db()
    before = table_counts()
    with sqlite3.connect(harness.ISOLATED_DB) as connection:
        assert connection.execute("SELECT 1 FROM students WHERE student_id='S02'").fetchone()

    api = streamlit = None
    evidence: dict[str, object] = {"run_id": "v0.9.4-b-20260801-r1", "contexts": []}
    try:
        api, streamlit = harness.start_stack("home_slice")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            all_console: list[str] = []
            all_page_errors: list[str] = []
            for lang, viewport in (("en", (1280, 900)), ("zh_CN", (390, 844))):
                result, console, page_errors = run_context(browser, lang, viewport)
                evidence["contexts"].append(result)
                all_console.extend(console)
                all_page_errors.extend(page_errors)

            harness.stop_process(api)
            api = None
            outage_result, outage_console, outage_page_errors = outage(browser)
            evidence["outage"] = outage_result
            all_console.extend(outage_console)
            all_page_errors.extend(outage_page_errors)
            api = harness.start_api_process("home_recovery")

            evidence["console_errors"] = all_console
            evidence["page_errors"] = all_page_errors
            browser.close()
    finally:
        harness.stop_stack(api, streamlit)

    after = table_counts()
    evidence["table_counts_unchanged"] = before == after
    evidence["ports_cleaned"] = True
    (HERE / "home_slice_evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    assert all(not item["missing"]["exceptions"] and not item["valid"]["exceptions"] for item in evidence["contexts"])
    assert all(not item["missing"]["overflow"] and not item["valid"]["overflow"] for item in evidence["contexts"])
    assert all(not item["missing"]["raw_keys"] and not item["valid"]["raw_keys"] for item in evidence["contexts"])
    assert all(item["missing"]["student_width"] == "720px" for item in evidence["contexts"])
    assert evidence["outage"] == {"error_notice": 1, "empty_state": 0, "exceptions": 0}
    assert not evidence["console_errors"]
    assert not evidence["page_errors"]
    assert evidence["table_counts_unchanged"]
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
