from __future__ import annotations

from dataclasses import replace

from app.analysis import AnalyzerRegistry, MetricRegistry
from app.config import Settings
from app.configuration import (
    ConfigurationCreate, ConfigurationRegistry, ConfigurationVersion,
    default_algorithm_registry, default_prompt_registry,
)


class ConfigurationRepository:
    def list_configurations(self): ...
    def get_configuration(self, configuration_id_or_version: str): ...
    def get_active_configuration(self): ...
    def create_configuration(self, request, parent_version): ...
    def set_configuration_validation(self, configuration_id, *, passed, errors, actor): ...
    def activate_configuration(self, configuration_id, *, actor, reason, action="activate"): ...
    def list_configuration_audit(self, configuration_id=None): ...


class ConfigurationService:
    def __init__(self, repository: ConfigurationRepository, analyzers: AnalyzerRegistry,
                 metrics: MetricRegistry) -> None:
        self.repository = repository
        self.registry = ConfigurationRegistry(
            default_prompt_registry(), metrics, default_algorithm_registry(), analyzers,
        )

    def list(self) -> list[ConfigurationVersion]:
        return self.repository.list_configurations()

    def active(self) -> ConfigurationVersion:
        return self.repository.get_active_configuration()

    def create(self, request: ConfigurationCreate) -> ConfigurationVersion:
        return self.repository.create_configuration(request, self.active().version)

    def validate(self, configuration_id: str, *, actor: str = "local_researcher") -> ConfigurationVersion:
        item = self.repository.get_configuration(configuration_id)
        if item is None:
            raise LookupError("Configuration not found.")
        errors: list[str] = []
        analyzers = {entry["analyzer_id"]: entry for entry in self.registry.analyzers.describe()}
        if item.payload.active_analyzer not in analyzers:
            errors.append("Active analyzer is not registered.")
        else:
            analyzer = self.registry.analyzers.get(item.payload.active_analyzer)
            health = analyzer.health() if hasattr(analyzer, "health") else {"available": True}
            if health.get("available") is False:
                errors.append("Requested analyzer resource is unavailable.")
        if item.payload.fallback_analyzer not in analyzers:
            errors.append("Fallback analyzer is not registered.")
        try:
            self.registry.prompts.get(item.payload.active_prompt_version)
        except ValueError as exc:
            errors.append(str(exc))
        metric_ids = {metric.metric_id for metric in self.registry.metrics.list()}
        if not {"word_count", "mattr", "lexical_density"} <= metric_ids:
            errors.append("Required metric registry entries are missing.")
        algorithm_ids = {algorithm.algorithm_id for algorithm in self.registry.algorithms.list()}
        if not {"longitudinal-trend", "revision-alignment", "feedback-uptake"} <= algorithm_ids:
            errors.append("Required algorithms are not registered.")
        return self.repository.set_configuration_validation(
            configuration_id, passed=not errors, errors=errors, actor=actor,
        )

    def activate(self, configuration_id: str, *, actor: str = "local_researcher",
                 reason: str = "Validated configuration activated.") -> ConfigurationVersion:
        return self.repository.activate_configuration(
            configuration_id, actor=actor, reason=reason,
        )

    def rollback(self, configuration_id: str, *, reason: str,
                 actor: str = "local_researcher") -> ConfigurationVersion:
        current = self.repository.get_configuration(configuration_id)
        if current is None:
            raise LookupError("Configuration not found.")
        if current.status != "active":
            raise ValueError("Rollback must start from the active configuration.")
        if not current.parent_version:
            raise ValueError("The active configuration has no parent version to roll back to.")
        parent = self.repository.get_configuration(current.parent_version)
        if parent is None:
            raise LookupError("Parent configuration not found.")
        return self.repository.activate_configuration(
            parent.configuration_id, actor=actor, reason=reason, action="rollback",
        )

    def audit(self) -> list[dict]:
        return self.repository.list_configuration_audit()

    def registries(self) -> dict:
        return {
            "analyzers": self.registry.analyzers.describe(),
            "metrics": [item.model_dump(mode="json") for item in self.registry.metrics.list()],
            "algorithms": [item.model_dump(mode="json") for item in self.registry.algorithms.list()],
            "prompts": self.registry.prompts.list(),
        }


def settings_from_configuration(settings: Settings, configuration: ConfigurationVersion) -> Settings:
    payload = configuration.payload
    return replace(
        settings,
        active_analyzer=payload.active_analyzer,
        fallback_analyzer=payload.fallback_analyzer,
        mattr_window=payload.mattr_window,
        local_repetition_window=payload.local_repetition_window,
        long_sentence_threshold=payload.long_sentence_threshold,
        analysis_configuration_version=configuration.version,
        prompt_version=payload.active_prompt_version,
        llm_temperature=payload.llm_temperature,
        llm_max_tokens=payload.llm_max_tokens,
    )
