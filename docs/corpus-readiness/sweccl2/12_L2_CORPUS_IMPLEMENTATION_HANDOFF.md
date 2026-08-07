# 12 — L2 Corpus Implementation Handoff

This document is the authoritative starting point for the next Corpus
Intelligence Goal. It answers every question the next Goal would otherwise
have to rediscover.

## What corpus is actually available

SWECCL 2.0 physical collection (written + spoken + tools), located at
`A:\[Linguistics Data] Corpus\SWECCL 2.0\`. The written WECCL 2.0 corpus is
the primary asset: 4,950 learner essays in three variants.

## Where it is

| Asset | Location |
| --- | --- |
| Raw corpus | `A:\[Linguistics Data] Corpus\SWECCL 2.0\WECCL20\{RAW,LEMMA,TAGGED}` |
| Spoken corpus | `A:\[Linguistics Data] Corpus\SWECCL 2.0\SECCL20\{AUDIO,TEXTS}` |
| Tools/scoring | `A:\[Linguistics Data] Corpus\SWECCL 2.0\TOOLS` (incl. exp.sav, exp.xls) |
| Derived UTF-8 layer | `A:\[Linguistics Data] Corpus\SWECCL 2.0\PREPARED\utf8\` |
| Readiness package | `docs/corpus-readiness/sweccl2/` (this directory) |
| Reproducible tooling | `scripts/corpus_readiness/` |

## Canonical inputs

- `data/physical_inventory.csv` - every source file with SHA-256 and encoding.
- `data/physical_inventory_discovery_snapshot.csv` - discovery-time snapshot
  (includes the manual PDF hash).
- `data/corpus_manifest.csv` - the canonical WECCL manifest (4,950 rows,
  parsed metadata, variant usability flags, provenance to inventory hashes).
- `data/derived_manifest.csv` - source-to-derived provenance for the UTF-8
  layer (17,703 files, round-trip verified).

## Which derived layer to use

Use `PREPARED\utf8\WECCL20\{RAW,LEMMA,TAGGED}` for all text processing.
It is byte-lossless relative to sources (encoding-only conversion, newlines
preserved) and fully reproducible (`python scripts/corpus_readiness/run_all.py`).
Never process the raw ANSI/GBK files directly for new feature work.

## Which metadata fields are reliable

- genre, prompt_id (ARG01-ARG26, EXP01), major_type, entry_year, grade,
  timed_status: 100% coverage, all counts match the manual - RELIABLE.
- document_id (WARG####/WEXP####): stable key - RELIABLE.
- SECCL header tags (8 tags) and folder structure: RELIABLE for the 2,852
  transcripts present.

## Which fields are unreliable / absent

- No learner IDs: same-learner linkage across documents is NOT possible from
  filenames (duplicate detection is the only proxy).
- No scores in WECCL headers; scores exist only for the 270 expository texts
  via TOOLS/exp.sav + exp.xls (linkage to verify).
- TEM8 metadata: absent (component missing from this copy).
- Manual token/minute figures: documentation expectations; do not treat as
  physical facts.

## Which reference groups are viable

See 08 and `data/reference_group_candidates.csv`: 33 groups ready for
validation, 7 promising, 2 too sparse (ARG13, ARG19). Viable dimensions:
same prompt, same genre, timed/untimed, grade, major type, entry year.
All groups must exclude/reconcile duplicate-group members and honor the
fallback hierarchy (same prompt, then same genre + condition, then broader
argumentative, then UNAVAILABLE).

## Which are not viable

- ARG13 (N=14) and ARG19 (N=18) as reference distributions.
- Any proficiency-like, mastery-like, or learning-gain interpretation of group
  differences (architecture I1 + D-07: observed descriptive evidence only).
- Cross-prompt normative claims without prompt control.
- Learner-facing group output without display policy (D-08/D-12).

## Which NLP features to implement first

Priority shortlist (see 09): text length, sentence length/T-unit proxies, POS
distribution (after CLAWS4 mapping decision), connectives; then lexical
diversity (normalized), phraseology, subordination patterns, stance signals.

## Which features need validation

- Lexical frequency/sophistication (blocked: no authorized frequency resource,
  D11 open).
- Lexical cohesion / discourse organization (D-L2-03 feasibility spike; no
  embeddings - D9 deferred).

## Which data must be protected for evaluation

- The 270 scored expository texts (one protected block).
- 240 duplicate-group members (never split across dev/eval).
- WARG2081 (tagged-only).
See 10 and `data/holdout_candidates.csv`.

## Licensing / privacy constraints

- License: PARTIALLY_DOCUMENTED (no explicit corpus-use license in the manual;
  external distribution or learner-facing use REQUIRES_REVIEW).
- Privacy: treat texts as sensitive research data; no external uploads; no
  PII propagation; 74 files contain learner-typed Chinese characters and 12
  transcript files contain transcriber notes (6 unique transcripts across
  task-folder copies) - handle as content, never publish raw text in reports.
- No raw corpus content in git; derived texts stay outside the repository.

## Quality exclusions recommended (candidate status)

- WECCL20/RAW/WARG2081.txt and WECCL20/LEMMA/WARG2081.txt (all-NUL).
- Duplicate-group members: resolve before evaluation use (240 documents).
No exclusions are applied silently; files remain in place.

## Corpus version / hash to reference

- Package: `sweccl2-weccl20-v0.1.0` (`corpus_version.json`).
- Manifest hash: `0d8940ff84613807c11c0e492c61fb8d39fc1152a386061f9711a41487659eb9`.
- Every future artifact must record this hash + preparation version.

## Unresolved questions

- TEM8 component location (documented 916 files not in this copy).
- Manual PDF new location (user-moved; hash in discovery snapshot).
- Expository score linkage (exp.sav/exp.xls to the 270 texts) - verify with a
  proper XLS reader in the next Goal.
- Duplicate policy and reference-group min-N (Researcher decisions).
- CLAWS4 tag mapping vs re-tagging (feature-contract decision).
- Audio-duration verification (no decoder available during preparation).

## First Corpus Intelligence Work Units (recommended)

- WU-A: register the corpus package (corpus_version.json + boundary contract
  implementation per D-24) with the hash above.
- WU-B: define the feature contract (token counter, CLAWS4 mapping or
  re-tagging, metric units) aligned with CALF resource_requirement (D-25).
- WU-C: validate expository scoring linkage and the 270-text protected block.
- WU-D: reconcile duplicate groups and finalize exclusion policy (with
  Research Evaluation).
- WU-E: reference-group validation on the 33 ready candidates (min-N and
  coverage rules as a Researcher decision).
- WU-F: implement the first deterministic feature set (READY tier) on both
  corpus and student sides under one FeatureSetVersion.

## Reproducibility

`python scripts/corpus_readiness/run_all.py` regenerates all machine-readable
artifacts; `pytest scripts/corpus_readiness/tests/` validates them
(8/8 passing).
