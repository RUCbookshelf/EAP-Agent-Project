"""v0.9.6-DP0-B focused provider tests.

Covers the owner-approved DP0-B test list: thinking mode disabled on the
structured-feedback request, metadata capture, truncation classification,
strict rejection of truncated/invalid JSON, retry/fallback policy, bounded
attempts, and unchanged submission timeouts.
"""

from __future__ import annotations

import json

import pytest

from app.llm import DeepSeekProvider, LocalDemoProvider, ProviderOutputError, ProviderRouter
from app.llm.deepseek import PROVIDER_LOGGER
from app.ui.api_client import LONG_SUBMIT_TIMEOUTS, WritingFeedbackApiClient


def _envelope(content: str, *, finish_reason: str = "stop", model: str = "deepseek-v4-pro",
              response_id: str = "resp-0001", usage: dict | None = None) -> dict:
    return {
        "id": response_id,
        "model": model,
        "system_fingerprint": "fp_test",
        "choices": [{"finish_reason": finish_reason, "index": 0,
                     "message": {"content": content, "reasoning_content": ""}}],
        "usage": usage or {"prompt_tokens": 100, "completion_tokens": 50,
                           "total_tokens": 150,
                           "completion_tokens_details": {"reasoning_tokens": 0}},
    }


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._payload


def _fake_urlopen(payloads, captured):
    def fake(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        captured["calls"] = captured.get("calls", 0) + 1
        item = payloads[min(captured["calls"] - 1, len(payloads) - 1)]
        if isinstance(item, Exception):
            raise item
        return _FakeResponse(item)
    return fake


def test_effective_model_remains_deepseek_v4_pro(settings):
    provider = DeepSeekProvider(settings.deepseek_api_key, settings.deepseek_base_url,
                                settings.deepseek_model)
    assert provider.model_name == settings.deepseek_model
    assert provider.provider_name == "deepseek"
    # The production model identifier is verified live in DP0-B (deepseek-v4-pro).


def test_json_response_format_and_thinking_disabled_sent(monkeypatch, prompt_bundle):
    expected = LocalDemoProvider().generate(prompt_bundle.messages, temperature=0.2)
    captured = {}
    monkeypatch.setattr(
        "app.llm.deepseek.urlopen",
        _fake_urlopen([_envelope(expected.model_dump_json())], captured),
    )
    provider = DeepSeekProvider("test-secret", "https://api.example", "deepseek-v4-pro")
    provider.generate(prompt_bundle.messages, temperature=0.2)
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert captured["payload"]["thinking"] == {"type": "disabled"}
    assert captured["payload"]["model"] == "deepseek-v4-pro"
    assert captured["payload"]["max_tokens"] == 1800


def test_finish_reason_stop_accepted_and_metadata_captured(monkeypatch, prompt_bundle):
    expected = LocalDemoProvider().generate(prompt_bundle.messages, temperature=0.2)
    usage = {"prompt_tokens": 14949, "completion_tokens": 764, "total_tokens": 15713,
             "completion_tokens_details": {"reasoning_tokens": 0}}
    captured = {}
    monkeypatch.setattr(
        "app.llm.deepseek.urlopen",
        _fake_urlopen([_envelope(expected.model_dump_json(), usage=usage)], captured),
    )
    provider = DeepSeekProvider("test-secret", "https://api.example", "deepseek-v4-pro")
    feedback = provider.generate(prompt_bundle.messages, temperature=0.2)
    assert feedback == expected
    meta = provider.last_request_metadata
    assert meta["finish_reason"] == "stop"
    assert meta["response_id"] == "resp-0001"
    assert meta["returned_model"] == "deepseek-v4-pro"
    assert meta["usage"]["completion_tokens"] == 764
    assert meta["usage"]["reasoning_tokens"] == 0
    assert meta["max_tokens"] == 1800
    assert meta["content_length"] > 0
    assert meta["duration_ms"] >= 0
    assert meta["json_parse_status"] == "success"
    assert meta["schema_validation_status"] == "passed"


def test_finish_reason_length_classified_as_truncation(monkeypatch, prompt_bundle):
    usage = {"prompt_tokens": 100, "completion_tokens": 1800, "total_tokens": 1900,
             "completion_tokens_details": {"reasoning_tokens": 1300}}
    captured = {}
    # Content happens to be parseable JSON, but finish_reason=length must still be rejected.
    monkeypatch.setattr(
        "app.llm.deepseek.urlopen",
        _fake_urlopen([_envelope('{"valid": "json"}', finish_reason="length", usage=usage)], captured),
    )
    provider = DeepSeekProvider("test-secret", "https://api.example", "deepseek-v4-pro")
    with pytest.raises(ProviderOutputError) as caught:
        provider.generate(prompt_bundle.messages, temperature=0.2)
    assert caught.value.reason_code == "provider_output_truncated"
    assert provider.last_request_metadata["finish_reason"] == "length"
    assert provider.last_request_metadata["usage"]["reasoning_tokens"] == 1300
    assert provider.last_request_metadata["schema_validation_status"] == "not_run"


def test_incomplete_json_rejected_without_repair(monkeypatch, prompt_bundle):
    captured = {}
    monkeypatch.setattr(
        "app.llm.deepseek.urlopen",
        _fake_urlopen([_envelope('{"positive_finding": {"evidence_quote": "unfinished')], captured),
    )
    provider = DeepSeekProvider("test-secret", "https://api.example", "deepseek-v4-pro")
    with pytest.raises(ProviderOutputError) as caught:
        provider.generate(prompt_bundle.messages, temperature=0.2)
    assert caught.value.reason_code == "provider_json_invalid"
    assert provider.last_request_metadata["json_parse_status"] == "failed"
    assert "unfinished" not in str(caught.value)
    assert "Unterminated string" in str(caught.value)


def test_missing_required_fields_remain_invalid(monkeypatch, prompt_bundle):
    captured = {}
    monkeypatch.setattr(
        "app.llm.deepseek.urlopen",
        _fake_urlopen([_envelope('{"positive_finding": {}}')], captured),
    )
    provider = DeepSeekProvider("test-secret", "https://api.example", "deepseek-v4-pro")
    with pytest.raises(ProviderOutputError) as caught:
        provider.generate(prompt_bundle.messages, temperature=0.2)
    assert "positive_finding.evidence_quote" in str(caught.value)
    assert provider.last_request_metadata["schema_validation_status"] == "failed"


def _capture_provider_logs():
    import logging
    records: list[str] = []
    handler = logging.Handler()
    handler.emit = lambda record: records.append(record.getMessage())
    PROVIDER_LOGGER.addHandler(handler)
    return records, handler


def test_reasoning_content_neither_logged_nor_stored(monkeypatch, prompt_bundle):
    expected = LocalDemoProvider().generate(prompt_bundle.messages, temperature=0.2)
    usage = {"prompt_tokens": 100, "completion_tokens": 1800, "total_tokens": 1900,
             "completion_tokens_details": {"reasoning_tokens": 1300}}
    captured = {}
    monkeypatch.setattr(
        "app.llm.deepseek.urlopen",
        _fake_urlopen([_envelope(expected.model_dump_json(), finish_reason="length",
                                 usage=usage)], captured),
    )
    records, handler = _capture_provider_logs()
    provider = DeepSeekProvider("test-secret", "https://api.example", "deepseek-v4-pro")
    with pytest.raises(ProviderOutputError):
        provider.generate(prompt_bundle.messages, temperature=0.2)
    PROVIDER_LOGGER.removeHandler(handler)
    assert "reasoning_content" not in provider.last_request_metadata
    assert "reasoning_tokens" in provider.last_request_metadata["usage"]
    assert "secret" not in str(provider.last_request_metadata)
    assert not any("test-secret" in line for line in records)


def test_secret_and_essay_redaction(monkeypatch, prompt_bundle):
    expected = LocalDemoProvider().generate(prompt_bundle.messages, temperature=0.2)
    captured = {}
    monkeypatch.setattr(
        "app.llm.deepseek.urlopen",
        _fake_urlopen([_envelope(expected.model_dump_json())], captured),
    )
    records, handler = _capture_provider_logs()
    provider = DeepSeekProvider("sk-test-secret-123", "https://api.example", "deepseek-v4-pro")
    provider.generate(prompt_bundle.messages, temperature=0.2)
    PROVIDER_LOGGER.removeHandler(handler)
    meta_text = json.dumps(provider.last_request_metadata)
    assert "sk-test-secret-123" not in meta_text
    essay_fragment = "parks give residents space to exercise"
    assert essay_fragment not in meta_text
    log_text = " ".join(records)
    assert "sk-test-secret-123" not in log_text
    assert essay_fragment not in log_text


def test_initial_attempt_success_produces_no_correction(monkeypatch, feedback_context, prompt_bundle):
    expected = LocalDemoProvider().generate(prompt_bundle.messages, temperature=0.2)
    captured = {}
    monkeypatch.setattr(
        "app.llm.deepseek.urlopen",
        _fake_urlopen([_envelope(expected.model_dump_json())], captured),
    )
    router = ProviderRouter(DeepSeekProvider("test-secret", "https://api.example", "deepseek-v4-pro"))
    result = router.generate(feedback_context)
    assert result.success_status == "success"
    assert result.provider_name == "deepseek"
    assert result.retry_count == 0
    assert captured["calls"] == 1
    assert result.feedback_provider_status.correction_attempted is False
    assert result.feedback_provider_status.fallback_used is False


def test_one_correctable_failure_permits_one_correction(monkeypatch, feedback_context, prompt_bundle):
    expected = LocalDemoProvider().generate(prompt_bundle.messages, temperature=0.2)
    captured = {}
    monkeypatch.setattr(
        "app.llm.deepseek.urlopen",
        _fake_urlopen([
            _envelope('{"positive_finding": {}}'),  # schema-invalid -> correction
            _envelope(expected.model_dump_json()),   # corrected success
        ], captured),
    )
    router = ProviderRouter(DeepSeekProvider("test-secret", "https://api.example", "deepseek-v4-pro"))
    result = router.generate(feedback_context)
    assert result.success_status == "success"
    assert result.retry_count == 1
    assert captured["calls"] == 2
    assert result.feedback_provider_status.correction_attempted is True
    assert result.feedback_provider_status.fallback_used is False


def test_request_failure_follows_approved_policy(monkeypatch, feedback_context):
    captured = {}
    monkeypatch.setattr(
        "app.llm.deepseek.urlopen",
        _fake_urlopen([TimeoutError("simulated timeout")], captured),
    )
    router = ProviderRouter(DeepSeekProvider("test-secret", "https://api.example", "deepseek-v4-pro"))
    result = router.generate(feedback_context)
    assert result.success_status == "fallback_success"
    assert result.provider_name == "local-demo"
    assert result.feedback_provider_status.fallback_used is True
    assert result.feedback_provider_status.correction_attempted is False
    assert captured["calls"] == 1
    assert "timeout" in result.fallback_reason.lower()


def test_fallback_never_reported_as_live_provider_success(monkeypatch, feedback_context):
    captured = {}
    monkeypatch.setattr(
        "app.llm.deepseek.urlopen",
        _fake_urlopen([TimeoutError("simulated timeout")], captured),
    )
    router = ProviderRouter(DeepSeekProvider("test-secret", "https://api.example", "deepseek-v4-pro"))
    result = router.generate(feedback_context)
    assert result.success_status == "fallback_success"
    assert result.feedback_provider_status.status == "request_failed"
    assert result.feedback_provider_status.fallback_used is True


def test_attempt_budget_bounded(monkeypatch, feedback_context):
    captured = {}
    monkeypatch.setattr(
        "app.llm.deepseek.urlopen",
        _fake_urlopen([_envelope('{"positive_finding": {}}'),
                       _envelope('{"positive_finding": {}}')], captured),
    )
    router = ProviderRouter(DeepSeekProvider("test-secret", "https://api.example", "deepseek-v4-pro"))
    result = router.generate(feedback_context)
    assert result.success_status == "fallback_success"
    assert captured["calls"] == 2
    assert result.retry_count == 1


def test_submission_timeouts_remain_180_seconds():
    assert LONG_SUBMIT_TIMEOUTS.read == 180.0
    assert LONG_SUBMIT_TIMEOUTS.write == 180.0
    client = WritingFeedbackApiClient("http://127.0.0.1:1")
    assert client.timeouts is not None
    assert client.timeouts.read == 10.0

def test_provider_log_line_includes_response_id(monkeypatch, prompt_bundle):
    expected = LocalDemoProvider().generate(prompt_bundle.messages, temperature=0.2)
    captured = {}
    monkeypatch.setattr(
        "app.llm.deepseek.urlopen",
        _fake_urlopen([_envelope(expected.model_dump_json(), response_id="resp-7777")], captured),
    )
    records, handler = _capture_provider_logs()
    provider = DeepSeekProvider("test-secret", "https://api.example", "deepseek-v4-pro")
    provider.generate(prompt_bundle.messages, temperature=0.2)
    PROVIDER_LOGGER.removeHandler(handler)
    assert any("resp-7777" in line for line in records)
