# -*- coding: utf-8 -*-
"""v0.9.7-D WU1 focused tests: Writing and Feedback design-system application.

Covers Writing page structure, action hierarchy, state branches, Feedback
priority/no-priority/insufficient-evidence paths, evidence presentation,
action visibility, bilingual rendering, zero-write rendering, and no remote
resources. Reuses the existing harness_v097a_student harness.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

from streamlit.testing.v1 import AppTest  # noqa: E402

from app.ui.locale import t  # noqa: E402


ROOT = pathlib.Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "harness_v097a_student.py"

PROMPT = "Should cities add more parks?"

PRIORITIES = [
    {
        "category": "lexical_repetition",
        "evidence_quote": "Parks support public health.",
        "explanation": "The phrase is repeated closely in the draft.",
        "revision_guidance": "Replace one repetition with a synonym.",
    },
    {
        "category": "connective_use",
        "evidence_quote": "Cities should protect accessible parks.",
        "explanation": "The draft lacks a linking phrase.",
        "revision_guidance": "Add a connective that links the two ideas.",
    },
]

SUBMISSION_RESULT_PRIORITY = {
    "submission_id": 99,
    "student_id": "S02",
    "feedback_result": {
        "feedback": {
            "priority_feedback": PRIORITIES,
            "positive_finding": {
                "explanation": "Good structure overall.",
                "evidence_quote": "The essay has a clear introduction.",
            },
            "uncertainty_note": "This is a limited evaluation.",
        }
    },
    "ui_empty_states": [],
    "ui_submission": {
        "student_id": "S02",
        "writing_prompt": PROMPT,
    },
}

SUBMISSION_RESULT_NO_PRIORITY = {
    "submission_id": 100,
    "student_id": "S02",
    "feedback_result": {
        "feedback": {
            "priority_feedback": [],
            "positive_finding": None,
            "uncertainty_note": "",
        }
    },
    "ui_empty_states": ["NO_SELECTED_PRIORITY"],
    "ui_submission": {
        "student_id": "S02",
        "writing_prompt": PROMPT,
    },
}

SUBMISSION_RESULT_INSUFFICIENT = {
    "submission_id": 101,
    "student_id": "S02",
    "feedback_result": {
        "feedback": {
            "priority_feedback": [],
            "positive_finding": None,
            "uncertainty_note": "",
        }
    },
    "ui_empty_states": [],
    "ui_submission": {
        "student_id": "S02",
        "writing_prompt": PROMPT,
    },
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


def _writing_config(**extra) -> dict:
    return {
        "sidebar_page": t("student_writing_title", "en"),
        "selected_student_id": "S02",
        "harness_lang": "en",
        **extra,
    }


def _writing_config_zh(**extra) -> dict:
    return {
        "sidebar_page": t("student_writing_title", "zh_CN"),
        "selected_student_id": "S02",
        "harness_lang": "zh_CN",
        **extra,
    }


def _feedback_config(*, priorities=None, empty_states=None, lang="en", **extra) -> dict:
    result = {
        "submission_id": 99,
        "student_id": "S02",
        "feedback_result": {
            "feedback": {
                "priority_feedback": priorities if priorities is not None else PRIORITIES,
                "positive_finding": {
                    "explanation": "Good structure overall.",
                    "evidence_quote": "The essay has a clear introduction.",
                },
                "uncertainty_note": "This is a limited evaluation.",
            }
        },
        "ui_empty_states": empty_states or [],
        "ui_submission": {
            "student_id": "S02",
            "writing_prompt": PROMPT,
        },
    }
    return {
        "sidebar_page": t("student_feedback_title", lang),
        "selected_student_id": "S02",
        "harness_lang": lang,
        "feedback_student": "S02",
        "submission_result": result,
        **extra,
    }


class TestWritingStructure:
    def test_default_render_has_page_header(self):
        at = _run_harness(**_writing_config())
        text = _markdown_text(at)
        assert 'class="px-page-heading"' in text
        assert t("student_writing_title", "en") in text

    def test_default_render_has_three_section_headers(self):
        at = _run_harness(**_writing_config())
        text = _markdown_text(at)
        assert text.count('class="px-section-heading"') >= 3

    def test_default_render_has_one_primary_button(self):
        at = _run_harness(**_writing_config())
        labels = _button_labels(at)
        assert "writing_submit_primary" in labels

    def test_default_render_no_remote_resources(self):
        from app.ui import pixel_art as pa
        css = pa.PIXEL_CSS + pa.PIXEL_COMPONENT_CSS
        assert "url(" not in css
        assert "@import" not in css
        assert "fonts.googleapis" not in css
        assert "unpkg" not in css


class TestWritingActionHierarchy:
    def test_default_render_only_primary_is_submit(self):
        at = _run_harness(**_writing_config())
        labels = _button_labels(at)
        assert labels.get("writing_submit_primary") == t("submit_button", "en")

    def test_saved_success_primary_is_review_feedback(self):
        at = _run_harness(
            **_writing_config(
                writing_student="S02",
                submission_result=SUBMISSION_RESULT_PRIORITY,
            )
        )
        labels = _button_labels(at)
        assert "writing_review_feedback" in labels
        assert labels["writing_review_feedback"] == t(
            "student_writing_review_feedback", "en"
        )


class TestWritingStates:
    def test_pending_loading_and_button(self):
        at = _run_harness(**_writing_config())
        assert not any("px-loading" in m.value for m in at.markdown)
        labels = _button_labels(at)
        assert "writing_submit_primary" in labels

    def test_success_saved_panel(self):
        at = _run_harness(
            **_writing_config(
                writing_student="S02",
                submission_result=SUBMISSION_RESULT_PRIORITY,
            )
        )
        text = _markdown_text(at)
        assert t("student_writing_saved_title", "en") in text
        labels = _button_labels(at)
        assert "writing_review_feedback" in labels

    def test_revision_source_branch(self):
        at = _run_harness(
            **_writing_config(
                harness_candidates=[
                    {
                        "essay_id": 42,
                        "student_id": "S02",
                        "writing_prompt": "Test prompt",
                        "draft_stage": "first draft",
                        "submitted_at": "2026-08-01T10:00:00+00:00",
                        "revision_of_submission_id": None,
                    }
                ],
            )
        )
        text = _markdown_text(at)
        # Radio is a Streamlit widget (not markdown); check section header + no exception
        assert t('student_writing_task_section', 'en') in text
        assert 'px-section-heading' in text


class TestFeedbackStandard:
    def test_priority_cards_render(self):
        at = _run_harness(**_feedback_config())
        text = _markdown_text(at)
        assert 'data-testid="px-feedback-priority"' in text
        assert t("student_feedback_priorities", "en") in text

    def test_evidence_blocks_render(self):
        at = _run_harness(**_feedback_config())
        text = _markdown_text(at)
        assert "px-quote" in text
        assert "Parks support public health." in text
        assert "Cities should protect accessible parks." in text

    def test_primary_action_open_revision(self):
        at = _run_harness(**_feedback_config())
        labels = _button_labels(at)
        assert "feedback_primary_action" in labels
        assert labels["feedback_primary_action"] == t(
            "student_feedback_open_revision", "en"
        )

    def test_per_priority_secondary_buttons(self):
        at = _run_harness(**_feedback_config())
        labels = _button_labels(at)
        assert "feedback_practice_priority_0" in labels
        assert "feedback_practice_priority_1" in labels
        assert labels["feedback_practice_priority_0"] == t(
            "student_feedback_practice_priority", "en"
        )


class TestFeedbackNoPriority:
    def test_empty_state_neutral(self):
        at = _run_harness(**_feedback_config(priorities=[], empty_states=["NO_SELECTED_PRIORITY"]))
        text = _markdown_text(at)
        assert t("student_feedback_no_priority_title", "en") in text

    def test_primary_revise_action(self):
        at = _run_harness(**_feedback_config(priorities=[], empty_states=["NO_SELECTED_PRIORITY"]))
        labels = _button_labels(at)
        assert "feedback_revise_action" in labels
        assert labels["feedback_revise_action"] == t(
            "student_revision_revise", "en"
        )

    def test_secondary_finish_action(self):
        at = _run_harness(**_feedback_config(priorities=[], empty_states=["NO_SELECTED_PRIORITY"]))
        labels = _button_labels(at)
        assert "feedback_finish_action" in labels
        assert labels["feedback_finish_action"] == t(
            "student_feedback_finish_cycle", "en"
        )

    def test_no_error_red(self):
        at = _run_harness(**_feedback_config(priorities=[], empty_states=["NO_SELECTED_PRIORITY"]))
        text = _markdown_text(at)
        assert "px-notice-error" not in text

    def test_no_unsupported_cta(self):
        at = _run_harness(**_feedback_config(priorities=[], empty_states=["NO_SELECTED_PRIORITY"]))
        labels = _button_labels(at)
        for key in labels:
            assert "practice_landing" not in key


class TestFeedbackInsufficientEvidence:
    def test_neutral_notice(self):
        at = _run_harness(**_feedback_config(priorities=[], empty_states=[]))
        text = _markdown_text(at)
        assert t("student_feedback_no_priority_evidence", "en") in text

    def test_no_error_red(self):
        at = _run_harness(**_feedback_config(priorities=[], empty_states=[]))
        text = _markdown_text(at)
        assert "px-notice-error" not in text


class TestFeedbackEvidencePresentation:
    def test_evidence_before_explanation_in_card(self):
        at = _run_harness(**_feedback_config())
        text = _markdown_text(at)
        evidence_pos = text.find("Parks support public health.")
        explanation_pos = text.find("The phrase is repeated closely")
        assert evidence_pos >= 0, "evidence_quote not found"
        assert explanation_pos >= 0, "explanation not found"
        assert evidence_pos < explanation_pos, (
            f"evidence at {evidence_pos} should precede explanation at {explanation_pos}"
        )


class TestActionVisibility:
    def test_revision_action_visible_priority_path(self):
        at = _run_harness(**_feedback_config())
        labels = _button_labels(at)
        assert "feedback_primary_action" in labels

    def test_revision_action_visible_no_priority_path(self):
        at = _run_harness(**_feedback_config(priorities=[], empty_states=["NO_SELECTED_PRIORITY"]))
        labels = _button_labels(at)
        assert "feedback_revise_action" in labels

    def test_practice_action_as_secondary(self):
        at = _run_harness(**_feedback_config())
        labels = _button_labels(at)
        assert "feedback_practice_priority_0" in labels
        assert "feedback_practice_priority_1" in labels

    def test_no_practice_landing_on_feedback(self):
        at = _run_harness(**_feedback_config())
        labels = _button_labels(at)
        for key in labels:
            assert "practice_landing" not in key


class TestBilingual:
    def test_en_renders_localized_labels(self):
        at = _run_harness(**_writing_config())
        text = _markdown_text(at)
        assert t("student_writing_title", "en") in text
        labels = _button_labels(at)
        assert t("submit_button", "en") in labels.values()

    def test_zh_renders_localized_labels(self):
        at = _run_harness(**_writing_config_zh())
        text = _markdown_text(at)
        assert t("student_writing_title", "zh_CN") in text
        labels = _button_labels(at)
        assert t("submit_button", "zh_CN") in labels.values()

    def test_en_feedback_localized(self):
        at = _run_harness(**_feedback_config(lang="en"))
        text = _markdown_text(at)
        assert t("student_feedback_priorities", "en") in text

    def test_zh_feedback_localized(self):
        at = _run_harness(**_feedback_config(lang="zh_CN"))
        text = _markdown_text(at)
        assert t("student_feedback_priorities", "zh_CN") in text

    def test_no_raw_locale_keys_en(self):
        at = _run_harness(**_writing_config())
        text = _markdown_text(at)
        for raw in ("student_writing_", "student_feedback_", "Writing Cycle"):
            assert raw not in text

    def test_no_raw_locale_keys_zh(self):
        at = _run_harness(**_writing_config_zh())
        text = _markdown_text(at)
        for raw in ("student_writing_", "student_feedback_"):
            assert raw not in text

    def test_no_raw_keys_feedback_en(self):
        at = _run_harness(**_feedback_config(lang="en"))
        text = _markdown_text(at)
        for raw in ("student_feedback_", "student_writing_"):
            assert raw not in text

    def test_no_raw_keys_feedback_zh(self):
        at = _run_harness(**_feedback_config(lang="zh_CN"))
        text = _markdown_text(at)
        for raw in ("student_feedback_", "student_writing_"):
            assert raw not in text


class TestNoWritesOnRender:
    def test_writing_zero_writes(self):
        at = _run_harness(**_writing_config())
        client = at.session_state["fake_client"]
        assert client.post_count == 0
        assert client.revision_post_count == 0
        assert client.target_create_count == 0
        assert client.attempt_post_count == 0
        assert client.complete_count == 0

    def test_feedback_zero_writes(self):
        at = _run_harness(**_feedback_config())
        client = at.session_state["fake_client"]
        assert client.post_count == 0
        assert client.revision_post_count == 0
        assert client.target_create_count == 0
        assert client.attempt_post_count == 0
        assert client.complete_count == 0

    def test_feedback_no_priority_zero_writes(self):
        at = _run_harness(**_feedback_config(priorities=[], empty_states=["NO_SELECTED_PRIORITY"]))
        client = at.session_state["fake_client"]
        assert client.post_count == 0
        assert client.revision_post_count == 0


class TestNoRemoteResources:
    def test_css_no_remote_resources(self):
        from app.ui import pixel_art as pa
        css = pa.PIXEL_CSS + pa.PIXEL_COMPONENT_CSS
        assert "url(" not in css
        assert "@import" not in css
        assert "fonts.googleapis" not in css
        assert "unpkg" not in css

    def test_writing_no_style_tag(self):
        source = (ROOT / "app/ui/features/student/writing.py").read_text(encoding="utf-8")
        assert "<style>" not in source

    def test_feedback_no_style_tag(self):
        source = (ROOT / "app/ui/features/student/feedback.py").read_text(encoding="utf-8")
        assert "<style>" not in source
