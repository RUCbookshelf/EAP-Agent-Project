from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.configuration import ConfigurationPayload
from app.models import LongitudinalAssessment, LongitudinalFeedback, StructuredFeedback

if TYPE_CHECKING:
    from app.llm.base import FeedbackContext


DEFAULT_RISKY_ABILITY_PHRASES = (
    "strong linguistic control", "advanced proficiency", "high rhetorical awareness",
    "mastery", "excellent command of english", "sophisticated writer",
    "native-like control", "native-like", "high-level writer",
    "superior writing ability", "superior ability",
)


class FeedbackReliabilityService:
    """Apply deterministic v0.7.1 facts without replacing valid feedback sections."""

    def __init__(self, configuration: ConfigurationPayload | None = None) -> None:
        self.configuration = configuration or ConfigurationPayload()

    def assessment(self, context: "FeedbackContext") -> LongitudinalAssessment:
        snapshot = context.learner_profile_snapshot
        if snapshot is None:
            comparable = max(0, context.history.comparable_submission_count)
            draft_count = max(1, comparable + 1)
            revision_groups = 1 if context.revision_snapshot is not None else 0
            total_independent = comparable + 1
            source_limitations = list(context.history.limitations)
        else:
            clusters = snapshot.task_clusters
            comparable = max(
                (len(cluster.representative_submission_ids) for cluster in clusters),
                default=len(snapshot.representative_submission_ids),
            )
            summary = snapshot.comparability_summary
            draft_count = int(summary.get("draft_submission_count") or len(snapshot.source_submission_ids) or 1)
            revision_groups = int(summary.get("revision_group_count") or 0)
            total_independent = int(
                summary.get("independent_task_count")
                or (snapshot.data_sufficiency.independent_task_count if snapshot.data_sufficiency else comparable)
            )
            source_limitations = list(snapshot.limitations)

        minimum = self.configuration.learner_model_min_pairwise_tasks
        if comparable < minimum:
            status = "not_comparable" if total_independent >= minimum else "unavailable"
        elif comparable < self.configuration.learner_model_min_direction_tasks:
            status = "pairwise_only"
        elif comparable < self.configuration.learner_model_adequate_tasks:
            status = "provisional_pattern"
        else:
            status = "descriptive_trend_available"

        history_ids = []
        if status not in {"unavailable", "not_comparable"}:
            allowed_ids = None
            if snapshot is not None:
                allowed_ids = {
                    evidence_id for target in snapshot.current_learning_targets
                    for evidence_id in target.history_evidence_ids
                }
            history_ids = [
                item.history_evidence_id for item in context.history.history_evidence
                if item.history_evidence_id
                and (allowed_ids is None or item.history_evidence_id in allowed_ids)
            ][:self.configuration.learner_model_max_feedback_evidence]
        limitations = [
            "Cross-task status describes available compatible records, not proficiency or ability growth.",
            *source_limitations[:2],
        ]
        assessment = LongitudinalAssessment(
            status=status, scope="cross_task", comparable_task_count=comparable,
            minimum_required=minimum, revision_group_count=revision_groups,
            draft_count=draft_count, comment="", history_evidence_ids=history_ids,
            limitations=list(dict.fromkeys(limitations)),
        )
        return assessment.model_copy(update={"comment": self.default_comment(assessment)})

    @staticmethod
    def default_comment(assessment: LongitudinalAssessment) -> str:
        if assessment.status == "unavailable":
            revision_clause = (
                " Multiple drafts within the same revision group support within-task revision analysis, "
                "but they do not count as separate evidence for cross-task development."
                if assessment.draft_count > assessment.comparable_task_count
                and assessment.revision_group_count > 0 else ""
            )
            return (
                "Longitudinal judgment is currently unavailable because only "
                f"{assessment.comparable_task_count} comparable independent writing task"
                f"{' is' if assessment.comparable_task_count == 1 else 's are'} available."
                + revision_clause
            )
        if assessment.status == "not_comparable":
            return (
                "Cross-task longitudinal judgment is currently unavailable because the independent "
                "writing tasks do not form a sufficiently comparable task cluster."
            )
        if assessment.status == "pairwise_only":
            return (
                "Two comparable independent writing tasks support a pairwise descriptive comparison only; "
                "they do not establish a longitudinal trend or ability change."
            )
        if assessment.status == "provisional_pattern":
            return (
                "The compatible independent tasks support a provisional descriptive pattern. "
                "This is not a validated trend, proficiency judgment, or ability-growth claim."
            )
        return (
            "The compatible independent tasks support a descriptive trend under the current prototype rules. "
            "The result remains task-specific and is not a proficiency or ability-growth judgment."
        )

    def repair(
        self, feedback: StructuredFeedback, context: "FeedbackContext",
    ) -> tuple[StructuredFeedback, list[str]]:
        repair_fields: list[str] = []
        positive = feedback.positive_finding
        if self.configuration.positive_finding_prohibit_ability_inference and self._has_risky_phrase(
            positive.explanation
        ):
            positive = positive.model_copy(update={
                "explanation": (
                    "This exact passage shows an observable feature in the current text; "
                    "it does not establish the writer's overall ability or proficiency."
                )
            })
            repair_fields.append("positive_finding.explanation")

        # The structured longitudinal contract is version-gated. Older prompt
        # contexts keep their original evidence binding and validation rules.
        if context.longitudinal_assessment is None:
            return feedback.model_copy(update={"positive_finding": positive}), repair_fields

        authoritative = context.longitudinal_assessment
        model_comment = feedback.longitudinal.comment.strip()
        if self._comment_is_compatible(model_comment, authoritative):
            comment = model_comment
        else:
            comment = self.default_comment(authoritative)
            repair_fields.append("longitudinal_assessment.comment")
        authoritative = authoritative.model_copy(update={"comment": comment})
        confidence = (
            "medium" if authoritative.status == "descriptive_trend_available" else "low"
        )
        legacy = LongitudinalFeedback(
            comment=comment,
            history_evidence_ids=authoritative.history_evidence_ids,
            confidence=confidence,
            limitation=authoritative.limitations[0],
        )

        return feedback.model_copy(update={
            "positive_finding": positive,
            "longitudinal": legacy,
            "longitudinal_assessment": authoritative,
        }), repair_fields

    def _has_risky_phrase(self, value: str) -> bool:
        configured = tuple(self.configuration.positive_finding_risky_ability_phrases)
        phrases = configured or DEFAULT_RISKY_ABILITY_PHRASES
        lowered = value.casefold()
        return any(phrase.casefold() in lowered for phrase in phrases)

    @staticmethod
    def _comment_is_compatible(comment: str, assessment: LongitudinalAssessment) -> bool:
        if not comment:
            return False
        lowered = comment.casefold()
        if re.search(r"\b(improved|improvement|progress|growth|mastery|proficiency increased|ability increased)\b", lowered):
            return False
        if assessment.status in {"unavailable", "not_comparable"}:
            if assessment.history_evidence_ids:
                return False
            return not re.search(r"\b(trend|pattern across|development shows|has developed)\b", lowered)
        if assessment.status == "pairwise_only":
            return bool(re.search(r"\b(pairwise|two comparable|two independent|comparison only)\b", lowered)) and not bool(
                re.search(r"\b(long[- ]term trend|stable trend|clear trend|unavailable|insufficient history)\b", lowered)
            )
        if assessment.status == "provisional_pattern":
            return "provisional" in lowered and "pattern" in lowered and "unavailable" not in lowered
        if assessment.status == "descriptive_trend_available":
            return "descriptive trend" in lowered and "unavailable" not in lowered
        return False
