# Corpus Readiness Tooling (SWECCL 2.0 / WECCL 2.0)

Department-owned, non-production preparation tooling for the L2 corpus package.
Isolated from product runtime; no external uploads; deterministic and idempotent.

## Requirements

- Windows, PowerShell or cmd
- Python 3.12+ (bundled Codex runtime verified: 3.12.13)
- `charset_normalizer` (fallback detection; bundled runtime has it)
- Read access to the physical corpus root
- Write access to the derived-layer location and the repo docs output dir

## Configuration

Constants at the top of each script:

- `CORPUS_ROOT` = `A:\[Linguistics Data] Corpus\SWECCL 2.0`
- `DERIVED_ROOT` = `CORPUS_ROOT\PREPARED\utf8` (derived canonical layer; outside git)
- `OUT_DIR` = `docs/corpus-readiness/sweccl2/data` (machine-readable artifacts)

## Run everything

```powershell
python scripts/corpus_readiness/run_all.py
```

The pipeline is deterministic: sorted traversal, fixed column order, chunked
SHA-256, strict decode with round-trip verification, UTF-8 outputs (BOM for
Excel). Rerunning regenerates identical artifacts (source hashes unchanged).
The derived layer is regenerated from sources; it is a DERIVED artifact and may
be deleted and rebuilt at any time.

## Steps and outputs

`run_all.py` orchestrates preparation steps 01-09; `10_version.py` is a
separate step that emits the package version record (run it after 01-09).

| Step | Outputs |
| --- | --- |
| 01_inventory.py | physical_inventory.csv, physical_inventory_summary.json |
| 02_encoding.py | derived_manifest.csv, encoding_report.json, PREPARED/utf8 layer |
| 03_manifest.py | corpus_manifest.csv, seccl_manifest.csv, metadata_coverage.csv, manifest_summary.json |
| 04_pairing.py | variant_pairing.csv, legacy_annotation_quality.json |
| 05_quality.py | quality_issues.csv, duplicate_report.csv, corpus_exclusions_draft.csv, quality_summary.json |
| 06_composition.py | corpus_composition.csv, documentation_vs_physical.csv, corpus_composition.json |
| 07_reference_groups.py | reference_group_candidates.csv, reference_group_summary.json |
| 08_features.py | feature_candidate_registry.csv, feature_summary.json |
| 09_leakage.py | holdout_candidates.csv, leakage_plan.json |
| 10_version.py | corpus_version.json (package identity + manifest hash) |

## Safety

- Read-only over raw corpus files; never overwrites, renames, deletes, or
  corrects source material.
- Raw corpus content is never committed to git and never uploaded anywhere.
- Derived texts stay under `PREPARED/` outside the repository.
- The discovery-time snapshot
  (`physical_inventory_discovery_snapshot.csv`) is preserved for provenance.

## Tests

```powershell
python -m pytest scripts/corpus_readiness/tests/
```

Tests are deterministic and fast; they validate schemas, documented
expectations, round-trip encoding, and artifact consistency.
