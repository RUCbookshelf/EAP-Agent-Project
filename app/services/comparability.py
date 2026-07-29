from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.config.longitudinal import RULES, LongitudinalRules
from app.core import ComparabilityResult


class ComparabilityService:
    def __init__(self, rules: LongitudinalRules = RULES) -> None:
        self.rules = rules

    def compare(self, current: dict[str, Any], historical: dict[str, Any]) -> ComparabilityResult:
        current_id = self._id(current)
        historical_id = self._id(historical)
        matched: list[str] = []
        mismatched: list[str] = []
        reasons: list[str] = []

        necessary = {
            "student_id": current.get("student_id") == historical.get("student_id"),
            "valid_text": bool(str(current.get("essay_text", "")).strip()) and bool(str(historical.get("essay_text", "")).strip()),
            "metrics_available": bool(current.get("metrics")) and bool(historical.get("metrics")),
        }
        for condition, ok in necessary.items():
            (matched if ok else mismatched).append(condition)
        if not all(necessary.values()):
            reasons.append("Necessary comparison information is missing or invalid: " + ", ".join(k for k, v in necessary.items() if not v) + ".")
            status = "not_comparable" if necessary["student_id"] is False else "insufficient_information"
            return ComparabilityResult(
                current_submission_id=current_id, historical_submission_id=historical_id,
                status=status, matched_conditions=matched, mismatched_conditions=mismatched,
                reasons=reasons, confidence="insufficient", rule_version=self.rules.rule_version,
            )

        if current.get("genre") != historical.get("genre"):
            mismatched.append("genre")
            reasons.append("Genre differs; the earlier submission is excluded from the primary trend cohort.")
            status = "not_comparable"
        else:
            matched.append("genre")
            status = "comparable"

        for field in ("timed", "tool_use", "draft_stage"):
            if current.get(field) == historical.get(field):
                matched.append(field)
            else:
                mismatched.append(field)
                reasons.append(f"{field} differs and limits task-condition comparability.")
                if status == "comparable": status = "partially_comparable"

        if current.get("timed") and historical.get("timed"):
            if current.get("time_limit_minutes") == historical.get("time_limit_minutes"):
                matched.append("time_limit_minutes")
            else:
                mismatched.append("time_limit_minutes")
                reasons.append("Recorded time limits differ.")
                if status == "comparable": status = "partially_comparable"

        similarity = self._prompt_similarity(str(current.get("writing_prompt", "")), str(historical.get("writing_prompt", "")))
        if similarity >= self.rules.prompt_similarity_floor:
            matched.append("writing_prompt_or_task_family")
        else:
            mismatched.append("writing_prompt_or_task_family")
            reasons.append(f"Prompt lexical overlap is limited ({similarity:.2f}); topic/task differences constrain interpretation.")
            if status == "comparable": status = "partially_comparable"

        current_words = self._numeric_metric(current, "word_count")
        historical_words = self._numeric_metric(historical, "word_count")
        ratio = abs(current_words - historical_words) / max(current_words, historical_words, 1.0)
        if ratio <= self.rules.large_word_count_ratio:
            matched.append("word_count_range")
        else:
            mismatched.append("word_count_range")
            reasons.append(f"Word-count difference ratio is {ratio:.2f}, above the prototype limit.")
            if status == "comparable": status = "partially_comparable"

        if current.get("analysis_version") == historical.get("analysis_version"):
            matched.append("analysis_version")
        else:
            mismatched.append("analysis_version")
            reasons.append("Analysis versions differ; metric estimates may not be directly compatible.")
            if status == "comparable": status = "partially_comparable"

        interval_hours = abs((self._datetime(current) - self._datetime(historical)).total_seconds()) / 3600
        if interval_hours < self.rules.short_interval_hours:
            mismatched.append("submission_interval")
            reasons.append("Submission interval is very short and may reflect the same immediate writing episode.")
            if status == "comparable": status = "partially_comparable"
        elif interval_hours > self.rules.long_interval_days * 24:
            mismatched.append("submission_interval")
            reasons.append("Submission interval is very long; unrecorded instruction or context may differ.")
            if status == "comparable": status = "partially_comparable"
        else:
            matched.append("submission_interval")

        if not reasons:
            reasons.append("Recorded necessary and important task conditions are sufficiently aligned for prototype comparison.")
        confidence = "medium" if status == "comparable" else "low"
        return ComparabilityResult(
            current_submission_id=current_id, historical_submission_id=historical_id,
            status=status, matched_conditions=matched, mismatched_conditions=mismatched,
            reasons=reasons, confidence=confidence, rule_version=self.rules.rule_version,
        )

    @staticmethod
    def _id(record: dict[str, Any]) -> str:
        return f"E{int(record.get('essay_id', 0)):06d}"

    @staticmethod
    def _numeric_metric(record: dict[str, Any], name: str) -> float:
        value = record.get("metrics", {}).get(name, 0)
        if isinstance(value, dict):
            return float(sum(value.values()))
        return float(value)

    @staticmethod
    def _prompt_similarity(left: str, right: str) -> float:
        tokenize = lambda value: set(re.findall(r"[a-z]+", value.casefold()))
        a, b = tokenize(left), tokenize(right)
        if not a or not b: return 0.0
        return len(a & b) / len(a | b)

    @staticmethod
    def _datetime(record: dict[str, Any]) -> datetime:
        value = record.get("submitted_at")
        if isinstance(value, datetime): return value
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
