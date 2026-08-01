"""v0.9.4-A representative browser suite — 24 renders.

Six pages x four combinations (en/zh_CN x desktop/mobile), with a FRESH
browser context per (combination x role) as required by the execution-
correction instructions. Uses the shared semantic-state harness.

Checks: readable sans body, deliberate mono technical roles, primary-action
computed styling, contrast-relevant colors, visible focus, 44px touch
targets on mobile, no raw keys, no console errors, no page exceptions, no
page-level overflow, correct Chinese labels.

Run: python verification/v0.9.4-a/v0.9.4-a-20260801-r1/representative_suite.py
"""

from __future__ import annotations

import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from v094a_harness import (  # noqa: E402
    UI,
    activate_tab,
    current_h2,
    is_allowed_console,
    prepare_isolated_db,
    select_locale,
    select_page,
    select_role,
    start_stack,
    stop_stack,
    wait_stable,
)

RAW_KEYS = [
    "student_home_title", "student_writing_title", "student_feedback_title",
    "student_revision_title", "learning_journey", "practice",
    "research_overview_title", "research_evidence_title", "tab_calf",
    "research_learning_title", "nav_research_data", "research_audit_title",
    "lang_en", "lang_zh_CN", "view_student", "view_research", "nav_pages",
    "human_review_target_id", "export_run_success", "journey_counts_label",
]

STUDENT_PAGES = {"en": ["Home", "Writing", "Feedback"], "zh_CN": ["首页", "写作", "反馈"]}
RESEARCH_PAGES = {
    "en": ["Research Overview", "Research Data", "System Audit"],
    "zh_CN": ["研究概览", "研究数据", "系统审计"],
}
EXPECTED_H2 = {
    "en": {"Home": "Home", "Writing": "Writing", "Feedback": "Feedback",
           "Research Overview": "Research Overview", "Research Data": "Research Data",
           "System Audit": "System Audit"},
    "zh_CN": {"首页": "首页", "写作": "写作", "反馈": "反馈",
              "研究概览": "研究概览", "研究数据": "研究数据", "系统审计": "系统审计"},
}


def check_render(page, page_label: str, *, mobile: bool, research: bool) -> dict:
    problems: list[str] = []
    if page.locator('[data-testid="stException"]').count() > 0:
        problems.append("stException: " + page.locator('[data-testid="stException"]').first.inner_text()[:120])

    vw = page.evaluate("() => window.innerWidth")
    doc_w = page.evaluate("() => document.documentElement.scrollWidth")
    body_w = page.evaluate("() => document.body.scrollWidth")
    if doc_w > vw or body_w > vw:
        problems.append(f"overflow doc={doc_w} body={body_w} vw={vw}")

    text = page.evaluate("() => document.body.innerText")
    raw = [k for k in RAW_KEYS if "_" in k and k in text]
    if raw:
        problems.append(f"raw keys: {raw}")

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

    # Primary action computed styling on pages that own one.
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
                         animation: s.animationName, minHeight: s.minHeight,
                         h: r.height, w: r.width };
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
            min_ok = (44 if mobile else 40)
            if cs["h"] < min_ok or cs["w"] <= 0:
                problems.append(f"primary undersized h={cs['h']} w={cs['w']}")

    # Focus visibility on the Writing page.
    if page_label in ("Writing", "写作"):
        # Programmatic focus avoids pointer interception by the mobile
        # sidebar overlay; the CSS `:focus` outline still applies.
        page.evaluate(
            "() => { const el = document.querySelector('[data-testid=\"stTextInput\"] input'); "
            "if (el) el.focus(); }"
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
        elif "29adff" not in focus["color"].lower() and "41, 173, 255" not in focus["color"]:
            problems.append(f"focus color unexpected: {focus['color']}")

    # Chinese Research Data labels.
    if page_label in ("研究数据",):
        tab_labels = page.evaluate(
            "() => [...document.querySelectorAll('[role=tab]')].map(t => t.innerText.trim())"
        )
        if "人工复核" not in tab_labels:
            problems.append(f"zh tab labels: {tab_labels}")
        activate_tab(page, 4)
        body = page.evaluate("() => document.body.innerText")
        if "目标 ID" not in body or "Target ID" in body:
            problems.append("zh Human Review labels wrong")

    return {
        "page": page_label,
        "ok": not problems,
        "problems": problems,
        "fonts": fonts,
    }


def run_context(browser, lang: str, viewport: tuple, role: str) -> dict:
    mobile = viewport[0] < 700
    context = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
    page = context.new_page()
    console_errors: list[str] = []
    page_errors: list[str] = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))
    page.goto(UI, timeout=30000, wait_until="networkidle")
    wait_stable(page, expected="[data-testid='stAppViewContainer']")
    if lang == "zh_CN":
        select_locale(page, "zh_CN")
    if role == "research":
        select_role(page, "research", lang)

    page_map = RESEARCH_PAGES[lang] if role == "research" else STUDENT_PAGES[lang]
    renders = {}
    for label in page_map:
        expected_h2 = EXPECTED_H2[lang][label]
        select_page(page, label, expected_h2)
        renders[label] = check_render(page, label, mobile=mobile, research=(role == "research"))
    unexpected = [m for m in console_errors if not is_allowed_console(m)]
    context.close()
    return {
        "combo": f"{lang}_{viewport[0]}x{viewport[1]}_{role}",
        "renders": renders,
        "console_errors": unexpected[:5],
        "page_errors": page_errors[:5],
    }


def main() -> int:
    prepare_isolated_db()
    api = streamlit = None
    try:
        api, streamlit = start_stack("representative")
        results = []
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            for lang in ("en", "zh_CN"):
                for viewport in ((1280, 900), (390, 844)):
                    for role in ("student", "research"):
                        results.append(run_context(browser, lang, viewport, role))
            browser.close()

        ok = all(
            r["renders"]
            and all(v["ok"] for v in r["renders"].values())
            and not r["console_errors"]
            and not r["page_errors"]
            for r in results
        )
        evidence = HERE / "representative_evidence.json"
        evidence.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        for r in results:
            print(json.dumps(r, indent=2, ensure_ascii=False))
        print(f"REPRESENTATIVE SUITE: {'PASS' if ok else 'FAIL'} (24 renders) -> {evidence}")
        return 0 if ok else 1
    finally:
        stop_stack(api, streamlit)


if __name__ == "__main__":
    sys.exit(main())
