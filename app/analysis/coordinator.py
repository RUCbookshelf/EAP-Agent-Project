from __future__ import annotations

from app.models import AnalysisResult

from .registry import AnalyzerRegistry


class UnavailableAnalyzer:
    def __init__(self, analyzer_id: str, version: str, reason: str) -> None:
        self.analyzer_id = analyzer_id
        self.version = version
        self.backend = analyzer_id
        self.reason = reason

    def analyze(self, text: str, *, writing_prompt: str = "", draft_stage: str | None = None,
                tool_use: str | None = None) -> AnalysisResult:
        raise RuntimeError(self.reason)


class AnalyzerCoordinator:
    """Selects a registered analyzer and records any explicit BasicAnalyzer fallback."""

    analyzer_id = "coordinator"

    def __init__(self, registry: AnalyzerRegistry, active_analyzer: str, fallback_analyzer: str = "basic") -> None:
        self.registry = registry
        self.active_analyzer = active_analyzer
        self.fallback_analyzer = fallback_analyzer
        self.version = registry.get(active_analyzer).version
        self.last_fallback_reason: str | None = None

    def analyze(self, text: str, *, writing_prompt: str = "", draft_stage: str | None = None,
                tool_use: str | None = None) -> AnalysisResult:
        selected = self.registry.get(self.active_analyzer)
        try:
            result = selected.analyze(text, writing_prompt=writing_prompt, draft_stage=draft_stage, tool_use=tool_use)
            self.last_fallback_reason = None
            return result
        except Exception as exc:
            if self.active_analyzer == self.fallback_analyzer:
                raise
            fallback = self.registry.get(self.fallback_analyzer)
            reason = f"{type(exc).__name__}: {str(exc)[:240]}"
            self.last_fallback_reason = reason
            result = fallback.analyze(text, writing_prompt=writing_prompt, draft_stage=draft_stage, tool_use=tool_use)
            return result.model_copy(update={
                "fallback_used": True, "fallback_reason": reason,
                "limitations": f"{result.limitations} Requested analyzer {self.active_analyzer} failed; explicit fallback was used.",
            })

    def health(self) -> dict:
        selected = self.registry.get(self.active_analyzer)
        unavailable = isinstance(selected, UnavailableAnalyzer)
        return {
            "active_analyzer": self.active_analyzer,
            "active_analyzer_version": selected.version,
            "available": not unavailable,
            "fallback_analyzer": self.fallback_analyzer,
            "fallback_active": unavailable or self.last_fallback_reason is not None,
            "fallback_reason": selected.reason if unavailable else self.last_fallback_reason,
        }
