"""v0.9.4-A focused probe: zh locale -> Research role -> Research Data -> Human Review.

Gate: three consecutive clean runs (fresh stack + fresh browser context per
run, no console errors, no page exceptions, correct Chinese labels, correct
selected role/page/tab, process cleanup confirmed).

Run: python verification/v0.9.4-a/v0.9.4-a-20260801-r1/zh_nav_probe.py
"""

from __future__ import annotations

import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from v094a_harness import (  # noqa: E402
    BASE,
    UI,
    activate_tab,
    current_h2,
    dump_diagnostics,
    is_allowed_console,
    prepare_isolated_db,
    radio_indices,
    select_locale,
    select_page,
    select_role,
    start_stack,
    stop_stack,
    wait_stable,
)


def run_probe(run_number: int) -> dict:
    prepare_isolated_db()
    api = streamlit = None
    result: dict = {"run": run_number}
    try:
        api, streamlit = start_stack(f"zh_probe_r{run_number}")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            page = context.new_page()
            console_errors: list[str] = []
            page_errors: list[str] = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda exc: page_errors.append(str(exc)))

            page.goto(UI, timeout=30000, wait_until="networkidle")
            assert wait_stable(page, expected="[data-testid='stAppViewContainer']"), "app did not stabilize"

            ok_locale = select_locale(page, "zh_CN")
            result["locale_selected"] = ok_locale
            result["radio_indices_after_locale"] = radio_indices(page)

            ok_role = select_role(page, "research", "zh_CN")
            result["role_selected"] = ok_role
            result["radio_indices_after_role"] = radio_indices(page)

            ok_page = select_page(page, "研究数据", "研究数据")
            result["page_selected"] = ok_page
            result["h2_after_page"] = current_h2(page)

            ok_tab = activate_tab(page, 4)
            result["tab_activated"] = ok_tab
            result["tab_selected_states"] = page.evaluate(
                "() => [...document.querySelectorAll('[role=tab]')].map(t => t.getAttribute('aria-selected'))"
            )

            body = page.evaluate("() => document.body.innerText")
            result["target_id_localized"] = "目标 ID" in body
            result["english_target_id_absent"] = "Target ID" not in body
            result["exception_count"] = page.locator('[data-testid="stException"]').count()
            result["console_errors"] = [m for m in console_errors if not is_allowed_console(m)][:5]
            result["page_errors"] = page_errors[:5]

            page.screenshot(path=str(HERE / "screenshots" / f"zh_probe_r{run_number}.png"), full_page=False)
            context.close()
            browser.close()

        result["pass"] = all(
            [
                result["locale_selected"],
                result["role_selected"],
                result["page_selected"],
                result["tab_activated"],
                result["target_id_localized"],
                result["english_target_id_absent"],
                result["exception_count"] == 0,
                not result["console_errors"],
                not result["page_errors"],
            ]
        )
        return result
    except Exception as exc:
        result["pass"] = False
        result["error"] = f"{type(exc).__name__}: {exc}"
        try:
            if "page" in locals():
                dump_diagnostics(page, HERE / "logs" / f"zh_probe_r{run_number}_diagnostics.json", "zh_probe")
        except Exception:
            pass
        return result
    finally:
        stop_stack(api, streamlit)


def main() -> int:
    results = [run_probe(i) for i in (1, 2, 3)]
    evidence = HERE / "zh_probe_evidence.json"
    evidence.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    for r in results:
        print(json.dumps(r, indent=2, ensure_ascii=False))
    overall = all(r.get("pass") for r in results)
    print(f"ZH NAV PROBE: {'PASS' if overall else 'FAIL'} (3 runs) -> {evidence}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
