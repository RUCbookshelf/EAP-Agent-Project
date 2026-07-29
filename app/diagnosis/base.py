from abc import ABC, abstractmethod

from app.models import AnalysisResult, DiagnosisResult


class Diagnoser(ABC):
    @abstractmethod
    def diagnose(self, analysis: AnalysisResult) -> DiagnosisResult:
        """Convert descriptive metrics into cautious prototype teaching signals."""

