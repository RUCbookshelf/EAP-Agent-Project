"""Shared core module for canonical frozen vocabularies.

Provides domain-aware registry mechanisms (TaskTypeRegistry,
FeedbackDimensionRegistry) and configuration/domain-pack lookup
readiness.  Shared Core = mechanism; domain departments = content.
References: D-04, D-22, D-25, D-26, D-37.
"""

from app.shared.task_type_registry import (
    LEGACY_UNCLASSIFIED,
    REGISTERED_NAMESPACES,
    TaskTypeEntry,
    TaskTypeRegistry,
    default_task_type_registry,
)
from app.shared.feedback_dimension_registry import (
    Availability,
    FeedbackDimensionEntry,
    FeedbackDimensionRegistry,
    LearnerExposure,
    default_feedback_dimension_registry,
)
