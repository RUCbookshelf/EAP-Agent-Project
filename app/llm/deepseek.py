from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import ValidationError

from app.models import StructuredFeedback

from .base import LLMProvider, ProviderOutputError


class DeepSeekProvider(LLMProvider):
    """Thin OpenAI-compatible transport; prompt policy lives in app.prompts."""

    provider_name = "deepseek"

    def __init__(self, api_key: str | None, base_url: str, model_name: str, timeout: float = 30.0,
                 max_tokens: int = 1800):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.last_request_metadata: dict[str, object] = {}

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def generate(self, messages: list[dict[str, str]], *, temperature: float) -> StructuredFeedback:
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured")
        payload = {
            "model": self.model_name,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": temperature,
            "max_tokens": self.max_tokens,
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
        }
        request = Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                response_data = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"DeepSeek request failed: {type(exc).__name__}") from exc
        try:
            content = response_data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ProviderOutputError("DeepSeek response did not contain message content") from exc
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        try:
            return StructuredFeedback.model_validate_json(content)
        except ValidationError as exc:
            raise ProviderOutputError("DeepSeek output failed StructuredFeedback validation") from exc
        except ValueError as exc:
            raise ProviderOutputError("DeepSeek output was not valid JSON") from exc
