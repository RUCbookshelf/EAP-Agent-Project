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

    def latest_list(self) -> list[MetricDefinition]:
        return [self.get(metric_id) for metric_id in sorted({key[0] for key in self._items})]


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
        ("word_count", "1.0.0", "words", "integer", "Legacy detected lexical-token count."),
        ("word_count", "2.0.0", "words", "integer", "Alphabetic spaCy-token count."),
        ("sentence_count", "1.0.0", "sentences", "integer", "Detected sentence count."),
        ("paragraph_count", "1.0.0", "paragraphs", "integer", "Non-empty paragraph count."),
        ("average_sentence_length", "1.0.0", "words_per_sentence", "number", "Mean detected sentence length."),
        ("unique_word_count", "1.0.0", "word_types", "integer", "Legacy surface word-type count."),
        ("unique_word_count", "2.0.0", "word_types", "integer", "Lowercase surface types over alphabetic spaCy tokens."),
        ("type_token_ratio", "1.0.0", "ratio", "number", "Legacy length-sensitive TTR."),
        ("type_token_ratio", "2.0.0", "ratio", "number", "Lowercase surface types divided by alphabetic spaCy tokens."),
        ("connective_count", "2.0.0", "expressions", "integer", "Legacy dictionary-detected connective expressions."),
        ("connective_count", "2.1.0", "expressions", "integer", "Typed dictionary-detected connective expressions."),
        ("repeated_content_words", "2.0.0", "mapping", "object", "Legacy lemma-based repeated candidates."),
        ("repeated_content_words", "3.0.0", "mapping", "object", "Auditable lemma-based repeated content-word candidates."),
        ("repetition_density", "0.6.1", "ratio", "number", "Repeated-candidate occurrences divided by content-token count."),
        ("lexical_density", "0.4.0", "ratio", "number", "Legacy prototype content-token proportion."),
        ("lexical_density", "0.6.1", "ratio", "number", "NOUN/PROPN/VERB/ADJ/ADV share of alphabetic tokens."),
        ("mattr", "0.4.0", "ratio", "number", "Legacy prototype moving-average TTR."),
        ("mattr", "0.6.1", "ratio", "number", "Lowercase-surface moving-average TTR."),
        ("mtld", "0.8.0", "index", "number", "Bidirectional original-factor MTLD with explicit partial factors."),
        ("hdd", "0.8.0", "expected_sample_ttr", "number", "Hypergeometric distribution diversity at a configured sample size."),
        ("finite_verb_candidates", "0.4.0", "candidates", "integer", "Legacy parser-derived candidate count."),
        ("finite_verb_candidates", "0.6.1", "candidates", "integer", "Morphology/tag-derived finite verb candidates."),
        ("subordinate_clause_candidates", "0.4.0", "candidates", "integer", "Legacy aggregate dependency candidates."),
        ("clause_like_dependency_candidates", "0.6.1", "mapping", "object", "Dependency candidates separated by relation."),
        ("coordination_candidates", "0.4.0", "candidates", "integer", "Legacy cc plus conj node count."),
        ("coordinator_token_count", "0.6.1", "tokens", "integer", "Parser tokens with dependency cc."),
        ("conjunct_dependency_count", "0.6.1", "dependencies", "integer", "Parser nodes with dependency conj."),
        ("coordinated_structure_candidates", "0.6.1", "candidates", "integer", "Distinct heads with one or more conjunct dependencies."),
        ("mean_dependency_tree_depth", "0.4.0", "levels", "number", "Mean parser-derived dependency depth."),
        ("mean_noun_phrase_length", "0.4.0", "tokens", "number", "Mean detected noun-phrase length."),
        ("long_sentence_candidates", "0.8.0", "candidates", "integer", "Sentence-length candidates for research audit only."),
        ("clause_candidate_count", "0.8.0", "candidates", "integer", "Conservative clause candidate count."),
        ("t_unit_candidate_count", "0.8.0", "candidates", "integer", "Conservative T-unit candidate count."),
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
