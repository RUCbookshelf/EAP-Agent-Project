from __future__ import annotations

from typing import Any, Iterable

from .schemas import ErrorAnnotation, TimingQuality


ACCURACY_UNAVAILABLE_REASON = "validated error annotations are not available"


def accuracy_availability(annotations: Iterable[ErrorAnnotation]) -> dict[str, Any]:
    eligible = [item for item in annotations if item.eligible_for_formal_accuracy]
    if not eligible:
        return {
            "measurement_status": "unavailable", "value": None,
            "reason": ACCURACY_UNAVAILABLE_REASON, "eligible_annotation_count": 0,
        }
    return {
        "measurement_status": "manual_annotation_required", "value": None,
        "reason": "Validated annotations are available for future manually specified Accuracy measures.",
        "eligible_annotation_count": len(eligible),
    }


def writing_output_rate(*, word_count: int, timed: bool,
                        active_writing_duration_seconds: float | None,
                        timing_quality: str | None, accepted_timing_quality: Iterable[str],
                        input_quality_acceptable: bool = True,
                        unexplained_interruption: bool = False) -> dict[str, Any]:
    accepted = {str(item) for item in accepted_timing_quality}
    quality = timing_quality or TimingQuality.UNAVAILABLE.value
    base = {
        "metric_id": "writing_output_rate_wpm", "metric_version": "0.8.0",
        "measurement_status": "descriptive_proxy", "automation_level": "deterministic",
        "word_count": word_count, "active_writing_duration_seconds": active_writing_duration_seconds,
        "timing_quality": quality, "accepted_timing_quality": sorted(accepted),
        "time_limit_used": False, "eligible_for_diagnosis": False,
        "eligible_for_longitudinal_comparison": False,
    }
    reason = None
    if not timed:
        reason = "The submission is not recorded as timed writing."
    elif active_writing_duration_seconds is None:
        reason = "Actual writing duration is unavailable; the task time limit is not used."
    elif active_writing_duration_seconds <= 0:
        reason = "Actual writing duration must be greater than zero."
    elif quality not in accepted:
        reason = "Timing quality does not meet the configured requirement."
    elif not input_quality_acceptable:
        reason = "Input quality does not support output-rate calculation."
    elif unexplained_interruption:
        reason = "An unexplained interruption makes active duration unreliable."
    if reason:
        return {**base, "status": "unavailable", "value": None, "reason": reason}
    value = word_count / (active_writing_duration_seconds / 60.0)
    return {
        **base, "status": "available", "value": value,
        "numerator": word_count, "denominator": active_writing_duration_seconds / 60.0,
        "eligible_for_longitudinal_comparison": True,
        "limitations": ["Output rate describes production conditions and is not a writing-fluency ability score."],
    }


def append_product_fluency_metric(analysis, submission, *, accepted_timing_quality=("verified", "estimated")):
    """Return an AnalysisResult copy with an auditable output-rate result; never use the task limit."""
    item = writing_output_rate(
        word_count=int(analysis.metrics.get("word_count") or 0), timed=submission.timed,
        active_writing_duration_seconds=submission.active_writing_duration_seconds,
        timing_quality=submission.timing_quality,
        accepted_timing_quality=accepted_timing_quality,
        input_quality_acceptable=not bool((analysis.input_quality or {}).get("exclude_from_longitudinal")),
        unexplained_interruption=submission.unexplained_interruption,
    )
    available = item["status"] == "available"
    result = {
        "metric_id": "writing_output_rate_wpm", "metric_version": "0.8.0",
        "value": item.get("value"), "unit": "words_per_minute",
        "parameters": {"accepted_timing_quality": item["accepted_timing_quality"],
                       "require_actual_duration": True, "time_limit_used": False},
        "analyzer_version": analysis.analyzer_version, "resource_versions": {},
        "verification_status": "automatic_unverified",
        "status": "available" if available else "insufficient_data",
        "measurement_status": "descriptive_proxy", "automation_level": "deterministic",
        "construct_id": "product_fluency", "subconstruct_id": "writing_output_rate",
        "analysis_unit_version": "timed-writing-event-v0.8.0",
        "confidence": "medium" if available and submission.timing_quality == "verified" else "low" if available else "insufficient",
        "confidence_reasons": ["Actual active-writing duration and normalized word count were used."] if available else [],
        "risk_factors": ["Output rate is a production-condition proxy, not a fluency ability score."],
        "eligible_for_diagnosis": False,
        "eligible_for_longitudinal_comparison": item.get("eligible_for_longitudinal_comparison", False),
        "eligible_for_revision_priority": False, "eligible_for_targeted_practice": False,
        "measurement_metadata": {
            "timed": submission.timed, "time_limit_minutes": submission.time_limit_minutes,
            "time_limit_used": False, "timing_source": submission.timing_source,
            "timing_quality": submission.timing_quality,
            "active_writing_duration_seconds": submission.active_writing_duration_seconds,
            "reason": item.get("reason"),
        },
        "numerator": item.get("numerator"), "denominator": item.get("denominator"),
        "intermediate_values": {"duration_minutes": item.get("denominator")},
        "evidence": [], "limitations": item.get("limitations", [item.get("reason")]),
    }
    metrics = {**analysis.metrics, "writing_output_rate_wpm": item.get("value")}
    prior = [value for value in analysis.metric_results if value.get("metric_id") != "writing_output_rate_wpm"]
    return analysis.model_copy(update={"metrics": metrics, "metric_results": [*prior, result]})
