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
        }
        quality = InputQualityService().inspect(text, draft_stage=draft_stage, tool_use=tool_use)
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
            limitations=(
                "Prototype heuristic counts based on surface forms. This is not a complete CALF analysis "
                "and must not be interpreted as a measure of learner ability."
            ),
        )
