"""Longitudinal Learner Model v1 -- typed observation contracts.

Goal PDW2-B-LEARNER-MODEL. Records are observation-only: an observation
describes what was seen in admitted observed evidence, never mastery,
proficiency, ability, or learning gain (WU-D F11; D-09 epistemic layers).
Proficiency context carries external anchors (CET-4/6, IELTS, TOEFL, other)
as contextual reference points declared by or for the learner; they are
never auto-converted from corpus statistics (``derived_from_corpus`` is
forbidden to be True). Insufficient-history states are first-class values
(``HistoryState.INSUFFICIENT_HISTORY``) with reasons.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.learner.evidence import ObservedEvidence


class ObservationType(StrEnum):
    """Observation families (bounded, non-normative)."""

    DIFFICULTY = "difficulty"
    STRENGTH = "strength"


class RevisionResponseState(StrEnum):
    """Observation-only revision behavior states (no outcome claims)."""

    CORRECTED_AFTER_FEEDBACK = "corrected_after_feedback"
    PERSISTED_AFTER_REVISION = "persisted_after_revision"
    REAPPEARED_LATER = "reappeared_later"
    NO_REVISION_EVIDENCE = "no_revision_evidence"


class HistoryState(StrEnum):
    """Explicit history-sufficiency states for longitudinal outputs."""

    SUFFICIENT = "sufficient"
    INSUFFICIENT_HISTORY = "insufficient_history"


class StabilityKind(StrEnum):
    """Why an observation is reported under the stable view."""

    STRENGTH_HISTORY = "strength_history"
    PREVIOUSLY_RECURRING_NOT_RECENTLY_OBSERVED = (
        "previously_recurring_not_recently_observed"
    )


class ExternalAnchorSystem(StrEnum):
    """External proficiency-context anchor systems (contextual only)."""

    CET4 = "CET-4"
    CET6 = "CET-6"
    IELTS = "IELTS"
    TOEFL = "TOEFL"
    OTHER = "OTHER"


class OccurrenceEntry(BaseModel):
    """One observed occurrence of an observation, linked to admitted evidence."""

    model_config = ConfigDict(extra="forbid")

    occurrence_id: str = Field(min_length=1)
    evidence_ref: str = Field(min_length=1)
    task_context: str = Field(min_length=1)
    observed_at: datetime
    qualified: bool = True
    qualification_reason: str = "declared comparable task conditions"


class ObservationRecord(BaseModel):
    """A persisted longitudinal observation (difficulty or strength)."""

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1)
    learner_id: str = Field(min_length=1)
    observation_type: ObservationType
    code: str = Field(min_length=1)
    label: str = Field(min_length=1)
    occurrences: list[OccurrenceEntry] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    record_version: str = "learner-observation-v0.1.0"


class SubmissionSample(BaseModel):
    """One writing submission sample used as a longitudinal comparison unit."""

    model_config = ConfigDict(extra="forbid")

    submission_id: str = Field(min_length=1)
    learner_id: str = Field(min_length=1)
    task_context: str = Field(min_length=1)
    submitted_at: datetime
    draft_stage: str = Field(min_length=1)
    qualified: bool = True
    qualification_reason: str = "declared comparable task conditions"


class RevisionBehavior(BaseModel):
    """Observation-only behavior state of an observation across a revision."""

    model_config = ConfigDict(extra="forbid")

    behavior_id: str = Field(min_length=1)
    learner_id: str = Field(min_length=1)
    observation_id: str = Field(min_length=1)
    revision_event_id: str = Field(min_length=1)
    state: RevisionResponseState
    occurred_at: datetime
    evidence_refs: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ExternalAnchor(BaseModel):
    """One declared external proficiency-context anchor (never corpus-derived)."""

    model_config = ConfigDict(extra="forbid")

    anchor_id: str = Field(min_length=1)
    system: ExternalAnchorSystem
    declared_value: str = Field(min_length=1)
    source: str = Field(min_length=1)
    recorded_at: datetime
    limitations: list[str] = Field(default_factory=list)


DEFAULT_ANCHOR_STATEMENT = (
    "External anchors are contextual reference points declared by or for "
    "the learner; they are not converted from corpus statistics and are not "
    "learner-performance labels."
)


class ProficiencyContext(BaseModel):
    """Learner proficiency context with external anchors only.

    ``derived_from_corpus`` is an invariant guard: it must always be False.
    Corpus statistics can never be auto-converted into proficiency anchors.
    """

    model_config = ConfigDict(extra="forbid")

    learner_id: str = Field(min_length=1)
    anchors: list[ExternalAnchor] = Field(default_factory=list)
    derived_from_corpus: bool = False
    statement: str = DEFAULT_ANCHOR_STATEMENT
    limitations: list[str] = Field(default_factory=list)
    record_version: str = "learner-proficiency-context-v0.1.0"

    @field_validator("derived_from_corpus")
    @classmethod
    def corpus_derivation_forbidden(cls, value: bool) -> bool:
        if value:
            raise ValueError(
                "proficiency context anchors must never be auto-converted "
                "from corpus statistics"
            )
        return value


class LearnerEvidenceRecord(BaseModel):
    """Observed evidence bound to a learner (evidence/provenance links)."""

    model_config = ConfigDict(extra="forbid")

    learner_id: str = Field(min_length=1)
    evidence: ObservedEvidence


class QualifiedFrequency(BaseModel):
    """Descriptive frequency of an observation over qualified recent samples."""

    model_config = ConfigDict(extra="forbid")

    qualified_occurrence_count: int = Field(ge=0)
    qualified_sample_count: int = Field(ge=0)
    window_size: int = Field(ge=0)
    descriptive_proportion: float | None = None
    history_state: HistoryState = HistoryState.INSUFFICIENT_HISTORY
    history_reasons: list[str] = Field(default_factory=list)
    limitation: str = Field(min_length=1)


class ObservationStatusView(BaseModel):
    """Longitudinal status of one observation (all longitudinal queries)."""

    model_config = ConfigDict(extra="forbid")

    learner_id: str
    observation_id: str
    code: str
    label: str
    observation_type: ObservationType
    occurrence_count: int = Field(ge=0)
    qualified_occurrence_count: int = Field(ge=0)
    prior_occurrence_count: int = Field(ge=0)
    appeared_before: bool
    first_observed_at: datetime | None = None
    last_observed_at: datetime | None = None
    days_since_last_observed: int | None = None
    contexts: list[str] = Field(default_factory=list)
    revision_response: RevisionResponseState = (
        RevisionResponseState.NO_REVISION_EVIDENCE
    )
    addressed_in_prior_revision: bool = False
    frequency: QualifiedFrequency
    history_state: HistoryState
    history_reasons: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    claims_status: str = "observation_only"


class RecurringDifficulty(ObservationStatusView):
    """Recurring difficulty view with full occurrence history."""

    occurrence_history: list[OccurrenceEntry] = Field(default_factory=list)


class StrengthView(BaseModel):
    """Strength observation with positive/stable history state."""

    model_config = ConfigDict(extra="forbid")

    learner_id: str
    observation_id: str
    code: str
    label: str
    occurrence_count: int = Field(ge=0)
    qualified_occurrence_count: int = Field(ge=0)
    first_observed_at: datetime | None = None
    last_observed_at: datetime | None = None
    days_since_last_observed: int | None = None
    history_state: HistoryState
    history_reasons: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    claims_status: str = "observation_only"


class StableObservation(BaseModel):
    """Stable observation: repeated strength history or previously recurring
    difficulty not observed across recent qualified samples (observation-only;
    never a validated ability statement)."""

    model_config = ConfigDict(extra="forbid")

    learner_id: str
    observation_id: str
    code: str
    label: str
    stability_kind: StabilityKind
    occurrence_count: int = Field(ge=0)
    qualified_occurrence_count: int = Field(ge=0)
    recent_window_occurrence_count: int = Field(ge=0)
    recent_window_sample_count: int = Field(ge=0)
    first_observed_at: datetime | None = None
    last_observed_at: datetime | None = None
    history_state: HistoryState
    history_reasons: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    claims_status: str = "observation_only"


class ProficiencyContextView(BaseModel):
    """Proficiency context output with explicit sufficiency state."""

    model_config = ConfigDict(extra="forbid")

    learner_id: str
    anchors: list[ExternalAnchor] = Field(default_factory=list)
    derived_from_corpus: bool = False
    statement: str = DEFAULT_ANCHOR_STATEMENT
    history_state: HistoryState
    history_reasons: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    claims_status: str = "observation_only"


class ObservationListView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: str
    history_state: HistoryState
    items: list[ObservationStatusView] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class RecurringDifficultyList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: str
    history_state: HistoryState
    items: list[RecurringDifficulty] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class StrengthList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: str
    items: list[StrengthView] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class StableList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: str
    items: list[StableObservation] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class EvidenceList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: str
    items: list[LearnerEvidenceRecord] = Field(default_factory=list)
    excluded_count: int = Field(ge=0)
    limitations: list[str] = Field(default_factory=list)


__all__ = [
    "DEFAULT_ANCHOR_STATEMENT",
    "EvidenceList",
    "ExternalAnchor",
    "ExternalAnchorSystem",
    "HistoryState",
    "LearnerEvidenceRecord",
    "ObservationListView",
    "ObservationRecord",
    "ObservationStatusView",
    "ObservationType",
    "OccurrenceEntry",
    "ProficiencyContext",
    "ProficiencyContextView",
    "QualifiedFrequency",
    "RecurringDifficulty",
    "RecurringDifficultyList",
    "RevisionBehavior",
    "RevisionResponseState",
    "StabilityKind",
    "StableList",
    "StableObservation",
    "StrengthList",
    "StrengthView",
    "SubmissionSample",
]
