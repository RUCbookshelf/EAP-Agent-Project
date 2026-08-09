"""No-normative-claims scanning (WU-D F7/F11; N7 banned vocabulary).

Deterministic, local scanner (no LLM; consistent with WU-D I5) that flags
prohibited normative vocabulary in strings that would otherwise be eligible
for persisted records or learner-facing output: proficiency/mastery/ability/
learning-gain/CEFR labels, risky ability phrases, and contextual Chinese
development claims.

Documentation exemption (WU-D F1-resolution convention): text that states the
prohibition itself (markers such as "does not establish", "must not",
"prohibited", "never", "not permitted", "banned", "out of scope", and their
Chinese equivalents) may be scanned with ``documentation=True`` and is
exempted line by line. Production artifact strings are scanned with the
strict default (``documentation=False``).

The banned set reuses the frozen shared vocabulary
(app.shared.vocabularies.BANNED_LEARNER_LABELS) and the product's frozen
risky-ability phrase list (app.feedback.reliability.DEFAULT_RISKY_ABILITY_
PHRASES) so the scanner cannot drift from existing claim-policy machinery.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from app.feedback.reliability import DEFAULT_RISKY_ABILITY_PHRASES
from app.shared.vocabularies import BANNED_LEARNER_LABELS


# Word-level banned terms (matched as case-insensitive substrings).
BANNED_NORMATIVE_TERMS: frozenset[str] = frozenset(
    {
        *BANNED_LEARNER_LABELS,
        "learning gain",
        "learning-gain",
        "cefr",
        "native-like",
        "native-like control",
        "advanced proficiency",
        "superior writing ability",
        "superior ability",
        "high-level writer",
        "sophisticated writer",
        "strong linguistic control",
        "high rhetorical awareness",
        "excellent command of english",
        "good writer",
        "weak writer",
        "strong writer",
        "advanced level",
        "proficient writer",
        "mastered",
    }
)

# Phrase-level risky ability wording, frozen in the product's reliability
# machinery (ConfigurationPayload.positive_finding_risky_ability_phrases).
RISKY_ABILITY_PHRASES: frozenset[str] = frozenset(
    phrase.casefold() for phrase in DEFAULT_RISKY_ABILITY_PHRASES
)

# Contextual Chinese development-claim patterns (mirrors the wording checks
# in app.feedback.validation and app.feedback.reliability).
ZH_NORMATIVE_PATTERNS: tuple[str, ...] = (
    r"能力(?:已经)?(?:提升|下降|提高|进步|退步)",
    r"已经(?:掌握|退步|提高|进步|提升)",
    r"(?:表现|水平)(?:明显|已经)?(?:提高|下降|进步|退步|提升)",
    r"(?:母语|熟练)(?:水平|程度)",
)

# Lines containing these markers state the prohibition itself and are exempt
# in documentation mode only (WU-D F1-resolution convention).
PROHIBITION_CONTEXT_MARKERS: tuple[str, ...] = (
    "does not establish",
    "does not prove",
    "does not count",
    "do not establish",
    "must not",
    "not permitted",
    "not authorized",
    "not a claim",
    "never",
    "prohibited",
    "forbidden",
    "banned",
    "out of scope",
    "not in scope",
    "no ",
    "not ",
    "is not",
    "are not",
    "cannot",
    "not proof",
    "禁止",
    "不得",
    "不代表",
    "并不",
    "不能",
    "不允许",
    "并非",
)


@dataclass(frozen=True)
class NormativeViolation:
    """One banned normative term found in a scanned string."""

    term: str
    location: str
    snippet: str
    rule: str = "WU-D F7/F11; N7 banned vocabulary"


def _is_prohibition_context(line: str) -> bool:
    lowered = line.casefold()
    return any(marker in lowered for marker in PROHIBITION_CONTEXT_MARKERS)


class NormativeClaimsScanner:
    """Deterministic scanner for normative-claim vocabulary."""

    def scan_text(
        self, text: str, *, documentation: bool = False, location: str = "<text>",
    ) -> list[NormativeViolation]:
        """Scan one string; returns every violation found."""

        findings: list[NormativeViolation] = []
        lines = text.splitlines() or [text]
        for line in lines:
            if documentation and _is_prohibition_context(line):
                continue
            lowered = line.casefold()
            for term in BANNED_NORMATIVE_TERMS:
                if term.casefold() in lowered:
                    findings.append(
                        NormativeViolation(
                            term=term, location=location, snippet=line.strip()[:160],
                        )
                    )
            for pattern in ZH_NORMATIVE_PATTERNS:
                match = re.search(pattern, line)
                if match:
                    findings.append(
                        NormativeViolation(
                            term=match.group(0), location=location,
                            snippet=line.strip()[:160],
                        )
                    )
        return findings

    def scan_mapping(
        self, mapping: Any, *, documentation: bool = False, prefix: str = "",
    ) -> list[NormativeViolation]:
        """Recursively scan a dict/list/str tree (pydantic dumps included)."""

        findings: list[NormativeViolation] = []
        if isinstance(mapping, str):
            location = prefix or "<value>"
            findings.extend(self.scan_text(mapping, documentation=documentation, location=location))
            return findings
        if isinstance(mapping, Mapping):
            for key, value in mapping.items():
                child = f"{prefix}.{key}" if prefix else str(key)
                findings.extend(self.scan_mapping(value, documentation=documentation, prefix=child))
            return findings
        if isinstance(mapping, (list, tuple)):
            for index, value in enumerate(mapping):
                child = f"{prefix}[{index}]"
                findings.extend(self.scan_mapping(value, documentation=documentation, prefix=child))
        return findings

    def scan_pydantic(
        self, obj: Any, *, documentation: bool = False,
    ) -> list[NormativeViolation]:
        """Scan a pydantic model's string fields (python-mode dump)."""

        if hasattr(obj, "model_dump"):
            payload = obj.model_dump(mode="python")
            return self.scan_mapping(payload, documentation=documentation)
        return self.scan_mapping(obj, documentation=documentation)


__all__ = [
    "BANNED_NORMATIVE_TERMS",
    "NormativeClaimsScanner",
    "NormativeViolation",
    "PROHIBITION_CONTEXT_MARKERS",
    "RISKY_ABILITY_PHRASES",
    "ZH_NORMATIVE_PATTERNS",
]
