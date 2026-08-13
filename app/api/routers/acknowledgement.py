"""Acknowledgement router: positive longitudinal acknowledgement (WU2-C).

Learner-owned, additive routes under
``/api/v1/students/{student_id}/acknowledgements``. The router resolves the
service exclusively from ``request.app.state.acknowledgement_service``
(composed by Worker D in the single composition root); it never wires
``main.py`` or ``deps.py`` itself. All failures map to stable HTTP statuses
with no acknowledgement write.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError

from app.learner.acknowledgement import (
    AcknowledgementError,
    AcknowledgementService,
)
from app.learner.acknowledgement_contracts import AcknowledgementRequest


router = APIRouter()


_STATUS_BY_KIND = {
    "consent_missing": 403,
    "consent_denied": 403,
    "consent_revoked": 403,
    "consent_scope_mismatch": 403,
    "consent_learner_mismatch": 403,
    "consent_invalid": 403,
    "evidence_unavailable": 503,
    "missing_evidence": 422,
    "invalid_source_kind": 422,
    "invalid_evidence_status": 422,
    "missing_provenance": 422,
    "missing_version": 422,
    "evidence_not_found": 404,
    "cross_student": 403,
    "invalid_source_record": 422,
    "learning_item_not_found": 404,
    "learning_item_owner_mismatch": 403,
    "practice_activity_not_found": 404,
    "practice_activity_owner_mismatch": 403,
    "review_event_not_found": 404,
    "review_event_owner_mismatch": 403,
    "invalid_authentic_evidence_status": 422,
    "normative_language": 422,
    "causal_language": 422,
    "duplicate_acknowledgement": 409,
    "conflict": 409,
}


def get_acknowledgement_service(request: Request) -> AcknowledgementService:
    """Composition-root dependency: resolve from ``request.app.state``."""

    service = getattr(request.app.state, "acknowledgement_service", None)
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="The acknowledgement service is not composed.",
        )
    return service


@router.post("/api/v1/students/{student_id}/acknowledgements")
def create_acknowledgement(
    student_id: str,
    payload: dict,
    service: AcknowledgementService = Depends(get_acknowledgement_service),
) -> dict:
    """Acknowledge already admitted learner evidence (descriptive only)."""

    if payload.get("learner_id") != student_id:
        raise HTTPException(
            status_code=422,
            detail="learner_id conflicts with the path student_id.",
        )
    try:
        request_model = AcknowledgementRequest.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422, detail="Malformed acknowledgement payload.",
        ) from exc
    try:
        result = service.acknowledge(request_model)
    except AcknowledgementError as exc:
        status = _STATUS_BY_KIND.get(exc.kind, 422)
        raise HTTPException(status_code=status, detail=exc.message) from exc
    return result.model_dump(mode="json")


@router.get("/api/v1/students/{student_id}/acknowledgements")
def list_acknowledgements(
    student_id: str,
    service: AcknowledgementService = Depends(get_acknowledgement_service),
) -> dict:
    """Append-only list of a learner's acknowledgements."""

    items = service.list_for_learner(student_id)
    return {
        "learner_id": student_id,
        "items": [record.model_dump(mode="json") for record in items],
    }


__all__ = ["get_acknowledgement_service", "router"]
