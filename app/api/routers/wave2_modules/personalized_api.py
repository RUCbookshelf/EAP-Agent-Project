"""Wave-2 Personalized Learning Bridge API (Goal PDW2-C-L2-REVISION-SCAFFOLD).

Router module under ``/api/v1/wave2/personalized/``: priority revision plan
(local + global + historical feedback), 7-level progressive scaffold
(default SCAFFOLD FIRST) and LearningItem v1 lifecycle. The CORE Wave-2
assembly mounts this module's ``router`` at integration; this module stays
importable as a namespace package on the L2 branch.

Outputs are bounded and non-normative; explicit insufficient-history states
are first-class. Composed outputs are scanned strictly with the shared
NormativeClaimsScanner and rejected structurally (HTTP 500); request
free-text that carries unsupported normative/mastery claims is rejected with
HTTP 422.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.learner.normative import NormativeClaimsScanner
from app.l2.wave2.corpus_routing import LocalWrittenCorpusRouter
from app.l2.wave2.personalized import PersonalizedBridgeService
from app.l2.wave2.pipeline import ExistingWritingPipeline
from app.l2.wave2.repository import InMemoryRevisionLoopRepository


router = APIRouter()

_SCANNER = NormativeClaimsScanner()
_DEFAULT_REPOSITORY = InMemoryRevisionLoopRepository()

NORMATIVE_REJECTION_DETAIL = (
    "An output candidate failed the no-normative-claims scan; nothing was "
    "returned (structural rejection)."
)


def get_personalized_bridge_service(request: Request) -> PersonalizedBridgeService:
    """Branch-local default: existing composition-root services + in-memory
    repository until the Wave-2 composition wiring lands at integration."""

    submission_service = getattr(request.app.state, "submission_service", None)
    reanalysis_service = getattr(request.app.state, "reanalysis", None)
    if submission_service is None or reanalysis_service is None:
        raise HTTPException(
            status_code=503,
            detail="Wave-2 personalized router requires the composition-root services.",
        )
    return PersonalizedBridgeService(
        repository=_DEFAULT_REPOSITORY,
        pipeline=ExistingWritingPipeline(submission_service, reanalysis_service),
        routing=LocalWrittenCorpusRouter(),
    )


def reject_normative_output(payload) -> None:
    """Strict no-normative-claims guard over a composed response payload."""
    violations = _SCANNER.scan_mapping(payload)
    if violations:
        raise HTTPException(status_code=500, detail=NORMATIVE_REJECTION_DETAIL)


def _reject_normative_input(value: str | None, field_name: str) -> None:
    if not value:
        return
    violations = _SCANNER.scan_text(value)
    if violations:
        raise HTTPException(
            status_code=422,
            detail=(
                f"The '{field_name}' field contains unsupported normative "
                "claims and was rejected."
            ),
        )


class PriorityPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: str = Field(min_length=1, max_length=100)
    task_id: str = Field(min_length=1)
    submission_id: int = Field(ge=1)


class ScaffoldRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: str = Field(min_length=1, max_length=100)
    plan_item_id: str | None = None
    learning_item_id: str | None = None
    category: str | None = Field(default=None, max_length=100)
    evidence: str | None = Field(default=None, max_length=500)
    level: int | None = Field(default=None, ge=1, le=7)

    @field_validator("evidence")
    @classmethod
    def evidence_must_not_carry_normative_claims(cls, value: str | None) -> str | None:
        if value:
            _reject_normative_input(value, "evidence")
        return value


class LearningItemCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: str = Field(min_length=1, max_length=100)
    plan_item_id: str = Field(min_length=1)


class LearningItemStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(pattern=r"^(proposed|active|superseded|closed)$")


@router.post("/api/v1/wave2/personalized/priority-plan")
def priority_plan(
    request: PriorityPlanRequest,
    service: PersonalizedBridgeService = Depends(get_personalized_bridge_service),
) -> dict:
    """Small actionable priority revision plan (local + global + historical)."""
    try:
        plan = service.build_priority_plan(
            request.learner_id, request.task_id, request.submission_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    payload = plan.model_dump(mode="json")
    reject_normative_output(payload)
    return payload


@router.post("/api/v1/wave2/personalized/scaffold")
def scaffold(
    request: ScaffoldRequest,
    service: PersonalizedBridgeService = Depends(get_personalized_bridge_service),
) -> dict:
    """One scaffold reveal (default SCAFFOLD FIRST; 7 levels)."""
    try:
        response = service.request_scaffold(
            request.learner_id,
            plan_item_id=request.plan_item_id,
            learning_item_id=request.learning_item_id,
            category=request.category,
            evidence=request.evidence,
            level=request.level,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    payload = response.model_dump(mode="json")
    reject_normative_output(payload)
    return payload


@router.get("/api/v1/wave2/personalized/learning-items")
def list_learning_items(
    student_id: str,
    status: str | None = None,
    service: PersonalizedBridgeService = Depends(get_personalized_bridge_service),
) -> dict:
    """List LearningItem v1 records for a learner."""
    items = service.list_learning_items(student_id, status=status)
    payload = {"student_id": student_id, "items": [
        item.model_dump(mode="json") for item in items
    ]}
    reject_normative_output(payload)
    return payload


@router.post("/api/v1/wave2/personalized/learning-items", status_code=201)
def create_learning_item(
    request: LearningItemCreateRequest,
    service: PersonalizedBridgeService = Depends(get_personalized_bridge_service),
) -> dict:
    """Create a durable LearningItem v1 from a priority plan item."""
    try:
        item = service.create_learning_item(
            request.learner_id, request.plan_item_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    payload = item.model_dump(mode="json")
    reject_normative_output(payload)
    return payload


@router.patch("/api/v1/wave2/personalized/learning-items/{learning_item_id}")
def update_learning_item_status(
    learning_item_id: str,
    request: LearningItemStatusRequest,
    service: PersonalizedBridgeService = Depends(get_personalized_bridge_service),
) -> dict:
    """Transition a LearningItem status (proposed/active/superseded/closed)."""
    try:
        item = service.update_learning_item_status(
            learning_item_id, request.status,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    payload = item.model_dump(mode="json")
    reject_normative_output(payload)
    return payload


__all__ = ["get_personalized_bridge_service", "reject_normative_output", "router"]
