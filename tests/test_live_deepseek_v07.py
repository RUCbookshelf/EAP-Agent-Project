from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import os

import pytest

from app.config import load_settings
from app.database import Database
from app.models import EssaySubmission
from app.services import build_submission_service


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_LLM_TESTS") != "1",
    reason="Set RUN_LIVE_LLM_TESTS=1 for the explicit quota-consuming DeepSeek test.",
)


def test_three_task_live_deepseek_uses_screened_v07_history(tmp_path):
    settings = load_settings()
    if not settings.deepseek_api_key:
        pytest.skip("Local .env does not configure DEEPSEEK_API_KEY.")
    settings = replace(settings, database_path=tmp_path / "live-v07.db", llm_provider="deepseek")
    repository = Database(settings.database_path); repository.initialize()
    service = build_submission_service(settings, repository)
    base = datetime(2026, 6, 1, tzinfo=timezone.utc)
    results = []
    for index, prompt in enumerate((
        "Should schools require community service?",
        "Should cities limit private cars downtown?",
        "Should universities record lectures?",
    )):
        text = (
            "A vague claim, a vague reason, and another vague claim appear together without enough specific support. "
            "Readers need concrete evidence because a general assertion cannot show how the proposal would work. "
            "For example, a writer can name one consequence, explain who is affected, and connect that evidence to the claim. "
            "However, an opposing view should also be represented fairly before the conclusion returns to the main position. "
        ) * 3
        results.append(service.submit(EssaySubmission(
            student_id="LIVE-V07-SYNTHETIC", writing_prompt=prompt,
            genre="argumentative essay", draft_stage="independent submission",
            timed=True, time_limit_minutes=45, tool_use="none", essay_text=text,
            submitted_at=base + timedelta(days=index * 14),
        ), synthetic=True))
    final = results[-1]
    assert final.provider.provider_name == "deepseek"
    assert final.provider.success_status == "success"
    assert final.provider.validation_status == "passed"
    assert final.provider.fallback_reason is None
    assert final.provider.prompt_version == "feedback-prompt-v0.7.0"
    assert final.provider.schema_version == "structured-feedback-v0.7.0"
    profile = repository.get_latest_learner_profile("LIVE-V07-SYNTHETIC")
    assert profile["profile_version"] == "learner-profile-v0.7.0"
    assert len(profile["representative_submission_ids"]) == 3
    assert profile["data_sufficiency"]["status"] == "provisional"
    assert profile["history_evidence"]
    assert all(item["history_evidence_id"].startswith("HE") for item in profile["history_evidence"])
    assert any(item.history_evidence_id.startswith("HE") for item in final.history.history_evidence)
    current_categories = {item.category for item in final.diagnosis.improvement_priorities}
    assert {item.category for item in final.provider.feedback.priority_feedback} <= current_categories
