"""Learner isolation and failure isolation for the WU3 services."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.l2.wave2.corpus_routing import LocalWrittenCorpusRouter
from app.l2.wave2.repository import InMemoryRevisionLoopRepository
from app.l2.wave2.revision_loop import RevisionLoopService
from app.l2.wave3.adapters import (
    ExistingPracticeActivitySource,
    InMemoryConsentStore,
    InMemoryReviewEvidenceStore,
)
from app.l2.wave3.adaptive_practice import AdaptivePracticeService
from app.l2.wave3.tutor import ProactiveTutorService
from tests.wave2_l2_pipeline import V1_SHORT_REPETITIVE, build_real_pipeline


PROMPT = "Take a position on studying abroad and support it with reasons."


class TestLearnerIsolation:
    def test_adaptive_recommendations_are_learner_scoped(self, tmp_path) -> None:
        pipeline, repository, _ = build_real_pipeline(tmp_path)
        revision_service = RevisionLoopService(
            repository=InMemoryRevisionLoopRepository(),
            pipeline=pipeline,
            routing=LocalWrittenCorpusRouter(),
        )
        for student_id in ("L-ISO-A", "L-ISO-B"):
            task = revision_service.create_task(
                student_id=student_id, task_type="argumentative",
                writing_context="ielts_task2", writing_prompt=PROMPT,
            )
            revision_service.submit_v1(task.task_id, V1_SHORT_REPETITIVE)
        service = AdaptivePracticeService(
            repository=revision_service.repository,
            pipeline=pipeline,
            activity_source=ExistingPracticeActivitySource(),
        )
        a = service.recommend("L-ISO-A")
        b = service.recommend("L-ISO-B")
        assert a.learner_id == "L-ISO-A"
        assert b.learner_id == "L-ISO-B"
        assert a.recommendation_id != b.recommendation_id
        # Learner A cannot select from Learner B's recommendation.
        with pytest.raises(LookupError):
            service.select("L-ISO-A", b.recommendation_id, b.default_activity_id)

    def test_tutor_consent_store_is_learner_scoped(self, tmp_path) -> None:
        consent_store = InMemoryConsentStore()
        review_evidence = InMemoryReviewEvidenceStore()
        pipeline, repository, _ = build_real_pipeline(tmp_path)
        revision_service = RevisionLoopService(
            repository=InMemoryRevisionLoopRepository(),
            pipeline=pipeline,
            routing=LocalWrittenCorpusRouter(),
        )
        task = revision_service.create_task(
            student_id="L-ISO-A", task_type="argumentative",
            writing_context="ielts_task2", writing_prompt=PROMPT,
        )
        revision_service.submit_v1(task.task_id, V1_SHORT_REPETITIVE)
        adaptive = AdaptivePracticeService(
            repository=revision_service.repository, pipeline=pipeline,
            activity_source=ExistingPracticeActivitySource(),
        )
        tutor = ProactiveTutorService(
            repository=revision_service.repository,
            consent_store=consent_store,
            review_evidence=review_evidence,
            observation_source=None,
            adaptive=adaptive,
        )
        recommendation = tutor.recommend("L-ISO-A")
        consent = tutor.new_consent("L-ISO-A")
        tutor.accept("L-ISO-A", recommendation.recommendation_id, consent)
        assert consent_store.list_consents("L-ISO-A")
        assert consent_store.list_consents("L-ISO-B") == []


class TestFailureIsolation:
    def test_missing_review_service_degrades_to_honest_state(self, tmp_path) -> None:
        pipeline, repository, _ = build_real_pipeline(tmp_path)
        consent_store = InMemoryConsentStore()
        review_evidence = InMemoryReviewEvidenceStore()
        adaptive = AdaptivePracticeService(
            repository=InMemoryRevisionLoopRepository(), pipeline=pipeline,
            activity_source=ExistingPracticeActivitySource(),
        )
        tutor = ProactiveTutorService(
            repository=InMemoryRevisionLoopRepository(),
            consent_store=consent_store,
            review_evidence=review_evidence,
            observation_source=None,
            adaptive=adaptive,
        )
        # Empty review evidence must not crash recommendation; it degrades
        # to an honest state.
        recommendation = tutor.recommend("L-ISO-A")
        assert recommendation.state in {
            "insufficient_history", "history_grounded", "unavailable",
        }
        assert recommendation.limitations

    def test_one_learner_failure_does_not_corrupt_another(self, tmp_path) -> None:
        pipeline, repository, _ = build_real_pipeline(tmp_path)
        revision_service = RevisionLoopService(
            repository=InMemoryRevisionLoopRepository(),
            pipeline=pipeline,
            routing=LocalWrittenCorpusRouter(),
        )
        task = revision_service.create_task(
            student_id="L-ISO-B", task_type="argumentative",
            writing_context="ielts_task2", writing_prompt=PROMPT,
        )
        revision_service.submit_v1(task.task_id, V1_SHORT_REPETITIVE)
        adaptive = AdaptivePracticeService(
            repository=revision_service.repository, pipeline=pipeline,
            activity_source=ExistingPracticeActivitySource(),
        )
        # A failing call for a stranger must not mutate learner B's state.
        before = adaptive.recommend("L-ISO-B").model_dump(mode="json")
        with pytest.raises(LookupError):
            adaptive.select("L-NEVER-SEEN", "AR999999", "QA999999")
        after = adaptive.recommend("L-ISO-B").model_dump(mode="json")
        assert before == after
