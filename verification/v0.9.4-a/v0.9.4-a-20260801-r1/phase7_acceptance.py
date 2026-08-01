"""v0.9.4-A final integrated browser acceptance — 48 page renders.

All twelve pages x four combinations (en/zh_CN x 1280x900/390x844), with a
FRESH browser context per (combination x role). Built on the shared
semantic-state harness (log-file stack, post-action state verification,
bounded stabilization).

Also covers: computed styles, 44px touch targets, representative
interactions (Writing validation/submit, Journey events/empty, one export
with duplicate-write check, zh Human Review labels, locale-switch no-writes),
before/after screenshots, and timing observations.

Run: python verification/v0.9.4-a/v0.9.4-a-20260801-r1/phase7_acceptance.py
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import time

import requests
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from v094a_harness import (  # noqa: E402
    BASE,
    UI,
    activate_tab,
    close_sidebar,
    commit_text_input,
    current_h2,
    db_counts,
    is_allowed_console,
    prepare_isolated_db,
    select_locale,
    select_page,
    select_role,
    start_stack,
    stop_stack,
    wait_stable,
)

SHOTS = HERE / "screenshots"

RAW_KEYS = [
    "student_home_title", "student_writing_title", "student_feedback_title",
    "student_revision_title", "learning_journey", "practice",
    "research_overview_title", "research_evidence_title", "tab_calf",
    "research_learning_title", "nav_research_data", "research_audit_title",
    "lang_en", "lang_zh_CN", "view_student", "view_research", "nav_pages",
    "human_review_target_id", "export_run_success", "journey_counts_label",
]

EXTERNAL_HOSTS = ("fonts.googleapis", "fonts.gstatic", "cdn.jsdelivr", "unpkg", "cdnjs")

PAGES = {
    ("en", "student"): [
        ("Home", "Home"), ("Writing", "Writing"), ("Feedback", "Feedback"),
        ("Revision", "Revision"), ("Practice", "Practice"),
        ("Learning Journey", "Learning Journey"),
    ],
    ("zh_CN", "student"): [
        ("首页", "首页"), ("写作", "写作"), ("反馈", "反馈"),
        ("修订", "修订"), ("练习", "练习"), ("学习旅程", "学习旅程"),
    ],
    ("en", "research"): [
        ("Research Overview", "Research Overview"),
        ("Research Evidence", "Research Evidence"),
        ("CALF Measures", "CALF Measures"),
        ("Learning Process", "Learning Process"),
        ("Research Data", "Research Data"),
        ("System Audit", "System Audit"),
    ],
    ("zh_CN", "research"): [
        ("研究概览", "研究概览"), ("研究证据", "研究证据"),
        ("CALF测量", "CALF测量"), ("学习过程", "学习过程"),
        ("研究数据", "研究数据"), ("系统审计", "系统审计"),
    ],
}

DEMO_PROMPT = "What actions matter for sustainability?"
DEMO_ESSAY = (
    "People should protect the environment. People should recycle more. "
    "People should save water. People should plant trees. People should reduce waste. "
    "People should protect the environment. People should recycle more. "
    "People should save water. People should plant trees. People should reduce waste. "
    "People should use public transport. People should teach children about nature. "
    "People should value clean air."
)


def check_render(page, page_label: str, expected_h2: str, *, mobile: bool, research: bool) -> dict:
    problems: list[str] = []
    if page.locator('[data-testid="stException"]').count() > 0:
        problems.append("stException: " + page.locator('[data-testid="stException"]').first.inner_text()[:120])
    h2s = current_h2(page)
    if not any(expected_h2 in h for h in h2s):
        problems.append(f"wrong page: h2={h2s} expected {expected_h2}")

    vw = page.evaluate("() => window.innerWidth")
    doc_w = page.evaluate("() => document.documentElement.scrollWidth")
    body_w = page.evaluate("() => document.body.scrollWidth")
    if doc_w > vw or body_w > vw:
        problems.append(f"overflow doc={doc_w} body={body_w} vw={vw}")

    text = page.evaluate("() => document.body.innerText")
    raw = [k for k in RAW_KEYS if "_" in k and k in text]
    if raw:
        problems.append(f"raw keys: {raw}")
    has_system = "[System]" in text
    if research and not has_system:
        problems.append("research view missing [System]")
    if not research and has_system:
        problems.append("student view leaks [System]")

    fonts = page.evaluate("""() => {
        const p = document.querySelector('.stApp p') || document.querySelector('.stApp label') || document.querySelector('.stApp');
        const h = document.querySelector('.stApp h2') || document.querySelector('.stApp h1');
        const mono = document.querySelector('[data-testid="px-mono"], code, pre, .px-badge');
        return {
            body: p ? getComputedStyle(p).fontFamily : '',
            heading: h ? getComputedStyle(h).fontFamily : '',
            mono: mono ? getComputedStyle(mono).fontFamily : '',
        };
    }""")
    if not any(t in fonts["body"] for t in ("Segoe UI", "-apple-system", "sans-serif")):
        problems.append(f"body font not sans: {fonts['body']}")
    if not any(t in fonts["heading"] for t in ("Cascadia", "Consolas", "SFMono", "monospace")):
        problems.append(f"heading font not mono: {fonts['heading']}")
    if fonts["mono"] and not any(t in fonts["mono"] for t in ("Cascadia", "Consolas", "SFMono", "monospace")):
        problems.append(f"technical element not mono: {fonts['mono']}")

    if page_label in ("Writing", "写作", "Research Data", "研究数据"):
        primary = page.locator('[data-testid="stBaseButton-primary"], button[kind="primary"]')
        if primary.count() != 1:
            problems.append(f"primary count != 1: {primary.count()}")
        else:
            cs = page.evaluate("""() => {
                const el = document.querySelector('[data-testid="stBaseButton-primary"], button[kind="primary"]');
                const s = getComputedStyle(el);
                const r = el.getBoundingClientRect();
                return { bg: s.backgroundColor, color: s.color, radius: s.borderRadius,
                         shadow: s.boxShadow, transition: s.transitionDuration,
                         animation: s.animationName, h: r.height, w: r.width };
            }""")
            if cs["bg"] != "rgb(224, 0, 71)":
                problems.append(f"primary bg {cs['bg']}")
            if cs["color"] != "rgb(255, 255, 255)":
                problems.append(f"primary text {cs['color']}")
            if cs["radius"] != "0px":
                problems.append(f"primary radius {cs['radius']}")
            if "blur" in cs["shadow"] or "rgba" in cs["shadow"]:
                problems.append(f"primary soft shadow {cs['shadow']}")
            if cs["transition"] not in ("0s", "0s, 0s"):
                problems.append(f"primary transition {cs['transition']}")
            if cs["animation"] != "none":
                problems.append(f"primary animation {cs['animation']}")
            min_ok = 44 if mobile else 40
            if cs["h"] < min_ok or cs["w"] <= 0:
                problems.append(f"primary undersized h={cs['h']} w={cs['w']}")

    if page_label in ("Writing", "写作"):
        page.evaluate(
            "() => { const el = document.querySelector('[data-testid=\"stTextInput\"] input'); if (el) el.focus(); }"
        )
        page.wait_for_timeout(250)
        focus = page.evaluate("""() => {
            const el = document.activeElement;
            if (!el) return null;
            const s = getComputedStyle(el);
            return { style: s.outlineStyle, width: s.outlineWidth, color: s.outlineColor };
        }""")
        if not focus or focus["style"] in ("none", "") or float(focus["width"].replace("px", "") or 0) < 2:
            problems.append(f"focus not visible: {focus}")

    if page_label == "研究数据":
        tab_labels = page.evaluate("() => [...document.querySelectorAll('[role=tab]')].map(t => t.innerText.trim())")
        if "人工复核" not in tab_labels:
            problems.append(f"zh tab labels: {tab_labels}")
        if not activate_tab(page, 4):
            problems.append("Human Review tab did not activate")
        body = page.evaluate("() => document.body.innerText")
        if "目标 ID" not in body or "Target ID" in body:
            problems.append("zh Human Review labels wrong")

    return {"page": page_label, "ok": not problems, "problems": problems, "fonts": fonts}


def run_matrix_context(browser, lang: str, viewport: tuple, role: str) -> dict:
    mobile = viewport[0] < 700
    context = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
    page = context.new_page()
    console_errors: list[str] = []
    page_errors: list[str] = []
    remote: list[str] = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))
    page.on("request", lambda req: remote.append(req.url) if any(h in req.url for h in EXTERNAL_HOSTS) else None)
    page.goto(UI, timeout=30000, wait_until="networkidle")
    wait_stable(page, expected="[data-testid='stAppViewContainer']")
    if lang == "zh_CN":
        select_locale(page, "zh_CN")
    if role == "research":
        select_role(page, "research", lang)
    renders = {}
    for label, expected_h2 in PAGES[(lang, role)]:
        t0 = time.monotonic()
        select_page(page, label, expected_h2)
        renders[label] = check_render(page, label, expected_h2, mobile=mobile, research=(role == "research"))
        renders[label]["nav_ms"] = round((time.monotonic() - t0) * 1000, 1)
    unexpected = [m for m in console_errors if not is_allowed_console(m)]
    context.close()
    return {
        "combo": f"{lang}_{viewport[0]}x{viewport[1]}_{role}",
        "renders": renders,
        "console_errors": unexpected[:5],
        "page_errors": page_errors[:5],
        "remote_requests": remote[:5],
    }


def interactions(browser, results: dict) -> None:
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.goto(UI, timeout=30000, wait_until="networkidle")
    wait_stable(page, expected="[data-testid='stAppViewContainer']")
    interactions_data: dict = {}

    # 1. Writing validation blocks empty prompt; valid submit writes once.
    select_page(page, "Writing", "Writing")
    before = db_counts()
    page.locator('[data-testid="stTextInput"] input').first.fill("S02")
    page.locator("textarea").nth(1).fill("Cities should add parks because parks provide space to exercise.")
    page.locator('[data-testid="stBaseButton-primary"], button[kind="primary"]').click()
    wait_stable(page, timeout=20)
    after_blocked = db_counts()
    interactions_data["writing_empty_prompt_blocked"] = {
        "field_error_visible": page.locator('[data-testid="px-field-error"]').count() > 0,
        "no_essay_written": after_blocked["essays"] == before["essays"],
    }
    page.locator('[data-testid="stTextInput"] input').first.fill("S02")
    page.locator("textarea").nth(0).fill(DEMO_PROMPT)
    page.locator("textarea").nth(1).fill(DEMO_ESSAY)
    page.locator('[data-testid="stBaseButton-primary"], button[kind="primary"]').click()
    wait_stable(page, timeout=30)
    after_submit = db_counts()
    interactions_data["writing_valid_submit"] = {
        "essay_count_delta": after_submit["essays"] - before["essays"],
        "mono_captions": page.locator('[data-testid="px-mono"]').count() > 0,
    }
    interactions_data["no_duplicate_write_on_submit"] = after_submit["essays"] == before["essays"] + 1
    page.screenshot(path=str(SHOTS / "en_1280x900_feedback_after_submit.png"), full_page=False)

    # 2. Learning Journey: DEMO-001 events; EMPTY01 empty state.
    select_page(page, "Learning Journey", "Learning Journey")
    commit_text_input(page, '[data-testid="stTextInput"] input', "DEMO-001")
    page.get_by_role("button", name="Load Learning Journey").click(timeout=8000)
    wait_stable(page, timeout=20)
    interactions_data["journey_demo_events"] = {
        "timeline_rendered": page.locator(".px-timeline-node").count() > 0,
    }
    page.screenshot(path=str(SHOTS / "en_1280x900_journey_events.png"), full_page=False)
    commit_text_input(page, '[data-testid="stTextInput"] input', "EMPTY01")
    page.get_by_role("button", name="Load Learning Journey").click(timeout=8000)
    wait_stable(page, timeout=20)
    interactions_data["journey_empty_state"] = {
        "empty_state_visible": page.locator('[data-testid="px-empty-state"]').count() > 0,
    }
    page.screenshot(path=str(SHOTS / "en_1280x900_journey_empty.png"), full_page=False)

    # 3. Research Data: Run Export once -> exactly one new job.
    select_role(page, "research", "en")
    select_page(page, "Research Data", "Research Data")
    export_root = pathlib.Path(__file__).resolve().parents[3] / "research_exports"
    export_root.mkdir(parents=True, exist_ok=True)
    before_dirs = sorted(p.name for p in export_root.iterdir() if p.is_dir())
    before_export = db_counts()
    page.locator('[data-testid="stBaseButton-primary"], button[kind="primary"]').click()
    wait_stable(page, timeout=20)
    after_export = db_counts()
    after_dirs = sorted(p.name for p in export_root.iterdir() if p.is_dir())
    export_body = page.evaluate("() => document.body.innerText")
    interactions_data["export_run"] = {
        "export_dir_delta": len(after_dirs) - len(before_dirs),
        "export_jobs_table_delta_observed": after_export["exports"] - before_export["exports"],
        "success_prefix_visible": "Export:" in export_body,
    }
    interactions_data["no_duplicate_export"] = len(after_dirs) - len(before_dirs) == 1
    interactions_data["export_note"] = (
        "run_export persists files under research_exports/ and does not "
        "insert export_jobs rows; the directory delta is the duplicate-write metric."
    )
    page.screenshot(path=str(SHOTS / "en_1280x900_research_data_export.png"), full_page=False)
    context.close()

    # 4. Chinese Human Review labels (fresh context; probe-proven flow).
    zh_context = browser.new_context(viewport={"width": 1280, "height": 900})
    zh_page = zh_context.new_page()
    zh_page.goto(UI, timeout=30000, wait_until="networkidle")
    wait_stable(zh_page, expected="[data-testid='stAppViewContainer']")
    select_locale(zh_page, "zh_CN")
    select_role(zh_page, "research", "zh_CN")
    select_page(zh_page, "研究数据", "研究数据")
    activate_tab(zh_page, 4)
    zh_body = zh_page.evaluate("() => document.body.innerText")
    interactions_data["zh_research_data_labels"] = {
        "target_id_localized": "目标 ID" in zh_body,
        "english_target_id_absent": "Target ID" not in zh_body,
    }
    zh_page.screenshot(path=str(SHOTS / "zh_1280x900_research_data_human_review.png"), full_page=False)
    zh_context.close()

    # 5. Locale-switch side effects (read-only counts).
    counts_before = db_counts()
    switch_context = browser.new_context(viewport={"width": 1280, "height": 900})
    switch_page = switch_context.new_page()
    switch_page.goto(UI, timeout=30000, wait_until="networkidle")
    wait_stable(switch_page, expected="[data-testid='stAppViewContainer']")
    for lang in ("zh_CN", "en", "zh_CN", "en"):
        select_locale(switch_page, lang)
    interactions_data["locale_switch_no_writes"] = db_counts() == counts_before
    switch_context.close()

    results["interactions"] = interactions_data


def before_after_screenshots(browser) -> None:
    shots = [
        ("en", "student", "Home", "en_1280x900_student_home"),
        ("en", "student", "Writing", "en_1280x900_student_writing"),
        ("en", "student", "Feedback", "en_1280x900_student_feedback"),
        ("en", "student", "Learning Journey", "en_1280x900_student_journey"),
        ("en", "research", "Research Overview", "en_1280x900_research_overview"),
        ("en", "research", "Research Data", "en_1280x900_research_data"),
        ("en", "research", "System Audit", "en_1280x900_research_audit"),
        ("zh_CN", "student", "首页", "zh_390x844_student_home"),
    ]
    for lang, role, page_label, name in shots:
        mobile = "390x844" in name
        context = browser.new_context(viewport={"width": 390 if mobile else 1280, "height": 844 if mobile else 900})
        page = context.new_page()
        page.goto(UI, timeout=30000, wait_until="networkidle")
        wait_stable(page, expected="[data-testid='stAppViewContainer']")
        if lang == "zh_CN":
            select_locale(page, "zh_CN")
        if role == "research":
            select_role(page, "research", lang)
        expected = dict(PAGES[(lang, role)])[page_label]
        select_page(page, page_label, expected)
        page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=False)
        context.close()


def main() -> int:
    prepare_isolated_db()
    SHOTS.mkdir(parents=True, exist_ok=True)
    api = streamlit = None
    results: dict = {"matrix": {}, "interactions": {}, "timings": {}}
    try:
        api, streamlit = start_stack("final_matrix")
        t0 = time.monotonic()
        requests.get(f"{BASE}/api/v1/students/DEMO-001/journey", timeout=10)
        results["timings"]["journey_api_ms"] = round((time.monotonic() - t0) * 1000, 1)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            for lang in ("en", "zh_CN"):
                for viewport in ((1280, 900), (390, 844)):
                    for role in ("student", "research"):
                        ctx_result = run_matrix_context(browser, lang, viewport, role)
                        results["matrix"][ctx_result["combo"]] = ctx_result
            interactions(browser, results)
            before_after_screenshots(browser)

            # CSS injected exactly once (performance boundary).
            probe_ctx = browser.new_context(viewport={"width": 1280, "height": 900})
            probe = probe_ctx.new_page()
            probe.goto(UI, timeout=30000, wait_until="networkidle")
            wait_stable(probe, expected="[data-testid='stAppViewContainer']")
            results["css_injected_once"] = probe.evaluate(
                "() => [...document.querySelectorAll('style')].filter(s => s.innerHTML.includes('--px-dark:')).length"
            )
            probe_ctx.close()
            browser.close()

        matrix_ok = all(
            r["renders"]
            and all(v["ok"] for v in r["renders"].values())
            and not r["console_errors"]
            and not r["page_errors"]
            and not r["remote_requests"]
            for r in results["matrix"].values()
        )
        int_ok = (
            results["interactions"].get("writing_empty_prompt_blocked", {}).get("field_error_visible")
            and results["interactions"].get("writing_empty_prompt_blocked", {}).get("no_essay_written")
            and results["interactions"].get("no_duplicate_write_on_submit")
            and results["interactions"].get("journey_demo_events", {}).get("timeline_rendered")
            and results["interactions"].get("journey_empty_state", {}).get("empty_state_visible")
            and results["interactions"].get("no_duplicate_export")
            and results["interactions"].get("zh_research_data_labels", {}).get("target_id_localized")
            and results["interactions"].get("zh_research_data_labels", {}).get("english_target_id_absent")
            and results["interactions"].get("locale_switch_no_writes")
        )
        overall = matrix_ok and int_ok and results.get("css_injected_once") == 1
        results["_overall"] = "PASS" if overall else "FAIL"
        evidence = HERE / "phase7_acceptance_evidence.json"
        evidence.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(results, indent=2, ensure_ascii=False))
        print(f"PHASE 7 ACCEPTANCE: {results['_overall']} -> {evidence}")
        return 0 if overall else 1
    finally:
        stop_stack(api, streamlit)


if __name__ == "__main__":
    sys.exit(main())
