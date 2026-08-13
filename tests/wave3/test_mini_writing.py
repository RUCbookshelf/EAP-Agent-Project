"""MiniWritingService: bounded mini-writing through the EXISTING Writing
Intelligence pipeline (no disconnected analysis or essay-generation service);
provenance preserved; learner ownership enforced."""

from __future__ import annotations

import pytest

from app.l2.wave2.corpus_routing import LocalWrittenCorpusRouter
from app.l2.wave2.repository import InMemoryRevisionLoopRepository
from app.l2.wave2.revision_loop import RevisionLoopService
from app.l2.wave3.mini_writing import MiniWritingService
from app.learner.normative import NormativeClaimsScanner
from tests.wave2_l2_pipeline import build_real_pipeline


SCANNER = NormativeClaimsScanner()
PROMPT = "Discuss whether cities should build more parks."
MINI_TEXT = (
    "Cities should build more parks because green spaces improve health. "
    "Parks also give people a place to meet and relax."
)


@pytest.fixture
def mini(tmp_path):
    pipeline, repository, _ = build_real_pipeline(tmp_path)
    revision_service = RevisionLoopService(
        repository=InMemoryRevisionLoopRepository(),
        pipeline=pipeline,
        routing=LocalWrittenCorpusRouter(),
    )
    task = revision_service.create_task(
        student_id="L-MINI-01", task_type="discussion",
        writing_context="cet6", writing_prompt=PROMPT,
    )
    service = MiniWritingService(revision_loop=revision_service)
    return {
        "service": service,
        "pipeline": pipeline,
        "revision_service": revision_service,
        "task": task,
    }


class TestMiniWriting:
    def test_submits_through_real_pipeline(self, mini) -> None:
        result = mini["service"].submit("L-MINI-01", mini["task"].task_id, MINI_TEXT)
        assert result.submission_id > 0
        assert result.analysis_run_id
        assert result.analysis_version
        assert result.feedback_record_id
        assert result.word_count > 0
        assert result.bounded is True
        assert "writing-intelligence" in result.pipeline_adapter
        # The bundle is really stored through the shared pipeline.
        bundle = mini["pipeline"].get_submission_bundle(result.submission_id)
        assert bundle is not None
        assert bundle["student_id"] == "L-MINI-01"

    def test_provenance_and_no_normative_claims(self, mini) -> None:
        result = mini["service"].submit("L-MINI-01", mini["task"].task_id, MINI_TEXT)
        assert result.essay_text_hash
        assert result.claims_status == "observation_only"
        assert SCANNER.scan_mapping(result.model_dump(mode="json")) == []

    def test_oversized_mini_writing_rejected(self, mini) -> None:
        with pytest.raises(ValueError):
            mini["service"].submit(
                "L-MINI-01", mini["task"].task_id, "x" * 1200,
            )

    def test_blank_mini_writing_rejected(self, mini) -> None:
        with pytest.raises(ValueError):
            mini["service"].submit("L-MINI-01", mini["task"].task_id, "   ")

    def test_cross_learner_task_rejected(self, mini) -> None:
        with pytest.raises(LookupError):
            mini["service"].submit("L-OTHER-99", mini["task"].task_id, MINI_TEXT)

    def test_unknown_task_rejected(self, mini) -> None:
        with pytest.raises(LookupError):
            mini["service"].submit("L-MINI-01", "WT999999", MINI_TEXT)

    def test_mini_writing_is_learner_text_not_essay_generation(self, mini) -> None:
        result = mini["service"].submit("L-MINI-01", mini["task"].task_id, MINI_TEXT)
        # The pipeline analyzes learner-supplied text; it never generated it.
        assert result.word_count == len(MINI_TEXT.split())
        assert result.limitations
        assert any(
            "learner text" in limitation.casefold() for limitation in result.limitations
        )
