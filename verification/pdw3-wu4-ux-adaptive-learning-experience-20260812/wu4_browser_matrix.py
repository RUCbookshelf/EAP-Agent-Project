# -*- coding: utf-8 -*-
"""Wave-3 WU4 rendered matrix (browser): Today/adaptive page.

Real production stack: for each of 4 locale/viewport combinations, render
the new Today/adaptive student page on the real DOM and capture evidence.
The L2 WU3 endpoints are not composed in this frontend worktree, so the
page must render the honest degraded/unavailable state (graceful API
degradation) with no exceptions, no console/page/remote errors, no
overflow, no raw locale keys, no forbidden wording, and zero DB writes on
render/reload.

The guided flow (recommendation/choice/evaluation/tutor/mini-writing) is
verified by the AppTest harness in tests/test_wave3_wu4_adaptive_ux.py.
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import sys

import requests
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
BASE_HARNESS_DIR = PROJECT_ROOT / "verification/v0.9.4-a/v0.9.4-a-20260801-r1"
WU6_DIR = PROJECT_ROOT / "verification/v0.9.7-b/v0.9.7-b-wu6-20260805-r1"
sys.path.insert(0, str(BASE_HARNESS_DIR))
sys.path.insert(0, str(WU6_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.locale import t  # noqa: E402

import v094a_harness as harness  # noqa: E402
import w6_harness as _w6  # noqa: E402

# Re-point harness state at this WU4 run directory.
harness.RUN_DIR = HERE
harness.ISOLATED_DB = HERE / "isolated" / "writing_feedback_wu4.db"
harness.LOG_DIR = HERE / "logs"

SCREENSHOTS = HERE / "screenshots"
RUN_ID = "pdw3-wu4-ux-adaptive-learning-experience-20260812"
STUDENTS = ("WU4-ED", "WU4-ZD", "WU4-EM", "WU4-ZM")

# The frontend venv's playwright expects chromium_headless_shell-1228 but
# only chromium-1234 is installed in this environment; launch explicitly
# with the installed executable (environment limitation, not a product
# defect).
CHROMIUM_EXE = (
    pathlib.Path(r"C:\Users\16073\AppData\Local\ms-playwright\chromium-1234")
    / "chrome-win64" / "chrome.exe"
)

FORBIDDEN_WORDING = (
    "mastery", "proficient", "cefr", "learning gain", "improved your writing",
)


def whole_db_counts():
    with sqlite3.connect(harness.ISOLATED_DB) as con:
        tables = [
            row[0] for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        ]
        return {table: int(con.execute(
            f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]) for table in tables}


def observe(page):
    console_errors, page_errors, remote_requests = [], [], []
    page.on("console", lambda m: console_errors.append(m.text)
            if m.type == "error" else None)
    page.on("pageerror", lambda e: page_errors.append(str(e)))
    page.on("request", lambda r: remote_requests.append(r.url)
            if not r.url.startswith(("http://127.0.0.1", "http://localhost"))
            else None)
    return console_errors, page_errors, remote_requests


def body_text(page):
    return page.locator('[data-testid="stMainBlockContainer"]').inner_text()


def nav_page(page, title_key, lang, timeout=15000):
    label_text = t(title_key, lang)
    js_code = """(labelText) => {
        const labels = document.querySelectorAll('label[data-testid="stRadioOption"]');
        for (const label of labels) {
            if (label.textContent.trim().includes(labelText) && label.offsetParent !== null) {
                label.scrollIntoView({block: "center"});
                label.click();
                return true;
            }
        }
        return false;
    }"""
    for _ in range(3):
        if page.evaluate(js_code, label_text):
            harness.wait_stable(page, timeout=20)
            _w6.close_sidebar(page)
            return
        page.wait_for_timeout(1500)
    raise RuntimeError(f"Could not click sidebar label '{label_text}'")


def run(browser, student_id, lang, viewport, tag):
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    console_errors, page_errors, remote_requests = observe(page)
    page.goto(harness.UI, timeout=30_000, wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    _w6.close_sidebar(page)

    result = {"combination": f"{lang} {viewport['width']}x{viewport['height']}"}

    _w6.open_sidebar(page)
    nav_page(page, "student_adaptive_title", lang)
    assert harness.wait_stable(page, timeout=20)
    _w6.close_sidebar(page)

    harness.commit_text_input(page, ".st-key-adaptive_student input", student_id)
    assert harness.wait_stable(page, timeout=15)
    _w6.close_sidebar(page)

    heading = page.locator("h2.px-page-heading")
    assert heading.count() >= 1
    heading_text = heading.first.inner_text()
    assert t("student_adaptive_title", lang) in heading_text

    width = page.evaluate("() => window.innerWidth")
    overflow = page.evaluate("() => document.documentElement.scrollWidth") > width
    text = body_text(page)
    raw_keys = [k for k in ("student_adaptive_", "wave2_") if k in text]
    normalized = text.lower()
    for phrase in (
        "none establishes learning, mastery, or stable transfer.",
        "are not proficiency or mastery judgments.",
    ):
        normalized = normalized.replace(phrase, "")
    forbidden = [w for w in FORBIDDEN_WORDING if w in normalized]
    exceptions = page.locator('[data-testid="stException"]').count()
    controls = {
        "recommend_unavailable": "student_adaptive_unavailable",
    }
    unavailable_text = t(controls["recommend_unavailable"], lang)
    honest_unavailable = unavailable_text in text
    degraded_note = t("student_adaptive_unavailable", lang) in text

    shot = SCREENSHOTS / f"{tag}_adaptive_today.png"
    shot.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(shot), full_page=True)

    # Zero-write check on render and reload.
    before = whole_db_counts()
    page.reload(wait_until="networkidle")
    assert harness.wait_stable(page)
    if lang == "zh_CN":
        assert harness.select_locale(page, lang)
    _w6.close_sidebar(page)
    after = whole_db_counts()
    zero_writes = before == after

    result.update({
        "heading": heading_text,
        "exceptions": exceptions,
        "overflow": overflow,
        "raw_keys": raw_keys,
        "forbidden": forbidden,
        "console_errors": console_errors,
        "page_errors": page_errors,
        "remote_requests": remote_requests,
        "honest_unavailable": honest_unavailable,
        "degraded_note": degraded_note,
        "zero_writes_reload": zero_writes,
        "screenshot": str(shot.relative_to(PROJECT_ROOT)),
    })

    assert exceptions == 0, (tag, exceptions)
    assert not overflow, (tag, overflow)
    assert not raw_keys, (tag, raw_keys)
    assert not forbidden, (tag, forbidden)
    assert not console_errors, (tag, console_errors)
    assert not page_errors, (tag, page_errors)
    assert not remote_requests, (tag, remote_requests)
    assert honest_unavailable, (tag, "honest unavailable state missing")
    assert degraded_note, (tag, "degraded note missing")
    assert zero_writes, (tag, "reload wrote to DB")

    context.close()
    return result


def main():
    harness.prepare_isolated_db()
    with sqlite3.connect(harness.ISOLATED_DB) as con:
        for student_id in STUDENTS:
            con.execute(
                "INSERT OR IGNORE INTO students (student_id, created_at, "
                "is_synthetic) VALUES (?, '2026-08-12T00:00:00+00:00', 1)",
                (student_id,),
            )
        con.commit()

    evidence = {"run_id": RUN_ID}
    api = streamlit = None
    try:
        api, streamlit = harness.start_stack("wu4_matrix")
        before = whole_db_counts()
        with sync_playwright() as pw:
            br = pw.chromium.launch(headless=True, executable_path=str(CHROMIUM_EXE))
            try:
                combos = [
                    (STUDENTS[0], "en", {"width": 1280, "height": 900}, "en_1280x900"),
                    (STUDENTS[1], "zh_CN", {"width": 1280, "height": 900}, "zh_1280x900"),
                    (STUDENTS[2], "en", {"width": 390, "height": 844}, "en_390x844"),
                    (STUDENTS[3], "zh_CN", {"width": 390, "height": 844}, "zh_390x844"),
                ]
                for student_id, lang, vp, tag in combos:
                    evidence[tag] = run(br, student_id, lang, vp, tag)
            finally:
                br.close()
        after = whole_db_counts()
        evidence["zero_writes_overall"] = before == after
    finally:
        harness.stop_stack(api, streamlit)

    (HERE / "rendered_wu4_matrix_evidence.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    for tag in ("en_1280x900", "zh_1280x900", "en_390x844", "zh_390x844"):
        combo = evidence[tag]
        assert not combo.get("exceptions"), (tag, combo)
        assert not combo.get("overflow"), (tag, combo)
        assert not combo.get("raw_keys"), (tag, combo)
        assert not combo.get("forbidden"), (tag, combo)
        assert not combo.get("console_errors"), (tag, combo)
        assert not combo.get("page_errors"), (tag, combo)
        assert not combo.get("remote_requests"), (tag, combo)
        assert combo.get("honest_unavailable"), (tag, combo)
        assert combo.get("degraded_note"), (tag, combo)
        assert combo.get("zero_writes_reload"), (tag, combo)
    assert evidence.get("zero_writes_overall") is True, "matrix wrote to DB"
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
