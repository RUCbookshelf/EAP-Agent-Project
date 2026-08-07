"""WU2/WU5 — FeatureSetVersion contract and deterministic extraction.

One implementation serves corpus texts and future Student-compatible texts.
All features are deterministic local computations. No inference fields.

FeatureSetVersion v0.1.0 features:
  text_length_tokens
  sentence_length_mean
  t_unit_proxy
  pos_share_* (noun/verb/adjective/adverb/pronoun/determiner/
               preposition/conjunction/numeral/other)
  connective_density
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from app.corpus.errors import CorpusIntelligenceError

FEATURE_SET_VERSION = "corpus-features-v0.1.0"
SPACY_MODEL = "en_core_web_sm"
SPACY_MODEL_VERSION = "3.8.0"
CONNECTIVES_RESOURCE = Path(r"A:\EAP Agent Project\writing-feedback-mvp\app\analysis\resources\connectives_v0_6_1.json")

POS_MACRO = {
    "NOUN": "noun",
    "PROPN": "noun",
    "VERB": "verb",
    "AUX": "verb",
    "ADJ": "adjective",
    "ADV": "adverb",
    "PRON": "pronoun",
    "DET": "determiner",
    "ADP": "preposition",
    "CCONJ": "conjunction",
    "SCONJ": "conjunction",
    "NUM": "numeral",
}
POS_ORDER = [
    "noun", "verb", "adjective", "adverb", "pronoun", "determiner",
    "preposition", "conjunction", "numeral", "other",
]
FINITE_TAGS = {"VBD", "VBZ", "VBP"}
FINITE_DEPS = {"ROOT", "ccomp", "advcl", "relcl"}


@dataclass(frozen=True)
class FeatureDefinition:
    feature_id: str
    feature_version: str
    input_variant: str
    unit: str
    algorithm: str
    tokenization_assumptions: str
    normalization: str
    minimum_evidence: str
    missing_behavior: str
    length_sensitivity: str
    known_limitations: str
    output_type: str


@dataclass(frozen=True)
class FeatureSnapshot:
    feature_set_version: str
    feature_id: str
    value: float | int | None
    unit: str
    analysis_status: str
    evidence_count: int
    limitations: tuple[str, ...]


def _load_connectives() -> tuple[dict, str]:
    raw = CONNECTIVES_RESOURCE.read_bytes()
    resource_hash = hashlib.sha256(raw).hexdigest()
    return json.loads(raw.decode("utf-8")), resource_hash


_NLP = None


def _get_nlp():
    global _NLP
    if _NLP is None:
        try:
            import spacy
        except ImportError as exc:
            raise CorpusIntelligenceError(
                f"spaCy unavailable; FeatureSetVersion {FEATURE_SET_VERSION} requires spaCy {SPACY_MODEL}"
            ) from exc
        _NLP = spacy.load(SPACY_MODEL)
    return _NLP


def _match_connectives(text: str) -> int:
    resource, _ = _load_connectives()
    lowered = text.lower()
    forms = sorted({form for lst in resource["items"].values() for form in lst}, key=len, reverse=True)
    matches: list[tuple[int, int]] = []
    for form in forms:
        for m in re.finditer(rf"\b{re.escape(form)}\b", lowered):
            matches.append((m.start(), m.end()))
    matches.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    deduped: list[tuple[int, int]] = []
    occupied: list[tuple[int, int]] = []
    for start, end in matches:
        if any(start >= s and end <= e for s, e in occupied):
            continue
        occupied.append((start, end))
        deduped.append((start, end))
    return len(deduped)


def _extract_from_doc(doc, text: str) -> list[FeatureSnapshot]:
    tokens = [t for t in doc if not t.is_space]
    total = len(tokens)
    sentences = list(doc.sents)
    sentence_lengths = [len([t for t in s if not t.is_space]) for s in sentences]
    finite = [t for t in tokens if t.dep_ in FINITE_DEPS and t.tag_ in FINITE_TAGS]
    pos_counts = {cat: 0 for cat in POS_ORDER}
    for token in tokens:
        pos_counts[POS_MACRO.get(token.pos_, "other")] += 1
    conn_count = _match_connectives(text)

    out: list[FeatureSnapshot] = []

    out.append(FeatureSnapshot(
        FEATURE_SET_VERSION, "text_length_tokens", total, "tokens", "available", total,
        ("tokenization uses pinned spaCy model; differs from whitespace counts",),
    ))

    if sentences:
        out.append(FeatureSnapshot(
            FEATURE_SET_VERSION, "sentence_length_mean",
            round(sum(sentence_lengths) / len(sentence_lengths), 4),
            "tokens_per_sentence", "available", len(sentences),
            ("sentence segmentation from pinned spaCy senter; learner punctuation errors affect boundaries",),
        ))
    else:
        out.append(FeatureSnapshot(
            FEATURE_SET_VERSION, "sentence_length_mean", None, "tokens_per_sentence",
            "unavailable", 0, ("no sentence boundaries detected",),
        ))

    if finite:
        out.append(FeatureSnapshot(
            FEATURE_SET_VERSION, "t_unit_proxy", round(total / len(finite), 4),
            "tokens_per_finite_clause", "available", len(finite),
            (
                "proxy only: finite clause heads = ROOT/ccomp/advcl/relcl with VBD/VBZ/VBP tags;",
                "coordination and fragments are not modeled; not a validated T-unit",
            ),
        ))
    else:
        out.append(FeatureSnapshot(
            FEATURE_SET_VERSION, "t_unit_proxy", None, "tokens_per_finite_clause",
            "unavailable", 0, ("no finite clause head detected (learner fragments)",),
        ))

    if total:
        for cat in POS_ORDER:
            out.append(FeatureSnapshot(
                FEATURE_SET_VERSION, f"pos_share_{cat}", round(pos_counts[cat] / total, 6),
                "proportion", "available", total,
                ("POS from pinned spaCy model; learner non-standard forms may receive fallback tags",),
            ))
    else:
        for cat in POS_ORDER:
            out.append(FeatureSnapshot(
                FEATURE_SET_VERSION, f"pos_share_{cat}", None, "proportion",
                "unavailable", 0, ("no tokens",),
            ))

    if total:
        out.append(FeatureSnapshot(
            FEATURE_SET_VERSION, "connective_density", round(conn_count / total * 1000.0, 4),
            "per_1000_tokens", "available", conn_count,
            (
                "dictionary connectives-v0.6.1;",
                "dictionary coverage is incomplete; undetected forms do not prove absence of cohesion",
            ),
        ))
    else:
        out.append(FeatureSnapshot(
            FEATURE_SET_VERSION, "connective_density", None, "per_1000_tokens",
            "unavailable", 0, ("no tokens",),
        ))
    return out


ALL_FEATURE_IDS = [
    "text_length_tokens",
    "sentence_length_mean",
    "t_unit_proxy",
    "connective_density",
] + [f"pos_share_{cat}" for cat in POS_ORDER]


def _select(snapshots: list[FeatureSnapshot], feature_ids: list[str]) -> list[FeatureSnapshot]:
    by_id = {s.feature_id: s for s in snapshots}
    missing = [f for f in feature_ids if f not in by_id]
    if missing:
        raise CorpusIntelligenceError(f"extraction did not produce requested feature(s): {missing}")
    return [by_id[f] for f in feature_ids]


def extract_features(text: str, feature_ids: list[str] | None = None) -> list[FeatureSnapshot]:
    """Extract all (or selected) v0.1 features from one text (single parse)."""
    selected = feature_ids or ALL_FEATURE_IDS
    unknown = [f for f in selected if f not in ALL_FEATURE_IDS]
    if unknown:
        raise CorpusIntelligenceError(f"unknown feature_id(s): {unknown}")
    doc = _get_nlp()(text)
    return _select(_extract_from_doc(doc, text), selected)


def extract_features_batch(texts: list[str], feature_ids: list[str] | None = None) -> list[list[FeatureSnapshot]]:
    """Same contract as extract_features, batched via nlp.pipe (deterministic)."""
    selected = feature_ids or ALL_FEATURE_IDS
    unknown = [f for f in selected if f not in ALL_FEATURE_IDS]
    if unknown:
        raise CorpusIntelligenceError(f"unknown feature_id(s): {unknown}")
    nlp = _get_nlp()
    return [
        _select(_extract_from_doc(doc, text), selected)
        for doc, text in zip(nlp.pipe(texts, batch_size=32), texts)
    ]


FEATURE_DEFINITIONS: dict[str, FeatureDefinition] = {}


def _register_definitions() -> None:
    FEATURE_DEFINITIONS["text_length_tokens"] = FeatureDefinition(
        "text_length_tokens", "v0.1.0", "raw", "tokens",
        "pinned spaCy tokenization; space tokens excluded",
        "pinned spaCy en_core_web_sm 3.8.0 tokenizer",
        "none beyond tokenizer; corpus header line removed by corpus adapter before extraction",
        "min 1 token", "value 0 for empty text; analysis_status available with 0",
        "length feature itself", "differs from whitespace counts", "int",
    )
    FEATURE_DEFINITIONS["sentence_length_mean"] = FeatureDefinition(
        "sentence_length_mean", "v0.1.0", "raw", "tokens_per_sentence",
        "mean tokens per sentence; boundaries from pinned spaCy senter",
        "spaCy senter boundaries",
        "space tokens excluded from sentence token counts",
        "min 1 sentence", "unavailable when no sentence boundaries",
        "moderate; outliers dominate mean (median via distribution artifacts)",
        "learner punctuation errors affect segmentation", "float",
    )
    FEATURE_DEFINITIONS["t_unit_proxy"] = FeatureDefinition(
        "t_unit_proxy", "v0.1.0", "raw", "tokens_per_finite_clause",
        "tokens / finite clause heads (ROOT/ccomp/advcl/relcl with VBD/VBZ/VBP)",
        "pinned spaCy parser tags",
        "none",
        "min 1 finite clause", "unavailable when no finite clause detected",
        "moderate",
        "proxy only; coordination/fragments not modeled; not a validated T-unit", "float",
    )
    FEATURE_DEFINITIONS["connective_density"] = FeatureDefinition(
        "connective_density", "v0.1.0", "raw", "per_1000_tokens",
        "connective matches per 1000 non-space tokens; longest-first word-boundary match on lowercased text",
        "dictionary connectives_v0_6_1 (resource version + hash recorded)",
        "lowercase matching; forms sorted longest-first; nested overlaps deduped",
        "min 1 token", "unavailable when no tokens",
        "moderate; rate normalized by length",
        "dictionary coverage incomplete", "float",
    )
    for cat in POS_ORDER:
        FEATURE_DEFINITIONS[f"pos_share_{cat}"] = FeatureDefinition(
            f"pos_share_{cat}", "v0.1.0", "raw", "proportion",
            f"count of spaCy POS in macro-category {cat} / non-space tokens",
            "pinned spaCy POS tags",
            "SPACE excluded; macro mapping documented in POS_MACRO",
            "min 1 token", "unavailable when no tokens",
            "low; proportions robust to length",
            "learner non-standard forms may receive fallback tags", "float",
        )


_register_definitions()