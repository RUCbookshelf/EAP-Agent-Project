from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.models import StructuredFeedback

if TYPE_CHECKING:
    from app.llm.base import FeedbackContext


class FeedbackValidationError(ValueError):
    def __init__(self, failures: list[str]):
        self.failures = failures
        super().__init__("; ".join(failures))


class FeedbackValidator:
    """Enforce evidence bindings after Pydantic shape validation."""

    def validate(self, feedback: StructuredFeedback, context: "FeedbackContext") -> None:
        failures: list[str] = []
        essay = self._normalize_whitespace(context.submission.essay_text)
        improvement = {
            signal.diagnosis_id: signal
            for signal in context.diagnosis.improvement_priorities
        }
        history_ids = {
            evidence.history_evidence_id for evidence in context.history.history_evidence
        }

        self._validate_quote(feedback.positive_finding.evidence_quote, essay, "positive_finding", failures)
        for index, item in enumerate(feedback.priority_feedback):
            signal = improvement.get(item.diagnosis_id)
            if signal is None:
                failures.append(f"priority_feedback[{index}] has unknown diagnosis_id {item.diagnosis_id}")
            elif item.category != signal.category:
                failures.append(
                    f"priority_feedback[{index}] category does not match {item.diagnosis_id}"
                )
            self._validate_quote(item.evidence_quote, essay, f"priority_feedback[{index}]", failures)

        used_history = feedback.longitudinal.history_evidence_ids
        unknown_history = sorted(set(used_history) - history_ids)
        if unknown_history:
            failures.append("unknown history_evidence_id: " + ", ".join(unknown_history))
        if not history_ids:
            if used_history:
                failures.append("history_evidence_ids must be empty when no history evidence exists")
            if self._contains_deterministic_development_claim(feedback.longitudinal.comment):
                failures.append("deterministic development claim is forbidden without history evidence")
            if not re.search(
                r"cannot|not possible|insufficient|unable|无法|不足",
                feedback.longitudinal.comment, flags=re.IGNORECASE,
            ):
                failures.append("no-history longitudinal comment must explicitly state that judgment is unavailable")
        elif not used_history:
            failures.append("longitudinal comment must bind at least one available history_evidence_id")

        for index, exercise in enumerate(feedback.exercises):
            signal = improvement.get(exercise.diagnosis_id)
            if signal is None:
                failures.append(f"exercises[{index}] has unknown diagnosis_id {exercise.diagnosis_id}")
            elif exercise.diagnosis_category != signal.category:
                failures.append(
                    f"exercises[{index}] category does not match {exercise.diagnosis_id}"
                )

        if failures:
            raise FeedbackValidationError(failures)

    def _validate_quote(self, quote: str, normalized_essay: str,
                        location: str, failures: list[str]) -> None:
        normalized_quote = self._normalize_whitespace(quote)
        if not normalized_quote or normalized_quote not in normalized_essay:
            failures.append(f"{location} evidence_quote is not a verbatim essay substring")

    @staticmethod
    def _normalize_whitespace(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _contains_deterministic_development_claim(value: str) -> bool:
        patterns = (
            r"\b(has|have|clearly|definitely)\s+(improved|declined|regressed|mastered)\b",
            r"\b(student|learner)\s+(improved|declined|regressed|mastered)\b",
            r"\b(student(?:'s)?|learner(?:'s)?|writer(?:'s)?|writing|language ability|proficiency|performance)"
            r"\b.{0,45}\b(shows?|demonstrates?|proves?|confirms?|indicates?|achieved?|made|has|is)"
            r"\b.{0,20}\b(improvement|progress|growth|decline|regression|mastery|better|worse)\b",
            r"\b(ability|proficiency|performance)\s+(has\s+)?"
            r"(increased|decreased|improved|declined|advanced|regressed)\b",
            r"\b(has|have)\s+(shown|made|demonstrated|achieved)\s+"
            r"(improvement|progress|growth|mastery|decline|regression)\b",
            r"能力(?:已经)?(?:提升|下降)",
            r"已经(?:掌握|退步|提高|进步)",
            r"(?:表现|水平)(?:明显|已经)?(?:提高|下降|进步|退步)",
        )
        return any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in patterns)
