"""Focused v0.9.4-B Student presentation contracts."""

from __future__ import annotations

import streamlit as st
import pytest

from app.ui import components as c
from app.ui.pixel_art import DESIGN_TOKENS, PIXEL_COMPONENT_CSS
from app.ui.locale import t


@pytest.fixture
def captured_markdown(monkeypatch):
    captured: list[str] = []

    def fake_markdown(body: str, unsafe_allow_html: bool = False) -> None:
        captured.append(body)

    monkeypatch.setattr(st, "markdown", fake_markdown)
    monkeypatch.setattr(c, "page_header", lambda *args, **kwargs: None)
    return captured


def test_student_page_intro_marks_role_and_purpose(captured_markdown):
    c.student_page_intro("student_home_title", "student_home_subtitle", "en")
    html = captured_markdown[-1]
    assert 'data-testid="px-student-page"' in html
    assert 'data-role="student"' in html
    assert t("student_home_subtitle", "en") in html


def test_student_steps_expose_text_state(captured_markdown):
    c.student_task_steps(["student_home_title", "student_writing_title"], 1, "en")
    html = captured_markdown[-1]
    assert 'data-testid="px-student-steps"' in html
    assert 'data-state="complete"' in html
    assert 'data-state="current"' in html
    assert "Complete" in html
    assert "Current step" in html


def test_student_action_block_has_stable_state(captured_markdown):
    c.student_action_block("student_home_next_action", "student_home_action_submit", "en")
    html = captured_markdown[-1]
    assert 'data-testid="px-student-primary-action"' in html
    assert 'data-state="ready"' in html


def test_student_context_escapes_record_values(captured_markdown):
    c.student_context_block([("student_context_learner", "<script>bad()</script>")], "en")
    html = captured_markdown[-1]
    assert 'data-testid="px-student-context"' in html
    assert "&lt;script&gt;" in html
    assert "<script>" not in html


def test_student_css_uses_existing_aliases_and_mobile_stack():
    assert "--px-content-width-student" in PIXEL_COMPONENT_CSS
    assert "--px-density-student-section" in PIXEL_COMPONENT_CSS
    assert '[data-testid="px-student-page"]' in PIXEL_COMPONENT_CSS
    assert "grid-template-columns: 1fr" in PIXEL_COMPONENT_CSS


def test_focus_token_meets_three_to_one_on_adjacent_surfaces():
    def luminance(hex_color: str) -> float:
        values = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [
            value / 12.92 if value <= 0.04045
            else ((value + 0.055) / 1.055) ** 2.4
            for value in values
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    def contrast(a: str, b: str) -> float:
        high, low = sorted((luminance(a), luminance(b)), reverse=True)
        return (high + 0.05) / (low + 0.05)

    colors = DESIGN_TOKENS["colors"]
    assert colors["focus"] == "#0f6dbd"
    assert contrast(colors["focus"], colors["bg"]) >= 3
    assert contrast(colors["focus"], colors["surface"]) >= 3
    assert contrast(colors["focus"], colors["text"]) >= 3


@pytest.mark.parametrize(
    "state,expected",
    [
        ("no_submissions", (0, "student_home_action_submit", "student_writing_title", "student_home_go_writing")),
        ("analysis_without_priority", (0, "student_home_action_submit", "student_writing_title", "student_home_go_writing")),
        ("target_no_attempt", (2, "student_home_action_practice", "practice", "student_home_go_practice")),
        ("revision_no_response", (2, "student_home_action_revise", "student_revision_title", "student_home_go_revision")),
    ],
)
def test_home_action_contract(state, expected):
    from app.ui.features.student.home import _home_action_contract

    assert _home_action_contract(state) == expected


def test_writing_lock_is_scoped_to_the_submitting_learner():
    from app.ui.features.student.session import _writing_saved_for_learner

    saved = {"submission_id": 12, "ui_submission": {"student_id": "S02"}}
    assert _writing_saved_for_learner(saved, " S02 ")
    assert not _writing_saved_for_learner(saved, "OTHER")
    assert not _writing_saved_for_learner(None, "S02")


def test_writing_page_no_longer_embeds_feedback_renderer():
    import inspect
    from app.ui.pages.student_pages import render_writing_page

    assert "render_feedback_content" not in inspect.getsource(render_writing_page)


def test_feedback_priority_card_omits_empty_quote(captured_markdown):
    c.feedback_priority_card("Focus", "", "Why", "Revise", lang="en")
    html = captured_markdown[-1]
    assert 'data-testid="px-feedback-priority"' in html
    assert 'class="px-quote"' not in html


def test_feedback_category_uses_approved_localized_label():
    from app.ui.features.student.formatting import _feedback_category_label

    assert _feedback_category_label("lexical_repetition", "en") == "Reduce lexical repetition"
    assert _feedback_category_label("lexical_repetition", "zh_CN") == "减少词汇重复"
    assert _feedback_category_label("unmapped_signal", "en") == "Unmapped Signal"


def test_feedback_content_orders_priority_before_action_and_evidence():
    import inspect
    from app.ui.pages.student_pages import render_feedback_content

    source = inspect.getsource(render_feedback_content)
    priority = source.index('section_header("student_feedback_priorities"')
    action = source.index('section_header("student_feedback_next"')
    evidence = source.index('section_header("student_feedback_evidence"')
    strengths = source.index('"student_feedback_strengths" if strengths else "student_feedback_neutral_passage"')
    assert priority < action < evidence < strengths
    assert "provider_name" not in source
    assert "provider_label" not in source


def test_shared_student_id_input_prefills_selected_learner(monkeypatch):
    from app.ui import student_context

    state: dict[str, str] = {}
    monkeypatch.setattr(st, "session_state", state)
    monkeypatch.setattr(student_context, "selected_learner", lambda: "S02")
    monkeypatch.setattr(student_context, "set_selected_learner", lambda value: value.strip())
    monkeypatch.setattr(st, "text_input", lambda _label, *, key, placeholder=None: state[key])

    assert student_context.student_id_input("student_id", "feedback_student", "en") == "S02"
    assert state["feedback_student"] == "S02"


def test_student_section_headers_pass_locale_by_keyword():
    import inspect
    import re
    from app.ui.pages import student_pages

    source = inspect.getsource(student_pages)
    assert not re.search(r'section_header\("[^"]+", lang\)', source)


def test_practice_uses_authoritative_localized_instruction():
    from app.ui.features.student.practice import _practice_instruction

    exercise = {
        "exercise_type": "guided_sentence_rewrite",
        "instructions": "Stored English instruction",
    }
    assert _practice_instruction(exercise, "en") == "Rewrite the following sentence to address the selected priority."
    assert _practice_instruction(exercise, "zh_CN") == "请重写以下句子以解决选定的优先级问题。"


def test_practice_localizes_frozen_constraints_and_statuses():
    from app.ui.features.student.practice import _practice_constraint_label, _practice_status_label

    assert _practice_constraint_label("Retain original meaning.", "zh_CN") == "保留原意。"
    assert _practice_status_label("completion", "completed", "en") == "Response completed"
    assert _practice_status_label("action", "candidate_detected", "zh_CN") == "已观察到目标回应候选"


def test_practice_page_auto_reads_and_has_no_manual_load_action():
    import inspect
    from app.ui.pages.student_pages import render_practice_page

    source = inspect.getsource(render_practice_page)
    assert "get_practice_targets" in source
    assert "get_exercise_instances" in source
    assert 't("load_practice"' not in source
    assert 'selected.get("target_code"' not in source
    assert "student_task_steps" in source


def test_revision_lock_is_learner_and_source_scoped():
    from app.ui.features.student.revision import _revision_saved_for_source

    saved = {
        "submission_id": 22,
        "ui_submission": {"student_id": "S02", "revision_of_submission_id": 21},
    }
    assert _revision_saved_for_source(saved, "S02")
    assert _revision_saved_for_source(saved, " S02 ", 21)
    assert not _revision_saved_for_source(saved, "S02", 20)
    assert not _revision_saved_for_source(saved, "OTHER", 21)


def test_revision_observation_uses_localized_conservative_text():
    from app.ui.features.student.revision import _revision_observation_text, _revision_status_label

    observed = "The prior signal is not currently observed in the linked draft."
    assert _revision_observation_text(observed, "zh_CN") == "当前关联草稿中未观察到先前信号。"
    assert _revision_status_label("confidence", "low", "en") == "Low attribution confidence"


def test_revision_page_uses_existing_read_and_submit_contracts():
    import inspect
    from app.ui.pages.student_pages import render_revision_page

    source = inspect.getsource(render_revision_page)
    assert "get_student_revision_candidates" in source
    assert "get_submission" in source
    assert "get_practice_targets" in source
    assert '"revision_of_submission_id": source_id' in source
    assert "create_revision(" not in source
    assert "save_within_task_response" not in source


def test_timeline_event_separates_time_evidence_source_and_limit(captured_markdown):
    c.timeline_event(
        "Draft recorded", "2026-08-01 12:00", detail="A draft was recorded.",
        boundary="Not a learning claim.", source_label="Essay #1",
        evidence_status="Confirmed system record", lang="en",
    )
    html = captured_markdown[-1]
    for testid in (
        "px-timeline-event", "px-journey-time", "px-journey-detail",
        "px-journey-evidence", "px-journey-source", "px-journey-limitation",
    ):
        assert f'data-testid="{testid}"' in html


def test_journey_mappings_localize_evidence_source_and_target():
    from app.ui.features.student.journey import (
        _journey_description_params, _journey_evidence_label, _journey_source_label,
    )

    event = {"source_record_type": "feedback_record", "source_record_id": "4"}
    assert _journey_source_label(event, "zh_CN") == "反馈 #4"
    assert _journey_evidence_label("derived_state", "en") == "Derived read-time state"
    params = _journey_description_params(
        {"description_params": {"target": "lexical_repetition_local"}}, "zh_CN"
    )
    assert params["target"] == "减少词汇重复"


def test_journey_page_auto_reads_without_manual_load():
    import inspect
    from app.ui.pages.student_pages import render_learning_journey_page

    source = inspect.getsource(render_learning_journey_page)
    assert "get_journey" in source
    assert 't("load_journey"' not in source
    assert "source_label=_journey_source_label" in source


def test_journey_action_contract_is_state_specific():
    from app.ui.features.student.journey import _journey_action_contract

    assert _journey_action_contract("target_no_attempt")[1:] == (
        "practice", "student_home_go_practice"
    )
    assert _journey_action_contract("analysis_without_priority")[1:] == (
        "student_writing_title", "student_home_go_writing"
    )
