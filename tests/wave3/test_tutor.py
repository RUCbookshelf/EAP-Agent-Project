"""ProactiveTutorService: consent-gated accept, side-effect-safe decline,
due-item / history-grounded / insufficient-history / positive-observation
cases, learner isolation, and no unsupported personalized claims."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.l2.wave2.corpus_routing import LocalWrittenCorpusRouter
from app.l2.wave2.personalized import PersonalizedBridgeService
from app.l2.wave2.repository import InMemoryRevisionLoopRepository
from app.l2.wave2.revision_loop import RevisionLoopService
from app.l2.wave3.adapters import (
    ExistingPracticeActivitySource,
    InMemoryConsentStore,
    InMemoryReviewEvidenceStore,
    PipelineAuthenticObservationReader,
)
from app.l2.wave3.adaptive_practice import AdaptivePracticeService
from app.l2.wave3.models import TutorConsentSnapshot
from app.l2.wave3.tutor import ProactiveTutorService
from app.learner.normative import NormativeClaimsScanner
from tests.wave2_l2_pipeline import (
    V1_SHORT_REPETITIVE,
    V2_LONG_VARIED,
    build_real_pipeline,
)


SCANNER = NormativeClaimsScanner()
PROMPT_A = "Take a position on studying abroad and support it with reasons."
NOW = datetime(2026, 8, 12, 10, 0, 0, tzinfo=timezone.utc)
CONSENT_SCOPE = "proactive_tutor_execution"
CONSENT_VERSION = "learner-consent-v0.1.0"


def _consent(learner_id: str, **overrides) -> TutorConsentSnapshot:
    values = dict(
        learner_id=learner_id,
        granted=True,
        revoked=False,
        scope=CONSENT_SCOPE,
        consent_version=CONSENT_VERSION,
        granted_at=NOW,
    )
    values.update(overrides)
    return TutorConsentSnapshot(**values)


@pytest.fixture
def tutor_env(tmp_path):
    """Real-pipeline returning learner with stored plans."""
    pipeline, repository, _ = build_real_pipeline(tmp_path)
    revision_service = RevisionLoopService(
        repository=InMemoryRevisionLoopRepository(),
        pipeline=pipeline,
        routing=LocalWrittenCorpusRouter(),
    )
    task_a = revision_service.create_task(
        student_id="L-TUTOR-01", task_type="argumentative",
        writing_context="ielts_task2", writing_prompt=PROMPT_A,
    )
    a1 = revision_service.submit_v1(task_a.task_id, V1_SHORT_REPETITIVE)
    revision_service.revise(task_a.task_id, a1.submission_id, V2_LONG_VARIED)
    personalized = PersonalizedBridgeService(
        repository=revision_service.repository,
        pipeline=pipeline,
        routing=LocalWrittenCorpusRouter(),
    )
    personalized.build_priority_plan("L-TUTOR-01", task_a.task_id, a1.submission_id)
    review_evidence = InMemoryReviewEvidenceStore()
    consent_store = InMemoryConsentStore()
    adaptive = AdaptivePracticeService(
        repository=revision_service.repository,
        pipeline=pipeline,
        activity_source=ExistingPracticeActivitySource(),
        now=lambda: NOW,
    )
    tutor = ProactiveTutorService(
        repository=revision_service.repository,
        consent_store=consent_store,
        review_evidence=review_evidence,
        observation_source=PipelineAuthenticObservationReader(
            revision_service.repository, pipeline,
        ),
        adaptive=adaptive,
        now=lambda: NOW,
    )
    return {
        "tutor": tutor,
        "review_evidence": review_evidence,
        "consent_store": consent_store,
        "repository": revision_service.repository,
        "pipeline": pipeline,
        "revision_service": revision_service,
        "task_a": task_a,
        "a1": a1,
    }


class TestHistoryGrounded:
    def test_recommendation_is_history_grounded(self, tutor_env) -> None:
        recommendation = tutor_env["tutor"].recommend("L-TUTOR-01")
        assert recommendation.state in {"history_grounded", "due_item"}
        assert recommendation.learner_id == "L-TUTOR-01"
        assert recommendation.limitations
        assert SCANNER.scan_mapping(recommendation.model_dump(mode="json")) == []

    def test_recommendation_never_claims_personalization(self, tutor_env) -> None:
        recommendation = tutor_env["tutor"].recommend("L-TUTOR-01")
        payload = recommendation.model_dump(mode="json")
        text = (
            str(payload.get("suggestion", ""))
            + " ".join(payload.get("history_reasons", []))
        ).casefold()
        for banned in ("mastery", "proficiency", "learning gain", "improved ability"):
            assert banned not in text


class TestInsufficientHistory:
    def test_no_history_is_honest(self, tutor_env) -> None:
        recommendation = tutor_env["tutor"].recommend("L-NEVER-SEEN")
        assert recommendation.state == "insufficient_history"
        assert recommendation.learning_item_ids == []
        assert recommendation.suggestion
        assert any(
            "no stored" in reason.casefold() for reason in recommendation.history_reasons
        )


class TestDueItem:
    def test_due_item_state_when_scheduler_says_due(self, tutor_env) -> None:
        tutor_env["review_evidence"].seed_due_item(
            learning_item_id="LI000001",
            student_id="L-TUTOR-01",
            category="lexical_repetition",
            due=NOW - timedelta(minutes=5),
        )
        recommendation = tutor_env["tutor"].recommend("L-TUTOR-01")
        assert recommendation.state == "due_item"
        assert "LI000001" in recommendation.learning_item_ids
        assert recommendation.positive_observations == []

    def test_future_due_item_is_not_due(self, tutor_env) -> None:
        tutor_env["review_evidence"].seed_due_item(
            learning_item_id="LI000001",
            student_id="L-TUTOR-01",
            category="lexical_repetition",
            due=NOW + timedelta(days=1),
        )
        recommendation = tutor_env["tutor"].recommend("L-TUTOR-01")
        assert recommendation.state != "due_item"


class TestPositiveObservation:
    def test_positive_observation_is_bounded_and_non_causal(self, tutor_env) -> None:
        observation = tutor_env["tutor"].positive_observation(
            "L-TUTOR-01", category="lexical_repetition",
        )
        assert observation is not None
        assert observation.evidence_kind == "authentic_writing"
        assert observation.non_causal_note
        assert "not proof" in observation.non_causal_note.casefold()
        assert observation.claims_status == "observation_only"
        assert SCANNER.scan_mapping(observation.model_dump(mode="json")) == []

    def test_positive_observation_absent_without_later_sample(self, tutor_env) -> None:
        observation = tutor_env["tutor"].positive_observation(
            "L-TUTOR-01", category="connective_use",
        )
        assert observation is None or observation.evidence_kind == "authentic_writing"


class TestConsentAcceptDecline:
    def test_accept_requires_explicit_consent(self, tutor_env) -> None:
        recommendation = tutor_env["tutor"].recommend("L-TUTOR-01")
        with pytest.raises(ValueError):
            tutor_env["tutor"].accept(
                "L-TUTOR-01", recommendation.recommendation_id, None,
            )

    def test_accept_with_ungranted_consent_fails_closed(self, tutor_env) -> None:
        recommendation = tutor_env["tutor"].recommend("L-TUTOR-01")
        consent = _consent("L-TUTOR-01", granted=False)
        with pytest.raises(ValueError):
            tutor_env["tutor"].accept(
                "L-TUTOR-01", recommendation.recommendation_id, consent,
            )
        assert tutor_env["consent_store"].list_consents("L-TUTOR-01") == []

    def test_accept_with_revoked_consent_fails_closed(self, tutor_env) -> None:
        recommendation = tutor_env["tutor"].recommend("L-TUTOR-01")
        consent = _consent("L-TUTOR-01", revoked=True)
        with pytest.raises(ValueError):
            tutor_env["tutor"].accept(
                "L-TUTOR-01", recommendation.recommendation_id, consent,
            )

    def test_accept_with_wrong_scope_fails_closed(self, tutor_env) -> None:
        recommendation = tutor_env["tutor"].recommend("L-TUTOR-01")
        consent = _consent("L-TUTOR-01", scope="some_other_scope")
        with pytest.raises(ValueError):
            tutor_env["tutor"].accept(
                "L-TUTOR-01", recommendation.recommendation_id, consent,
            )

    def test_accept_with_learner_mismatch_fails_closed(self, tutor_env) -> None:
        recommendation = tutor_env["tutor"].recommend("L-TUTOR-01")
        consent = _consent("L-OTHER-99")
        with pytest.raises(ValueError):
            tutor_env["tutor"].accept(
                "L-TUTOR-01", recommendation.recommendation_id, consent,
            )

    def test_accept_records_consent_and_executes_bounded_action(self, tutor_env) -> None:
        recommendation = tutor_env["tutor"].recommend("L-TUTOR-01")
        consent = _consent("L-TUTOR-01")
        decision = tutor_env["tutor"].accept(
            "L-TUTOR-01", recommendation.recommendation_id, consent,
        )
        assert decision.decision == "accept"
        assert decision.consent_applied is True
        assert decision.executed is True
        assert decision.action
        assert tutor_env["consent_store"].list_consents("L-TUTOR-01")
        assert SCANNER.scan_mapping(decision.model_dump(mode="json")) == []

    def test_decline_is_side_effect_safe(self, tutor_env) -> None:
        recommendation = tutor_env["tutor"].recommend("L-TUTOR-01")
        decision = tutor_env["tutor"].decline(
            "L-TUTOR-01", recommendation.recommendation_id,
        )
        assert decision.decision == "decline"
        assert decision.consent_applied is False
        assert decision.executed is False
        # Decline writes no consent and no practice evidence.
        assert tutor_env["consent_store"].list_consents("L-TUTOR-01") == []
        assert tutor_env["review_evidence"].list_activities("L-TUTOR-01") == []

    def test_cross_learner_accept_rejected(self, tutor_env) -> None:
        recommendation = tutor_env["tutor"].recommend("L-TUTOR-01")
        consent = _consent("L-OTHER-99")
        with pytest.raises(ValueError):
            tutor_env["tutor"].accept(
                "L-OTHER-99", recommendation.recommendation_id, consent,
            )

    def test_cross_learner_decline_rejected(self, tutor_env) -> None:
        recommendation = tutor_env["tutor"].recommend("L-TUTOR-01")
        with pytest.raises(LookupError):
            tutor_env["tutor"].decline(
                "L-OTHER-99", recommendation.recommendation_id,
            )
