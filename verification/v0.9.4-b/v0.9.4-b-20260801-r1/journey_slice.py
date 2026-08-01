"""Focused v0.9.4-B Learning Journey verification with isolated persistence."""

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


def table_counts() -> dict[str, int]:
    with sqlite3.connect(harness.ISOLATED_DB) as connection:
        tables = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()]
        return {
            table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            for table in tables
        }


def api_journey(student_id: str) -> dict:
    response = requests.get(
        f"{harness.BASE}/api/v1/students/{student_id}/journey", timeout=20
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


def open_journey(page, lang: str) -> None:
    assert harness.select_page(page, t("learning_journey", lang), t("learning_journey", lang))
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


def journey_context(
    browser, lang: str, viewport: tuple[int, int], student_id: str, zero_priority: bool
) -> tuple[dict, list[str], list[str]]:
    authoritative = api_journey(student_id)
    repeat = api_journey(student_id)
    events = authoritative["events"]
    assert events == repeat["events"]
    dedup_keys = [item["deduplication_key"] for item in events]
    assert len(dedup_keys) == len(set(dedup_keys))
    assert all(item.get("source_record_type") and item.get("source_record_id") for item in events)
    assert all(item.get("evidence_status") and item.get("limitations") for item in events)
    if zero_priority:
        assert any(item["event_type"] == "feedback_without_priority" for item in events)

    context = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
    page = context.new_page()
    console_errors, page_errors = observe_errors(page)
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    open_journey(page, lang)
    before = table_counts()
    harness.commit_text_input(page, '.st-key-journey_student_v2 input', student_id)
    assert harness.wait_stable(page, expected='[data-testid="px-timeline-event"]')

    event_count = page.locator('[data-testid="px-timeline-event"]').count()
    labels = page.locator('[data-testid="px-journey-label"]').all_inner_texts()
    expected_labels = [t(item["title_key"], lang) for item in events]
    assert event_count == len(events) and labels == expected_labels
    assert page.locator('[data-testid="px-journey-time"]').count() == len(events)
    assert page.locator('[data-testid="px-journey-evidence"]').count() == len(events)
    assert page.locator('[data-testid="px-journey-source"]').count() == len(events)
    assert page.locator('[data-testid="px-journey-limitation"]').count() == len(events)
    source_texts = page.locator('[data-testid="px-journey-source"]').all_inner_texts()
    assert all(item["source_record_id"] in source_text for item, source_text in zip(events, source_texts))
    evidence_texts = page.locator('[data-testid="px-journey-evidence"]').all_inner_texts()
    expected_evidence = {
        "confirmed_record": t("student_journey_evidence_confirmed_record", lang),
        "derived_state": t("student_journey_evidence_derived_state", lang),
    }
    assert all(expected_evidence[item["evidence_status"]] in text for item, text in zip(events, evidence_texts))
    body = page.locator('[data-testid="stMainBlockContainer"]').inner_text()
    if zero_priority:
        assert t("journey_event_feedback_without_priority", lang) in body
        assert t("journey_state_analysis_without_priority", lang) in body
    assert "lexical_repetition_local" not in body
    for raw in (
        "confirmed_record", "derived_state", "feedback_record", "analysis_run",
        "response_candidate_detected", "major_rewrite_limits_attribution",
    ):
        assert raw not in body

    primary = page.locator('[data-testid="stBaseButton-primary"]')
    assert primary.count() == 1
    size = primary.first.evaluate(
        "el => { const r=el.getBoundingClientRect(); return {width:r.width,height:r.height}; }"
    )
    if viewport[0] < 700:
        assert size["width"] >= 44 and size["height"] >= 44
    page_health = health(
        page,
        (
            "student_journey_purpose", "student_journey_event_time",
            "student_journey_event_evidence", "student_journey_event_source",
        ),
    )
    assert page_health["exceptions"] == 0
    assert not page_health["overflow"] and not page_health["raw_keys"]
    assert page_health["main_max_width"] == "720px"
    assert table_counts() == before

    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    state = "zero_priority" if zero_priority else "full"
    shot = SCREENSHOTS / f"journey_{lang}_{viewport[0]}x{viewport[1]}_{state}.png"
    page.screenshot(path=str(shot), full_page=True)

    alternate = "zh_CN" if lang == "en" else "en"
    assert harness.select_locale(page, alternate)
    open_journey(page, alternate)
    assert page.locator('[data-testid="px-timeline-event"]').count() == len(events)
    assert table_counts() == before

    page.reload(wait_until="networkidle")
    assert harness.wait_stable(page)
    open_journey(page, "en")
    harness.commit_text_input(page, '.st-key-journey_student_v2 input', student_id)
    assert harness.wait_stable(page, expected='[data-testid="px-timeline-event"]')
    after_refresh = api_journey(student_id)
    assert [item["deduplication_key"] for item in after_refresh["events"]] == dedup_keys
    assert table_counts() == before

    result = {
        "combo": f"{lang}_{viewport[0]}x{viewport[1]}_{state}",
        "event_count": event_count,
        "dedup_key_count": len(dedup_keys),
        "all_times": len(events),
        "all_sources": len(events),
        "all_evidence_statuses": len(events),
        "all_limitations": len(events),
        "primary_size": size,
        "render_locale_refresh_counts_stable": table_counts() == before,
        "health": page_health,
        "screenshot": str(shot.relative_to(ROOT)),
    }
    unexpected = [item for item in console_errors if not harness.is_allowed_console(item)]
    context.close()
    return result, unexpected, page_errors


def absent_states(browser) -> tuple[dict, list[str], list[str]]:
    results: dict[str, object] = {}
    all_console: list[str] = []
    all_page_errors: list[str] = []
    for name, student_id in (("blank", ""), ("not_found", "V094B-JOURNEY-MISSING")):
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        console_errors, page_errors = observe_errors(page)
        page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
        assert harness.wait_stable(page)
        open_journey(page, "en")
        before = table_counts()
        if student_id:
            harness.commit_text_input(page, '.st-key-journey_student_v2 input', student_id)
            assert harness.wait_stable(page, expected='.px-notice-error[data-testid="px-notice"]')
        results[name] = {
            "blocked_actions": page.locator('[data-state="blocked"]').count(),
            "error_notices": page.locator('.px-notice-error[data-testid="px-notice"]').count(),
            "events": page.locator('[data-testid="px-timeline-event"]').count(),
            "counts_stable": table_counts() == before,
            "exceptions": page.locator('[data-testid="stException"]').count(),
        }
        all_console.extend(item for item in console_errors if not harness.is_allowed_console(item))
        all_page_errors.extend(page_errors)
        context.close()
    assert results["blank"] == {
        "blocked_actions": 1, "error_notices": 0, "events": 0,
        "counts_stable": True, "exceptions": 0,
    }
    assert results["not_found"] == {
        "blocked_actions": 0, "error_notices": 1, "events": 0,
        "counts_stable": True, "exceptions": 0,
    }
    return results, all_console, all_page_errors


def outage(browser, api_process) -> tuple[dict, list[str], list[str]]:
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    console_errors, page_errors = observe_errors(page)
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    open_journey(page, "en")
    before = table_counts()
    harness.stop_process(api_process)
    harness.commit_text_input(page, '.st-key-journey_student_v2 input', "S02")
    assert harness.wait_stable(page, expected='.px-notice-error[data-testid="px-notice"]')
    result = {
        "error_notices": page.locator('.px-notice-error[data-testid="px-notice"]').count(),
        "events": page.locator('[data-testid="px-timeline-event"]').count(),
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
    evidence: dict[str, object] = {"run_id": "v0.9.4-b-20260801-r1", "contexts": []}
    try:
        api, streamlit = harness.start_stack("journey_slice")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            console_errors: list[str] = []
            page_errors: list[str] = []
            for lang, viewport, student, zero_priority in (
                ("en", (1280, 900), "DEMO-001", False),
                ("zh_CN", (390, 844), "S02", True),
            ):
                result, console, errors = journey_context(
                    browser, lang, viewport, student, zero_priority
                )
                evidence["contexts"].append(result)
                console_errors.extend(console)
                page_errors.extend(errors)
            states, state_console, state_errors = absent_states(browser)
            evidence["absent_states"] = states
            console_errors.extend(state_console)
            page_errors.extend(state_errors)
            outage_result, outage_console, outage_errors = outage(browser, api)
            api = None
            evidence["outage"] = outage_result
            console_errors.extend(outage_console)
            page_errors.extend(outage_errors)
            api = harness.start_api_process("journey_recovery")
            evidence["console_errors"] = console_errors
            evidence["page_errors"] = page_errors
            browser.close()
    finally:
        harness.stop_stack(api, streamlit)

    evidence["ports_cleaned"] = True
    (HERE / "journey_slice_evidence.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    assert all(item["event_count"] == item["dedup_key_count"] for item in evidence["contexts"])
    assert all(item["render_locale_refresh_counts_stable"] for item in evidence["contexts"])
    assert evidence["outage"] == {
        "error_notices": 1, "events": 0, "counts_stable": True, "exceptions": 0,
    }
    assert not evidence["console_errors"] and not evidence["page_errors"]
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
