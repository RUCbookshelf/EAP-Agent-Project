"""Student-safe view mapping for Wave-2 payloads.

Views are built by allowlist: only display-safe, learner-facing fields pass
through, and the raw technical internals listed in ``STUDENT_INTERNAL_KEYS``
(hashes, artifact paths, evidence refs, internal feature/record ids,
epistemic-status codes, provenance JSON, reference-group/distribution
internals) are dropped before anything reaches a student surface. Stable
references needed to operate the journey (task_id, submission_id,
learner_id, timestamps) are carried in views but are never rendered by the
student renderers.
"""

from __future__ import annotations

from typing import Any

from app.ui.wave2.contracts import STUDENT_INTERNAL_KEYS

# The no-internals guard set exported for tests: every key in this set must
# never appear anywhere inside a student view.
FORBIDDEN_VIEW_KEYS = set(STUDENT_INTERNAL_KEYS)

_RECURRENCE_STATES = {
    "recurring", "stable", "reappeared", "first_observed", "insufficient_history",
}


def _safe_str(value: Any, default: str = "") -> str:
    return str(value) if value is not None else default


def build_task_view(task: dict[str, Any] | None) -> dict[str, Any]:
    task = task or {}
    metadata = task.get("metadata") or {}
    raw_task_id = task.get("task_id")
    return {
        "task_id": raw_task_id if raw_task_id else None,
        "task_type": _safe_str(task.get("task_type")),
        "writing_context": _safe_str(task.get("writing_context")),
        "writing_prompt": _safe_str(task.get("writing_prompt")),
        "created_at": _safe_str(task.get("created_at")),
        "metadata": {
            "audience": metadata.get("audience"),
            "purpose": metadata.get("purpose"),
            "word_constraint": metadata.get("word_constraint"),
        },
    }


def build_version_view(version: dict[str, Any] | None) -> dict[str, Any]:
    version = version or {}
    return {
        "version_number": int(version["version_number"]) if version.get("version_number") else 1,
        "submission_id": int(version["submission_id"]) if version.get("submission_id") is not None else 0,
        "draft_stage": _safe_str(version.get("draft_stage"), "first draft"),
        "submitted_at": _safe_str(version.get("submitted_at")),
        "revision_of_submission_id": (
            int(version["revision_of_submission_id"])
            if version.get("revision_of_submission_id") is not None else None
        ),
        "ancestry": list(version.get("ancestry") or []),
    }


def _plan_item_view(item: dict[str, Any] | None) -> dict[str, Any]:
    item = item or {}
    context = item.get("context") or {}
    recurrence = item.get("recurrence_status")
    if recurrence not in _RECURRENCE_STATES:
        recurrence = "insufficient_history"
    return {
        "category": _safe_str(item.get("category")),
        "recurrence_status": recurrence,
        "action_statement": _safe_str(item.get("action_statement")),
        "context_text": _safe_str(context.get("explanation") or context.get("quote")),
        "try_text": _safe_str(item.get("action_statement")),
        "evidence_quote": _safe_str(context.get("quote")),
    }


def build_feedback_view(plan: dict[str, Any] | None) -> dict[str, Any]:
    """Map a PriorityRevisionPlan (or legacy-shaped feedback) to a student view."""
    plan = plan or {}
    history_state = plan.get("history_state")
    if history_state not in {"sufficient", "insufficient_history"}:
        history_state = "insufficient_history"
    items = [_plan_item_view(item) for item in (plan.get("items") or [])]
    historical = plan.get("historical_feedback") or []
    return {
        "history_state": history_state,
        "items": items,
        "local_statements": [
            _safe_str(item.get("statement"))
            for item in (plan.get("local_observations") or [])
            if item.get("statement")
        ],
        "global_statements": [
            _safe_str(item.get("descriptive_statement"))
            for item in (plan.get("global_observations") or [])
            if item.get("descriptive_statement")
        ],
        "historical_summary": [
            {
                "category": _safe_str(item.get("category")),
                "recurrence_status": item.get("status")
                if item.get("status") in _RECURRENCE_STATES else "insufficient_history",
            }
            for item in historical
            if item.get("category")
        ],
        "insufficiency_notice": (
            "Not enough of your earlier writing is stored yet to compare "
            "patterns, so this feedback is based only on the current draft."
            if history_state == "insufficient_history" else ""
        ),
    }


def build_observation_view(observation: dict[str, Any] | None) -> dict[str, Any]:
    observation = observation or {}
    what_changed = observation.get("what_changed") or {}
    addressed: list[dict[str, str]] = []
    remaining: list[dict[str, str]] = []
    for area in observation.get("feedback_areas") or []:
        entry = {
            "category": _safe_str(area.get("category")),
            "status": _safe_str(area.get("status")),
        }
        if area.get("status") == "addressed":
            addressed.append(entry)
        elif area.get("status") == "remaining":
            remaining.append(entry)
    return {
        "what_changed_summary": _safe_str(what_changed.get("summary")),
        "addressed": addressed,
        "remaining": remaining,
        "new_observations": [
            {
                "category": _safe_str(item.get("category")),
                "status": _safe_str(item.get("status")),
            }
            for item in (observation.get("new_observations") or [])
        ],
        "no_intent_inference": _safe_str(observation.get("no_intent_inference")),
    }


def build_learning_items_view(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    return {
        "items": [
            {
                "category": _safe_str(item.get("category")),
                "status": _safe_str(item.get("status"), "proposed"),
                "created_at": _safe_str(item.get("created_at")),
            }
            for item in (payload.get("items") or [])
        ],
    }


def build_longitudinal_view(bundle: dict[str, Any] | None) -> dict[str, Any]:
    bundle = bundle or {}
    difficulties = (bundle.get("difficulties") or {}).get("items") or []
    strengths = (bundle.get("strengths") or {}).get("items") or []
    stable = (bundle.get("stable") or {}).get("items") or []
    proficiency = (bundle.get("proficiency") or {}).get("anchors") or []
    history_state = (bundle.get("observations") or {}).get("history_state")
    if history_state not in {"sufficient", "insufficient_history"}:
        history_state = "insufficient_history"
    return {
        "history_state": history_state,
        "difficulties": [
            {"label": _safe_str(item.get("label"), _safe_str(item.get("category"))),
             "state": "seen_before" if item.get("appeared_before") else "first_time"}
            for item in difficulties
        ],
        "strengths": [
            {"label": _safe_str(item.get("label"), _safe_str(item.get("category"))),
             "state": "observed"}
            for item in strengths
        ],
        "stable": [
            {"label": _safe_str(item.get("label"), _safe_str(item.get("category"))),
             "state": _safe_str(item.get("stability_kind"))}
            for item in stable
        ],
        "proficiency_anchors": [
            {
                "system": _safe_str(item.get("system")),
                "declared_value": _safe_str(item.get("declared_value")),
            }
            for item in proficiency
        ],
        "statement": _safe_str((bundle.get("proficiency") or {}).get("statement")),
    }


def build_history_view(history: dict[str, Any] | None) -> dict[str, Any]:
    """Assemble the student history view from tasks/versions/plans/items.

    Input bundle keys (built by the gateway): learner_id, tasks (list of
    {task, versions, plan}), learning_items (raw list), longitudinal
    (the build_longitudinal_view bundle).
    """
    history = history or {}
    tasks = []
    for entry in history.get("tasks") or []:
        task_view = build_task_view(entry.get("task"))
        versions = [build_version_view(v) for v in (entry.get("versions") or [])]
        plan = entry.get("plan") or {}
        feedback_summary = [
            {
                "category": _safe_str(item.get("category")),
                "recurrence_status": item.get("recurrence_status")
                if item.get("recurrence_status") in _RECURRENCE_STATES
                else "insufficient_history",
            }
            for item in (plan.get("items") or [])
        ]
        tasks.append({
            "task": task_view,
            "versions": versions,
            "feedback_summary": feedback_summary,
        })
    longitudinal = build_longitudinal_view(history.get("longitudinal") or {})
    history_state = "sufficient" if (tasks or (history.get("learning_items") or [])) else "insufficient_history"
    return {
        "learner_id": _safe_str(history.get("learner_id")),
        "history_state": history_state,
        "tasks": tasks,
        "learning_items": build_learning_items_view(
            {"items": history.get("learning_items") or []}
        )["items"],
        "longitudinal": longitudinal,
    }


def build_legacy_feedback_view(result: dict[str, Any] | None) -> dict[str, Any]:
    """Map the existing /api/v1/submissions feedback payload to the same
    student view shape used by the guided flow (degraded mode)."""
    result = result or {}
    provider = result.get("feedback_result") or {}
    feedback = provider.get("feedback") or {}
    priorities = feedback.get("priority_feedback") or []
    history = result.get("history") or {}
    comparability = history.get("comparability_status")
    history_state = "sufficient" if comparability == "sufficient_history" else "insufficient_history"
    items = []
    for priority in priorities:
        items.append({
            "category": _safe_str(priority.get("category")),
            "recurrence_status": "insufficient_history",
            "action_statement": _safe_str(priority.get("explanation")),
            "context_text": _safe_str(priority.get("explanation")),
            "try_text": _safe_str(priority.get("revision_guidance")),
            "evidence_quote": _safe_str(priority.get("evidence_quote")),
        })
    positive = feedback.get("positive_finding") or {}
    statements = []
    if positive.get("explanation"):
        statements.append(_safe_str(positive.get("explanation")))
    return {
        "history_state": history_state,
        "items": items,
        "local_statements": statements,
        "global_statements": [],
        "historical_summary": [],
        "insufficiency_notice": (
            "Not enough of your earlier writing is stored yet to compare "
            "patterns, so this feedback is based only on the current draft."
            if history_state == "insufficient_history" else ""
        ),
    }


def build_legacy_version_view(result: dict[str, Any] | None) -> dict[str, Any]:
    result = result or {}
    revision_of = result.get("revision_of_submission_id")
    return {
        "version_number": 2 if revision_of is not None else 1,
        "submission_id": int(result["submission_id"]) if result.get("submission_id") is not None else 0,
        "draft_stage": _safe_str(result.get("draft_stage"), "first draft"),
        "submitted_at": _safe_str(result.get("submitted_at")),
        "revision_of_submission_id": (
            int(revision_of) if revision_of is not None else None
        ),
        "ancestry": [],
    }


__all__ = [
    "FORBIDDEN_VIEW_KEYS",
    "build_feedback_view",
    "build_history_view",
    "build_learning_items_view",
    "build_legacy_feedback_view",
    "build_legacy_version_view",
    "build_longitudinal_view",
    "build_observation_view",
    "build_task_view",
    "build_version_view",
]