"""v0.9.7-C WU3 focused tests: Student Journey functional UI closure.

Covers the grouped cycle rendering (cycle cards, original/revision
distinction, feedback stages, Practice activities with honest states,
provenance notes, completion wording, safe actions), multiple cycles,
empty and API-error states, English and Chinese localization, rerun
stability, and zero-write rendering.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from streamlit.testing.v1 import AppTest  # noqa: E402

from app.ui.locale import t  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "harness_v097a_student.py"


def _submission(submission_id: int, *, revision_of: int | None = None,
                writing_state: str = "feedback_available",
                is_revision: bool = False) -> dict:
    return {
        "submission_id": submission_id,
        "is_revision": is_revision or revision_of is not None,
        "revision_of_submission_id": revision_of,
        "revision_sequence": 2 if revision_of else None,
        "draft_stage": "revised draft" if revision_of else "first draft",
        "genre": "argumentative essay",
        "submitted_at": "2026-08-01T10:00:00+00:00",
        "writing_state": writing_state,
    }


def _stage(submission_id: int, feedback_id: int, *,
           priorities: list[dict] | None = None,
           writing_state: str = "feedback_available") -> dict:
    return {
        "submission_id": submission_id,
        "feedback_id": feedback_id,
        "created_at": "2026-08-01T10:02:00+00:00",
        "priority_count": len(priorities or []),
        "priorities": priorities or [],
        "writing_state": writing_state,
    }


def _practice(practice_target_id: str, *, status: str = "active",
              activity_state: str = "available",
              evaluation_state: str = "not_applicable",
              provenance: dict | None = None,
              attempt: dict | None = None,
              evaluation: dict | None = None) -> dict:
    return {
        "practice_target_id": practice_target_id,
        "target_code": "lexical_repetition_local",
        "target_label": "Reduce lexical repetition",
        "status": status,
        "created_at": "2026-08-01T10:03:00+00:00",
        "updated_at": "2026-08-02T10:00:00+00:00" if status == "completed" else None,
        "source_submission_id": 28,
        "priority_provenance": provenance or {
            "status": "legacy", "reference": None},
        "exercise": {"exercise_id": "EX000001",
                     "exercise_type": "sentence_rewrite",
                     "created_at": "2026-08-01T10:03:30+00:00"},
        "attempt": attempt,
        "evaluation": evaluation,
        "activity_state": activity_state,
        "evaluation_state": evaluation_state,
        "completion_state": "completed" if status == "completed" else "active",
    }


VALID_PROVENANCE = {
    "status": "valid",
    "reference": "PRIO-1-0",
    "feedback_id": 1,
    "priority_index": 0,
    "category": "lexical_repetition",
}

ATTEMPT = {
    "attempt_id": "EA000001",
    "attempt_number": 1,
    "status": "submitted",
    "created_at": "2026-08-01T10:04:00+00:00",
}

EVALUATION = {
    "evaluation_id": "PE000001",
    "created_at": "2026-08-01T10:05:00+00:00",
    "completion_status": "completed",
}


def _cycle(*, cycle_id: str = "cycle-28", root: dict | None = None,
           revisions: list[dict] | None = None,
           stages: list[dict] | None = None,
           practices: list[dict] | None = None,
           current_state: str = "completed",
           relationship_status: str = "linked",
           actions: list[dict] | None = None,
           limitations: list[str] | None = None) -> dict:
    root = root if root is not None else _submission(28)
    revisions = revisions if revisions is not None else [
        _submission(29, revision_of=28, writing_state="revision_submitted",
                    is_revision=True)]
    stages = stages if stages is not None else [
        _stage(28, 1, priorities=[{
            "index": 0, "category": "lexical_repetition",
            "diagnosis_id": "D001"}])]
    practices = practices if practices is not None else [
        _practice("PT000001", status="completed",
                  activity_state="completed",
                  evaluation_state="available",
                  provenance=VALID_PROVENANCE,
                  attempt=ATTEMPT, evaluation=EVALUATION)]
    actions = actions if actions is not None else [
        {"action": "open_revision", "submission_id": 28},
        {"action": "open_revision", "submission_id": 29},
        {"action": "open_practice", "practice_target_id": "PT000001"},
    ]
    return {
        "cycle_id": cycle_id,
        "learner_id": "S02",
        "relationship_status": relationship_status,
        "root_submission": root,
        "revisions": revisions,
        "feedback_stages": stages,
        "practice_cycles": practices,
        "current_state": current_state,
        "chronology": [],
        "available_actions": actions,
        "limitations": limitations or [],
    }


def _journey(*cycles: dict, state: str = "journey_events") -> dict:
    return {
        "student_id": "S02",
        "learner_found": True,
        "counts": {
            "submissions": len(cycles), "analysis_runs": 1,
            "feedback_records": 1, "selected_priorities": 1,
            "practice_targets": 1, "exercise_attempts": 1,
            "practice_evaluations": 1, "within_task_responses": 0,
            "transfer_evidence_candidates": 0,
        },
        "events": [],
        "derived_states": [],
        "state": state,
        "cycles": list(cycles),
        "cycles_version": "journey-cycle-v0.9.7-c",
    }


def _run_harness(**config):
    at = AppTest.from_file(str(HARNESS), default_timeout=90)
    for key, value in config.items():
        at.session_state[key] = json.loads(json.dumps(value))
    at.run()
    assert not at.exception, at.exception
    return at


def _markdown_text(at) -> str:
    return " ".join(m.value for m in at.markdown)


def _button_labels(at) -> dict:
    return {button.key: button.label for button in at.button}


def _fake_client(at):
    return at.session_state["fake_client"]


def _base_config(*cycles: dict, lang: str = "en", **extra) -> dict:
    return {
        "sidebar_page": t("learning_journey", lang),
        "selected_student_id": "S02",
        "harness_lang": lang,
        "harness_journey": _journey(*cycles),
        **extra,
    }


class TestCycleRendering:
    """WU3 acceptance 1-5, 9-10: grouped cycle structure and actions."""

    def test_full_cycle_renders_grouped_sections(self):
        at = _run_harness(**_base_config(_cycle()))
        text = _markdown_text(at)
        assert t("student_journey_cycle_title", "en") in text
        assert t("student_journey_original_writing", "en") in text
        assert "#28" in text
        assert t("student_journey_revised_draft", "en") in text
        assert "#29" in text
        assert t("student_journey_revision_of", "en") in text
        assert t("student_journey_feedback", "en") in text
        assert t("student_journey_practice_activity", "en") in text
        assert "Reduce lexical repetition" in text
        labels = _button_labels(at)
        assert labels.get("journey_action_revision_28") == t(
            "student_journey_action_open_revision", "en")
        assert labels.get("journey_action_revision_29") == t(
            "student_journey_action_open_revision", "en")
        assert labels.get("journey_action_practice_PT000001") == t(
            "student_journey_action_open_practice", "en")

    def test_multiple_cycles_render_distinguishably(self):
        second = _cycle(
            cycle_id="cycle-30",
            root=_submission(30),
            revisions=[_submission(31, revision_of=30,
                                   writing_state="revision_submitted",
                                   is_revision=True)],
            stages=[_stage(30, 2, priorities=[
                {"index": 0, "category": "connective_use",
                 "diagnosis_id": "D002"}])],
            practices=[_practice("PT000002")],
            current_state="feedback_available",
            actions=[
                {"action": "open_revision", "submission_id": 30},
                {"action": "open_revision", "submission_id": 31},
                {"action": "open_practice", "practice_target_id": "PT000002"},
            ],
        )
        at = _run_harness(**_base_config(_cycle(), second))
        text = _markdown_text(at)
        assert t("student_journey_cycle_title", "en") in text
        assert "#28" in text and "#30" in text
        order = [m.value for m in at.markdown]
        joined = "\n".join(order)
        assert joined.index("#28") < joined.index("#30")

    def test_original_and_revision_distinction(self):
        at = _run_harness(**_base_config(_cycle()))
        text = _markdown_text(at)
        assert t("student_journey_original_writing", "en") in text
        assert t("student_journey_revised_draft", "en") in text
        assert "Revision of: #28" in text

    def test_priority_reference_caption(self):
        at = _run_harness(**_base_config(_cycle()))
        text = _markdown_text(at)
        assert t("student_journey_priority_reference", "en") in text
        assert "PRIO-1-0" in text
        assert "Reduce lexical repetition" in text

    def test_actions_absent_when_unsupported(self):
        cycle = _cycle(actions=[])
        at = _run_harness(**_base_config(cycle))
        labels = _button_labels(at)
        assert "journey_action_revision_28" not in labels
        assert "journey_action_practice_PT000001" not in labels
        assert "journey_primary_action" in labels  # next-step action remains

    def test_unlinked_cycle_shows_warning(self):
        cycle = _cycle(relationship_status="unlinked",
                       limitations=["unlinked test limitation"])
        at = _run_harness(**_base_config(cycle))
        text = _markdown_text(at)
        assert t("student_journey_cycle_unlinked", "en") in text
        assert "unlinked test limitation" in text


class TestPracticeStates:
    """WU3 acceptance 6-7: active/completed/evaluation states visible."""

    def test_active_practice_available_state(self):
        cycle = _cycle(practices=[_practice("PT000001")])
        at = _run_harness(**_base_config(cycle))
        text = _markdown_text(at)
        assert t("student_journey_state_available", "en") in text
        assert t("student_practice_completed_title", "en") not in text

    def test_completed_practice_uses_allowed_wording(self):
        cycle = _cycle(practices=[
            _practice("PT000001", status="completed",
                      activity_state="completed",
                      evaluation_state="available",
                      provenance=VALID_PROVENANCE,
                      attempt=ATTEMPT, evaluation=EVALUATION)])
        at = _run_harness(**_base_config(cycle))
        text = _markdown_text(at)
        assert t("student_practice_completed_title", "en") in text
        assert t("student_practice_completed_saved", "en") in text
        assert "EA000001" in text
        assert "practice_finish" not in _button_labels(at)

    def test_completed_without_evaluation_stays_honest(self):
        cycle = _cycle(practices=[
            _practice("PT000001", status="completed",
                      activity_state="completed",
                      evaluation_state="unavailable",
                      provenance=VALID_PROVENANCE,
                      attempt=ATTEMPT, evaluation=None)])
        at = _run_harness(**_base_config(cycle))
        text = _markdown_text(at)
        assert t("student_practice_completed_title", "en") in text
        assert t("student_practice_attempt_saved", "en") in text
        assert t("student_practice_evaluation_unavailable", "en") in text

    def test_evaluation_unavailable_state(self):
        cycle = _cycle(practices=[
            _practice("PT000001", activity_state="evaluation_unavailable",
                      evaluation_state="unavailable",
                      provenance=VALID_PROVENANCE, attempt=ATTEMPT)])
        at = _run_harness(**_base_config(cycle))
        text = _markdown_text(at)
        assert t("student_journey_state_evaluation_unavailable", "en") in text
        assert t("student_practice_attempt_saved", "en") in text
        assert t("student_practice_evaluation_unavailable", "en") in text
        assert t("student_practice_completed_title", "en") not in text

    def test_legacy_provenance_note(self):
        cycle = _cycle(practices=[
            _practice("PT000001", provenance={"status": "legacy",
                                              "reference": None})])
        at = _run_harness(**_base_config(cycle))
        assert t("student_journey_practice_legacy", "en") in _markdown_text(at)

    def test_unresolved_provenance_note(self):
        cycle = _cycle(practices=[
            _practice("PT000001", provenance={
                "status": "unresolved", "reference": "PRIO-999-9",
                "reason": "feedback_mismatch"})])
        at = _run_harness(**_base_config(cycle))
        assert t("student_journey_practice_provenance_unresolved", "en") in \
            _markdown_text(at)


class TestWritingStates:
    """WU3 acceptance 8: no-priority and insufficient-evidence states."""

    def test_no_priority_stage(self):
        root = _submission(28, writing_state="feedback_without_priority")
        cycle = _cycle(root=root, revisions=[], stages=[
            _stage(28, 1, priorities=[],
                   writing_state="feedback_without_priority")],
            practices=[], current_state="feedback_without_priority")
        at = _run_harness(**_base_config(cycle))
        text = _markdown_text(at)
        assert t("student_journey_state_feedback_without_priority", "en") in text
        assert t("journey_event_feedback_without_priority_desc", "en") in text

    def test_insufficient_evidence_stage(self):
        root = _submission(28, writing_state="insufficient_evidence")
        cycle = _cycle(root=root, revisions=[], stages=[],
                       practices=[], current_state="insufficient_evidence")
        at = _run_harness(**_base_config(cycle))
        text = _markdown_text(at)
        assert t("student_journey_state_insufficient_evidence", "en") in text
        assert t("journey_event_insufficient_evidence_desc", "en") in text


class TestNavigationActions:
    """WU3: safe action buttons navigate through the WU2 helpers."""

    def test_open_revision_action_navigates(self):
        at = _run_harness(**_base_config(_cycle()))
        at.button(key="journey_action_revision_28").click().run()
        assert not at.exception, at.exception
        assert at.session_state["sidebar_page"] == t("student_revision_title", "en")
        assert at.session_state["revision_source_preset"] == 28
        assert _fake_client(at).revision_post_count == 0

    def test_open_practice_action_navigates(self):
        target = {
            "practice_target_id": "PT000001",
            "student_id": "S02",
            "source_submission_id": 28,
            "source_diagnosis_id": "D001",
            "source_priority_id": "PRIO-1-0",
            "target_code": "lexical_repetition_local",
            "target_label": "Reduce lexical repetition",
            "evidence_ids": ["1"],
            "status": "active",
            "created_at": "2026-08-01T00:00:00+00:00",
        }
        at = _run_harness(
            **_base_config(_cycle()),
            harness_targets=[target],
        )
        at.button(key="journey_action_practice_PT000001").click().run()
        assert not at.exception, at.exception
        assert at.session_state["sidebar_page"] == t("practice", "en")
        assert "practice_target_preset" not in at.session_state
        assert "Reduce lexical repetition" in _markdown_text(at)
        assert _fake_client(at).target_create_count == 0
        assert _fake_client(at).attempt_post_count == 0

    def test_rendering_performs_zero_writes(self):
        at = _run_harness(**_base_config(_cycle()))
        client = _fake_client(at)
        assert client.post_count == 0
        assert client.revision_post_count == 0
        assert client.target_create_count == 0
        assert client.attempt_post_count == 0
        assert client.complete_count == 0

    def test_rerun_is_stable(self):
        at = _run_harness(**_base_config(_cycle()))
        first = _markdown_text(at)
        at.run()
        assert not at.exception, at.exception
        assert _markdown_text(at) == first


class TestEmptyAndErrorStates:
    """WU3 acceptance 11-12: empty and API-error handling."""

    def test_empty_journey_state(self):
        at = _run_harness(
            sidebar_page=t("learning_journey", "en"),
            selected_student_id="S02",
            harness_journey={
                "student_id": "S02", "learner_found": True,
                "counts": {"submissions": 0, "analysis_runs": 0,
                           "feedback_records": 0, "selected_priorities": 0,
                           "practice_targets": 0, "exercise_attempts": 0,
                           "practice_evaluations": 0,
                           "within_task_responses": 0,
                           "transfer_evidence_candidates": 0},
                "events": [], "derived_states": [], "state": "no_submissions",
                "cycles": [],
            },
        )
        assert t("journey_empty_no_submissions_title", "en") in _markdown_text(at)

    def test_api_error_renders_error_box(self):
        script = """
import streamlit as st
from app.ui.api_client import ApiClientError, ErrorCategory
from app.ui.features.student.journey import render_learning_journey_page

class BoomClient:
    def get_journey(self, student_id):
        raise ApiClientError(
            ErrorCategory.BACKEND_PROCESSING_ERROR, "probe boom",
            operation="get_journey")

st.session_state["selected_student_id"] = "S02"
render_learning_journey_page(BoomClient(), "en")
"""
        at = AppTest.from_string(script, default_timeout=30)
        at.run()
        assert not at.exception, at.exception
        assert t("error_backend_processing_error", "en") in _markdown_text(at)


class TestChineseLocalization:
    """WU3 acceptance 15: Chinese cycle UI."""

    def test_chinese_cycle_renders_localized(self):
        at = _run_harness(**_base_config(_cycle(), lang="zh_CN"))
        text = _markdown_text(at)
        assert t("student_journey_cycle_title", "zh_CN") in text
        assert t("student_journey_original_writing", "zh_CN") in text
        assert t("student_journey_revised_draft", "zh_CN") in text
        assert t("student_journey_state_completed", "zh_CN") in text
        labels = _button_labels(at)
        assert labels.get("journey_action_revision_28") == t(
            "student_journey_action_open_revision", "zh_CN")
        assert labels.get("journey_action_practice_PT000001") == t(
            "student_journey_action_open_practice", "zh_CN")
        # No raw keys or English-only cycle copy leaks into the zh view.
        assert "Writing Cycle" not in text
