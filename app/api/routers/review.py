"""Review / Scheduling Foundation router (CORE, Wave-3 WU1).

Thin API surface over the shared ``ReviewService``: practice activities,
review events, and the durable FSRS memory-scheduling state. The router
validates and translates requests; application services own workflows.
Tutor behavior and UX presentation are NOT owned here.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.deps import get_review_service
from app.review.models import (
    Rating,
    ReviewEvent,
    PracticeActivity,
    PracticeActivityStatus,
)
from app.review.service import ReviewError

router = APIRouter()

_NOT_FOUND_KINDS = frozenset(
    {"learning_item_not_found", "practice_activity_not_found"}
)
_FORBIDDEN_KINDS = frozenset(
    {"learning_item_owner_mismatch", "practice_activity_owner_mismatch"}
)
_CONFLICT_KINDS = frozenset(
    {"practice_activity_already_exists", "review_event_already_exists"}
)


def _review_error_status(kind: str) -> int:
    """Stable ReviewError kind -> HTTP status mapping (fail-closed)."""
    if kind in _NOT_FOUND_KINDS:
        return 404
    if kind in _FORBIDDEN_KINDS:
        return 403
    if kind in _CONFLICT_KINDS:
        return 409
    return 422


def _require_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("datetime must be timezone-aware and set to UTC")
    return value


class PracticeActivityRequest(BaseModel):
    """Client payload for one shared practice activity."""

    model_config = ConfigDict(extra="forbid")

    activity_id: str | None = None
    student_id: str = Field(min_length=1)
    learning_item_id: str = Field(min_length=1)
    activity_type: str = Field(min_length=1, max_length=100)
    source: str = "practice"
    status: PracticeActivityStatus
    occurred_at: datetime
    completed_at: datetime | None = None
    evaluator: str | None = None
    evaluation_id: str | None = None
    evaluator_version: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    authentic_evidence_status: Literal["insufficient", "present"] = (
        "insufficient"
    )

    @field_validator("occurred_at", "completed_at", mode="after")
    @classmethod
    def _validate_utc(cls, value: datetime | None) -> datetime | None:
        return _require_utc(value)


class ReviewEventRequest(BaseModel):
    """Client payload for one review (rating channels stay separate)."""

    model_config = ConfigDict(extra="forbid")

    student_id: str = Field(min_length=1)
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


def _to_activity(payload: PracticeActivityRequest) -> PracticeActivity:
    return PracticeActivity(
        activity_id=payload.activity_id or "PA-PENDING",
        student_id=payload.student_id,
        learning_item_id=payload.learning_item_id,
        activity_type=payload.activity_type,
        source=payload.source,
        status=payload.status,
        occurred_at=payload.occurred_at,
        completed_at=payload.completed_at,
        evaluator=payload.evaluator,
        evaluation_id=payload.evaluation_id,
        evaluator_version=payload.evaluator_version,
        provenance=payload.provenance,
        authentic_evidence_status=payload.authentic_evidence_status,
    )


@router.post("/api/v1/review/practice-activities")
def record_practice_activity(
    payload: PracticeActivityRequest, request: Request
) -> PracticeActivity:
    service = get_review_service(request)
    try:
        return service.record_practice_activity(_to_activity(payload))
    except ReviewError as exc:
        raise HTTPException(
            status_code=_review_error_status(exc.kind), detail=exc.message
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail=str(exc) or "Invalid request input."
        ) from exc


@router.get("/api/v1/review/practice-activities/{learning_item_id}")
def list_practice_activities(
    learning_item_id: str, request: Request
) -> list[PracticeActivity]:
    return get_review_service(request).list_practice_activities(
        learning_item_id
    )


@router.post("/api/v1/review/events")
def record_review(
    payload: ReviewEventRequest, request: Request
) -> ReviewEvent:
    service = get_review_service(request)
    try:
        return service.record_review(
            student_id=payload.student_id,
            learning_item_id=payload.learning_item_id,
            reviewed_at=payload.reviewed_at,
            system_provisional_rating=payload.system_provisional_rating,
            learner_self_rating=payload.learner_self_rating,
            practice_activity_id=payload.practice_activity_id,
            authentic_evidence_status=payload.authentic_evidence_status,
            provenance=payload.provenance,
        )
    except ReviewError as exc:
        raise HTTPException(
            status_code=_review_error_status(exc.kind), detail=exc.message
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail=str(exc) or "Invalid request input."
        ) from exc


@router.get("/api/v1/review/events/{learning_item_id}")
def list_review_events(
    learning_item_id: str, request: Request
) -> list[ReviewEvent]:
    return get_review_service(request).list_review_events(learning_item_id)


@router.get("/api/v1/review/schedule/{learning_item_id}")
def get_schedule(
    learning_item_id: str, request: Request
) -> dict[str, Any]:
    service = get_review_service(request)
    state, identity = service.get_schedule(learning_item_id)
    if state is None or identity is None:
        raise HTTPException(
            status_code=404,
            detail="No durable scheduler state exists for this LearningItem.",
        )
    return {
        "learning_item_id": learning_item_id,
        "scheduler_implementation": identity.implementation,
        "scheduler_version": identity.library_version,
        "state": state.model_dump(mode="json"),
    }


__all__ = ["get_review_service", "router"]
