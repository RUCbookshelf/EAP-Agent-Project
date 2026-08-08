"""FeedbackDimensionRegistry mechanism with availability + learner_exposure axes (D-37, RT-17).

Shared Core provides the MECHANISM; domain departments provide CONTENT.
Entries carry two orthogonal axes:
  - availability: available | insufficient_evidence | not_applicable
  - learner_exposure: student | research_only

Content entries exist ONLY where directly evidenced by current code/docs.
Otherwise the content is empty with an NR note.

References: D-37, RT-17, D-26.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Availability(str, Enum):
    """Whether the dimension is functionally available."""
    AVAILABLE = "available"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NOT_APPLICABLE = "not_applicable"


class LearnerExposure(str, Enum):
    """Whether the dimension is exposed to students or research-only."""
    STUDENT = "student"
    RESEARCH_ONLY = "research_only"


@dataclass(frozen=True)
class FeedbackDimensionEntry:
    """Metadata for a single feedback dimension.

    The ``availability`` axis records whether the dimension is
    functionally available. The ``learner_exposure`` axis records
    whether students can see it or it is research-only.
    """

    dimension_id: str
    display_name: str | None = None
    description: str | None = None
    availability: Availability = Availability.INSUFFICIENT_EVIDENCE
    learner_exposure: LearnerExposure = LearnerExposure.RESEARCH_ONLY
    metadata: dict[str, Any] = field(default_factory=dict)


class FeedbackDimensionRegistry:
    """Registry for feedback dimension metadata with axes validation.

    In H1 this is a mechanism-only registry. Content entries are added
    only where directly evidenced by current code/docs. Un-evidenced
    dimensions are left empty with an NR note in metadata.
    """

    def __init__(self) -> None:
        self._entries: dict[str, FeedbackDimensionEntry] = {}

    def register(self, entry: FeedbackDimensionEntry) -> None:
        """Register a feedback dimension entry.

        Raises ``ValueError`` if an entry with the same dimension_id
        already exists.
        """
        if entry.dimension_id in self._entries:
            raise ValueError(
                f"Feedback dimension already registered: {entry.dimension_id!r}"
            )
        self._entries[entry.dimension_id] = entry

    def get(self, dimension_id: str) -> FeedbackDimensionEntry:
        """Retrieve a dimension entry by id."""
        if dimension_id not in self._entries:
            raise ValueError(f"Unknown feedback dimension: {dimension_id!r}")
        return self._entries[dimension_id]

    def list_available(self) -> list[FeedbackDimensionEntry]:
        """List all dimensions that are functionally available."""
        return [
            entry
            for entry in sorted(self._entries.values(), key=lambda e: e.dimension_id)
            if entry.availability == Availability.AVAILABLE
        ]

    def list_student_visible(self) -> list[FeedbackDimensionEntry]:
        """List dimensions visible to students."""
        return [
            entry
            for entry in sorted(self._entries.values(), key=lambda e: e.dimension_id)
            if (
                entry.availability == Availability.AVAILABLE
                and entry.learner_exposure == LearnerExposure.STUDENT
            )
        ]

    def list_all(self) -> list[FeedbackDimensionEntry]:
        """List all registered dimensions."""
        return [entry for entry in sorted(self._entries.values(), key=lambda e: e.dimension_id)]

    def has_entry(self, dimension_id: str) -> bool:
        """Check whether a dimension entry exists."""
        return dimension_id in self._entries

    def count(self) -> int:
        """Return the number of registered dimensions."""
        return len(self._entries)


def default_feedback_dimension_registry() -> FeedbackDimensionRegistry:
    """Create a FeedbackDimensionRegistry with H1 baseline content.

    In H1, content entries exist ONLY where directly evidenced by the
    current code/docs. The lexical_repetition, cohesion, and sentence
    structure dimensions are documented in the analysis pipeline.
    """
    registry = FeedbackDimensionRegistry()

    # Evidenced by app/analysis/connective_features.py and
    # app/analysis/coordinator.py: cohesion/connective features are
    # computed and surfaced in feedback.
    registry.register(FeedbackDimensionEntry(
        dimension_id="cohesion",
        display_name="Cohesion",
        description="Connective and cohesive feature analysis (D-37).",
        availability=Availability.AVAILABLE,
        learner_exposure=LearnerExposure.STUDENT,
    ))

    # Evidenced by app/analysis/lexical_features.py: lexical density
    # and repetition features are computed.
    registry.register(FeedbackDimensionEntry(
        dimension_id="lexical_repetition",
        display_name="Lexical Repetition",
        description="Repeated content-word and density analysis (D-37).",
        availability=Availability.AVAILABLE,
        learner_exposure=LearnerExposure.RESEARCH_ONLY,
    ))

    # Evidenced by app/analysis/syntactic_features.py: dependency and
    # clause candidate features are computed.
    registry.register(FeedbackDimensionEntry(
        dimension_id="sentence_structure",
        display_name="Sentence Structure",
        description="Syntactic complexity candidate analysis (D-37).",
        availability=Availability.AVAILABLE,
        learner_exposure=LearnerExposure.RESEARCH_ONLY,
    ))

    # Evidenced by app/calf/: lexical diversity metrics (TTR, MATTR,
    # MTLD, HDD) are computed and available.
    registry.register(FeedbackDimensionEntry(
        dimension_id="lexical_diversity",
        display_name="Lexical Diversity",
        description="Multiple lexical diversity indices (D-37).",
        availability=Availability.AVAILABLE,
        learner_exposure=LearnerExposure.STUDENT,
    ))

    # Accuracy: no automatic measure in v0.8 (only annotation
    # foundation). Mark as insufficient_evidence for automatic use.
    registry.register(FeedbackDimensionEntry(
        dimension_id="accuracy",
        display_name="Accuracy",
        description="Error-related observations from validated annotations (D-37).",
        availability=Availability.INSUFFICIENT_EVIDENCE,
        learner_exposure=LearnerExposure.RESEARCH_ONLY,
        metadata={"note": "NR: no automatic accuracy measure in v0.8; annotation foundation only."},
    ))

    # Fluency: writing_output_rate is a descriptive proxy only.
    registry.register(FeedbackDimensionEntry(
        dimension_id="fluency",
        display_name="Fluency",
        description="Product fluency output-rate proxy (D-37).",
        availability=Availability.AVAILABLE,
        learner_exposure=LearnerExposure.RESEARCH_ONLY,
    ))

    return registry
