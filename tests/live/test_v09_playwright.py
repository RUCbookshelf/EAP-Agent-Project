"""v0.9.1 Playwright verification — role-based UI, desktop + mobile, console errors, localization."""
import os, sys, pathlib, subprocess, time, requests, json
from playwright.sync_api import sync_playwright

API_PORT = 8001
STREAMLIT_PORT = 8502
BASE_URL = f"http://127.0.0.1:{STREAMLIT_PORT}"
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]


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


def wait_for_server(url, timeout=30):
    for _ in range(timeout * 2):
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def check_console(page):
    errors = [m for m in page._console if m.type == "error"]
    return errors


def check_horizontal_overflow(page):
    body_width = page.evaluate("() => document.body.scrollWidth")
    viewport_width = page.evaluate("() => window.innerWidth")
    return body_width <= viewport_width + 10, body_width, viewport_width


def test_desktop_student_view():
    """Desktop: Student View pages load without errors."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        console_msgs = []
        page.on("console", lambda msg: console_msgs.append(msg))

        page.goto(BASE_URL, timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(5000)
        page.wait_for_selector("[data-testid='stAppViewContainer']", timeout=15000)

        assert page.title(), "Page must have a title"

        # Navigate through Student View pages
        student_pages = ["Home", "Writing", "Feedback", "Revision", "Practice", "Learning Journey"]
        for pg in student_pages:
            try:
                page.locator(f"label:has-text('{pg}')").last.click(timeout=3000)
                page.wait_for_timeout(1000)
            except Exception:
                pass

        # Check console
        errors = [m for m in console_msgs if m.type == "error"]
        assert len(errors) == 0, f"Console errors: {[e.text for e in errors]}"

        # Check no horizontal overflow
        ok, bw, vw = check_horizontal_overflow(page)
        assert ok, f"Body width {bw} exceeds viewport {vw}"

        browser.close()
        return True


def test_desktop_research_view():
    """Desktop: Research View pages load without errors."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        console_msgs = []
        page.on("console", lambda msg: console_msgs.append(msg))

        page.goto(BASE_URL, timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(5000)

        # Switch to Research View
        try:
            page.locator("label:has-text('Research View')").click(timeout=5000)
            page.wait_for_timeout(2000)
        except Exception:
            pass

        # Navigate through Research View pages
        research_pages = ["Overview", "Evidence", "CALF Measures", "Learning Process", "Research Data", "System Audit"]
        for pg in research_pages:
            try:
                page.locator(f"label:has-text('{pg}')").last.click(timeout=3000)
                page.wait_for_timeout(1000)
            except Exception:
                pass

        errors = [m for m in console_msgs if m.type == "error"]
        assert len(errors) == 0, f"Console errors: {[e.text for e in errors]}"

        browser.close()
        return True


def test_mobile_390x844():
    """Mobile: app loads at 390x844 without horizontal overflow."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        console_msgs = []
        page.on("console", lambda msg: console_msgs.append(msg))

        page.goto(BASE_URL, timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(5000)

        assert page.title(), "Page must have a title"

        ok, bw, vw = check_horizontal_overflow(page)
        assert ok, f"Body width {bw} exceeds viewport {vw} at mobile"

        errors = [m for m in console_msgs if m.type == "error"]
        assert len(errors) == 0, f"Console errors: {[e.text for e in errors]}"

        browser.close()
        return True


def test_chinese_locale():
    """Switch to Chinese locale - no console errors."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        console_msgs = []
        page.on("console", lambda msg: console_msgs.append(msg))

        page.goto(BASE_URL, timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(5000)

        # Switch to Chinese
        try:
            page.locator("label:has-text('简体中文')").click(timeout=5000)
            page.wait_for_timeout(3000)
        except Exception:
            pass

        errors = [m for m in console_msgs if m.type == "error"]
        assert len(errors) == 0, f"Console errors after locale switch: {[e.text for e in errors]}"

        browser.close()
        return True


def test_no_raw_locale_keys():
    """Verify no raw locale keys appear as visible text."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        page.goto(BASE_URL, timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(5000)

        text = page.evaluate("() => document.body.innerText")

        # Common raw keys that should never appear
        raw_keys = ["tab_practice", "tab_learning_journey", "tab_practice_audit",
                     "student_home_title", "student_writing_title", "research_overview_title"]
        for key in raw_keys:
            assert key not in text, f"Raw locale key '{key}' appears in UI"

        browser.close()
        return True


def test_student_home_page():
    """Student Home page renders expected elements."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        page.goto(BASE_URL, timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(5000)

        # Should be on Student Home by default
        text = page.evaluate("() => document.body.innerText")
        assert "Home" in text or "首页" in text, "Home page not found"
        assert "prototype" in text.lower(), "Prototype warning not visible"

        browser.close()
        return True


if __name__ == "__main__":
    print("Starting servers...")
    api_proc, sl_proc = start_server()

    try:
        print("Waiting for servers...")
        if not wait_for_server(f"http://127.0.0.1:{API_PORT}/api/v1/system/health"):
            print("FAIL: API server did not start")
            sys.exit(1)
        if not wait_for_server(BASE_URL):
            print("FAIL: Streamlit server did not start")
            sys.exit(1)

        results = {}
        tests = [
            ("desktop_student", test_desktop_student_view),
            ("desktop_research", test_desktop_research_view),
            ("mobile_390x844", test_mobile_390x844),
            ("chinese_locale", test_chinese_locale),
            ("no_raw_keys", test_no_raw_locale_keys),
            ("student_home", test_student_home_page),
        ]
        for name, test_fn in tests:
            try:
                test_fn()
                results[name] = "PASS"
                print(f"  {name}: PASS")
            except Exception as e:
                results[name] = f"FAIL: {e}"
                print(f"  {name}: FAIL: {e}")

        print(json.dumps(results, indent=2))
        if any("FAIL" in v for v in results.values()):
            print("Playwright verification: FAIL")
            sys.exit(1)
        else:
            print("Playwright verification: PASS")
    finally:
        api_proc.terminate()
        sl_proc.terminate()
        api_proc.wait()
        sl_proc.wait()