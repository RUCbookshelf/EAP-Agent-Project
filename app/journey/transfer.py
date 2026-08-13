"""Learner-owned WU2 typed projections: practice history and authentic
writing application observations.

Two clearly separate, additive read-time projections for the Learning
Journey. They consume only the existing learner-owned Journey projection
port (the same persisted records the raw event derivation uses) and, when a
CORE-shaped review-event reader is injected, durable ``ReviewEvent`` rows
consumed structurally (field names mirror the CORE JSON keys; nothing is
imported or copied from ``app/review``).

Semantic boundaries (binding):

- Practice history is ACTIVITY/EVIDENCE ONLY. It never claims mastery,
  proficiency, ability, or learning gain, and practice completion/review
  never implies authentic writing transfer.
- Authentic writing application observations are a SEPARATE channel built
  from later writing/submission observations and the existing within-task /
  transfer candidate concepts. Practice records never merge into it, and no
  causal link from practice to writing is ever inferred.
- Non-comparable or insufficient observations remain explicitly
  non-comparable/insufficient; missing or malformed fields fail closed
  descriptively rather than being fabricated.

No persistence, no migration, no writes: both projections are derived at
read time from authoritative persisted records.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

PRACTICE_HISTORY_PROJECTION_VERSION = "journey-practice-history-v0.9.7"
AUTHENTIC_APPLICATION_PROJECTION_VERSION = "journey-authentic-application-v0.9.7"

PRACTICE_ACTIVITY_LIMITATION = (
    "Practice records are activity/evidence only; they do not establish "
    "mastery, proficiency, ability, or learning gain, and they do not imply "
    "authentic writing transfer."
)

REVIEW_IS_SCHEDULING_STATE = (
    "Review scheduler state is memory scheduling state only; it is not "
    "proficiency, mastery, ability, validated acquisition, or learning gain."
)

NO_TRANSFER_IMPLICATION = (
    "Practice completion or review does not imply authentic writing "
    "transfer; authentic writing evidence is tracked separately and remains "
    "distinct from practice evidence."
)

AUTHENTIC_OBSERVATION_LIMITATION = (
    "A later submission or candidate observation is descriptive only; it "
    "does not prove transfer, mastery, proficiency, ability, or learning "
    "gain, and no causal link to prior practice is inferred."
)


def _normalize_timestamp(value: str | None) -> str:
    """Return a UTC ISO-8601 sortable timestamp for mixed stored formats."""
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return str(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="microseconds")


@runtime_checkable
class JourneyReviewEventReadPort(Protocol):
    """Optional learner-owned structural read of CORE-shaped review-event
    rows (``review_events`` JSON). Not part of the pinned Journey projection
    port; the JourneyService detects it structurally and the projection fails
    closed to ``unavailable`` when it is absent."""

    def list_review_events_by_student(self, student_id: str) -> list[dict]: ...


# ---------------------------------------------------------------------------
# Practice-history projection (activity-only channel)
# ---------------------------------------------------------------------------


class PracticeActivityRecord(BaseModel):
    """One persisted practice activity/evidence or review record."""

    model_config = ConfigDict(extra="forbid")

    record_id: str
    record_kind: Literal["practice_activity", "review_event"]
    activity_type: str
    occurred_at: str
    status: str | None = None
    evidence_kind: Literal["practice"] = "practice"
    authentic_evidence_status: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    rating_channels: dict[str, Any] | None = None
    limitations: list[str] = Field(default_factory=list)


class PracticeHistoryProjection(BaseModel):
    """Typed practice-history projection (activity/evidence only)."""

    model_config = ConfigDict(extra="forbid")

    section: Literal["practice_history"] = "practice_history"
    projection_version: str = PRACTICE_HISTORY_PROJECTION_VERSION
    learner_id: str
    available: bool
    status: Literal["available", "insufficient_history"]
    rating_channel_visibility: Literal["available", "unavailable"]
    records: list[PracticeActivityRecord] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


def _practice_provenance(
    record_kind: str, record: dict[str, Any]
) -> dict[str, Any]:
    if record_kind == "practice_target":
        return {
            key: record.get(key)
            for key in (
                "source_analysis_run_id",
                "source_diagnosis_id",
                "source_priority_id",
                "target_code",
                "target_label",
                "target_scope",
                "diagnostic_version",
                "configuration_version",
                "updated_at",
            )
        }
    if record_kind == "exercise_attempt":
        return {
            key: record.get(key)
            for key in (
                "exercise_id",
                "attempt_number",
                "timing_source",
                "hint_count",
            )
        }
    if record_kind == "practice_evaluation":
        return {
            key: record.get(key)
            for key in (
                "attempt_id",
                "practice_target_id",
                "evaluation_method",
                "completion_status",
                "target_action_status",
                "confidence",
                "evaluator_version",
                "evidence",
            )
        }
    return {}


def _review_rating_channels(row: dict[str, Any]) -> dict[str, Any]:
    """The three CORE rating channels, kept separate and verbatim; a missing
    channel is reported as null, never averaged or reinterpreted."""
    return {
        "system_provisional_rating": row.get("system_provisional_rating"),
        "learner_self_rating": row.get("learner_self_rating"),
        "final_scheduler_rating": row.get("final_scheduler_rating"),
    }


def _review_provenance(row: dict[str, Any]) -> dict[str, Any]:
    """Stable provenance/version fields of a CORE-shaped review-event row."""
    return {
        "learning_item_id": row.get("learning_item_id"),
        "practice_activity_id": row.get("practice_activity_id"),
        "rating_rule_version": row.get("rating_rule_version"),
        "scheduler_implementation": row.get("scheduler_implementation"),
        "scheduler_version": row.get("scheduler_version"),
        "scheduler_parameters": row.get("scheduler_parameters"),
        "state_before": row.get("state_before"),
        "state_after": row.get("state_after"),
        "scheduling_result": row.get("scheduling_result"),
        "review_source_provenance": row.get("provenance"),
    }


def build_practice_history(
    student_id: str,
    targets: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
    evaluations: list[dict[str, Any]],
    review_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Derive the typed practice-history projection from persisted records.

    ``review_events=None`` means no CORE-shaped review reader is available;
    the projection reports ``rating_channel_visibility="unavailable"`` and
    never fabricates rating channels or scheduler provenance. When a reader
    is present, malformed rows (non-dict, empty id) are skipped and missing
    channels stay null with an explicit limitation.
    """
    records: list[PracticeActivityRecord] = []

    for target in targets:
        record_id = str(target.get("practice_target_id") or "")
        if not record_id:
            continue
        records.append(PracticeActivityRecord(
            record_id=record_id,
            record_kind="practice_activity",
            activity_type="practice_target",
            occurred_at=_normalize_timestamp(target.get("created_at")),
            status=target.get("status"),
            provenance=_practice_provenance("practice_target", target),
            limitations=[PRACTICE_ACTIVITY_LIMITATION],
        ))

    for attempt in attempts:
        record_id = str(attempt.get("attempt_id") or "")
        if not record_id:
            continue
        records.append(PracticeActivityRecord(
            record_id=record_id,
            record_kind="practice_activity",
            activity_type="exercise_attempt",
            occurred_at=_normalize_timestamp(attempt.get("created_at")),
            status=attempt.get("status"),
            provenance=_practice_provenance("exercise_attempt", attempt),
            limitations=[PRACTICE_ACTIVITY_LIMITATION],
        ))

    for evaluation in evaluations:
        record_id = str(evaluation.get("evaluation_id") or "")
        if not record_id:
            continue
        records.append(PracticeActivityRecord(
            record_id=record_id,
            record_kind="practice_activity",
            activity_type="practice_evaluation",
            occurred_at=_normalize_timestamp(evaluation.get("created_at")),
            status=evaluation.get("completion_status"),
            provenance=_practice_provenance("practice_evaluation", evaluation),
            limitations=[PRACTICE_ACTIVITY_LIMITATION],
        ))

    if review_events is not None:
        for row in review_events:
            if not isinstance(row, dict):
                continue
            record_id = str(row.get("review_event_id") or "")
            if not record_id:
                continue
            channels = _review_rating_channels(row)
            limitations = [
                REVIEW_IS_SCHEDULING_STATE,
                NO_TRANSFER_IMPLICATION,
            ]
            if any(value is None for value in channels.values()):
                limitations.append(
                    "One or more rating channels are unavailable for this "
                    "review record; no channel is fabricated.")
            limitations.extend(
                item for item in row.get("limitations") or []
                if isinstance(item, str) and item
            )
            records.append(PracticeActivityRecord(
                record_id=record_id,
                record_kind="review_event",
                activity_type="review_event",
                occurred_at=_normalize_timestamp(row.get("reviewed_at")),
                evidence_kind="practice",
                authentic_evidence_status=row.get(
                    "authentic_evidence_status"),
                provenance=_review_provenance(row),
                rating_channels=channels,
                limitations=limitations,
            ))

    records.sort(key=lambda r: (r.occurred_at, r.record_id, r.record_kind))

    counts = {
        "practice_targets": len(targets),
        "exercise_attempts": len(attempts),
        "practice_evaluations": len(evaluations),
        "review_events": len(
            [r for r in records if r.record_kind == "review_event"]),
    }
    limitations = [PRACTICE_ACTIVITY_LIMITATION]
    if review_events is None:
        limitations.append(
            "Review events are not exposed through the current learner-owned "
            "read port; rating channels and scheduler provenance are "
            "unavailable. An injected CORE-shaped review-event reader will "
            "surface them without schema change.")
    if not records:
        limitations.append(
            "No practice activity records exist for this learner; practice "
            "history is insufficient to characterize practice engagement.")

    return PracticeHistoryProjection(
        learner_id=student_id,
        available=bool(records),
        status="available" if records else "insufficient_history",
        rating_channel_visibility=(
            "available" if review_events is not None else "unavailable"),
        records=records,
        counts=counts,
        limitations=limitations,
    ).model_dump(mode="json")


# ---------------------------------------------------------------------------
# Authentic writing application projection (separate channel)
# ---------------------------------------------------------------------------


class AuthenticApplicationObservation(BaseModel):
    """One later writing/submission or within-task / transfer observation."""

    model_config = ConfigDict(extra="forbid")

    observation_id: str
    observation_kind: Literal[
        "later_submission", "within_task_response", "later_task_evidence"]
    source_submission_id: int | None = None
    later_submission_id: int | None = None
    task_id: str | None = None
    target_code: str | None = None
    observed_status: str
    comparability: str | None = None
    comparison_version: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class AuthenticApplicationProjection(BaseModel):
    """Typed authentic writing application observation projection."""

    model_config = ConfigDict(extra="forbid")

    section: Literal["authentic_application"] = "authentic_application"
    projection_version: str = AUTHENTIC_APPLICATION_PROJECTION_VERSION
    learner_id: str
    available: bool
    status: Literal["present", "insufficient"]
    observations: list[AuthenticApplicationObservation] = Field(
        default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


def build_authentic_application(
    student_id: str,
    essays: list[dict[str, Any]],
    responses: list[dict[str, Any]],
    transfers: list[dict[str, Any]],
) -> dict[str, Any]:
    """Derive the typed authentic writing application projection.

    Only authentic writing observations are used: later submissions
    (persisted revision links), within-task response candidates, and later
    task evidence candidates. Practice targets/attempts/evaluations never
    enter this channel. Stored ``observed_status`` and comparability values
    are retained verbatim so non-comparable and insufficient observations
    stay explicitly non-comparable/insufficient.
    """
    observations: list[AuthenticApplicationObservation] = []

    for essay in essays:
        revision_of = essay.get("revision_of_submission_id")
        if revision_of is None:
            continue
        essay_id = int(essay.get("essay_id") or 0)
        observations.append(AuthenticApplicationObservation(
            observation_id=str(essay_id),
            observation_kind="later_submission",
            source_submission_id=int(revision_of),
            later_submission_id=essay_id,
            task_id=essay.get("revision_group_id"),
            observed_status="submitted",
            comparability="within_task_revision",
            provenance={
                "draft_stage": essay.get("draft_stage"),
                "genre": essay.get("genre"),
                "revision_sequence": essay.get("revision_sequence"),
                "submitted_at": essay.get("submitted_at"),
            },
            limitations=[AUTHENTIC_OBSERVATION_LIMITATION],
        ))

    for response in responses:
        record_id = str(response.get("response_id") or "")
        if not record_id:
            continue
        observations.append(AuthenticApplicationObservation(
            observation_id=record_id,
            observation_kind="within_task_response",
            source_submission_id=response.get("source_submission_id"),
            later_submission_id=response.get("later_submission_id"),
            task_id=response.get("revision_group_id"),
            target_code=response.get("target_code"),
            observed_status=str(response.get("observed_status") or ""),
            comparability="within_task",
            comparison_version=response.get("comparison_version"),
            provenance={
                "practice_target_id": response.get("practice_target_id"),
                "evidence_ids": response.get("evidence_ids"),
                "confidence": response.get("confidence"),
                "created_at": response.get("created_at"),
            },
            limitations=[
                AUTHENTIC_OBSERVATION_LIMITATION,
                *(
                    item for item in response.get("limitations") or []
                    if isinstance(item, str) and item
                ),
            ],
        ))

    for transfer in transfers:
        record_id = str(transfer.get("transfer_evidence_id") or "")
        if not record_id:
            continue
        observations.append(AuthenticApplicationObservation(
            observation_id=record_id,
            observation_kind="later_task_evidence",
            source_submission_id=transfer.get("source_submission_id"),
            later_submission_id=transfer.get("later_submission_id"),
            target_code=transfer.get("target_code"),
            observed_status=str(transfer.get("observed_status") or ""),
            comparability=transfer.get("task_comparability"),
            provenance={
                "practice_target_id": transfer.get("practice_target_id"),
                "history_evidence_ids": transfer.get("history_evidence_ids"),
                "confidence": transfer.get("confidence"),
                "created_at": transfer.get("created_at"),
            },
            limitations=[
                AUTHENTIC_OBSERVATION_LIMITATION,
                *(
                    item for item in transfer.get("limitations") or []
                    if isinstance(item, str) and item
                ),
            ],
        ))

    observations.sort(
        key=lambda o: (
            _normalize_timestamp(
                str((o.provenance or {}).get("created_at") or "")
                or str((o.provenance or {}).get("submitted_at") or "")),
            o.observation_id,
            o.observation_kind,
        ))

    counts = {
        "later_submissions": len(
            [o for o in observations
             if o.observation_kind == "later_submission"]),
        "within_task_responses": len(
            [o for o in observations
             if o.observation_kind == "within_task_response"]),
        "later_task_evidence": len(
            [o for o in observations
             if o.observation_kind == "later_task_evidence"]),
    }
    limitations = [
        AUTHENTIC_OBSERVATION_LIMITATION,
        NO_TRANSFER_IMPLICATION,
    ]
    if not observations:
        limitations.append(
            "No later writing or transfer observations exist for this "
            "learner; authentic writing application evidence is "
            "insufficient.")

    return AuthenticApplicationProjection(
        learner_id=student_id,
        available=bool(observations),
        status="present" if observations else "insufficient",
        observations=observations,
        counts=counts,
        limitations=limitations,
    ).model_dump(mode="json")


__all__ = [
    "AUTHENTIC_APPLICATION_PROJECTION_VERSION",
    "AUTHENTIC_OBSERVATION_LIMITATION",
    "NO_TRANSFER_IMPLICATION",
    "PRACTICE_ACTIVITY_LIMITATION",
    "PRACTICE_HISTORY_PROJECTION_VERSION",
    "REVIEW_IS_SCHEDULING_STATE",
    "AuthenticApplicationObservation",
    "AuthenticApplicationProjection",
    "JourneyReviewEventReadPort",
    "PracticeActivityRecord",
    "PracticeHistoryProjection",
    "build_authentic_application",
    "build_practice_history",
]
