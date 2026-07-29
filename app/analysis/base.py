from __future__ import annotations

from typing import Protocol

from app.models import AnalysisResult


class AnalyzerProtocol(Protocol):
    analyzer_id: str
    version: str

    def analyze(self, text: str, *, writing_prompt: str = "", draft_stage: str | None = None,
                tool_use: str | None = None) -> AnalysisResult: ...


class MetricCalculator(Protocol):
    metric_id: str
    metric_version: str

    def calculate(self, context: dict) -> object: ...
