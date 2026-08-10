"""Shared record builders for Wave-2 longitudinal learner model tests.

New-file test support only (Goal PDW2-B-LEARNER-MODEL). Builders construct
the typed longitudinal records used by the red/green wave2 tests.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.learner.evidence import (
    EvidenceAdmissionStatus,
    ExposureClass,
    ObservedEvidence,
    ProvenanceChain,
)
from app.learner.wave2.models import (
    ExternalAnchor,
    ExternalAnchorSystem,
    ObservationRecord,
    ObservationType,
    OccurrenceEntry,
    ProficiencyContext,
    RevisionBehavior,
    RevisionResponseState,
    SubmissionSample,
)


def utc(year: int, month: int, day: int, hour: int = 9, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


DEMO_MANIFEST = "DEMO-MANIFEST-001"


def make_provenance(processing_version: str = "wave2-demo-v1") -> ProvenanceChain:
    return ProvenanceChain(
        source_package="learner-synthetic-wave2-demo",
        manifest_hash=DEMO_MANIFEST,
        processing_version=processing_version,
        availability="available",
    )


def make_evidence(
    evidence_id: str,
    learner_id: str,
    observed_at: datetime,
    *,
    admission_status: EvidenceAdmissionStatus = EvidenceAdmissionStatus.ADMISSIBLE,
    value: dict | None = None,
) -> ObservedEvidence:
    return ObservedEvidence(
        evidence_id=evidence_id,
        source_event_id=f"EVT-{evidence_id}",
        evidence_type="wave2_observation_occurrence",
        observed_at=observed_at,
        admission_status=admission_status,
        exposure_class=ExposureClass.RESEARCH_ONLY,
        provenance=make_provenance(),
        value=value or {"kind": "occurrence"},
    )


def make_observation(
    observation_id: str,
    learner_id: str,
    observation_type: ObservationType,
    code: str,
    label: str,
    occurrences: list[OccurrenceEntry],
) -> ObservationRecord:
    return ObservationRecord(
        observation_id=observation_id,
        learner_id=learner_id,
        observation_type=observation_type,
        code=code,
        label=label,
        occurrences=occurrences,
    )


def make_occurrence(
    occurrence_id: str,
    evidence_ref: str,
    task_context: str,
    observed_at: datetime,
    *,
    qualified: bool = True,
) -> OccurrenceEntry:
    return OccurrenceEntry(
        occurrence_id=occurrence_id,
        evidence_ref=evidence_ref,
        task_context=task_context,
        observed_at=observed_at,
        qualified=qualified,
        qualification_reason=(
            "declared comparable task conditions" if qualified
            else "declared non-comparable task conditions"
        ),
    )


def make_sample(
    submission_id: str,
    learner_id: str,
    task_context: str,
    submitted_at: datetime,
    *,
    qualified: bool = True,
) -> SubmissionSample:
    return SubmissionSample(
        submission_id=submission_id,
        learner_id=learner_id,
        task_context=task_context,
        submitted_at=submitted_at,
        draft_stage="first draft",
        qualified=qualified,
        qualification_reason=(
            "declared comparable task conditions" if qualified
            else "declared non-comparable task conditions"
        ),
    )


def make_behavior(
    behavior_id: str,
    learner_id: str,
    observation_id: str,
    revision_event_id: str,
    state: RevisionResponseState,
    occurred_at: datetime,
) -> RevisionBehavior:
    return RevisionBehavior(
        behavior_id=behavior_id,
        learner_id=learner_id,
        observation_id=observation_id,
        revision_event_id=revision_event_id,
        state=state,
        occurred_at=occurred_at,
        evidence_refs=[f"E-{behavior_id}"],
    )


def make_anchor(
    anchor_id: str,
    system: ExternalAnchorSystem,
    declared_value: str,
    recorded_at: datetime,
    *,
    source: str = "learner_declared",
) -> ExternalAnchor:
    return ExternalAnchor(
        anchor_id=anchor_id,
        system=system,
        declared_value=declared_value,
        source=source,
        recorded_at=recorded_at,
    )


def make_proficiency_context(
    learner_id: str, anchors: list[ExternalAnchor] | None = None,
) -> ProficiencyContext:
    return ProficiencyContext(
        learner_id=learner_id,
        anchors=anchors or [],
    )
