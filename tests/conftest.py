from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.analyzer import BasicAnalyzer
from app.config import Settings
from app.diagnosis import HeuristicDiagnoser
from app.llm import FeedbackContext
from app.models import EssaySubmission, HistoryResult
from app.prompts import PromptBuilder


@pytest.fixture
def settings(tmp_path):
    return Settings(
        database_path=tmp_path / "test.db", llm_provider="local", deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com", deepseek_model="deepseek-chat",
    )


@pytest.fixture
def submission():
    return EssaySubmission(
        student_id="TEST001", writing_prompt="Should cities add more parks?",
        genre="argumentative essay", draft_stage="first draft", timed=False,
        tool_use="none",
        essay_text=(
            "Cities should add more parks because parks give residents space to exercise. "
            "Parks also support community events and provide shade during hot weather. "
            "However, new parks require land and regular maintenance. Therefore, city leaders "
            "should first identify neighborhoods with limited green space and consult residents."
        ),
        submitted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def feedback_context(submission):
    analysis = BasicAnalyzer().analyze(submission.essay_text)
    diagnosis = HeuristicDiagnoser().diagnose(analysis)
    history = HistoryResult(
        comparability_status="insufficient_history", comparable_submission_count=0,
        history_evidence=[], summary="数据不足，无法判断趋势。",
        limitations=["Prototype history evidence does not establish ability change."],
        comparability_reasons=["No earlier submission exists for this student_id."],
    )
    return FeedbackContext(submission, analysis, diagnosis, history)


@pytest.fixture
def prompt_bundle(feedback_context):
    return PromptBuilder().build(feedback_context)
