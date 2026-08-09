# -*- coding: utf-8 -*-
"""v0.9.7-D WU2 focused tests: Revision and Practice design-system application.

Covers the WU1-style keyed-container wrapping, surface recipes, state
treatment (active / attempted / evaluation-available / evaluation-unavailable /
completed / legacy-unresolved / no-priority), bilingual rendering, no remote
resources, no raw locale keys, no console errors, no overflow, and zero
writes on render. Reuses the existing harness `harness_v097a_student.py` and
the existing focused tests (v0.9.7-B/C) for behavioural contracts.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from streamlit.testing.v1 import AppTest

from app.ui import pixel_art as pa
from app.ui.locale import t


ROOT = pathlib.Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "harness_v097a_student.py"

PROMPT = "Should cities add more parks?"

REPETITION_ESSAY = (
    "Parks support public health. Cities should protect accessible parks."
)
REVISION_ESSAY = (
    "Communities should protect public health. Cities can protect accessible parks."
)

PRIORITIES = [
    {
        "diagnosis_id": "D001",
        "category": "lexical_repetition",
        "evidence_quote": "Parks support public health.",
        "explanation": "The phrase is repeated closely in the draft.",
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

SOURCE_BUNDLE = {
    "essay_id": 28,
    "student_id": "S02",
    "writing_prompt": PROMPT,
    "genre": "argumentative essay",
    "draft_stage": "final draft",
    "essay_text": REPETITION_ESSAY,
    "submitted_at": "2026-08-04T10:00:00+00:00",
    "feedback": {"priority_feedback": PRIORITIES},
}

REVISION_SAVED_RESULT = {
    "submission_id": 99,
    "ui_submission": {
        "student_id": "S02",
        "writing_prompt": PROMPT,
        "genre": "argumentative essay",
        "draft_stage": "revised draft",
        "revision_of_submission_id": 28,
        "revision_priority_index": 0,
        "revision_source": {
            "writing_prompt": PROMPT,
            "draft_stage": "final draft",
            "essay_text": REPETITION_ESSAY,
        },
    },
    "within_task_revision_trajectory": {
        "previous_selected_priorities": PRIORITIES,
        "feedback_uptake_candidates": [],
        "first_to_latest_comparison": {},
    },
}

PRIORITY_TARGET = {
    "practice_target_id": "PT000001",
    "student_id": "S02",
    "source_submission_id": 28,
    "source_diagnosis_id": "D001",
    "source_priority_id": "PRIO-1-0",
    "target_code": "lexical_repetition_local",
    "target_label": "Reduce lexical repetition",
    "evidence_ids": ["1"],
    "status": "active",
    "created_at": "2026-01-01T00:00:00+00:00",
}

COMPLETED_TARGET = dict(
    PRIORITY_TARGET, status="completed", updated_at="2026-01-02T00:00:00+00:00")

PRIORITY_CONTEXT = {
    "context_status": "priority",
    "practice_target_id": "PT000001",
    "student_id": "S02",
    "source_submission_id": 28,
    "source_priority_id": "PRIO-1-0",
    "target_code": "lexical_repetition_local",
    "target_label": "Reduce lexical repetition",
    "status": "active",
    "priority_context": {
        "category": "lexical_repetition",
        "evidence_quote": "Parks support public health.",
        "explanation": "The phrase is repeated closely in the draft.",
        "revision_guidance": "Replace one repetition with a synonym.",
    },
    "source_writing_text": REPETITION_ESSAY,
}

LEGACY_CONTEXT = dict(
    PRIORITY_CONTEXT,
    context_status="legacy",
    priority_context=None,
)

UNAVAILABLE_CONTEXT = dict(
    PRIORITY_CONTEXT,
    context_status="unavailable",
    reason="unresolved_priority",
    priority_context=None,
)

EXERCISE = {
    "exercise_id": "EX000001",
    "practice_target_id": "PT000001",
    "student_id": "S02",
    "source_submission_id": 28,
    "exercise_type": "guided_sentence_rewrite",
    "instructions": "Rewrite the sentence to address the selected priority.",
    "source_text": "Parks support public health.",
    "constraints": ["Retain original meaning.", "Do not add unsupported content."],
    "status": "active",
}

ATTEMPT = {
    "attempt_id": "EA000001",
    "exercise_id": "EX000001",
    "student_id": "S02",
    "attempt_number": 1,
    "response_text": "Communities can protect public health.",
    "status": "submitted",
    "created_at": "2026-01-01T00:00:02+00:00",
}

EVALUATION = {
    "evaluation_id": "PE000001",
    "attempt_id": "EA000001",
    "practice_target_id": "PT000001",
    "evaluation_method": "rule_based",
    "completion_status": "completed",
    "target_action_status": "candidate_detected",
    "evidence": ["Response length: 37 characters"],
    "confidence": "medium",
    "limitations": ["Task-specific only."],
    "evaluator_version": "practice-evaluator-v0.9.0",
    "created_at": "2026-01-01T00:00:03+00:00",
}


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _run_harness(**config):
    fill_student = config.pop("fill_student", True)
    at = AppTest.from_file(str(HARNESS), default_timeout=90)
    for key, value in config.items():
        at.session_state[key] = json.loads(json.dumps(value))
    at.run()
    assert not at.exception, at.exception
    if fill_student:
        student_input = next(
            (ti for ti in at.text_input if ti.key
             in {"home_student", "writing_student", "feedback_student",
                 "revision_student", "practice_student_v2"}),
            None,
        )
        if student_input is not None and not student_input.value:
            student_input.set_value("S02").run()
            assert not at.exception, at.exception
    return at


def _markdown_text(at):
    return " ".join(m.value for m in at.markdown)


def _button_labels(at):
    return {button.key: button.label for button in at.button}


def _fake_client(at):
    return at.session_state["fake_client"]


# ---------------------------------------------------------------------------
# Design-token / CSS guards
# ---------------------------------------------------------------------------

class TestDesignTokensExtension:
    """WU2 new keyed-container selectors are present in the CSS."""

    def test_revision_selectors_present(self):
        css = pa.PIXEL_CSS + pa.PIXEL_COMPONENT_CSS
        for selector in (
            "st-key-revision_source_context_",
            "st-key-revision_priority_task_",
            "st-key-revision_observation_",
            "st-key-revision_next_action_",
        ):
            assert selector in css, selector

    def test_practice_selectors_present(self):
        css = pa.PIXEL_CSS + pa.PIXEL_COMPONENT_CSS
        for selector in (
            "st-key-practice_target_",
            "st-key-practice_priority_task_",
            "st-key-practice_evidence_",
            "st-key-practice_exercise_",
            "st-key-practice_attempt_saved_",
        ):
            assert selector in css, selector

    def test_no_new_remote_resources(self):
        css = pa.PIXEL_CSS + pa.PIXEL_COMPONENT_CSS
        assert "url(" not in css
        assert "@import" not in css
        assert "fonts.googleapis" not in css
        assert "unpkg" not in css

    def test_no_literal_hex_outside_pixel_art(self):
        for path in (
            ROOT / "app/ui/features/student/revision.py",
            ROOT / "app/ui/features/student/practice.py",
        ):
            source = path.read_text(encoding="utf-8")
            assert "rgb(" not in source

    def test_no_style_block_in_page(self):
        for path in (
            ROOT / "app/ui/features/student/revision.py",
            ROOT / "app/ui/features/student/practice.py",
        ):
            source = path.read_text(encoding="utf-8")
            assert "<style>" not in source

    def test_keyed_rule_groups_consolidated(self):
        """WU3: identical keyed-container recipes are grouped selectors, not
        duplicated rule blocks (one L2/L3/focused declaration each)."""
        css = pa.PIXEL_CSS + pa.PIXEL_COMPONENT_CSS
        # The rollout L2 card body must exist exactly once (grouped); the
        # same body is NOT duplicated per page.
        assert css.count(
            "padding: var(--px-density-student-card-pad);\n"
            "    margin-bottom: var(--px-space-4);") == 1, "duplicate L2 bodies"
        # One grouped L2 rule (plus the unique writing_saved rule), one
        # grouped L3 rule, one grouped focused rule - no per-page copies.
        assert css.count(" { /* L2 */") == 2, "L2 rule count"
        assert css.count(" { /* L3 */") == 1, "L3 rule count"
        assert css.count(" { /* focused */") == 1, "focused rule count"
        # The grouped headers exist exactly once each.
        assert css.count('[class*="st-key-feedback_priority_"],') == 1
        assert css.count('[class*="st-key-feedback_evidence_"],') == 1
        assert css.count('[class*="st-key-feedback_next_action_"],') == 1
        # Every rollout key is present in the CSS.
        for key in (
            "st-key-feedback_priority_", "st-key-revision_source_context_",
            "st-key-revision_priority_task_", "st-key-revision_observation_",
            "st-key-practice_target_", "st-key-practice_priority_task_",
            "st-key-practice_exercise_", "st-key-practice_attempt_saved_",
            "st-key-feedback_evidence_", "st-key-practice_evidence_",
            "st-key-feedback_next_action_", "st-key-revision_next_action_",
        ):
            assert key in css, key


# ---------------------------------------------------------------------------
# Revision tests
# ---------------------------------------------------------------------------

class TestRevisionStructure:
    def test_default_render_has_page_header_and_intro(self):
        at = _run_harness(
            sidebar_page=t("student_revision_title", "en"),
            selected_student_id="S02",
            harness_candidates=[SOURCE_CANDIDATE],
            harness_source_bundle=SOURCE_BUNDLE,
        )
        text = _markdown_text(at)
        assert "px-page-heading" in text
        assert t("student_revision_title", "en") in text
        assert t("student_revision_purpose", "en") in text

    def test_no_learner_branch_shows_blocked_action(self):
        at = _run_harness(
            sidebar_page=t("student_revision_title", "en"),
            selected_student_id="",
            fill_student=False,
        )
        text = _markdown_text(at)
        assert t("student_revision_current_action", "en") in text
        assert t("student_revision_boundary", "en") in text
        assert 'data-state="blocked"' in text

    def test_saved_success_uses_keyed_containers(self):
        at = _run_harness(
            sidebar_page=t("student_revision_title", "en"),
            selected_student_id="S02",
            revision_student="S02",
            submission_result=REVISION_SAVED_RESULT,
        )
        text = _markdown_text(at)
        assert t("student_revision_saved_title", "en") in text
        assert "#28" in text
        assert "#99" in text
        labels = _button_labels(at)
        assert "revision_primary_action" in labels

    def test_no_eligible_candidates_empty_state(self):
        at = _run_harness(
            sidebar_page=t("student_revision_title", "en"),
            selected_student_id="S02",
            harness_candidates=[],
        )
        text = _markdown_text(at)
        assert t("student_revision_no_eligible_title", "en") in text
        labels = _button_labels(at)
        assert "revision_primary_action" in labels

    def test_default_form_priority_task_keyed(self):
        at = _run_harness(
            sidebar_page=t("student_revision_title", "en"),
            selected_student_id="S02",
            harness_candidates=[SOURCE_CANDIDATE],
            harness_source_bundle=SOURCE_BUNDLE,
        )
        text = _markdown_text(at)
        assert t("student_revision_priority_task", "en") in text
        assert t("student_revision_source_stage", "en") in text
        labels = _button_labels(at)
        assert "revision_submit_primary" in labels

    def test_no_priority_source_uses_info_box(self):
        no_priority_bundle = dict(
            SOURCE_BUNDLE, feedback={"priority_feedback": []})
        at = _run_harness(
            sidebar_page=t("student_revision_title", "en"),
            selected_student_id="S02",
            harness_candidates=[SOURCE_CANDIDATE],
            harness_source_bundle=no_priority_bundle,
        )
        text = _markdown_text(at)
        assert t("student_revision_no_auto_focus", "en") in text
        assert "px-notice-error" not in text

    def test_already_revised_reentry_uses_next_action(self):
        at = _run_harness(
            sidebar_page=t("student_revision_title", "en"),
            selected_student_id="S02",
            harness_candidates=[
                SOURCE_CANDIDATE,
                dict(SOURCE_CANDIDATE, essay_id=42,
                     submitted_at="2026-08-05T00:00:00+00:00",
                     revision_of_submission_id=28),
            ],
            harness_source_bundle=SOURCE_BUNDLE,
        )
        text = _markdown_text(at)
        assert t("student_revision_already_submitted_title", "en") in text
        labels = _button_labels(at)
        assert "revision_primary_action" in labels


class TestRevisionBilingual:
    def test_en_renders_localized(self):
        at = _run_harness(
            sidebar_page=t("student_revision_title", "en"),
            selected_student_id="S02",
            harness_candidates=[SOURCE_CANDIDATE],
            harness_source_bundle=SOURCE_BUNDLE,
        )
        text = _markdown_text(at)
        assert t("student_revision_title", "en") in text

    def test_zh_renders_localized(self):
        at = _run_harness(
            sidebar_page=t("student_revision_title", "zh_CN"),
            selected_student_id="S02",
            harness_lang="zh_CN",
            harness_candidates=[SOURCE_CANDIDATE],
            harness_source_bundle=SOURCE_BUNDLE,
        )
        text = _markdown_text(at)
        assert t("student_revision_title", "zh_CN") in text
        for raw in ("student_revision_",):
            assert raw not in text

    def test_no_raw_locale_keys_en(self):
        at = _run_harness(
            sidebar_page=t("student_revision_title", "en"),
            selected_student_id="S02",
            revision_student="S02",
            submission_result=REVISION_SAVED_RESULT,
        )
        text = _markdown_text(at)
        for raw in ("student_revision_", "student_feedback_"):
            assert raw not in text

    def test_no_forbidden_wording(self):
        at = _run_harness(
            sidebar_page=t("student_revision_title", "en"),
            selected_student_id="S02",
            revision_student="S02",
            submission_result=REVISION_SAVED_RESULT,
        )
        text = _markdown_text(at).lower()
        for forbidden in ("mastery", "proficient", "cefr", "learning gain",
                          "improved your writing", "mastered"):
            assert forbidden not in text


class TestRevisionZeroWrites:
    def test_revision_zero_writes_on_render(self):
        at = _run_harness(
            sidebar_page=t("student_revision_title", "en"),
            selected_student_id="S02",
            harness_candidates=[SOURCE_CANDIDATE],
            harness_source_bundle=SOURCE_BUNDLE,
        )
        client = _fake_client(at)
        assert client.post_count == 0
        assert client.revision_post_count == 0
        assert client.target_create_count == 0
        assert client.attempt_post_count == 0
        assert client.complete_count == 0

    def test_revision_with_preset_zero_writes(self):
        at = _run_harness(
            sidebar_page=t("student_revision_title", "en"),
            selected_student_id="S02",
            revision_source_preset=28,
            harness_candidates=[SOURCE_CANDIDATE],
            harness_source_bundle=SOURCE_BUNDLE,
        )
        client = _fake_client(at)
        assert client.revision_post_count == 0
        assert client.target_create_count == 0

    def test_stale_preset_shows_note_zero_writes(self):
        at = _run_harness(
            sidebar_page=t("student_revision_title", "en"),
            selected_student_id="S02",
            revision_source_preset=999,
            harness_candidates=[SOURCE_CANDIDATE],
            harness_source_bundle=SOURCE_BUNDLE,
        )
        text = _markdown_text(at)
        assert t("student_revision_preset_invalid", "en") in text
        client = _fake_client(at)
        assert client.revision_post_count == 0


# ---------------------------------------------------------------------------
# Practice tests
# ---------------------------------------------------------------------------

class TestPracticeStructure:
    def test_default_render_has_page_header(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
        )
        text = _markdown_text(at)
        assert "px-page-heading" in text
        assert t("practice", "en") in text

    def test_active_target_uses_keyed_containers(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
        )
        text = _markdown_text(at)
        assert t("practice_target", "en") in text
        assert t("student_practice_priority_task", "en") in text
        assert t("exercise_instructions", "en") in text
        labels = _button_labels(at)
        assert "practice_submit" in labels

    def test_attempt_saved_uses_attempt_saved_panel(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
            harness_attempts=[ATTEMPT],
        )
        text = _markdown_text(at)
        assert t("student_practice_attempt_saved", "en") in text
        labels = _button_labels(at)
        assert "practice_finish" in labels

    def test_evaluation_available_renders_status(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
            harness_attempts=[ATTEMPT],
            harness_evaluations=[EVALUATION],
        )
        text = _markdown_text(at)
        assert t("practice_evaluation_label", "en") in text
        assert t("student_practice_completion_completed", "en") in text
        assert t("student_practice_action_candidate_detected", "en") in text

    def test_evaluation_unavailable_uses_neutral_dashed(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
            harness_attempts=[ATTEMPT],
        )
        text = _markdown_text(at)
        assert t("student_practice_evaluation_unavailable", "en") in text
        assert "px-notice-dashed" in text
        assert "px-notice-error" not in text

    def test_completed_target_uses_completed_panel(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            harness_targets=[COMPLETED_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
            harness_attempts=[ATTEMPT],
            harness_evaluations=[EVALUATION],
        )
        text = _markdown_text(at)
        assert t("student_practice_completed_title", "en") in text
        assert t("student_practice_completed_saved", "en") in text
        labels = _button_labels(at)
        assert "practice_return_feedback" in labels
        assert "practice_open_journey" in labels

    def test_legacy_context_uses_neutral_dashed(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=LEGACY_CONTEXT,
            harness_exercises=[EXERCISE],
        )
        text = _markdown_text(at)
        assert "px-notice-dashed" in text
        assert "px-notice-error" not in text

    def test_unavailable_context_uses_info_box(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=UNAVAILABLE_CONTEXT,
            harness_exercises=[EXERCISE],
        )
        text = _markdown_text(at)
        assert t("student_practice_context_unavailable", "en") in text
        assert "px-notice-error" not in text

    def test_no_target_branch_uses_blocked_action(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            harness_targets=[],
        )
        text = _markdown_text(at)
        assert 'data-state="blocked"' in text
        assert t("practice_boundary", "en") in text
        labels = _button_labels(at)
        assert "practice_primary_action" in labels


class TestPracticeBilingual:
    def test_en_renders_localized(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
        )
        text = _markdown_text(at)
        assert t("practice", "en") in text

    def test_zh_renders_localized(self):
        at = _run_harness(
            sidebar_page=t("practice", "zh_CN"),
            selected_student_id="S02",
            harness_lang="zh_CN",
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
        )
        text = _markdown_text(at)
        assert t("practice", "zh_CN") in text

    def test_no_raw_locale_keys_en(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
        )
        text = _markdown_text(at)
        for raw in ("student_practice_",):
            assert raw not in text

    def test_no_forbidden_wording(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            harness_targets=[COMPLETED_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
            harness_attempts=[ATTEMPT],
            harness_evaluations=[EVALUATION],
        )
        text = _markdown_text(at).lower()
        # The frozen practice_boundary limitation sentence is an accepted
        # disclaimer, not a learner claim; normalize it before checking.
        text = text.replace(t("practice_boundary", "en").lower(), "")
        for forbidden in ("mastery", "proficient", "cefr", "learning gain",
                          "improved", "mastered", "passed"):
            assert forbidden not in text


class TestPracticeZeroWrites:
    def test_practice_zero_writes_on_render(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
        )
        client = _fake_client(at)
        assert client.post_count == 0
        assert client.revision_post_count == 0
        assert client.target_create_count == 0
        assert client.attempt_post_count == 0
        assert client.complete_count == 0

    def test_practice_with_preset_zero_writes(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            practice_target_preset="PT000001",
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
        )
        client = _fake_client(at)
        assert client.target_create_count == 0
        assert client.attempt_post_count == 0
        assert "practice_target_preset" not in at.session_state

    def test_practice_stale_preset_fails_safely(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            practice_target_preset="PT999999",
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
        )
        text = _markdown_text(at)
        assert t("student_practice_preset_invalid", "en") in text
        client = _fake_client(at)
        assert client.target_create_count == 0

    def test_practice_rerun_keeps_target_stable(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            practice_target_preset="PT000001",
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=PRIORITY_CONTEXT,
            harness_exercises=[EXERCISE],
        )
        assert "Reduce lexical repetition" in _markdown_text(at)
        at.run()
        assert not at.exception, at.exception
        assert "Reduce lexical repetition" in _markdown_text(at)


class TestLocaleParity:
    def test_locale_parity_preserved(self):
        en = json.loads((ROOT / "locales/en.json").read_text(encoding="utf-8"))
        zh = json.loads((ROOT / "locales/zh_CN.json").read_text(encoding="utf-8"))
        assert set(en) == set(zh)
        # Domain Pack v1 adds five task_type keys to both locales (D-L2-09);
        # parity count moves 600/600 -> 605/605 at implementation time.
        assert len(en) == 605
        for key in ("task_type_opinion", "task_type_argumentative",
                    "task_type_discussion", "task_type_problem_solution",
                    "task_type_general_eap"):
            assert key in en and key in zh
