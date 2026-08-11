"""Wave-2 Goal C -- context-aware revision loop tests (TDD red phase).

Required flow (acceptance gate): V1 submit -> feedback -> revise -> persisted
V2 -> ancestry -> comparison/observation -> V2 reanalysis. Every submission
and revision runs through the EXISTING real Writing Intelligence pipeline
(analyzer -> diagnosis -> feedback router -> revision relationships ->
history). Prior submissions are never overwritten; historical versions are
evidence.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.l2.wave2.corpus_routing import (
    MODALITY_WRITTEN,
    WECCL_PACKAGE_ID,
    LocalWrittenCorpusRouter,
)
from app.l2.wave2.models import (
    RevisionObservation,
    WritingTask,
    WritingTaskMetadata,
)
from app.l2.wave2.revision_loop import (
    RevisionLoopService,
    build_revision_observation,
)
from app.l2.wave2.repository import InMemoryRevisionLoopRepository
from tests.wave2_l2_pipeline import (
    V1_SHORT_NON_REPETITIVE,
    V1_SHORT_REPETITIVE,
    V2_LONG_VARIED,
    build_real_pipeline,
    categories_of,
    feedback_categories_of,
)


PROMPT_A = "Take a position on studying abroad and support it with reasons."
PROMPT_B = "Discuss whether cities should build more parks."


@pytest.fixture
def revision_loop(tmp_path):
    pipeline, repository, _ = build_real_pipeline(tmp_path)
    service = RevisionLoopService(
        repository=InMemoryRevisionLoopRepository(),
        pipeline=pipeline,
        routing=LocalWrittenCorpusRouter(),
    )
    return service, pipeline


class TestTaskContextAwareSubmission:
    def test_task_prompt_and_context_are_preserved_with_submissions(
        self, revision_loop, tmp_path,
    ) -> None:
        service, pipeline = revision_loop
        task = service.create_task(
            student_id="L-REV-01",
            task_type="argumentative",
            writing_context="ielts_task2",
            writing_prompt=PROMPT_A,
            metadata=WritingTaskMetadata(
                audience="IELTS examiner",
                word_constraint="at least 250 words",
                assessment_environment="timed exam",
            ),
        )
        version = service.submit_v1(task.task_id, V1_SHORT_REPETITIVE)
        assert version.task_id == task.task_id
        assert version.version_number == 1
        assert version.task_context["task_type"] == "argumentative"
        assert version.task_context["writing_context"] == "ielts_task2"
        assert version.task_context["writing_prompt"] == PROMPT_A
        assert version.task_context["metadata"]["word_constraint"] == "at least 250 words"
        bundle = pipeline.get_submission_bundle(version.submission_id)
        assert bundle["writing_prompt"] == PROMPT_A
        assert bundle["genre"] == "ielts_task2"
        assert bundle["student_id"] == "L-REV-01"

    def test_corpus_routing_attached_to_version(self, revision_loop) -> None:
        service, _ = revision_loop
        task = service.create_task(
            student_id="L-REV-01", task_type="argumentative",
            writing_context="ielts_task2", writing_prompt=PROMPT_A,
        )
        version = service.submit_v1(task.task_id, V1_SHORT_REPETITIVE)
        assert version.corpus_routing is not None
        assert version.corpus_routing["modality"] == MODALITY_WRITTEN
        assert version.corpus_routing["resolved_resource_id"] == WECCL_PACKAGE_ID
        assert version.corpus_routing["learner_exposure"] == "research_only"


class TestRevisionVersioning:
    def test_v1_submit_feedback_revise_persisted_v2_ancestry(
        self, revision_loop,
    ) -> None:
        service, pipeline = revision_loop
        task = service.create_task(
            student_id="L-REV-02", task_type="argumentative",
            writing_context="ielts_task2", writing_prompt=PROMPT_A,
        )
        v1 = service.submit_v1(task.task_id, V1_SHORT_REPETITIVE)
        v1_bundle = pipeline.get_submission_bundle(v1.submission_id)
        assert v1_bundle["feedback"] is not None
        assert feedback_categories_of(v1_bundle)

        v2 = service.revise(task.task_id, v1.submission_id, V2_LONG_VARIED)
        assert v2.version_number == 2
        assert v2.revision_of_submission_id == v1.submission_id
        assert v2.ancestry == [v1.submission_id, v2.submission_id]
        assert v2.submission_id != v1.submission_id

        # Prior submission is never overwritten: V1 text and feedback remain.
        v1_again = pipeline.get_submission_bundle(v1.submission_id)
        assert v1_again["essay_text"] == V1_SHORT_REPETITIVE
        assert v1_again["feedback"]["priority_feedback"]

        versions = service.version_history(task.task_id)
        assert [v.version_number for v in versions] == [1, 2]
        assert versions[0].ancestry == [v1.submission_id]
        assert versions[1].ancestry == [v1.submission_id, v2.submission_id]
        assert versions[1].analysis_run_id
        assert versions[1].feedback_record_id

    def test_third_revision_extends_chain(self, revision_loop) -> None:
        service, _ = revision_loop
        task = service.create_task(
            student_id="L-REV-03", task_type="discussion",
            writing_context="cet6", writing_prompt=PROMPT_B,
        )
        v1 = service.submit_v1(task.task_id, V1_SHORT_NON_REPETITIVE)
        v2 = service.revise(task.task_id, v1.submission_id, V2_LONG_VARIED)
        v3 = service.revise(task.task_id, v2.submission_id, V2_LONG_VARIED)
        assert v3.version_number == 3
        assert v3.ancestry == [v1.submission_id, v2.submission_id, v3.submission_id]
        assert len(service.version_history(task.task_id)) == 3

    def test_revision_does_not_overwrite_prior_versions(self, revision_loop) -> None:
        service, pipeline = revision_loop
        task = service.create_task(
            student_id="L-REV-04", task_type="argumentative",
            writing_context="ielts_task2", writing_prompt=PROMPT_A,
        )
        v1 = service.submit_v1(task.task_id, V1_SHORT_REPETITIVE)
        v2 = service.revise(task.task_id, v1.submission_id, V2_LONG_VARIED)
        v3 = service.revise(task.task_id, v2.submission_id, V1_SHORT_REPETITIVE)
        stored_v1 = pipeline.get_submission_bundle(v1.submission_id)
        stored_v2 = pipeline.get_submission_bundle(v2.submission_id)
        stored_v3 = pipeline.get_submission_bundle(v3.submission_id)
        assert stored_v1["essay_text"] == V1_SHORT_REPETITIVE
        assert stored_v2["essay_text"] == V2_LONG_VARIED
        assert stored_v3["essay_text"] == V1_SHORT_REPETITIVE


class TestRevisionObservation:
    def test_observation_after_v2_is_bounded_and_observational(self, revision_loop) -> None:
        service, _ = revision_loop
        task = service.create_task(
            student_id="L-REV-05", task_type="argumentative",
            writing_context="ielts_task2", writing_prompt=PROMPT_A,
        )
        v1 = service.submit_v1(task.task_id, V1_SHORT_REPETITIVE)
        v2 = service.revise(task.task_id, v1.submission_id, V2_LONG_VARIED)
        observation = service.observe(task.task_id, v2.submission_id)
        assert isinstance(observation, RevisionObservation)
        assert observation.source_submission_id == v1.submission_id
        assert observation.target_submission_id == v2.submission_id
        assert observation.what_changed["inserted_tokens"] > 0
        assert observation.feedback_areas
        # V1 feedback areas (essay_length, lexical_repetition) are no longer
        # observed in V2's diagnosis.
        assert all(
            area["status"] in {"appears_addressed", "appears_remaining", "not_assessable"}
            for area in observation.feedback_areas
        )
        assert "essay_length" in {
            area["category"] for area in observation.feedback_areas
        }
        assert observation.no_intent_inference
        assert "intent" in observation.no_intent_inference.casefold()
        assert any("not infer" in item.casefold() for item in observation.limitations)

    def test_observation_never_claims_feedback_caused_the_revision(self, revision_loop) -> None:
        service, _ = revision_loop
        task = service.create_task(
            student_id="L-REV-06", task_type="argumentative",
            writing_context="ielts_task2", writing_prompt=PROMPT_A,
        )
        v1 = service.submit_v1(task.task_id, V1_SHORT_REPETITIVE)
        v2 = service.revise(task.task_id, v1.submission_id, V2_LONG_VARIED)
        observation = service.observe(task.task_id, v2.submission_id)
        payload = observation.model_dump(mode="json")
        assert "caused" not in str(payload).casefold()
        assert "proficiency" not in str(payload).casefold()


class TestObservationBuilderUnit:
    """Controlled-bundle unit cases for exact status classification."""

    def _bundle(self, essay_id: int, *, categories: list[str],
                feedback_categories: list[str], text: str = "some draft text",
                submitted_at: str = "2026-08-01T00:00:00+00:00") -> dict:
        return {
            "essay_id": essay_id,
            "student_id": "L-UNIT-01",
            "writing_prompt": "prompt",
            "genre": "ielts_task2",
            "draft_stage": "first draft",
            "submitted_at": submitted_at,
            "essay_text": text,
            "feedback_id": essay_id * 10,
            "diagnosis": {
                "improvement_priorities": [
                    {
                        "diagnosis_id": f"D{i+1:03d}",
                        "category": category,
                        "evidence": f"evidence for {category}",
                        "interpretation": "signal",
                        "confidence": "low",
                        "kind": "improvement",
                        "rule_version": "test",
                        "limitation": "test",
                        "source_metrics": [],
                        "selection_status": "selected_priority",
                    }
                    for i, category in enumerate(categories)
                ],
            },
            "feedback": {
                "priority_feedback": [
                    {
                        "diagnosis_id": f"D{i+1:03d}",
                        "category": category,
                        "evidence_quote": "quote",
                        "explanation": "explanation",
                        "revision_guidance": "guidance",
                    }
                    for i, category in enumerate(feedback_categories)
                ],
            },
        }

    def _version(self, task_id: str, submission_id: int, version_number: int):
        return {
            "task_id": task_id,
            "submission_id": submission_id,
            "version_number": version_number,
            "revision_of_submission_id": None,
            "ancestry": [submission_id],
            "submitted_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
            "task_context": {"task_type": "argumentative"},
            "essay_text_hash": "hash",
            "draft_stage": "first draft",
        }

    def test_addressed_remaining_and_new_observations(self) -> None:
        source = self._bundle(
            1, categories=["essay_length", "lexical_repetition"],
            feedback_categories=["essay_length", "lexical_repetition"],
        )
        target = self._bundle(
            2, categories=["connective_use"],
            feedback_categories=[],
            submitted_at="2026-08-02T00:00:00+00:00",
        )
        observation = build_revision_observation(
            source, target, self._version("WT000001", 1, 1),
            self._version("WT000001", 2, 2),
            now=lambda: datetime(2026, 8, 3, tzinfo=timezone.utc),
        )
        by_category = {item["category"]: item for item in observation.feedback_areas}
        assert by_category["essay_length"]["status"] == "appears_addressed"
        assert by_category["lexical_repetition"]["status"] == "appears_addressed"
        assert {item["category"] for item in observation.new_observations} == {
            "connective_use",
        }
        assert observation.apparent_independent_corrections == []

    def test_remaining_area_stays_remaining(self) -> None:
        source = self._bundle(
            1, categories=["essay_length"],
            feedback_categories=["essay_length"],
        )
        target = self._bundle(
            2, categories=["essay_length"],
            feedback_categories=[],
            submitted_at="2026-08-02T00:00:00+00:00",
        )
        observation = build_revision_observation(
            source, target, self._version("WT000001", 1, 1),
            self._version("WT000001", 2, 2),
            now=lambda: datetime(2026, 8, 3, tzinfo=timezone.utc),
        )
        assert observation.feedback_areas[0]["status"] == "appears_remaining"

    def test_apparent_independent_correction_detected(self) -> None:
        # The learner changed a source diagnosis area that NO feedback item
        # ever targeted: an apparent independent correction (observational
        # only; no intent inference).
        source = self._bundle(
            1, categories=["sentence_length_pattern", "essay_length"],
            feedback_categories=["essay_length"],
        )
        target = self._bundle(
            2, categories=["essay_length"],
            feedback_categories=[],
            submitted_at="2026-08-02T00:00:00+00:00",
        )
        observation = build_revision_observation(
            source, target, self._version("WT000001", 1, 1),
            self._version("WT000001", 2, 2),
            now=lambda: datetime(2026, 8, 3, tzinfo=timezone.utc),
        )
        assert {
            item["category"] for item in observation.apparent_independent_corrections
        } == {"sentence_length_pattern"}
        assert observation.feedback_areas[0]["category"] == "essay_length"
        assert observation.feedback_areas[0]["status"] == "appears_remaining"


class TestReanalysis:
    def test_v2_reanalysis_through_existing_pipeline(self, revision_loop) -> None:
        service, _ = revision_loop
        task = service.create_task(
            student_id="L-REV-07", task_type="argumentative",
            writing_context="ielts_task2", writing_prompt=PROMPT_A,
        )
        v1 = service.submit_v1(task.task_id, V1_SHORT_REPETITIVE)
        v2 = service.revise(task.task_id, v1.submission_id, V2_LONG_VARIED)
        result = service.reanalyze(task.task_id, v2.submission_id)
        assert result.submission_id == v2.submission_id
        assert result.analysis_run_id
        assert result.feedback_record_id
        assert result.provider_status in {"success", "fallback_success"}
        version = service.get_version(task.task_id, v2.submission_id)
        assert version.analysis_run_id == result.analysis_run_id
        assert version.feedback_record_id == result.feedback_record_id
        assert len(version.reanalysis_events) == 1
        assert version.reanalysis_events[0]["analysis_run_id"] == result.analysis_run_id

    def test_reanalysis_uses_real_analyzer_run(self, revision_loop) -> None:
        service, pipeline = revision_loop
        task = service.create_task(
            student_id="L-REV-08", task_type="argumentative",
            writing_context="ielts_task2", writing_prompt=PROMPT_A,
        )
        v1 = service.submit_v1(task.task_id, V1_SHORT_REPETITIVE)
        result = service.reanalyze(task.task_id, v1.submission_id)
        assert result.analysis_version.startswith("basic-analyzer")


class TestTaskErrors:
    def test_unknown_task_rejected(self, revision_loop) -> None:
        service, _ = revision_loop
        with pytest.raises(LookupError):
            service.submit_v1("WT999999", V1_SHORT_REPETITIVE)

    def test_revision_of_unknown_submission_rejected(self, revision_loop) -> None:
        service, _ = revision_loop
        task = service.create_task(
            student_id="L-REV-09", task_type="argumentative",
            writing_context="ielts_task2", writing_prompt=PROMPT_A,
        )
        with pytest.raises(LookupError):
            service.revise(task.task_id, 999999, V2_LONG_VARIED)
