"""Explicit-only legacy genre -> task_type mapping (D-22, manifest v1.0.0).

Historical rows carry arbitrary free-text ``genre`` and no ``task_type``.
This module applies the approved, versioned mapping manifest
(``l2-legacy-genre-mapping-v1.0.0``, QUALIFIED 2026-08-09; embedded in the
L2 Domain Pack v1 content) with EXACT normalized-value matching only:

- no substring matching, no string similarity, and no taxonomy-definition
  inference (contract Constraint 4 / Constraint 5.2);
- every outcome records the manifest id, rule version, rule id, reason code,
  and approval references (write-time provenance contract, D-L2-02);
- genres without an approved rule stay ``legacy_unclassified`` (the D-22
  sentinel); ``general_eap`` is never assigned from genre alone;
- reads never re-map: the mapping applies once at write time
  (D-L2-02); this module is the deterministic function that write-time
  application and the learner-model cluster key use.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.shared.task_type_registry import LEGACY_UNCLASSIFIED

_PACK_DIR = (
    Path(__file__).resolve().parents[1]
    / "configuration" / "domain_packs" / "l2" / "v1.0.0"
)


@dataclass(frozen=True)
class LegacyGenreMappingResult:
    """Deterministic D-22 mapping outcome for one legacy genre value."""

    genre: str
    normalized_value: str
    mapping: str
    rule_id: str
    reason_code: str | None
    manifest_id: str
    rule_version: str
    taxonomy_version: str
    approvals: tuple[str, ...]
    rationale: str


@lru_cache(maxsize=1)
def _load_manifest() -> dict[str, Any]:
    path = _PACK_DIR / "legacy_genre_mapping.json"
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def load_legacy_genre_manifest() -> dict[str, Any]:
    """Return the qualified D-22 mapping manifest (pack content)."""
    return _load_manifest()


def normalize_genre_value(genre: str | None) -> str:
    """Normalize a legacy genre value (manifest normalization discipline).

    NFC + casefold + strip + Unicode-whitespace collapse; EXACT normalized
    value match only (no punctuation stripping, no substring, no similarity).
    """
    if genre is None:
        return ""
    text = unicodedata.normalize("NFC", str(genre))
    text = text.casefold().strip()
    return re.sub(r"\s+", " ", text)


def map_legacy_genre(genre: str | None) -> LegacyGenreMappingResult:
    """Apply the approved manifest to one legacy genre value (explicit-only).

    Rule selection: empty/missing value -> M4 (missing_genre); exact
    normalized-value match -> the single approved rule (rules are disjoint by
    value; multiple matches would be a manifest validation error and are
    mapped defensively to ``legacy_unclassified`` with reason code
    ``mapping_rule_conflict``); no match -> M0 default
    (``legacy_unclassified`` / ``no_mapping_rule``). Never inferred.
    """
    manifest = _load_manifest()
    normalized = normalize_genre_value(genre)
    rules = {rule["rule_id"]: rule for rule in manifest["rules"]}

    if normalized == "":
        rule = rules["M4"]
    else:
        applicable = [
            rule for rule in manifest["rules"]
            if rule["normalized_value"] == normalized
        ]
        if len(applicable) == 1:
            rule = applicable[0]
        elif len(applicable) > 1:
            # Defensive: manifest validation guarantees disjoint values.
            rule = {
                "rule_id": "M0",
                "normalized_value": "*",
                "locale": None,
                "mapping": LEGACY_UNCLASSIFIED,
                "reason_code": "mapping_rule_conflict",
                "rationale": "Multiple approved rules matched the same value; "
                             "manifest validation error. Sentinel, never guessed.",
                "evidence": [],
            }
        else:
            rule = rules["M0"]

    approvals = tuple(
        approval["decision_id"] for approval in manifest["approvals"]
    )
    return LegacyGenreMappingResult(
        genre="" if genre is None else str(genre),
        normalized_value=normalized,
        mapping=rule["mapping"],
        rule_id=rule["rule_id"],
        reason_code=rule.get("reason_code"),
        manifest_id=manifest["manifest_id"],
        rule_version=manifest["rule_version"],
        taxonomy_version=manifest["taxonomy_version"],
        approvals=approvals,
        rationale=rule["rationale"],
    )
