from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.models import StructuredFeedback

if TYPE_CHECKING:
    from app.llm.base import FeedbackContext

from .versioning import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    rendered_prompt_hash,
    system_template,
    system_template_hash,
    user_template_hash,
    validate_prompt_versioning,
)


@dataclass(frozen=True)
class PromptBundle:
    messages: list[dict[str, str]]
    user_payload: dict[str, Any]
    prompt_version: str
    schema_version: str
    system_template_hash: str
    user_template_hash: str
    rendered_prompt_hash: str


class PromptBuilder:
    """Build versioned messages; providers never splice student text into control instructions."""

    def build(self, context: "FeedbackContext") -> PromptBundle:
        validate_prompt_versioning()
        submission = context.submission
        payload = {
            "submission": {
                "essay_text": submission.essay_text,
                "writing_prompt": submission.writing_prompt,
                "genre": submission.genre,
                "draft_stage": submission.draft_stage,
                "timed": submission.timed,
                "time_limit_minutes": submission.time_limit_minutes,
                "tool_use": submission.tool_use,
                "submitted_at": submission.submitted_at.isoformat(),
            },
            "metrics": [
                {"name": name, "value": value}
                for name, value in context.analysis.metrics.items()
            ],
            "diagnoses": [
                signal.model_dump(mode="json") for signal in context.diagnosis.all_signals
            ],
            "learner_history": {
                "comparability_status": context.history.comparability_status,
                "comparable_submission_count": context.history.comparable_submission_count,
                "history_evidence": [
                    item.model_dump(mode="json") for item in context.history.history_evidence
                ],
                "summary": context.history.summary,
                "limitations": context.history.limitations,
                "comparability_reasons": context.history.comparability_reasons,
            },
            "required_schema": StructuredFeedback.model_json_schema(),
        }
        messages = [
            {"role": "system", "content": system_template()},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        return self._bundle(messages, payload)

    def correction(self, bundle: PromptBundle, validation_error: str) -> PromptBundle:
        correction = (
            "The previous response failed validation. Return a corrected JSON object only. "
            "Do not change or add diagnosis IDs, categories, quotations, or history evidence IDs. "
            f"Validation failure: {validation_error[:800]}"
        )
        messages = [*bundle.messages, {"role": "user", "content": correction}]
        return self._bundle(messages, bundle.user_payload)

    @staticmethod
    def _bundle(messages: list[dict[str, str]], payload: dict[str, Any]) -> PromptBundle:
        return PromptBundle(
            messages=messages, user_payload=payload,
            prompt_version=PROMPT_VERSION, schema_version=SCHEMA_VERSION,
            system_template_hash=system_template_hash(),
            user_template_hash=user_template_hash(),
            rendered_prompt_hash=rendered_prompt_hash(messages),
        )
