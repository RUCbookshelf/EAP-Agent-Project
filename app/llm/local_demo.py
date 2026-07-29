from __future__ import annotations

import json
import re

from app.feedback.exercises import ExerciseGenerator
from app.models import (
    DiagnosisSignal,
    FeedbackItem,
    LongitudinalFeedback,
    PositiveFinding,
    RevisionFeedback,
    StructuredFeedback,
)

from .base import LLMProvider


GUIDANCE = {
    "essay_length": "Add one clearly supported reason or example, then check that it directly answers the prompt.",
    "lexical_repetition": "Underline repeated content words and replace only those whose alternatives preserve the intended meaning.",
    "connective_use": "Check each paragraph boundary and add a connector only where the logical relation is otherwise unclear.",
    "sentence_length_pattern": "Split or combine one sentence at a time and read both versions aloud for clarity.",
    "targeted_review": "Choose one paragraph and test whether its claim, support, and link to the prompt are explicit.",
}


class LocalDemoProvider(LLMProvider):
    provider_name = "local-demo"
    model_name = "heuristic-template-v0.1.1"

    def __init__(self, exercise_generator: ExerciseGenerator | None = None):
        self.exercise_generator = exercise_generator or ExerciseGenerator()

    def generate(self, messages: list[dict[str, str]], *, temperature: float) -> StructuredFeedback:
        del temperature
        payload = json.loads(messages[1]["content"])
        essay_text = payload["submission"]["essay_text"]
        diagnoses = [DiagnosisSignal.model_validate(item) for item in payload["diagnoses"]]
        strengths = [item for item in diagnoses if item.kind == "strength"]
        priorities = [
            item for item in diagnoses
            if item.kind == "improvement" and item.selection_status in {"selected_priority", "raw_signal"}
        ][:2]
        quotes = self._verbatim_fragments(essay_text)
        strength = strengths[0] if strengths else None
        history = payload["learner_history"]
        history_evidence = history["history_evidence"]
        if history_evidence:
            used_ids = [item["history_evidence_id"] for item in history_evidence]
            longitudinal = LongitudinalFeedback(
                comment=(
                    "The supplied prototype history evidence identifies descriptive patterns worth reviewing; "
                    "it does not establish language-ability change. Evidence used: " + ", ".join(used_ids) + "."
                ),
                history_evidence_ids=used_ids,
                confidence="low",
                limitation=history["limitations"][0],
            )
        else:
            longitudinal = LongitudinalFeedback(
                comment="数据不足，无法进行纵向判断。",
                history_evidence_ids=[], confidence="low",
                limitation=history["limitations"][0],
            )
        revision_payload = payload.get("revision_snapshot")
        revision = None
        if revision_payload:
            evidence = revision_payload.get("revision_evidence", [])
            evidence_ids = [item["revision_evidence_id"] for item in evidence[:3]]
            revision = RevisionFeedback(
                comment=(
                    "The local revision engine reports observed text-level changes only; these do not prove "
                    "proficiency growth or that feedback caused the revision. Evidence used: " + ", ".join(evidence_ids) + "."
                ),
                revision_evidence_ids=evidence_ids, confidence="low",
                limitation=revision_payload["limitations"][0],
            )
        return StructuredFeedback(
            positive_finding=PositiveFinding(
                evidence_quote=(strength.evidence_quote_candidates[0] if strength and strength.evidence_quote_candidates else quotes[0]),
                explanation=(
                    f"This exact passage contains the observable {strength.category.replace('_', ' ')} feature; "
                    "the local observation does not establish overall writing ability."
                    if strength else
                    "This exact passage provides a neutral text location for formative review; no reliable automatic strength was inferred."
                ),
            ),
            priority_feedback=[
                FeedbackItem(
                    diagnosis_id=item.diagnosis_id,
                    category=item.category,
                    evidence_quote=(item.evidence_quote_candidates[0] if item.evidence_quote_candidates else quotes[min(index + 1, len(quotes) - 1)]),
                    explanation=item.interpretation,
                    revision_guidance=GUIDANCE.get(item.category, GUIDANCE["targeted_review"]),
                )
                for index, item in enumerate(priorities)
            ],
            exercises=self.exercise_generator.generate(
                priorities, payload.get("diagnostic_calibration", {}).get("exercise_generation")
            ),
            longitudinal=longitudinal,
            revision=revision,
            uncertainty_note=(
                "This feedback uses prototype surface-form heuristics and is not a proficiency assessment, "
                "a validated longitudinal judgment, or a replacement for teacher review."
            ),
        )

    @staticmethod
    def _verbatim_fragments(essay_text: str) -> list[str]:
        fragments = [
            match.group(0).strip()
            for match in re.finditer(r"[^.!?]+(?:[.!?]+|$)", essay_text)
            if match.group(0).strip()
        ]
        return fragments or [essay_text]
