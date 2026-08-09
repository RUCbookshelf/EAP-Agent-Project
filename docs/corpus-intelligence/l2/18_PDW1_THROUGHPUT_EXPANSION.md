# 18 — PDW1 CORPUS Throughput Expansion (SECCL20 spoken layer)

**Goal:** `PDW1-CORPUS-THROUGHPUT-EXPANSION` (re-dispatch)
**Owner:** CORPUS
**Worktree:** `A:\EAP Agent Project\worktrees\corpus` (branch `dept/corpus`)
**Baseline:** `b6fce9a500502c6929fe0a0e8da4748348967426` (promoted master)
**Date:** 2026-08-10
**Status:** DEPARTMENT GREEN — real measured throughput delivered; no promotion

---

## 1. Purpose

Deliver real, measured corpus throughput over the eligible unprocessed
material of the raw SWECCL 2.0 source, using deterministic, resumable,
idempotent CORPUS-owned tooling, and governed non-reconstructive aggregate
artifacts with `research_only` exposure. This is not a contract-only Goal.

## 2. Inventory (measured from disk, 2026-08-10)

| Component | Total | Already processed | Eligible unprocessed | Blocked | Excluded |
| --- | --- | --- | --- | --- | --- |
| WECCL20 written RAW | 4,950 logical texts | 4,950 (69,300 snapshot rows; 2 docs unavailable) | 0 | 0 | 1 corrupt RAW (WARG2081, all-NUL) |
| SECCL20 spoken transcripts | 2,852 files | **0** | **2,852** | 0 | 0 |
| TEM8 component | documented 916 files | 0 | 0 | 916 (absent from this physical copy) | 0 |
| WECCL20 LEMMA/TAGGED | 4,949/4,950 | 0 | 0 | 0 | 9,899 (historical-only; no v0.1 feature consumes them) |

Eligibility rule applied to SECCL20: manifest-backed row
(`seccl_manifest.csv`, 2,852 rows, all `metadata_status=parsed`) AND
prepared UTF-8 file present AND decodes as UTF-8 AND not all-NUL.
Measured result: 2,852 eligible, 0 blocked, 0 excluded.

## 3. Throughput execution

New deterministic tooling (TDD, 29 unit tests + 7 artifact tests):

- `app/corpus/seccl.py` — SECCL20 manifest adapter, header normalization
  (`<SPOKEN>` header + standalone `TASK n` markers removed before the frozen
  v0.1 feature contract applies), eligibility classification, reference-group
  index (min-N = 30), deterministic resumable batch plan with disjoint
  partition assignment.
- `scripts/corpus_intelligence/build_seccl.py` — batch runner with run
  ledger (outside git), per-document numeric snapshots (outside git), safe
  partition fan-out (`--partition i/n`, disjoint per-partition CSV) plus a
  parent-integrated `--merge`, and governed aggregate generation.

Execution (three runs; third reproduced byte-identical aggregates):

| Run | Result |
| --- | --- |
| 1 (full) | eligible 2,852; already processed 0; newly processed 2,852; failed 0; excluded 0; blocked 0 |
| 2 (resume) | already processed 2,852; pending 0; no re-extraction, no duplicate rows |
| 3 (determinism) | distributions JSONL SHA-256 `4B1B958C...2094` identical to run 1/2 output |

Snapshot file (outside git): `PREPARED/corpus-intelligence/seccl_feature_snapshots.csv`
— 39,928 rows = 2,852 documents x 14 features, all `analysis_status=available`,
token lengths 114–2,296 per transcript.
Run ledger (outside git): `PREPARED/corpus-intelligence/seccl_run_ledger.jsonl`
— 2,852 processed entries with per-file SHA-256 for resumability.

Partition fan-out smoke (isolated temp fixture, 8 docs): partitions 0/2 and
1/2 each processed 4 disjoint documents (56 rows each); parent `--merge`
integrated 112 rows with zero overlap. Verified by test
`test_partitions_are_disjoint_and_exhaustive` over the real 2,852-row
manifest (4-way partition union = 2,852 unique keys).

## 4. Governed aggregates (non-reconstructive, research_only)

Output directory: `docs/corpus-intelligence/l2/data/seccl/`

| Artifact | Content | Provenance |
| --- | --- | --- |
| `seccl_package_descriptor.json` | package `sweccl2-seccl20-v0.1.0`, manifest hash, row count, exposure | SECCL manifest SHA-256 `d4258448...` |
| `seccl_feature_set_version.json` | frozen feature contract `corpus-features-v0.1.0`, 14 features | same contract as WECCL20 |
| `seccl_reference_group_version.json` | 21 approved groups, min-N 30, duplicate policy | `seccl-reference-groups-v0.1.0` |
| `seccl_distribution_version.json` | algorithm/statistics/quantile method | `seccl-reference-distributions-v0.1.0` |
| `seccl_reference_group_membership.csv` | 10,695 memberships (21 groups) | document-id only |
| `seccl_reference_distributions.jsonl` | 294 records (21 groups x 14 features), all available | per-record 7-field provenance |
| `seccl_artifact_register.json` | class register (all NON-RECONSTRUCTIVE AGGREGATE, PERMITTED) | binding matrix UD-04 |

Reference groups (dimensions: exam, task_folder, year_folder, grade,
task_folder x year_folder). Effective samples apply the documented duplicate
policy `effective_sample_excludes_merged_task123_members`: TASK123 files are
merged reproductions of the same speakers' TASK1/TASK2/TASK3 transcripts;
they are processed into snapshots (713 docs included in throughput) but
excluded from every reference-group effective sample, mirroring the WECCL20
duplicate policy. Group sizes (effective): exam 2,139; each task 713;
each year 483–558; each task x year 161–186; grade 2,139 — all at or above
min-N 30.

Every distribution record and the package descriptor carry
`learner_exposure="research_only"` and `exposure_class="research_only"`.

## 5. Hygiene verification

| Check | Result |
| --- | --- |
| Raw SWECCL path/handle scan of repo artifacts (`A:\`, `PREPARED/`, `SECCL20/TEXTS`) | CLEAN (0 hits) |
| Raw transcript text scan (sample wording, `<SPOKEN>`, `TASK n`) | CLEAN |
| Banned vocabulary (proficiency/mastery/CEFR/ability/level/score/learning gain, word-boundary) | CLEAN |
| Exposure fields on all 294 distribution records + descriptor | PASS |
| Raw tree mutation | NONE (read-only; snapshots/ledger written only under PREPARED outside git) |
| Frozen WECCL20 artifacts (1,050 distributions, membership, versions) | UNTOUCHED (byte-identical; this Goal adds a sibling SECCL artifact set) |
| Learner-facing exposure | NONE (research_only default; no display path) |

## 6. Coverage and remaining scope

- SECCL20 coverage: 2,852/2,852 = 100% of manifest rows processed.
- Remaining unprocessed scope: TEM8 (916 documented files absent from this
  physical copy — blocked until the component is located); WECCL20
  LEMMA/TAGGED variants (historical annotations; no v0.1 feature consumes
  them); SECCL audio (2,139 mp3 — outside the text-feature contract);
  WARG2081 corrupt RAW (excluded, recorded in WECCL20 snapshot as
  unavailable).
- No proficiency/mastery/ability/learning-gain interpretation of any
  distribution; all values are observed descriptive statistics of the
  spoken transcripts under the frozen feature contract (D-07 semantics).

## 7. Boundary compliance

- No raw text, excerpt, paraphrase, or reconstructive derivative persisted
  anywhere in the repository; numeric snapshots stay outside git.
- No D3/D8/D12 widening: no learner-facing exposure, no display class, no
  UI surface; `research_only` default throughout.
- No generic retrieval, Skills/MCP, or cross-department raw access; SECCL
  aggregates are CORPUS-owned governed artifacts with full provenance.
- No reset/clean/rebase/push/PR/promotion; local candidate commit only.
