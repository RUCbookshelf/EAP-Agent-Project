from __future__ import annotations

from collections import Counter
from math import comb
from typing import Any


def _mtld_direction(tokens: list[str], threshold: float, minimum_factor_length: int) -> dict[str, Any]:
    factors = 0.0
    segment_tokens = 0
    segment_types: set[str] = set()
    completed_factor_lengths: list[int] = []
    running_ttr = 1.0
    for index, token in enumerate(tokens):
        segment_tokens += 1
        segment_types.add(token)
        running_ttr = len(segment_types) / segment_tokens
        if index < len(tokens) - 1 and running_ttr < threshold and segment_tokens >= minimum_factor_length:
            factors += 1.0
            completed_factor_lengths.append(segment_tokens)
            segment_tokens = 0
            segment_types = set()
            running_ttr = 1.0
    partial_factor = 0.0
    if segment_tokens:
        partial_factor = (1.0 - running_ttr) / (1.0 - threshold)
        partial_factor = max(0.0, partial_factor)
        factors += partial_factor
    value = len(tokens) / factors if factors > 0 else None
    return {
        "value": value,
        "factor_count": factors,
        "completed_factor_count": len(completed_factor_lengths),
        "completed_factor_lengths": completed_factor_lengths,
        "partial_factor": partial_factor,
        "remaining_segment_token_count": segment_tokens,
        "remaining_segment_ttr": running_ttr if segment_tokens else None,
    }


def calculate_mtld(tokens: list[str], *, threshold: float = 0.72,
                   calculate_reverse: bool = True, minimum_tokens: int = 10) -> dict[str, Any]:
    """Deterministic original-factor MTLD with explicit partial-factor accounting."""
    if not 0 < threshold < 1:
        raise ValueError("MTLD threshold must be between zero and one")
    normalized = [token.lower() for token in tokens if token]
    base = {
        "metric_id": "mtld", "token_count": len(normalized), "factor_threshold": threshold,
        "normalization": "lowercase_surface_alphabetic_tokens",
        "partial_factor_method": "(1-current_segment_ttr)/(1-factor_threshold)",
        "minimum_tokens": minimum_tokens, "calculate_reverse": calculate_reverse,
    }
    if len(normalized) < minimum_tokens:
        return {**base, "status": "insufficient_data", "value": None,
                "reason": f"MTLD requires at least {minimum_tokens} normalized tokens."}
    forward = _mtld_direction(normalized, threshold, minimum_tokens)
    reverse = _mtld_direction(list(reversed(normalized)), threshold, minimum_tokens) if calculate_reverse else None
    available_values = [item["value"] for item in (forward, reverse) if item and item["value"] is not None]
    if not available_values:
        return {
            **base, "status": "insufficient_data", "value": None,
            "reason": "No complete or partial MTLD factor was observed under the configured threshold.",
            "forward": forward, "reverse": reverse,
        }
    combined = sum(available_values) / len(available_values)
    return {
        **base, "status": "available", "value": combined,
        "forward_value": forward["value"],
        "reverse_value": reverse["value"] if reverse else None,
        "combined_value": combined, "forward": forward, "reverse": reverse,
    }


def calculate_hdd(tokens: list[str], *, sample_size: int = 42) -> dict[str, Any]:
    """Expected sample TTR under sampling without replacement (HD-D)."""
    if sample_size < 1:
        raise ValueError("HD-D sample_size must be positive")
    normalized = [token.lower() for token in tokens if token]
    token_count = len(normalized)
    frequencies = dict(sorted(Counter(normalized).items()))
    base = {
        "metric_id": "hdd", "token_count": token_count, "sample_size": sample_size,
        "effective_sample_size": sample_size if token_count >= sample_size else None,
        "normalization": "lowercase_surface_alphabetic_tokens", "type_frequencies": frequencies,
        "hypergeometric_method": "sum(1-C(N-f,n)/C(N,n))/n",
        "short_text_policy": "unavailable_when_token_count_is_below_configured_sample_size",
    }
    if token_count < sample_size:
        return {
            **base, "status": "insufficient_data", "value": None,
            "reason": "HD-D token count is below the configured sample size; the sample size was not reduced silently.",
            "type_probabilities": {}, "probability_sum": None,
        }
    denominator = comb(token_count, sample_size)
    probabilities = {
        token_type: 1.0 - (comb(token_count - frequency, sample_size) / denominator
                           if token_count - frequency >= sample_size else 0.0)
        for token_type, frequency in frequencies.items()
    }
    probability_sum = sum(probabilities.values())
    return {
        **base, "status": "available", "value": probability_sum / sample_size,
        "type_probabilities": probabilities, "probability_sum": probability_sum,
    }
