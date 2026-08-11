"""Locally-defined repository protocol for longitudinal learner evidence.

Goal PDW2-B-LEARNER-MODEL: the protocol is defined here in the LEARNER
domain and must NOT import CORE-branch-only persistence
(``app.infrastructure.sqlite.repositories.wave2`` or migration-14 DDL; those
land at integration). Two implementations ship with this module set:
``InMemoryObservationRepository`` (tests and branch-local default) and
``SqliteObservationRepository`` (self-contained TEST-ONLY database).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.learner.evidence import ObservedEvidence
from app.learner.wave2.models import (
    ObservationRecord,
    ObservationType,
    ProficiencyContext,
    RevisionBehavior,
    SubmissionSample,
)


@runtime_checkable
class ObservationRepository(Protocol):
    """Persistence boundary for longitudinal learner observations."""

    def save_observation(self, record: ObservationRecord) -> None: ...

    def get_observation(
        self, learner_id: str, observation_id: str,
    ) -> ObservationRecord | None: ...

    def list_observations(
        self, learner_id: str,
        observation_type: ObservationType | None = None,
    ) -> list[ObservationRecord]: ...

    def save_submission_sample(self, sample: SubmissionSample) -> None: ...

    def list_submission_samples(self, learner_id: str) -> list[SubmissionSample]: ...

    def save_evidence(self, learner_id: str, evidence: ObservedEvidence) -> None: ...

    def get_evidence(
        self, learner_id: str, evidence_id: str,
    ) -> ObservedEvidence | None: ...

    def list_evidence(self, learner_id: str) -> list[ObservedEvidence]: ...

    def save_revision_behavior(self, behavior: RevisionBehavior) -> None: ...

    def list_revision_behavior(
        self, learner_id: str, observation_id: str | None = None,
    ) -> list[RevisionBehavior]: ...

    def save_proficiency_context(self, context: ProficiencyContext) -> None: ...

    def get_proficiency_context(self, learner_id: str) -> ProficiencyContext | None: ...


class InMemoryObservationRepository:
    """In-memory implementation (tests and branch-local default)."""

    def __init__(self) -> None:
        self._observations: dict[tuple[str, str], ObservationRecord] = {}
        self._samples: dict[tuple[str, str], SubmissionSample] = {}
        self._evidence: dict[tuple[str, str], ObservedEvidence] = {}
        self._behaviors: dict[tuple[str, str], RevisionBehavior] = {}
        self._contexts: dict[str, ProficiencyContext] = {}

    def save_observation(self, record: ObservationRecord) -> None:
        self._observations[(record.learner_id, record.observation_id)] = record

    def get_observation(
        self, learner_id: str, observation_id: str,
    ) -> ObservationRecord | None:
        return self._observations.get((learner_id, observation_id))

    def list_observations(
        self, learner_id: str,
        observation_type: ObservationType | None = None,
    ) -> list[ObservationRecord]:
        records = [
            record
            for (learner, _), record in self._observations.items()
            if learner == learner_id
        ]
        if observation_type is not None:
            records = [
                record for record in records
                if record.observation_type is observation_type
            ]
        return records

    def save_submission_sample(self, sample: SubmissionSample) -> None:
        self._samples[(sample.learner_id, sample.submission_id)] = sample

    def list_submission_samples(self, learner_id: str) -> list[SubmissionSample]:
        samples = [
            sample
            for (learner, _), sample in self._samples.items()
            if learner == learner_id
        ]
        return sorted(samples, key=lambda sample: sample.submitted_at)

    def save_evidence(self, learner_id: str, evidence: ObservedEvidence) -> None:
        self._evidence[(learner_id, evidence.evidence_id)] = evidence

    def get_evidence(
        self, learner_id: str, evidence_id: str,
    ) -> ObservedEvidence | None:
        return self._evidence.get((learner_id, evidence_id))

    def list_evidence(self, learner_id: str) -> list[ObservedEvidence]:
        return [
            evidence
            for (learner, _), evidence in self._evidence.items()
            if learner == learner_id
        ]

    def save_revision_behavior(self, behavior: RevisionBehavior) -> None:
        self._behaviors[(behavior.learner_id, behavior.behavior_id)] = behavior

    def list_revision_behavior(
        self, learner_id: str, observation_id: str | None = None,
    ) -> list[RevisionBehavior]:
        behaviors = [
            behavior
            for (learner, _), behavior in self._behaviors.items()
            if learner == learner_id
        ]
        if observation_id is not None:
            behaviors = [
                behavior for behavior in behaviors
                if behavior.observation_id == observation_id
            ]
        return sorted(behaviors, key=lambda behavior: behavior.occurred_at)

    def save_proficiency_context(self, context: ProficiencyContext) -> None:
        self._contexts[context.learner_id] = context

    def get_proficiency_context(self, learner_id: str) -> ProficiencyContext | None:
        return self._contexts.get(learner_id)


__all__ = ["InMemoryObservationRepository", "ObservationRepository"]
