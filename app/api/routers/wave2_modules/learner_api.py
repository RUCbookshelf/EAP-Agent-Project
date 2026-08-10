"""Wave-2 Longitudinal Learner Model API (Goal PDW2-B-LEARNER-MODEL).

Router module under ``/api/v1/wave2/learner/`` exposing observation-only,
non-normative longitudinal views: observations, recurring difficulties,
strengths, stable observations, proficiency context (external anchors only)
and current evidence with provenance links. The CORE Wave-2 assembly
(``app.api.routers.wave2``) mounts this module's ``router`` at integration;
``wave2_modules/__init__.py`` is contributed by CORE, so this module stays
importable as a namespace package on the LEARNER branch.

The dependency returns a branch-local service backed by the in-memory
repository until the Wave-2 composition root wiring lands at integration;
test clients override it with ``app.dependency_overrides``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.learner.wave2.repository import InMemoryObservationRepository
from app.learner.wave2.services import LongitudinalLearnerService

router = APIRouter()

_DEFAULT_LEARNER_SERVICE = LongitudinalLearnerService(
    InMemoryObservationRepository()
)


def get_learner_model_service() -> LongitudinalLearnerService:
    """Branch-local default service (in-memory until integration wiring)."""

    return _DEFAULT_LEARNER_SERVICE


@router.get("/api/v1/wave2/learner/observations")
def list_observations(
    learner_id: str,
    service: LongitudinalLearnerService = Depends(get_learner_model_service),
) -> dict:
    """Longitudinal status for every observation of a learner."""

    return service.list_observation_statuses(learner_id).model_dump(mode="json")


@router.get("/api/v1/wave2/learner/observations/{observation_id}")
def get_observation(
    learner_id: str,
    observation_id: str,
    service: LongitudinalLearnerService = Depends(get_learner_model_service),
) -> dict:
    """Longitudinal status of one observation (has it appeared before? how
    often in qualified recent writing? in which contexts? was it addressed in
    a prior revision?)."""

    view = service.observation_status(learner_id, observation_id)
    if view is None:
        raise HTTPException(
            status_code=404,
            detail="Observation not found for this learner.",
        )
    return view.model_dump(mode="json")


@router.get("/api/v1/wave2/learner/difficulties")
def list_difficulties(
    learner_id: str,
    min_occurrences: int = 2,
    recent_window: int = 3,
    service: LongitudinalLearnerService = Depends(get_learner_model_service),
) -> dict:
    """Recurring difficulties with occurrence history, recency and revision
    response."""

    return service.recurring_difficulties(
        learner_id,
        min_occurrences=min_occurrences,
        recent_window=recent_window,
    ).model_dump(mode="json")


@router.get("/api/v1/wave2/learner/strengths")
def list_strengths(
    learner_id: str,
    service: LongitudinalLearnerService = Depends(get_learner_model_service),
) -> dict:
    """Strengths with positive/stable history (observation-only)."""

    return service.strengths(learner_id).model_dump(mode="json")


@router.get("/api/v1/wave2/learner/stable")
def stable_observations(
    learner_id: str,
    recent_window: int = 3,
    min_qualified_recent: int = 2,
    service: LongitudinalLearnerService = Depends(get_learner_model_service),
) -> dict:
    """What is stable recently: repeated strength history or previously
    recurring issues no longer observed across recent qualified samples."""

    return service.stable_recently(
        learner_id,
        recent_window=recent_window,
        min_qualified_recent=min_qualified_recent,
    ).model_dump(mode="json")


@router.get("/api/v1/wave2/learner/proficiency-context")
def proficiency_context(
    learner_id: str,
    service: LongitudinalLearnerService = Depends(get_learner_model_service),
) -> dict:
    """Learner proficiency context with external anchors only (CET-4/6,
    IELTS, TOEFL, other); never auto-converted from corpus statistics."""

    return service.proficiency_context(learner_id).model_dump(mode="json")


@router.get("/api/v1/wave2/learner/evidence")
def current_evidence(
    learner_id: str,
    service: LongitudinalLearnerService = Depends(get_learner_model_service),
) -> dict:
    """Current admissible observed evidence with provenance links."""

    return service.current_evidence(learner_id).model_dump(mode="json")


__all__ = ["get_learner_model_service", "router"]
