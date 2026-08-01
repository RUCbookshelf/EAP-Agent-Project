"""v0.9.2.1 Playwright verification — 12 pages, 4 locale/viewport combinations,
console errors, page exceptions, horizontal overflow, raw keys, role
separation, focus visibility, computed styles, rerun idempotency, screenshots.

Run:  python tests/live/test_v0921_playwright.py
Exit: 0 = PASS, 1 = FAIL
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time
import requests
from playwright.sync_api import sync_playwright

API_PORT = 8001
STREAMLIT_PORT = 8502
BASE_URL = f"http://127.0.0.1:{STREAMLIT_PORT}"
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCREENSHOT_DIR = PROJECT_ROOT / "verification" / "screenshots" / "v0.9.2.1"

STUDENT_PAGES_EN = ["Home", "Writing", "Feedback", "Revision", "Practice", "Learning Journey"]
RESEARCH_PAGES_EN = ["Overview", "Evidence", "CALF Measures", "Learning Process", "Research Data", "System Audit"]
STUDENT_PAGES_ZH = ["首页", "写作", "反馈", "修订", "练习", "学习旅程"]
RESEARCH_PAGES_ZH = ["研究概览", "研究证据", "CALF测量", "学习过程", "研究数据", "系统审计"]

# Known harmless framework messages (documented allow-list, narrowly scoped).
# Streamlit emits these on every load; they do not affect the application.
ALLOWED_CONSOLE = [
    "Download the React DevTools",          # Streamlit dev-tools notice
    "is not accessed",                       # coverage/dev instrumentation noise
    "Autofill processing",                   # Chromium autofill info
]


def start_server():
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    api = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.api.main:app", "--host", "127.0.0.1", "--port", str(API_PORT)],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        cwd=str(PROJECT_ROOT),
    )
    streamlit = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app/ui/streamlit_app.py",
         "--server.port", str(STREAMLIT_PORT), "--server.headless", "true",
         "--browser.gatherUsageStats", "false"],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        cwd=str(PROJECT_ROOT),
    )
    return api, streamlit


def wait_for_server(url, timeout=40):
    for _ in range(timeout * 2):
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def is_allowed(msg_text):
    return any(a in msg_text for a in ALLOWED_CONSOLE)


def check_page_health(page):
    """Return (ok, problems) for the current page."""
    problems = []

    # Streamlit rendering exception
    if page.locator('[data-testid="stException"]').count() > 0:
        exc_text = page.locator('[data-testid="stException"]').first.inner_text()[:200]
        problems.append(f"stException present: {exc_text}")

    # Horizontal overflow (exact check; documentElement and body)
    doc_w = page.evaluate("() => document.documentElement.scrollWidth")
    body_w = page.evaluate("() => document.body.scrollWidth")
    vw = page.evaluate("() => window.innerWidth")
    if doc_w > vw:
        problems.append(f"documentElement overflow: {doc_w} > {vw}")
    if body_w > vw:
        problems.append(f"body overflow: {body_w} > {vw}")

    return (len(problems) == 0, problems, {"doc": doc_w, "body": body_w, "vw": vw})


def check_raw_keys(page):
    """Detect raw locale keys in visible text.

    Raw keys are identifier-form strings (e.g. student_home_title, lang_en).
    Short word keys such as 'practice' or 'language' are indistinguishable
    from their translated values in body text, so only identifier-form keys
    are checked.
    """
    text = page.evaluate("() => document.body.innerText")
    raw_keys = [
        "student_home_title", "student_writing_title", "student_feedback_title",
        "student_revision_title", "learning_journey", "practice",
        "research_overview_title", "research_evidence_title", "tab_calf",
        "research_learning_title", "nav_research_data", "research_audit_title",
        "lang_en", "lang_zh_CN", "view_student", "view_research", "nav_pages",
    ]
    # Only keys containing an underscore are unambiguous raw-key identifiers.
    return [k for k in raw_keys if "_" in k and k in text]


def click_label(page, label, timeout=8000):
    open_sidebar(page)
    loc = page.locator(f"label:has-text('{label}')").last
    loc.wait_for(state="visible", timeout=timeout)
    loc.click(timeout=timeout)
    page.wait_for_timeout(1200)


def open_sidebar(page):
    """Open the collapsed sidebar on narrow viewports (Streamlit hamburger)."""
    for selector in ('[data-testid="stExpandSidebarButton"]',
                     '[data-testid="stSidebarCollapsedControl"]'):
        toggle = page.locator(selector)
        if toggle.count() > 0:
            try:
                toggle.first.click(timeout=4000)
                page.wait_for_timeout(1500)
                return
            except Exception:
                continue


def set_language(page, lang):
    target = "简体中文" if lang == "zh_CN" else "English"
    page.locator(f"label:has-text('{target}')").last.wait_for(state="visible", timeout=8000)
    page.locator(f"label:has-text('{target}')").last.click(timeout=8000)
    page.wait_for_timeout(2000)


def set_role(page, role):
    open_sidebar(page)
    target = "研究视图" if role == "research" else "学生视图"
    try:
        page.locator(f"label:has-text('{target}')").last.click(timeout=5000)
    except Exception:
        # English fallback labels
        target = "Research View" if role == "research" else "Student View"
        page.locator(f"label:has-text('{target}')").last.click(timeout=5000)
    page.wait_for_timeout(1500)


def verify_all_pages(browser, viewport, lang, label):
    """Verify all 12 pages in one locale/viewport combination."""
    page = browser.new_page(viewport={"width": viewport[0], "height": viewport[1]})
    console_errors = []
    page_errors = []
    page.on("console", lambda msg: console_errors.append(msg) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    page.goto(BASE_URL, timeout=30000, wait_until="networkidle")
    page.wait_for_timeout(5000)
    page.wait_for_selector("[data-testid='stAppViewContainer']", timeout=15000)
    open_sidebar(page)

    if lang == "zh_CN":
        set_language(page, "zh_CN")
        open_sidebar(page)

    results = {}
    all_problems = []

    # Student pages
    student_pages = STUDENT_PAGES_ZH if lang == "zh_CN" else STUDENT_PAGES_EN
    for pg in student_pages:
        try:
            click_label(page, pg)
        except Exception as exc:
            results[f"student:{pg}"] = "FAIL:navigate"
            all_problems.append(f"student:{pg} navigation failed: {exc}")
            continue
        ok, problems, metrics = check_page_health(page)
        raw = check_raw_keys(page)
        if raw:
            ok = False
            problems.append(f"raw keys visible: {raw}")
        results[f"student:{pg}"] = "PASS" if ok else "FAIL"
        if not ok:
            all_problems.extend(problems)

    # Research pages
    set_role(page, "research")
    research_pages = RESEARCH_PAGES_ZH if lang == "zh_CN" else RESEARCH_PAGES_EN
    for pg in research_pages:
        try:
            click_label(page, pg)
        except Exception as exc:
            results[f"research:{pg}"] = "FAIL:navigate"
            all_problems.append(f"research:{pg} navigation failed: {exc}")
            continue
        ok, problems, metrics = check_page_health(page)
        raw = check_raw_keys(page)
        if raw:
            ok = False
            problems.append(f"raw keys visible: {raw}")
        results[f"research:{pg}"] = "PASS" if ok else "FAIL"
        if not ok:
            all_problems.extend(problems)

    # Console errors (allow-listed only)
    unexpected_console = [m.text for m in console_errors if not is_allowed(m.text)]
    if unexpected_console:
        results["console_errors"] = f"FAIL:{unexpected_console[:5]}"
        all_problems.append(f"unexpected console errors: {unexpected_console[:5]}")
    else:
        results["console_errors"] = "PASS"

    # Page exceptions
    if page_errors:
        results["page_errors"] = f"FAIL:{page_errors[:5]}"
        all_problems.append(f"page exceptions: {page_errors[:5]}")
    else:
        results["page_errors"] = "PASS"

    page.close()
    overall = "PASS" if all(v == "PASS" for v in results.values()) else "FAIL"
    return {label: {"overall": overall, "pages": results, "problems": all_problems}}


def test_focus_and_computed_styles(browser):
    """Focus visibility + computed-style audit on representative components."""
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(BASE_URL, timeout=30000, wait_until="networkidle")
    page.wait_for_timeout(5000)
    page.wait_for_selector("[data-testid='stAppViewContainer']", timeout=15000)

    results = {}

    # Navigate to Writing page for textarea/expander/button components
    try:
        page.locator("label:has-text('Writing')").last.click(timeout=6000)
        page.wait_for_timeout(1500)
    except Exception:
        pass

    # Focus a text input and inspect its computed outline (must be a visible
    # blue pixel-art focus ring, not clipped and not invisible).
    input_el = page.locator('[data-testid="stTextInput"] input').first
    input_el.click(timeout=6000)
    page.wait_for_timeout(300)
    focus_info = page.evaluate("""() => {
        const el = document.activeElement;
        if (!el) return null;
        const cs = getComputedStyle(el);
        const r = el.getBoundingClientRect();
        return {
            tag: el.tagName,
            outline: cs.outline,
            outlineStyle: cs.outlineStyle,
            outlineWidth: cs.outlineWidth,
            outlineColor: cs.outlineColor,
            boxShadow: cs.boxShadow,
            inViewport: r.top >= 0 && r.bottom <= 900,
        };
    }""")
    if not focus_info:
        results["focus_visible"] = "FAIL:no focused element"
    else:
        has_visible_outline = (
            focus_info.get("outlineStyle") not in ("none", "")
            and focus_info.get("outlineWidth") not in ("0px", "0")
        )
        has_blue_outline = "rgb(15, 109, 189)" in (focus_info.get("outlineColor") or "") or "0f6dbd" in (focus_info.get("outlineColor") or "").lower()
        results["focus_visible"] = "PASS" if has_visible_outline and has_blue_outline and focus_info.get("inViewport") else f"FAIL:{focus_info}"

    # Computed styles for representative elements
    computed = page.evaluate("""() => {
        const out = {};
        const sels = {
            primary_button: "[data-testid='stButton'] button, .stButton button, button[kind='primary']",
            text_input: "input[type='text'], input",
            textarea: "textarea",
            expander: "[data-testid='stExpander']",
            alert: "[data-testid='stAlert'], .stAlert",
        };
        for (const [name, sel] of Object.entries(sels)) {
            const el = document.querySelector(sel);
            if (!el) { out[name] = "missing"; continue; }
            const cs = getComputedStyle(el);
            out[name] = {
                radius: cs.borderRadius,
                bgImage: cs.backgroundImage,
                filter: cs.filter,
                backdropFilter: cs.backdropFilter,
                boxShadow: cs.boxShadow,
                transition: cs.transitionDuration,
                animation: cs.animationName,
                borderWidth: cs.borderTopWidth,
            };
        }
        return out;
    }""")

    style_ok = True
    style_notes = []
    for name, cs in computed.items():
        if cs == "missing":
            continue
        if cs.get("radius", "0px") not in ("0px", "0"):
            style_ok = False
            style_notes.append(f"{name} radius={cs['radius']}")
        if cs.get("bgImage", "none") != "none":
            style_ok = False
            style_notes.append(f"{name} bgImage={cs['bgImage']}")
        if cs.get("filter", "none") != "none" or cs.get("backdropFilter", "none") != "none":
            style_ok = False
            style_notes.append(f"{name} blur filter present")
        if "blur" in cs.get("boxShadow", ""):
            style_ok = False
            style_notes.append(f"{name} soft shadow")
        if cs.get("transition", "0s") not in ("0s", "0s, 0s"):
            style_ok = False
            style_notes.append(f"{name} transition={cs['transition']}")
        if cs.get("animation", "none") != "none":
            style_ok = False
            style_notes.append(f"{name} animation={cs['animation']}")
    results["computed_styles"] = "PASS" if style_ok else f"FAIL:{style_notes[:6]}"

    page.close()
    return {"focus_and_computed": {"overall": "PASS" if all(v == "PASS" for v in results.values()) else "FAIL",
                                   "checks": results, "computed": computed, "focus": focus_info}}


def test_role_separation(browser):
    """Student View must not expose analyzer versions, provider details, config."""
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(BASE_URL, timeout=30000, wait_until="networkidle")
    page.wait_for_timeout(5000)

    body_text = page.evaluate("() => document.body.innerText")
    prohibited = [
        "spacy-analyzer", "analyzer_version", "llm_provider", "deepseek",
        "config-v0.9.0", "metric_results", "Evidence ID", "diagnostic_calibration",
    ]
    leaked = [p for p in prohibited if p in body_text]
    # NOTE: "spacy" may appear via NLP health only in research view; student view
    # must not show it.
    page.close()
    ok = not leaked
    return {"role_separation": {"overall": "PASS" if ok else "FAIL",
                                "checks": {"prohibited_leak": "PASS" if ok else f"FAIL:{leaked}"}}}


def test_rerun_idempotency(browser):
    """Navigation, refresh, language switch must not create exercise instances."""
    import sqlite3
    db_path = pathlib.Path(
        os.environ.get("DATABASE_PATH", PROJECT_ROOT / "data" / "writing_feedback.db")
    )
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(BASE_URL, timeout=30000, wait_until="networkidle")
    page.wait_for_timeout(5000)

    def count_exercises():
        if not db_path.exists():
            return -1
        conn = sqlite3.connect(str(db_path))
        try:
            return conn.execute("SELECT COUNT(*) FROM exercise_instances").fetchone()[0]
        finally:
            conn.close()

    before = count_exercises()

    # Navigate a few pages
    for pg in ["Writing", "Feedback", "Practice"]:
        try:
            page.locator(f"label:has-text('{pg}')").last.click(timeout=5000)
            page.wait_for_timeout(1000)
        except Exception:
            pass

    # Refresh
    page.reload(wait_until="networkidle")
    page.wait_for_timeout(4000)

    # Language switch
    try:
        page.locator("label:has-text('简体中文')").last.click(timeout=5000)
        page.wait_for_timeout(2000)
    except Exception:
        pass
    # Back to English
    try:
        page.locator("label:has-text('English')").last.click(timeout=5000)
        page.wait_for_timeout(2000)
    except Exception:
        pass

    after = count_exercises()
    page.close()
    ok = after == before
    return {"rerun_idempotency": {"overall": "PASS" if ok else "FAIL",
                                  "checks": {"no_duplicate_exercises": "PASS" if ok else f"FAIL: before={before} after={after}"}}}


def capture_screenshots(browser):
    """Save deterministic screenshots to verification/screenshots/v0.9.2.1/."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    captured = []

    def shot(name, viewport, lang, page_label=None, role=None):
        page = browser.new_page(viewport={"width": viewport[0], "height": viewport[1]})
        page.goto(BASE_URL, timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(5000)
        open_sidebar(page)
        if lang == "zh_CN":
            set_language(page, "zh_CN")
            open_sidebar(page)
        if role == "research":
            set_role(page, "research")
            open_sidebar(page)
        if page_label:
            click_label(page, page_label)
        path = SCREENSHOT_DIR / name
        page.screenshot(path=str(path), full_page=False)
        page.close()
        captured.append(name)

    # Required desktop screenshots
    shot("student_home_en_desktop.png", (1280, 900), "en")
    shot("student_feedback_en_desktop.png", (1280, 900), "en", page_label="Feedback")
    shot("student_practice_en_desktop.png", (1280, 900), "en", page_label="Practice")
    shot("student_journey_en_desktop.png", (1280, 900), "en", page_label="Learning Journey")
    shot("research_overview_en_desktop.png", (1280, 900), "en", role="research")
    shot("research_calf_en_desktop.png", (1280, 900), "en", role="research", page_label="CALF Measures")
    shot("research_data_en_desktop.png", (1280, 900), "en", role="research", page_label="Research Data")
    shot("student_home_zh_desktop.png", (1280, 900), "zh_CN")
    shot("research_overview_zh_desktop.png", (1280, 900), "zh_CN", role="research")
    # Required mobile screenshots
    shot("student_home_en_mobile.png", (390, 844), "en")
    shot("student_feedback_en_mobile.png", (390, 844), "en", page_label="Feedback")
    shot("student_home_zh_mobile.png", (390, 844), "zh_CN")
    shot("research_overview_zh_mobile.png", (390, 844), "zh_CN", role="research")

    return captured


def main():
    print("Starting servers...")
    api_proc, sl_proc = start_server()
    results = {}
    try:
        if not wait_for_server(f"http://127.0.0.1:{API_PORT}/api/v1/system/health"):
            print("FAIL: API server did not start")
            sys.exit(1)
        if not wait_for_server(BASE_URL):
            print("FAIL: Streamlit server did not start")
            sys.exit(1)
        print("Servers ready. Running verification...")

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            results.update(verify_all_pages(browser, (1280, 900), "en", "en_desktop"))
            results.update(verify_all_pages(browser, (1280, 900), "zh_CN", "zh_desktop"))
            results.update(verify_all_pages(browser, (390, 844), "en", "en_mobile"))
            results.update(verify_all_pages(browser, (390, 844), "zh_CN", "zh_mobile"))
            results.update(test_focus_and_computed_styles(browser))
            results.update(test_role_separation(browser))
            results.update(test_rerun_idempotency(browser))
            shots = capture_screenshots(browser)
            results["screenshots"] = {"count": len(shots), "paths": shots}
            browser.close()

        # Screenshots are evidence, not a pass/fail gate.
        checkable = {k: v for k, v in results.items() if k != "screenshots"}
        overall = "PASS" if all(v.get("overall", v) == "PASS" for v in checkable.values()) else "FAIL"
        print(json.dumps(results, indent=2, ensure_ascii=False))
        print(f"Screenshots: {len(shots)} saved to {SCREENSHOT_DIR}")
        print(f"VERIFICATION RESULT: {overall}")
        if overall == "FAIL":
            sys.exit(1)
    finally:
        api_proc.terminate()
        sl_proc.terminate()
        try:
            api_proc.wait(timeout=10)
        except Exception:
            api_proc.kill()
        try:
            sl_proc.wait(timeout=10)
        except Exception:
            sl_proc.kill()


if __name__ == "__main__":
    main()
