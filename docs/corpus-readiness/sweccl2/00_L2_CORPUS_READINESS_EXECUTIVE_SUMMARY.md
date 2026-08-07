# 00 — L2 Corpus Readiness Executive Summary

Status: DEPARTMENT-LEVEL CORPUS PREPARATION COMPLETE (independent review: READY_WITH_DOCUMENTED_LIMITATIONS).
Package id: `sweccl2-weccl20-v0.1.0`
Date: 2026-08-07

## What was prepared

The physical SWECCL 2.0 collection at `A:\[Linguistics Data] Corpus\SWECCL 2.0`
was transformed from an undocumented file collection into a reproducible,
immutable, auditable, machine-readable L2 corpus package focused on the
WECCL 2.0 written corpus (primary product target: L2 writing development).

## Headline results

- Physical corpus located and read reliably: 19,858 source files, 1.88 GB.
- WECCL 2.0: 4,950 logical texts in three variants (RAW, LEMMA, TAGGED).
- All documented metadata counts match the physical corpus exactly:
  genre 4,680 argumentative + 270 expository; major type 4,359 + 591;
  entry year 68/307/1,672/2,450/453; grade 1,549/2,172/1,108/121;
  timed 2,499 / untimed 2,451; 27 prompts (ARG01-ARG26, EXP01).
- Encoding: 17,703 text files decoded losslessly (round-trip verified);
  canonical UTF-8 derived layer created with full provenance.
- Metadata coverage: 100% for all six documented WECCL dimensions and the
  eight SECCL header tags.
- Variant audit: 4,950/4,950 documents have all three variants by name;
  one document (WARG2081) has corrupt RAW/LEMMA (all-NUL) with an intact
  TAGGED variant.
- Quality: 90 findings catalogued; 348 duplicate groups identified
  (240 unique documents touched); 2 candidate exclusions (corrupt variants).
- Reference groups: 42 conservative candidates (33 ready-for-validation,
  7 promising, 2 too sparse).
- Feature feasibility: 10 families assessed; 8 on the priority shortlist,
  2 require validation.
- Licensing: PARTIALLY_DOCUMENTED; external use REQUIRES_REVIEW.

## Package contents

- Reports: 00-12 in this directory.
- Machine-readable data: `data/` (inventory, manifests, coverage, pairing,
  quality, duplicates, composition, reference groups, features, holdouts).
- Version record: `corpus_version.json` (manifest hash
  `0d8940ff84613807c11c0e492c61fb8d39fc1152a386061f9711a41487659eb9`).
- Reproducible tooling: `scripts/corpus_readiness/` (10-step pipeline,
  scripts 01-10, plus tests).

## Key constraints respected

- Raw corpus untouched: no overwrite, rename, correction, or deletion.
- No raw texts in reports; no commits of raw corpus content or derived texts.
- Architecture invariants I1-I6 and naming contract respected in all artifacts.
- No production code, database migration, API, or UI changes.

## Next Goal starting point

`12_L2_CORPUS_IMPLEMENTATION_HANDOFF.md` is the authoritative handoff.
Recommended first Corpus Intelligence work units are listed there.
