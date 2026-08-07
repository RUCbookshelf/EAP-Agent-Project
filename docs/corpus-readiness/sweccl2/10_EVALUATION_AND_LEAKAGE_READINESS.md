# 10 — Evaluation and Leakage Readiness

Data: `data/holdout_candidates.csv` (511 candidate records),
`data/leakage_plan.json`.

## Partitioning status

No final train/dev/test partitions were created (not justified before a
research design). The following constraints and candidates prepare future
evaluation.

## Leakage risks (actual, from data)

- Same-text duplicates: 240 documents in duplicate groups; placing group
  members in both development and evaluation is forbidden.
- Same-prompt leakage: 27 prompts; prompt-level grouping is required for
  prompt-controlled splits.
- Corrupt-variant risk: WARG2081 has usable TAGGED only.
- Scored-data contamination: the 270 expository texts carry human scores
  (TOOLS/exp.sav, exp.xls); using them as both reference and evaluation is
  circular (architecture D-07 circularity prohibition).
- Unknown learner identity: WECCL filenames carry no learner ID; same-learner
  isolation across documents cannot be guaranteed; duplicate detection is the
  only proxy available.

## Stable grouping keys

document_id; prompt_id; genre; duplicate_group_id (derived); timed_status;
grade; major_type; entry_year.

## Protection candidates

- 270 expository texts (scored; single prompt) - highest-value protected block.
- 240 duplicate-group members - exclude from evaluation or dedupe explicitly.
- WARG2081 - tagged-only text; excluded from raw/lemma-based evaluations.

## Partitioning constraints (frozen for the next Goal)

- Never split duplicate-group members across dev/eval.
- Never split the same prompt across dev/eval without explicit
  prompt-matching design.
- Protect the expository scored block as one unit.
- Any future partition must be reproducible from document_id + grouping keys
  and versioned.
