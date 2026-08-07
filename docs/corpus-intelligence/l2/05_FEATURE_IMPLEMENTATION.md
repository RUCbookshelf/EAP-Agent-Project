# 05 — Feature Implementation

## Module

`app/corpus/features.py` - single deterministic implementation:

- `extract_features(text, feature_ids=None)` - one text, one parse.
- `extract_features_batch(texts, feature_ids=None)` - nlp.pipe batching with
  the identical per-document computation.
- `FEATURE_DEFINITIONS` - versioned contract registry.
- FeatureSnapshot schema: feature_set_version, feature_id, value, unit,
  analysis_status, evidence_count, limitations.

## POS macro mapping

spaCy universal POS -> macro categories (POS_MACRO): noun (NOUN+PROPN),
verb (VERB+AUX), adjective, adverb, pronoun, determiner, preposition (ADP),
conjunction (CCONJ+SCONJ), numeral, other (INTJ/PART/X/SYM/PUNCT). SPACE
tokens excluded from the denominator.

## Connective resource

Reuses the product resource `app/analysis/resources/connectives_v0_6_1.json`
(version connectives-v0.6.1) with word-boundary, longest-first, lowercased
matching and nested-overlap deduplication. The product's own
`app/analysis/connective_features.py` is NOT modified.

## Per-feature validation coverage

Tests cover: normal text, short text, empty input, non-ASCII learner text,
malformed punctuation-only input, corrupt variant handling (WARG2081-style),
determinism/repeatability, batch-vs-single equivalence, POS shares summing to
1, unknown-feature rejection, definition completeness.

## Corpus-side honesty rules

- RAW-required features never silently substitute TAGGED/LEMMA content.
- WARG2081 (corrupt RAW/LEMMA): all 14 features unavailable with reason
  "corrupt or missing RAW variant".
- WARG0228: t_unit_proxy unavailable ("no finite clause head detected");
  other features available.
