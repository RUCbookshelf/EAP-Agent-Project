"""v0.9.7-A focused tests: priority-guided revision cycle completion.

Covers the frozen Work Unit 2-4 scope at the page/state layer:
Feedback-to-Revision priority transfer, active-priority task context and
selection, revision submission completion state, re-entry after submission,
end-of-cycle and Practice continuation actions, no-priority and malformed
priority degradation, rerun/locale behavior, and the pure priority/revision
helpers. Service and persistence behavior is covered by the existing
v0.9.6-A linked-revision suite.
"""
from __future__ import annotations

import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from app.ui.features.student.formatting import _feedback_category_label
from app.ui.features.student.revision import _latest_revision_of_source, _source_priorities
from app.ui.locale import t

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "harness_v097a_student.py"
PROMPT = "Should cities add more parks?"

PRIORITIES = [
    {
        "diagnosis_id": "D001",
        "category": "lexical_repetition",
        "evidence_quote": "Parks support public health.",
        "explanation": "The phrase 'public health' is repeated closely in the draft.",
        "revision_guidance": "Replace one repetition with a synonym.",
    },
    {
        "diagnosis_id": "D002",
        "category": "connective_use",
        "evidence_quote": "Cities should protect accessible parks.",
        "explanation": "The draft lacks a linking phrase between the two ideas.",
        "revision_guidance": "Add a connective that links the two ideas.",
    },
]

PRIORITY_RESULT = {
    "submission_id": 28,
    "ui_submission": {
        "student_id": "S02",
        "writing_prompt": PROMPT,
        "genre": "argumentative essay",
        "draft_stage": "final draft",
    },
    "ui_empty_states": [],
    "diagnosis": {"strengths": []},
    "feedback_result": {
        "feedback": {
            "priority_feedback": PRIORITIES,
            "positive_finding": {
                "evidence_quote": "Urban historians have documented green space trends.",
                "explanation": "This exact passage provides a neutral text location for formative review.",
            },
            "uncertainty_note": "This feedback uses prototype heuristics.",
        }
    },
}

REVISION_SAVED_RESULT = {
    "submission_id": 99,
    "ui_submission": {
        "student_id": "S02",
        "writing_prompt": PROMPT,
        "genre": "argumentative essay",
        "draft_stage": "revised draft",
        "revision_of_submission_id": 28,
        "revision_priority_index": 1,
        "revision_source": {
            "writing_prompt": PROMPT,
            "draft_stage": "final draft",
            "essay_text": "Parks support public health. Cities should protect accessible parks.",
        },
    },
    "within_task_revision_trajectory": {
        "previous_selected_priorities": PRIORITIES,
        "feedback_uptake_candidates": [],
        "first_to_latest_comparison": {},
    },
}

SOURCE_CANDIDATE = {
    "essay_id": 28,
    "student_id": "S02",
    "writing_prompt": PROMPT,
    "genre": "argumentative essay",
    "draft_stage": "final draft",
    "timed": False,
    "time_limit_minutes": None,
    "tool_use": "none",
    "submitted_at": "2026-08-04T10:00:00+00:00",
    "revision_of_submission_id": None,
    "revision_group_id": None,
    "revision_sequence": None,
    "revision_stage": None,
    "original_draft_stage": None,
    "writing_started_at": None,
    "writing_submitted_at": None,
    "active_writing_duration_seconds": None,
    "timing_source": "unknown",
    "timing_quality": "unavailable",
    "unexplained_interruption": False,
}

REVISION_CANDIDATE = {
    **SOURCE_CANDIDATE,
    "essay_id": 29,
    "draft_stage": "revised draft",
    "submitted_at": "2026-08-04T11:00:00+00:00",
    "revision_of_submission_id": 28,
    "revision_group_id": "RG000009",
    "revision_sequence": 1,
    "revision_stage": "revised_draft",
}

SINGLE_PRIORITY_BUNDLE = json.loads(json.dumps({"essay_id": 28, "student_id": "S02", "writing_prompt": PROMPT, "genre": "argumentative essay", "draft_stage": "final draft", "essay_text": "Parks support public health. Cities should protect accessible parks.", "submitted_at": "2026-08-04T10:00:00+00:00", "feedback": {"priority_feedback": [PRIORITIES[0]]}}))

SOURCE_BUNDLE = {
    "essay_id": 28,
    "student_id": "S02",
    "writing_prompt": PROMPT,
    "genre": "argumentative essay",
    "draft_stage": "final draft",
    "essay_text": "Parks support public health. Cities should protect accessible parks.",
    "submitted_at": "2026-08-04T10:00:00+00:00",
    "feedback": {"priority_feedback": PRIORITIES},
}


def _markdown_text(at) -> str:
    return " ".join(m.value for m in at.markdown)


def _button_labels(at) -> dict:
    return {button.key: button.label for button in at.button}


def _run_harness(**config):
    at = AppTest.from_file(str(HARNESS), default_timeout=90)
    configured_result = config.pop("submission_result", None)
    for key, value in config.items():
        at.session_state[key] = value
    at.run()
    assert not at.exception, at.exception
    student_input = next(
        ti
        for ti in at.text_input
        if ti.key
        in {"home_student", "writing_student", "feedback_student",
            "revision_student", "practice_student_v2"}
    )
    student_input.set_value("S02").run()
    assert not at.exception, at.exception
    if configured_result is not None:
        at.session_state["submission_result"] = json.loads(json.dumps(configured_result))
        at.run()
        assert not at.exception, at.exception
    return at


def test_feedback_priority_branch_transfers_to_revision():
    at = _run_harness(
        submission_result=PRIORITY_RESULT,
        sidebar_page=t("student_feedback_title", "en"),
    )
    labels = _button_labels(at)
    assert labels.get("feedback_primary_action") == t("student_feedback_open_revision", "en")
    assert labels.get("feedback_practice_action") == t("student_feedback_open_practice", "en")
    assert t("student_feedback_practice_note", "en") in _markdown_text(at)

    at.button(key="feedback_primary_action").click().run()
    assert not at.exception, at.exception
    assert at.session_state["sidebar_page"] == t("student_revision_title", "en")
    assert at.session_state["revision_source_preset"] == 28
    assert "revision_priority_selection" not in at.session_state


def test_revision_preset_renders_priority_task():
    at = _run_harness(
        sidebar_page=t("student_revision_title", "en"),
        harness_candidates=[SOURCE_CANDIDATE],
        harness_source_bundle=SINGLE_PRIORITY_BUNDLE,
        revision_source_preset=28,
    )
    text = _markdown_text(at)
    assert t("student_revision_priority_task", "en") in text
    assert _feedback_category_label("lexical_repetition", "en") in text
    import html as _html
    assert _html.escape(PRIORITIES[0]["explanation"]) in text
    assert PRIORITIES[0]["revision_guidance"] in text
    assert PRIORITIES[0]["evidence_quote"] in text
    assert t("student_revision_instruction", "en") in text
    assert "revision_submit_primary" in _button_labels(at)
    assert not at.radio  # a single priority needs no selector


def test_revision_multiple_priorities_select_and_recover():
    at = _run_harness(
        sidebar_page=t("student_revision_title", "en"),
        harness_candidates=[SOURCE_CANDIDATE],
        harness_source_bundle=SOURCE_BUNDLE,
        revision_source_preset=28,
    )
    assert len(at.radio) == 1
    radio = at.radio[0]
    assert radio.key == "revision_priority_select_28"
    radio.set_value(1).run()
    assert not at.exception, at.exception
    assert at.session_state["revision_priority_selection"] == {
        "submission_id": 28,
        "index": 1,
    }
    assert _feedback_category_label("connective_use", "en") in _markdown_text(at)

    # A stale/invalid selection falls back to the first priority with a note.
    at.session_state["revision_priority_selection"] = {"submission_id": 28, "index": 9}
    at.run()
    assert not at.exception, at.exception
    assert t("student_revision_selection_reset", "en") in _markdown_text(at)
    assert at.session_state["revision_priority_selection"] == {
        "submission_id": 28,
        "index": 0,
    }


def test_revision_no_priority_flow_unchanged():
    bundle = json.loads(json.dumps(SOURCE_BUNDLE))
    bundle["feedback"] = {"priority_feedback": []}
    at = _run_harness(
        sidebar_page=t("student_revision_title", "en"),
        harness_candidates=[SOURCE_CANDIDATE],
        harness_source_bundle=bundle,
        revision_source_preset=28,
    )
    assert t("student_revision_no_auto_focus", "en") in _markdown_text(at)
    assert "revision_submit_primary" in _button_labels(at)
    assert not at.radio


def test_revision_malformed_priority_degrades_safely():
    bundle = json.loads(json.dumps(SOURCE_BUNDLE))
    bundle["feedback"] = {"priority_feedback": [{"category": "lexical_repetition"}]}
    at = _run_harness(
        sidebar_page=t("student_revision_title", "en"),
        harness_candidates=[SOURCE_CANDIDATE],
        harness_source_bundle=bundle,
        revision_source_preset=28,
    )
    assert not at.exception
    assert t("student_revision_no_auto_focus", "en") in _markdown_text(at)
    assert "revision_submit_primary" in _button_labels(at)


def test_revision_submit_completion_state():
    at = _run_harness(
        sidebar_page=t("student_revision_title", "en"),
        harness_candidates=[SOURCE_CANDIDATE],
        harness_source_bundle=SOURCE_BUNDLE,
        revision_source_preset=28,
    )
    at.text_area(key="revision_text_input").set_value(
        "Cities should expand parks because they support public health."
    ).run()
    assert not at.exception, at.exception
    at.button(key="revision_submit_primary").click().run()
    assert not at.exception, at.exception
    assert at.session_state["fake_client"].revision_post_count == 1
    text = _markdown_text(at)
    assert t("student_revision_saved_title", "en") in text
    assert t("student_revision_priority_addressed", "en") in text
    assert _feedback_category_label("lexical_repetition", "en") in text
    assert PRIORITIES[0]["revision_guidance"] in text
    assert t("student_revision_step_complete", "en") in text
    labels = _button_labels(at)
    assert labels.get("revision_finish_cycle") == t("student_revision_finish_cycle", "en")
    assert labels.get("revision_open_practice") == t("student_revision_open_practice", "en")
    assert labels.get("revision_primary_action") == t("student_revision_open_journey", "en")
    assert t("student_revision_practice_note", "en") in text


def test_revision_submit_empty_text_validation():
    at = _run_harness(
        sidebar_page=t("student_revision_title", "en"),
        harness_candidates=[SOURCE_CANDIDATE],
        harness_source_bundle=SOURCE_BUNDLE,
        revision_source_preset=28,
    )
    at.button(key="revision_submit_primary").click().run()
    assert not at.exception, at.exception
    assert t("student_revision_empty_text", "en") in _markdown_text(at)
    assert at.session_state["fake_client"].revision_post_count == 0


def test_revision_submit_failure_preserves_input():
    at = _run_harness(
        sidebar_page=t("student_revision_title", "en"),
        harness_candidates=[SOURCE_CANDIDATE],
        harness_source_bundle=SOURCE_BUNDLE,
        revision_source_preset=28,
        harness_fail_submit=True,
    )
    at.text_area(key="revision_text_input").set_value(
        "Cities should expand parks because they support public health."
    ).run()
    assert not at.exception, at.exception
    at.button(key="revision_submit_primary").click().run()
    assert not at.exception, at.exception
    assert at.session_state["fake_client"].revision_post_count == 1
    assert t("submission_error", "en") in _markdown_text(at)
    assert (
        at.text_area(key="revision_text_input").value
        == "Cities should expand parks because they support public health."
    )


def test_revision_reentry_shows_completed_state():
    # Newest-first candidate order mirrors list(reversed(items)) on the server.
    at = _run_harness(
        sidebar_page=t("student_revision_title", "en"),
        harness_candidates=[REVISION_CANDIDATE, SOURCE_CANDIDATE],
        harness_source_bundle=SOURCE_BUNDLE,
        revision_source_preset=28,
    )
    text = _markdown_text(at)
    assert t("student_revision_already_submitted_title", "en") in text
    assert t("student_revision_priority_addressed", "en") in text
    assert _feedback_category_label("lexical_repetition", "en") in text
    assert "revision_submit_primary" not in _button_labels(at)
    assert t("student_revision_finish_cycle", "en") in _button_labels(at).values()
    assert at.session_state["fake_client"].revision_post_count == 0


def test_finish_revision_cycle_clears_and_navigates_home():
    at = _run_harness(
        submission_result=REVISION_SAVED_RESULT,
        sidebar_page=t("student_revision_title", "en"),
    )
    at.button(key="revision_finish_cycle").click().run()
    assert not at.exception, at.exception
    assert at.session_state["sidebar_page"] == t("student_home_title", "en")
    assert "submission_result" not in at.session_state
    assert "revision_source_preset" not in at.session_state
    assert "revision_priority_selection" not in at.session_state
    assert t("student_home_title", "en") in _markdown_text(at)


def test_saved_state_shows_selected_priority_addressed():
    at = _run_harness(
        submission_result=REVISION_SAVED_RESULT,
        sidebar_page=t("student_revision_title", "en"),
    )
    text = _markdown_text(at)
    assert t("student_revision_priority_addressed", "en") in text
    assert PRIORITIES[1]["revision_guidance"] in text
    assert t("student_revision_finish_cycle", "en") in _button_labels(at).values()


def test_revision_priority_task_renders_in_chinese():
    at = _run_harness(
        harness_lang="zh_CN",
        sidebar_page=t("student_revision_title", "zh_CN"),
        harness_candidates=[SOURCE_CANDIDATE],
        harness_source_bundle=SOURCE_BUNDLE,
        revision_source_preset=28,
    )
    text = _markdown_text(at)
    assert t("student_revision_priority_task", "zh_CN") in text
    assert t("student_revision_instruction", "zh_CN") in text
    assert "revision_submit_primary" in _button_labels(at)


def test_source_priorities_helper_validates_persisted_items():
    valid = {"category": "c", "explanation": "e", "revision_guidance": "g"}
    source = {"feedback": {"priority_feedback": [valid, {"category": "x"}, "junk", None]}}
    items = _source_priorities(source)
    assert items == [valid]
    assert _source_priorities({"feedback": None}) == []
    assert _source_priorities({}) == []
    assert _source_priorities({"feedback": {"priority_feedback": []}}) == []


def test_latest_revision_of_source_helper():
    assert _latest_revision_of_source([SOURCE_CANDIDATE], 28) is None
    found = _latest_revision_of_source(
        [REVISION_CANDIDATE, SOURCE_CANDIDATE], 28
    )
    assert found is not None and found["essay_id"] == 29
    assert _latest_revision_of_source([REVISION_CANDIDATE, SOURCE_CANDIDATE], 99) is None