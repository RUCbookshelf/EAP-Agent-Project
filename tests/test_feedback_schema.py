import pytest
from pydantic import ValidationError

from app.llm import LocalDemoProvider
from app.models import StructuredFeedback


def local_feedback(prompt_bundle):
    return LocalDemoProvider().generate(prompt_bundle.messages, temperature=0.2)


def test_feedback_schema_accepts_local_provider_output(prompt_bundle):
    feedback = local_feedback(prompt_bundle)
    validated = StructuredFeedback.model_validate(feedback.model_dump())
    assert validated.positive_finding.evidence_quote
    assert len(validated.priority_feedback) <= 2
    assert all(item.diagnosis_id.startswith("D") for item in validated.priority_feedback)
    assert {item.exercise_type for item in validated.exercises} <= {
        "error_identification", "sentence_rewrite", "short_writing_transfer"
    }
    assert all(item.expected_response or item.reference_guidance for item in validated.exercises)
    assert validated.longitudinal.history_evidence_ids == []


def test_feedback_schema_rejects_invalid_exercise_type(prompt_bundle):
    payload = local_feedback(prompt_bundle).model_dump()
    payload["exercises"][0]["exercise_type"] = "unsupported"
    with pytest.raises(ValidationError):
        StructuredFeedback.model_validate(payload)
