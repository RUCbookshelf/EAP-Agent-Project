"""AppTest journey tests for the Wave-2 Student Writing Experience (CASE A-F).

Drives the real studio/history renderers through Streamlit AppTest with the
scripted gateway harness (tests/harness_wave2_studio.py):

- CASE A: new learner first submission without fabricated history
- CASE B: revise and resubmit (observation result)
- CASE C: returning learner sees historical feedback and priority plan
- CASE D: expand scaffold (progressive levels) and revise
- CASE E: inspect history and LearningItems
- CASE F: fail-closed/insufficient-evidence states and standard-mode
          degradation, both understandable to a student

Also asserts the no-technical-internals rule on the rendered UI.
"""

from __future__ import annotations

import re
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tests" / "harness_wave2_studio.py"
PROMPT = "Should cities add more parks?"
ESSAY = (
    "Cities should add more parks because parks give residents space to exercise. "
    "Parks also support community events and provide shade during hot weather. "
    "However, new parks require land and regular maintenance. Therefore, city "
    "leaders should first identify neighborhoods with limited green space and "
    "consult residents."
)
REVISED = (
    "Cities should add more parks because green spaces give residents room to "
    "exercise. Parks also support community events and provide shade during hot "
    "weather. However, new parks require land and regular maintenance. Therefore, "
    "city leaders should first identify neighborhoods with limited green space "
    "and consult residents before spending money. Adding more green space also "
    "gives neighbors a calm place to meet and talk."
)

INTERNAL_PATTERNS = (
    "T-0001", "LI-0001", "OBS-", "PLAN-", "PI-", "D-0001", "AR-", "RG-", "RS-",
    "EVID-", "GLO-", "LOC-", "ANCHOR-", "essay_text_hash", "feature_id",
    "corpus_routing", "claims_status", "provenance", "descriptive_proportion",
    "occurrence_count", "reanalysis_events", "supporting_submission_ids",
)


def text_collect(at: AppTest) -> str:
    parts = []
    for element in at.markdown:
        parts.append(element.value)
    for element in at.caption:
        parts.append(element.value)
    for element in at.title:
        parts.append(element.value)
    for element in at.header:
        parts.append(element.value)
    for element in at.subheader:
        parts.append(element.value)
    for element in list(at.info) + list(at.warning) + list(at.success) + list(at.error):
        parts.append(element.value)
    return re.sub(r"<[^>]+>", " ", "\n".join(parts))


def assert_no_internals(at: AppTest) -> None:
    rendered = text_collect(at)
    for pattern in INTERNAL_PATTERNS:
        assert pattern not in rendered, f"internal value {pattern!r} leaked into the UI"


def click(at: AppTest, key: str) -> AppTest:
    """Click a button and rerun until the new step is rendered."""
    at.button(key=key).click()
    at.run()
    at.run()
    return at


def new_app(mode: str = "guided", scenario: str = "new_learner",
            page: str = "studio") -> AppTest:
    at = AppTest.from_file(str(HARNESS), default_timeout=90)
    at.session_state["harness_mode"] = mode
    at.session_state["harness_scenario"] = scenario
    at.session_state["harness_page"] = page
    at.run()
    assert not at.exception
    return at


def drive_to_feedback(mode: str = "guided", scenario: str = "new_learner",
                      learner: str = "L-NEW-001") -> AppTest:
    at = new_app(mode=mode, scenario=scenario)
    at.text_input(key="wave2_student").set_value(learner).run()
    assert not at.exception
    click(at, "wave2_start_new")
    click(at, "wave2_task_next")
    at.text_area(key="wave2_prompt_input").set_value(PROMPT).run()
    click(at, "wave2_prompt_create")
    at.text_area(key="wave2_essay_input").set_value(ESSAY).run()
    click(at, "wave2_submit_v1")
    assert not at.exception
    return at


def test_case_a_new_learner_first_submission_no_fabricated_history():
    at = drive_to_feedback()
    rendered = text_collect(at)
    assert "Your revision plan" in rendered
    assert "What to revise" in rendered
    assert "Why" in rendered
    assert "What to try" in rendered
    assert "This is new in this draft." in rendered
    assert "Not enough of your earlier writing is stored yet to compare patterns, so this plan is based only on the current draft." in rendered
    # no fabricated historical patterns for a brand-new learner
    assert "Patterns from your earlier writing" not in rendered
    assert "Yes - this has shown up in your earlier writing." not in rendered
    feedback = at.session_state["wave2_feedback"]
    assert feedback["history_state"] == "insufficient_history"
    assert feedback["items"]
    assert at.session_state["wave2_mode"] == "guided"
    assert_no_internals(at)


def test_case_b_revise_and_resubmit():
    at = drive_to_feedback()
    click(at, "wave2_go_revise")
    rendered = text_collect(at)
    assert "Write your revision" in rendered
    # the revise box is prefilled with the learner's own previous text
    assert at.text_area(key="wave2_revise_input").value == ESSAY
    at.text_area(key="wave2_revise_input").set_value(REVISED).run()
    click(at, "wave2_submit_revision")
    rendered = text_collect(at)
    assert "Your revision result" in rendered
    assert "What changed" in rendered
    assert "Improved in this revision" in rendered
    assert "Still present" in rendered
    observation = at.session_state["wave2_observation"]
    assert observation["addressed"]
    assert observation["remaining"]
    assert observation["no_intent_inference"]
    version = at.session_state["wave2_last_version"]
    assert version["version_number"] == 2
    assert version["revision_of_submission_id"] == 1
    assert_no_internals(at)


def test_case_c_returning_learner_sees_history_and_priority_plan():
    at = drive_to_feedback(scenario="returning_learner", learner="L-RET-001")
    rendered = text_collect(at)
    assert "Your revision plan" in rendered
    assert "Patterns from your earlier writing" in rendered
    assert "Yes - this has shown up in your earlier writing." in rendered
    feedback = at.session_state["wave2_feedback"]
    assert feedback["history_state"] == "sufficient"
    assert feedback["historical_summary"]
    assert any(item["recurrence_status"] == "recurring"
               for item in feedback["historical_summary"])
    assert_no_internals(at)


def test_case_d_expand_scaffold_and_revise():
    at = drive_to_feedback()
    click(at, "wave2_scaffold_item_0")
    rendered = text_collect(at)
    assert "Step-by-step help" in rendered
    assert "Hint 1 / 7" in rendered
    assert "Guidance only: the revision stays your own writing" in rendered
    click(at, "wave2_scaffold_next")
    rendered = text_collect(at)
    assert "Hint 2 / 7" in rendered
    scaffold = at.session_state["wave2_scaffold"]
    assert scaffold["level"] == 2
    click(at, "wave2_scaffold_done")
    rendered = text_collect(at)
    assert "Write your revision" in rendered
    at.text_area(key="wave2_revise_input").set_value(REVISED).run()
    click(at, "wave2_submit_revision")
    rendered = text_collect(at)
    assert "Your revision result" in rendered
    assert_no_internals(at)


def test_case_e_history_and_learning_items():
    at = new_app(mode="guided", scenario="returning_learner", page="history")
    at.text_input(key="wave2_history_student").set_value("L-RET-001").run()
    assert not at.exception
    rendered = text_collect(at)
    assert "Your writing history" in rendered
    assert "Version 1" in rendered
    assert "Version 2" in rendered
    assert "Feedback you saw" in rendered
    assert "Long-term patterns" in rendered
    assert "Things that have recurred" in rendered
    assert "Things that went well" in rendered
    assert "What has stayed stable" in rendered
    assert "Learning items - what to learn next" in rendered
    assert "Active" in rendered
    assert "Proposed" in rendered
    assert "CET-4: Passed" in rendered
    assert "Repeated word use" in rendered
    assert_no_internals(at)


def test_case_f_standard_degradation_is_understandable():
    at = drive_to_feedback(mode="standard", learner="S-STD-001")
    rendered = text_collect(at)
    assert "The guided studio is temporarily unavailable, so you are using the standard feedback flow. Your writing still works." in rendered
    assert "Not enough history to tell yet." in rendered
    assert at.session_state["wave2_mode"] == "standard"
    click(at, "wave2_scaffold_item_0")
    rendered = text_collect(at)
    assert "Step-by-step help is part of the guided studio. In standard mode, use the suggestions in your revision plan." in rendered
    click(at, "wave2_scaffold_done")
    at.text_area(key="wave2_revise_input").set_value(REVISED).run()
    click(at, "wave2_submit_revision")
    rendered = text_collect(at)
    assert "Your revision result" in rendered
    assert "In standard mode your revised draft was saved for feedback." in rendered
    assert at.session_state["wave2_observation"] is None
    assert_no_internals(at)


def test_case_f2_history_insufficient_states():
    at = new_app(mode="guided", scenario="new_learner", page="history")
    at.text_input(key="wave2_history_student").set_value("L-NEW-001").run()
    assert not at.exception
    rendered = text_collect(at)
    assert "No writing stored yet for this learner" in rendered
    assert "Not enough history yet to show long-term patterns." in rendered
    assert "No learning items yet. They appear after you revise from a plan." in rendered
    assert_no_internals(at)