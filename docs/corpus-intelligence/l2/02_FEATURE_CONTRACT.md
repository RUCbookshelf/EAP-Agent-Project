# 02 — Feature Contract

## FeatureSetVersion

`corpus-features-v0.1.0` - frozen. Definitions registry:
`app/corpus/features.py::FEATURE_DEFINITIONS`; machine artifact:
`data/feature_set_version.json`.

## Implemented features (14)

| feature_id | unit | algorithm summary |
| --- | --- | --- |
| text_length_tokens | tokens | pinned spaCy tokenization, spaces excluded |
| sentence_length_mean | tokens_per_sentence | mean tokens per spaCy sentence |
| t_unit_proxy | tokens_per_finite_clause | tokens / finite clause heads (ROOT/ccomp/advcl/relcl with VBD/VBZ/VBP) |
| connective_density | per_1000_tokens | connectives_v0_6_1 dictionary, longest-first word-boundary match, rate per 1000 tokens |
| pos_share_noun | proportion | spaCy POS macro categories / non-space tokens |
| pos_share_verb | proportion | verb incl. auxiliary |
| pos_share_adjective | proportion | adjective |
| pos_share_adverb | proportion | adverb |
| pos_share_pronoun | proportion | pronoun |
| pos_share_determiner | proportion | determiner |
| pos_share_preposition | proportion | adposition |
| pos_share_conjunction | proportion | coordinating + subordinating |
| pos_share_numeral | proportion | numeral |
| pos_share_other | proportion | intj/part/x/sym/punct |

Every feature definition records: feature_version, input_variant (raw),
unit, algorithm, tokenization assumptions, normalization, minimum evidence,
missing/unavailable behavior, length sensitivity, known limitations, and
output type.

## Shared contract guarantees

- Corpus texts and future Student texts are processed by the SAME
  implementation (`extract_features` / `extract_features_batch`).
- Corpus batch adapter strips the documented corpus header line
  (`<STU..>...`) before extraction; Student input must not contain the corpus
  header format. The extractor itself treats input as plain text.
- Missing spaCy model fails loudly (CorpusIntelligenceError); no silent
  fallback to another tokenizer.
- Determinism: pinned spaCy 3.8.14 + en_core_web_sm 3.8.0; repeated runs
  produce identical snapshots.

## CLAWS4 decision

Decision: HYBRID-NONE-FOR-V0.1. The historical CLAWS4 TAGGED variant remains
available as HISTORICAL annotation. v0.1 features use pinned spaCy on RAW for
POS distribution and sentence segmentation, so corpus and Student sides
inhabit the same feature space by construction. No CLAWS4 tag is compared
against a spaCy tag without an explicit mapping contract; such a mapping is
deferred (documented in 10).

Rationale: comparability (single taxonomy both sides), reproducibility
(pinned model), student-side applicability (same model), licensing (local),
no annotation drift within a version.

## Deferred features

- Lexical diversity (normalized TTR variants) - deferred to v0.2.
- Phraseology/n-grams, subordination patterns, stance signals - deferred.
- Lexical frequency/sophistication - blocked (D11 authorization missing).
- Lexical cohesion/discourse organization - requires D-L2-03 feasibility.
