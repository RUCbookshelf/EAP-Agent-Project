from __future__ import annotations

import re
import time
from collections import Counter

from app.models import AnalysisResult

from .base import Analyzer


WORD_RE = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)?")
SENTENCE_RE = re.compile(r"[^.!?]+(?:[.!?]+|$)")
CONNECTIVES = (
    "however", "therefore", "moreover", "furthermore", "nevertheless",
    "consequently", "although", "because", "firstly", "secondly", "finally",
    "in addition", "for example", "for instance", "on the other hand", "as a result",
)
STOPWORDS = {
    "about", "after", "again", "also", "because", "before", "being", "could",
    "every", "first", "from", "have", "into", "more", "other", "should", "some",
    "than", "that", "their", "there", "these", "they", "this", "those", "through",
    "very", "what", "when", "where", "which", "while", "with", "would", "your",
}


class BasicAnalyzer(Analyzer):
    analyzer_id = "basic"
    version = "basic-analyzer-v0.1"
    backend = "regex"

    def analyze(self, text: str, *, writing_prompt: str = "", draft_stage: str | None = None,
                tool_use: str | None = None) -> AnalysisResult:
        from app.analysis.input_quality import InputQualityService

        started = time.perf_counter()
        words = [w.lower().replace("’", "'") for w in WORD_RE.findall(text)]
        sentences = [s.strip() for s in SENTENCE_RE.findall(text) if WORD_RE.search(s)]
        paragraphs = [p for p in re.split(r"\r?\n\s*\r?\n", text.strip()) if p.strip()]
        counts = Counter(words)
        repeated = {
            word: count for word, count in sorted(counts.items())
            if count >= 3 and len(word) >= 4 and word not in STOPWORDS
        }
        lowered = text.lower()
        connective_count = sum(len(re.findall(rf"\b{re.escape(item)}\b", lowered)) for item in CONNECTIVES)
        word_count = len(words)
        from app.calf import calculate_hdd, calculate_mtld
        mtld = calculate_mtld(words)
        hdd = calculate_hdd(words)
        sentence_count = len(sentences)
        metrics = {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "paragraph_count": len(paragraphs) if text.strip() else 0,
            "average_sentence_length": round(word_count / sentence_count, 2) if sentence_count else 0.0,
            "unique_word_count": len(set(words)),
            "type_token_ratio": round(len(set(words)) / word_count, 3) if word_count else 0.0,
            "connective_count": connective_count,
            "repeated_content_words": repeated,
            "mtld": mtld.get("value"), "hdd": hdd.get("value"),
        }
        quality = InputQualityService().inspect(text, draft_stage=draft_stage, tool_use=tool_use)
        metric_versions = {
            "word_count": "1.0.0", "sentence_count": "1.0.0", "paragraph_count": "1.0.0",
            "average_sentence_length": "1.0.0", "unique_word_count": "1.0.0",
            "type_token_ratio": "1.0.0", "connective_count": "2.0.0",
            "repeated_content_words": "2.0.0",
            "mtld": "0.8.0", "hdd": "0.8.0",
        }
        metric_results = [
            {
                "metric_id": metric_id, "metric_version": metric_versions[metric_id],
                "value": value, "unit": "prototype", "parameters": {},
                "analyzer_version": self.version, "resource_versions": {},
                "verification_status": "automatic_unverified",
                "status": (mtld["status"] if metric_id == "mtld" else hdd["status"] if metric_id == "hdd" else "available"),
                "measurement_status": "research_metric" if metric_id in {"mtld", "hdd"} else "available",
                "automation_level": "deterministic" if metric_id in {"mtld", "hdd"} else None,
                "construct_id": "lexical_complexity" if metric_id in {"mtld", "hdd"} else None,
                "subconstruct_id": "lexical_diversity" if metric_id in {"mtld", "hdd"} else None,
                "analysis_unit_version": "basic-regex-word-v0.8.0" if metric_id in {"mtld", "hdd"} else None,
                "confidence": "low" if value is not None else "insufficient",
                "confidence_reasons": ["A regex-only fallback Analyzer produced this metric."],
                "risk_factors": ["Tokenization and linguistic resources differ from the spaCy pipeline."],
                "eligible_for_diagnosis": metric_id in {"word_count", "sentence_count", "paragraph_count"},
                "eligible_for_longitudinal_comparison": False,
                "measurement_metadata": ({key: val for key, val in (mtld if metric_id == "mtld" else hdd).items()
                                          if key not in {"value", "forward", "reverse", "type_probabilities"}}
                                         if metric_id in {"mtld", "hdd"} else {
                    "token_definition": "basic_regex_words", "normalization": "lowercase_surface",
                    "lemma_used": False, "punctuation_excluded": True, "numbers_excluded": True,
                    "token_count_used": word_count, "type_count_used": len(set(words)),
                } if metric_id in {"word_count", "unique_word_count", "type_token_ratio"} else {}),
                "intermediate_values": ({"forward": mtld.get("forward"), "reverse": mtld.get("reverse")}
                                        if metric_id == "mtld" else
                                        {"type_frequencies": hdd.get("type_frequencies", {}),
                                         "type_probabilities": hdd.get("type_probabilities", {})}
                                        if metric_id == "hdd" else {}),
                "eligible_for_revision_priority": False, "eligible_for_targeted_practice": False,
                "evidence": [], "limitations": ["Fallback metric; do not silently compare with spaCy metric versions."],
            }
            for metric_id, value in metrics.items()
        ]
        return AnalysisResult(
            metrics=metrics,
            analysis_version=self.version,
            analyzer_id=self.analyzer_id,
            analyzer_version=self.version,
            backend=self.backend,
            parameters={},
            resource_versions={"input_quality": InputQualityService.version},
            configuration_version="basic-config-v0.1",
            analysis_duration_ms=round((time.perf_counter() - started) * 1000, 3),
            input_quality=quality.model_dump(mode="json"),
            artifacts={"analysis_text_hash": quality.analysis_text_hash},
            metric_results=metric_results,
            limitations=(
                "Prototype heuristic counts based on surface forms. This is not a complete CALF analysis "
                "and must not be interpreted as a measure of learner ability."
            ),
        )
