"""Branch-local adapters for the WU3 narrow protocols.

- ``ExistingPracticeActivitySource`` consumes the EXISTING practice
  capability (``app.practice`` schemas + rule-based evaluator); no practice
  engine is copied or created.
- ``InMemoryReviewEvidenceStore`` / ``InMemoryConsentStore`` are TEST-ONLY
  structural stand-ins for the accepted CORE/LEARNER WU2 contracts. They are
  never wired into the composition root; the INT consolidated Wave-3 gate
  injects the real CORE ReviewService and LEARNER consent persistence behind
  the same protocols (recorded as an integration dependency).
- ``PipelineAuthenticObservationReader`` reads authentic (non-practice)
  writing samples through the existing pipeline.
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any

from app.l2.wave2.pipeline import WritingPipelinePort
from app.l2.wave2.repository import RevisionLoopRepository
from app.l2.wave3.models import TutorConsentSnapshot
from app.practice.mapping import (
    PriorityMappingError,
    map_category_to_target_code,
)
from app.practice.schemas import default_exercise_specifications
from app.practice.service import PracticeService


class ExistingPracticeActivitySource:
    """Existing practice capability: specs, mapping, rule-based evaluation."""

    def __init__(self) -> None:
        self._practice_service = PracticeService()
        self._specs = default_exercise_specifications()

    def exercise_specifications(self) -> dict[str, Any]:
        return dict(self._specs)

    def target_code_for_category(self, category: str) -> str | None:
        try:
            return map_category_to_target_code(category)
        except PriorityMappingError:
            return None

    def evaluate(
        self,
        *,
        target_code: str,
        response_text: str,
        source_text: str,
    ) -> dict[str, Any]:
        attempt = {
            "status": "submitted",
            "response_text": response_text,
            "attempt_id": None,
        }
        target = {
            "target_code": target_code,
            "practice_target_id": "",
        }
        return self._practice_service.evaluate_attempt(
            attempt, target, source_text=source_text,
        )


class InMemoryReviewEvidenceStore:
    """TEST-ONLY structural stand-in for the CORE review/scheduler contract."""

    def __init__(self) -> None:
        self._due: dict[str, list[Any]] = {}
        self._activities: dict[str, list[Any]] = {}

    def seed_due_item(
        self, *, learning_item_id: str, student_id: str, category: str, due: datetime,
    ) -> None:
        self._due.setdefault(student_id, []).append({
            "learning_item_id": learning_item_id,
            "student_id": student_id,
            "category": category,
            "due": due,
        })

    def list_due_items(
        self, student_id: str, *, now: datetime,
    ) -> list[Any]:
        return [
            SimpleNamespace(**item) for item in self._due.get(student_id, [])
            if item["due"] <= now
        ]

    def list_activities(self, student_id: str) -> list[Any]:
        return list(self._activities.get(student_id, []))

    def record_activity(self, activity: Any) -> Any:
        student_id = getattr(activity, "student_id", "unknown")
        self._activities.setdefault(student_id, []).append(activity)
        return activity


class InMemoryConsentStore:
    """TEST-ONLY structural stand-in for the LEARNER consent contract."""

    def __init__(self) -> None:
        self._consents: dict[str, list[TutorConsentSnapshot]] = {}

    def get_consent(self, learner_id: str, scope: str) -> TutorConsentSnapshot | None:
        for consent in self._consents.get(learner_id, []):
            if consent.scope == scope:
                return consent
        return None

    def record_consent(self, consent: TutorConsentSnapshot) -> None:
        self._consents.setdefault(consent.learner_id, []).append(consent)

    def list_consents(self, learner_id: str) -> list[TutorConsentSnapshot]:
        return list(self._consents.get(learner_id, []))


class PipelineAuthenticObservationReader:
    """Authentic writing samples through the existing pipeline."""

    def __init__(
        self,
        repository: RevisionLoopRepository,
        pipeline: WritingPipelinePort,
    ) -> None:
        self.repository = repository
        self.pipeline = pipeline

    def latest_writing_samples(self, learner_id: str) -> list[dict[str, Any]]:
        return self.pipeline.list_student_submissions(learner_id)


__all__ = [
    "ExistingPracticeActivitySource",
    "InMemoryConsentStore",
    "InMemoryReviewEvidenceStore",
    "PipelineAuthenticObservationReader",
]
