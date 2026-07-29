from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LongitudinalRules:
    rule_version: str = "comparability-v0.3.0"
    analysis_version: str = "longitudinal-v0.3.0"
    configuration_version: str = "longitudinal-config-v0.3.0"
    minimum_baseline_submissions: int = 3
    minimum_trend_points: int = 3
    direction_relative_change: float = 0.10
    low_variability_cv: float = 0.10
    high_variability_cv: float = 0.25
    large_word_count_ratio: float = 0.50
    prompt_similarity_floor: float = 0.25
    short_interval_hours: float = 1.0
    long_interval_days: float = 730.0
    recent_window: int = 2
    minimum_prior_occurrences_for_reduction: int = 2


RULES = LongitudinalRules()

METRIC_NAMES = (
    "word_count", "sentence_count", "paragraph_count", "average_sentence_length",
    "unique_word_count", "type_token_ratio", "connective_count", "repeated_content_words",
)

DESCRIPTIVE_METRICS = {"word_count", "sentence_count", "paragraph_count"}
LENGTH_SENSITIVE_METRICS = {
    "unique_word_count", "type_token_ratio", "connective_count", "repeated_content_words"
}
