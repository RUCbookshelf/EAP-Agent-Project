"""Feedback-policy application scaffolding (D-03; 08 doc section 2).

Additive scaffolding only. The live L2 feedback pipeline keeps its current
implicit policy; this module formalizes the minimum FeedbackPolicy interface
as a default instance with zero behavior change (no composition-root, API,
persistence, or UI wiring). It consumes WU-D-gated evidence envelopes
(app.learner.exposure.ExposureEnvelope) and produces L2 recommendations with
provenance (policy/model/config versions, evidence ids, time).

Hard rules enforced here:
- observed evidence (L0) -> gated inference (L1) -> recommendation (L2)
  layers stay distinct; the application never emits outcome claims (L3).
- no proficiency/mastery/ability/learning-gain/CEFR wording (WU-D F11); every
  recommendation is scanned by the normative scanner before it is returned.
- no-priority / insufficient-evidence states are explicit and never
  fabricated (WU-D F15; D-03 semantics).
- feedback is never attributed to outcomes (A-23).
- displayable exposure never enters the policy application (fail-closed).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.schemas import utc_now
from app.shared.vocabularies import EpistemicStatus

from .evidence import EvidenceAdmissionStatus, ObservedEvidence
from .exposure import ExposureClass, ExposureEnforcer, ExposureEnvelope
from .normative import NormativeClaimsScanner


NO_CLAIM_LIMITATION = (
    "This recommendation is a workflow priority computed from observed "
    "evidence; it is not a proficiency, mastery, ability, or learning-gain "
    "claim (WU-D F11), and it is not attributed to any learning outcome (A-23)."
)


class FeedbackPolicy(BaseModel):
    """Minimum FeedbackPolicy contract (D-03 / 08 doc section 2)."""

    model_config = ConfigDict(extra="forbid")

    policy_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    gate_rules: list[str] = Field(min_length=1)
    priority_limit: int = Field(ge=1, le=5)
    evidence_eligibility: list[str] = Field(min_length=1)
    no_priority_semantics: str = Field(min_length=1)
    insufficient_evidence_semantics: str = Field(min_length=1)
    claims_constraints: list[str] = Field(min_length=1)
    domain_pre_gate_hooks: list[str] = Field(default_factory=list)


class FeedbackRecommendation(BaseModel):
    """One L2 recommendation with provenance (08 doc section 4)."""

    model_config = ConfigDict(extra="forbid")

    recommendation_id: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    priority: int = Field(ge=1)
    statement: str = Field(min_length=1)
    epistemic_status: EpistemicStatus = EpistemicStatus.RECOMMENDATION
    limitations: list[str] = Field(default_factory=list)


class FeedbackPolicyApplication(BaseModel):
    """Result of applying one policy to one evidence envelope."""

    model_config = ConfigDict(extra="forbid")

    application_id: str = Field(min_length=1)
    policy_id: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    status: Literal["applied", "no_priority", "insufficient_evidence", "unavailable"]
    evidence_ids: list[str] = Field(default_factory=list)
    recommendations: list[FeedbackRecommendation] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    provenance: dict[str, str] = Field(default_factory=dict)
    applied_at: datetime = Field(default_factory=utc_now)


def default_feedback_policy() -> FeedbackPolicy:
    """Default policy instance: current implicit policy, zero behavior change.

    priority_limit=2 mirrors the frozen two-priority product limit; gate
    rules reference the current Diagnostic Gate version (practice schemas);
    evidence eligibility mirrors the verified-evidence rule; no-priority and
    insufficient-evidence semantics follow D-03.
    """

    return FeedbackPolicy(
        policy_id="feedback-policy-v0.1.0",
        version="0.1.0",
        gate_rules=["diagnostic-v0.6.1"],
        priority_limit=2,
        evidence_eligibility=[
            "admission status ADMISSIBLE or LIMITED-with-disclosure",
            "evidence status verified",
            "epistemic layer L0 or L1 only",
            "same FeatureSetVersion on both sides",
            "provenance chain complete",
        ],
        no_priority_semantics=(
            "No priority is selected when no candidate clears the gate; "
            "absence of a priority is not evidence of absence of a problem."
        ),
        insufficient_evidence_semantics=(
            "Insufficient evidence: the requested judgment is unavailable; "
            "nothing is fabricated or substituted (WU-D F15)."
        ),
        claims_constraints=[
            "No proficiency/mastery/ability/learning-gain/CEFR claims (WU-D F11).",
            "No feedback-to-outcome attribution (A-23).",
            "Recommendations are workflow rankings only (canonical templates).",
            "HISTORY_LIMITATION accompanies all longitudinal output (F14).",
        ],
        domain_pre_gate_hooks=[],
    )


def _recommendation_statement(
    policy: FeedbackPolicy, priority: int, evidence_ids: list[str],
) -> str:
    ids = ", ".join(evidence_ids)
    return (
        f"Priority {priority}: revise the targeted feature; evidence ids: "
        f"{ids}; policy {policy.policy_id}@{policy.version} "
        "(workflow ranking only, not an ability judgment)."
    )


class FeedbackPolicyService:
    """Apply a FeedbackPolicy over WU-D-gated evidence envelopes."""

    def __init__(
        self,
        policy: FeedbackPolicy | None = None,
        scanner: NormativeClaimsScanner | None = None,
    ) -> None:
        self.policy = policy or default_feedback_policy()
        self.scanner = scanner or NormativeClaimsScanner()

    def apply(
        self,
        envelope: ExposureEnvelope,
        candidates: list[ObservedEvidence],
        *,
        application_id: str = "FA000001",
        gate_records: Any = None,
    ) -> FeedbackPolicyApplication:
        """Apply the policy and return L2 recommendations (or explicit states).

        The envelope must have been exposure-enforced by the caller (or
        ``gate_records`` is passed through so this service re-checks O2).
        """

        enforcement = ExposureEnforcer().enforce(envelope, gate_records=gate_records)
        if enforcement.reject or enforcement.exposure_class in {
            ExposureClass.DISPLAYABLE,
            ExposureClass.UNAVAILABLE,
        }:
            return FeedbackPolicyApplication(
                application_id=application_id,
                policy_id=self.policy.policy_id,
                policy_version=self.policy.version,
                status="unavailable",
                limitations=[
                    "Policy application unavailable: exposure enforcement "
                    f"rejected the envelope ({enforcement.reasons})",
                ],
                provenance={"enforcement_exposure": enforcement.exposure_class.value},
            )

        eligible: list[ObservedEvidence] = []
        for candidate in candidates:
            if candidate.admission_status not in {
                EvidenceAdmissionStatus.ADMISSIBLE,
                EvidenceAdmissionStatus.LIMITED,
            }:
                continue
            if candidate.epistemic_status not in {
                EpistemicStatus.OBSERVED_DESCRIPTIVE,
                EpistemicStatus.GATED_INFERENCE,
            }:
                continue
            eligible.append(candidate)

        if not eligible:
            return FeedbackPolicyApplication(
                application_id=application_id,
                policy_id=self.policy.policy_id,
                policy_version=self.policy.version,
                status="insufficient_evidence",
                limitations=[self.policy.insufficient_evidence_semantics],
                provenance={"envelope_artifact": envelope.artifact_id},
            )

        # A gate rule ("selected priority" semantics) may still select none.
        selected = eligible[: self.policy.priority_limit]
        if not selected:
            return FeedbackPolicyApplication(
                application_id=application_id,
                policy_id=self.policy.policy_id,
                policy_version=self.policy.version,
                status="no_priority",
                evidence_ids=[item.evidence_id for item in eligible],
                limitations=[self.policy.no_priority_semantics],
                provenance={"envelope_artifact": envelope.artifact_id},
            )

        recommendations: list[FeedbackRecommendation] = []
        for priority, item in enumerate(selected, 1):
            statement = _recommendation_statement(
                self.policy, priority, [item.evidence_id],
            )
            violations = self.scanner.scan_text(statement)
            if violations:
                # Structural tripwire: a recommendation that fails the
                # normative scan must never be returned.
                raise ValueError(
                    "recommendation failed no-normative-claims scan: "
                    + "; ".join(v.term for v in violations)
                )
            recommendations.append(FeedbackRecommendation(
                recommendation_id=f"{application_id}-R{priority:02d}",
                evidence_ids=[item.evidence_id],
                priority=priority,
                statement=statement,
                limitations=[NO_CLAIM_LIMITATION],
            ))

        return FeedbackPolicyApplication(
            application_id=application_id,
            policy_id=self.policy.policy_id,
            policy_version=self.policy.version,
            status="applied",
            evidence_ids=[item.evidence_id for item in selected],
            recommendations=recommendations,
            limitations=[
                "Recommendations are workflow priorities only; completion of "
                "any practice activity remains activity, not learning outcome.",
            ],
            provenance={
                "envelope_artifact": envelope.artifact_id,
                "policy_id": self.policy.policy_id,
                "policy_version": self.policy.version,
                "gate_rules": ",".join(self.policy.gate_rules),
                "applied_at": utc_now().isoformat(),
            },
        )


__all__ = [
    "FeedbackPolicy",
    "FeedbackPolicyApplication",
    "FeedbackPolicyService",
    "FeedbackRecommendation",
    "NO_CLAIM_LIMITATION",
    "default_feedback_policy",
]
