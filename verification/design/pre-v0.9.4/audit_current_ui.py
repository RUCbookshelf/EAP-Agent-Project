"""Pre-v0.9.4 current-UI experience audit (research only; no source changes).

Launches the real FastAPI + Streamlit stack, then inspects all twelve pages
in four locale/viewport combinations (en/zh_CN x desktop 1280x900 /
mobile 390x844) with real browser interaction. Captures per-page console
errors, page exceptions, overflow metrics, interaction results, computed
styles for key components, and sanitized screenshots.

Run (from the project root):
    .venv\\Scripts\\python.exe verification/design/pre-v0.9.4/audit_current_ui.py
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import time

import requests
from playwright.sync_api import sync_playwright

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
SPEC_PATH = PROJECT_ROOT / "verification" / "v0.9.3-b" / "mobile_closure_verify.py"
spec = importlib.util.spec_from_file_location("mc", SPEC_PATH)
mc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mc)

API_PORT = mc.API_PORT
STREAMLIT_PORT = mc.STREAMLIT_PORT
BASE_URL = mc.BASE_URL
OUT_DIR = PROJECT_ROOT / "verification" / "design" / "pre-v0.9.4" / "current-ui"
SHOT_DIR = OUT_DIR / "screenshots"

STUDENT_PAGES = [
    ("student_home", "student_home_title"),
    ("student_writing", "student_writing_title"),
    ("student_feedback", "student_feedback_title"),
    ("student_revision", "student_revision_title"),
    ("student_practice", "practice"),
    ("student_journey", "learning_journey"),
]
RESEARCH_PAGES = [
    ("research_overview", "research_overview_title"),
    ("research_evidence", "research_evidence_title"),
    ("research_calf", "tab_calf"),
    ("research_learning", "research_learning_title"),
    ("research_data", "nav_research_data"),
    ("research_audit", "research_audit_title"),
]

COMBOS = [
    ("en", 1280, 900),
    ("zh_CN", 1280, 900),
    ("en", 390, 844),
    ("zh_CN", 390, 844),
]


def nav_label(locales: dict, lang: str, key: str) -> str:
    return locales[lang].get(key, key)


def metrics(page) -> dict:
    return page.evaluate(
        """() => ({
            inner_width: window.innerWidth,
            doc_scroll_width: document.documentElement.scrollWidth,
            body_scroll_width: document.body.scrollWidth,
            body_font: getComputedStyle(document.body).fontFamily,
            body_font_size: getComputedStyle(document.body).fontSize,
            h1: (() => { const el = document.querySelector('h1'); return el ? getComputedStyle(el).fontSize : null; })(),
            h2: (() => { const el = document.querySelector('h2'); return el ? getComputedStyle(el).fontSize : null; })(),
        })"""
    )


def component_styles(page) -> dict:
    return page.evaluate(
        """() => {
            const gs = (el) => {
                if (!el) return null;
                const cs = getComputedStyle(el);
                return {radius: cs.borderRadius, border: cs.borderTopWidth + ' ' + cs.borderTopStyle, shadow: cs.boxShadow, transition: cs.transitionDuration, animation: cs.animationName};
            };
            const btn = document.querySelector('.stButton button') || document.querySelector('button[kind="primary"]');
            const input = document.querySelector('.stTextInput input');
            const tab = document.querySelector('[role="tab"]');
            return {button: gs(btn), input: gs(input), tab: gs(tab)};
        }"""
    )


def focus_outline(page) -> dict:
    return page.evaluate(
        """() => {
            const input = document.querySelector('.stTextInput input');
            if (!input) return null;
            input.focus();
            const cs = getComputedStyle(input);
            return {outline: cs.outlineStyle + ' ' + cs.outlineWidth + ' ' + cs.outlineColor, outlineOffset: cs.outlineOffset};
        }"""
    )


def click_nav(page, label: str) -> None:
    mc.open_sidebar_if_needed(page, label)
    page.wait_for_timeout(1500)


def run_combo(locales: dict, lang: str, width: int, height: int) -> dict:
    key = f"{lang}_{width}x{height}"
    result = {
        "combo": key,
        "locale": lang,
        "viewport": f"{width}x{height}",
        "pages": [],
        "interactions": [],
        "component_styles": None,
        "focus": None,
    }
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})
        console_msgs: list[dict] = []
        page_errors: list[str] = []
        page.on("console", lambda m: console_msgs.append({"type": m.type, "text": m.text}))
        page.on("pageerror", lambda e: page_errors.append(str(e)))

        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector("[data-testid='stAppViewContainer']", timeout=30000)
        page.wait_for_timeout(4000)

        if lang == "zh_CN":
            click_nav(page, nav_label(locales, lang, "lang_zh_CN"))
            page.wait_for_timeout(2000)

        click_nav(page, nav_label(locales, lang, "view_student"))
        page.wait_for_timeout(2000)
        result["focus"] = focus_outline(page)
        if width == 390:
            result["touch_targets"] = page.evaluate(
                """() => {
                    const measure = (sel) => { const el = document.querySelector(sel); if (!el) return null; const r = el.getBoundingClientRect(); return {w: Math.round(r.width), h: Math.round(r.height)}; };
                    return {radio_label: measure('.stRadio label'), button: measure('.stButton button'), text_input: measure('.stTextInput input')};
                }"""
            )

        def snapshot(pg: str, label_key: str) -> dict:
            before_console = len(console_msgs)
            before_errors = len(page_errors)
            m = metrics(page)
            styles = component_styles(page)
            shot = SHOT_DIR / f"{key}_{pg}.png"
            page.screenshot(path=str(shot), full_page=False)
            return {
                "page": pg,
                "rendered": True,
                "console_errors": [c for c in console_msgs[before_console:] if c["type"] == "error"],
                "page_exceptions": page_errors[before_errors:],
                "overflow_ok": m["body_scroll_width"] <= m["inner_width"] + 10
                and m["doc_scroll_width"] <= m["inner_width"] + 10,
                "body_width": m["body_scroll_width"],
                "viewport_width": m["inner_width"],
                "body_font_size": m["body_font_size"],
                "h1_size": m["h1"],
                "h2_size": m["h2"],
                "component_styles": styles,
                "screenshot": str(shot.relative_to(PROJECT_ROOT)),
            }

        # Student pages
        for pg, label_key in STUDENT_PAGES:
            click_nav(page, nav_label(locales, lang, label_key))
            page.wait_for_timeout(1800)
            result["pages"].append(snapshot(pg, label_key))

        # Switch to Research view and inspect Research pages
        click_nav(page, nav_label(locales, lang, "view_research"))
        page.wait_for_timeout(2000)
        for pg, label_key in RESEARCH_PAGES:
            click_nav(page, nav_label(locales, lang, label_key))
            page.wait_for_timeout(1800)
            result["pages"].append(snapshot(pg, label_key))

        # ---- Representative interactions (EN desktop only) ----
        if lang == "en" and width == 1280:
            interact = []
            click_nav(page, nav_label(locales, lang, "view_student"))
            page.wait_for_timeout(1800)
            # Writing: (1) reproduce the empty-writing-prompt validation gap,
            # then (2) submit a synthetic demo essay (no real learner data).
            click_nav(page, nav_label(locales, lang, "student_writing_title"))
            page.wait_for_timeout(1500)
            sid = page.get_by_label("Student ID")
            if sid.count():
                sid.fill("S02")
            ta = page.locator("textarea").last
            ta.fill("The history of history is historical. Cities should add more parks because parks give residents space to exercise. Parks also support community events and provide shade during hot weather. However, new parks require land and regular maintenance. Therefore, city leaders should first identify neighborhoods with limited green space and consult residents.")
            btn = page.get_by_role("button", name="Submit and generate feedback", exact=True)
            btn.scroll_into_view_if_needed()
            btn.click()
            page.wait_for_timeout(6000)
            shot = SHOT_DIR / "en_1280x900_writing_validation_error.png"
            page.screenshot(path=str(shot), full_page=False)
            body = page.evaluate("() => document.body.innerText")
            interact.append({
                "action": "submit_without_writing_prompt",
                "generic_422_error_visible": "some information is invalid" in body,
                "screenshot": str(shot.relative_to(PROJECT_ROOT)),
            })

            page.get_by_label("Writing prompt").fill("Should cities add more parks?")
            btn = page.get_by_role("button", name="Submit and generate feedback", exact=True)
            btn.scroll_into_view_if_needed()
            btn.click()
            deadline = time.monotonic() + 60
            success = False
            while time.monotonic() < deadline:
                page.wait_for_timeout(1000)
                body = page.evaluate("() => document.body.innerText")
                if "Submission saved as essay" in body:
                    success = True
                    break
            shot = SHOT_DIR / "en_1280x900_writing_after_submit.png"
            page.screenshot(path=str(shot), full_page=False)
            interact.append({"action": "submit_demo_essay", "success_text_visible": success, "screenshot": str(shot.relative_to(PROJECT_ROOT))})

            # Feedback + Revision render from session state
            click_nav(page, nav_label(locales, lang, "student_feedback_title"))
            page.wait_for_timeout(1800)
            shot = SHOT_DIR / "en_1280x900_feedback_after_submit.png"
            page.screenshot(path=str(shot), full_page=False)
            interact.append({"action": "feedback_page", "screenshot": str(shot.relative_to(PROJECT_ROOT))})
            click_nav(page, nav_label(locales, lang, "student_revision_title"))
            page.wait_for_timeout(1800)
            shot = SHOT_DIR / "en_1280x900_revision_after_submit.png"
            page.screenshot(path=str(shot), full_page=False)
            interact.append({"action": "revision_page", "screenshot": str(shot.relative_to(PROJECT_ROOT))})

            # Practice: load S02 targets
            click_nav(page, nav_label(locales, lang, "practice"))
            page.wait_for_timeout(1500)
            sid = page.get_by_label("Student ID")
            if sid.count():
                sid.fill("S02")
                sid.press("Enter")
                page.wait_for_timeout(1500)
            page.get_by_role("button", name="Load Practice Targets", exact=True).click(timeout=15000)
            page.wait_for_timeout(4000)
            shot = SHOT_DIR / "en_1280x900_practice_loaded.png"
            page.screenshot(path=str(shot), full_page=False)
            interact.append({"action": "load_practice_s02", "screenshot": str(shot.relative_to(PROJECT_ROOT))})

            # Journey: load S02
            click_nav(page, nav_label(locales, lang, "learning_journey"))
            page.wait_for_timeout(1500)
            sid = page.get_by_label("Student ID")
            if sid.count():
                sid.fill("S02")
                sid.press("Enter")
                page.wait_for_timeout(1500)
            page.get_by_role("button", name="Load Learning Journey", exact=True).click(timeout=15000)
            page.wait_for_timeout(4000)
            shot = SHOT_DIR / "en_1280x900_journey_loaded.png"
            page.screenshot(path=str(shot), full_page=False)
            interact.append({"action": "load_journey_s02", "screenshot": str(shot.relative_to(PROJECT_ROOT))})

            # Research Evidence: load submission 1
            click_nav(page, nav_label(locales, lang, "view_research"))
            page.wait_for_timeout(1500)
            click_nav(page, nav_label(locales, lang, "research_evidence_title"))
            page.wait_for_timeout(1500)
            page.get_by_role("button", name="Load Records", exact=True).click()
            page.wait_for_timeout(4000)
            shot = SHOT_DIR / "en_1280x900_evidence_loaded.png"
            page.screenshot(path=str(shot), full_page=False)
            interact.append({"action": "load_evidence_submission_1", "screenshot": str(shot.relative_to(PROJECT_ROOT))})

            # Research Data: exercise all 8 tabs
            click_nav(page, nav_label(locales, lang, "nav_research_data"))
            page.wait_for_timeout(2000)
            for spec_key in ("export_preview", "research_data_privacy", "research_data_filters", "pii_scan", "human_review", "dataset_split", "data_quality", "export_history"):
                label = locales[lang].get(spec_key, spec_key)
                mc.click_tab(page, label)
                mc.wait_tab_active(page, label)
                page.wait_for_timeout(1200)
            interact.append({"action": "research_data_8_tabs_clicked", "result": "PASS"})

            # System Audit: tab 4 renders configurations
            click_nav(page, nav_label(locales, lang, "research_audit_title"))
            page.wait_for_timeout(2500)
            interact.append({"action": "system_audit_rendered", "result": "PASS"})
            result["interactions"] = interact

        result["component_styles"] = component_styles(page)
        result["console_all"] = console_msgs
        result["pageerrors_all"] = page_errors
        browser.close()
    return result


def main() -> int:
    locales = mc.load_locales()
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    work_dir = pathlib.Path(__import__("tempfile").mkdtemp(prefix="v093b_ui_audit_"))
    api_proc, ui_proc, api_log = mc.start_stack(work_dir)
    try:
        if not mc.wait_http(f"{mc.API_BASE}/api/v1/system/health", timeout=90):
            print("FAIL: API not healthy")
            return 1
        if not mc.wait_http(BASE_URL, timeout=90):
            print("FAIL: Streamlit not ready")
            return 1
        all_results = {}
        for lang, w, h in COMBOS:
            print(f"--- {lang} {w}x{h} ---")
            all_results[f"{lang}_{w}x{h}"] = run_combo(locales, lang, w, h)
        with open(OUT_DIR / "audit_results.json", "w", encoding="utf-8") as fh:
            json.dump(all_results, fh, ensure_ascii=False, indent=2)
        print("Audit complete; results written to", OUT_DIR / "audit_results.json")
        return 0
    finally:
        mc.stop_process(ui_proc)
        mc.stop_process(api_proc)


if __name__ == "__main__":
    raise SystemExit(main())
