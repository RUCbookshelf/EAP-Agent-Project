from __future__ import annotations

from typing import Any

from .schemas import MetricConfidence


PARSER_METRICS = {
    "finite_verb_candidates", "clause_like_dependency_candidates",
    "coordinator_token_count", "conjunct_dependency_count",
    "coordinated_structure_candidates", "mean_dependency_tree_depth",
    "mean_noun_phrase_length",
}
DICTIONARY_METRICS = {"connective_count"}
LEXICAL_METRICS = {
    "word_count", "unique_word_count", "type_token_ratio", "mattr",
    "lexical_density", "repeated_content_words", "repetition_density",
}


def assess_metric_confidence(
    metric_id: str,
    *,
    status: str,
    token_count: int,
    fallback_used: bool,
    model_available: bool,
    parameters: dict[str, Any] | None = None,
    resource_versions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Transparent engineering confidence, not reliability or measurement validity."""
    parameters = parameters or {}
    resource_versions = resource_versions or {}
    reasons: list[str] = []
    risks: list[str] = []
    limitations: list[str] = []

    if status == "not_applicable":
        return _result("not_applicable", reasons, risks, False, False, limitations)
    if status != "available":
        reasons.append("The minimum valid data requirement was not met.")
        return _result("insufficient", reasons, risks, False, False, limitations)
    if fallback_used:
        reasons.append("The requested Analyzer failed and a fallback Analyzer produced this result.")
        risks.append("Fallback tokenization and resources differ from the configured spaCy pipeline.")
        return _result("low", reasons, risks, metric_id in {"word_count", "sentence_count", "paragraph_count"}, False, limitations)

    if token_count < 20:
        reasons.append(f"Only {token_count} alphabetic tokens were available.")
        risks.append("Short texts make lexical and parser-derived signals unstable.")
        return _result("low", reasons, risks, False, False, limitations)

    if metric_id in PARSER_METRICS:
        reasons.append("The pinned spaCy model produced complete parser annotations." if model_available else "Parser model status is unavailable.")
        risks.append("Parser nodes are candidates, not confirmed linguistic structures.")
        confidence: MetricConfidence = "medium" if model_available and token_count >= 80 else "low"
        return _result(confidence, reasons, risks, confidence == "medium", confidence == "medium", limitations)

    if metric_id in DICTIONARY_METRICS:
        reasons.append("A versioned connective resource was applied to the complete text.")
        risks.append("Dictionary coverage is incomplete; non-detection is not absence of cohesion.")
        return _result("medium" if resource_versions else "low", reasons, risks, False, bool(resource_versions), limitations)

    if metric_id in LEXICAL_METRICS:
        reasons.append(f"The calculation used {token_count} alphabetic spaCy tokens.")
        if metric_id == "mattr":
            reasons.append(f"Configured MATTR window is {parameters.get('window_size', parameters.get('mattr_window'))}.")
            risks.append("MATTR depends on token definition, normalization and window size.")
        if metric_id in {"repeated_content_words", "repetition_density"}:
            risks.append("Repetition candidates depend on lemma, POS and necessary-term heuristics.")
        confidence = "high" if token_count >= 150 and metric_id in {"word_count", "unique_word_count", "type_token_ratio"} else "medium"
        return _result(confidence, reasons, risks, True, token_count >= 50, limitations)

    reasons.append("The metric was calculated from the complete Analyzer output.")
    return _result("medium", reasons, risks, True, token_count >= 50, limitations)


def _result(confidence: MetricConfidence, reasons: list[str], risks: list[str],
            eligible_diagnosis: bool, eligible_longitudinal: bool,
            limitations: list[str]) -> dict[str, Any]:
    return {
        "measurement_status": "not_applicable" if confidence == "not_applicable" else "insufficient_data" if confidence == "insufficient" else "available",
        "confidence": confidence,
        "confidence_reasons": reasons,
        "risk_factors": risks,
        "eligible_for_diagnosis": eligible_diagnosis,
        "eligible_for_longitudinal_comparison": eligible_longitudinal,
        "limitations": limitations,
    }
