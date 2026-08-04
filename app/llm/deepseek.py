from __future__ import annotations

import json
import logging
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import ValidationError

from app.models import StructuredFeedback

from .base import LLMProvider, ProviderOutputError

PROVIDER_LOGGER = logging.getLogger("writing_feedback.provider")


class DeepSeekProvider(LLMProvider):
    """Thin OpenAI-compatible transport; prompt policy lives in app.prompts.

    Structured-feedback requests explicitly disable DeepSeek thinking mode
    (v0.9.6-DP0): the provider defaults to thinking enabled, and reasoning
    tokens consumed the 1800-token output budget, truncating the JSON
    (finish_reason=length) and timing out the correction attempt.
    """

    provider_name = "deepseek"

    def __init__(self, api_key: str | None, base_url: str, model_name: str, timeout: float = 30.0,
                 max_tokens: int = 1800):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.last_request_metadata: dict[str, object] = {}
        if not PROVIDER_LOGGER.handlers:
            _handler = logging.StreamHandler()
            _handler.setFormatter(logging.Formatter(
                "%(asctime)s writing_feedback.provider %(levelname)s %(message)s"
            ))
            PROVIDER_LOGGER.addHandler(_handler)
            PROVIDER_LOGGER.setLevel(logging.INFO)
            PROVIDER_LOGGER.propagate = False

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def generate(self, messages: list[dict[str, str]], *, temperature: float) -> StructuredFeedback:
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured")
        # A correction request carries a third message and needs enough room to
        # regenerate the complete structured object after a truncated response.
        output_budget = min(self.max_tokens * (2 if len(messages) > 2 else 1), 8192)
        payload = {
            "model": self.model_name,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
            "temperature": temperature,
            "max_tokens": output_budget,
        }
        try:
            user_payload = json.loads(messages[1]["content"])
            history_count = len(user_payload["learner_history"]["history_evidence"])
            submission_fields = sorted(user_payload["submission"].keys())
        except (IndexError, KeyError, TypeError, json.JSONDecodeError):
            history_count = -1
            submission_fields = []
        self.last_request_metadata = {
            "history_evidence_count": history_count,
            "submission_fields": submission_fields,
            "message_count": len(messages),
            "max_tokens": output_budget,
        }
        request = Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        start = time.monotonic()
        try:
            with urlopen(request, timeout=self.timeout) as response:
                response_data = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            duration_ms = round((time.monotonic() - start) * 1000, 1)
            self.last_request_metadata.update({
                "duration_ms": duration_ms, "json_parse_status": "not_attempted",
                "schema_validation_status": "not_run", "finish_reason": None,
            })
            self._log_call(duration_ms=duration_ms, response_id=None, finish_reason=None,
                           max_tokens=output_budget, content_length=None, parse_status="not_attempted",
                           schema_status="not_run", usage={}, classification=None,
                           error_class=type(exc).__name__)
            raise RuntimeError(f"DeepSeek request failed: {type(exc).__name__}") from exc
        duration_ms = round((time.monotonic() - start) * 1000, 1)
        try:
            choice = response_data["choices"][0]
            content = (choice["message"]["content"] or "").strip()
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ProviderOutputError(
                "DeepSeek response did not contain message content",
                reason_code="response_parse_failed",
            ) from exc
        finish_reason = choice.get("finish_reason")
        usage_raw = response_data.get("usage") or {}
        usage = {
            "prompt_tokens": usage_raw.get("prompt_tokens"),
            "completion_tokens": usage_raw.get("completion_tokens"),
            "total_tokens": usage_raw.get("total_tokens"),
            "reasoning_tokens": (usage_raw.get("completion_tokens_details") or {}).get("reasoning_tokens"),
            "prompt_cache_hit_tokens": usage_raw.get("prompt_cache_hit_tokens"),
            "prompt_cache_miss_tokens": usage_raw.get("prompt_cache_miss_tokens"),
        }
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        parse_status = "success"
        parse_error = None
        try:
            json.loads(content)
        except json.JSONDecodeError as exc:
            parse_status = "failed"
            parse_error = f"{exc.msg} at line {exc.lineno} column {exc.colno}"
        if parse_status == "failed":
            # Malformed JSON is rejected explicitly with a precise classification
            # before pydantic wraps the decode error into a validation summary.
            self._record_metadata(
                response_data, choice, usage, output_budget, content, duration_ms,
                parse_status, "not_run", parse_error,
            )
            self._log_call(duration_ms=duration_ms,
                           response_id=self.last_request_metadata.get("response_id"),
                           finish_reason=finish_reason,
                           max_tokens=output_budget, content_length=len(content),
                           parse_status=parse_status, schema_status="not_run", usage=usage,
                           classification="provider_json_invalid")
            raise ProviderOutputError(
                f"DeepSeek output was not valid JSON: {parse_error}",
                reason_code="provider_json_invalid",
            )
        if finish_reason == "length":
            # A length-truncated generation is never accepted as complete
            # feedback, even when the cut happens to land on a JSON boundary.
            self._record_metadata(
                response_data, choice, usage, output_budget, content, duration_ms,
                parse_status, "not_run", parse_error,
            )
            self._log_call(duration_ms=duration_ms,
                           response_id=self.last_request_metadata.get("response_id"),
                           finish_reason=finish_reason,
                           max_tokens=output_budget, content_length=len(content),
                           parse_status=parse_status, schema_status="not_run", usage=usage,
                           classification="provider_output_truncated")
            raise ProviderOutputError(
                "DeepSeek output was truncated (finish_reason=length); not accepted as complete feedback",
                reason_code="provider_output_truncated",
            )
        try:
            feedback = StructuredFeedback.model_validate_json(content)
        except ValidationError as exc:
            details = self._validation_summary(exc)
            self._record_metadata(
                response_data, choice, usage, output_budget, content, duration_ms,
                parse_status, "failed", parse_error,
            )
            self._log_call(duration_ms=duration_ms,
                           response_id=self.last_request_metadata.get("response_id"),
                           finish_reason=finish_reason,
                           max_tokens=output_budget, content_length=len(content),
                           parse_status=parse_status, schema_status="failed", usage=usage,
                           classification="provider_schema_invalid")
            raise ProviderOutputError(
                f"DeepSeek output failed StructuredFeedback validation: {details}"
            ) from exc
        except ValueError as exc:
            self._record_metadata(
                response_data, choice, usage, output_budget, content, duration_ms,
                parse_status, "failed", parse_error,
            )
            self._log_call(duration_ms=duration_ms,
                           response_id=self.last_request_metadata.get("response_id"),
                           finish_reason=finish_reason,
                           max_tokens=output_budget, content_length=len(content),
                           parse_status=parse_status, schema_status="failed", usage=usage,
                           classification="provider_json_invalid")
            raise ProviderOutputError(
                "DeepSeek output was not valid JSON", reason_code="response_parse_failed"
            ) from exc
        self._record_metadata(
            response_data, choice, usage, output_budget, content, duration_ms,
            parse_status, "passed", parse_error,
        )
        self._log_call(duration_ms=duration_ms,
                       response_id=self.last_request_metadata.get("response_id"),
                       finish_reason=finish_reason,
                       max_tokens=output_budget, content_length=len(content),
                       parse_status=parse_status, schema_status="passed", usage=usage,
                       classification="provider_success")
        return feedback

    def _record_metadata(self, response_data: dict, choice: dict, usage: dict,
                         output_budget: int, content: str, duration_ms: float,
                         parse_status: str, schema_status: str,
                         parse_error: str | None = None) -> None:
        """Retain sanitized response metadata; never stores message content or reasoning content."""
        self.last_request_metadata.update({
            "response_id": response_data.get("id"),
            "returned_model": response_data.get("model"),
            "finish_reason": choice.get("finish_reason"),
            "system_fingerprint": response_data.get("system_fingerprint"),
            "usage": usage,
            "max_tokens": output_budget,
            "content_length": len(content),
            "duration_ms": duration_ms,
            "json_parse_status": parse_status,
            "schema_validation_status": schema_status,
            "json_error": parse_error,
        })

    def _log_call(self, *, duration_ms: float, response_id=None, finish_reason=None, max_tokens: int,
                  content_length, parse_status: str, schema_status: str, usage: dict,
                  classification: str | None, error_class: str | None = None) -> None:
        """Emit one sanitized structured provider-call log line (no secrets or content)."""
        PROVIDER_LOGGER.info(
            "provider_call provider=%s model=%s messages_count=%s duration_ms=%s response_id=%s "
            "finish_reason=%s max_tokens=%s content_length=%s json_parse=%s schema_validation=%s "
            "prompt_tokens=%s completion_tokens=%s reasoning_tokens=%s total_tokens=%s "
            "classification=%s error_class=%s",
            self.provider_name, self.model_name, self.last_request_metadata.get("message_count"),
            duration_ms, response_id, finish_reason, max_tokens, content_length, parse_status,
            schema_status, usage.get("prompt_tokens"), usage.get("completion_tokens"),
            usage.get("reasoning_tokens"), usage.get("total_tokens"), classification, error_class,
        )

    @staticmethod
    def _validation_summary(exc: ValidationError) -> str:
        """Return actionable schema errors without echoing model output or secrets."""
        summaries: list[str] = []
        for error in exc.errors(include_url=False, include_context=False, include_input=False)[:8]:
            location = ".".join(str(part) for part in error.get("loc", ())) or "response"
            summaries.append(
                f"{location}: {error.get('msg', 'invalid value')} [{error.get('type', 'validation_error')}]"
            )
        return "; ".join(summaries) or "schema validation failed"