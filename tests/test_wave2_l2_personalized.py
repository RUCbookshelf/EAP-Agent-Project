"""Wave-2 Goal C -- personalized feedback bridge tests (TDD red phase).

Personalized outputs combine local observations (current submission), global
whole-text observations (bounded; basic organization observation only --
discourse_organization validated measurement NOT established) and historical
feedback grounded in stored evidence (recurring/stable/reappeared/
insufficient-history). Historical feedback is never fabricated for learners
without stored history. Scaffolding is a 7-level progressive reveal defaulting
to SCAFFOLD FIRST, always helping the learner revise and never replacing
writing. LearningItem v1 is a durable learning target with full linkage.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.l2.wave2.corpus_routing import LocalWrittenCorpusRouter
from app.l2.wave2.personalized import PersonalizedBridgeService
from app.l2.wave2.repository import InMemoryRevisionLoopRepository
from app.l2.wave2.revision_loop import RevisionLoopService
from tests.wave2_l2_pipeline import (
    V1_SHORT_NON_REPETITIVE,
    V1_SHORT_REPETITIVE,
    V2_LONG_VARIED,
    build_real_pipeline,
    categories_of,
)


PROMPT_A = "Take a position on studying abroad and support it with reasons."
PROMPT_B = "Discuss whether cities should build more parks."


@pytest.fixture
def returning_learner(tmp_path):
    """Real-pipeline returning-learner fixture.

    Task A (ielts_task2): V1 short+repetitive, V2 long+varied.
    Task B (cet6): V1 short but non-repetitive.
    Expected stored evidence states:
    - essay_length: TaskA-V1 -> absent TaskA-V2 -> TaskB-V1 => reappeared
    - lexical_repetition: TaskA-V1 only, absent in the two later samples =>
      stable
    - targeted_review: TaskA-V2 only => first_observed
    """
    pipeline, repository, _ = build_real_pipeline(tmp_path)
    revision_service = RevisionLoopService(
        repository=InMemoryRevisionLoopRepository(),
        pipeline=pipeline,
        routing=LocalWrittenCorpusRouter(),
    )
    task_a = revision_service.create_task(
        student_id="L-RETURN-01", task_type="argumentative",
        writing_context="ielts_task2", writing_prompt=PROMPT_A,
    )
    a1 = revision_service.submit_v1(task_a.task_id, V1_SHORT_REPETITIVE)
    a2 = revision_service.revise(task_a.task_id, a1.submission_id, V2_LONG_VARIED)
    task_b = revision_service.create_task(
        student_id="L-RETURN-01", task_type="discussion",
        writing_context="cet6", writing_prompt=PROMPT_B,
    )
    b1 = revision_service.submit_v1(task_b.task_id, V1_SHORT_NON_REPETITIVE)
    a1_categories = categories_of(pipeline.get_submission_bundle(a1.submission_id))
    a2_categories = categories_of(pipeline.get_submission_bundle(a2.submission_id))
    b1_categories = categories_of(pipeline.get_submission_bundle(b1.submission_id))
    # Fixture preconditions: deterministic diagnosis must hold.
    assert "essay_length" in a1_categories
    assert "essay_length" not in a2_categories
    assert "essay_length" in b1_categories
    return {
        "pipeline": pipeline,
        "revision_service": revision_service,
        "repository": revision_service.repository,
        "task_a": task_a, "task_b": task_b,
        "a1": a1, "a2": a2, "b1": b1,
        "a1_categories": a1_categories,
        "a2_categories": a2_categories,
        "b1_categories": b1_categories,
    }


@pytest.fixture
def personalized(returning_learner):
    service = PersonalizedBridgeService(
        repository=returning_learner["repository"],
        pipeline=returning_learner["pipeline"],
        routing=LocalWrittenCorpusRouter(),
    )
    return service


class TestHistoricalFeedback:
    def test_recurring_stable_reappeared_and_insufficient_states(
        self, returning_learner, personalized,
    ) -> None:
        view = personalized.historical_feedback("L-RETURN-01")
        assert view.history_state == "sufficient"
        by_category = {item.category: item for item in view.items}
        assert by_category["essay_length"].status == "reappeared"
        assert by_category["lexical_repetition"].status == "stable"
        assert by_category["targeted_review"].status == "first_observed"
        assert by_category["essay_length"].supporting_submission_ids == [
            returning_learner["a1"].submission_id,
            returning_learner["b1"].submission_id,
        ]
        assert by_category["essay_length"].revision_success_note
        assert all(
            item.claims_status == "observation_only" for item in view.items
        )
        assert all(item.evidence_refs for item in view.items)

    def test_no_history_is_never_fabricated(self, personalized) -> None:
        view = personalized.historical_feedback("L-NEVER-SEEN")
        assert view.history_state == "insufficient_history"
        assert view.items == []
        assert view.history_reasons


class TestPriorityRevisionPlan:
    def test_plan_is_small_actionable_and_recurrence_aware(
        self, returning_learner, personalized,
    ) -> None:
        plan = personalized.build_priority_plan(
            "L-RETURN-01",
            returning_learner["task_b"].task_id,
            returning_learner["b1"].submission_id,
        )
        assert plan.history_state == "sufficient"
        assert 0 < len(plan.items) <= 3
        categories = [item.category for item in plan.items]
        assert "essay_length" in categories
        by_category = {item.category: item for item in plan.items}
        assert by_category["essay_length"].recurrence_status == "reappeared"
        assert any(
            "revision evidence:" in limitation
            for limitation in by_category["essay_length"].limitations
        )
        assert all(
            item.ordering_note == "action-priority ordering only; not a learner-performance ranking"
            for item in plan.items
        )
        assert all(item.evidence_refs for item in plan.items)

    def test_local_and_global_observations_are_bounded(self, returning_learner, personalized) -> None:
        plan = personalized.build_priority_plan(
            "L-RETURN-01",
            returning_learner["task_b"].task_id,
            returning_learner["b1"].submission_id,
        )
        assert plan.local_observations
        assert all(item.limitation for item in plan.local_observations)
        assert plan.global_observations
        organization = next(
            item for item in plan.global_observations
            if item.kind == "basic_organization"
        )
        assert organization.scope == "whole_text"
        assert "discourse_organization" in organization.limitation
        assert "NOT established" in organization.limitation

    def test_no_history_fallback_uses_current_submission_only(
        self, returning_learner, personalized,
    ) -> None:
        task = returning_learner["revision_service"].create_task(
            student_id="L-NEW-01", task_type="argumentative",
            writing_context="ielts_task2", writing_prompt=PROMPT_A,
        )
        v1 = returning_learner["revision_service"].submit_v1(
            task.task_id, V1_SHORT_REPETITIVE,
        )
        plan = personalized.build_priority_plan("L-NEW-01", task.task_id, v1.submission_id)
        assert plan.history_state == "insufficient_history"
        assert plan.historical_feedback == []
        assert plan.items
        assert any("no stored" in reason for reason in plan.history_reasons)
        assert any(
            "current submission only" in limitation for limitation in plan.limitations
        )


class TestProgressiveScaffold:
    def test_seven_levels_default_scaffold_first(self, personalized) -> None:
        response = personalized.request_scaffold(
            "L-RETURN-01", category="essay_length",
            evidence="The draft contains 20 words.",
        )
        assert response.level == 1
        assert response.default_first is True
        assert response.available_levels == [1, 2, 3, 4, 5, 6, 7]
        assert response.never_writes_statement
        for level in (1, 3, 5, 7):
            item = personalized.request_scaffold(
                "L-RETURN-01", category="essay_length",
                evidence="The draft contains 20 words.", level=level,
            )
            assert item.level == level
            assert item.content.text

    def test_scaffold_helps_revise_and_never_replaces_writing(self, personalized) -> None:
        response = personalized.request_scaffold(
            "L-RETURN-01", category="connective_use",
            evidence="No listed connectives detected.",
            level=7,
        )
        assert response.never_writes_statement
        assert "learner" in response.learner_action.casefold()
        assert "writes" in response.learner_action.casefold()

    def test_scaffold_history_recorded(self, returning_learner) -> None:
        repository = InMemoryRevisionLoopRepository()
        service = PersonalizedBridgeService(
            repository=repository,
            pipeline=returning_learner["pipeline"],
            routing=LocalWrittenCorpusRouter(),
        )
        service.request_scaffold(
            "L-RETURN-01", category="essay_length",
            evidence="The draft contains 20 words.",
        )
        service.request_scaffold(
            "L-RETURN-01", category="essay_length",
            evidence="The draft contains 20 words.", level=4,
        )
        events = repository.list_scaffold_events("L-RETURN-01")
        assert [event.level for event in events] == [1, 4]
        assert events[0].default_first is True
        assert events[0].category == "essay_length"

    def test_invalid_level_rejected(self, personalized) -> None:
        with pytest.raises(ValueError):
            personalized.request_scaffold(
                "L-RETURN-01", category="essay_length", level=8,
            )


class TestLearningItem:
    def test_create_from_priority_plan_with_full_linkage(
        self, returning_learner, personalized,
    ) -> None:
        plan = personalized.build_priority_plan(
            "L-RETURN-01",
            returning_learner["task_b"].task_id,
            returning_learner["b1"].submission_id,
        )
        item = personalized.create_learning_item(
            "L-RETURN-01", plan.items[0].plan_item_id,
        )
        assert item.learning_item_id
        assert item.student_id == "L-RETURN-01"
        assert item.status == "proposed"
        assert item.task_id == returning_learner["task_b"].task_id
        assert item.task_context["writing_context"] == "cet6"
        assert item.originating_evidence["submission_ids"]
        assert item.originating_evidence["diagnosis_ids"]
        assert item.feedback_reference
        assert item.revision_history
        assert "no fsrs" in item.no_fsrs_note.casefold()
        assert "practice" in item.no_practice_note.casefold()
        stored = personalized.repository.get_learning_item(item.learning_item_id)
        assert stored is not None and stored.student_id == "L-RETURN-01"

    def test_list_and_status_transitions(self, returning_learner, personalized) -> None:
        plan = personalized.build_priority_plan(
            "L-RETURN-01",
            returning_learner["task_b"].task_id,
            returning_learner["b1"].submission_id,
        )
        item = personalized.create_learning_item(
            "L-RETURN-01", plan.items[0].plan_item_id,
        )
        assert [i.learning_item_id for i in personalized.list_learning_items("L-RETURN-01")] == [
            item.learning_item_id,
        ]
        updated = personalized.update_learning_item_status(
            item.learning_item_id, "active",
        )
        assert updated.status == "active"
        assert personalized.list_learning_items("L-RETURN-01", status="active")

    def test_create_from_unknown_plan_rejected(self, personalized) -> None:
        with pytest.raises(LookupError):
            personalized.create_learning_item("L-RETURN-01", "PP999999")
