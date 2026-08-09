"""LEARNER-FOUNDATION -- typed source-event / observed-evidence contracts.

ADR-03 (Memory Epistemic / Provenance / Invalidation Model, QUALIFIED
2026-08-09) concept adoption, bounded to the LEARNER foundation. This module
defines typed *record contracts* for interaction/source events and admitted
observed evidence, with provenance and evidence-admission status. It
deliberately does NOT implement L1/L2/L3 memory schemas or any memory
subsystem: those remain gated by the INT persistence ADR (ADR-03
implementation_gate; LEARNER capability program).

Binding sources:
- RD-D3-UD06-approved.json (O1 default / O2 gates; no proficiency/mastery/
  ability/learning-gain semantics from diagnostic_only).
- RD-D08-approved.json (exposure classes; never-expose list).
- RD-D09-approved-C1.json (persist_minimum: epistemic_status, rule_id,
  rule_version, source/provenance reference, effective state/version;
  append-only invalidation/retraction/supersession).
- WU-D diagnostic gating contract
  (docs/corpus-intelligence/l2/17_STAGE6_WU_D_DIAGNOSTIC_GATING_CONTRACT.md)
  sections 5/6/8: admissibility statuses, epistemic layers, provenance
  chain, input envelope.
- docs/architecture/writing-intelligence-platform/08_FEEDBACK_LEARNER_
  INTELLIGENCE.md sections 3/4: evidence-status and epistemic taxonomy.

Invariants enforced here:
- observed evidence != diagnostic inference != feedback recommendation !=
  learning outcome (epistemic layers stay distinct; downgrade-only).
- admission precedence INVALID -> UNAVAILABLE -> LIMITED (WU-D F14 / N6).
- provenance completeness is required before a record may be admitted.
- memory state is never mastery, proficiency, ability, or learning gain.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.schemas import utc_now
from app.shared.vocabularies import EpistemicStatus


# ---------------------------------------------------------------------------
# Evidence-admission status (WU-D section 5 / N6; exact corpus spellings)
# ---------------------------------------------------------------------------


class EvidenceAdmissionStatus(StrEnum):
    """Admissibility status of an artifact or evidence record (N6 section 2)."""

    ADMISSIBLE = "ADMISSIBLE"
    LIMITED = "LIMITED"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID = "INVALID"


ADMISSION_PRECEDENCE: tuple[EvidenceAdmissionStatus, ...] = (
    EvidenceAdmissionStatus.INVALID,
    EvidenceAdmissionStatus.UNAVAILABLE,
    EvidenceAdmissionStatus.LIMITED,
)


def effective_admission_status(
    statuses: Iterable[EvidenceAdmissionStatus],
) -> EvidenceAdmissionStatus:
    """Combine admission statuses under the N6 F14 precedence.

    INVALID is evaluated first, then UNAVAILABLE, then LIMITED; ADMISSIBLE is
    the fallback when every input is admissible.
    """

    for candidate in ADMISSION_PRECEDENCE:
        if any(status == candidate for status in statuses):
            return candidate
    return EvidenceAdmissionStatus.ADMISSIBLE


def admission_downgrade_allowed(
    current: EvidenceAdmissionStatus, target: EvidenceAdmissionStatus,
) -> bool:
    """Downgrade-only admission invariant (D-09; WU-D F14).

    ADMISSIBLE -> LIMITED -> UNAVAILABLE -> INVALID are downgrades; any
    upgrade requires new gate evidence and is not allowed here.
    """

    rank = {
        status: index
        for index, status in enumerate(
            (*ADMISSION_PRECEDENCE, EvidenceAdmissionStatus.ADMISSIBLE)
        )
    }
    return rank[target] <= rank[current]


# ---------------------------------------------------------------------------
# Provenance chain (WU-D G4: 7-field provenance; ADR-03 provenance edges)
# ---------------------------------------------------------------------------


class ProvenanceChain(BaseModel):
    """Provenance of one artifact/evidence record.

    Corpus-derived aggregates carry the full WU-D G4 chain
    (``corpus_aggregate=True``); learner-side records carry the minimum
    provenance fields. ``policy_version`` / ``model_version`` /
    ``config_version`` satisfy ADR-03's policy/model/config versioning
    requirement on the record level.
    """

    model_config = ConfigDict(extra="forbid")

    source_package: str = Field(min_length=1)
    manifest_hash: str = Field(min_length=1)
    feature_set_version: str | None = None
    reference_group_version: str | None = None
    distribution_version: str | None = None
    processing_version: str = Field(min_length=1)
    algorithm_version: str | None = None
    effective_n: int | None = Field(default=None, ge=0)
    availability: str = "available"

    @field_validator("availability")
    @classmethod
    def availability_vocabulary(cls, value: str) -> str:
        if value not in {"available", "limited", "unavailable"}:
            raise ValueError("availability must be available|limited|unavailable")
        return value


MINIMUM_PROVENANCE_FIELDS: tuple[str, ...] = (
    "source_package",
    "manifest_hash",
    "processing_version",
    "availability",
)

# WU-D G4: source package + manifest hash, FeatureSetVersion,
# ReferenceGroupVersion, DistributionVersion, processing/algorithm versions,
# effective N, availability.
CORPUS_AGGREGATE_PROVENANCE_FIELDS: tuple[str, ...] = (
    "source_package",
    "manifest_hash",
    "feature_set_version",
    "reference_group_version",
    "distribution_version",
    "processing_version",
    "algorithm_version",
    "effective_n",
    "availability",
)


class ProvenanceCompletenessResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    complete: bool
    missing: list[str]
    required: list[str]


def check_provenance_completeness(
    chain: ProvenanceChain, *, corpus_aggregate: bool = False,
) -> ProvenanceCompletenessResult:
    """Fail-closed provenance completeness check (WU-D G4).

    A missing mandatory field makes the chain incomplete; an incomplete
    chain cannot support admission or diagnostic computation.
    """

    required = (
        CORPUS_AGGREGATE_PROVENANCE_FIELDS if corpus_aggregate
        else MINIMUM_PROVENANCE_FIELDS
    )
    missing: list[str] = []
    for field in required:
        value = getattr(chain, field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)
    return ProvenanceCompletenessResult(
        complete=not missing, missing=missing, required=list(required),
    )


# ---------------------------------------------------------------------------
# Exposure class (D-08 / WU-D section 3; learner-side mirror)
# ---------------------------------------------------------------------------


class ExposureClass(StrEnum):
    """Exposure classes from the WU-D diagnostic gating contract (D-08)."""

    RESEARCH_ONLY = "research_only"
    DIAGNOSTIC_ONLY = "diagnostic_only"
    DISPLAYABLE = "displayable"
    HIDDEN = "hidden"
    UNAVAILABLE = "unavailable"


EXPOSURE_CLASSES: frozenset[str] = frozenset(cls.value for cls in ExposureClass)

# displayable is the only learner-facing class, and it requires the D-08
# opt-in path that does not exist yet (see exposure.py).
LEARNER_FACING_CLASSES: frozenset[str] = frozenset({ExposureClass.DISPLAYABLE.value})

# O1 default (RD-D3): research_only whenever qualification is incomplete.
DEFAULT_EXPOSURE_CLASS = ExposureClass.RESEARCH_ONLY


EPISTEMIC_LAYER_ORDER: tuple[EpistemicStatus, ...] = (
    EpistemicStatus.OBSERVED_DESCRIPTIVE,
    EpistemicStatus.GATED_INFERENCE,
    EpistemicStatus.RECOMMENDATION,
    EpistemicStatus.OUTCOME_CLAIM,
)


def epistemic_downgrade_allowed(
    current: EpistemicStatus, target: EpistemicStatus,
) -> bool:
    """D-09 downgrade-only display invariant for the four epistemic layers."""

    rank = {status: index for index, status in enumerate(EPISTEMIC_LAYER_ORDER)}
    return rank[target] <= rank[current]


# ---------------------------------------------------------------------------
# Source events and observed evidence (ADR-03 typed contracts)
# ---------------------------------------------------------------------------


class SourceEventType(StrEnum):
    """Learner evidence families (08 doc section 5; 04 doc section 3)."""

    SUBMISSION_EVIDENCE = "submission_evidence"
    REVISION_RESPONSE = "revision_response"
    PRACTICE_RESPONSE = "practice_response"
    WITHIN_TASK_OBSERVATION = "within_task_observation"
    LATER_TASK_OBSERVATION = "later_task_observation"
    RECURRING_PATTERN = "recurring_pattern"


class SourceEvent(BaseModel):
    """Typed interaction/source event (ADR-03).

    A source event is NOT yet evidence: it carries provenance fields
    (event id, time, actor, source, evidence-admission status,
    policy/model/config version) and becomes observed evidence only through
    an explicit admission step.
    """

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    event_type: SourceEventType
    occurred_at: datetime
    actor: str = Field(min_length=1)
    source: str = Field(min_length=1)
    policy_version: str | None = None
    model_version: str | None = None
    config_version: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    admission_status: EvidenceAdmissionStatus = EvidenceAdmissionStatus.ADMISSIBLE
    admission_reason: str | None = None
    recorded_at: datetime = Field(default_factory=utc_now)


class ObservedEvidence(BaseModel):
    """Admitted observed evidence (L0), typed and provenance-linked (ADR-03).

    The record keeps its epistemic layer, admission status, exposure class,
    and provenance chain attached so no consumer can re-derive them. It is
    distinct from diagnostic inference, feedback recommendation, and
    learning outcome by construction (``epistemic_status``).
    """

    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1)
    source_event_id: str = Field(min_length=1)
    evidence_type: str = Field(min_length=1)
    observed_at: datetime
    epistemic_status: EpistemicStatus = EpistemicStatus.OBSERVED_DESCRIPTIVE
    admission_status: EvidenceAdmissionStatus = EvidenceAdmissionStatus.ADMISSIBLE
    admission_reason: str | None = None
    exposure_class: ExposureClass = DEFAULT_EXPOSURE_CLASS
    provenance: ProvenanceChain
    value: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    recorded_at: datetime = Field(default_factory=utc_now)

    @field_validator("epistemic_status")
    @classmethod
    def observed_evidence_is_l0(cls, value: EpistemicStatus) -> EpistemicStatus:
        if value not in {
            EpistemicStatus.OBSERVED_DESCRIPTIVE,
            EpistemicStatus.GATED_INFERENCE,
        }:
            raise ValueError(
                "observed evidence records may only carry L0/L1 epistemic "
                "status; L2/L3 are separate typed contracts"
            )
        return value


class EvidenceAdmissionRecord(BaseModel):
    """Admissibility record (N6 section 2 / WU-D section 8 item 2).

    Every consumed artifact must carry one; LEARNER rejects artifacts without
    a record. Statuses use the N6 precedence; reasons are required for any
    non-ADMISSIBLE status.
    """

    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(min_length=1)
    status: EvidenceAdmissionStatus
    reasons: list[str] = Field(default_factory=list)
    provenance: ProvenanceChain
    record_version: str = "evidence-admissibility-record-v0.1.0"
    recorded_at: datetime = Field(default_factory=utc_now)

    @field_validator("reasons")
    @classmethod
    def reasons_required_for_non_admissible(cls, value: list[str], info: Any) -> list[str]:
        status = info.data.get("status")
        if status is not None and status != EvidenceAdmissionStatus.ADMISSIBLE and not value:
            raise ValueError("reasons are required when status is not ADMISSIBLE")
        return value


__all__ = [
    "ADMISSION_PRECEDENCE",
    "CORPUS_AGGREGATE_PROVENANCE_FIELDS",
    "DEFAULT_EXPOSURE_CLASS",
    "EPISTEMIC_LAYER_ORDER",
    "EXPOSURE_CLASSES",
    "EvidenceAdmissionRecord",
    "EvidenceAdmissionStatus",
    "ExposureClass",
    "LEARNER_FACING_CLASSES",
    "MINIMUM_PROVENANCE_FIELDS",
    "ObservedEvidence",
    "ProvenanceChain",
    "ProvenanceCompletenessResult",
    "SourceEvent",
    "SourceEventType",
    "admission_downgrade_allowed",
    "check_provenance_completeness",
    "effective_admission_status",
    "epistemic_downgrade_allowed",
]
