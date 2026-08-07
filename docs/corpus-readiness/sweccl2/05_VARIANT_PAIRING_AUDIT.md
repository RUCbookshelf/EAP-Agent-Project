# 05 — Variant Pairing Audit

Data: `data/variant_pairing.csv`, `data/legacy_annotation_quality.json`.

## Pairing summary

| Check | Result |
| --- | --- |
| Logical documents | 4,950 |
| RAW present | 4,950 |
| LEMMA present | 4,950 |
| TAGGED present | 4,950 |
| Missing variants | 0 |
| Usable RAW / LEMMA / TAGGED | 4,949 / 4,949 / 4,950 |
| Header identical across variants | 4,950/4,950 |
| TAGGED tag-format validity | 100% (0 documents with malformed tokens) |
| LEMMA TreeTagger tab artifacts | 2 files (WARG2730, WARG4140) |
| Token ratio tagged/raw | median 1.142, range 1.000-1.332 (expected expansion from punctuation/contraction splitting); 0 outliers beyond [0.7, 1.6] |

## Findings

- WARG2081: RAW and LEMMA are all-NUL (2,157/2,150 bytes); TAGGED is intact.
  Document-level metadata recovered from TAGGED. RAW/LEMMA flagged as corrupt
  variants (candidate exclusions for those variants only).
- WARG3437: LEMMA byte-identical to RAW (1,391 bytes) - lemmatization produced
  no change for this text (base-form-only learner language); recorded, not
  treated as corruption.
- LEMMA artifacts: two files contain TreeTagger `word TAB tag TAB lemma` rows
  for Chinese characters embedded in the essay; historical annotation
  artifact, flagged for review.

## Status of legacy annotation

CLAWS4 (TAGGED) and TreeTagger (LEMMA) outputs are treated as HISTORICAL
annotation: machine-readable and consistent (100% format validity), but not
automatically canonical for future NLP. The future feature contract must
decide CLAWS4-tag mapping or re-tagging (spaCy) with a single versioned
representation (feature contract + CALF resource requirements per the frozen
architecture).
