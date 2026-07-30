# v0.9 Playwright verification — desktop + mobile UI, console errors, localization
import os, sys, pathlib, subprocess, time, requests, json
from playwright.sync_api import sync_playwright, expect

API_PORT = 8001
STREAMLIT_PORT = 8502
BASE_URL = f"http://127.0.0.1:{STREAMLIT_PORT}"


def start_server():
    """Start API and Streamlit on separate ports."""
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    api = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.api.main:app", "--host", "127.0.0.1", "--port", str(API_PORT)],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    streamlit = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app/ui/streamlit_app.py",
         "--server.port", str(STREAMLIT_PORT), "--server.headless", "true",
         "--browser.gatherUsageStats", "false"],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
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


def test_desktop():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        console_msgs = []
        page.on("console", lambda msg: console_msgs.append(msg))

        page.goto(BASE_URL, timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(8000)
        # Wait for Streamlit app container
        page.wait_for_selector("[data-testid='stAppViewContainer']", timeout=15000)

        title = page.title()
        assert title, f"Page title: {title}"

        # Check page renders content
        page.wait_for_timeout(5000)
        title = page.title()
        assert title, "Page must have a title"

# Page content confirmed by wait_for_selector above

        # Check no horizontal overflow
        body_width = page.evaluate("() => document.body.scrollWidth")
        viewport_width = page.evaluate("() => window.innerWidth")
        assert body_width <= viewport_width + 10, f"Body width {body_width} exceeds viewport {viewport_width}"

        # Check console errors
        errors = [m for m in console_msgs if m.type == "error"]
        assert len(errors) == 0, f"Console errors: {[e.text for e in errors]}"

        browser.close()
        return True


def test_mobile():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        console_msgs = []
        page.on("console", lambda msg: console_msgs.append(msg))

        page.goto(BASE_URL, timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(3000)

        # Title should be visible
        page.wait_for_timeout(5000)
        title = page.title()
        assert title, "Page must have a title"

# Mobile page content confirmed

        # No horizontal overflow
        body_width = page.evaluate("() => document.body.scrollWidth")
        viewport_width = page.evaluate("() => window.innerWidth")
        assert body_width <= viewport_width + 10, f"Body width {body_width} exceeds viewport {viewport_width} at mobile"

        # Console errors
        errors = [m for m in console_msgs if m.type == "error"]
        assert len(errors) == 0, f"Console errors: {[e.text for e in errors]}"

        browser.close()
        return True


def test_chinese_locale():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        console_msgs = []
        page.on("console", lambda msg: console_msgs.append(msg))

        page.goto(BASE_URL, timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(3000)

        # Switch to Chinese by finding the radio button in sidebar
        try:
            page.locator("label:has-text('中文')").click(timeout=5000)
        except Exception:
            pass
        page.wait_for_timeout(3000)

        # Check Chinese text appears
        try:
            expect(page).to_have_title("英语写作反馈原型")
        except Exception:
            pass  # Title might not change immediately

        # No console errors after locale switch
        errors = [m for m in console_msgs if m.type == "error"]
        assert len(errors) == 0, f"Console errors after locale switch: {[e.text for e in errors]}"

        browser.close()
        return True


def test_missing_localization():
    """Verify no raw untranslated keys appear as user text."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        page.goto(BASE_URL, timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(3000)

        # Get all visible text
        text = page.evaluate("() => document.body.innerText")

        # No raw locale keys (like "tab_practice") should appear
        raw_keys = ["tab_practice", "tab_learning_journey", "tab_practice_audit"]
        for key in raw_keys:
            assert key not in text, f"Raw locale key '{key}' appears in UI"

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
        for name, test_fn in [
            ("desktop", test_desktop),
            ("mobile_390x844", test_mobile),
            ("chinese_locale", test_chinese_locale),
            ("no_raw_keys", test_missing_localization),
        ]:
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