from __future__ import annotations

import re

from app.models import AnalysisResult, DiagnosisSignal


class EvidenceRelevanceValidator:
    version = "evidence-relevance-v0.6.1"

    def assess_signal(self, signal: DiagnosisSignal, analysis: AnalysisResult) -> tuple[str, list[str]]:
        candidates = [item for item in signal.evidence_quote_candidates if item.strip()]
        if signal.category == "lexical_repetition":
            term = str(signal.evidence_metadata.get("target_lemma", "")).lower()
            relevant = [quote for quote in candidates if re.search(rf"\b{re.escape(term)}\w*\b", quote.lower())]
            return ("verified", relevant) if relevant else ("irrelevant", [])
        if signal.category == "connective_use":
            if not signal.evidence_metadata.get("specific_location"):
                return "insufficient_evidence", []
            return ("verified", candidates) if candidates else ("insufficient_evidence", [])
        if signal.category == "sentence_structure_candidate":
            flagged = signal.evidence_metadata.get("flagged_sentence", "")
            return ("verified", [flagged]) if flagged and flagged in candidates else ("irrelevant", [])
        if signal.category == "input_quality":
            span = signal.evidence_metadata.get("flag_span", "")
            return ("verified", [span]) if span and span in candidates else ("irrelevant", [])
        if signal.category.startswith("revision_"):
            alignment_ids = signal.evidence_metadata.get("supporting_alignment_ids", [])
            metric_change = signal.evidence_metadata.get("metric_change")
            if alignment_ids or metric_change:
                return ("verified", candidates) if candidates else ("partially_verified", [])
            return "insufficient_evidence", []
        if signal.kind == "strength":
            return ("verified", candidates) if candidates else ("insufficient_evidence", [])
        return "partially_verified" if candidates else "insufficient_evidence", candidates

    def validate_feedback_quote(self, signal: DiagnosisSignal, quote: str,
                                analysis: AnalysisResult) -> str:
        normalized = self._normalize(quote)
        allowed = [self._normalize(item) for item in signal.evidence_quote_candidates]
        if signal.category == "lexical_repetition":
            term = str(signal.evidence_metadata.get("target_lemma", "")).lower()
            if not re.search(rf"\b{re.escape(term)}\w*\b", normalized.lower()):
                return "irrelevant"
        if signal.category == "connective_use" and not signal.evidence_metadata.get("specific_location"):
            return "insufficient_evidence"
        if signal.category.startswith("revision_") and not (
            signal.evidence_metadata.get("supporting_alignment_ids")
            or signal.evidence_metadata.get("metric_change")
        ):
            return "insufficient_evidence"
        if allowed and not any(normalized in item or item in normalized for item in allowed):
            return "irrelevant"
        return "verified"

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()
