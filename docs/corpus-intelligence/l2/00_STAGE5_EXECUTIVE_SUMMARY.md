# 00 — Stage 5 Executive Summary

Status: STAGE 5 IMPLEMENTED — pending independent review.
Date: 2026-08-07

## What Stage 5 delivers

A versioned, deterministic, auditable Corpus Intelligence foundation over the
prepared WECCL 2.0 package (`sweccl2-weccl20-v0.1.0`, manifest hash
`0d8940ff84613807c11c0e492c61fb8d39fc1152a386061f9711a41487659eb9`):

- Corpus resource registration with verified manifest hash.
- FeatureSetVersion `corpus-features-v0.1.0` (14 features, one implementation
  for corpus and Student-compatible text).
- ReferenceGroupVersion `reference-groups-v0.1.0` (75 approved groups,
  explicit min-N=30 policy, deterministic fallback hierarchy, duplicate
  policy applied).
- Corpus batch extraction: 4,949 usable RAW texts -> 69,300 feature snapshot rows (4,950 documents x 14 features, including 14 unavailable rows for the corrupt WARG2081)
  rows (WARG2081 honestly unavailable; no variant substitution).
- Reference distributions: 1,050 records (75 groups x 14 features), all
  available, versioned with full provenance.
- Read-only Corpus Intelligence query boundary (app/corpus/intelligence.py)
  consumable by Stage 6 without inspecting corpus files or preparation CSVs.

## Key decisions

- CLAWS4 decision: historical CLAWS4 TAGGED remains historical annotation;
  v0.1 features use pinned spaCy en_core_web_sm 3.8.0 on RAW for POS and
  segmentation so corpus and Student sides share one feature space. No
  CLAWS4<->spaCy comparison without an explicit mapping contract.
- Duplicate policy: effective reference samples exclude non-canonical
  duplicate members (canonical = lexicographically smallest document_id);
  physical counts and raw records untouched.
- Score linkage: 270 expository scores link deterministically to EXP01
  documents by ID (270/270, no missing, no ambiguity).
- Evaluation protection: the 270 scored expository texts remain one protected
  block; duplicate-group members never split across dev/eval; no final
  partitions created.

## Boundaries respected

- No diagnostic interpretation, no student comparison, no feedback, no
  learner-facing exposure (all results learner_exposure=research_only).
- No prohibited proficiency/mastery/learning-gain fields.
- No migrations, no shared-contract changes, no production behavior changes.
- Raw corpus and prepared texts untouched; no raw text in git.

## Verification

- Focused tests: 36/36 passed (resource, features, groups, intelligence).
- Query boundary smoke tests passed (exact group, fallback, unavailable
  states, unknown feature).
- See 09 for the full verification matrix.
