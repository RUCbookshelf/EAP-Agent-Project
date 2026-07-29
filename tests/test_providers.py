from __future__ import annotations

import json

from app.llm import DeepSeekProvider, LocalDemoProvider, ProviderRouter
from app.models import StructuredFeedback


def test_no_api_key_automatically_uses_local_demo(feedback_context):
    router = ProviderRouter(DeepSeekProvider(None, "https://example.invalid", "deepseek-chat"))
    result = router.generate(feedback_context)
    assert result.provider_name == "local-demo"
    assert result.success_status == "fallback_success"
    assert result.retry_count == 0
    assert "not configured" in result.fallback_reason


def test_deepseek_provider_receives_prebuilt_messages(monkeypatch, prompt_bundle):
    expected = LocalDemoProvider().generate(prompt_bundle.messages, temperature=0.2)

    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self):
            return json.dumps({"choices": [{"message": {"content": expected.model_dump_json()}}]}).encode()

    captured = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["authorization"] = request.headers["Authorization"]
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("app.llm.deepseek.urlopen", fake_urlopen)
    provider = DeepSeekProvider("test-secret", "https://api.example", "deepseek-test")
    feedback = provider.generate(prompt_bundle.messages, temperature=0.2)
    assert isinstance(feedback, StructuredFeedback)
    assert captured["payload"]["messages"] == prompt_bundle.messages
    assert captured["payload"]["temperature"] == 0.2
    assert captured["url"] == "https://api.example/chat/completions"
    assert captured["authorization"].startswith("Bearer ")
    assert provider.last_request_metadata["history_evidence_count"] == 0
    assert "writing_prompt" in provider.last_request_metadata["submission_fields"]


def test_api_failure_falls_back_without_interrupting_pipeline(feedback_context):
    class FailingProvider(DeepSeekProvider):
        def generate(self, messages, *, temperature):
            raise RuntimeError("simulated network failure")

    result = ProviderRouter(FailingProvider("hidden", "https://example.invalid", "test")).generate(feedback_context)
    assert result.success_status == "fallback_success"
    assert result.feedback.priority_feedback
    assert "simulated network failure" in result.fallback_reason
