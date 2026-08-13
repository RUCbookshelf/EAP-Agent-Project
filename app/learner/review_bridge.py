"""Learner-owned structural bridge to the shared CORE Review contracts (WU2).

Boundary (binding):
- The CORE ``app/review`` package (Wave-3 WU1) lives in the shared-core
  worktree and is NOT importable from LEARNER; CORE implementation is never
  copied here.
- This module defines learner-owned typed record contracts that are
  STRUCTURALLY equivalent to the CORE ``PracticeActivity`` and review
  request models (same field names, types, and JSON shape), plus the narrow
  ``CoreReviewServicePort`` Protocol that matches the CORE ``ReviewService``
  surface LEARNER consumes.
- The future INT composition root injects the integrated CORE service (with
  its repository and scheduler) behind that Protocol. Because the records
  mirror the CORE field surface exactly, the raw CORE service/repository can
  consume them through attribute access alone: no second scheduler, store,
  database, runtime, or migration is introduced.

Semantic boundary (binding): practice evidence, review events, and authentic
writing evidence stay separate channels. ``evidence_kind`` is the literal
``"practice"``; ``authentic_evidence_status`` marks whether authentic writing
evidence accompanies a record. The three CORE rating channels (system
provisional, learner self, final scheduler) are never averaged or
reinterpreted; the CORE rating-rule version and the scheduler
identity/version/parameters are carried explicitly in provenance so
reconstructed evidence is deterministic from stored fields.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.schemas import utc_now


# ---------------------------------------------------------------------------
# Ordered rating space (structural mirror of the CORE ``Rating`` enum)
# ---------------------------------------------------------------------------


class Rating(StrEnum):
    """Ordered review rating space; ordinals match py-fsrs ``Rating``."""

    AGAIN = "again"
    HARD = "hard"
    GOOD = "good"
    EASY = "easy"


RATING_ORDINALS: dict[Rating, int] = {
    Rating.AGAIN: 1,
    Rating.HARD: 2,
    Rating.GOOD: 3,
    Rating.EASY: 4,
}


# ---------------------------------------------------------------------------
# Fixed limitation / boundary statements (CORE wording, prohibition context)
# ---------------------------------------------------------------------------


PRACTICE_ACTIVITY_LIMITATION = (
    "Practice completion is activity only; it does not establish mastery, "
    "proficiency, ability, or learning gain, and it does not imply authentic "
    "writing transfer."
)

NO_TRANSFER_IMPLICATION = (
    "Practice success does not imply authentic transfer; authentic writing "
    "evidence is tracked separately and remains distinct from practice "
    "evidence."
)


class PracticeActivityStatus(StrEnum):
    """Activity statuses only; completion never implies mastery."""

    COMPLETED = "completed"
    INCOMPLETE = "incomplete"
    INVALID = "invalid"
    NOT_ATTEMPTED = "not_attempted"
    ABANDONED = "abandoned"


# ---------------------------------------------------------------------------
# Provenance validation (explicit, fail-closed, deterministic)
# ---------------------------------------------------------------------------


BRIDGE_SOURCE = "learner_practice_review_bridge"
BRIDGE_VERSION = "learner-practice-review-bridge-v0.1.0"

# Keys the bridge owns and derives from the injected CORE service; caller
# provenance may never override them (malformed provenance fails closed).
RESERVED_PROVENANCE_KEYS: frozenset[str] = frozenset(
    {
        "bridge",
        "bridge_version",
        "evidence_channel",
        "authentic_evidence_channel",
        "rating_rule_version",
        "scheduler_implementation",
        "scheduler_version",
        "scheduler_parameters",
    }
)

ACTIVITY_RESERVED_PROVENANCE_KEYS: frozenset[str] = frozenset(
    {
        "bridge",
        "bridge_version",
        "evidence_channel",
        "authentic_evidence_channel",
    }
)


class ReviewBridgeError(Exception):
    """Learner-side pre-flight failure with a stable machine-readable kind.

    Raised only for failures detected BEFORE any write: missing injected
    CORE service, non-UTC timestamps, invalid rating/status values, malformed
    provenance, or an unusable scheduler identity/rating-rule version.
    Failures raised by the injected CORE service (missing durable
    LearningItem, ownership mismatch, append-only conflicts, invalid
    transitions) propagate unchanged with the CORE stable kind.
    """

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message


def ensure_json_safe(value: dict[str, Any]) -> None:
    """Fail-closed: provenance must serialize for deterministic storage."""
    try:
        json.dumps(value, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise ReviewBridgeError(
            "malformed_provenance",
            "provenance must be JSON-serializable for deterministic "
            "reconstruction from stored fields.",
        ) from exc


def validate_provenance(
    provenance: dict[str, Any], *, reserved: frozenset[str]
) -> None:
    """Fail-closed provenance check before any write.

    Caller provenance must be JSON-safe and must not override the
    bridge-owned keys (channel markers, rating-rule version, scheduler
    identity/version/parameters), which are derived from the injected CORE
    service.
    """
    for key in provenance:
        if key in reserved:
            raise ReviewBridgeError(
                "malformed_provenance",
                f"provenance must not override bridge-owned field {key!r}.",
            )
    ensure_json_safe(provenance)


# ---------------------------------------------------------------------------
# Learner-owned typed records (structural CORE equivalents)
# ---------------------------------------------------------------------------


def _require_utc(value: datetime | None) -> datetime | None:
    """Fail-closed: reject naive or non-UTC datetimes."""
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(
        None
    ):
        raise ValueError("datetime must be timezone-aware and set to UTC")
    return value


class PracticeActivityRecord(BaseModel):
    """One practice activity record (structural CORE ``PracticeActivity``).

    ``evidence_kind`` is the literal ``"practice"``: the record is practice
    evidence, distinguishable from authentic writing evidence
    (``authentic_evidence_status``). Field names and types mirror the CORE
    contract so the raw CORE service/repository can consume the record
    directly.
    """

    model_config = ConfigDict(extra="forbid")

    activity_id: str = "PA-PENDING"
    student_id: str = Field(min_length=1, max_length=100)
    learning_item_id: str = Field(min_length=1)
    activity_type: str = Field(min_length=1, max_length=100)
    source: str = "practice"
    status: PracticeActivityStatus
    occurred_at: datetime
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    evaluator: str | None = None
    evaluation_id: str | None = None
    evaluator_version: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    evidence_kind: Literal["practice"] = "practice"
    authentic_evidence_status: Literal["insufficient", "present"] = (
        "insufficient"
    )
    limitations: list[str] = Field(
        default_factory=lambda: [PRACTICE_ACTIVITY_LIMITATION]
    )

    @field_validator("occurred_at", "completed_at", mode="after")
    @classmethod
    def _validate_utc(cls, value: datetime | None) -> datetime | None:
        return _require_utc(value)


class ReviewRequestRecord(BaseModel):
    """One review request (structural CORE review request payload).

    The three rating channels stay separate: the request carries the system
    provisional and learner self channels; the final scheduler rating is
    resolved by the CORE versioned rating rule, never by LEARNER.
    """

    model_config = ConfigDict(extra="forbid")

    student_id: str = Field(min_length=1, max_length=100)
    learning_item_id: str = Field(min_length=1)
    practice_activity_id: str | None = None
    reviewed_at: datetime
    system_provisional_rating: Rating
    learner_self_rating: Rating | None = None
    authentic_evidence_status: Literal["insufficient", "present"] = (
        "insufficient"
    )
    provenance: dict[str, Any] = Field(default_factory=dict)

    @field_validator("reviewed_at", mode="after")
    @classmethod
    def _validate_utc(cls, value: datetime) -> datetime:
        return _require_utc(value)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Narrow structural CORE-service port (injected by the INT composition root)
# ---------------------------------------------------------------------------


@runtime_checkable
class CoreReviewServicePort(Protocol):
    """Narrow structural protocol for the injected CORE ``ReviewService``.

    Matches the public CORE ``ReviewService`` surface LEARNER consumes:
    rating-rule version, scheduler identity, practice activity persistence,
    and review recording. Payloads are CORE model instances or the
    structurally-equivalent learner records above; the injected service owns
    its own validation and persistence (no second store).
    """

    rating_rule_version: str

    def scheduler_identity(self) -> Any: ...

    def record_practice_activity(self, activity: Any) -> Any: ...

    def record_review(
        self,
        *,
        student_id: str,
        learning_item_id: str,
        reviewed_at: datetime,
        system_provisional_rating: Any,
        learner_self_rating: Any | None = None,
        practice_activity_id: str | None = None,
        authentic_evidence_status: Literal["insufficient", "present"] = (
            "insufficient"
        ),
        provenance: dict[str, Any] | None = None,
    ) -> Any: ...


__all__ = [
    "ACTIVITY_RESERVED_PROVENANCE_KEYS",
    "BRIDGE_SOURCE",
    "BRIDGE_VERSION",
    "CoreReviewServicePort",
    "NO_TRANSFER_IMPLICATION",
    "PRACTICE_ACTIVITY_LIMITATION",
    "PracticeActivityRecord",
    "PracticeActivityStatus",
    "RATING_ORDINALS",
    "RESERVED_PROVENANCE_KEYS",
    "Rating",
    "ReviewBridgeError",
    "ReviewRequestRecord",
    "ensure_json_safe",
    "validate_provenance",
]
