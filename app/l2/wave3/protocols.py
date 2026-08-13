"""Narrow structural protocols for the WU3 L2 domain.

The accepted CORE (Review/Scheduling Foundation) and LEARNER
(acknowledgement/consent) WU2 contracts are NOT physically present on the L2
branch; they land at integration. These narrow protocols mirror the accepted
record shapes and service surfaces so the L2 domain consumes them by
attribute access alone: no CORE/LEARNER product code is copied or imported,
no second store/scheduler/database is introduced. The INT composition root
injects the real implementations behind these protocols at the consolidated
Wave-3 gate (recorded as an integration dependency).

Existing practice capability (``app.practice``) is consumed through
``PracticeActivitySource``; the existing Writing Intelligence pipeline is
consumed through the already-defined ``app.l2.wave2.pipeline.
WritingPipelinePort`` (imported here, never redefined).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from app.l2.wave2.pipeline import WritingPipelinePort  # noqa: F401  (re-export)


@runtime_checkable
class PracticeActivitySource(Protocol):
    """Existing practice capability: specs, target codes, rule evaluation."""

    def exercise_specifications(self) -> dict[str, Any]: ...

    def target_code_for_category(self, category: str) -> str | None: ...

    def evaluate(
        self,
        *,
        target_code: str,
        response_text: str,
        source_text: str,
    ) -> dict[str, Any]: ...


@runtime_checkable
class ReviewEvidencePort(Protocol):
    """Structural CORE WU2 boundary: due items + practice/review evidence.

    The real CORE ``ReviewService``/repository satisfies this port at
    integration. In-memory adapter used on the L2 branch is test-only and
    never becomes a second scheduler/store.
    """

    def list_due_items(
        self, student_id: str, *, now: datetime,
    ) -> list[Any]: ...

    def list_activities(self, student_id: str) -> list[Any]: ...

    def record_activity(self, activity: Any) -> Any: ...


@runtime_checkable
class LearnerConsentStorePort(Protocol):
    """Structural LEARNER WU2 boundary: consent snapshots + acknowledgements.

    The real LEARNER acknowledgement/consent persistence satisfies this port
    at integration. In-memory adapter used on the L2 branch is test-only.
    """

    def get_consent(
        self, learner_id: str, scope: str,
    ) -> Any | None: ...

    def record_consent(self, consent: Any) -> None: ...

    def list_consents(self, learner_id: str) -> list[Any]: ...


@runtime_checkable
class AuthenticWritingObservationPort(Protocol):
    """Source of authentic (non-practice) writing evidence for observation."""

    def latest_writing_samples(self, learner_id: str) -> list[dict[str, Any]]: ...


__all__ = [
    "AuthenticWritingObservationPort",
    "LearnerConsentStorePort",
    "PracticeActivitySource",
    "ReviewEvidencePort",
    "WritingPipelinePort",
]
