from __future__ import annotations

import importlib.metadata
import re
import time
from pathlib import Path

from app.models import AnalysisResult

from .connective_features import ConnectiveFeatureExtractor
from .input_quality import InputQualityService
from .lexical_features import extract_lexical_features
from .registry import MetricRegistry, default_metric_registry
from .schemas import MetricResult
from .syntactic_features import extract_syntactic_features


class SpacyAnalyzer:
    analyzer_id = "spacy"
    version = "spacy-analyzer-v0.4.0"
    backend = "spacy"

    def __init__(
        self, *, model_name: str = "en_core_web_sm", mattr_window: int = 50,
        local_repetition_window: int = 30, long_sentence_threshold: int = 30,
        configuration_version: str = "nlp-config-v0.4.0", registry: MetricRegistry | None = None,
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
        )
        connective = self.connectives.extract(text, sentence_spans, paragraph_spans)
        syntactic = extract_syntactic_features(doc, long_sentence_threshold=self.long_sentence_threshold)
        words = [token for token in doc if token.is_alpha]
        metrics = {
            "word_count": len(words), "sentence_count": len(sentences),
            "paragraph_count": len(paragraph_spans),
            "average_sentence_length": round(len(words) / len(sentences), 2) if sentences else 0.0,
            "unique_word_count": len({token.text.lower() for token in words}),
            "type_token_ratio": lexical["type_token_ratio"],
            "connective_count": len(connective["detected_connectives"]),
            "repeated_content_words": lexical["repeated_content_words"],
            "lexical_density": lexical["lexical_density"], "mattr": lexical["mattr"],
            "finite_verb_candidates": len(syntactic["finite_verb_candidates"]),
            "subordinate_clause_candidates": len(syntactic["subordinate_clause_candidates"]),
            "coordination_candidates": len(syntactic["coordination_candidates"]),
            "mean_dependency_tree_depth": syntactic["mean_dependency_tree_depth"],
            "mean_noun_phrase_length": syntactic["mean_noun_phrase_length"],
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
                        "long_sentence_threshold": self.long_sentence_threshold},
            resource_versions={"connectives": self.connectives.version, "input_quality": self.quality.version},
            configuration_version=self.configuration_version,
            analysis_duration_ms=round((time.perf_counter() - started) * 1000, 3),
            input_quality=quality.model_dump(mode="json"),
            artifacts={"tokens": annotations, "lexical_features": lexical, "connective_features": connective,
                       "syntactic_features": syntactic, "analysis_text_hash": quality.analysis_text_hash},
            metric_results=[item.model_dump(mode="json") for item in metric_results],
            limitations=(
                "spaCy parser and dictionary features are automatic prototype signals that may misanalyse learner text. "
                "They are feedback inputs, not a complete CALF analysis or measure of learner ability."
            ),
        )

    def _metric_results(self, metrics: dict, lexical: dict, connective: dict, syntactic: dict) -> list[MetricResult]:
        results: list[MetricResult] = []
        for definition in self.registry.list():
            value = metrics.get(definition.metric_id)
            status = "available"
            if definition.metric_id == "mattr" and lexical["mattr_status"] == "insufficient_data":
                status = "insufficient_data"
            evidence = []
            if definition.metric_id == "connective_count":
                evidence = connective["detected_connectives"]
            elif definition.metric_id == "repeated_content_words":
                evidence = lexical["repeated_content_word_details"]
            elif definition.metric_id == "finite_verb_candidates":
                evidence = syntactic["finite_verb_candidates"]
            parameters = {"mattr_window": self.mattr_window} if definition.metric_id == "mattr" else {}
            results.append(MetricResult(
                metric_id=definition.metric_id, metric_version=definition.metric_version,
                value=value, unit=definition.unit, parameters=parameters,
                analyzer_version=self.version,
                resource_versions={"connectives": self.connectives.version} if definition.metric_id == "connective_count" else {},
                status=status, evidence=evidence, limitations=definition.limitations,
            ))
        return results


def _paragraph_spans(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in re.finditer(r"\S(?:.*?\S)?(?=(?:\r?\n\s*){2,}|\Z)", text, re.DOTALL)]
