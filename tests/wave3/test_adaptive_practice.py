"""AdaptivePracticeService: deterministic explainable recommendation default,
explicit learner choice, qualified subset from existing practice capability,
provenance preservation, and honest insufficient-history states."""

from __future__ import annotations

import pytest

from app.l2.wave2.corpus_routing import LocalWrittenCorpusRouter
from app.l2.wave2.personalized import PersonalizedBridgeService
from app.l2.wave2.repository import InMemoryRevisionLoopRepository
from app.l2.wave2.revision_loop import RevisionLoopService
from app.l2.wave3.adaptive_practice import AdaptivePracticeService
from app.l2.wave3.adapters import ExistingPracticeActivitySource
from app.learner.normative import NormativeClaimsScanner
from tests.wave2_l2_pipeline import V1_SHORT_REPETITIVE, build_real_pipeline


SCANNER = NormativeClaimsScanner()
PROMPT_A = "Take a position on studying abroad and support it with reasons."


@pytest.fixture
def adaptive(tmp_path):
    """Real-pipeline adaptive-practice fixture with one stored plan."""
    pipeline, repository, _ = build_real_pipeline(tmp_path)
    revision_service = RevisionLoopService(
        repository=InMemoryRevisionLoopRepository(),
        pipeline=pipeline,
        routing=LocalWrittenCorpusRouter(),
    )
    task = revision_service.create_task(
        student_id="L-ADAPT-01", task_type="argumentative",
        writing_context="ielts_task2", writing_prompt=PROMPT_A,
    )
    v1 = revision_service.submit_v1(task.task_id, V1_SHORT_REPETITIVE)
    personalized = PersonalizedBridgeService(
        repository=revision_service.repository,
        pipeline=pipeline,
        routing=LocalWrittenCorpusRouter(),
    )
    personalized.build_priority_plan(
        "L-ADAPT-01", task.task_id, v1.submission_id,
    )
    service = AdaptivePracticeService(
        repository=revision_service.repository,
        pipeline=pipeline,
        activity_source=ExistingPracticeActivitySource(),
    )
    return {
        "service": service,
        "pipeline": pipeline,
        "repository": revision_service.repository,
        "task": task,
        "v1": v1,
    }


class TestRecommendationDefault:
    def test_recommendation_is_deterministic_and_explainable(self, adaptive) -> None:
        service = adaptive["service"]
        first = service.recommend("L-ADAPT-01")
        second = service.recommend("L-ADAPT-01")
        assert first.recommendation_id == second.recommendation_id
        assert first.default_activity_id == second.default_activity_id
        assert first.state == "recommended"
        assert first.learner_choice_allowed is True
        assert first.reasons  # explainable reasons are mandatory
        assert first.qualified_activities  # meaningful qualified subset

    def test_qualified_subset_comes_from_existing_practice_capability(
        self, adaptive,
    ) -> None:
        recommendation = adaptive["service"].recommend("L-ADAPT-01")
        for activity in recommendation.qualified_activities:
            assert activity.exercise_version == "exercise-v0.9.0"
            assert activity.evaluation_criteria["evaluation_method"] == "rule_based"
            assert activity.target_code
        default = next(
            activity for activity in recommendation.qualified_activities
            if activity.activity_id == recommendation.default_activity_id
        )
        assert default.activity_id

    def test_provenance_preserved_from_stored_plan(self, adaptive) -> None:
        recommendation = adaptive["service"].recommend("L-ADAPT-01")
        for activity in recommendation.qualified_activities:
            assert activity.source_submission_id == adaptive["v1"].submission_id
            assert activity.evidence_ids  # provenance never empty
            assert activity.claims_status == "observation_only"
        assert SCANNER.scan_mapping(recommendation.model_dump(mode="json")) == []

    def test_learner_explicit_choice_honored(self, adaptive) -> None:
        service = adaptive["service"]
        recommendation = service.recommend("L-ADAPT-01")
        subset_ids = {activity.activity_id for activity in recommendation.qualified_activities}
        assert len(subset_ids) >= 1
        picked = sorted(subset_ids)[-1]
        selection = service.select(
            "L-ADAPT-01", recommendation.recommendation_id, picked,
        )
        assert selection.choice_kind == "explicit"
        assert selection.activity.activity_id == picked
        assert selection.recommendation_id == recommendation.recommendation_id

    def test_default_selection_matches_default_activity(self, adaptive) -> None:
        service = adaptive["service"]
        recommendation = service.recommend("L-ADAPT-01")
        selection = service.select(
            "L-ADAPT-01", recommendation.recommendation_id,
            recommendation.default_activity_id,
        )
        assert selection.choice_kind == "default"
        assert selection.activity.activity_id == recommendation.default_activity_id

    def test_learner_isolation_on_selection(self, adaptive) -> None:
        service = adaptive["service"]
        recommendation = service.recommend("L-ADAPT-01")
        with pytest.raises(LookupError):
            service.select(
                "L-OTHER-99", recommendation.recommendation_id,
                recommendation.default_activity_id,
            )

    def test_unknown_activity_rejected(self, adaptive) -> None:
        service = adaptive["service"]
        recommendation = service.recommend("L-ADAPT-01")
        with pytest.raises(LookupError):
            service.select(
                "L-ADAPT-01", recommendation.recommendation_id, "QA999999",
            )


class TestInsufficientHistory:
    def test_no_history_is_never_fabricated(self, adaptive) -> None:
        recommendation = adaptive["service"].recommend("L-NEVER-SEEN")
        assert recommendation.state == "insufficient_history"
        assert recommendation.qualified_activities == []
        assert recommendation.default_activity_id is None
        assert recommendation.learner_choice_allowed is False
        assert any(
            "nothing" in reason.casefold() or "no stored" in reason.casefold()
            for reason in recommendation.reasons
        )


class TestDeterministicEvaluation:
    def test_rule_based_evaluation_of_attempt(self, adaptive) -> None:
        service = adaptive["service"]
        recommendation = service.recommend("L-ADAPT-01")
        evaluation = service.evaluate(
            "L-ADAPT-01", recommendation.default_activity_id,
            "Parks are good for health and bring communities together.",
        )
        assert evaluation.evaluation_method == "rule_based"
        assert evaluation.evaluator_version
        assert evaluation.evidence
        assert evaluation.claims_status == "observation_only"
        assert SCANNER.scan_mapping(evaluation.model_dump(mode="json")) == []

    def test_evaluation_is_deterministic(self, adaptive) -> None:
        service = adaptive["service"]
        recommendation = service.recommend("L-ADAPT-01")
        text = "Parks are good for health and bring communities together."
        first = service.evaluate("L-ADAPT-01", recommendation.default_activity_id, text)
        second = service.evaluate("L-ADAPT-01", recommendation.default_activity_id, text)
        assert first.model_dump(mode="json") == second.model_dump(mode="json")

    def test_unknown_activity_evaluation_rejected(self, adaptive) -> None:
        with pytest.raises(LookupError):
            adaptive["service"].evaluate("L-ADAPT-01", "QA999999", "text")
