from abc import ABC, abstractmethod

from app.models import AnalysisResult


class Analyzer(ABC):
    @abstractmethod
    def analyze(self, text: str, *, writing_prompt: str = "", draft_stage: str | None = None,
                tool_use: str | None = None) -> AnalysisResult:
        """Return descriptive signals used as feedback inputs."""
