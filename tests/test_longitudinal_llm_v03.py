from __future__ import annotations

import json

from app.analyzer import BasicAnalyzer
from app.diagnosis import HeuristicDiagnoser
from app.feedback.validation import FeedbackValidator
from app.llm import FeedbackContext, LocalDemoProvider
from app.models import EssaySubmission, HistoryResult
from app.prompts import PromptBuilder
from app.services import ProgressService
from tests.test_longitudinal_v03 import FakeRepository, record


def context_with(history, snapshot=None):
    submission = EssaySubmission(
        student_id="S001", writing_prompt="Should cities protect public parks?",
        genre="argumentative essay", draft_stage="first draft", timed=False,
        tool_use="none", essay_text=(
            "Cities should protect parks because parks support public health. "
            "Therefore, leaders should preserve accessible green space."
        ),
    )
    analysis = BasicAnalyzer().analyze(submission.essay_text)
    diagnosis = HeuristicDiagnoser().diagnose(analysis)
    return FeedbackContext(submission, analysis, diagnosis, history, snapshot)


def test_snapshot_evidence_enters_prompt_by_validated_id_and_local_demo_works():
    repository = FakeRepository([record(i, 100 + i * 20, category="lexical_repetition") for i in range(1, 5)])
    progress = ProgressService(repository, repository)
    snapshot = progress.create_snapshot("S001", persist=False)
    history = HistoryResult(
        comparability_status="comparable", comparable_submission_count=3,
        history_evidence=[], summary="Local history available.", limitations=["prototype"],
        comparability_reasons=["Comparable local records."],
    )
    enriched = progress.enrich_history(history, snapshot)
    assert enriched.history_evidence
    assert all(item.history_evidence_id.startswith("H") for item in enriched.history_evidence)
    context = context_with(enriched, snapshot)
    bundle = PromptBuilder().build(context)
    payload = json.loads(bundle.messages[1]["content"])
    assert payload["learner_history"]["history_evidence"]
    assert payload["learner_profile_snapshot"]["snapshot_id"] is None
    assert "excluded_submissions" not in payload["learner_profile_snapshot"]
    assert "observations" not in json.dumps(payload["learner_profile_snapshot"])
    feedback = LocalDemoProvider().generate(bundle.messages, temperature=0)
    FeedbackValidator().validate(feedback, context)
    assert set(feedback.longitudinal.history_evidence_ids) == {
        item.history_evidence_id for item in enriched.history_evidence
    }


def test_no_valid_trend_keeps_deterministic_comment_unavailable():
    repository = FakeRepository([record(1, 100)])
    progress = ProgressService(repository, repository)
    snapshot = progress.create_snapshot("S001", persist=False)
    history = HistoryResult(
        comparability_status="insufficient_history", comparable_submission_count=0,
        history_evidence=[], summary="数据不足，无法判断趋势。", limitations=["prototype"],
        comparability_reasons=["No comparable history."],
    )
    enriched = progress.enrich_history(history, snapshot)
    assert not enriched.history_evidence
    context = context_with(enriched)
    bundle = PromptBuilder().build(context)
    feedback = LocalDemoProvider().generate(bundle.messages, temperature=0)
    FeedbackValidator().validate(feedback, context)
    assert feedback.longitudinal.history_evidence_ids == []
    assert "无法" in feedback.longitudinal.comment
