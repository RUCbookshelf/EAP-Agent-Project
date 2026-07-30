from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.config import load_settings
from app.database import Database, rollback, upgrade
from app.feedback import FeedbackReliabilityService, FeedbackValidator
from app.llm import FeedbackContext, LLMProvider, LocalDemoProvider, ProviderOutputError, ProviderRouter
from app.models import EssaySubmission, LongitudinalAssessment, StructuredFeedback
from app.prompts import PromptBuilder
from app.prompts.versioning_v071 import validate_prompt_versioning
from app.services import build_submission_service
from app.ui.streamlit_app import grouped_connectives


PROMPT = "Should cities protect public parks?"


def submission(student: str, text: str, *, day: int = 0, stage: str = "independent submission",
               source: int | None = None, prompt: str = PROMPT) -> EssaySubmission:
    return EssaySubmission(
        student_id=student, writing_prompt=prompt, genre="argumentative essay",
        draft_stage=stage, timed=False, tool_use="none", essay_text=text,
        submitted_at=datetime(2026, 7, 1, tzinfo=timezone.utc) + timedelta(days=day),
        revision_of_submission_id=source,
    )


def local_stack(tmp_path):
    settings = replace(
        load_settings(), database_path=tmp_path / "v071.db", llm_provider="local",
        deepseek_api_key=None,
    )
    repository = Database(settings.database_path); repository.initialize()
    return settings, repository, build_submission_service(settings, repository)


class ScriptedProvider(LLMProvider):
    provider_name = "scripted"
    model_name = "scripted-v071"
    configured = True

    def __init__(self, responses):
        self.responses = list(responses)

    def generate(self, messages, *, temperature):
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def test_case_1_no_history_uses_structured_status_without_retry_or_fallback(tmp_path):
    _, repository, service = local_stack(tmp_path)
    result = service.submit(submission(
        "V071-A", "Public parks support exercise and community events. Cities should protect accessible parks."
    ), synthetic=True)
    assessment = result.longitudinal_assessment
    assert assessment.status == "unavailable"
    assert assessment.scope == "cross_task"
    assert assessment.comparable_task_count == 1
    assert assessment.history_evidence_ids == []
    assert "unavailable" in assessment.comment.casefold()
    assert result.provider.retry_count == 0 and result.provider.success_status == "success"
    assert result.provider.prompt_version == "feedback-prompt-v0.7.1"
    assert result.provider.schema_version == "structured-feedback-v0.7.1"
    assert repository.get_feedback_record(result.essay_id)["validation_status"] == "passed"


def test_cases_3_and_5_four_drafts_are_one_task_with_explained_empty_states(tmp_path):
    _, _, service = local_stack(tmp_path)
    texts = [
        "Parks support public health. Cities should protect them.",
        "Parks support public health and provide shade. Cities should protect them.",
        "Parks support health, provide shade, and host events. Cities should protect them.",
        "Parks support health, provide shade, and host events. Cities should protect accessible parks in every neighborhood.",
    ]
    source = None
    result = None
    for index, text in enumerate(texts):
        result = service.submit(submission(
            "V071-FOUR", text, day=index,
            stage=["first draft", "revised draft", "revised draft", "final draft"][index],
            source=source,
        ), synthetic=True)
        source = result.essay_id
    assert result is not None
    summary = result.revision_group_summary
    assert (summary.draft_submission_count, summary.revision_group_count,
            summary.independent_task_count, summary.longitudinal_representative_count) == (4, 1, 1, 1)
    trajectory = result.within_task_revision_trajectory
    assert len(trajectory.draft_chain) == 4
    assert len(trajectory.pairwise_comparisons) == 3
    assert trajectory.first_to_latest_comparison.source_submission_id == 1
    assert trajectory.first_to_latest_comparison.target_submission_id == 4
    assert result.longitudinal_assessment.comparable_task_count == 1
    assert "INSUFFICIENT_CROSS_TASK_HISTORY" in result.ui_empty_states
    if not result.provider.feedback.priority_feedback:
        assert {"NO_SELECTED_PRIORITY", "NO_TARGETED_PRACTICE"} <= set(result.ui_empty_states)


def test_case_4_three_independent_tasks_are_provisional_not_revision_history(tmp_path):
    _, _, service = local_stack(tmp_path)
    final = None
    for index in range(3):
        final = service.submit(submission(
            "V071-THREE",
            "A clear claim needs a concrete example and an explanation of its consequence for residents.",
            day=index, prompt=f"Independent public-policy prompt {index}",
        ), synthetic=True)
    assert final.longitudinal_assessment.status == "provisional_pattern"
    assert final.longitudinal_assessment.comparable_task_count == 3
    assert final.revision_group_summary is None


def test_case_6_major_rewrite_limits_attribution(tmp_path):
    _, _, service = local_stack(tmp_path)
    first = service.submit(submission(
        "V071-MAJOR", "Parks support exercise and community events for residents.", stage="first draft"
    ), synthetic=True)
    revised = service.submit(submission(
        "V071-MAJOR", "Quantum computers use qubits. Error correction remains difficult. Researchers test new materials.",
        day=1, stage="revised draft", source=first.essay_id,
    ), synthetic=True)
    trajectory = revised.within_task_revision_trajectory
    assert trajectory.major_rewrite_detected
    assert trajectory.attribution_confidence == "insufficient"
    assert "MAJOR_REWRITE_LIMITS_ATTRIBUTION" in revised.ui_empty_states
    assert all(item.status == "not_assessable" for item in trajectory.feedback_uptake_candidates)


def test_case_2_longitudinal_wording_is_repaired_locally_without_losing_sections(feedback_context):
    original = LocalDemoProvider().generate(PromptBuilder().build(feedback_context).messages, temperature=0.2)
    assessment = LongitudinalAssessment(
        status="unavailable", comparable_task_count=1, revision_group_count=0, draft_count=1,
        comment="Longitudinal judgment is currently unavailable.", history_evidence_ids=[],
        limitations=["Prototype status only."],
    )
    context = FeedbackContext(
        feedback_context.submission, feedback_context.analysis, feedback_context.diagnosis,
        feedback_context.history, longitudinal_assessment=assessment,
    )
    invalid = original.model_copy(update={
        "longitudinal": original.longitudinal.model_copy(update={
            "comment": "The learner shows a clear long-term trend of improvement."
        })
    })
    repaired, fields = FeedbackReliabilityService().repair(invalid, context)
    assert fields == ["longitudinal_assessment.comment"]
    assert repaired.positive_finding == original.positive_finding
    assert repaired.priority_feedback == original.priority_feedback
    assert repaired.exercises == original.exercises
    FeedbackValidator().validate(repaired, context)


def test_v071_prompt_manifest_and_field_specific_correction_are_versioned(feedback_context):
    assessment = LongitudinalAssessment(
        status="unavailable", comparable_task_count=1, revision_group_count=0, draft_count=1,
        comment="Longitudinal judgment is currently unavailable.", history_evidence_ids=[],
        limitations=["Prototype status only."],
    )
    context = FeedbackContext(
        feedback_context.submission, feedback_context.analysis, feedback_context.diagnosis,
        feedback_context.history, longitudinal_assessment=assessment,
    )
    bundle = PromptBuilder().build(context)
    correction = PromptBuilder().correction(bundle, "longitudinal_assessment.comment conflicts")
    manifest = validate_prompt_versioning()
    assert manifest["prompt_version"] == "feedback-prompt-v0.7.1"
    assert manifest["schema_version"] == "structured-feedback-v0.7.1"
    assert "Required state:" in correction.messages[-1]["content"]
    assert "status = unavailable" in correction.messages[-1]["content"]
    assert "Only one comparable independent task is available" in correction.messages[-1]["content"]


def test_server_generated_comment_and_external_server_repair_status(feedback_context):
    assessment = LongitudinalAssessment(
        status="unavailable", comparable_task_count=1, revision_group_count=0, draft_count=1,
        comment="Longitudinal judgment is currently unavailable.", history_evidence_ids=[],
        limitations=["Prototype status only."],
    )
    context = FeedbackContext(
        feedback_context.submission, feedback_context.analysis, feedback_context.diagnosis,
        feedback_context.history, longitudinal_assessment=assessment,
    )
    original = LocalDemoProvider().generate(PromptBuilder().build(context).messages, temperature=0.2)
    invalid = original.model_copy(update={
        "longitudinal": original.longitudinal.model_copy(update={
            "comment": "The learner shows a stable long-term trend of improvement."
        })
    })
    result = ProviderRouter(ScriptedProvider([invalid])).generate(context)
    status = result.feedback_provider_status
    assert status.status == "external_success_with_server_repair"
    assert status.server_repair_used and not status.fallback_used
    assert status.server_repair_fields == ["longitudinal_assessment.comment"]
    assert result.validation_status == "passed_with_server_repair"
    assert result.feedback.priority_feedback == original.priority_feedback


def test_case_9_positive_ability_inference_is_repaired_without_whole_feedback_loss(feedback_context):
    original = LocalDemoProvider().generate(PromptBuilder().build(feedback_context).messages, temperature=0.2)
    invalid = original.model_copy(update={
        "positive_finding": original.positive_finding.model_copy(update={
            "explanation": "This indicates strong linguistic control and high rhetorical awareness."
        })
    })
    repaired, fields = FeedbackReliabilityService().repair(invalid, feedback_context)
    assert fields == ["positive_finding.explanation"]
    assert "strong linguistic control" not in repaired.positive_finding.explanation.casefold()
    assert repaired.priority_feedback == original.priority_feedback


def test_cases_7_and_8_provider_failures_are_classified_and_sanitized(feedback_context):
    requested = ProviderRouter(ScriptedProvider([RuntimeError("network unavailable")])).generate(feedback_context)
    assert requested.feedback_provider_status.status == "request_failed"
    assert requested.feedback_provider_status.fallback_used
    assert requested.feedback_provider_status.fallback_reason_code == "request_failed"

    invalid = ProviderOutputError("invalid structured response")
    validated = ProviderRouter(ScriptedProvider([invalid, invalid])).generate(feedback_context)
    status = validated.feedback_provider_status
    assert status.status == "response_validation_failed"
    assert status.correction_attempted and status.correction_validation_status == "failed"
    assert status.fallback_reason_code == "correction_failed"
    assert status.sanitized_reason.count("invalid structured response") == 1

    parsed = ProviderRouter(ScriptedProvider([
        ProviderOutputError("response body was not parseable", reason_code="response_parse_failed"),
        ProviderOutputError("response body was not parseable", reason_code="response_parse_failed"),
    ])).generate(feedback_context)
    assert parsed.feedback_provider_status.status == "response_parse_failed"
    assert parsed.feedback_provider_status.fallback_reason_code == "correction_failed"


def test_case_10_connectives_are_deduplicated_and_grouped_for_display():
    analysis = {"artifacts": {"connective_features": {"detected_connectives": [
        {"text": "However", "normalized_form": "however", "same_form_count": 2,
         "function_category": "contrast", "expression_class": "discourse_connective"},
        {"text": "however", "normalized_form": "however", "same_form_count": 2,
         "function_category": "contrast", "expression_class": "discourse_connective"},
        {"text": "and", "normalized_form": "and", "same_form_count": 4,
         "function_category": "coordination", "expression_class": "coordinating_conjunction"},
    ]}}}
    grouped = grouped_connectives(analysis)
    assert grouped["discourse_connective"] == [
        {"expression": "However", "count": 2, "function": "contrast"}
    ]
    assert grouped["coordinating_conjunction"][0]["expression"] == "and"


def test_migration_9_is_additive_persists_provider_status_and_rolls_back_logically(tmp_path):
    settings, repository, service = local_stack(tmp_path)
    result = service.submit(submission(
        "V071-MIG", "Parks support public health and community activities."
    ), synthetic=True)
    with repository.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 12
        columns = {row[1] for row in connection.execute("PRAGMA table_info(feedback_records)")}
        stored = connection.execute(
            "SELECT provider_status_json FROM feedback_records WHERE essay_id=?", (result.essay_id,)
        ).fetchone()[0]
        assert "fallback_used" in stored
        assert rollback(connection, 11) == 11
        assert connection.execute("SELECT essay_text FROM essays WHERE essay_id=?", (result.essay_id,)).fetchone()
        assert connection.execute(
            "SELECT version FROM configuration_versions WHERE status='active'"
        ).fetchone()[0] == "config-v0.8.2"
        assert upgrade(connection) == 12
        assert repository.get_active_configuration().version == "config-v0.9.0"
    assert settings.application_version == "0.8.0"


def test_api_returns_backward_compatible_and_v071_fields(tmp_path):
    settings = replace(
        load_settings(), database_path=tmp_path / "api-v071.db", llm_provider="local",
        deepseek_api_key=None,
    )
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/v1/submissions", json=submission(
            "V071-API", "Parks support health and community activities."
        ).model_dump(mode="json"))
        assert response.status_code == 201
        payload = response.json()
        assert {"feedback_result", "history", "revision_snapshot"} <= payload.keys()
        assert {
            "feedback_provider_status", "longitudinal_assessment", "revision_group_summary",
            "within_task_revision_trajectory", "ui_empty_states",
        } <= payload.keys()
        assert payload["longitudinal_assessment"]["status"] == "unavailable"
        assert client.get("/api/v1/system/version").json()["schema_version"] == "structured-feedback-v0.7.1"


def test_revision_trajectory_api_returns_pairwise_and_first_to_latest(tmp_path):
    settings = replace(
        load_settings(), database_path=tmp_path / "api-trajectory.db", llm_provider="local",
        deepseek_api_key=None,
    )
    with TestClient(create_app(settings)) as client:
        first = client.post("/api/v1/submissions", json=submission(
            "V071-TRJ", "Parks support health and community activities.", stage="first draft",
        ).model_dump(mode="json")).json()
        second = client.post("/api/v1/submissions", json=submission(
            "V071-TRJ", "Parks support health, shade, and community activities.", day=1,
            stage="revised draft", source=first["submission_id"],
        ).model_dump(mode="json")).json()
        group_id = second["revision_group_summary"]["revision_group_id"]
        response = client.get(f"/api/v1/revisions/{group_id}/trajectory")
        assert response.status_code == 200
        payload = response.json()
        assert len(payload["draft_chain"]) == 2
        assert len(payload["pairwise_comparisons"]) == 1
        assert payload["first_to_latest_comparison"] == payload["pairwise_comparisons"][0]
