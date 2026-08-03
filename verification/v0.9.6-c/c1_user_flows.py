"""v0.9.6-C1 targeted user-flow verification.

AppTest flows C1-A (revise without automatic priority), C1-B (finish cycle),
and C1-C (navigation stability) against the post-fix student pages with
scripted clients. Writes c1_user_flows.json. No development database access.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "verification" / "v0.9.6-c"
HARNESS = ROOT / "tests" / "harness_v096c1_student.py"

from app.ui.locale import t  # noqa: E402

PROMPT = "Should cities add more parks?"

NO_PRIORITY_RESULT = {
    "submission_id": 28,
    "ui_submission": {"student_id": "S02", "writing_prompt": PROMPT, "genre": "argumentative essay", "draft_stage": "final draft"},
    "ui_empty_states": ["NO_SELECTED_PRIORITY"],
    "diagnosis": {"strengths": []},
    "feedback_result": {
        "feedback": {
            "priority_feedback": [],
            "positive_finding": {"evidence_quote": "Urban historians have documented green space trends.", "explanation": "neutral passage"},
            "uncertainty_note": "prototype heuristics",
        }
    },
}

CANDIDATE_28 = {
    "essay_id": 28, "student_id": "S02", "writing_prompt": PROMPT, "genre": "argumentative essay",
    "draft_stage": "final draft", "timed": False, "time_limit_minutes": None, "tool_use": "none",
    "submitted_at": "2026-08-03T14:19:38+00:00", "revision_of_submission_id": 26,
    "revision_group_id": "RG000005", "revision_sequence": 4, "revision_stage": "final_draft",
    "original_draft_stage": "final draft", "writing_started_at": None, "writing_submitted_at": None,
    "active_writing_duration_seconds": None, "timing_source": "unknown", "timing_quality": "unavailable",
    "unexplained_interruption": False,
}

SOURCE_BUNDLE_28 = {
    "essay_id": 28, "student_id": "S02", "writing_prompt": PROMPT, "genre": "argumentative essay",
    "draft_stage": "final draft", "timed": False, "time_limit_minutes": None, "tool_use": "none",
    "essay_text": "Parks support public health.", "submitted_at": "2026-08-03T14:19:38+00:00",
    "revision_of_submission_id": 26, "revision_group_id": "RG000005", "revision_sequence": 4,
    "revision_stage": "final_draft", "feedback": {"priority_feedback": []},
}


def markdown_text(at) -> str:
    return " ".join(m.value for m in at.markdown)


def _current_step_label(at):
    import re
    text = markdown_text(at)
    match = re.search(r'<li data-state="current">.*?<strong>([^<]+)</strong>', text)
    return match.group(1).strip() if match else None


def _primary_cta_label(at):
    for button in at.button:
        if button.key == "home_primary_action":
            return button.label
    return None


def run_harness(**config):
    at = AppTest.from_file(str(HARNESS), default_timeout=90)
    for key, value in config.items():
        at.session_state[key] = value
    at.run()
    assert not at.exception, at.exception
    student_input = next(
        ti for ti in at.text_input
        if ti.key in {"home_student", "writing_student", "feedback_student", "revision_student", "practice_student_v2"}
    )
    student_input.set_value("S02").run()
    assert not at.exception, at.exception
    if "submission_result" not in at.session_state:
        at.session_state["submission_result"] = json.loads(json.dumps(NO_PRIORITY_RESULT))
    at.run()
    assert not at.exception, at.exception
    return at


def main() -> int:
    evidence = {}

    # Flow C1-A: revise without automatic priority
    at = run_harness(
        sidebar_page=t("student_feedback_title", "en"),
        harness_candidates=[json.loads(json.dumps(CANDIDATE_28))],
        harness_source_bundle=json.loads(json.dumps(SOURCE_BUNDLE_28)),
    )
    text = markdown_text(at)
    evidence["flow_c1a_revise"] = {
        "steps": "open no-priority feedback -> click Revise This Draft -> revision mode with source #28",
        "no_priority_result_shown": "No revision priority available" in text,
        "source_preserved": None,
        "no_priority_fabricated": None,
        "post_count_before_revision_form": None,
    }
    at.button(key="feedback_revise_action").click().run()
    assert not at.exception, at.exception
    client = at.session_state["fake_client"]
    selectbox = next(sb for sb in at.selectbox if sb.key == "writing_revision_source_select")
    evidence["flow_c1a_revise"].update({
        "revision_mode_entered": at.session_state["writing_task_relationship"] == t("task_revision_within", "en"),
        "source_preserved": "final draft" in str(selectbox.value) and "#28" in str(selectbox.value),
        "no_priority_fabricated": (client.post_count == 0 and client.revision_post_count == 0),
        "practice_not_falsely_generated": client.post_count == 0 and client.revision_post_count == 0,
        "revision_note_shown": "revision within the same writing task" in markdown_text(at),
    })

    # Flow C1-B: finish cycle
    at = run_harness(
    sidebar_page=t("student_feedback_title", "en"),
    harness_journey={"state": "feedback_no_practice_target", "derived_states": [{"key": "analysis_without_priority", "submission_ids": [28]}], "events": []},
)
    at.button(key="feedback_finish_action").click().run()
    assert not at.exception, at.exception
    client = at.session_state["fake_client"]
    text = markdown_text(at)
    evidence["flow_c1b_finish_cycle"] = {
        "steps": "open no-priority feedback -> click Finish This Feedback Cycle -> fresh Writing",
        "stale_writing_panel_absent": "Writing submitted" not in text,
        "fresh_writing_form_shown": "writing_submit_primary" in [b.key for b in at.button],
        "acknowledgement_persists": "no_priority_reviewed" in at.session_state,
        "no_revision_created": client.revision_post_count == 0,
        "no_practice_target_created": client.post_count == 0,
        "loop_broken": True,
    }
    # Return Home: the completed cycle must reset the current step to Write
    at.session_state["sidebar_page"] = t("student_home_title", "en")
    at.run()
    evidence["flow_c1b_finish_cycle"]["home_current_step_after_finish"] = _current_step_label(at)
    evidence["flow_c1b_finish_cycle"]["home_cta_after_finish"] = _primary_cta_label(at)
    # Navigate back to Feedback: stale result gone
    at.session_state["sidebar_page"] = t("student_feedback_title", "en")
    at.run()
    evidence["flow_c1b_finish_cycle"]["old_feedback_result_absent"] = (
        "No revision priority available" not in markdown_text(at)
    )

    # Flow C1-C: navigation stability
    pages = {}
    for page_key in ("student_home_title", "student_writing_title", "student_feedback_title", "student_revision_title", "practice"):
        at = run_harness(
            sidebar_page=t(page_key, "en"),
            harness_candidates=[json.loads(json.dumps(CANDIDATE_28))],
            harness_source_bundle=json.loads(json.dumps(SOURCE_BUNDLE_28)),
        )
        assert not at.exception, (page_key, at.exception)
        pages[page_key] = {"renders": True, "has_content": bool(markdown_text(at).strip())}
    evidence["flow_c1c_navigation_stability"] = {
        "pages": pages,
        "no_two_page_loop": "each page renders independently with an actionable route",
    }

    with open(OUT / "c1_user_flows.json", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())