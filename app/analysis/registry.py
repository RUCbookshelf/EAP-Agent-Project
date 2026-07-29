from __future__ import annotations

from collections.abc import Iterable

from .base import AnalyzerProtocol
from .schemas import AlgorithmVersion, MetricDefinition


class AnalyzerRegistry:
    def __init__(self, analyzers: Iterable[AnalyzerProtocol] = ()) -> None:
        self._items: dict[str, AnalyzerProtocol] = {}
        for analyzer in analyzers:
            self.register(analyzer)

    def register(self, analyzer: AnalyzerProtocol) -> None:
        if analyzer.analyzer_id in self._items:
            raise ValueError(f"Analyzer already registered: {analyzer.analyzer_id}")
        self._items[analyzer.analyzer_id] = analyzer

    def get(self, analyzer_id: str) -> AnalyzerProtocol:
        try:
            return self._items[analyzer_id]
        except KeyError as exc:
            raise ValueError(f"Unknown analyzer: {analyzer_id}") from exc

    def describe(self) -> list[dict]:
        return [
            {"analyzer_id": key, "analyzer_version": item.version, "backend": getattr(item, "backend", "unknown")}
            for key, item in sorted(self._items.items())
        ]


class MetricRegistry:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], MetricDefinition] = {}

    def register(self, definition: MetricDefinition) -> None:
        key = (definition.metric_id, definition.metric_version)
        if key in self._items:
            raise ValueError(f"Metric already registered: {key}")
        self._items[key] = definition

    def get(self, metric_id: str, version: str | None = None) -> MetricDefinition:
        candidates = [item for (mid, _), item in self._items.items() if mid == metric_id]
        if version is not None:
            candidates = [item for item in candidates if item.metric_version == version]
        if not candidates:
            raise ValueError(f"Unknown metric: {metric_id} {version or ''}".strip())
        return sorted(candidates, key=lambda item: item.metric_version)[-1]

    def list(self) -> list[MetricDefinition]:
        return [self._items[key] for key in sorted(self._items)]


class AlgorithmRegistry:
    def __init__(self, algorithms: Iterable[AlgorithmVersion] = ()) -> None:
        self._items = {(item.algorithm_id, item.version): item for item in algorithms}

    def register(self, algorithm: AlgorithmVersion) -> None:
        key = (algorithm.algorithm_id, algorithm.version)
        if key in self._items:
            raise ValueError(f"Algorithm already registered: {key}")
        self._items[key] = algorithm

    def list(self) -> list[AlgorithmVersion]:
        return [self._items[key] for key in sorted(self._items)]


def default_metric_registry() -> MetricRegistry:
    registry = MetricRegistry()
    definitions = [
        ("word_count", "1.0.0", "words", "integer", "Detected lexical-token count."),
        ("sentence_count", "1.0.0", "sentences", "integer", "Detected sentence count."),
        ("paragraph_count", "1.0.0", "paragraphs", "integer", "Non-empty paragraph count."),
        ("average_sentence_length", "1.0.0", "words_per_sentence", "number", "Mean detected sentence length."),
        ("unique_word_count", "1.0.0", "word_types", "integer", "Surface word-type count."),
        ("type_token_ratio", "1.0.0", "ratio", "number", "Length-sensitive surface TTR."),
        ("connective_count", "2.0.0", "expressions", "integer", "Dictionary-detected connective expressions."),
        ("repeated_content_words", "2.0.0", "mapping", "object", "Lemma-based repeated content-word candidates."),
        ("lexical_density", "0.4.0", "ratio", "number", "Prototype content-token proportion."),
        ("mattr", "0.4.0", "ratio", "number", "Prototype moving-average TTR."),
        ("finite_verb_candidates", "0.4.0", "candidates", "integer", "Parser-derived finite-verb candidate count."),
        ("subordinate_clause_candidates", "0.4.0", "candidates", "integer", "Parser-derived subordinate-clause candidate count."),
        ("coordination_candidates", "0.4.0", "candidates", "integer", "Parser-derived coordination candidate count."),
        ("mean_dependency_tree_depth", "0.4.0", "levels", "number", "Mean parser-derived dependency depth."),
        ("mean_noun_phrase_length", "0.4.0", "tokens", "number", "Mean detected noun-phrase length."),
    ]
    for metric_id, version, unit, value_type, description in definitions:
        limitations = ["Automatic prototype metric; teacher/researcher interpretation is required."]
        if metric_id in {"type_token_ratio", "mattr"}:
            limitations.append("Lexical-diversity values are text-length and parameter sensitive, not ability scores.")
        registry.register(MetricDefinition(
            metric_id=metric_id, metric_version=version, label=metric_id.replace("_", " ").title(),
            unit=unit, value_type=value_type, description=description, limitations=limitations,
        ))
    return registry

