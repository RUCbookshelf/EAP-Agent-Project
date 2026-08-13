"""Semantic-boundary scans for the Review/Scheduling Foundation.

FSRS state is strictly MEMORY SCHEDULING STATE: it must never be named or
exposed as proficiency, mastery, ability, validated acquisition, learning
gain, or any ``mastery_score`` / ``proficiency_score``. These scans fail
closed on any violation in the review module.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import get_args

from app.review.models import (
    ReviewEvent,
    PracticeActivity,
    SchedulerStateSnapshot,
)


ROOT = Path(__file__).resolve().parents[2]
REVIEW_MODULE = ROOT / "app" / "review"

FORBIDDEN_IDENTIFIERS = (
    "mastery_score",
    "proficiency_score",
    "mastery",
    "proficiency",
    "validated_acquisition",
    "learning_gain",
)


def _model_field_names(model) -> set[str]:
    return set(getattr(model, "model_fields", {}).keys())


def test_no_forbidden_scheduling_semantics_in_field_names():
    for model in (SchedulerStateSnapshot, ReviewEvent, PracticeActivity):
        for field in _model_field_names(model):
            lowered = field.casefold()
            assert not any(
                token in lowered for token in FORBIDDEN_IDENTIFIERS
            ), f"{model.__name__}.{field} names scheduling state as mastery/proficiency"


def test_scheduler_state_snapshot_is_scheduling_only():
    assert _model_field_names(SchedulerStateSnapshot) == {
        "card_id", "state", "step", "stability", "difficulty", "due",
        "last_review",
    }


def test_no_absolute_forbidden_identifiers_in_review_module_source():
    """AST-level scan: prose prohibition statements are allowed, but no code
    identifier (field, variable, attribute, key) may carry the forbidden
    scheduling-as-mastery semantics."""
    for path in sorted(REVIEW_MODULE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        identifiers: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                identifiers.add(node.id)
            elif isinstance(node, ast.Attribute):
                identifiers.add(node.attr)
            elif isinstance(node, ast.arg):
                identifiers.add(node.arg)
            elif isinstance(node, ast.keyword) and node.arg is not None:
                identifiers.add(node.arg)
            elif isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                identifiers.add(node.name)
        forbidden = {
            "mastery_score", "proficiency_score",
            "mastery", "proficiency", "validated_acquisition",
            "learning_gain", "ability", "masteryScore",
            "proficiencyScore",
        }
        assert not (identifiers & forbidden), (
            f"{path.name} uses scheduling-state-as-mastery identifiers: "
            f"{sorted(identifiers & forbidden)}"
        )


def test_no_ability_word_in_model_field_names():
    """Case G extension: no model field may name ability semantics.

    Uses word-boundary matching (``\\bability\\b``), not substring, because
    ``stability`` legitimately contains the letters ``ability``; the word
    ``ability`` itself is forbidden everywhere in the review contracts.
    """
    for model in (ReviewEvent, PracticeActivity, SchedulerStateSnapshot):
        for field in _model_field_names(model):
            assert re.search(r"\bability\b", field.casefold()) is None, (
                f"{model.__name__}.{field} names scheduling state as ability"
            )


def test_practice_activity_evidence_kind_is_literal_practice_only():
    annotation = PracticeActivity.model_fields["evidence_kind"].annotation
    assert get_args(annotation) == ("practice",)


def test_fixed_boundary_statements_are_present():
    from app.review.models import (
        FSRS_STATE_IS_SCHEDULING,
        NO_TRANSFER_IMPLICATION,
    )

    assert "memory scheduling state" in FSRS_STATE_IS_SCHEDULING
    assert "not proficiency" in FSRS_STATE_IS_SCHEDULING
    assert "authentic writing evidence" in NO_TRANSFER_IMPLICATION
    assert "does not imply authentic transfer" in NO_TRANSFER_IMPLICATION
