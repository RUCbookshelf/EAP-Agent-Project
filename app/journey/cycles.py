"""Student Journey cycle view model (v0.9.7-C WU1).

A learner-owned, read-time grouping of the existing raw Journey events
into coherent writing cycles and Practice activities. The cycle view is
derived from the same persisted records as the raw projection and never
writes: no cycle rows, no updates, no targets/exercises/attempts/
evaluations, and no raw events are created or changed.

Cycle rules (frozen for v0.9.7-C):

- The writing-cycle anchor is the original (root) submission resolved
  through persisted revision linkage (``revision_of_submission_id``);
  a revision whose chain cannot be resolved forms a controlled unlinked
  group and never cross-associates.
- Feedback attaches to the submission it was generated for (persisted
  ``feedback_records.essay_id``).
- Practice targets attach to the cycle whose submissions include the
  target's persisted ``source_submission_id``; the stable priority
  provenance (``PRIO-{feedback_id}-{priority_index}``) is validated
  against the cycle's persisted feedback before it is shown; legacy and
  unresolved references never gain fabricated provenance.
- Attempts attach to their target through the persisted
  exercise -> target relationship; evaluations attach to their attempt.
- Student-facing states describe persisted activity only: no mastery,
  proficiency, CEFR, learning-gain, pass/fail, or causal claims.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.practice.mapping import (
    PriorityMappingError,
    parse_stable_priority_reference,
)

CYCLE_MODEL_VERSION = "journey-cycle-v0.9.7-c"

# Writing states (student-facing, persisted-activity only).
WRITING_SUBMITTED = "submitted"
WRITING_ANALYZED = "analyzed"
WRITING_FEEDBACK_AVAILABLE = "feedback_available"
WRITING_FEEDBACK_WITHOUT_PRIORITY = "feedback_without_priority"
WRITING_INSUFFICIENT_EVIDENCE = "insufficient_evidence"
WRITING_REVISION_SUBMITTED = "revision_submitted"

# Practice activity states (student-facing).
PRACTICE_AVAILABLE = "available"
PRACTICE_ATTEMPTED = "attempted"
PRACTICE_EVALUATION_AVAILABLE = "evaluation_available"
PRACTICE_EVALUATION_UNAVAILABLE = "evaluation_unavailable"
PRACTICE_COMPLETED = "completed"
PRACTICE_UNAVAILABLE = "unavailable"

# Practice evaluation states.
EVALUATION_NOT_APPLICABLE = "not_applicable"
EVALUATION_AVAILABLE = "available"
EVALUATION_UNAVAILABLE = "unavailable"

# Cycle relationship and provenance statuses.
RELATIONSHIP_LINKED = "linked"
RELATIONSHIP_UNLINKED = "unlinked"
PROVENANCE_VALID = "valid"
PROVENANCE_LEGACY = "legacy"
PROVENANCE_UNRESOLVED = "unresolved"

# Stable cycle-state order for the cycle current_state derivation.
_CYCLE_STATE_ORDER: dict[str, int] = {
    PRACTICE_UNAVAILABLE: 5,
    WRITING_SUBMITTED: 10,
    WRITING_INSUFFICIENT_EVIDENCE: 20,
    WRITING_ANALYZED: 30,
    WRITING_FEEDBACK_WITHOUT_PRIORITY: 40,
    WRITING_FEEDBACK_AVAILABLE: 50,
    WRITING_REVISION_SUBMITTED: 60,
    PRACTICE_AVAILABLE: 70,
    PRACTICE_ATTEMPTED: 75,
    PRACTICE_EVALUATION_UNAVAILABLE: 80,
    PRACTICE_EVALUATION_AVAILABLE: 85,
    PRACTICE_COMPLETED: 90,
}


class JourneySubmissionView(BaseModel):
    """One persisted submission inside a writing cycle."""

    model_config = ConfigDict(extra="forbid")

    submission_id: int
    is_revision: bool
    revision_of_submission_id: int | None = None
    revision_sequence: int | None = None
    draft_stage: str | None = None
    genre: str | None = None
    submitted_at: str
    writing_state: str


class JourneyFeedbackStage(BaseModel):
    """The persisted feedback stage for one submission."""

    model_config = ConfigDict(extra="forbid")

    submission_id: int
    feedback_id: int | str
    created_at: str
    priority_count: int
    priorities: list[dict[str, Any]] = []
    writing_state: str


class JourneyPracticeCycle(BaseModel):
    """One Practice target and its persisted activity within a cycle."""

    model_config = ConfigDict(extra="forbid")

    practice_target_id: str
    target_code: str
    target_label: str | None = None
    status: str
    created_at: str
    updated_at: str | None = None
    source_submission_id: int
    priority_provenance: dict[str, Any]
    exercise: dict[str, Any] | None = None
    attempt: dict[str, Any] | None = None
    evaluation: dict[str, Any] | None = None
    activity_state: str
    evaluation_state: str
    completion_state: str


class JourneyCycle(BaseModel):
    """One learner-owned writing cycle with its Practice activities."""

    model_config = ConfigDict(extra="forbid")

    cycle_id: str
    learner_id: str
    relationship_status: str
    root_submission: JourneySubmissionView | None = None
    revisions: list[JourneySubmissionView] = []
    feedback_stages: list[JourneyFeedbackStage] = []
    practice_cycles: list[JourneyPracticeCycle] = []
    current_state: str
    chronology: list[dict[str, Any]] = []
    # Populated by WU2 (safe Journey actions); empty in WU1.
    available_actions: list[dict[str, Any]] = []
    limitations: list[str] = []


def _priority_items(feedback_record: dict[str, Any]) -> list[dict[str, Any]]:
    """Priority items of a feedback record (defensive, mirrors the raw
    projection's conservative parsing)."""
    raw = feedback_record.get("feedback_json") or {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            raw = {}
    priorities = raw.get("priority_feedback") or []
    if not isinstance(priorities, list):
        return []
    items: list[dict[str, Any]] = []
    for index, item in enumerate(priorities):
        if not isinstance(item, dict):
            continue
        items.append({
            "index": index,
            "category": item.get("category"),
            "diagnosis_id": item.get("diagnosis_id"),
        })
    return items


def _writing_state(
    essay: dict[str, Any],
    analyses: dict[int, dict[str, Any]],
    feedbacks: dict[int, dict[str, Any]],
) -> str:
    """Most informative honest writing state for one submission."""
    if essay.get("revision_of_submission_id") is not None:
        return WRITING_REVISION_SUBMITTED
    essay_id = int(essay.get("essay_id") or 0)
    if essay_id not in analyses:
        return WRITING_INSUFFICIENT_EVIDENCE
    feedback = feedbacks.get(essay_id)
    if feedback is None:
        return WRITING_ANALYZED
    if _priority_items(feedback):
        return WRITING_FEEDBACK_AVAILABLE
    return WRITING_FEEDBACK_WITHOUT_PRIORITY


def _submission_view(
    essay: dict[str, Any],
    analyses: dict[int, dict[str, Any]],
    feedbacks: dict[int, dict[str, Any]],
) -> JourneySubmissionView:
    essay_id = int(essay.get("essay_id") or 0)
    return JourneySubmissionView(
        submission_id=essay_id,
        is_revision=essay.get("revision_of_submission_id") is not None,
        revision_of_submission_id=essay.get("revision_of_submission_id"),
        revision_sequence=essay.get("revision_sequence"),
        draft_stage=essay.get("draft_stage"),
        genre=essay.get("genre"),
        submitted_at=str(essay.get("submitted_at") or ""),
        writing_state=_writing_state(essay, analyses, feedbacks),
    )


def _feedback_stages(
    submission_ids: list[int],
    feedbacks: dict[int, dict[str, Any]],
) -> list[JourneyFeedbackStage]:
    stages: list[JourneyFeedbackStage] = []
    for essay_id in submission_ids:
        feedback = feedbacks.get(essay_id)
        if feedback is None:
            continue
        items = _priority_items(feedback)
        raw_feedback_id = feedback.get("feedback_id")
        try:
            feedback_id: int | str = int(raw_feedback_id)
        except (TypeError, ValueError):
            feedback_id = str(raw_feedback_id or "")
        stages.append(JourneyFeedbackStage(
            submission_id=essay_id,
            feedback_id=feedback_id,
            created_at=str(feedback.get("created_at") or ""),
            priority_count=len(items),
            priorities=items,
            writing_state=(
                WRITING_FEEDBACK_AVAILABLE if items
                else WRITING_FEEDBACK_WITHOUT_PRIORITY
            ),
        ))
    return stages


def _resolve_root(
    essay: dict[str, Any],
    essay_by_id: dict[int, dict[str, Any]],
) -> tuple[int, bool]:
    """Return (anchor_essay_id, linked) for one essay.

    Linked means the anchor is an original submission (no revision link).
    A broken chain (missing parent) yields an unlinked group anchored at
    the topmost resolvable essay; nothing is ever cross-associated.
    """
    current = essay
    seen: set[int] = set()
    while True:
        essay_id = int(current.get("essay_id") or 0)
        if essay_id in seen:
            return essay_id, False
        seen.add(essay_id)
        parent = current.get("revision_of_submission_id")
        if parent is None:
            return essay_id, True
        parent_essay = essay_by_id.get(int(parent))
        if parent_essay is None:
            return essay_id, False
        current = parent_essay


def _practice_provenance(
    target: dict[str, Any],
    feedbacks: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Validate the target's stable priority provenance read-only."""
    reference = target.get("source_priority_id")
    if not reference:
        return {"status": PROVENANCE_LEGACY, "reference": None}
    try:
        feedback_id, priority_index = parse_stable_priority_reference(reference)
    except PriorityMappingError:
        return {
            "status": PROVENANCE_UNRESOLVED,
            "reference": reference,
            "reason": "invalid_reference",
        }
    feedback = feedbacks.get(int(target.get("source_submission_id") or 0))
    raw_feedback_id = feedback.get("feedback_id") if feedback else None
    try:
        stored_feedback_id: int | str = int(raw_feedback_id)
    except (TypeError, ValueError):
        stored_feedback_id = str(raw_feedback_id or "")
    if feedback is None or stored_feedback_id != feedback_id:
        return {
            "status": PROVENANCE_UNRESOLVED,
            "reference": reference,
            "reason": "feedback_mismatch",
        }
    items = _priority_items(feedback)
    if priority_index < 0 or priority_index >= len(items):
        return {
            "status": PROVENANCE_UNRESOLVED,
            "reference": reference,
            "reason": "index_out_of_range",
        }
    return {
        "status": PROVENANCE_VALID,
        "reference": reference,
        "feedback_id": feedback_id,
        "priority_index": priority_index,
        "category": items[priority_index].get("category"),
    }


def _activity_state(
    target: dict[str, Any],
    attempt: dict[str, Any] | None,
    evaluation: dict[str, Any] | None,
) -> tuple[str, str]:
    status = target.get("status") or ""
    if status == "completed":
        return PRACTICE_COMPLETED, (
            EVALUATION_AVAILABLE if evaluation else EVALUATION_UNAVAILABLE
        )
    if attempt is not None:
        if evaluation is not None:
            return PRACTICE_EVALUATION_AVAILABLE, EVALUATION_AVAILABLE
        if status == "active":
            return PRACTICE_EVALUATION_UNAVAILABLE, EVALUATION_UNAVAILABLE
        return PRACTICE_ATTEMPTED, EVALUATION_UNAVAILABLE
    if status == "active":
        return PRACTICE_AVAILABLE, EVALUATION_NOT_APPLICABLE
    return PRACTICE_UNAVAILABLE, EVALUATION_NOT_APPLICABLE


def build_cycles(
    student_id: str,
    essays: list[dict[str, Any]],
    analyses: dict[int, dict[str, Any]],
    feedbacks: dict[int, dict[str, Any]],
    targets: list[dict[str, Any]],
    exercises: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
    evaluations: list[dict[str, Any]],
    responses: list[dict[str, Any]],
    transfers: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Derive the learner-owned cycle view from persisted records only."""
    essay_by_id = {
        int(essay.get("essay_id") or 0): essay
        for essay in essays
    }

    # Group essays into cycles by their resolved anchor.
    groups: dict[int, list[dict[str, Any]]] = {}
    for essay in essays:
        anchor_id, _linked = _resolve_root(essay, essay_by_id)
        groups.setdefault(anchor_id, []).append(essay)

    # Exercises/attempts/evaluations indexed for practice association.
    exercise_by_id = {
        exercise.get("exercise_id"): exercise
        for exercise in exercises
    }
    exercises_by_target: dict[str, list[dict[str, Any]]] = {}
    for exercise in exercises:
        target_id = exercise.get("practice_target_id") or ""
        exercises_by_target.setdefault(target_id, []).append(exercise)
    attempts_by_exercise: dict[str, list[dict[str, Any]]] = {}
    for attempt in attempts:
        exercise_id = attempt.get("exercise_id") or ""
        attempts_by_exercise.setdefault(exercise_id, []).append(attempt)
    evaluation_by_attempt = {
        evaluation.get("attempt_id"): evaluation
        for evaluation in evaluations
    }

    cycles: list[JourneyCycle] = []
    linked_target_ids: set[str] = set()

    for anchor_id, group in sorted(
        groups.items(),
        key=lambda item: (
            str(essay_by_id[item[0]].get("submitted_at") or ""),
            item[0],
        ),
    ):
        anchor = essay_by_id[anchor_id]
        linked = anchor.get("revision_of_submission_id") is None
        submission_ids = [int(e.get("essay_id") or 0) for e in group]
        submission_id_set = set(submission_ids)
        ordered = sorted(
            group,
            key=lambda e: (
                0 if e is anchor else 1,
                int(e.get("revision_sequence") or 0),
                str(e.get("submitted_at") or ""),
                int(e.get("essay_id") or 0),
            ),
        )
        root_view = _submission_view(anchor, analyses, feedbacks)
        revisions = [
            _submission_view(essay, analyses, feedbacks)
            for essay in ordered
            if essay is not anchor
        ]
        stages = _feedback_stages(submission_ids, feedbacks)

        practice_cycles: list[JourneyPracticeCycle] = []
        cycle_attempt_ids: set[str] = set()
        cycle_evaluation_ids: set[str] = set()
        for target in targets:
            target_id = target.get("practice_target_id") or ""
            if int(target.get("source_submission_id") or 0) not in submission_id_set:
                continue
            linked_target_ids.add(target_id)
            target_exercises = exercises_by_target.get(target_id, [])
            latest_exercise = (
                target_exercises[-1] if target_exercises else None
            )
            target_attempts: list[dict[str, Any]] = []
            for exercise in target_exercises:
                target_attempts.extend(
                    attempts_by_exercise.get(exercise.get("exercise_id") or "", [])
                )
            target_attempts.sort(
                key=lambda a: (
                    str(a.get("created_at") or ""),
                    int(a.get("attempt_number") or 0),
                )
            )
            latest_attempt = target_attempts[-1] if target_attempts else None
            evaluation = None
            if latest_attempt is not None:
                evaluation = evaluation_by_attempt.get(
                    latest_attempt.get("attempt_id"))
                cycle_attempt_ids.add(latest_attempt.get("attempt_id") or "")
            if evaluation is not None:
                cycle_evaluation_ids.add(evaluation.get("evaluation_id") or "")
            activity_state, evaluation_state = _activity_state(
                target, latest_attempt, evaluation)
            practice_cycles.append(JourneyPracticeCycle(
                practice_target_id=target_id,
                target_code=str(target.get("target_code") or ""),
                target_label=target.get("target_label"),
                status=str(target.get("status") or ""),
                created_at=str(target.get("created_at") or ""),
                updated_at=target.get("updated_at"),
                source_submission_id=int(
                    target.get("source_submission_id") or 0),
                priority_provenance=_practice_provenance(target, feedbacks),
                exercise=latest_exercise,
                attempt=latest_attempt,
                evaluation=evaluation,
                activity_state=activity_state,
                evaluation_state=evaluation_state,
                completion_state=(
                    "completed" if target.get("status") == "completed"
                    else "active"
                ),
            ))

        practice_target_ids = {
            pc.practice_target_id for pc in practice_cycles
        }
        chronology = [
            event
            for event in events
            if _event_belongs(
                event,
                submission_id_set,
                practice_target_ids,
                cycle_attempt_ids,
                cycle_evaluation_ids,
            )
        ]

        limitations: list[str] = []
        if not linked:
            limitations.append(
                "This cycle's original submission could not be resolved "
                "from the persisted revision link; no root relationship "
                "was fabricated.")
        states = [root_view.writing_state]
        states.extend(rv.writing_state for rv in revisions)
        states.extend(pc.activity_state for pc in practice_cycles)
        current_state = max(
            states, key=lambda s: _CYCLE_STATE_ORDER.get(s, 0))

        cycles.append(JourneyCycle(
            cycle_id=f"cycle-{anchor_id}",
            learner_id=student_id,
            relationship_status=(
                RELATIONSHIP_LINKED if linked else RELATIONSHIP_UNLINKED),
            root_submission=root_view,
            revisions=revisions,
            feedback_stages=stages,
            practice_cycles=practice_cycles,
            current_state=current_state,
            chronology=chronology,
            limitations=limitations,
        ))

    # Controlled unlinked-practice group for targets whose source
    # submission cannot be resolved (stale/legacy data; never fabricated).
    unlinked_practice_targets = [
        target for target in targets
        if (target.get("practice_target_id") or "") not in linked_target_ids
    ]
    if unlinked_practice_targets:
        unlinked_cycles: list[JourneyPracticeCycle] = []
        for target in unlinked_practice_targets:
            target_id = target.get("practice_target_id") or ""
            target_exercises = exercises_by_target.get(target_id, [])
            target_attempts: list[dict[str, Any]] = []
            for exercise in target_exercises:
                target_attempts.extend(
                    attempts_by_exercise.get(exercise.get("exercise_id") or "", [])
                )
            latest_attempt = target_attempts[-1] if target_attempts else None
            evaluation = (
                evaluation_by_attempt.get(latest_attempt.get("attempt_id"))
                if latest_attempt is not None else None
            )
            activity_state, evaluation_state = _activity_state(
                target, latest_attempt, evaluation)
            unlinked_cycles.append(JourneyPracticeCycle(
                practice_target_id=target_id,
                target_code=str(target.get("target_code") or ""),
                target_label=target.get("target_label"),
                status=str(target.get("status") or ""),
                created_at=str(target.get("created_at") or ""),
                updated_at=target.get("updated_at"),
                source_submission_id=int(
                    target.get("source_submission_id") or 0),
                priority_provenance=_practice_provenance(target, feedbacks),
                exercise=target_exercises[-1] if target_exercises else None,
                attempt=latest_attempt,
                evaluation=evaluation,
                activity_state=activity_state,
                evaluation_state=evaluation_state,
                completion_state=(
                    "completed" if target.get("status") == "completed"
                    else "active"
                ),
            ))
        states = [pc.activity_state for pc in unlinked_cycles]
        current_state = max(
            states, key=lambda s: _CYCLE_STATE_ORDER.get(s, 0))
        cycles.append(JourneyCycle(
            cycle_id="cycle-unlinked-practice",
            learner_id=student_id,
            relationship_status=RELATIONSHIP_UNLINKED,
            root_submission=None,
            practice_cycles=unlinked_cycles,
            current_state=current_state,
            chronology=[],
            limitations=[
                "Practice target source submissions could not be resolved "
                "from the persisted records; these activities are shown "
                "without a fabricated writing-cycle relationship."],
        ))

    return [cycle.model_dump(mode="json") for cycle in cycles]


def _event_belongs(
    event: dict[str, Any],
    submission_ids: set[int],
    practice_target_ids: set[str],
    attempt_ids: set[str],
    evaluation_ids: set[str],
) -> bool:
    if event.get("submission_id") in submission_ids:
        return True
    source_type = event.get("source_record_type")
    source_id = str(event.get("source_record_id") or "")
    if source_type == "practice_target" and source_id in practice_target_ids:
        return True
    if source_type == "exercise_attempt" and source_id in attempt_ids:
        return True
    if source_type == "practice_evaluation" and source_id in evaluation_ids:
        return True
    return False
