# 15 - Stage 6 WU-E: Expository-Score-Based Evaluation Design (Protected Block)

## Purpose

WU-E records the DESIGN for evaluating the WU-A/B/C research pipeline
against the human expository scores, using the protected 270-document block.
This is a design artifact: **no partitions are created, no model is trained,
and no learner-facing output exists** in this Goal.

## Protected block (from Stage 5, WU3.1/WU3.3)

- 270 scored expository texts (EXP01 series, `WEXP####` ids), protected
  block - not development material without Research Evaluation approval.
- Score linkage established: `TOOLS/exp.xls` / `TOOLS/exp.sav` (raw SWECCL,
  read-only metadata inspection), key `ID = WEXP####`, 270/270 coverage, no
  ambiguity, no missingness. Fields: Rater_A/B/C (100-scale), Language,
  Content, Organization, Average_score.
- Duplicate policy: duplicate-group members are never split across
  dev/eval; no final partitions exist.

## Design objectives

1. Descriptive association between per-feature observed-descriptive
   comparison output (estimated percentile, z_distance from WU-C) and the
   rater scores, at document level within the block.
2. Coverage and availability accounting (feature/distribution availability
   across the block); missingness recorded, never imputed.

Claim limits: observed-descriptive association only - no causal claim, no
diagnostic threshold, no proficiency/mastery/learning-gain interpretation.

## Machine-readable design record

`data/stage6_wu_e_evaluation_design.json` (version
`stage6-wu-e-design-v0.1.0`) - machine-checkable constraints, protected-block
facts, licensing basis, and provenance. Validated by
`tests/corpus/test_stage6_artifacts.py`.

## Constraints (binding)

- No final train/dev/test partitions; duplicate-group members never split.
- Protected block not used as development material without approval.
- All results `learner_exposure="research_only"`.
- No raw corpus text, excerpts, or reconstructed wording in any artifact.
- No raw SWECCL path or handle leaves the CORPUS boundary (ADR-06).
- No LLM computation of corpus statistics (I5).
