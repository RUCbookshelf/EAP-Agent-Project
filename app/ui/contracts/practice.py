"""UI-safe Practice presentation contract (v0.9.5-C).

Display-only exercise instruction metadata. The learner-facing bilingual
strings below are the exact strings the backend exercise specification
previously supplied to the Practice page. No evaluation, target-selection,
or domain-validation logic lives here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExerciseInstruction:
    """Display-only learner instructions for one exercise type."""

    exercise_type: str
    learner_instructions: dict[str, str]


EXERCISE_INSTRUCTIONS: dict[str, ExerciseInstruction] = {
    "guided_sentence_rewrite": ExerciseInstruction(
        exercise_type="guided_sentence_rewrite",
        learner_instructions={
            "en": "Rewrite the following sentence to address the selected priority.",
            "zh_CN": "请重写以下句子以解决选定的优先级问题。",
        },
    ),
    "constrained_micro_revision": ExerciseInstruction(
        exercise_type="constrained_micro_revision",
        learner_instructions={
            "en": "Revise this short text under the given constraints.",
            "zh_CN": "请在给定约束下修改这段短文。",
        },
    ),
    "target_feature_identification": ExerciseInstruction(
        exercise_type="target_feature_identification",
        learner_instructions={
            "en": "Identify which part of the passage illustrates the selected issue.",
            "zh_CN": "请指出文章中哪个部分体现了所选问题。",
        },
    ),
}


def exercise_instruction(exercise_type: str, lang: str, fallback: str) -> str:
    """Return the learner instruction with the pre-extraction lookup semantics."""
    specification = EXERCISE_INSTRUCTIONS.get(exercise_type)
    if specification is None:
        return fallback
    return specification.learner_instructions.get(
        lang, specification.learner_instructions.get("en", fallback)
    )
