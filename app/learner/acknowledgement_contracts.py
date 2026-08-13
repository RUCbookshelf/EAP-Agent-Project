"""Positive longitudinal acknowledgement contracts (LEARNER-owned, WU2-C).

An acknowledgement is a *descriptive, learner-facing* acknowledgement of
already admitted observed evidence or a bounded practice/history signal. It
is NOT mastery, proficiency, writing ability, learning gain, score, ranking,
diagnosis, recommendation, or causal transfer attribution. The record
structurally enforces that boundary:

- ``epistemic_status`` is locked to ``observed_descriptive`` (L0 only);
- ``outcome_claim`` is locked to the literal ``"none"``;
- the source kind is a typed discriminator that keeps source event,
  observed evidence, diagnostic inference, feedback recommendation,
  practice activity/result, and outcome distinct; only descriptive kinds are
  acknowledgeable;
- the default limitation states the non-claim in prohibition language;
- every acknowledgement requires an explicit learner consent snapshot,
  non-empty source evidence IDs, stable provenance, policy/model/config or
  record version, and an explicit evidence status.

Binding sources: WU-D diagnostic gating contract sections 5/6/8 (epistemic
layers, admissibility, provenance chain, input envelope), RD-D09
(policy/model/config versioning, append-only records), 08_FEEDBACK_LEARNER_
INTELLIGENCE.md sections 3/4 (evidence-status and epistemic taxonomy), and
the frozen shared vocabularies (no mastery/proficiency/ability/learning-gain
semantics).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.schemas import utc_now
from app.shared.vocabularies import EpistemicStatus, EvidenceStatus

from .evidence import ProvenanceChain


ACKNOWLEDGEMENT_CONSENT_SCOPE = "learner_facing_acknowledgement"
ACKNOWLEDGEMENT_RECORD_VERSION = "acknowledgement-record-v0.1.0"
ACKNOWLEDGEMENT_CONSENT_VERSION = "learner-consent-v0.1.0"

ACKNOWLEDGEMENT_LIMITATION = (
    "An acknowledgement is a descriptive learner-facing acknowledgement of "
    "observed evidence or a bounded practice/history signal; it does not "
    "establish mastery, proficiency, writing ability, learning gain, score, "
    "ranking, diagnosis, recommendation, or causal transfer attribution."
)


class AcknowledgementSourceKind(StrEnum):
    """Typed discriminator preserving the six record families.

    The distinction between source event, observed evidence, diagnostic
    inference, feedback recommendation, practice activity/result, and
    outcome is preserved structurally: each acknowledgement names exactly
    one kind and only descriptive kinds may be acknowledged.
    """

    SOURCE_EVENT = "source_event"
    OBSERVED_EVIDENCE = "observed_evidence"
    DIAGNOSTIC_INFERENCE = "diagnostic_inference"
    FEEDBACK_RECOMMENDATION = "feedback_recommendation"
    PRACTICE_ACTIVITY = "practice_activity"
    PRACTICE_RESULT = "practice_result"
    HISTORY_SIGNAL = "history_signal"
    OUTCOME_CLAIM = "outcome_claim"


# Descriptive, learner-facing acknowledgeable kinds only. Raw source events,
# diagnostic inference, feedback recommendation, and outcome claims are
# never acknowledgeable: doing so would conflate epistemic layers.
ACKNOWLEDGEABLE_SOURCE_KINDS: frozenset[AcknowledgementSourceKind] = frozenset({
    AcknowledgementSourceKind.OBSERVED_EVIDENCE,
    AcknowledgementSourceKind.PRACTICE_ACTIVITY,
    AcknowledgementSourceKind.PRACTICE_RESULT,
    AcknowledgementSourceKind.HISTORY_SIGNAL,
})


class LearnerConsent(BaseModel):
    """Explicit learner consent snapshot for learner-facing acknowledgement.

    Missing, false, revoked, scoped elsewhere, learner-mismatched, or
    future-dated consent fails closed with no acknowledgement write.
    """

    model_config = ConfigDict(extra="forbid")

    granted: bool
    revoked: bool = False
    scope: str = Field(min_length=1)
    consent_version: str = Field(min_length=1)
    granted_at: datetime
    learner_id: str = Field(min_length=1)


class AcknowledgementRequest(BaseModel):
    """Input contract for one acknowledgement; the service validates it.

    The four structural link fields (``learning_item_id``,
    ``authentic_evidence_status``, ``practice_activity_id``,
    ``review_event_id``) are loose learner/LearningItem/authentic-evidence/
    practice-review links with bounded descriptive semantics: they scope the
    acknowledgement to an owned structural anchor when provided and never
    change the L0 descriptive claim boundary.
    """

    model_config = ConfigDict(extra="forbid")

    learner_id: str = Field(min_length=1)
    source_kind: AcknowledgementSourceKind
    source_evidence_ids: list[str] = Field(min_length=1)
    source_event_ids: list[str] = Field(default_factory=list)
    learning_item_id: str | None = None
    authentic_evidence_status: Literal["insufficient", "present"] | None = None
    practice_activity_id: str | None = None
    review_event_id: str | None = None
    evidence_status: EvidenceStatus
    epistemic_status: EpistemicStatus = EpistemicStatus.OBSERVED_DESCRIPTIVE
    provenance: ProvenanceChain | None = None
    policy_version: str | None = None
    model_version: str | None = None
    config_version: str | None = None
    record_version: str = Field(min_length=1)
    acknowledgement_text: str = Field(min_length=1)
    consent: LearnerConsent | None = None
    observed_span_start: datetime | None = None
    observed_span_end: datetime | None = None
    acknowledgement_id: str | None = None

    @field_validator("source_evidence_ids", "source_event_ids")
    @classmethod
    def strip_source_ids(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("source ids must not be blank")
        return cleaned

    @field_validator("acknowledgement_text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("acknowledgement_text must not be blank")
        return value

    @field_validator("acknowledgement_id")
    @classmethod
    def strip_acknowledgement_id(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("acknowledgement_id must not be blank")
        return value

    @field_validator("learning_item_id", "practice_activity_id", "review_event_id")
    @classmethod
    def strip_link_ids(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("structural link ids must not be blank")
        return value

    @field_validator("epistemic_status")
    @classmethod
    def acknowledgement_is_l0_only(cls, value: EpistemicStatus) -> EpistemicStatus:
        if value != EpistemicStatus.OBSERVED_DESCRIPTIVE:
            raise ValueError(
                "acknowledgements may only carry observed_descriptive "
                "epistemic status; higher layers are separate contracts"
            )
        return value

    @model_validator(mode="after")
    def validate_span_order(self) -> "AcknowledgementRequest":
        if (
            self.observed_span_start is not None
            and self.observed_span_end is not None
            and self.observed_span_end < self.observed_span_start
        ):
            raise ValueError("observed_span_end must not precede observed_span_start")
        return self


class AcknowledgementRecord(BaseModel):
    """Append-only acknowledgement record written after all gates pass.

    The record embeds the consent snapshot, the source-kind discriminator,
    the descriptive text, provenance, versions, evidence status, and the
    frozen non-claim limitation so no consumer can re-derive or relabel it.
    The four structural link fields (``learning_item_id``,
    ``authentic_evidence_status``, ``practice_activity_id``,
    ``review_event_id``) are loose learner/LearningItem/authentic-evidence/
    practice-review links with bounded descriptive semantics.
    """

    model_config = ConfigDict(extra="forbid")

    acknowledgement_id: str = Field(min_length=1)
    learner_id: str = Field(min_length=1)
    source_kind: AcknowledgementSourceKind
    source_evidence_ids: list[str] = Field(min_length=1)
    source_event_ids: list[str] = Field(default_factory=list)
    learning_item_id: str | None = None
    authentic_evidence_status: Literal["insufficient", "present"] | None = None
    practice_activity_id: str | None = None
    review_event_id: str | None = None
    evidence_status: EvidenceStatus
    epistemic_status: EpistemicStatus = EpistemicStatus.OBSERVED_DESCRIPTIVE
    outcome_claim: Literal["none"] = "none"
    provenance: ProvenanceChain
    policy_version: str | None = None
    model_version: str | None = None
    config_version: str | None = None
    record_version: str = Field(min_length=1)
    acknowledgement_text: str = Field(min_length=1)
    limitations: list[str] = Field(default_factory=lambda: [ACKNOWLEDGEMENT_LIMITATION])
    consent: LearnerConsent
    observed_span_start: datetime | None = None
    observed_span_end: datetime | None = None
    recorded_at: datetime = Field(default_factory=utc_now)

    @field_validator("epistemic_status")
    @classmethod
    def record_is_l0_only(cls, value: EpistemicStatus) -> EpistemicStatus:
        if value != EpistemicStatus.OBSERVED_DESCRIPTIVE:
            raise ValueError(
                "acknowledgement records may only carry observed_descriptive "
                "epistemic status"
            )
        return value

    @field_validator("acknowledgement_text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("acknowledgement_text must not be blank")
        return value

    @field_validator("learning_item_id", "practice_activity_id", "review_event_id")
    @classmethod
    def strip_link_ids(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("structural link ids must not be blank")
        return value

    @model_validator(mode="after")
    def validate_span_order(self) -> "AcknowledgementRecord":
        if (
            self.observed_span_start is not None
            and self.observed_span_end is not None
            and self.observed_span_end < self.observed_span_start
        ):
            raise ValueError("observed_span_end must not precede observed_span_start")
        return self


class AcknowledgementResult(BaseModel):
    """Successful acknowledgement result returned to the caller."""

    model_config = ConfigDict(extra="forbid")

    acknowledged: bool = True
    record: AcknowledgementRecord


__all__ = [
    "ACKNOWLEDGEABLE_SOURCE_KINDS",
    "ACKNOWLEDGEMENT_CONSENT_SCOPE",
    "ACKNOWLEDGEMENT_CONSENT_VERSION",
    "ACKNOWLEDGEMENT_LIMITATION",
    "ACKNOWLEDGEMENT_RECORD_VERSION",
    "AcknowledgementRecord",
    "AcknowledgementRequest",
    "AcknowledgementResult",
    "AcknowledgementSourceKind",
    "LearnerConsent",
]
