"""ProactiveTutorService: consented, history-aware Tutor orchestration.

Bounded Tutor contract covering recommendation, learner accept, learner
decline, due-item / history-grounded suggestion, insufficient-history, and
positive-observation cases. Explicit learner consent is REQUIRED before any
Tutor execution; decline and unavailable states are side-effect safe (no
consent write, no practice/review evidence write, no execution). No
unsupported personalized claim is ever recorded.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from app.l2.wave2.pipeline import WritingPipelinePort
from app.l2.wave2.repository import RevisionLoopRepository
from app.l2.wave3.adaptive_practice import AdaptivePracticeService
from app.l2.wave3.models import (
    DueItem,
    OBSERVATION_ONLY,
    PositiveObservation,
    TutorConsentSnapshot,
    TutorDecision,
    TutorRecommendation,
)
from app.l2.wave3.protocols import (
    AuthenticWritingObservationPort,
    LearnerConsentStorePort,
    ReviewEvidencePort,
)
from app.models.schemas import utc_now


CONSENT_SCOPE = "proactive_tutor_execution"
CONSENT_VERSION = "learner-consent-v0.1.0"


def _diagnosis_categories(bundle: dict[str, Any] | None) -> set[str]:
    if not bundle:
        return set()
    return {
        str(item.get("category"))
        for item in (bundle.get("diagnosis") or {}).get("improvement_priorities", [])
        if item.get("category")
    }


class ProactiveTutorService:
    """Consented tutor orchestration over stored learner evidence."""

    def __init__(
        self,
        *,
        repository: RevisionLoopRepository,
        consent_store: LearnerConsentStorePort,
        review_evidence: ReviewEvidencePort,
        adaptive: AdaptivePracticeService,
        observation_source: AuthenticWritingObservationPort | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.consent_store = consent_store
        self.review_evidence = review_evidence
        self.adaptive = adaptive
        self.observation_source = observation_source
        self._now = now or utc_now
        self._recommendations: dict[tuple[str, str], TutorRecommendation] = {}

    # ------------------------------------------------------------------
    # Recommendation
    # ------------------------------------------------------------------

    def recommend(self, learner_id: str) -> TutorRecommendation:
        due_items = self._due_items(learner_id)
        if due_items:
            recommendation = TutorRecommendation(
                recommendation_id=self._recommendation_id(
                    learner_id, "due", due_items[0].learning_item_id,
                ),
                learner_id=learner_id,
                state="due_item",
                learning_item_ids=[item.learning_item_id for item in due_items],
                categories=list(
                    dict.fromkeys(item.category for item in due_items)
                ),
                suggestion=(
                    f"{len(due_items)} due review item(s) are available for "
                    "practice; scheduling state is descriptive."
                ),
                history_reasons=[
                    "due per the durable scheduler state",
                ],
                positive_observations=[],
                limitations=[
                    "Scheduling state is descriptive; it is not an outcome "
                    "measure.",
                ],
                claims_status=OBSERVATION_ONLY,
            )
            self._recommendations[(learner_id, recommendation.recommendation_id)] = (
                recommendation
            )
            return recommendation

        plans = self.repository.list_priority_plans(learner_id)
        learning_items = self.repository.list_learning_items(learner_id)
        positive_observations = self._positive_observations(learner_id)
        if not plans and not learning_items and not positive_observations:
            recommendation = TutorRecommendation(
                recommendation_id=self._recommendation_id(learner_id, "none", "none"),
                learner_id=learner_id,
                state="insufficient_history",
                learning_item_ids=[],
                categories=[],
                suggestion=(
                    "No stored history is available for a grounded suggestion; "
                    "nothing was fabricated."
                ),
                history_reasons=[
                    "no stored learning items, plans, or authentic writing "
                    "observations for this learner",
                ],
                positive_observations=[],
                limitations=[
                    "A Tutor suggestion requires stored learner evidence.",
                ],
                claims_status=OBSERVATION_ONLY,
            )
            self._recommendations[(learner_id, recommendation.recommendation_id)] = (
                recommendation
            )
            return recommendation

        categories = list(dict.fromkeys([
            *[item.category for plan in plans for item in plan.items],
            *[item.category for item in learning_items],
        ]))
        recommendation = TutorRecommendation(
            recommendation_id=self._recommendation_id(
                learner_id, "history", ",".join(categories),
            ),
            learner_id=learner_id,
            state="history_grounded",
            learning_item_ids=[item.learning_item_id for item in learning_items],
            categories=categories,
            suggestion=(
                "Stored learner history is available to ground a practice "
                "suggestion; the suggestion is descriptive only."
            ),
            history_reasons=[
                "grounded in stored priority plans and learning items",
            ],
            positive_observations=positive_observations,
            limitations=[
                "History-grounded suggestions are descriptive; they do not "
                "measure the learner or predict outcomes.",
            ],
            claims_status=OBSERVATION_ONLY,
        )
        self._recommendations[(learner_id, recommendation.recommendation_id)] = (
            recommendation
        )
        return recommendation

    def _due_items(self, learner_id: str) -> list[DueItem]:
        now = self._now()
        items = self.review_evidence.list_due_items(learner_id, now=now)
        return [
            DueItem(
                learning_item_id=str(item.learning_item_id),
                student_id=str(item.student_id),
                category=str(item.category),
                due=item.due,
                note=(
                    "memory scheduling state only; it is not an outcome measure"
                ),
            )
            for item in items
        ]

    # ------------------------------------------------------------------
    # Positive bounded observation (authentic writing evidence)
    # ------------------------------------------------------------------

    def positive_observation(
        self, learner_id: str, *, category: str,
    ) -> PositiveObservation | None:
        if self.observation_source is None:
            return None
        samples = self.observation_source.latest_writing_samples(learner_id)
        if len(samples) < 2:
            return None
        latest = samples[-1]
        earlier = samples[:-1]
        latest_categories = _diagnosis_categories(latest)
        if category in latest_categories:
            return None
        if not any(category in _diagnosis_categories(sample) for sample in earlier):
            return None
        target_code = self.adaptive.activity_source.target_code_for_category(category)
        return PositiveObservation(
            observation_id=f"PO-{learner_id}-{category}",
            learner_id=learner_id,
            category=category,
            target_code=target_code or category,
            later_submission_id=int(latest.get("essay_id") or 0),
            statement=(
                f"The targeted feature ('{category}') is not observed in the "
                "latest writing sample."
            ),
            non_causal_note=(
                "Observation only; it is not proof of learning, transfer, or "
                "ability change."
            ),
            evidence_kind="authentic_writing",
            limitations=[
                "A single-sample absence is descriptive only and does not "
                "establish outcomes.",
            ],
            claims_status=OBSERVATION_ONLY,
        )

    def _positive_observations(self, learner_id: str) -> list[PositiveObservation]:
        plans = self.repository.list_priority_plans(learner_id)
        categories = [
            item.category for plan in plans for item in plan.items
        ]
        observations: list[PositiveObservation] = []
        for category in dict.fromkeys(categories):
            observation = self.positive_observation(learner_id, category=category)
            if observation is not None:
                observations.append(observation)
        return observations

    # ------------------------------------------------------------------
    # Accept / decline (consent-gated; side-effect safe)
    # ------------------------------------------------------------------

    def accept(
        self,
        learner_id: str,
        recommendation_id: str,
        consent: TutorConsentSnapshot | None,
    ) -> TutorDecision:
        if (learner_id, recommendation_id) not in self._recommendations:
            raise ValueError(
                f"Recommendation {recommendation_id} does not exist for "
                f"learner {learner_id}."
            )
        self._validate_consent(learner_id, consent)
        self.consent_store.record_consent(consent)
        decision = TutorDecision(
            decision_id=self._decision_id(learner_id, recommendation_id, "accept"),
            learner_id=learner_id,
            recommendation_id=recommendation_id,
            decision="accept",
            consent_applied=True,
            executed=True,
            action=(
                "presented the history-grounded activity suggestion after "
                "explicit learner consent; no external notification or "
                "background delivery was performed"
            ),
            limitations=[
                "No unsupported personalized claim is recorded.",
            ],
            claims_status=OBSERVATION_ONLY,
        )
        return decision

    def decline(self, learner_id: str, recommendation_id: str) -> TutorDecision:
        self._require_recommendation(learner_id, recommendation_id)
        return TutorDecision(
            decision_id=self._decision_id(learner_id, recommendation_id, "decline"),
            learner_id=learner_id,
            recommendation_id=recommendation_id,
            decision="decline",
            consent_applied=False,
            executed=False,
            action=None,
            limitations=[
                "Decline performs no execution and records no practice evidence.",
            ],
            claims_status=OBSERVATION_ONLY,
        )

    def new_consent(self, learner_id: str) -> TutorConsentSnapshot:
        """Build a default granted consent snapshot for the Tutor scope."""
        return TutorConsentSnapshot(
            learner_id=learner_id,
            granted=True,
            revoked=False,
            scope=CONSENT_SCOPE,
            consent_version=CONSENT_VERSION,
            granted_at=self._now(),
        )

    # ------------------------------------------------------------------
    # guards
    # ------------------------------------------------------------------

    def _require_recommendation(
        self, learner_id: str, recommendation_id: str,
    ) -> None:
        if (learner_id, recommendation_id) not in self._recommendations:
            raise LookupError(
                f"Recommendation {recommendation_id} does not exist for "
                f"learner {learner_id}."
            )

    def _validate_consent(
        self,
        learner_id: str,
        consent: TutorConsentSnapshot | None,
    ) -> None:
        if consent is None:
            raise ValueError(
                "Explicit learner consent is required before Tutor execution."
            )
        if consent.learner_id != learner_id:
            raise ValueError(
                "Consent learner does not match the requesting learner."
            )
        if not consent.granted or consent.revoked:
            raise ValueError(
                "Consent must be granted and not revoked before Tutor execution."
            )
        if consent.scope != CONSENT_SCOPE:
            raise ValueError(
                f"Consent scope must be '{CONSENT_SCOPE}' for Tutor execution."
            )
        if not consent.consent_version:
            raise ValueError("Consent version is required.")
        if consent.granted_at.tzinfo is None or consent.granted_at > self._now():
            raise ValueError("Consent must be granted in the present, not the future.")

    @staticmethod
    def _recommendation_id(learner_id: str, kind: str, anchor: str) -> str:
        safe = "".join(
            character if character.isalnum() else "-"
            for character in anchor
        )[:24]
        return f"TR-{learner_id}-{kind}-{safe}"

    @staticmethod
    def _decision_id(
        learner_id: str, recommendation_id: str, kind: str,
    ) -> str:
        return f"TD-{learner_id}-{recommendation_id}-{kind}"


__all__ = [
    "CONSENT_SCOPE",
    "CONSENT_VERSION",
    "ProactiveTutorService",
]
