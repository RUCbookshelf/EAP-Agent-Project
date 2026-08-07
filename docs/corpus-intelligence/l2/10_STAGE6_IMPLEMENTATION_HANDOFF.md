# 10 — Stage 6 Implementation Handoff

## Which Corpus Intelligence resource is registered

`sweccl2-weccl20-v0.1.0` via `app/corpus/resource.py`; descriptor fields in
`01_CORPUS_RESOURCE_REGISTRATION.md`; accessor `get_corpus_resource()`.

## Corpus/version/hash

SWECCL 2.0 / package sweccl2-weccl20-v0.1.0 / manifest hash
`0d8940ff84613807c11c0e492c61fb8d39fc1152a386061f9711a41487659eb9`.

## FeatureSetVersion and implemented features

`corpus-features-v0.1.0`, 14 features (see 02). All use RAW input via pinned
spaCy; extractor identical for corpus and Student-compatible text.

## How features are calculated

See `app/corpus/features.py` + 05. Batch corpus extraction:
`scripts/corpus_intelligence/build_stage5.py` (snapshots outside git under
`PREPARED/corpus-intelligence/`).

## Required input variants

RAW for all v0.1 features. TAGGED (CLAWS4) and LEMMA remain historical
artifacts; no v0.1 feature consumes them.

## POS/tagging decision

Historical CLAWS4 preserved; v0.1 uses spaCy en_core_web_sm 3.8.0 on both
sides. A CLAWS4<->spaCy mapping contract is deferred; do not compare them
without it.

## ReferenceGroupVersion and available groups

`reference-groups-v0.1.0`; 75 approved groups (see 04 and
`data/reference_group_membership.csv`).

## Unavailable groups

ARG13 / ARG19 standalone; any group with effective N < 30; unknown ids.

## Fallback hierarchy

prompt+timed -> prompt -> genre+timed -> genre -> UNAVAILABLE; disclosure
required in results.

## Duplicate policy

`effective_sample_excludes_non_canonical_duplicate_members` (canonical =
lexicographically smallest document_id); applied to memberships and
distributions; raw records untouched.

## Distributions and querying

`reference-distributions-v0.1.0`, 1,050 records in
`data/reference_distributions.jsonl`; query via
`app/corpus/intelligence.py::get_feature_distribution`.

## Failure/unavailable states

Explicit errors/availability for unknown corpus, wrong hash, unknown feature,
unknown/too-small group, missing distribution, corrupt resource; see 07.

## Student-compatible FeatureSnapshot

`extract_features(student_text)` returns the same FeatureSnapshot schema.
Stage 6 must compare only under the same FeatureSetVersion and the same
feature contract; fallback-analyzer comparisons are prohibited (I3).

## Protected evaluation data

270 scored expository texts (protected block; scores linked via exp.xls/exp.sav
by WEXP ID); duplicate-group members never split across dev/eval; no final
partitions.

## Remaining corpus limitations

TEM8 absent; WARG2081 RAW/LEMMA corrupt; 240 docs in duplicate groups;
ARG13/ARG19 sparse; license PARTIALLY_DOCUMENTED; no learner IDs; token
counts differ by counter; 2 LEMMA TreeTagger artifacts.

## What Stage 6 may build next (recommended first Work Units)

- WU-A: Student FeatureSnapshot harness on real (or synthetic) submissions
  using `extract_features`; version/eligibility checks.
- WU-B: reference-group matching (TaskSignature) with explicit unmatched
  states; same FeatureSetVersion enforcement.
- WU-C: comparison math (distance/percentile within group) as
  observed-descriptive evidence only (D-07); no normative labels.
- WU-D: diagnostic gating design (availability, min-N, fallback disclosure)
  with Feedback & Learner Intelligence.
- WU-E: expository-score-based evaluation design using the protected block.

Stage 6 must NOT: emit proficiency/mastery/learning-gain vocabulary, expose
learner-facing corpus content (D-08), or use LLM for corpus statistics (I5).
