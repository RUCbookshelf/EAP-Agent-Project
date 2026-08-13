"""Wave-2/3 Personalized Learning Bridge API.

Wave-2 routes (Goal PDW2-C-L2-REVISION-SCAFFOLD): priority revision plan
(local + global + historical feedback), 7-level progressive scaffold
(default SCAFFOLD FIRST) and LearningItem v1 lifecycle.

Wave-3 WU3 routes (Goal PDW3-WU3-L2-ADAPTIVE-PRACTICE-TUTOR-20260812):
adaptive-practice recommendation/selection/evaluation, bounded mini-writing
through the existing Writing Intelligence pipeline, and consented
history-aware Tutor orchestration (recommend/accept/decline/observation).
Existing WU2 routes and contracts are preserved unchanged.

The CORE Wave-2 assembly mounts this module's ``router`` at integration; this
module stays importable as a namespace package on the L2 branch. Outputs are
bounded and non-normative; explicit insufficient-history states are
first-class. Composed outputs are scanned strictly with the shared
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
from app.l2.wave2.revision_loop import RevisionLoopService
from app.l2.wave3.adapters import (
    ExistingPracticeActivitySource,
    InMemoryConsentStore,
    InMemoryReviewEvidenceStore,
    PipelineAuthenticObservationReader,
)
from app.l2.wave3.adaptive_practice import AdaptivePracticeService
from app.l2.wave3.mini_writing import MiniWritingService
from app.l2.wave3.models import TutorConsentSnapshot
from app.l2.wave3.tutor import (
    CONSENT_SCOPE,
    CONSENT_VERSION,
    ProactiveTutorService,
)


router = APIRouter()

_SCANNER = NormativeClaimsScanner()
_DEFAULT_REPOSITORY = InMemoryRevisionLoopRepository()

NORMATIVE_REJECTION_DETAIL = (
    "An output candidate failed the no-normative-claims scan; nothing was "
    "returned (structural rejection)."
)


def _composition_services(request: Request):
    """Composition-root services required by both Wave-2 and Wave-3."""
    submission_service = getattr(request.app.state, "submission_service", None)
    reanalysis_service = getattr(request.app.state, "reanalysis", None)
    if submission_service is None or reanalysis_service is None:
        raise HTTPException(
            status_code=503,
            detail="Wave-2/3 personalized router requires the composition-root services.",
        )
    return submission_service, reanalysis_service


def _wave2_pipeline(request: Request) -> ExistingWritingPipeline:
    submission_service, reanalysis_service = _composition_services(request)
    return ExistingWritingPipeline(submission_service, reanalysis_service)


def _wave2_repository(request: Request):
    repository = getattr(request.app.state, "wave2_repository", None)
    return repository or _DEFAULT_REPOSITORY


def get_personalized_bridge_service(request: Request) -> PersonalizedBridgeService:
    """Composition-aware default: existing composition-root services + the
    CORE-composed shared repository (``request.app.state.wave2_repository``)
    when present; module-local in-memory repository only for standalone test
    contexts."""

    pipeline = _wave2_pipeline(request)
    repository = _wave2_repository(request)
    return PersonalizedBridgeService(
        repository=repository,
        pipeline=pipeline,
        routing=LocalWrittenCorpusRouter(),
    )


def get_wave3_adaptive_service(request: Request) -> AdaptivePracticeService:
    """Adaptive-practice service over the shared composition seam."""
    return AdaptivePracticeService(
        repository=_wave2_repository(request),
        pipeline=_wave2_pipeline(request),
        activity_source=ExistingPracticeActivitySource(),
    )


def get_wave3_mini_writing_service(request: Request) -> MiniWritingService:
    """Mini-writing service re-entering the existing pipeline."""
    repository = _wave2_repository(request)
    return MiniWritingService(
        revision_loop=RevisionLoopService(
            repository=repository,
            pipeline=_wave2_pipeline(request),
            routing=LocalWrittenCorpusRouter(),
        ),
    )


def get_wave3_tutor_service(request: Request) -> ProactiveTutorService:
    """Consented Tutor orchestration over the shared composition seam.

    The CORE review/scheduler and LEARNER consent ports are structurally
    consumed; the real CORE ReviewService and LEARNER consent persistence
    are injected by the INT composition root behind the same protocols at
    the consolidated Wave-3 gate. Branch-local in-memory adapters are used
    here only for standalone test contexts.
    """
    repository = _wave2_repository(request)
    pipeline = _wave2_pipeline(request)
    adaptive = AdaptivePracticeService(
        repository=repository,
        pipeline=pipeline,
        activity_source=ExistingPracticeActivitySource(),
    )
    return ProactiveTutorService(
        repository=repository,
        consent_store=getattr(
            request.app.state, "learner_consent_store", InMemoryConsentStore(),
        ),
        review_evidence=getattr(
            request.app.state, "core_review_evidence", InMemoryReviewEvidenceStore(),
        ),
        adaptive=adaptive,
        observation_source=PipelineAuthenticObservationReader(repository, pipeline),
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


class AdaptivePracticeRecommendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: str = Field(min_length=1, max_length=100)


class AdaptivePracticeSelectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: str = Field(min_length=1, max_length=100)
    recommendation_id: str = Field(min_length=1)
    activity_id: str = Field(min_length=1)


class AdaptivePracticeEvaluateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: str = Field(min_length=1, max_length=100)
    activity_id: str = Field(min_length=1)
    response_text: str = Field(min_length=1, max_length=2000)

    @field_validator("response_text")
    @classmethod
    def response_must_not_carry_normative_claims(cls, value: str) -> str:
        _reject_normative_input(value, "response_text")
        return value


class MiniWritingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: str = Field(min_length=1, max_length=100)
    task_id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=2000)

    @field_validator("text")
    @classmethod
    def text_must_not_carry_normative_claims(cls, value: str) -> str:
        _reject_normative_input(value, "text")
        return value


class TutorRecommendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: str = Field(min_length=1, max_length=100)


class TutorAcceptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: str = Field(min_length=1, max_length=100)
    recommendation_id: str = Field(min_length=1)
    consent: dict | None = None


class TutorDeclineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: str = Field(min_length=1, max_length=100)
    recommendation_id: str = Field(min_length=1)


class TutorObservationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=100)


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


@router.post("/api/v1/wave2/personalized/adaptive-practice/recommend")
def adaptive_practice_recommend(
    request: AdaptivePracticeRecommendRequest,
    service: AdaptivePracticeService = Depends(get_wave3_adaptive_service),
) -> dict:
    """Deterministic, explainable qualified activity recommendation."""
    recommendation = service.recommend(request.learner_id)
    payload = recommendation.model_dump(mode="json")
    reject_normative_output(payload)
    return payload


@router.post("/api/v1/wave2/personalized/adaptive-practice/select")
def adaptive_practice_select(
    request: AdaptivePracticeSelectRequest,
    service: AdaptivePracticeService = Depends(get_wave3_adaptive_service),
) -> dict:
    """Explicit (or default) learner choice over a qualified activity."""
    try:
        selection = service.select(
            request.learner_id, request.recommendation_id, request.activity_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    payload = selection.model_dump(mode="json")
    reject_normative_output(payload)
    return payload


@router.post("/api/v1/wave2/personalized/adaptive-practice/evaluate")
def adaptive_practice_evaluate(
    request: AdaptivePracticeEvaluateRequest,
    service: AdaptivePracticeService = Depends(get_wave3_adaptive_service),
) -> dict:
    """Deterministic rule-based evaluation of one attempt."""
    try:
        evaluation = service.evaluate(
            request.learner_id, request.activity_id, request.response_text,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    payload = evaluation.model_dump(mode="json")
    reject_normative_output(payload)
    return payload


@router.post(
    "/api/v1/wave2/personalized/mini-writing", status_code=201,
)
def mini_writing(
    request: MiniWritingRequest,
    service: MiniWritingService = Depends(get_wave3_mini_writing_service),
) -> dict:
    """Bounded mini-writing through the existing Writing Intelligence pipeline."""
    try:
        result = service.submit(request.learner_id, request.task_id, request.text)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    payload = result.model_dump(mode="json")
    reject_normative_output(payload)
    return payload


@router.post("/api/v1/wave2/personalized/tutor/recommend")
def tutor_recommend(
    request: TutorRecommendRequest,
    service: ProactiveTutorService = Depends(get_wave3_tutor_service),
) -> dict:
    """History/due-item grounded Tutor suggestion (never executed here)."""
    recommendation = service.recommend(request.learner_id)
    payload = recommendation.model_dump(mode="json")
    reject_normative_output(payload)
    return payload


@router.post("/api/v1/wave2/personalized/tutor/accept")
def tutor_accept(
    request: TutorAcceptRequest,
    service: ProactiveTutorService = Depends(get_wave3_tutor_service),
) -> dict:
    """Accept a Tutor suggestion with explicit learner consent."""
    consent = None
    if request.consent is not None:
        consent = TutorConsentSnapshot(**request.consent)
    try:
        decision = service.accept(
            request.learner_id, request.recommendation_id, consent,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    payload = decision.model_dump(mode="json")
    reject_normative_output(payload)
    return payload


@router.post("/api/v1/wave2/personalized/tutor/decline")
def tutor_decline(
    request: TutorDeclineRequest,
    service: ProactiveTutorService = Depends(get_wave3_tutor_service),
) -> dict:
    """Decline a Tutor suggestion (side-effect safe)."""
    try:
        decision = service.decline(request.learner_id, request.recommendation_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    payload = decision.model_dump(mode="json")
    reject_normative_output(payload)
    return payload


@router.post("/api/v1/wave2/personalized/tutor/observation")
def tutor_observation(
    request: TutorObservationRequest,
    service: ProactiveTutorService = Depends(get_wave3_tutor_service),
) -> dict:
    """Bounded positive observation of authentic writing evidence."""
    observation = service.positive_observation(
        request.learner_id, category=request.category,
    )
    payload = {
        "learner_id": request.learner_id,
        "observation": (
            observation.model_dump(mode="json") if observation is not None else None
        ),
    }
    reject_normative_output(payload)
    return payload


__all__ = [
    "get_personalized_bridge_service",
    "get_wave3_adaptive_service",
    "get_wave3_mini_writing_service",
    "get_wave3_tutor_service",
    "reject_normative_output",
    "router",
]
