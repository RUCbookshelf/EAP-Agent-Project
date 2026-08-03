"""v0.9.6-B pre-fix UI duplicate-submit reproduction for first drafts (AppTest driver)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "verification" / "v0.9.6-b" / "ui_harness_before_writing.py"
OUT = ROOT / "verification" / "v0.9.6-b"

at = AppTest.from_file(str(HARNESS), default_timeout=90).run()
assert not at.exception, at.exception

at.text_input(key="writing_student").set_value("S96W").run()
assert not at.exception, at.exception
at.text_area(key="writing_prompt_input").set_value("Should cities add more parks?").run()
assert not at.exception, at.exception
at.text_area(key="writing_essay").set_value(
    "Parks support public health. Cities should protect accessible parks."
).run()
assert not at.exception, at.exception

at.button(key="writing_submit_primary").click().run()
assert not at.exception, at.exception
client = at.session_state["fake_client"]
first_count = client.post_count
markdown_text = " ".join(m.value for m in at.markdown)
error_shown = "took too long" in markdown_text and "(while submit)" in markdown_text
retry_button_shown = any(b.label == "Retry" for b in at.button)

at.button(key="writing_submit_primary").click().run()
assert not at.exception, at.exception
second_count = client.post_count

payload = {
    "stage": "v0.9.6-B",
    "kind": "reproduction_before_ui",
    "flow": "open first-draft form -> enter prompt + draft -> submit (first POST raises client REQUEST_TIMEOUT) -> old timeout message rendered -> click submit again",
    "first_click_post_count": first_count,
    "second_click_post_count": second_count,
    "old_timeout_error_message_rendered": error_shown,
    "retry_button_rendered": retry_button_shown,
    "duplicate_post_possible_from_ui": second_count > first_count,
    "conclusion": "Pre-fix: the writing page has no pending guard; after the old timeout message is displayed, a second click issues a second POST with the same payload, which can create a duplicate first draft server-side.",
}
with open(OUT / "reproduction_before_ui.json", "w", encoding="utf-8", newline="\n") as fh:
    fh.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
print(json.dumps(payload, indent=2, sort_keys=True))