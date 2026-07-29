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
from . import versioning_v04


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
        is_v04 = context.analysis.analyzer_id == "spacy" or context.analysis.analysis_version.startswith("spacy-analyzer-v0.4")
        if is_v04:
            versioning_v04.validate_prompt_versioning()
        else:
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
            "learner_profile_snapshot": self._screened_snapshot(context.learner_profile_snapshot),
            "required_schema": StructuredFeedback.model_json_schema(),
        }
        if is_v04:
            payload["analysis_evidence"] = self._analysis_evidence(context.analysis)
        messages = [
            {"role": "system", "content": versioning_v04.system_template() if is_v04 else system_template()},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        return self._bundle(messages, payload, is_v04=is_v04)

    @staticmethod
    def _analysis_evidence(analysis):
        artifacts = analysis.artifacts
        lexical = artifacts.get("lexical_features", {})
        connective = artifacts.get("connective_features", {})
        syntactic = artifacts.get("syntactic_features", {})
        return {
            "analysis_run_id": analysis.analysis_run_id,
            "analyzer_id": analysis.analyzer_id, "analyzer_version": analysis.analyzer_version,
            "backend": analysis.backend, "nlp_library": analysis.nlp_library,
            "nlp_library_version": analysis.nlp_library_version,
            "nlp_model_name": analysis.nlp_model_name, "nlp_model_version": analysis.nlp_model_version,
            "parameters": analysis.parameters, "resource_versions": analysis.resource_versions,
            "configuration_version": analysis.configuration_version,
            "fallback_used": analysis.fallback_used, "fallback_reason": analysis.fallback_reason,
            "input_quality": analysis.input_quality,
            "lexical_features": lexical, "prompt_keywords": lexical.get("prompt_keywords", []),
            "detected_connectives": connective.get("detected_connectives", []),
            "syntactic_candidates": syntactic,
            "metric_results": analysis.metric_results, "limitations": analysis.limitations,
        }

    @staticmethod
    def _screened_snapshot(snapshot):
        if snapshot is None:
            return None
        return {
            "snapshot_id": snapshot.snapshot_id,
            "baseline_status": snapshot.baseline_status,
            "included_submission_ids": snapshot.included_submission_ids,
            "metric_trends": {
                name: {
                    "metric_name": trend.metric_name, "direction": trend.direction,
                    "slope": trend.slope, "variability": trend.variability,
                    "data_points": trend.data_points, "confidence": trend.confidence,
                    "interpretation": trend.interpretation, "limitations": trend.limitations,
                    "analysis_version": trend.analysis_version,
                }
                for name, trend in snapshot.metric_trends.items()
            },
            "persistent_issues": [item.model_dump(mode="json") for item in snapshot.persistent_issues],
            "recently_reduced_issues": [item.model_dump(mode="json") for item in snapshot.recently_reduced_issues],
            "current_priority_candidates": [item.model_dump(mode="json") for item in snapshot.current_priority_candidates],
            "confidence_summary": snapshot.confidence_summary,
            "limitations": snapshot.limitations,
            "analysis_version": snapshot.analysis_version,
            "configuration_version": snapshot.configuration_version,
        }

    def correction(self, bundle: PromptBundle, validation_error: str) -> PromptBundle:
        correction = (
            "The previous response failed validation. Return a corrected JSON object only. "
            "Do not change or add diagnosis IDs, categories, quotations, or history evidence IDs. "
            f"Validation failure: {validation_error[:800]}"
        )
        messages = [*bundle.messages, {"role": "user", "content": correction}]
        return self._bundle(messages, bundle.user_payload, is_v04=bundle.prompt_version == versioning_v04.PROMPT_VERSION)

    @staticmethod
    def _bundle(messages: list[dict[str, str]], payload: dict[str, Any], *, is_v04: bool = False) -> PromptBundle:
        if is_v04:
            return PromptBundle(
                messages=messages, user_payload=payload,
                prompt_version=versioning_v04.PROMPT_VERSION,
                schema_version=versioning_v04.SCHEMA_VERSION,
                system_template_hash=versioning_v04.system_template_hash(),
                user_template_hash=versioning_v04.user_template_hash(),
                rendered_prompt_hash=versioning_v04.rendered_prompt_hash(messages),
            )
        return PromptBundle(
            messages=messages, user_payload=payload,
            prompt_version=PROMPT_VERSION, schema_version=SCHEMA_VERSION,
            system_template_hash=system_template_hash(),
            user_template_hash=user_template_hash(),
            rendered_prompt_hash=rendered_prompt_hash(messages),
        )
