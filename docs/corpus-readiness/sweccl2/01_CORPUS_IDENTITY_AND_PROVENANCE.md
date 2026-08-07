# 01 — Corpus Identity and Provenance

## Identity record

| Field | Value |
| --- | --- |
| corpus_id | sweccl2.0 (source product); package `sweccl2-weccl20-v0.1.0` |
| corpus_name | 中国学生英语口笔语语料库 2.0 (SWECCL 2.0) |
| corpus_version | 2.0 (ISBN 978-7-5600-8015-4; FLTRP, 2008-12 first edition) |
| source_location | `A:\[Linguistics Data] Corpus\SWECCL 2.0\` |
| documentation_source | `A:\EAP Agent Project\SWECCL2.0_语料库概况报告.md` (manual-derived report; the 82-page scanned manual PDF was the original source) |
| physical_discovery_date | 2026-08-07 |
| physical_root | `A:\[Linguistics Data] Corpus\SWECCL 2.0\` |
| license_status | PARTIALLY_DOCUMENTED (published book with copyright page; no explicit corpus-use license in the manual; external use REQUIRES_REVIEW) |
| raw_immutable | true |
| preparation_pipeline_version | 0.1.0 |

## Physical components (discovery snapshot, 19,858 files)

| Component | Path | Files | Bytes |
| --- | --- | --- | --- |
| weccl_raw | WECCL20/RAW | 4,950 | 7,356,093 |
| weccl_lemma | WECCL20/LEMMA | 4,950 | 7,331,503 |
| weccl_tagged | WECCL20/TAGGED | 4,950 | 12,791,446 |
| seccl_audio | SECCL20/AUDIO | 2,139 | 1,801,346,957 |
| seccl_texts | SECCL20/TEXTS | 2,852 | 8,450,275 |
| tools | TOOLS | 13 | 35,624,177 |
| root_artifact | root | 4 | 20,646,463 |

Root artifacts at discovery: `autorun.inf`, `autorun.exe`, `fltrp.avi`, and the
manual PDF (15,126,818 bytes, sha256 `28dee8c39a46c6ca...`; full hash in
`data/physical_inventory_discovery_snapshot.csv`).

## Provenance events

- 2026-08-07 discovery: full inventory with SHA-256 captured for all 19,858
  files (`physical_inventory_discovery_snapshot.csv`).
- 2026-08-07 (during preparation): the manual PDF was observed missing from the
  physical root after discovery; its hash remains in the snapshot. The manual's
  content is preserved in the documentation report. No corpus data was affected.
- Derived layer created at `PREPARED/utf8/` with per-file provenance
  (`data/derived_manifest.csv`: source path, source hash, derived hash, encoding).
- Current-state inventory (`data/physical_inventory.csv`) reflects the root as
  of the final pipeline run.

## Duplicate-copy scan

A bounded scan under the workspace roots found no second copy of the corpus
(only the canonical physical root). No hash-level duplicate-copy ambiguity.

## Governance boundaries

- Raw files: read-only inputs.
- Derived artifacts: `PREPARED/` (outside git) + `docs/corpus-readiness/sweccl2/`
  + `scripts/corpus_readiness/`.
- TEM8 documented component (916 files, TEM8 folder per manual) is NOT present
  in this physical copy; recorded as an unexplained absence.
