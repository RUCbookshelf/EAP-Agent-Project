from __future__ import annotations

import importlib.metadata
import re
import time
from pathlib import Path

from app.models import AnalysisResult

from .connective_features import ConnectiveFeatureExtractor
from .input_quality import InputQualityService
from .lexical_features import extract_lexical_features
from .metric_confidence import assess_metric_confidence
from .registry import MetricRegistry, default_metric_registry
from .schemas import MetricResult
from .syntactic_features import extract_syntactic_features
from app.calf import SyntacticUnitSegmenter, default_calf_registry


class SpacyAnalyzer:
    analyzer_id = "spacy"
    version = "spacy-analyzer-v0.8.0"
    backend = "spacy"

    def __init__(
        self, *, model_name: str = "en_core_web_sm", mattr_window: int = 50,
        local_repetition_window: int = 30, long_sentence_threshold: int = 30,
        configuration_version: str = "nlp-config-v0.4.0", registry: MetricRegistry | None = None,
        mtld_threshold: float = 0.72, mtld_calculate_reverse: bool = True,
        mtld_minimum_tokens: int = 10, hdd_sample_size: int = 42,
    ) -> None:
        import spacy

        self.spacy = spacy
        self.model_name = model_name
        self.nlp = spacy.load(model_name)
        self.mattr_window = mattr_window
        self.local_repetition_window = local_repetition_window
        self.long_sentence_threshold = long_sentence_threshold
        self.configuration_version = configuration_version
        self.registry = registry or default_metric_registry()
        self.calf_registry = default_calf_registry()
        self.unit_segmenter = SyntacticUnitSegmenter()
        self.mtld_threshold = mtld_threshold
        self.mtld_calculate_reverse = mtld_calculate_reverse
        self.mtld_minimum_tokens = mtld_minimum_tokens
        self.hdd_sample_size = hdd_sample_size
        self.connectives = ConnectiveFeatureExtractor()
        self.quality = InputQualityService()
        self.model_version = importlib.metadata.version(model_name.replace("-", "_"))

    def analyze(self, text: str, *, writing_prompt: str = "", draft_stage: str | None = None,
                tool_use: str | None = None) -> AnalysisResult:
        started = time.perf_counter()
        quality = self.quality.inspect(text, draft_stage=draft_stage, tool_use=tool_use)
        doc = self.nlp(text)
        prompt_doc = self.nlp(writing_prompt)
        sentences = list(doc.sents)
        sentence_spans = [(sent.start_char, sent.end_char) for sent in sentences]
        paragraph_spans = _paragraph_spans(text)
        lexical = extract_lexical_features(
            doc, prompt_doc, mattr_window=self.mattr_window,
            local_window=self.local_repetition_window,
            mtld_threshold=self.mtld_threshold,
            mtld_calculate_reverse=self.mtld_calculate_reverse,
            mtld_minimum_tokens=self.mtld_minimum_tokens,
            hdd_sample_size=self.hdd_sample_size,
        )
        connective = self.connectives.extract(text, sentence_spans, paragraph_spans)
        syntactic = extract_syntactic_features(doc, long_sentence_threshold=self.long_sentence_threshold)
        sentence_units = self.unit_segmenter.segment_sentences(doc)
        clause_units = self.unit_segmenter.segment_clause_candidates(doc)
        t_unit_units = self.unit_segmenter.segment_t_unit_candidates(doc)
        words = [token for token in doc if token.is_alpha]
        metrics = {
            "word_count": len(words), "sentence_count": len(sentences),
            "paragraph_count": len(paragraph_spans),
            "average_sentence_length": round(len(words) / len(sentences), 2) if sentences else 0.0,
            "unique_word_count": len({token.text.lower() for token in words}),
            "type_token_ratio": lexical["type_token_ratio"],
            "connective_count": len(connective["detected_connectives"]),
            "repeated_content_words": lexical["repeated_content_words"],
            "repetition_density": lexical["repetition_density"],
            "lexical_density": lexical["lexical_density"], "mattr": lexical["mattr"],
            "mtld": lexical["mtld"].get("value"), "hdd": lexical["hdd"].get("value"),
            "finite_verb_candidates": len(syntactic["finite_verb_candidates"]),
            "subordinate_clause_candidates": len(syntactic["subordinate_clause_candidates"]),
            "coordination_candidates": len(syntactic["coordination_candidates"]),
            "clause_like_dependency_candidates": {
                dep: len(items) for dep, items in syntactic["clause_like_dependency_candidates_by_type"].items()
            },
            "coordinator_token_count": len(syntactic["coordinator_tokens"]),
            "conjunct_dependency_count": len(syntactic["conjunct_dependencies"]),
            "coordinated_structure_candidates": len(syntactic["coordinated_structure_candidates"]),
            "mean_dependency_tree_depth": syntactic["mean_dependency_tree_depth"],
            "mean_noun_phrase_length": syntactic["mean_noun_phrase_length"],
            "long_sentence_candidates": len(syntactic["long_sentence_candidates"]),
            "clause_candidate_count": len(clause_units),
            "t_unit_candidate_count": len(t_unit_units),
        }
        metric_results = self._metric_results(metrics, lexical, connective, syntactic)
        annotations = [
            {
                "token_id": f"T{token.i+1:04d}", "text": token.text, "lemma": token.lemma_,
                "pos": token.pos_, "tag": token.tag_, "dependency": token.dep_,
                "head_token_id": f"T{token.head.i+1:04d}", "start_offset": token.idx,
                "end_offset": token.idx + len(token.text),
                "sentence_id": next((i for i, sent in enumerate(sentences, 1) if sent.start <= token.i < sent.end), None),
            }
            for token in doc
        ]
        return AnalysisResult(
            metrics=metrics, analysis_version=self.version, analyzer_id=self.analyzer_id,
            analyzer_version=self.version, backend=self.backend, nlp_library="spacy",
            nlp_library_version=self.spacy.__version__, nlp_model_name=self.model_name,
            nlp_model_version=self.model_version,
            parameters={"mattr_window": self.mattr_window, "local_repetition_window": self.local_repetition_window,
                        "long_sentence_threshold": self.long_sentence_threshold,
                        "mtld_factor_threshold": self.mtld_threshold,
                        "mtld_calculate_reverse": self.mtld_calculate_reverse,
                        "mtld_minimum_tokens": self.mtld_minimum_tokens,
                        "hdd_sample_size": self.hdd_sample_size},
            resource_versions={"connectives": self.connectives.version, "input_quality": self.quality.version},
            configuration_version=self.configuration_version,
            analysis_duration_ms=round((time.perf_counter() - started) * 1000, 3),
            input_quality=quality.model_dump(mode="json"),
            artifacts={"tokens": annotations, "lexical_features": lexical, "connective_features": connective,
                       "syntactic_features": syntactic,
                       "analysis_units": [item.model_dump(mode="json") for item in [*sentence_units, *clause_units, *t_unit_units]],
                       "analysis_unit_registry_version": "analysis-unit-registry-v0.8.0",
                       "analysis_text_hash": quality.analysis_text_hash},
            metric_results=[item.model_dump(mode="json") for item in metric_results],
            limitations=(
                "spaCy parser and dictionary features are automatic prototype signals that may misanalyse learner text. "
                "They are feedback inputs, not a complete CALF analysis or measure of learner ability."
            ),
        )

    def _metric_results(self, metrics: dict, lexical: dict, connective: dict, syntactic: dict) -> list[MetricResult]:
        results: list[MetricResult] = []
        deprecated_aggregate_ids = {"subordinate_clause_candidates", "coordination_candidates"}
        for definition in self.registry.latest_list():
            if definition.metric_id in deprecated_aggregate_ids:
                continue
            value = metrics.get(definition.metric_id)
            status = "available"
            if definition.metric_id == "mattr" and lexical["mattr_status"] == "insufficient_data":
                status = "insufficient_data"
            if definition.metric_id == "mtld" and lexical["mtld"]["status"] != "available":
                status = "insufficient_data"
            if definition.metric_id == "hdd" and lexical["hdd"]["status"] != "available":
                status = "insufficient_data"
            evidence = []
            if definition.metric_id == "connective_count":
                evidence = connective["detected_connectives"]
            elif definition.metric_id == "repeated_content_words":
                evidence = lexical["repeated_content_word_details"]
            elif definition.metric_id == "finite_verb_candidates":
                evidence = syntactic["finite_verb_candidates"]
            elif definition.metric_id == "clause_like_dependency_candidates":
                evidence = [item for items in syntactic["clause_like_dependency_candidates_by_type"].values() for item in items]
            elif definition.metric_id == "coordinator_token_count":
                evidence = syntactic["coordinator_tokens"]
            elif definition.metric_id == "conjunct_dependency_count":
                evidence = syntactic["conjunct_dependencies"]
            elif definition.metric_id == "coordinated_structure_candidates":
                evidence = syntactic["coordinated_structure_candidates"]
            metadata = self._measurement_metadata(definition.metric_id, lexical, syntactic)
            parameters = {"mattr_window": self.mattr_window} if definition.metric_id == "mattr" else {}
            if definition.metric_id == "mtld":
                parameters = {"factor_threshold": self.mtld_threshold, "calculate_reverse": self.mtld_calculate_reverse,
                              "minimum_tokens": self.mtld_minimum_tokens}
            if definition.metric_id == "hdd":
                parameters = {"sample_size": self.hdd_sample_size, "short_text_policy": "unavailable"}
            confidence = assess_metric_confidence(
                definition.metric_id, status=status, token_count=lexical["type_token_ratio_protocol"]["token_count_used"],
                fallback_used=False, model_available=bool(self.model_version), parameters={**parameters, **metadata},
                resource_versions={"connectives": self.connectives.version} if definition.metric_id == "connective_count" else {},
            )
            confidence.pop("measurement_status", None)
            try:
                specification = self.calf_registry.get_specification(definition.metric_id)
            except ValueError:
                specification = None
            if specification and specification.measurement_status.value == "automatic_candidate":
                confidence["eligible_for_diagnosis"] = False
                confidence["eligible_for_longitudinal_comparison"] = False
            results.append(MetricResult(
                metric_id=definition.metric_id, metric_version=definition.metric_version,
                value=value, unit=definition.unit, parameters=parameters,
                analyzer_version=self.version,
                resource_versions={"connectives": self.connectives.version} if definition.metric_id == "connective_count" else {},
                status=status, evidence=evidence, limitations=[*definition.limitations, *confidence.pop("limitations")],
                measurement_metadata=metadata,
                measurement_status=specification.measurement_status.value if specification else ("unavailable" if status != "available" else "available"),
                automation_level=specification.automation_level.value if specification else None,
                construct_id=specification.construct_id if specification else None,
                subconstruct_id=specification.subconstruct_id if specification else None,
                analysis_unit_version=specification.analysis_unit_version if specification else None,
                numerator=metadata.get("numerator_count"), denominator=metadata.get("denominator_count"),
                intermediate_values=self._intermediate_values(definition.metric_id, lexical),
                eligible_for_revision_priority=False, eligible_for_targeted_practice=False,
                **confidence,
            ))
        return results

    @staticmethod
    def _measurement_metadata(metric_id: str, lexical: dict, syntactic: dict) -> dict:
        if metric_id in {"word_count", "unique_word_count", "type_token_ratio"}:
            return lexical["type_token_ratio_protocol"]
        if metric_id == "mattr":
            return lexical["mattr_protocol"]
        if metric_id == "mtld":
            return {key: value for key, value in lexical["mtld"].items() if key not in {"value", "forward", "reverse"}}
        if metric_id == "hdd":
            return {key: value for key, value in lexical["hdd"].items() if key not in {"value", "type_probabilities"}}
        if metric_id == "lexical_density":
            return lexical["lexical_density_protocol"]
        if metric_id in {"repeated_content_words", "repetition_density"}:
            return {
                **lexical["repetition_protocol"],
                "numerator_count": lexical["repetition_density_numerator"],
                "denominator_count": lexical["repetition_density_denominator"],
            }
        if metric_id == "finite_verb_candidates":
            return {
                "finite_tags": ["VBD", "VBP", "VBZ", "MD"], "finite_morphology": "VerbForm=Fin",
                "auxiliary_policy": "finite AUX counted once; non-finite lexical participle not independently finite",
                "coordinated_verb_policy": "each parser token meeting the finite rule is a candidate",
            }
        if metric_id == "clause_like_dependency_candidates":
            return {"dependency_types": sorted(syntactic["clause_like_dependency_candidates_by_type"]),
                    "confirmed_clause_count": False}
        if metric_id in {"coordinator_token_count", "conjunct_dependency_count", "coordinated_structure_candidates"}:
            return {"counts_are_separate": True, "confirmed_structure_count": False}
        return {}

    @staticmethod
    def _intermediate_values(metric_id: str, lexical: dict) -> dict:
        if metric_id == "mtld":
            item = lexical["mtld"]
            return {"forward": item.get("forward"), "reverse": item.get("reverse"),
                    "forward_value": item.get("forward_value"), "reverse_value": item.get("reverse_value")}
        if metric_id == "hdd":
            item = lexical["hdd"]
            return {"type_frequencies": item.get("type_frequencies", {}),
                    "type_probabilities": item.get("type_probabilities", {}),
                    "probability_sum": item.get("probability_sum")}
        return {}


def _paragraph_spans(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in re.finditer(r"\S(?:.*?\S)?(?=(?:\r?\n\s*){2,}|\Z)", text, re.DOTALL)]
