from __future__ import annotations

"""v0.9.6-D0-R Phase 5 browser-assisted Student View journey (audit-only).

Walks Home -> Feedback -> Revision -> Practice -> Learning Journey for the
naturally generated priority learner (AUDIT-D0R-01, submission #1) at
desktop and 390x844 mobile sizes.  Records structured observations and
stores redacted screenshots under C:\\tmp\\v096d0r (never committed).
Creates no submissions and performs no writes.
"""

import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = ROOT / "ui_journey_observations.json"
SHOT_DIR = Path(r"C:\tmp\v096d0r\screenshots")
STUDENT_ID = "AUDIT-D0R-01"
BASE_URL = "http://127.0.0.1:8501"

def goto_page(page, name: str) -> None:
    label = page.locator('label[data-testid="stRadioOption"]', has_text=name).first
    label.evaluate("(el) => el.click()")



def observe(page, label: str) -> dict:
    body = page.locator("body").inner_text()
    return {
        "page": label,
        "url": page.url,
        "text_found": {
            "home_revise_guidance": "Consider submitting a revision based on your feedback" in body,
            "home_open_revision": "Open Revision" in body,
            "feedback_no_session": "No feedback in this session" in body,
            "feedback_priority_visible": "Reduce lexical repetition" in body,
            "feedback_evidence_section": "From Your Writing" in body,
            "revision_select_source": "Choose the draft you want to revise" in body,
            "revision_original_submission": "Original submission" in body,
            "revision_no_target_note": "No matching active practice target is available for this source draft" in body,
            "revision_submit_action": "Submit linked revision" in body,
            "practice_no_target": "No active practice target is available" in body,
            "journey_priority_event": "Practice priority available" in body,
            "fallback_text_present": "fallback" in body.lower(),
            "internal_diagnostic_text_present": "D001" in body or "diagnostic-gate" in body.lower(),
        },
        "priority_reference_in_revision": "#1" in body,
        "learner_context": STUDENT_ID in body,
        "body_snippet": " | ".join(body.splitlines())[:400],
    }


def main() -> None:
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    observations = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for viewport, label in (((1280, 800), "desktop"), ((390, 844), "mobile")):
            page = browser.new_page(viewport={"width": viewport[0], "height": viewport[1]})
            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
            expect(page.locator("body")).to_contain_text("English Writing Feedback", timeout=30000)

            # Home: enter the learner.
            textbox = page.get_by_role("textbox").first
            textbox.fill(STUDENT_ID)
            textbox.press("Enter")
            expect(page.locator("body")).to_contain_text(
                "Consider submitting a revision based on your feedback", timeout=30000
            )
            observations.append({"viewport": label, **observe(page, "home")})
            page.screenshot(path=str(SHOT_DIR / f"{label}_01_home.png"), full_page=False)

            # Feedback (session-gated by design; no UI submission in this session).
            goto_page(page, "Feedback")
            expect(page.locator("body")).to_contain_text("No feedback in this session", timeout=30000)
            observations.append({"viewport": label, **observe(page, "feedback")})
            page.screenshot(path=str(SHOT_DIR / f"{label}_02_feedback.png"), full_page=False)

            # Revision: durable read path.
            goto_page(page, "Revision")
            expect(page.locator("body")).to_contain_text("Choose the draft you want to revise", timeout=30000)
            observations.append({"viewport": label, **observe(page, "revision")})
            page.screenshot(path=str(SHOT_DIR / f"{label}_03_revision.png"), full_page=False)

            # Practice: accurate missing-target state.
            goto_page(page, "Practice")
            expect(page.locator("body")).to_contain_text(
                "No active practice target is available", timeout=30000
            )
            observations.append({"viewport": label, **observe(page, "practice")})
            page.screenshot(path=str(SHOT_DIR / f"{label}_04_practice.png"), full_page=False)

            # Learning Journey: durable priority event.
            goto_page(page, "Learning Journey")
            expect(page.locator("body")).to_contain_text("Practice priority available", timeout=30000)
            observations.append({"viewport": label, **observe(page, "journey")})
            page.screenshot(path=str(SHOT_DIR / f"{label}_05_journey.png"), full_page=False)

            page.close()
        browser.close()
    output = {
        "audit_stage": "v0.9.6-D0-R",
        "phase": "Phase 5 - browser-assisted Student View journey",
        "student": STUDENT_ID,
        "submission_id": 1,
        "note": "audit-only; no submission or write performed; screenshots stored locally under C:\\tmp\\v096d0r\\screenshots (redacted synthetic audit content)",
        "views": observations,
    }
    OUTPUT_PATH.write_text(
        json.dumps(output, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    for obs in observations:
        print(obs["viewport"], obs["page"], obs["text_found"])


if __name__ == "__main__":
    main()
