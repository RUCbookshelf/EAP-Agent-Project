"""AdaptivePracticeService: qualified activity recommendation + evaluation.

Selects a meaningful qualified activity subset from the EXISTING practice
capability (``app.practice`` exercise specifications) using a deterministic,
explainable recommendation default while allowing an explicit learner choice.
Source/provenance/evaluation criteria are preserved on every activity and
never fabricated: learners without stored evidence receive an honest
``insufficient_history`` state.
"""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
from typing import Any, Callable

from app.l2.wave2.pipeline import WritingPipelinePort
from app.l2.wave2.repository import RevisionLoopRepository
from app.l2.wave3.models import (
    ActivityEvaluation,
    ActivityRecommendation,
    ActivitySelection,
    OBSERVATION_ONLY,
    QualifiedActivity,
)
from app.l2.wave3.protocols import PracticeActivitySource
from app.models.schemas import utc_now


EVALUATOR_VERSION = "practice-evaluator-v0.9.0"
ACTIVITY_LIMITATION = (
    "Activities are practice suggestions; they are descriptive only and do "
    "not establish outcomes."
)


def _diagnosis_categories(bundle: dict[str, Any] | None) -> set[str]:
    if not bundle:
        return set()
    return {
        str(item.get("category"))
        for item in (bundle.get("diagnosis") or {}).get("improvement_priorities", [])
        if item.get("category")
    }


class AdaptivePracticeService:
    """Deterministic adaptive-practice recommendation over existing specs."""

    def __init__(
        self,
        *,
        repository: RevisionLoopRepository,
        pipeline: WritingPipelinePort,
        activity_source: PracticeActivitySource,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.pipeline = pipeline
        self.activity_source = activity_source
        self._now = now or utc_now
        self._recommendations: dict[tuple[str, str], ActivityRecommendation] = {}

    # ------------------------------------------------------------------
    # Recommendation
    # ------------------------------------------------------------------

    def recommend(self, learner_id: str) -> ActivityRecommendation:
        plans = self.repository.list_priority_plans(learner_id)
        learning_items = self.repository.list_learning_items(learner_id)
        if not plans and not learning_items:
            recommendation = ActivityRecommendation(
                recommendation_id=self._recommendation_id(learner_id, "none"),
                learner_id=learner_id,
                state="insufficient_history",
                default_activity_id=None,
                qualified_activities=[],
                reasons=[
                    "no stored priority plan or learning item exists for this "
                    "learner; nothing was fabricated or substituted",
                ],
                learner_choice_allowed=False,
                limitations=[
                    "Activity selection requires stored evidence; none is "
                    "available for this learner.",
                ],
                claims_status=OBSERVATION_ONLY,
            )
            self._recommendations[(learner_id, recommendation.recommendation_id)] = (
                recommendation
            )
            return recommendation

        categories: OrderedDict[str, str | None] = OrderedDict()
        source_submission_ids: list[int] = []
        evidence_by_category: dict[str, list[str]] = {}
        for plan in plans:
            source_submission_ids.append(plan.submission_id)
            for item in plan.items:
                category = item.category
                if category not in categories:
                    target_code = self.activity_source.target_code_for_category(
                        category,
                    )
                    categories[category] = target_code
                    evidence_by_category[category] = list(item.evidence_refs)
                else:
                    evidence_by_category[category].extend(item.evidence_refs)

        specs = self.activity_source.exercise_specifications()
        qualified: list[QualifiedActivity] = []
        reasons: list[str] = []
        for category, target_code in categories.items():
            if target_code is None:
                reasons.append(
                    f"category '{category}' has no supported practice target "
                    "in the existing practice capability; excluded"
                )
                continue
            source_text = self._source_text_for(category, plans, source_submission_ids)
            matched = False
            for spec in specs.values():
                if (
                    target_code not in spec.supported_target_codes
                    or spec.evaluation_method != "rule_based"
                    or spec.student_eligible is False
                ):
                    continue
                matched = True
                evidence_ids = list(
                    dict.fromkeys(evidence_by_category.get(category, []))
                )
                qualified.append(QualifiedActivity(
                    activity_id=self._activity_id(learner_id, target_code, spec),
                    learner_id=learner_id,
                    target_code=target_code,
                    target_label=spec.learner_instructions.get("en", ""),
                    category=category,
                    exercise_type=spec.exercise_type,
                    exercise_version=spec.exercise_version,
                    source_submission_id=source_submission_ids[-1],
                    source_priority_id=None,
                    evidence_ids=evidence_ids or [str(source_submission_ids[-1])],
                    instructions=spec.learner_instructions.get("en", ""),
                    source_text=source_text,
                    evaluation_criteria={
                        "evaluation_method": spec.evaluation_method,
                        "evaluator_version": EVALUATOR_VERSION,
                        "completion_criteria": spec.completion_criteria,
                        "observable_target_criteria": spec.observable_target_criteria,
                    },
                    limitations=[ACTIVITY_LIMITATION],
                    claims_status=OBSERVATION_ONLY,
                ))
            if not matched:
                reasons.append(
                    f"category '{category}' maps to target '{target_code}' but "
                    "no rule-based student-eligible exercise supports it; excluded"
                )

        if not qualified:
            recommendation = ActivityRecommendation(
                recommendation_id=self._recommendation_id(learner_id, "none"),
                learner_id=learner_id,
                state="unavailable",
                default_activity_id=None,
                qualified_activities=[],
                reasons=[
                    *reasons,
                    "no qualified practice activity is available for the "
                    "learner's stored categories; nothing was fabricated",
                ],
                learner_choice_allowed=False,
                limitations=[
                    "No rule-based activity in the existing practice "
                    "capability supports the learner's stored categories.",
                ],
                claims_status=OBSERVATION_ONLY,
            )
            self._recommendations[(learner_id, recommendation.recommendation_id)] = (
                recommendation
            )
            return recommendation

        default_activity_id = qualified[0].activity_id
        reasons.extend([
            f"qualified subset selected from the existing practice capability "
            f"({len(qualified)} rule-based student-eligible activities)",
            "deterministic default: stored plan order, then exercise-spec "
            "order; the learner may choose any qualified activity explicitly",
        ])
        recommendation = ActivityRecommendation(
            recommendation_id=self._recommendation_id(
                learner_id, default_activity_id,
            ),
            learner_id=learner_id,
            state="recommended",
            default_activity_id=default_activity_id,
            qualified_activities=qualified,
            reasons=reasons,
            learner_choice_allowed=True,
            limitations=[
                "Activities are practice suggestions; they are descriptive "
                "only and do not establish outcomes.",
            ],
            claims_status=OBSERVATION_ONLY,
        )
        self._recommendations[(learner_id, recommendation.recommendation_id)] = (
            recommendation
        )
        return recommendation

    def _source_text_for(
        self,
        category: str,
        plans: list[Any],
        source_submission_ids: list[int],
    ) -> str:
        for plan in reversed(plans):
            bundle = self.pipeline.get_submission_bundle(plan.submission_id)
            if bundle is None:
                continue
            if category in _diagnosis_categories(bundle):
                return str(bundle.get("essay_text") or "")[:500]
        bundle = self.pipeline.get_submission_bundle(source_submission_ids[-1])
        return str((bundle or {}).get("essay_text") or "")[:500]

    # ------------------------------------------------------------------
    # Selection (explicit learner choice)
    # ------------------------------------------------------------------

    def select(
        self, learner_id: str, recommendation_id: str, activity_id: str,
    ) -> ActivitySelection:
        recommendation = self._recommendations.get((learner_id, recommendation_id))
        if recommendation is None:
            raise LookupError(
                f"Recommendation {recommendation_id} does not exist for "
                f"learner {learner_id}."
            )
        activity = next(
            (
                item for item in recommendation.qualified_activities
                if item.activity_id == activity_id
            ),
            None,
        )
        if activity is None:
            raise LookupError(
                f"Activity {activity_id} is not in the qualified subset of "
                f"recommendation {recommendation_id}."
            )
        return ActivitySelection(
            selection_id=self._selection_id(learner_id, activity_id),
            learner_id=learner_id,
            recommendation_id=recommendation_id,
            activity=activity,
            choice_kind=(
                "default" if activity_id == recommendation.default_activity_id
                else "explicit"
            ),
            limitations=[
                "Selection is learner-owned; it is descriptive only.",
            ],
            claims_status=OBSERVATION_ONLY,
        )

    # ------------------------------------------------------------------
    # Deterministic evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self, learner_id: str, activity_id: str, response_text: str,
    ) -> ActivityEvaluation:
        activity = self._find_activity(learner_id, activity_id)
        if activity is None:
            raise LookupError(
                f"Activity {activity_id} does not exist for learner {learner_id}."
            )
        result = self.activity_source.evaluate(
            target_code=activity.target_code,
            response_text=response_text,
            source_text=activity.source_text,
        )
        return ActivityEvaluation(
            evaluation_id=self._evaluation_id(learner_id, activity_id),
            learner_id=learner_id,
            activity_id=activity_id,
            completion_status=str(result.get("completion_status", "incomplete")),
            target_action_status=str(
                result.get("target_action_status", "inconclusive")
            ),
            evidence=[str(item) for item in result.get("evidence", [])],
            evaluator_version=str(
                result.get("evaluator_version", EVALUATOR_VERSION)
            ),
            evaluation_method="rule_based",
            limitations=[
                "Observable evidence is task-specific; it is descriptive only.",
            ],
            claims_status=OBSERVATION_ONLY,
        )

    def _find_activity(
        self, learner_id: str, activity_id: str,
    ) -> QualifiedActivity | None:
        for recommendation in self._recommendations.values():
            if recommendation.learner_id != learner_id:
                continue
            for activity in recommendation.qualified_activities:
                if activity.activity_id == activity_id:
                    return activity
        return None

    # ------------------------------------------------------------------
    # Deterministic ids
    # ------------------------------------------------------------------

    def _recommendation_id(self, learner_id: str, anchor: str) -> str:
        safe = "".join(
            character if character.isalnum() else "-"
            for character in anchor
        )[:24]
        return f"AR-{learner_id}-{safe}"

    @staticmethod
    def _activity_id(
        learner_id: str, target_code: str, spec: Any,
    ) -> str:
        exercise_type = str(getattr(spec, "exercise_type", "exercise"))
        return f"QA-{learner_id}-{target_code}-{exercise_type}"

    @staticmethod
    def _selection_id(learner_id: str, activity_id: str) -> str:
        return f"AS-{learner_id}-{activity_id}"

    @staticmethod
    def _evaluation_id(learner_id: str, activity_id: str) -> str:
        return f"AE-{learner_id}-{activity_id}"


__all__ = ["ACTIVITY_LIMITATION", "AdaptivePracticeService", "EVALUATOR_VERSION"]
