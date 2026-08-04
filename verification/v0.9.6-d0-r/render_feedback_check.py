from __future__ import annotations

"""v0.9.6-D0-R Phase 5 focused Feedback-page render check (audit-only).

Renders the production Streamlit Feedback page with the REAL submission
response of the naturally generated priority case (D0-01, submission #1)
cached from the live audit API, seeded into session state exactly as the
production Writing page stores it.  Performs no writes and creates no
submissions.
"""

import json
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parent
WORKSPACE = Path(r"C:\tmp\v096d0r")
PAYLOAD = WORKSPACE / "payloads" / "D0-01-1.json"
APP = ROOT.parents[1] / "streamlit_app.py"


def main() -> None:
    cache = json.loads(PAYLOAD.read_text(encoding="utf-8"))
    response = cache["response"]
    response["ui_submission"] = {
        "student_id": "AUDIT-D0R-01",
        "writing_prompt": cache["writing_prompt"],
        "genre": "argumentative essay",
        "draft_stage": "first draft",
    }
    at = AppTest.from_file(str(APP), default_timeout=30)
    at.session_state["ui_language"] = "en"
    at.session_state["selected_student_id"] = "AUDIT-D0R-01"
    at.session_state["sidebar_page"] = "Feedback"
    at.session_state["submission_result"] = response
    at.run()
    assert not at.exception, at.exception
    at.run(timeout=30)
    assert not at.exception, at.exception
    body = "\n".join(item.value for item in at.markdown if getattr(item, "value", None))
    text = " ".join(item.value for item in at.markdown if getattr(item, "value", None))
    buttons = [b.label for b in at.button]
    checks = {
        "priority_category_visible": "Reduce Lexical Repetition" in text,
        "explanation_visible": "The word 'really' is repeated three times" in text,
        "revision_guidance_visible": "Revision guidance" in text,
        "evidence_section_visible": "From Your Writing" in text,
        "evidence_quote_visible": "A second language is really useful and really practical" in text,
        "no_fallback_label": "fallback" not in text.lower(),
        "no_internal_diagnostic_text": "D001" not in text and "diagnostic-gate" not in text.lower(),
        "no_duplicate_priority_heading": text.count("Reduce Lexical Repetition") == 1,
        "submission_reference_visible": "#1" in text,
        "app_rendered_without_exception": True,
    }
    output = {
        "audit_stage": "v0.9.6-D0-R",
        "phase": "Phase 5 - Feedback page render check (production renderer, real response payload)",
        "student": "AUDIT-D0R-01",
        "submission_id": 1,
        "method": "AppTest render of streamlit_app.py with the real cached POST /api/v1/submissions response seeded as submission_result (same shape the Writing page stores); no writes, no new submission",
        "checks": checks,
        "buttons_present": buttons,
    }
    (ROOT / "feedback_render_check.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    print(json.dumps({"checks": checks, "buttons": buttons}, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
