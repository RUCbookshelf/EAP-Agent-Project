"""Practice provenance records (LEARNER-owned, ADR-03 provenance concept).

Practice activity records are provenance-tracked *activity* records: practice
completion remains activity unless a validated measurement contract states
otherwise (frozen contract; 08 doc section 5; practice schemas
``CompletionStatus``). The record type structurally cannot carry an outcome
claim: ``outcome_claim`` is the literal ``"none"``, and validation runs the
no-normative-claims scanner over every string field.

This module defines record contracts and validation only. No table, column,
or repository is created here: persistence is routed through the migration
gate (see docs/learner/LEARNER_FOUNDATION_PERSISTENCE_DESIGN_NOTE.md).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.schemas import utc_now

from .evidence import EvidenceAdmissionStatus
from .normative import NormativeClaimsScanner


PRACTICE_ACTIVITY_LIMITATION = (
    "Practice completion is activity only; it does not establish mastery, "
    "proficiency, ability, or learning gain."
)


class PracticeActivityStatus(StrEnum):
    """Activity statuses only; completion never implies mastery."""

    COMPLETED = "completed"
    INCOMPLETE = "incomplete"
    INVALID = "invalid"
    NOT_ATTEMPTED = "not_attempted"
    ABANDONED = "abandoned"


REQUIRED_PRACTICE_PROVENANCE_FIELDS: tuple[str, ...] = (
    "record_id",
    "student_id",
    "practice_target_id",
    "exercise_id",
    "exercise_version",
    "activity_status",
    "occurred_at",
)


class PracticeProvenanceRecord(BaseModel):
    """One provenance-tracked practice activity record (ADR-03 fields)."""

    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(min_length=1)
    student_id: str = Field(min_length=1)
    practice_target_id: str = Field(min_length=1)
    exercise_id: str = Field(min_length=1)
    exercise_version: str = Field(min_length=1)
    attempt_id: str | None = None
    evaluation_id: str | None = None
    evaluator_version: str | None = None
    activity_status: PracticeActivityStatus
    occurred_at: datetime
    actor: str = "learner"
    source: str = "practice_attempt"
    policy_version: str | None = None
    model_version: str | None = None
    config_version: str | None = None
    outcome_claim: Literal["none"] = "none"
    measurement_contract: str | None = None
    admission_status: EvidenceAdmissionStatus = EvidenceAdmissionStatus.ADMISSIBLE
    admission_reason: str | None = None
    limitations: list[str] = Field(default_factory=lambda: [PRACTICE_ACTIVITY_LIMITATION])
    recorded_at: datetime = Field(default_factory=utc_now)


class PracticeProvenanceValidation(BaseModel):
    """Machine-checkable validation result for one provenance record."""

    model_config = ConfigDict(extra="forbid")

    record_id: str
    complete: bool
    missing: list[str]
    findings: list[str]
    violations: list[str]


def validate_practice_provenance(
    record: PracticeProvenanceRecord,
    *,
    scanner: NormativeClaimsScanner | None = None,
) -> PracticeProvenanceValidation:
    """Fail-closed validation of one practice provenance record.

    Checks completeness of the mandatory provenance fields, the
    activity-only invariant (no measurement contract means activity-only
    language is required), and the no-normative-claims scan over all string
    fields. Prohibition text (such as the activity-only limitation itself)
    is exempted line-by-line per the WU-D F1-resolution convention
    (documentation mode); any assertion line without a prohibition marker is
    still flagged.
    """

    scanner = scanner or NormativeClaimsScanner()
    missing = [
        field for field in REQUIRED_PRACTICE_PROVENANCE_FIELDS
        if getattr(record, field) in (None, "")
    ]
    findings: list[str] = []
    if record.measurement_contract is None:
        findings.append("activity-only: no validated measurement contract applies")
    else:
        findings.append(
            f"measurement contract {record.measurement_contract} governs "
            "interpretation; activity semantics remain until validated"
        )
    violations = [
        f"{v.location}: {v.term}"
        for v in scanner.scan_pydantic(record, documentation=True)
    ]
    return PracticeProvenanceValidation(
        record_id=record.record_id,
        complete=not missing,
        missing=missing,
        findings=findings,
        violations=violations,
    )


__all__ = [
    "PRACTICE_ACTIVITY_LIMITATION",
    "PracticeActivityStatus",
    "PracticeProvenanceRecord",
    "PracticeProvenanceValidation",
    "REQUIRED_PRACTICE_PROVENANCE_FIELDS",
    "validate_practice_provenance",
]
