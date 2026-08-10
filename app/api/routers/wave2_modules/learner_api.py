"""Wave-2 Longitudinal Learner Model API (Goal PDW2-B-LEARNER-MODEL).

Router module under ``/api/v1/wave2/learner/`` exposing observation-only,
non-normative longitudinal views: observations, recurring difficulties,
strengths, stable observations, proficiency context (external anchors only)
and current evidence with provenance links. The CORE Wave-2 assembly
(``app.api.routers.wave2``) mounts this module's ``router`` at integration;
``wave2_modules/__init__.py`` is contributed by CORE, so this module stays
importable as a namespace package on the LEARNER branch.

Shared-repository consumption (F-1): when the composition root has wired a
CORE-composed shared wave2 store at ``request.app.state.wave2_repository``
(``SQLiteWave2Repository`` at integration), the dependency builds the
longitudinal service over a duck-typed adapter (``SharedObservationRepository``)
so learner views share ONE store with the revision and personalized routers.
The shared store owns the ``learning_observations`` family; LEARNER-only
families with no shared table yet (submission samples, evidence, revision
behavior, proficiency context) remain in a local in-memory store until a
shared contract exists. When the shared store is absent (standalone test
contexts), the dependency falls back to the branch-local in-memory service.
Test clients may still override the dependency with ``app.dependency_overrides``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.learner.evidence import ObservedEvidence
from app.learner.wave2.models import (
    ObservationRecord,
    ObservationType,
    ProficiencyContext,
    RevisionBehavior,
    SubmissionSample,
)
from app.learner.wave2.repository import InMemoryObservationRepository
from app.learner.wave2.services import LongitudinalLearnerService

router = APIRouter()

_DEFAULT_LEARNER_SERVICE = LongitudinalLearnerService(
    InMemoryObservationRepository()
)

_LEARNER_RECORD_PAYLOAD_KEY = "learner_observation_record_v1"


@dataclass
class _SharedLearningObservation:
    """Duck-typed learning-observation row accepted by the shared store.

    Attribute names match what the CORE ``SQLiteWave2Repository``
    ``save_learning_observation`` reads; no CORE-branch import is required
    so this module remains importable standalone on the LEARNER branch.
    """

    student_id: str
    observation_type: str
    evidence_refs: list[str]
    task_id: str | None
    context: dict[str, Any]
    occurrence_count: int
    first_observed_at: str | None
    last_observed_at: str | None
    recency: str
    revision_response: dict[str, Any]
    limitations: list[str]
    created_at: str | None = None


class SharedObservationRepository:
    """``ObservationRepository`` over the CORE-composed shared wave2 store.

    Consumes ``request.app.state.wave2_repository`` (a CORE
    ``SQLiteWave2Repository`` at integration) through its
    ``learning_observations`` family. LEARNER ``ObservationRecord`` payloads
    are preserved losslessly inside the shared row's free-form ``context``
    dict under a namespaced key, so the richer LEARNER record round-trips
    even though the shared store assigns its own generated row ids. Shared
    rows written without the LEARNER payload are not LEARNER-typed
    observations and are skipped (never surfaced as learner observations).

    LEARNER-only families with no shared table yet (submission samples,
    evidence, revision behavior, proficiency context) are served from a
    local in-memory store inside this adapter; they are NOT shared across
    routers until a shared contract exists.
    """

    _payload_key = _LEARNER_RECORD_PAYLOAD_KEY

    def __init__(self, shared_store: Any) -> None:
        self._shared = shared_store
        self._local = InMemoryObservationRepository()

    # ------------------------------------------------------------------
    # observations (delegated to the shared store)
    # ------------------------------------------------------------------

    def save_observation(self, record: ObservationRecord) -> None:
        occurrences = sorted(
            record.occurrences, key=lambda occurrence: occurrence.observed_at,
        )
        self._shared.save_learning_observation(_SharedLearningObservation(
            student_id=record.learner_id,
            observation_type=record.observation_type.value,
            evidence_refs=[occurrence.evidence_ref for occurrence in occurrences],
            task_id=None,
            context={self._payload_key: record.model_dump(mode="json")},
            occurrence_count=len(occurrences),
            first_observed_at=(
                occurrences[0].observed_at.isoformat() if occurrences else None
            ),
            last_observed_at=(
                occurrences[-1].observed_at.isoformat() if occurrences else None
            ),
            recency="unknown",
            revision_response={},
            limitations=list(record.limitations),
        ))

    def get_observation(
        self, learner_id: str, observation_id: str,
    ) -> ObservationRecord | None:
        for record in self.list_observations(learner_id):
            if record.observation_id == observation_id:
                return record
        return None

    def list_observations(
        self, learner_id: str,
        observation_type: ObservationType | None = None,
    ) -> list[ObservationRecord]:
        type_value = (
            observation_type.value if observation_type is not None else None
        )
        rows = self._shared.list_learning_observations(learner_id, type_value)
        records: list[ObservationRecord] = []
        for row in rows:
            translated = self._from_shared_row(row)
            if translated is not None:
                records.append(translated)
        return records

    @classmethod
    def _from_shared_row(cls, row: Any) -> ObservationRecord | None:
        context = getattr(row, "context", None) or {}
        payload = (
            context.get(cls._payload_key)
            if isinstance(context, dict) else None
        )
        if isinstance(payload, dict):
            return ObservationRecord.model_validate(payload)
        # Shared row written without the LEARNER payload: not a LEARNER-typed
        # observation; never reinterpreted or surfaced.
        return None

    # ------------------------------------------------------------------
    # LEARNER-only families (no shared table yet; local in-memory)
    # ------------------------------------------------------------------

    def save_submission_sample(self, sample: SubmissionSample) -> None:
        self._local.save_submission_sample(sample)

    def list_submission_samples(self, learner_id: str) -> list[SubmissionSample]:
        return self._local.list_submission_samples(learner_id)

    def save_evidence(self, learner_id: str, evidence: ObservedEvidence) -> None:
        self._local.save_evidence(learner_id, evidence)

    def get_evidence(
        self, learner_id: str, evidence_id: str,
    ) -> ObservedEvidence | None:
        return self._local.get_evidence(learner_id, evidence_id)

    def list_evidence(self, learner_id: str) -> list[ObservedEvidence]:
        return self._local.list_evidence(learner_id)

    def save_revision_behavior(self, behavior: RevisionBehavior) -> None:
        self._local.save_revision_behavior(behavior)

    def list_revision_behavior(
        self, learner_id: str, observation_id: str | None = None,
    ) -> list[RevisionBehavior]:
        return self._local.list_revision_behavior(
            learner_id, observation_id=observation_id,
        )

    def save_proficiency_context(self, context: ProficiencyContext) -> None:
        self._local.save_proficiency_context(context)

    def get_proficiency_context(
        self, learner_id: str,
    ) -> ProficiencyContext | None:
        return self._local.get_proficiency_context(learner_id)


def get_learner_model_service(request: Request) -> LongitudinalLearnerService:
    """Dependency: shared store when composed; local fallback otherwise.

    When the composition root has wired ``request.app.state.wave2_repository``
    (CORE-composed shared ``SQLiteWave2Repository``), the service is built
    over ``SharedObservationRepository`` so learner views consume the same
    store as the revision and personalized routers. When the shared store is
    absent (standalone test contexts), the branch-local in-memory service is
    returned.
    """

    shared_store = getattr(request.app.state, "wave2_repository", None)
    if shared_store is not None:
        return LongitudinalLearnerService(
            SharedObservationRepository(shared_store)
        )
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


__all__ = ["SharedObservationRepository", "get_learner_model_service", "router"]
