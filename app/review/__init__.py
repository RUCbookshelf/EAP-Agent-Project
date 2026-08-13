"""Shared Review / Scheduling Foundation (CORE, Wave-3 WU1).

This package owns the shared platform contracts and persistence for the
approved Wave-3 learning loop
``LearningItem -> Practice -> Review Evidence -> FSRS Scheduling``.
It does NOT own Practice pedagogy, Tutor behavior, or UX.
"""

from .models import (
    PRACTICE_ACTIVITY_LIMITATION,
    Rating,
    ReviewEvent,
    PracticeActivity,
    PracticeActivityStatus,
    SchedulerIdentity,
    SchedulerStateSnapshot,
    SchedulingResult,
)
from .rating_policy import RATING_RULE_VERSION, resolve_final_rating
from .scheduler import FSRSSchedulerAdapter, SCHEDULER_IMPLEMENTATION
from .service import ReviewError, ReviewService
from .protocols import ReviewEvidenceLookupProtocol

__all__ = [
    "FSRSSchedulerAdapter",
    "PRACTICE_ACTIVITY_LIMITATION",
    "RATING_RULE_VERSION",
    "Rating",
    "ReviewError",
    "ReviewEvent",
    "ReviewService",
    "PracticeActivity",
    "PracticeActivityStatus",
    "ReviewEvidenceLookupProtocol",
    "SCHEDULER_IMPLEMENTATION",
    "SchedulerIdentity",
    "SchedulerStateSnapshot",
    "SchedulingResult",
    "resolve_final_rating",
]
