"""View-mapping tests: student-safe views and the no-technical-internals rule.

Student surfaces must never expose raw technical internals by default:
reference-group N, distribution internals, hashes, artifact paths,
epistemic-status codes, provenance JSON, or internal feature ids. Views are
built by allowlist: forbidden keys may never appear anywhere in a view, and
forbidden string values (hash values, internal ids) are never passed through.
"""

from __future__ import annotations

import pytest

from app.ui.wave2.mock import MockWave2Backend
from app.ui.wave2.views import (
    FORBIDDEN_VIEW_KEYS,
    build_feedback_view,
    build_history_view,
    build_learning_items_view,
    build_legacy_feedback_view,
    build_longitudinal_view,
    build_observation_view,
    build_task_view,
    build_version_view,
)


ESSAY = (
    "Cities should add more parks because parks give residents space to exercise. "
    "Parks also support community events and provide shade during hot weather. "
    "However, new parks require land and regular maintenance. Therefore, city leaders "
    "should first identify neighborhoods with limited green space and consult residents."
)


def _assert_no_forbidden_keys(payload) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            assert key not in FORBIDDEN_VIEW_KEYS, f"forbidden key {key!r} leaked into view"
            _assert_no_forbidden_keys(value)
    elif isinstance(payload, list):
        for item in payload:
            _assert_no_forbidden_keys(item)


def _assert_no_internal_values(payload, values) -> None:
    """Assert raw internal values (hashes/ids/paths) never reach a view."""
    if isinstance(payload, dict):
        for value in payload.values():
            _assert_no_internal_values(value, values)
    elif isinstance(payload, list):
        for item in payload:
            _assert_no_internal_values(item, values)
    elif isinstance(payload, str):
        for forbidden in values:
            assert forbidden not in payload, f"internal value {forbidden!r} leaked into view"


def make_task(backend, student_id="L-STU-001") -> dict:
    return backend.create_task(
        student_id=student_id, task_type="opinion", writing_context="cet4",
        writing_prompt="Should cities add more parks?",
    )


def test_task_view_is_allowlisted():
    backend = MockWave2Backend()
    task = make_task(backend)
    view = build_task_view(task)
    assert set(view) == {"task_id", "task_type", "writing_context", "writing_prompt", "created_at", "metadata"}
    _assert_no_forbidden_keys(view)


def test_version_view_strips_hashes_and_run_ids():
    backend = MockWave2Backend()
    task = make_task(backend)
    version = backend.submit_v1(task["task_id"], ESSAY)
    view = build_version_view(version)
    assert set(view) == {
        "version_number", "submission_id", "draft_stage", "submitted_at",
        "revision_of_submission_id", "ancestry",
    }
    _assert_no_forbidden_keys(view)
    _assert_no_internal_values(view, [version["essay_text_hash"], version["analysis_run_id"]])


def test_feedback_view_is_student_safe():
    backend = MockWave2Backend()
    task = make_task(backend)
    version = backend.submit_v1(task["task_id"], ESSAY)
    plan = backend.priority_plan("L-STU-001", task["task_id"], version["submission_id"])
    view = build_feedback_view(plan)
    assert set(view) == {
        "history_state", "items", "local_statements", "global_statements",
        "historical_summary", "insufficiency_notice",
    }
    item = view["items"][0]
    assert set(item) == {
        "category", "recurrence_status", "action_statement", "context_text",
        "try_text", "evidence_quote",
    }
    _assert_no_forbidden_keys(view)
    all_values = [version["essay_text_hash"], version["analysis_run_id"]]
    _assert_no_internal_values(view, all_values)
    # recurrence status stays machine-readable for locale mapping
    assert item["recurrence_status"] in {
        "recurring", "stable", "reappeared", "first_observed", "insufficient_history",
    }


def test_feedback_view_insufficient_notice_for_new_learner():
    backend = MockWave2Backend(scenario="new_learner")
    task = make_task(backend, student_id="L-NEW-001")
    version = backend.submit_v1(task["task_id"], ESSAY)
    plan = backend.priority_plan("L-NEW-001", task["task_id"], version["submission_id"])
    view = build_feedback_view(plan)
    assert view["history_state"] == "insufficient_history"
    assert view["insufficiency_notice"]
    assert view["historical_summary"] == []


def test_feedback_view_historical_summary_for_returning_learner():
    backend = MockWave2Backend(scenario="returning_learner")
    task = make_task(backend, student_id="L-RET-001")
    version = backend.submit_v1(task["task_id"], ESSAY)
    plan = backend.priority_plan("L-RET-001", task["task_id"], version["submission_id"])
    view = build_feedback_view(plan)
    assert view["history_state"] == "sufficient"
    assert view["historical_summary"]
    assert set(view["historical_summary"][0]) == {"category", "recurrence_status"}


def test_observation_view_is_student_safe():
    backend = MockWave2Backend()
    task = make_task(backend)
    v1 = backend.submit_v1(task["task_id"], ESSAY)
    v2 = backend.revise(task["task_id"], v1["submission_id"], ESSAY.replace("parks", "green spaces"))
    observation = backend.revision_observation(task["task_id"], v2["submission_id"])
    view = build_observation_view(observation)
    assert set(view) == {
        "what_changed_summary", "addressed", "remaining", "new_observations",
        "no_intent_inference",
    }
    _assert_no_forbidden_keys(view)
    _assert_no_internal_values(view, [observation["observation_id"]])


def test_learning_items_view_is_student_safe():
    backend = MockWave2Backend()
    task = make_task(backend)
    version = backend.submit_v1(task["task_id"], ESSAY)
    plan = backend.priority_plan("L-STU-001", task["task_id"], version["submission_id"])
    backend.create_learning_item("L-STU-001", plan["items"][0]["plan_item_id"])
    items = backend.list_learning_items("L-STU-001")
    view = build_learning_items_view(items)
    assert set(view) == {"items"}
    assert set(view["items"][0]) == {"category", "status", "created_at"}
    _assert_no_forbidden_keys(view)


def test_longitudinal_view_is_student_safe():
    backend = MockWave2Backend(scenario="returning_learner")
    longitudinal = {
        "observations": backend.list_observations("L-RET-001"),
        "difficulties": backend.difficulties("L-RET-001"),
        "strengths": backend.strengths("L-RET-001"),
        "stable": backend.stable("L-RET-001"),
        "proficiency": backend.proficiency_context("L-RET-001"),
    }
    view = build_longitudinal_view(longitudinal)
    assert set(view) == {
        "history_state", "difficulties", "strengths", "stable",
        "proficiency_anchors", "statement",
    }
    assert view["difficulties"]
    assert set(view["difficulties"][0]) == {"label", "state"}
    assert view["strengths"]
    assert view["stable"]
    assert view["proficiency_anchors"]
    assert set(view["proficiency_anchors"][0]) == {"system", "declared_value"}
    _assert_no_forbidden_keys(view)


def test_history_view_assembles_all_surfaces():
    backend = MockWave2Backend(scenario="returning_learner")
    task = make_task(backend, student_id="L-RET-001")
    version = backend.submit_v1(task["task_id"], ESSAY)
    plan = backend.priority_plan("L-RET-001", task["task_id"], version["submission_id"])
    backend.create_learning_item("L-RET-001", plan["items"][0]["plan_item_id"])
    history = {
        "learner_id": "L-RET-001",
        "tasks": [{
            "task": task,
            "versions": backend.version_history(task["task_id"])["versions"],
            "plan": plan,
        }],
        "learning_items": backend.list_learning_items("L-RET-001")["items"],
        "longitudinal": {
            "observations": backend.list_observations("L-RET-001"),
            "difficulties": backend.difficulties("L-RET-001"),
            "strengths": backend.strengths("L-RET-001"),
            "stable": backend.stable("L-RET-001"),
            "proficiency": backend.proficiency_context("L-RET-001"),
        },
    }
    view = build_history_view(history)
    assert set(view) == {
        "learner_id", "history_state", "tasks", "learning_items", "longitudinal",
    }
    task_view = view["tasks"][0]
    assert set(task_view) == {
        "task", "versions", "feedback_summary",
    }
    assert task_view["versions"][0]["version_number"] == 1
    assert task_view["feedback_summary"]
    assert "proposed" in {item["status"] for item in view["learning_items"]}
    _assert_no_forbidden_keys(view)


def test_legacy_feedback_view_maps_existing_priorities():
    legacy_result = {
        "submission_id": 100,
        "student_id": "S1",
        "feedback_result": {
            "feedback": {
                "priority_feedback": [
                    {
                        "category": "lexical_repetition",
                        "evidence_quote": "Parks support public health.",
                        "explanation": "The word 'parks' is repeated closely in the draft.",
                        "revision_guidance": "Replace one repetition with a synonym.",
                    }
                ],
                "positive_finding": {"explanation": "The draft answers the prompt."},
                "uncertainty_note": "Prototype feedback.",
            }
        },
        "history": {"comparability_status": "insufficient_history"},
    }
    view = build_legacy_feedback_view(legacy_result)
    assert set(view) == {
        "history_state", "items", "local_statements", "global_statements",
        "historical_summary", "insufficiency_notice",
    }
    item = view["items"][0]
    assert item["category"] == "lexical_repetition"
    assert item["action_statement"] == "The word 'parks' is repeated closely in the draft."
    assert item["try_text"] == "Replace one repetition with a synonym."
    assert item["evidence_quote"] == "Parks support public health."
    assert item["recurrence_status"] == "insufficient_history"
    _assert_no_forbidden_keys(view)


def test_views_tolerate_missing_optional_fields():
    assert build_task_view({})["writing_prompt"] == ""
    assert build_feedback_view({"items": []})["items"] == []
    assert build_observation_view({})["addressed"] == []
    assert build_longitudinal_view({})["difficulties"] == []
    assert build_learning_items_view({})["items"] == []