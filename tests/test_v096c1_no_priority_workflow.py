"""v0.9.6-C1 focused tests: no-priority feedback workflow completion.

Proves the no-priority Diagnostic Gate result is a complete actionable branch:
Feedback choices (Revise This Draft / Finish This Feedback Cycle), exactly one
next-step heading, no unsupported Strength label, stale Writing-success state
clearing, fresh Writing state, no fabricated revision or practice target,
Home reflection, Revision/Practice actionable no-priority states, ordinary
priority-selected behavior, submission reliability unchanged, and locale
parity.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.ui.features.student.feedback import render_feedback_content
from app.ui.locale import t

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "harness_v096c1_student.py"
PROMPT = "Should cities add more parks?"

NO_PRIORITY_RESULT = {
    "submission_id": 28,
    "ui_submission": {"student_id": "S02", "writing_prompt": PROMPT, "genre": "argumentative essay", "draft_stage": "final draft"},
    "ui_empty_states": ["NO_SELECTED_PRIORITY"],
    "diagnosis": {"strengths": []},
    "feedback_result": {
        "feedback": {
            "priority_feedback": [],
            "positive_finding": {
                "evidence_quote": "Urban historians have documented green space trends.",
                "explanation": "This exact passage provides a neutral text location for formative review; no reliable automatic strength was inferred.",
            },
            "uncertainty_note": "This feedback uses prototype heuristics.",
        }
    },
}

CANDIDATE_28 = {
    "essay_id": 28,
    "student_id": "S02",
    "writing_prompt": PROMPT,
    "genre": "argumentative essay",
    "draft_stage": "final draft",
    "timed": False,
    "time_limit_minutes": None,
    "tool_use": "none",
    "submitted_at": "2026-08-03T14:19:38+00:00",
    "revision_of_submission_id": 26,
    "revision_group_id": "RG000005",
    "revision_sequence": 4,
    "revision_stage": "final_draft",
    "original_draft_stage": "final draft",
    "writing_started_at": None,
    "writing_submitted_at": None,
    "active_writing_duration_seconds": None,
    "timing_source": "unknown",
    "timing_quality": "unavailable",
    "unexplained_interruption": False,
}

SOURCE_BUNDLE_28 = {
    "essay_id": 28,
    "student_id": "S02",
    "writing_prompt": PROMPT,
    "genre": "argumentative essay",
    "draft_stage": "final draft",
    "timed": False,
    "time_limit_minutes": None,
    "tool_use": "none",
    "essay_text": "Parks support public health. Cities should protect accessible parks.",
    "submitted_at": "2026-08-03T14:19:38+00:00",
    "revision_of_submission_id": 26,
    "revision_group_id": "RG000005",
    "revision_sequence": 4,
    "revision_stage": "final_draft",
    "feedback": {"priority_feedback": []},
}


def _markdown_text(at) -> str:
    return " ".join(m.value for m in at.markdown)


def _run_harness(**config):
    at = AppTest.from_file(str(HARNESS), default_timeout=90)
    configured_result = config.pop("submission_result", None)
    for key, value in config.items():
        at.session_state[key] = value
    at.run()
    assert not at.exception, at.exception
    # Establish the learner first so the learner-scoped state clearing in
    # set_selected_learner cannot remove the seeded submission_result.
    student_input = next(
        ti for ti in at.text_input
        if ti.key in {"home_student", "writing_student", "feedback_student",
                      "revision_student", "practice_student_v2"}
    )
    student_input.set_value("S02").run()
    assert not at.exception, at.exception
    # Seed the just-submitted result AFTER the learner is stable; the
    # learner-scoped clearing only removes keys set before the transition.
    at.session_state["submission_result"] = (
        configured_result
        if configured_result is not None
        else json.loads(json.dumps(NO_PRIORITY_RESULT))
    )
    at.run()
    assert not at.exception, at.exception
    return at


class NoOpClient:
    """Minimal StudentFeedbackApiPort for render_feedback_content unit tests."""

    def get_student_revision_candidates(self, student_id):
        return {"candidates": []}


# ---------------------------------------------------------------------------
# Feedback content rendering
# ---------------------------------------------------------------------------

def test_no_priority_is_a_valid_result_and_suggested_next_step_rendered_once(monkeypatch):
    import streamlit as st
    captured = []
    monkeypatch.setattr(st, "markdown", lambda body, unsafe_allow_html=False: captured.append(body))
    monkeypatch.setattr(st, "write", lambda value: captured.append(str(value)))
    monkeypatch.setattr(st, "button", lambda *a, **k: captured.append("BTN:" + str(a[0])) or False)
    render_feedback_content(NO_PRIORITY_RESULT, NoOpClient(), "en")
    text = "\n".join(captured)
    assert "No revision priority available" in text
    assert text.count("Suggested Next Step") == 1
    assert "#28" in text


def test_no_unsupported_strength_label_for_neutral_passage(monkeypatch):
    import streamlit as st
    captured = []
    monkeypatch.setattr(st, "markdown", lambda body, unsafe_allow_html=False: captured.append(body))
    monkeypatch.setattr(st, "write", lambda value: captured.append(str(value)))
    monkeypatch.setattr(st, "button", lambda *a, **k: False)
    render_feedback_content(NO_PRIORITY_RESULT, NoOpClient(), "en")
    text = "\n".join(captured)
    assert "Passage From Your Writing" in text
    assert "Strengths" not in text


def test_priority_selected_workflow_unchanged(monkeypatch):
    import streamlit as st
    captured = []
    monkeypatch.setattr(st, "markdown", lambda body, unsafe_allow_html=False: captured.append(body))
    monkeypatch.setattr(st, "write", lambda value: captured.append(str(value)))
    monkeypatch.setattr(st, "button", lambda *a, **k: captured.append("BTN:" + str(a[0])) or False)
    result = json.loads(json.dumps(NO_PRIORITY_RESULT))
    result["ui_empty_states"] = []
    result["diagnosis"] = {"strengths": [{"category": "lexical_repetition"}]}
    result["feedback_result"]["feedback"]["priority_feedback"] = [{
        "category": "lexical_repetition",
        "evidence_quote": "repeat words",
        "explanation": "Repeated words reduce clarity.",
        "revision_guidance": "Vary the wording.",
    }]
    render_feedback_content(result, NoOpClient(), "en")
    text = "\n".join(captured)
    assert "Strengths" in text
    assert "Suggested Next Step" in text
    assert f"BTN:{t('student_feedback_practice_priority', 'en')}" in text


# ---------------------------------------------------------------------------
# AppTest flows
# ---------------------------------------------------------------------------

def test_feedback_page_no_priority_choices_rendered():
    at = _run_harness(
        submission_result=json.loads(json.dumps(NO_PRIORITY_RESULT)),
        sidebar_page=t("student_feedback_title", "en"),
    )
    text = _markdown_text(at)
    assert "No revision priority available" in text
    assert "Suggested Next Step" in text
    labels = [b.label for b in at.button]
    assert "Revise This Draft" in labels
    assert "Finish This Feedback Cycle" in labels
    assert text.count("Suggested Next Step") == 1


def test_flow_c1a_revise_preserves_source_and_no_priority_is_not_fabricated():
    at = _run_harness(
        submission_result=json.loads(json.dumps(NO_PRIORITY_RESULT)),
        sidebar_page=t("student_feedback_title", "en"),
        harness_candidates=[json.loads(json.dumps(CANDIDATE_28))],
        harness_source_bundle=json.loads(json.dumps(SOURCE_BUNDLE_28)),
    )
    at.button(key="feedback_revise_action").click().run()
    assert not at.exception, at.exception
    client = at.session_state["fake_client"]
    assert client.post_count == 0 and client.revision_post_count == 0
    # The writing page is now in revision mode with source #28 preserved.
    assert at.session_state["writing_task_relationship"] == t("task_revision_within", "en")
    selectbox = next(sb for sb in at.selectbox if sb.key == "writing_revision_source_select")
    assert "final draft" in str(selectbox.value) and "#28" in str(selectbox.value)
    assert "revision within the same writing task" in _markdown_text(at)


def test_flow_c1b_finish_clears_stale_state_and_fresh_writing():
    at = _run_harness(
        submission_result=json.loads(json.dumps(NO_PRIORITY_RESULT)),
        sidebar_page=t("student_feedback_title", "en"),
    )
    at.button(key="feedback_finish_action").click().run()
    assert not at.exception, at.exception
    client = at.session_state["fake_client"]
    assert client.post_count == 0 and client.revision_post_count == 0
    assert "submission_result" not in at.session_state
    assert at.session_state["no_priority_reviewed"] == 28
    text = _markdown_text(at)
    assert "Writing submitted" not in text
    assert "writing_submit_primary" in [b.key for b in at.button]
    assert "You finished this feedback cycle" in text


def test_flow_c1b_no_old_loop_after_finish():
    at = _run_harness(
        submission_result=json.loads(json.dumps(NO_PRIORITY_RESULT)),
        sidebar_page=t("student_feedback_title", "en"),
    )
    at.button(key="feedback_finish_action").click().run()
    # Navigate back to Feedback: the stale result must be gone.
    at.session_state["sidebar_page"] = t("student_feedback_title", "en")
    at.run()
    assert not at.exception, at.exception
    text = _markdown_text(at)
    assert "no newly submitted draft" in text
    assert "No revision priority available" not in text


def test_home_reflects_unresolved_no_priority_decision():
    at = _run_harness(
        submission_result=json.loads(json.dumps(NO_PRIORITY_RESULT)),
        sidebar_page=t("student_home_title", "en"),
        harness_journey={"state": "feedback_no_practice_target", "events": []},
        harness_targets=[],
    )
    text = _markdown_text(at)
    assert "#28" in text
    assert "No automatic priority selected" in text
    labels = [b.label for b in at.button]
    assert "Revise This Draft" in labels
    assert "Finish This Feedback Cycle" in labels


def test_home_returns_to_normal_contract_after_finish():
    at = _run_harness(
        submission_result=json.loads(json.dumps(NO_PRIORITY_RESULT)),
        sidebar_page=t("student_home_title", "en"),
        harness_journey={"state": "feedback_no_practice_target", "events": []},
        harness_targets=[],
    )
    at.button(key="home_finish_action").click().run()
    assert not at.exception, at.exception
    # The finish callback lands on a fresh Writing state; return Home to
    # confirm the unresolved decision block is gone.
    at.session_state["sidebar_page"] = t("student_home_title", "en")
    at.run()
    assert not at.exception, at.exception
    text = _markdown_text(at)
    assert "No automatic priority selected" not in text
    assert "No practice target yet" in text


def test_revision_page_explains_no_auto_focus():
    at = _run_harness(
        submission_result=json.loads(json.dumps(NO_PRIORITY_RESULT)),
        sidebar_page=t("student_revision_title", "en"),
        harness_candidates=[json.loads(json.dumps(CANDIDATE_28))],
        harness_source_bundle=json.loads(json.dumps(SOURCE_BUNDLE_28)),
    )
    assert not at.exception, at.exception
    text = _markdown_text(at)
    assert "No automatic revision focus was selected" in text


def test_practice_page_explains_skipped_no_priority_target():
    at = _run_harness(
        submission_result=json.loads(json.dumps(NO_PRIORITY_RESULT)),
        sidebar_page=t("practice", "en"),
        harness_targets=[],
        no_priority_reviewed=True,
    )
    assert not at.exception, at.exception
    text = _markdown_text(at)
    assert "No practice target was created because no automatic revision priority was selected" in text
    assert "Open Writing" in [b.label for b in at.button]


def test_navigation_stability_across_all_pages():
    for page_key in ("student_home_title", "student_writing_title", "student_feedback_title", "student_revision_title", "practice"):
        at = _run_harness(
            submission_result=json.loads(json.dumps(NO_PRIORITY_RESULT)),
            sidebar_page=t(page_key, "en"),
            harness_candidates=[json.loads(json.dumps(CANDIDATE_28))],
            harness_source_bundle=json.loads(json.dumps(SOURCE_BUNDLE_28)),
            harness_targets=[],
        )
        assert not at.exception, (page_key, at.exception)
        text = _markdown_text(at)
        assert text.strip() != ""
    # After finishing, every page still renders.
    at = _run_harness(
        submission_result=json.loads(json.dumps(NO_PRIORITY_RESULT)),
        sidebar_page=t("student_feedback_title", "en"),
    )
    at.button(key="feedback_finish_action").click().run()
    for page_key in ("student_home_title", "student_writing_title", "student_feedback_title", "student_revision_title", "practice"):
        at.session_state["sidebar_page"] = t(page_key, "en")
        at.run()
        assert not at.exception, (page_key, at.exception)


def test_state_persists_across_reruns_within_session():
    at = _run_harness(
        submission_result=json.loads(json.dumps(NO_PRIORITY_RESULT)),
        sidebar_page=t("student_feedback_title", "en"),
    )
    at.run()
    assert not at.exception, at.exception
    assert "no_priority_reviewed" not in at.session_state
    # Rerun without interaction does not change state.
    at.run()
    assert "submission_result" in at.session_state


# ---------------------------------------------------------------------------
# Locale
# ---------------------------------------------------------------------------

def test_locale_parity_and_new_keys():
    def leaf_keys(obj, prefix=""):
        keys = set()
        for k, v in obj.items():
            p = prefix + "/" + k
            if isinstance(v, dict):
                keys |= leaf_keys(v, p)
            else:
                keys.add(p)
        return keys

    en = json.loads((ROOT / "locales/en.json").read_text(encoding="utf-8"))
    zh = json.loads((ROOT / "locales/zh_CN.json").read_text(encoding="utf-8"))
    en_keys, zh_keys = leaf_keys(en), leaf_keys(zh)
    assert en_keys == zh_keys
    for key in (
        "student_feedback_choose_action",
        "student_feedback_choose_action_desc",
        "student_feedback_finish_cycle",
        "student_feedback_neutral_passage",
        "student_home_feedback_result",
        "student_home_latest_submission",
        "student_home_no_priority_selected",
        "student_home_review_choose_desc",
        "student_practice_skipped_no_priority",
        "student_revision_no_auto_focus",
        "student_revision_revise",
        "student_writing_cycle_finished",
    ):
        assert "/" + key in en_keys
        assert en[key] != zh[key]
# ---------------------------------------------------------------------------
# C1 follow-up: Home step transition after finishing a no-priority cycle
# ---------------------------------------------------------------------------

JOURNEY_NO_PRIORITY_28 = {
    "state": "feedback_no_practice_target",
    "derived_states": [{"key": "analysis_without_priority", "submission_ids": [28]}],
    "events": [],
}


def _current_step_label(at) -> str:
    import re

    text = " ".join(m.value for m in at.markdown)
    match = re.search(r'<li data-state="current">.*?<strong>([^<]+)</strong>', text)
    return match.group(1).strip() if match else None


def _primary_cta_label(at) -> str:
    for button in at.button:
        if button.key == "home_primary_action":
            return button.label
    return None


def test_home_unresolved_no_priority_step_is_review_feedback():
    at = _run_harness(
        submission_result=json.loads(json.dumps(NO_PRIORITY_RESULT)),
        sidebar_page=t("student_home_title", "en"),
        harness_journey=json.loads(json.dumps(JOURNEY_NO_PRIORITY_28)),
        harness_targets=[],
    )
    assert _current_step_label(at) == "Review feedback"
    labels = [b.label for b in at.button]
    assert "Revise This Draft" in labels and "Finish This Feedback Cycle" in labels


def test_home_after_finish_cycle_shows_write_step_and_fresh_action():
    at = _run_harness(
        submission_result=json.loads(json.dumps(NO_PRIORITY_RESULT)),
        sidebar_page=t("student_home_title", "en"),
        harness_journey=json.loads(json.dumps(JOURNEY_NO_PRIORITY_28)),
        harness_targets=[],
    )
    at.button(key="home_finish_action").click().run()
    at.session_state["sidebar_page"] = t("student_home_title", "en")
    at.run()
    assert not at.exception, at.exception
    assert at.session_state["no_priority_reviewed"] == 28
    assert _current_step_label(at) == "Write"
    assert _primary_cta_label(at) == "Open Writing"
    assert "No automatic priority selected" not in _markdown_text(at)


def test_home_step_override_survives_reruns_and_navigation():
    at = _run_harness(
        submission_result=json.loads(json.dumps(NO_PRIORITY_RESULT)),
        sidebar_page=t("student_feedback_title", "en"),
        harness_journey=json.loads(json.dumps(JOURNEY_NO_PRIORITY_28)),
    )
    at.button(key="feedback_finish_action").click().run()
    for page_key in ("student_home_title", "student_writing_title", "student_feedback_title"):
        at.session_state["sidebar_page"] = t(page_key, "en")
        at.run()
        assert not at.exception, at.exception
    at.session_state["sidebar_page"] = t("student_home_title", "en")
    at.run()
    assert _current_step_label(at) == "Write"
    assert _primary_cta_label(at) == "Open Writing"


def test_new_unresolved_submission_not_treated_as_completed():
    # A previous cycle (#28) was finished, but a NEW unresolved no-priority
    # submission (#29) exists in the session: Home must stay at Review.
    newer = json.loads(json.dumps(NO_PRIORITY_RESULT))
    newer["submission_id"] = 29
    at = _run_harness(
        submission_result=newer,
        sidebar_page=t("student_home_title", "en"),
        harness_journey={
            "state": "feedback_no_practice_target",
            "derived_states": [{"key": "analysis_without_priority", "submission_ids": [29]}],
            "events": [],
        },
        harness_targets=[],
        no_priority_reviewed=28,
    )
    assert _current_step_label(at) == "Review feedback"
    labels = [b.label for b in at.button]
    assert "Revise This Draft" in labels and "Finish This Feedback Cycle" in labels
    assert "#29" in _markdown_text(at)


def test_home_after_revise_shows_revision_goal_not_write():
    at = _run_harness(
        submission_result=json.loads(json.dumps(NO_PRIORITY_RESULT)),
        sidebar_page=t("student_home_title", "en"),
        harness_journey=json.loads(json.dumps(JOURNEY_NO_PRIORITY_28)),
        harness_candidates=[json.loads(json.dumps(CANDIDATE_28))],
        harness_source_bundle=json.loads(json.dumps(SOURCE_BUNDLE_28)),
        harness_targets=[],
    )
    at.button(key="home_revise_action").click().run()
    assert not at.exception, at.exception
    assert "no_priority_reviewed" not in at.session_state
    at.session_state["sidebar_page"] = t("student_home_title", "en")
    at.run()
    assert not at.exception, at.exception
    # Revise does not finish the cycle: the durable revision goal remains the
    # current step and the CTA is Revision, not Writing.
    assert _current_step_label(at) != "Write"
    assert _primary_cta_label(at) == "Open Revision"


def test_latest_no_priority_submission_id_helper():
    from app.ui.features.student.home import _latest_no_priority_submission_id

    journey = {"derived_states": [{"key": "analysis_without_priority", "submission_ids": [20, 21, 28]}]}
    assert _latest_no_priority_submission_id(journey) == 28
    assert _latest_no_priority_submission_id({"derived_states": []}) is None
    assert _latest_no_priority_submission_id({"derived_states": [{"key": "other", "submission_ids": [1]}]}) is None
    assert _latest_no_priority_submission_id({"state": "no_submissions"}) is None
