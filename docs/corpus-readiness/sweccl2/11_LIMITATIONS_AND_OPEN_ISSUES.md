# 11 — Limitations and Open Issues

## Corpus-level limitations (physical facts)

- WARG2081 RAW/LEMMA corrupt (all-NUL); TAGGED intact.
- TEM8 component absent from this physical copy (manual documents 916 files).
- Manual PDF relocated out of the corpus root during preparation (hash
  preserved in the discovery snapshot; content preserved in the documentation
  report).
- 240 documents in duplicate groups - review required before any
  evaluation use.
- 2 LEMMA files with TreeTagger artifacts from Chinese characters.
- 74 WECCL files contain learner-typed non-ASCII content (preserved as-is).
- 12 SECCL transcript files (6 unique transcripts across TASK1/TASK123
  copies) contain Chinese transcriber annotations (annotator notes, not
  learner speech).
- Audio durations not independently verified (no audio decoder available in
  the environment); documented durations remain estimates.
- exp.sav/exp.xls present but not parsed (no XLS reader); scoring linkage to
  the 270 expository texts is expected per the manual and must be verified in
  the next Goal.

## Methodological limitations

- Token counts differ between tools; a single token counter must be frozen in
  the feature contract.
- Legacy CLAWS4/TreeTagger annotation is historical, not canonical.
- No learner IDs in WECCL; no within-learner longitudinal grouping possible
  from this corpus alone.
- All counts are physical-file facts; the manual's minutes/token estimates are
  documentation expectations.

## Open decisions (architecture-level, carried forward, not resolvable here)

- D1 corpus authorization; D3 licensing model; D4 band method/min-N; D8
  feature-set scope; D11 frequency-resource authorization; D12 UI exposure
  (architecture register).
- D-L2-03 discourse-organization feasibility; D-L2-04 corpus-profile contents.
- Final exclusion policy for duplicates/corrupt variants (Researcher).
- Final reference-group policy (Researcher).
- CLAWS4 tag mapping vs re-tagging (Corpus & NLP + Research Evaluation).

## License status

PARTIALLY_DOCUMENTED: the corpus ships as a published book (ISBN
978-7-5600-8015-4) with a copyright page but no explicit corpus-use license in
the manual. Local preparation, analysis, and descriptive reporting are
permitted; external distribution or learner-facing use REQUIRES_REVIEW.

## Non-blocking status

All limitations above are documented and do not block corpus preparation;
they are carried into the implementation handoff (AMBER-class findings).
