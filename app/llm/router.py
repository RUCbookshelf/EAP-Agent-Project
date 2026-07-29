from __future__ import annotations

from datetime import datetime, timezone
import re

from app.feedback.validation import FeedbackValidationError, FeedbackValidator
from app.models import LLMCallAudit, ProviderResult
from app.prompts import PromptBuilder, PromptBundle

from .base import FeedbackContext, LLMProvider, ProviderOutputError
from .local_demo import LocalDemoProvider


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProviderRouter:
    temperature = 0.2

    def __init__(self, primary: LLMProvider, fallback: LocalDemoProvider | None = None,
                 prompt_builder: PromptBuilder | None = None,
                 validator: FeedbackValidator | None = None):
        self.primary = primary
        self.fallback = fallback or LocalDemoProvider()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.validator = validator or FeedbackValidator()

    def generate(self, context: FeedbackContext) -> ProviderResult:
        original = self.prompt_builder.build(context)
        if isinstance(self.primary, LocalDemoProvider):
            return self._local_result(context, original, success_status="success", call_audits=[])

        audits: list[LLMCallAudit] = []
        bundle = original
        failures: list[str] = []
        max_attempts = 1 if not getattr(self.primary, "configured", True) else 2
        for attempt in range(max_attempts):
            request_time = utc_now()
            try:
                feedback = self.primary.generate(bundle.messages, temperature=self.temperature)
                self.validator.validate(feedback, context)
                response_time = utc_now()
                audits.append(self._audit(
                    bundle, self.primary, request_time, response_time, "success", "passed", attempt,
                ))
                return ProviderResult(
                    feedback=feedback, provider_name=self.primary.provider_name,
                    model_name=self.primary.model_name, success_status="success",
                    validation_status="passed", retry_count=attempt,
                    prompt_version=bundle.prompt_version,
                    system_template_hash=bundle.system_template_hash,
                    user_template_hash=bundle.user_template_hash,
                    rendered_prompt_hash=bundle.rendered_prompt_hash,
                    schema_version=bundle.schema_version, temperature=self.temperature,
                    request_time=request_time, response_time=response_time, call_audits=audits,
                )
            except (FeedbackValidationError, ProviderOutputError) as exc:
                response_time = utc_now()
                failure = self._safe_failure(exc)
                failures.append(failure)
                audits.append(self._audit(
                    bundle, self.primary, request_time, response_time, "failed", "failed", attempt,
                    failure,
                ))
                if attempt == 0 and max_attempts == 2:
                    bundle = self.prompt_builder.correction(original, failure)
                    continue
                break
            except Exception as exc:
                response_time = utc_now()
                failure = self._safe_failure(exc)
                failures.append(failure)
                audits.append(self._audit(
                    bundle, self.primary, request_time, response_time, "failed", "not_run", attempt,
                    failure,
                ))
                break

        fallback_reason = " | ".join(failures)[-1200:]
        return self._local_result(
            context, original, success_status="fallback_success", call_audits=audits,
            fallback_reason=fallback_reason, retry_count=max(0, len(audits) - 1),
        )

    def _local_result(self, context: FeedbackContext, bundle: PromptBundle, *,
                      success_status: str, call_audits: list[LLMCallAudit],
                      fallback_reason: str | None = None, retry_count: int = 0) -> ProviderResult:
        request_time = utc_now()
        feedback = self.fallback.generate(bundle.messages, temperature=self.temperature)
        self.validator.validate(feedback, context)
        response_time = utc_now()
        local_status = "fallback_success" if success_status == "fallback_success" else "success"
        call_audits.append(self._audit(
            bundle, self.fallback, request_time, response_time,
            local_status, "passed", retry_count, fallback_reason,
        ))
        return ProviderResult(
            feedback=feedback, provider_name=self.fallback.provider_name,
            model_name=self.fallback.model_name, success_status=success_status,
            validation_status="passed", retry_count=retry_count,
            fallback_reason=fallback_reason, prompt_version=bundle.prompt_version,
            system_template_hash=bundle.system_template_hash,
            user_template_hash=bundle.user_template_hash,
            rendered_prompt_hash=bundle.rendered_prompt_hash,
            schema_version=bundle.schema_version, temperature=self.temperature,
            request_time=request_time, response_time=response_time, call_audits=call_audits,
        )

    def _audit(self, bundle: PromptBundle, provider: LLMProvider,
               request_time: datetime, response_time: datetime,
               success_status: str, validation_status: str, retry_count: int,
               fallback_reason: str | None = None) -> LLMCallAudit:
        return LLMCallAudit(
            prompt_version=bundle.prompt_version,
            system_template_hash=bundle.system_template_hash,
            user_template_hash=bundle.user_template_hash,
            rendered_prompt_hash=bundle.rendered_prompt_hash,
            schema_version=bundle.schema_version,
            provider_name=provider.provider_name, model_name=provider.model_name,
            temperature=self.temperature, request_time=request_time, response_time=response_time,
            success_status=success_status, validation_status=validation_status,
            retry_count=retry_count, fallback_reason=fallback_reason,
        )

    def _safe_failure(self, exc: Exception) -> str:
        value = f"{type(exc).__name__}: {str(exc)}"
        secret = getattr(self.primary, "api_key", None)
        if secret:
            value = value.replace(str(secret), "[REDACTED]")
        value = re.sub(r"(?i)Bearer\s+[A-Za-z0-9._-]+", "Bearer [REDACTED]", value)
        value = re.sub(r"\bsk-[A-Za-z0-9_-]{8,}\b", "[REDACTED]", value)
        return value[:1200]
