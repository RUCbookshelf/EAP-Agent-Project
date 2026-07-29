from app.llm import LLMProvider, LocalDemoProvider, ProviderOutputError, ProviderRouter
from app.models import StructuredFeedback
from app.prompts import PromptBuilder


class ScriptedProvider(LLMProvider):
    provider_name = "scripted"
    model_name = "scripted-test"
    configured = True

    def __init__(self, responses):
        self.responses = list(responses)
        self.messages_seen = []

    def generate(self, messages, *, temperature):
        self.messages_seen.append(messages)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def make_invalid_quote(feedback):
    payload = feedback.model_dump()
    payload["positive_finding"]["evidence_quote"] = "Fabricated evidence quote."
    return StructuredFeedback.model_validate(payload)


def test_validation_failure_retries_once_then_succeeds(feedback_context):
    bundle = PromptBuilder().build(feedback_context)
    valid = LocalDemoProvider().generate(bundle.messages, temperature=0.2)
    provider = ScriptedProvider([make_invalid_quote(valid), valid])
    result = ProviderRouter(provider).generate(feedback_context)
    assert result.provider_name == "scripted"
    assert result.success_status == "success"
    assert result.retry_count == 1
    assert len(provider.messages_seen) == 2
    assert len(provider.messages_seen[1]) == 3
    assert [audit.validation_status for audit in result.call_audits] == ["failed", "passed"]


def test_second_validation_failure_falls_back(feedback_context):
    bundle = PromptBuilder().build(feedback_context)
    valid = LocalDemoProvider().generate(bundle.messages, temperature=0.2)
    invalid = make_invalid_quote(valid)
    provider = ScriptedProvider([invalid, invalid])
    result = ProviderRouter(provider).generate(feedback_context)
    assert result.provider_name == "local-demo"
    assert result.success_status == "fallback_success"
    assert result.retry_count == 1
    assert len(provider.messages_seen) == 2
    assert len(result.call_audits) == 3
    assert [audit.validation_status for audit in result.call_audits] == ["failed", "failed", "passed"]


def test_schema_output_error_receives_one_correction_retry(feedback_context):
    bundle = PromptBuilder().build(feedback_context)
    valid = LocalDemoProvider().generate(bundle.messages, temperature=0.2)
    provider = ScriptedProvider([
        ProviderOutputError("response failed StructuredFeedback validation"), valid,
    ])
    result = ProviderRouter(provider).generate(feedback_context)
    assert result.provider_name == "scripted"
    assert result.retry_count == 1
    assert len(provider.messages_seen) == 2
    assert "previous response failed validation" in provider.messages_seen[1][-1]["content"].lower()
    assert [audit.validation_status for audit in result.call_audits] == ["failed", "passed"]


def test_two_schema_output_errors_fall_back_without_formal_primary_feedback(feedback_context):
    provider = ScriptedProvider([
        ProviderOutputError("invalid schema response one"),
        ProviderOutputError("invalid schema response two"),
    ])
    result = ProviderRouter(provider).generate(feedback_context)
    assert result.provider_name == "local-demo"
    assert result.success_status == "fallback_success"
    assert result.retry_count == 1
    assert [audit.validation_status for audit in result.call_audits] == ["failed", "failed", "passed"]
