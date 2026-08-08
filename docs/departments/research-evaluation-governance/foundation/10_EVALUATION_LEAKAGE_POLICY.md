# 10 — Evaluation Leakage Policy

**Department:** Research Evaluation & Data Governance
**Policy id:** `evaluation-leakage-policy-v0.1.0`
**Ratification:** RD-POL-010 (2026-08-07)
**Status:** RATIFIED
**Supersedes:** none (first canonical version; formalizes the readiness constraints, RD-10:37-42)

## 1. Purpose

Formalize future leakage constraints so that accidental leakage is prevented — not to
prematurely freeze research design. No final benchmark split is created by this policy;
any future partition must satisfy these constraints and be versioned.

## 2. Leakage risks (verified facts)

| Risk | Fact | Evidence |
| --- | --- | --- |
| Same-text duplicates | 240 documents in duplicate groups; splitting group members across dev/eval leaks | RD-10:17-20; RD-06 |
| Same-prompt leakage | 27 prompts; prompt-level grouping required for prompt-controlled splits | RD-10:19-20 |
| Corrupt variant | WARG2081 RAW/LEMMA corrupt (TAGGED only) | RD-10:21; corpus_version.json |
| Scored-data contamination | 270 expository texts carry human scores; using the **scores (or score-derived norms)** as both construction and evaluation of a target signal is circular (04 §6). Text-feature participation in descriptive reference distributions remains allowed (04 §3) | RD-10:21-22; ARCH-07:45; 04_EVALUATION_PROTECTION_POLICY.md §3/§6 |
| Unknown learner identity | WECCL filenames carry no learner ID; same-learner isolation cannot be guaranteed; duplicate detection is the only proxy | RD-10:22-23; RD-11:28 |
| Cross-domain mixing | Exports must be domain-scoped by default; unknown domain values rejected/quarantined (D-19/D-36) | ARCH-04:18,91; ARCH-14:176-183,269-272 |

## 3. Binding constraints

1. **Duplicate groups never split.** Members of one duplicate-group (05 definition)
   may not be placed in different sides of any development/evaluation boundary
   (RD-10:39; 05 DP-05).
2. **Same-prompt leakage controlled.** The same prompt may not be split across
   dev/eval without an explicit prompt-matching design that records the grouping and
   its justification (RD-10:40-41; machine check requires `prompt_matching_design=true`
   AND a non-empty `prompt_matching_design_reason` — F10 resolution). Prompt_id is a
   stable grouping key.
3. **270 scored block protected.** The 270 expository texts move as one unit; no
   development use without approval; no score fields in derived artifacts
   (04 EP-07/EP-08/EP-06; RD-10:42).
4. **Unknown learner IDs acknowledged.** No partition may claim learner-level
   isolation from WECCL filenames; duplicate detection is the only proxy; any
   design requiring learner-level isolation must declare it impossible for this
   corpus and use documented proxies.
5. **Versioned partition logic.** Any future partition must be reproducible from
   `document_id` + grouping keys (document_id, prompt_id, genre, duplicate_group_id
   (derived), timed_status, grade, major_type, entry_year — RD-10:25-28), recorded
   with a version, a seed (when randomization is used), and the governing policy
   version. No unversioned partition may be used in research output.
6. **Domain scoping.** Exports and partitions are domain-scoped by default (D-19);
   unknown domain values are rejected/quarantined at export time until the
   migration-14 CHECK exists (D-36) — integration dependency listed in 12.
7. **Evaluation-triggered checks.** Any evaluation design touching corpus data must
   pass the reusable validation logic (section 4) before execution.

## 4. Reusable validation logic (WU11)

Department-owned deterministic validator (pure function, no production wiring):

```text
validate_partition_plan(plan) -> {status: PASS|FAIL, findings: [...]}
```

Checks:
- duplicate-group members never cross boundaries (uses `duplicate_group_id`);
- the same prompt never crosses boundaries without `prompt_matching_design=true` + a
  non-empty `prompt_matching_design_reason` (recorded grouping + justification);
- the 270 block is entirely on one side or entirely absent;
- WARG2081 may only enter a side explicitly declared `side_type=tagged` (unknown side
  types default to mixed and fail);
- every plan document id must exist in the corpus manifest (unknown ids fail);
- plan carries version, seed (when randomized), grouping keys, and policy version;
- no learner-level isolation claim is made for this corpus
  (`claims_learner_isolation` must not be true).

The existing prototype splitter (`app/research/service.py::build_dataset_split`,
student-level, seed 20260730, 0.70/0.15/0.15) is infrastructure tooling with an
explicit "not suitable for model training" boundary (research schemas
interpretation_boundary). It does **not** satisfy section 3 by itself; any future
research partition must run the validation logic and record the result. Replacing or
augmenting the splitter is an integration dependency (12), not a change made here.

## 5. Out of scope

Creating a final train/dev/test partition; freezing a benchmark; defining leakage
mitigation for model training (05 §4.4 remains open); Academic-domain partition design.

## 6. Machine artifact

`policies/evaluation_leakage_policy.json` mirrors sections 3-4 and validates against
`policies/policy_schema.json` (WU11). The validator implementation and tests are listed
in 11_VERIFICATION.md.