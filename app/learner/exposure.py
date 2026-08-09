"""WU-D exposure-class enforcement (CORPUS <-> LEARNER consumption).

Consumes the WU-D diagnostic gating contract exposure classes
(docs/corpus-intelligence/l2/17_STAGE6_WU_D_DIAGNOSTIC_GATING_CONTRACT.md
sections 3/6/7 and its machine mirror
data/wu_d_diagnostic_gating_contract.json):

- ``research_only`` is the O1 default (RD-D3); qualification incomplete,
  missing, or stale means O1 -- never inferred (F1/F2).
- ``diagnostic_only`` is a *computation* class entered ONLY when ALL O2
  gates G0-G7 hold with persisted, evidence-backed gate records (section 6;
  a missing or empty-evidence record is a failed gate).
- ``displayable`` is FAIL-CLOSED: no D-08 display-policy opt-in exists
  (``DISPLAY_POLICY_OPT_IN_EXISTS = False``), so any displayable resolution
  is rejected.
- ``unavailable`` is terminal for that artifact version (F3); no widening,
  no substitution.
- Epistemic layers permitted per class (section 5); downgrade-only (D-09).
- WU-D section 8 input-envelope checks (10 items) are enforced by
  ``ExposureEnforcer.enforce``.

The enforcer is pure policy logic: it makes no network, database, or UI
contact and writes nothing.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.schemas import utc_now
from app.shared.vocabularies import EpistemicStatus

from .evidence import (
    DEFAULT_EXPOSURE_CLASS,
    EvidenceAdmissionRecord,
    EvidenceAdmissionStatus,
    ExposureClass,
    ProvenanceChain,
    check_provenance_completeness,
)


# No D-08 display policy exists anywhere in the program: displayable is
# defined for the contract only (WU-D section 3 rule 3, section 9 item 3).
DISPLAY_POLICY_OPT_IN_EXISTS = False


class O2Gate(StrEnum):
    """O2 qualification gates G0-G7 (WU-D section 6)."""

    G0 = "G0"
    G1 = "G1"
    G2 = "G2"
    G3 = "G3"
    G4 = "G4"
    G5 = "G5"
    G6 = "G6"
    G7 = "G7"


O2_GATE_CRITERIA: dict[O2Gate, str] = {
    O2Gate.G0: (
        "named consumer + authorization: consuming capability (LEARNER "
        "foundation) declared; Goal authorization covers the diagnostic use"
    ),
    O2Gate.G1: (
        "permitted-use/licensing classification: NON-RECONSTRUCTIVE AGGREGATE; "
        "internal research-pipeline category permitted"
    ),
    O2Gate.G2: "non-reconstructive aggregate: statistics/distributions/numeric snapshots only",
    O2Gate.G3: "anonymization/privacy: P1-P9 satisfied",
    O2Gate.G4: "provenance completeness: 7-field provenance chain",
    O2Gate.G5: "evidence-admissibility: ADMISSIBLE or LIMITED-with-disclosure",
    O2Gate.G6: (
        "D-08 display-policy compatibility: exposure class assigned; canonical "
        "claim templates; no normative labels; banned vocabulary absent"
    ),
    O2Gate.G7: (
        "diagnostic-contract qualification: construct-registry entries; declared "
        "reference group; validated-measurement status; FeedbackPolicy compatibility"
    ),
}


class GateRecord(BaseModel):
    """Persisted, evidence-backed record for one O2 gate."""

    model_config = ConfigDict(extra="forbid")

    gate: O2Gate
    passed: bool
    evidence: list[str] = Field(min_length=1)
    record_version: str = "wu-d-gate-record-v0.1.0"
    recorded_at: datetime = Field(default_factory=utc_now)


class O2Qualification(BaseModel):
    """Result of evaluating all O2 gate records for one artifact version."""

    model_config = ConfigDict(extra="forbid")

    qualified: bool
    passed_gates: list[str] = Field(default_factory=list)
    failed_gates: list[str] = Field(default_factory=list)
    missing_gates: list[str] = Field(default_factory=list)
    qualification_version: str = "wu-d-o2-qualification-v0.1.0"
    qualified_at: datetime | None = None


def qualify_diagnostic_only(
    records: Mapping[O2Gate, GateRecord] | Iterable[GateRecord],
) -> O2Qualification:
    """Evaluate O2 qualification: ALL G0-G7 must hold with persisted evidence.

    Strict reading of WU-D section 6: "A governed aggregate MAY support
    diagnostic computation only when ALL of the following gates hold" (the
    G0-G7 list). An absent record or an empty-evidence record is a failed
    gate (fail closed, F2). Returns the machine-checkable qualification.
    """

    if isinstance(records, Mapping):
        by_gate = dict(records)
    else:
        by_gate = {record.gate: record for record in records}
    missing = [gate.value for gate in O2Gate if gate not in by_gate]
    failed = [
        gate.value
        for gate, record in by_gate.items()
        if not record.passed or not record.evidence
    ]
    passed = [
        gate.value
        for gate in O2Gate
        if gate in by_gate and by_gate[gate].passed and by_gate[gate].evidence
    ]
    qualified = not missing and not failed
    return O2Qualification(
        qualified=qualified,
        passed_gates=sorted(passed),
        failed_gates=sorted(failed),
        missing_gates=sorted(missing),
        qualified_at=utc_now() if qualified else None,
    )


EPISTEMIC_LAYER_PERMISSIONS: dict[ExposureClass, frozenset[EpistemicStatus]] = {
    ExposureClass.RESEARCH_ONLY: frozenset({
        EpistemicStatus.OBSERVED_DESCRIPTIVE,
        EpistemicStatus.GATED_INFERENCE,
    }),
    ExposureClass.DIAGNOSTIC_ONLY: frozenset({
        EpistemicStatus.OBSERVED_DESCRIPTIVE,
        EpistemicStatus.GATED_INFERENCE,
    }),
    ExposureClass.DISPLAYABLE: frozenset({EpistemicStatus.OBSERVED_DESCRIPTIVE}),
    ExposureClass.HIDDEN: frozenset({
        EpistemicStatus.OBSERVED_DESCRIPTIVE,
        EpistemicStatus.GATED_INFERENCE,
    }),
    ExposureClass.UNAVAILABLE: frozenset(),
}


def permitted_layers(exposure_class: ExposureClass) -> frozenset[EpistemicStatus]:
    return EPISTEMIC_LAYER_PERMISSIONS[exposure_class]


def layer_permitted(exposure_class: ExposureClass, status: EpistemicStatus) -> bool:
    """WU-D section 5: which epistemic layers may ride on which exposure."""

    return status in EPISTEMIC_LAYER_PERMISSIONS[exposure_class]


def resolve_displayable(display_policy_opt_in: bool = DISPLAY_POLICY_OPT_IN_EXISTS) -> ExposureClass | None:
    """Displayable resolution is FAIL-CLOSED.

    Without the D-08 opt-in (Researcher decision + display policy +
    licensing/anonymization gate) the class never resolves; the caller must
    treat ``None`` as "not displayable".
    """

    if display_policy_opt_in:
        return ExposureClass.DISPLAYABLE
    return None


class ExposureEnvelope(BaseModel):
    """WU-D section 8 input envelope (machine-checkable, item 1)."""

    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(min_length=1)
    artifact_version: str = Field(min_length=1)
    stated_exposure_class: ExposureClass | None = None
    learner_exposure: str = "research_only"
    admissibility_record: EvidenceAdmissionRecord | None = None
    epistemic_status: EpistemicStatus = EpistemicStatus.OBSERVED_DESCRIPTIVE
    feature_set_version: str | None = None
    required_feature_set_version: str | None = None
    provenance: ProvenanceChain | None = None
    n_effective: int | None = Field(default=None, ge=0)
    n_raw: int | None = Field(default=None, ge=0)
    complete_case_n: int | None = Field(default=None, ge=0)
    missingness_flags: list[str] = Field(default_factory=list)
    unavailable_reason: str | None = None


class ExposureEnforcementResult(BaseModel):
    """Machine-checkable exposure decision for one artifact/result."""

    model_config = ConfigDict(extra="forbid")

    artifact_id: str
    exposure_class: ExposureClass
    learner_exposure: str
    diagnostic_eligible: bool
    reject: bool
    reasons: list[str]


class ExposureEnforcer:
    """Fail-closed exposure enforcement over the WU-D input envelope.

    ``known_artifact_ids`` optionally bounds consumption to registered
    artifacts (WU-D F3/F5); unknown artifacts resolve to ``unavailable``.
    ``corpus_minimum_effective_n`` defaults to the min-N = 30 eligibility
    floor (WU-D N10); below-floor aggregates never support diagnostic
    computation.
    """

    def __init__(
        self,
        *,
        known_artifact_ids: Any | None = None,
        corpus_minimum_effective_n: int = 30,
    ) -> None:
        self.known_artifact_ids = known_artifact_ids
        self.corpus_minimum_effective_n = corpus_minimum_effective_n

    def enforce(
        self,
        envelope: ExposureEnvelope,
        *,
        gate_records: Iterable[GateRecord] | None = None,
    ) -> ExposureEnforcementResult:
        """Resolve the exposure class and consumption decision.

        Order: registry/known-artifact check (F3), admissibility record
        presence and status (section 8 item 2), FeatureSetVersion match (F4),
        O1 default resolution (F1/F2), O2 qualification, stated-class
        downgrade-only, displayable fail-close, layer compatibility, and the
        min-N diagnostic floor.
        """

        reasons: list[str] = []

        # F3: unknown artifact/version -> unavailable, never fabricated.
        if self.known_artifact_ids is not None and envelope.artifact_id not in self.known_artifact_ids:
            return ExposureEnforcementResult(
                artifact_id=envelope.artifact_id,
                exposure_class=ExposureClass.UNAVAILABLE,
                learner_exposure="research_only",
                diagnostic_eligible=False,
                reject=True,
                reasons=["F3: unknown artifact; exposure unavailable (no widening)"],
            )

        # Section 8 item 2: LEARNER must reject artifacts without a record.
        record = envelope.admissibility_record
        if record is None:
            return ExposureEnforcementResult(
                artifact_id=envelope.artifact_id,
                exposure_class=ExposureClass.UNAVAILABLE,
                learner_exposure="research_only",
                diagnostic_eligible=False,
                reject=True,
                reasons=["F2: no admissibility record; artifact must be rejected"],
            )
        if record.status == EvidenceAdmissionStatus.INVALID:
            return ExposureEnforcementResult(
                artifact_id=envelope.artifact_id,
                exposure_class=ExposureClass.UNAVAILABLE,
                learner_exposure="research_only",
                diagnostic_eligible=False,
                reject=True,
                reasons=[f"F6/N6: INVALID admissibility record: {record.reasons}"],
            )
        if record.status == EvidenceAdmissionStatus.UNAVAILABLE:
            return ExposureEnforcementResult(
                artifact_id=envelope.artifact_id,
                exposure_class=ExposureClass.UNAVAILABLE,
                learner_exposure="research_only",
                diagnostic_eligible=False,
                reject=True,
                reasons=[f"N6: UNAVAILABLE record is terminal: {record.reasons}"],
            )
        if record.status == EvidenceAdmissionStatus.LIMITED:
            reasons.append("N6: LIMITED record; disclosure and limitations carried")

        # F4: FeatureSetVersion mismatch is UNAVAILABLE, never best-effort.
        if (
            envelope.feature_set_version is not None
            and envelope.required_feature_set_version is not None
            and envelope.feature_set_version != envelope.required_feature_set_version
        ):
            return ExposureEnforcementResult(
                artifact_id=envelope.artifact_id,
                exposure_class=ExposureClass.UNAVAILABLE,
                learner_exposure="research_only",
                diagnostic_eligible=False,
                reject=True,
                reasons=[
                    "F4: FeatureSetVersion mismatch; comparison UNAVAILABLE "
                    "(never best-effort comparable)",
                ],
            )

        # O1 default (F1/F2): research_only unless all O2 gates hold.
        exposure = DEFAULT_EXPOSURE_CLASS
        diagnostic_eligible = False
        if gate_records is None:
            reasons.append("F2: no O2 gate records; O1 research_only default")
        else:
            qualification = qualify_diagnostic_only(gate_records)
            if qualification.qualified:
                exposure = ExposureClass.DIAGNOSTIC_ONLY
                diagnostic_eligible = True
                reasons.append("O2: ALL gates G0-G7 hold; diagnostic_only computation class")
            else:
                reasons.append(
                    "F2: O2 qualification incomplete "
                    f"(missing={qualification.missing_gates}, failed={qualification.failed_gates}); "
                    "O1 research_only default"
                )

        # Stated class may never be higher than the computed class (section 8
        # item 1: consumer may not assume a class the record does not state).
        stated = envelope.stated_exposure_class
        if stated is not None:
            if stated == ExposureClass.DISPLAYABLE:
                if not DISPLAY_POLICY_OPT_IN_EXISTS:
                    return ExposureEnforcementResult(
                        artifact_id=envelope.artifact_id,
                        exposure_class=ExposureClass.UNAVAILABLE,
                        learner_exposure="research_only",
                        diagnostic_eligible=False,
                        reject=True,
                        reasons=[
                            "F9/D-08: displayable FAIL-CLOSED; no display-policy "
                            "opt-in exists",
                        ],
                    )
            elif stated == ExposureClass.UNAVAILABLE:
                return ExposureEnforcementResult(
                    artifact_id=envelope.artifact_id,
                    exposure_class=ExposureClass.UNAVAILABLE,
                    learner_exposure="research_only",
                    diagnostic_eligible=False,
                    reject=True,
                    reasons=["F3: stated unavailable is terminal; no widening"],
                )
            elif stated not in {exposure, ExposureClass.HIDDEN}:
                # Never upgrade; silently downgrade to the computed class.
                reasons.append(
                    f"stated exposure {stated.value} exceeds computed {exposure.value}; "
                    "downgraded (D-09 downgrade-only)"
                )

        # Section 5: epistemic layer must be permitted for the exposure class.
        if not layer_permitted(exposure, envelope.epistemic_status):
            return ExposureEnforcementResult(
                artifact_id=envelope.artifact_id,
                exposure_class=ExposureClass.UNAVAILABLE,
                learner_exposure="research_only",
                diagnostic_eligible=False,
                reject=True,
                reasons=[
                    f"F7/N6: epistemic layer {envelope.epistemic_status.value} not "
                    f"permitted for {exposure.value}",
                ],
            )

        # WU-D G4/N10: below-floor aggregates never support diagnostic
        # computation (missingness never imputed, F15).
        if diagnostic_eligible and envelope.n_effective is not None:
            if envelope.n_effective < self.corpus_minimum_effective_n:
                diagnostic_eligible = False
                exposure = DEFAULT_EXPOSURE_CLASS
                reasons.append(
                    f"N10/F15: n_effective={envelope.n_effective} below the "
                    f"min-N={self.corpus_minimum_effective_n} eligibility floor; "
                    "not eligible for diagnostic computation"
                )

        return ExposureEnforcementResult(
            artifact_id=envelope.artifact_id,
            exposure_class=exposure,
            learner_exposure="research_only" if exposure != ExposureClass.DISPLAYABLE else "student",
            diagnostic_eligible=diagnostic_eligible,
            reject=False,
            reasons=reasons,
        )


def check_envelope_provenance(
    envelope: ExposureEnvelope, *, corpus_aggregate: bool = True,
) -> list[str]:
    """WU-D section 8 item 8: provenance-chain completeness as envelope reasons."""

    if envelope.provenance is None:
        return ["G4: provenance chain missing"]
    result = check_provenance_completeness(envelope.provenance, corpus_aggregate=corpus_aggregate)
    if not result.complete:
        return [f"G4: provenance incomplete; missing={result.missing}"]
    return []


__all__ = [
    "DISPLAY_POLICY_OPT_IN_EXISTS",
    "EPISTEMIC_LAYER_PERMISSIONS",
    "ExposureEnforcementResult",
    "ExposureEnforcer",
    "ExposureEnvelope",
    "GateRecord",
    "O2Gate",
    "O2Qualification",
    "O2_GATE_CRITERIA",
    "check_envelope_provenance",
    "layer_permitted",
    "permitted_layers",
    "qualify_diagnostic_only",
    "resolve_displayable",
]
