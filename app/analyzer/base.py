from abc import ABC, abstractmethod

from app.models import AnalysisResult


class Analyzer(ABC):
    @abstractmethod
    def analyze(self, text: str) -> AnalysisResult:
        """Return descriptive signals used as feedback inputs."""

