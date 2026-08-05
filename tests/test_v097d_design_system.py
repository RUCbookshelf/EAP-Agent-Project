"""v0.9.7-D D1.2 focused tests: Student design-system foundations and the
Journey representative implementation.

Covers token availability, shared component output (quiet badges/notices,
page/section heading classes), Journey page structure (cycle cards, stage
items, status badges), status variants (active/completed, evaluation
unavailable, no-priority, insufficient evidence, legacy), empty and API
error states, action hierarchy, locale usage, no remote resources, no
page-specific CSS, and zero-write rendering.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

from streamlit.testing.v1 import AppTest  # noqa: E402

from app.ui import pixel_art as pa  # noqa: E402
from app.ui.locale import t  # noqa: E402


ROOT = pathlib.Path(__file__).resolve().parents[1]
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
                  attempt=ATTEMPT)]
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


def _base_config(*cycles: dict, lang: str = "en", **extra) -> dict:
    return {
        "sidebar_page": t("learning_journey", lang),
        "selected_student_id": "S02",
        "harness_lang": lang,
        "harness_journey": _journey(*cycles),
        **extra,
    }


class TestDesignTokens:
    def test_approved_tokens_available(self):
        css_vars = pa.build_css_vars()
        for name in (
            "--px-border-subtle", "--px-destructive",
            "--px-status-accent-success", "--px-status-accent-warning",
            "--px-status-accent-error", "--px-status-accent-info",
            "--px-status-accent-neutral", "--px-font-display",
            "--px-font-size-card-title", "--px-font-weight-semibold",
            "--px-icon-sm", "--px-icon-md", "--px-icon-lg",
        ):
            assert name in css_vars, name

    def test_heading_role_is_sans_display(self):
        assert pa.build_css_vars()["--px-font-heading"] == \
            "var(--px-font-display)"

    def test_quiet_notice_recipes_present(self):
        css = pa.PIXEL_COMPONENT_CSS
        assert ".px-notice-warning" in css
        assert ".px-notice-success" in css
        assert "border-left: var(--px-border-thick)" in css
        assert ".px-notice-dashed" in css
        assert ".px-status-badge[data-state=\"success\"]" in css

    def test_no_remote_resources(self):
        css = pa.PIXEL_CSS + pa.PIXEL_COMPONENT_CSS
        assert "url(" not in css
        assert "@import" not in css
        assert "fonts.googleapis" not in css
        assert "unpkg" not in css


class TestSharedComponents:
    def test_status_badge_has_icon_and_label(self, monkeypatch):
        import streamlit as st

        captured = []

        def fake_markdown(body, unsafe_allow_html=False):
            captured.append(body)

        monkeypatch.setattr(st, "markdown", fake_markdown)
        from app.ui import components as c

        c.status_badge("completed", "en")
        html = captured[-1]
        assert 'data-testid="px-status-badge"' in html
        assert 'data-state="success"' in html
        assert "px-icon" in html
        assert t("status_completed", "en") in html

    def test_notice_core_has_accent_icon_and_label(self, monkeypatch):
        import streamlit as st

        captured = []

        def fake_markdown(body, unsafe_allow_html=False):
            captured.append(body)

        monkeypatch.setattr(st, "markdown", fake_markdown)
        from app.ui import components as c

        c.notice("app_prototype_warning", "en", state="warning")
        html = captured[-1]
        assert 'class="px-notice px-notice-warning"' in html
        assert "px-icon" in html

    def test_page_and_section_headers_use_classes(self, monkeypatch):
        import streamlit as st

        captured = []

        def fake_markdown(body, unsafe_allow_html=False):
            captured.append(body)

        monkeypatch.setattr(st, "markdown", fake_markdown)
        from app.ui import components as c

        c.page_header("student_home_title", lang="en")
        c.section_header("student_home_current_task", lang="en")
        assert 'class="px-page-heading"' in captured[0]
        assert 'class="px-section-heading"' in captured[1]


class TestJourneyStructure:
    def test_cycle_card_and_stage_items_render(self):
        at = _run_harness(**_base_config(_cycle()))
        text = _markdown_text(at)
        assert 'data-testid="px-cycle-head"' in text
        assert text.count('data-testid="px-stage-item"') == 4  # 2 subs + fb + practice
        assert 'data-testid="px-status-badge"' in text
        assert t("student_journey_cycle_title", "en") in text

    def test_stage_badge_state_families(self):
        neutral_cycle = _cycle(
            cycle_id="cycle-30",
            root=_submission(30, writing_state="insufficient_evidence"),
            revisions=[], stages=[], practices=[], actions=[],
            current_state="insufficient_evidence")
        at = _run_harness(**_base_config(_cycle(), neutral_cycle))
        text = _markdown_text(at)
        assert 'data-state="success"' in text  # completed / revision badge
        assert 'data-state="neutral"' in text  # insufficient-evidence family

    def test_active_and_completed_practice_distinct(self):
        cycle = _cycle(practices=[
            _practice("PT000001", status="completed",
                      activity_state="completed",
                      evaluation_state="available",
                      provenance=VALID_PROVENANCE, attempt=ATTEMPT),
            _practice("PT000002", activity_state="available",
                      provenance=VALID_PROVENANCE),
        ], actions=[
            {"action": "open_revision", "submission_id": 28},
            {"action": "open_revision", "submission_id": 29},
            {"action": "open_practice", "practice_target_id": "PT000001"},
            {"action": "open_practice", "practice_target_id": "PT000002"},
        ])
        at = _run_harness(**_base_config(cycle))
        text = _markdown_text(at)
        assert t("student_journey_state_completed", "en") in text
        assert t("student_journey_state_available", "en") in text
        assert t("student_practice_completed_title", "en") in text
        labels = _button_labels(at)
        assert labels.get("journey_action_practice_PT000001") == t(
            "student_journey_action_open_practice", "en")
        assert labels.get("journey_action_practice_PT000002") == t(
            "student_journey_action_open_practice", "en")

    def test_evaluation_unavailable_stays_honest(self):
        cycle = _cycle(practices=[
            _practice("PT000001", activity_state="evaluation_unavailable",
                      evaluation_state="unavailable",
                      provenance=VALID_PROVENANCE, attempt=ATTEMPT)])
        at = _run_harness(**_base_config(cycle))
        text = _markdown_text(at)
        assert t("student_journey_state_evaluation_unavailable", "en") in text
        assert t("student_practice_evaluation_unavailable", "en") in text
        assert 'px-notice-dashed' in text
        assert t("student_practice_completed_title", "en") not in text

    def test_no_priority_and_insufficient_evidence_are_neutral_outcomes(self):
        no_priority = _cycle(
            root=_submission(28, writing_state="feedback_without_priority"),
            revisions=[], stages=[
                _stage(28, 1, priorities=[],
                       writing_state="feedback_without_priority")],
            practices=[], current_state="feedback_without_priority",
            actions=[{"action": "open_revision", "submission_id": 28}])
        insufficient = _cycle(
            cycle_id="cycle-30",
            root=_submission(30, writing_state="insufficient_evidence"),
            revisions=[], stages=[], practices=[],
            current_state="insufficient_evidence", actions=[])
        at = _run_harness(**_base_config(no_priority, insufficient))
        text = _markdown_text(at)
        assert t("student_journey_state_feedback_without_priority", "en") in text
        assert t("journey_event_feedback_without_priority_desc", "en") in text
        assert t("student_journey_state_insufficient_evidence", "en") in text
        assert t("journey_event_insufficient_evidence_desc", "en") in text

    def test_legacy_provenance_neutral_dashed(self):
        cycle = _cycle(practices=[
            _practice("PT000001", provenance={"status": "legacy",
                                              "reference": None})])
        at = _run_harness(**_base_config(cycle))
        text = _markdown_text(at)
        assert t("student_journey_practice_legacy", "en") in text
        assert "px-notice-dashed" in text

    def test_unlinked_cycle_warning(self):
        cycle = _cycle(relationship_status="unlinked",
                       limitations=["unlinked limitation text"])
        at = _run_harness(**_base_config(cycle))
        text = _markdown_text(at)
        assert t("student_journey_cycle_unlinked", "en") in text
        assert "unlinked limitation text" in text

    def test_action_hierarchy_one_primary_cta(self):
        at = _run_harness(**_base_config(_cycle()))
        labels = _button_labels(at)
        assert labels.get("journey_primary_action") == t(
            "student_home_go_writing", "en")
        assert "journey_action_revision_28" in labels
        assert "journey_action_practice_PT000001" in labels

    def test_loading_box_is_transient(self):
        """The unified loading box clears once content is rendered."""
        at = _run_harness(**_base_config(_cycle()))
        assert not any("px-loading" in m.value for m in at.markdown)
        assert t("student_journey_cycle_title", "en") in _markdown_text(at)

    def test_empty_state_and_api_error(self):
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


class TestJourneyContractsPreserved:
    def test_zero_writes_on_render(self):
        at = _run_harness(**_base_config(_cycle()))
        client = at.session_state["fake_client"]
        assert client.post_count == 0
        assert client.revision_post_count == 0
        assert client.target_create_count == 0
        assert client.attempt_post_count == 0
        assert client.complete_count == 0

    def test_chinese_renders_localized_without_raw_keys(self):
        at = _run_harness(**_base_config(_cycle(), lang="zh_CN"))
        text = _markdown_text(at)
        assert t("student_journey_cycle_title", "zh_CN") in text
        assert t("student_journey_original_writing", "zh_CN") in text
        assert t("student_journey_state_completed", "zh_CN") in text
        for raw in ("student_journey_", "student_practice_", "journey_"):
            assert raw not in text
        assert "Writing Cycle" not in text

    def test_no_page_specific_css(self):
        source = (ROOT / "app/ui/features/student/journey.py").read_text(
            encoding="utf-8")
        assert "<style>" not in source
        assert "st.markdown" in source  # HTML fragments only, no style blocks

    def test_no_new_locale_keys_needed(self):
        # The Journey page consumes only existing locale keys; parity is
        # preserved without a locale diff (600/600).
        import json as _json

        en = _json.loads((ROOT / "locales/en.json").read_text(encoding="utf-8"))
        zh = _json.loads((ROOT / "locales/zh_CN.json").read_text(encoding="utf-8"))
        assert set(en) == set(zh)
        assert len(en) == 600

    def test_state_label_keys_exist_in_both_locales(self):
        import json as _json

        en = _json.loads((ROOT / "locales/en.json").read_text(encoding="utf-8"))
        zh = _json.loads((ROOT / "locales/zh_CN.json").read_text(encoding="utf-8"))
        for state in ("completed", "available", "evaluation_unavailable",
                      "feedback_without_priority", "insufficient_evidence",
                      "revision_submitted", "attempted"):
            key = f"student_journey_state_{state}"
            assert en.get(key), key
            assert zh.get(key), key
