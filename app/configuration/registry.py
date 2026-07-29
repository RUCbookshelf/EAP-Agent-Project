from __future__ import annotations

from app.analysis import AlgorithmRegistry, AlgorithmVersion, AnalyzerRegistry, MetricRegistry, default_metric_registry
from app.prompts import versioning, versioning_v04, versioning_v05


class PromptRegistry:
    def __init__(self) -> None:
        self._items: dict[str, dict] = {}

    def register(self, *, prompt_version: str, schema_version: str, manifest: dict) -> None:
        if prompt_version in self._items:
            raise ValueError(f"Prompt already registered: {prompt_version}")
        self._items[prompt_version] = {
            "prompt_version": prompt_version,
            "schema_version": schema_version,
            "system_template_hash": manifest["system_template_hash"],
            "user_template_hash": manifest["user_template_hash"],
            "status": "active",
        }

    def get(self, prompt_version: str) -> dict:
        if prompt_version not in self._items:
            raise ValueError(f"Unknown prompt: {prompt_version}")
        return self._items[prompt_version]

    def list(self) -> list[dict]:
        return [self._items[key] for key in sorted(self._items)]


class ConfigurationRegistry:
    def __init__(self, prompt_registry: PromptRegistry, metric_registry: MetricRegistry,
                 algorithm_registry: AlgorithmRegistry, analyzer_registry: AnalyzerRegistry) -> None:
        self.prompts = prompt_registry
        self.metrics = metric_registry
        self.algorithms = algorithm_registry
        self.analyzers = analyzer_registry


def default_prompt_registry() -> PromptRegistry:
    registry = PromptRegistry()
    for item in (versioning, versioning_v04, versioning_v05):
        registry.register(
            prompt_version=item.PROMPT_VERSION,
            schema_version=item.SCHEMA_VERSION,
            manifest=item.validate_prompt_versioning(),
        )
    return registry


def default_algorithm_registry() -> AlgorithmRegistry:
    return AlgorithmRegistry([
        AlgorithmVersion(
            algorithm_id="longitudinal-trend", version="0.3.0",
            implementation="app.services.progress.ProgressService",
            parameter_schema={"minimum_trend_points": "integer", "direction_relative_change": "number"},
            compatible_input_versions=["basic-analyzer-v0.1", "spacy-analyzer-v0.4.0"],
            output_schema_version="learner-profile-snapshot-v0.3.0",
            limitations=["Descriptive prototype trend; not ability growth."],
        ),
        AlgorithmVersion(
            algorithm_id="revision-alignment", version="0.5.0",
            implementation="app.revision.alignment.LocalRevisionAligner",
            parameter_schema={"similarity_thresholds": "working assumptions"},
            compatible_input_versions=["plain-text-v1"],
            output_schema_version="revision-snapshot-v0.5.0",
            limitations=["Surface similarity is not semantic equivalence."],
        ),
        AlgorithmVersion(
            algorithm_id="feedback-uptake", version="0.5.0",
            implementation="app.services.revision.RevisionService",
            parameter_schema={"trajectory_status": "categorical"},
            compatible_input_versions=["structured-feedback-v0.1.1", "structured-feedback-v0.5.0"],
            output_schema_version="revision-snapshot-v0.5.0",
            limitations=["Observable consistency is not causal evidence."],
        ),
    ])
