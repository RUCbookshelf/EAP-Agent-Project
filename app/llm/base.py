from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models import (
    AnalysisResult,
    DiagnosisResult,
    EssaySubmission,
    HistoryResult,
    StructuredFeedback,
)
from app.core import LearnerProfileSnapshot


@dataclass(frozen=True)
class FeedbackContext:
    submission: EssaySubmission
    analysis: AnalysisResult
    diagnosis: DiagnosisResult
    history: HistoryResult
    learner_profile_snapshot: LearnerProfileSnapshot | None = None


class ProviderOutputError(RuntimeError):
    """A provider returned a response that could not satisfy the Pydantic schema."""


class LLMProvider(ABC):
    provider_name: str
    model_name: str

    @abstractmethod
    def generate(self, messages: list[dict[str, str]], *, temperature: float) -> StructuredFeedback:
        """Generate schema-valid feedback from already-rendered messages."""
