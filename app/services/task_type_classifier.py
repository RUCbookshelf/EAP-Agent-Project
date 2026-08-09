"""Deterministic L2 task-type classification (Domain Pack v1 content, G5).

Implements the closed, versioned, rule-based decision procedure fixed by
``docs/domain/L2_TASK_TYPE_TAXONOMY_CONTRACT.md`` Constraints 1-3 and 6-7,
using the G5 trigger dictionaries and conflict-pair table shipped as Domain
Pack v1 content (``app/configuration/domain_packs/l2/v1.0.0``).

Semantics are task-routing / task-semantics metadata ONLY:

- the classifier assigns one of the five types (opinion, argumentative,
  discussion, problem_solution, general_eap) or the honest ``unclassified``
  state with a reason code;
- it NEVER assigns ``legacy_unclassified`` (that sentinel is produced only by
  the D-22 legacy mapping lane for historical rows);
- it NEVER measures learners, orders types, or participates in any
  comparability predicate;
- no model output, no LLM judgment, and no probabilistic scoring is used.

The V1 adjudication outcomes (A-1..A-8) are implemented here: A-1/A-2
(discussion > opinion chain for balanced treatment + viewpoint request),
A-3 (conflict-pair table is pack content; canonical pair argumentative +
discussion), A-4 (problem_solution > argumentative by chain), A-5 (general_eap
condition (c) is a version-binding hook), A-6 (unit of classification is the
registered task definition), A-7 (effects-only prompts never match
problem_solution), A-8 (mandate detection is dictionary-based G5 content).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.shared.task_type_registry import LEGACY_UNCLASSIFIED

_PACK_DIR = (
    Path(__file__).resolve().parents[1]
    / "configuration" / "domain_packs" / "l2" / "v1.0.0"
)

# Priority chain (taxonomy contract section 4): highest first.
_PRECEDENCE: tuple[str, ...] = (
    "problem_solution",
    "argumentative",
    "discussion",
    "opinion",
    "general_eap",
)

_SPECIFIC_TYPES: tuple[str, ...] = (
    "opinion",
    "argumentative",
    "discussion",
    "problem_solution",
)

_TYPE_IDS: tuple[str, ...] = _PRECEDENCE

# Reason codes for the unclassified state (new-task classification).
REASON_NO_PROMPT = "no_prompt"
REASON_NOT_EAP = "not_eap"
REASON_AMBIGUOUS_CONFLICT = "ambiguous_precedence_conflict"
REASON_DECLARED_MISMATCH = "declared_type_mismatch"


class TaskTypeClassificationError(ValueError):
    """Raised for invalid classifier inputs (rejection path, D-L2-10)."""


@dataclass(frozen=True)
class ClassificationResult:
    """Deterministic classification outcome for one task definition.

    ``task_type`` is set for typed outcomes and None for ``unclassified``.
    ``reason_code`` is set for unclassified outcomes (and never for typed).
    ``matched_triggers`` records every dictionary phrase matched in the
    normalized prompt (provenance, contract Constraint 2.4).
    """

    task_type: str | None
    outcome: str
    reason_code: str | None
    taxonomy_version: str
    dictionary_version: str
    matched_triggers: tuple[dict[str, str], ...] = field(default_factory=tuple)
    provenance: dict[str, Any] = field(default_factory=dict)


@lru_cache(maxsize=1)
def _load_json(name: str) -> dict[str, Any]:
    path = _PACK_DIR / name
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def load_trigger_dictionaries() -> dict[str, Any]:
    """Return the versioned G5 trigger dictionaries (pack content)."""
    return _load_json("trigger_dictionaries.json")


def load_conflict_pairs() -> dict[str, Any]:
    """Return the versioned G5 conflict-pair table (pack content)."""
    return _load_json("conflict_pairs.json")


def load_task_types() -> dict[str, Any]:
    """Return the versioned five-type definitions (pack content)."""
    return _load_json("task_types.json")


def normalize_prompt(prompt: str | None) -> str:
    """Normalize a task prompt for classification (contract Constraint 1.2).

    NFC + casefold + strip + Unicode-whitespace collapse. No punctuation
    stripping: word-boundary matching handles punctuation adjacency for
    English, and multi-character phrases are matched as substrings for zh_CN.
    """
    if prompt is None:
        return ""
    text = unicodedata.normalize("NFC", str(prompt))
    text = text.casefold().strip()
    return re.sub(r"\s+", " ", text)


def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    escaped = re.escape(phrase)
    # Phrase-internal whitespace may be any whitespace run.
    inner = escaped.replace(r"\ ", r"\s+")
    return re.compile(r"\b" + inner + r"\b")


def _match_phrase(phrase: str, normalized: str) -> bool:
    if any("\u4e00" <= ch <= "\u9fff" for ch in phrase):
        # zh_CN: substring matching (multi-character phrases by content
        # validation); Chinese has no word boundaries.
        return phrase in normalized
    return _phrase_pattern(phrase).search(normalized) is not None


def match_triggers(prompt: str) -> list[dict[str, str]]:
    """Match trigger dictionaries against a normalized prompt.

    Returns a list of ``{"task_type", "group", "phrase", "locale"}`` records
    for every matched phrase (both en and zh_CN dictionaries are matched).
    """
    dictionaries = load_trigger_dictionaries()
    normalized = normalize_prompt(prompt)
    matches: list[dict[str, str]] = []
    for task_type, spec in dictionaries["types"].items():
        for group, group_spec in spec["groups"].items():
            for locale in ("en", "zh_CN"):
                for phrase in group_spec.get(locale, []):
                    if _match_phrase(phrase, normalized):
                        matches.append({
                            "task_type": task_type,
                            "group": group,
                            "phrase": phrase,
                            "locale": locale,
                        })
    return matches


def _group_matches(
    matches: list[dict[str, str]], task_type: str, group: str,
) -> bool:
    return any(
        item["task_type"] == task_type and item["group"] == group
        for item in matches
    )


def _full_matches(matches: list[dict[str, str]]) -> set[str]:
    """Compute the set of fully-matched trigger classes (pack composition)."""
    opinion_viewpoint = _group_matches(matches, "opinion", "viewpoint_request")
    evidence = _group_matches(matches, "argumentative", "evidence_mandate")
    full: set[str] = set()

    if _group_matches(matches, "problem_solution", "cause_or_solution_mandate") and (
        _group_matches(matches, "problem_solution", "problem_naming")
        or _group_matches(matches, "problem_solution", "topic_referencing")
    ):
        full.add("problem_solution")

    if (_group_matches(matches, "argumentative", "stance_mandate") or opinion_viewpoint) and evidence:
        full.add("argumentative")

    if _group_matches(matches, "discussion", "balanced_multiperspective"):
        full.add("discussion")

    if opinion_viewpoint and not evidence:
        full.add("opinion")

    return full


def _conflict_detected(full: set[str]) -> bool:
    pairs = load_conflict_pairs()["pairs"]
    for pair_spec in pairs:
        left, right = pair_spec["pair"]
        if left in full and right in full:
            return True
    return False


def _taxonomy_version() -> str:
    return load_trigger_dictionaries()["taxonomy_version"]


def _dictionary_version() -> str:
    return load_trigger_dictionaries()["dictionary_version"]


def classify_task_definition(
    prompt: str | None,
    declared_task_type: str | None = None,
) -> ClassificationResult:
    """Deterministically classify one registered task definition.

    The unit of classification is the registered task definition (one prompt
    plus declared task metadata, V1 adjudication A-6). Classification NEVER
    operates on learner output, learner behavior, or learner history
    (contract Constraint 1.1).

    ``declared_task_type`` is optional declared task metadata (D-L2-10
    picker, deferred; dormant until a picker consumer exists). An unknown
    declared id is rejected (``TaskTypeClassificationError``); a valid
    declared id that disagrees with the prompt-derived outcome yields
    ``unclassified`` with reason code ``declared_type_mismatch`` (Domain Pack
    v1 content decision, recorded in docs/domain/L2_DOMAIN_PACK_V1_CONTENT.md).
    """
    matches = match_triggers(prompt or "")
    normalized_prompt = normalize_prompt(prompt)
    full = _full_matches(matches)

    if not normalized_prompt:
        outcome = "unclassified"
        task_type = None
        reason = REASON_NO_PROMPT
    elif _conflict_detected(full):
        outcome = "unclassified"
        task_type = None
        reason = REASON_AMBIGUOUS_CONFLICT
    elif full:
        task_type = next(item for item in _PRECEDENCE if item in full)
        outcome = "typed"
        reason = None
    elif _group_matches(matches, "general_eap", "eap_affirmative"):
        task_type = "general_eap"
        outcome = "typed"
        reason = None
    else:
        outcome = "unclassified"
        task_type = None
        reason = REASON_NOT_EAP

    if declared_task_type is not None:
        if declared_task_type not in _TYPE_IDS:
            raise TaskTypeClassificationError(
                f"Unknown declared task type: {declared_task_type!r}. "
                f"Valid types: {list(_TYPE_IDS)}"
            )
        if outcome == "typed" and declared_task_type != task_type:
            outcome = "unclassified"
            reason = REASON_DECLARED_MISMATCH
            provenance = {
                "declared_task_type": declared_task_type,
                "prompt_derived_task_type": task_type,
                "note": "Declared metadata disagrees with the deterministic "
                        "prompt classification; no coercion (contract Constraint 6).",
            }
            task_type = None
        elif outcome == "typed":
            provenance = {
                "declared_task_type": declared_task_type,
                "declaration_agreement": True,
            }
        else:
            provenance = {
                "declared_task_type": declared_task_type,
                "note": "Prompt-derived outcome is unclassified; declaration "
                        "cannot be confirmed and no coercion is applied "
                        "(contract Constraint 6).",
            }
    else:
        provenance = {}

    provenance.update({
        "rule_version": _dictionary_version(),
        "classification_scope": "task_definition_only",
        "legacy_sentinel_unreachable": LEGACY_UNCLASSIFIED,
    })

    return ClassificationResult(
        task_type=task_type,
        outcome=outcome,
        reason_code=reason,
        taxonomy_version=_taxonomy_version(),
        dictionary_version=_dictionary_version(),
        matched_triggers=tuple(matches),
        provenance=provenance,
    )


def canonical_display_order() -> list[str]:
    """Canonical non-hierarchical display order (D-L2-09, contract section 1)."""
    return list(load_task_types()["display_order"])
