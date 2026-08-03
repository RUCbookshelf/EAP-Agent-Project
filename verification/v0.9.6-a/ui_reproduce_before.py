"""v0.9.6-A pre-fix UI duplicate-submit reproduction (AppTest driver)."""
from __future__ import annotations

import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "verification" / "v0.9.6-a" / "ui_harness_before.py"
OUT = ROOT / "verification" / "v0.9.6-a"

at = AppTest.from_file(str(HARNESS), default_timeout=60).run()
assert not at.exception, at.exception

at.text_input(key="revision_student").set_value("S96B").run()
assert not at.exception, at.exception

at.selectbox(key="revision_source_select").select("Should cities add more parks? \u00b7 first draft \u00b7 #1").run()
assert not at.exception, at.exception

at.text_area(key="revision_text_input").set_value(
    "Parks support health and community life. Cities should protect accessible parks for everyone."
).run()
assert not at.exception, at.exception

at.button(key="revision_submit_primary").click().run()
assert not at.exception, at.exception
client = at.session_state["fake_client"]
first_count = client.post_count
markdown_text = " ".join(m.value for m in at.markdown)
error_shown = "took too long" in markdown_text and "(while submit)" in markdown_text
retry_button_shown = any(b.label == "Retry" for b in at.button)

at.button(key="revision_submit_primary").click().run()
assert not at.exception, at.exception
second_count = client.post_count

payload = {
    "stage": "v0.9.6-A",
    "kind": "reproduction_before_ui",
    "flow": "open revision form -> enter revised text -> submit (first POST raises client REQUEST_TIMEOUT) -> error rendered -> click submit again",
    "first_click_post_count": first_count,
    "second_click_post_count": second_count,
    "old_timeout_error_message_rendered": error_shown,
    "retry_button_rendered": retry_button_shown,
    "duplicate_post_possible_from_ui": second_count > first_count,
    "conclusion": "Pre-fix: the revision page has no pending guard; after the timeout error is displayed, a second click issues a second POST with the same payload, which can create a duplicate linked revision server-side (incident essays 24/25 mechanism).",
}
with open(OUT / "reproduction_before_ui.json", "w", encoding="utf-8", newline="\n") as fh:
    fh.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
print(json.dumps(payload, indent=2, sort_keys=True))