from datetime import timedelta

from app.feedback.service import FeedbackPipeline


def test_second_submission_produces_structured_history_evidence(settings, submission):
    pipeline = FeedbackPipeline(settings)
    first = pipeline.submit(submission)
    second_submission = submission.model_copy(update={
        "essay_text": submission.essay_text + " Moreover, residents can help plan safe paths and community activities.",
        "submitted_at": submission.submitted_at + timedelta(days=7),
    })
    second = pipeline.submit(second_submission)
    assert first.history.comparability_status == "insufficient_history"
    assert first.history.history_evidence == []
    assert second.history.comparability_status == "comparable"
    assert second.comparable_history_count == 1
    assert second.history.history_evidence
    assert [item.history_evidence_id for item in second.history.history_evidence] == [
        f"H{index:03d}" for index in range(1, len(second.history.history_evidence) + 1)
    ]
    assert all(item.supporting_submission_ids for item in second.history.history_evidence)


def test_different_draft_stage_is_explicitly_partial(settings, submission):
    pipeline = FeedbackPipeline(settings)
    pipeline.submit(submission)
    revised = submission.model_copy(update={
        "draft_stage": "revised draft", "submitted_at": submission.submitted_at + timedelta(days=1),
    })
    result = pipeline.submit(revised)
    assert result.history.comparability_status == "partially_comparable"
    assert any("explicitly allows" in reason for reason in result.history.comparability_reasons)


def test_incomparable_essay_does_not_enter_history_evidence(settings, submission):
    pipeline = FeedbackPipeline(settings)
    first = pipeline.submit(submission)
    different = submission.model_copy(update={
        "genre": "narrative essay", "timed": True, "time_limit_minutes": 30,
        "tool_use": "dictionary", "writing_prompt": "Describe a journey.",
        "submitted_at": submission.submitted_at + timedelta(days=1),
    })
    result = pipeline.submit(different)
    assert result.history.comparability_status == "not_comparable"
    assert result.history.history_evidence == []
    assert f"E{first.essay_id:06d}" in result.history.excluded_submission_ids
