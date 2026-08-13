# L2 Domain Pack v1 Freeze Record (L2-DOMAIN-PACK-V1-FREEZE)

**Owner:** L2  
**Branch:** `dept/l2-writing`  
**Worktree:** `A:\EAP Agent Project\worktrees\l2-writing`  
**Starting SHA:** `09264abbd93cdc6b62b83cefd94b3b640319ac9b`  
**Frozen candidate SHA:** `fa6655c165f589b03c1fd1cfda511c3e80f42201`  
**Verdict:** GREEN — the Wave-5 gate-qualified Domain Pack v1 state was frozen in one scoped local commit. Promotion is not part of this Goal.

## 1. Authorization and preflight

- Active Goal: `L2-DOMAIN-PACK-V1-FREEZE` in `program-control/work-status/L2.current.json`.
- Authorized worktree, branch, and starting SHA matched the Goal Packet exactly.
- Wave-5 gate evidence: `program-control/runs/INT-INTEGRATION-GATES-WAVE5__20260809T105217Z__41b143/handoff.json` and `worktrees/int-study-base/docs/integration/INT-INTEGRATION-GATES-WAVE5-20260809.md`.
- No promotion, push, PR, merge, rebase, reset, or `git clean` was performed. No other worktree or raw SWECCL source was touched.

The older `WORKSTREAM_REGISTRY.json`/`WORKTREE_REGISTRY.md` L2 head projection was stale. Per the executor prompt, the authoritative current-state projection was `program-control/work-status/L2.current.json`, which named this active Goal, worktree, branch, and baseline `09264ab...`.

## 2. Gate-qualified fingerprints

All Wave-5 fingerprint prefixes matched the live working tree before staging and the checked-out committed tree afterward.

| File | Required prefix | Verified SHA-256 |
| --- | --- | --- |
| `app/configuration/domain_packs/l2/v1.0.0/manifest.json` | `6CE081F6` | `6CE081F62DD8353F440432AFE340B9A80997A8B59E3F6777D85F1A42E99AE482` |
| `app/configuration/domain_packs/l2/v1.0.0/task_types.json` | `A0B6AF01` | `A0B6AF0148E47D1D39C697C89BBCE46A6F05F92214CC609F263D9FB20A3E2DA7` |
| `app/configuration/domain_packs/l2/v1.0.0/trigger_dictionaries.json` | `65A537FD` | `65A537FD5492B5D26DFB300E741230C0FBCDB42879C861E5F9674DD1F21C432A` |
| `app/configuration/domain_packs/l2/v1.0.0/conflict_pairs.json` | `4C20116E` | `4C20116E12C94B23675D919EE37754C39E5750839BA11677FF0199E0765D6C07` |
| `app/configuration/domain_packs/l2/v1.0.0/legacy_genre_mapping.json` | `B5ADC66A` | `B5ADC66A87365F995019A6EF3A0BB421CA45DD39F4EE99EE0A6A421241ABCE79` |
| `app/services/task_type_classifier.py` | `9F52A2F4` | `9F52A2F40E5FD4719572ECCB21F29889B66CE377049C11CAC82B8B686F79794A` |
| `app/services/legacy_genre_mapping.py` | `FBB6EDD1` | `FBB6EDD190E0721E9DEE2467BB438E851D5F5AB97FC3D2004B34E1BA6640A55D` |

The qualified working-tree and committed-tree fingerprints are both:

```text
B17467375BCA77CDB6CDDF23F9AEA9AF1BE0335FFCF13035186ACC9E8BC08E34
```

Fingerprint algorithm: SHA-256 of UTF-8 canonical manifest lines, sorted by relative path, with one trailing LF; each line is `SHA256␠␠relative-path`. The manifest contains the exact 23 committed candidate files. `git diff --quiet HEAD -- <candidate paths>` verified that the checked-out tree equals the commit.

## 3. Scoped commit

Commit message:

```text
feat(l2): freeze Domain Pack v1 gate-qualified candidate
```

- Parent: `09264abbd93cdc6b62b83cefd94b3b640319ac9b` (the assigned baseline).
- Commit: `fa6655c165f589b03c1fd1cfda511c3e80f42201`.
- Scope: 23 files, exactly 9 modified tracked files and 14 added digest artifacts; `2599 insertions(+), 21 deletions(-)`.
- `git diff --check HEAD^ HEAD` passed.
- `git diff --name-status HEAD^ HEAD` matched the allowlist exactly; no unrelated entry entered the commit.

### Modified (9)

- `app/api/schemas.py`
- `app/core/longitudinal_models.py`
- `app/services/learner_model.py`
- `app/shared/task_type_registry.py`
- `locales/en.json`
- `locales/zh_CN.json`
- `tests/shared/test_registry_domain_policy.py`
- `tests/test_v097d_design_system.py`
- `tests/test_v097d_wu2_revision_practice.py`

### Added digest artifacts (14)

- `app/configuration/domain_packs/l2/v1.0.0/manifest.json`
- `app/configuration/domain_packs/l2/v1.0.0/task_types.json`
- `app/configuration/domain_packs/l2/v1.0.0/trigger_dictionaries.json`
- `app/configuration/domain_packs/l2/v1.0.0/conflict_pairs.json`
- `app/configuration/domain_packs/l2/v1.0.0/legacy_genre_mapping.json`
- `app/services/task_type_classifier.py`
- `app/services/legacy_genre_mapping.py`
- `docs/domain/L2_DOMAIN_PACK_V1_CONTENT.md`
- `docs/domain/D-L2-02_MIGRATION_14_DESIGN_NOTE.md`
- `docs/integration/L2_DOMAIN_PACK_V1_REPORT.md`
- `tests/test_task_type_classifier_v1.py`
- `tests/test_legacy_genre_mapping_v1.py`
- `tests/test_learner_model_task_type_v1.py`
- `tests/shared/test_domain_pack_v1_content.py`

## 4. Regression and identity checks

The gate's focused five-file suite was run before and after the commit using the worktree-local environment with bytecode/cache output kept outside the repository:

```text
tests/test_task_type_classifier_v1.py
tests/test_legacy_genre_mapping_v1.py
tests/test_learner_model_task_type_v1.py
tests/shared/test_domain_pack_v1_content.py
tests/test_learner_model_v07.py
```

Results:

- Pre-commit: `106 passed, 2 warnings in 7.56s`.
- Post-commit: `106 passed, 2 warnings in 4.43s`.
- The warnings are third-party FastAPI/Starlette and spaCy/Click deprecation warnings; no test failed.

## 5. Transient handoff cleanup and preserved state

Only these positively identified root-level scratch copies were removed:

| Removed scratch copy | Authoritative Program Control handoff |
| --- | --- |
| `handoff.L2-D22-CENSUS-AND-V1.json` | `program-control/handoffs/L2/L2-D22-CENSUS-AND-V1__L2-D22-CENSUS-AND-V1__20260809T072133Z__6ab4b6.handoff.json` |
| `handoff.json` | `program-control/handoffs/L2/L2-PREREQ-RESOLUTION__L2-PREREQ-RESOLUTION__20260809T010118Z__c89bb2.handoff.json` |

Both scratch files matched their authoritative records by stable handoff identity (`handoff_id`, Goal, owner, branch, worktree, baseline/final SHA, verdict, and return time). Program Control retains normalized/ingested representations, so bytewise hashes differ; this is not evidence of content drift. No other removal occurred.

Before this freeze record was written, the residual untracked set contained exactly the following 22 excluded prior-goal evidence entries. None was staged or committed:

- `docs/domain/D-22_LEGACY_GENRE_MAPPING_PROPOSAL.md`
- `docs/domain/D-22_legacy_genre_mapping_manifest.proposal.json`
- `docs/domain/D-22_legacy_genre_mapping_manifest.v1.0.0.qualified.json`
- `docs/domain/D-L2-02_TASK_TYPE_PERSISTENCE_DECISION.md`
- `docs/domain/D-L2-09_ZHCN_LABELS_DECISION.md`
- `docs/domain/D-L2-10_TASK_TYPE_PICKER_DECISION.md`
- `docs/domain/L2_TASK_TYPE_TAXONOMY_CONTRACT.md`
- `docs/domain/L2_TAXONOMY_VALIDITY_EVIDENCE_PACKAGE.md`
- `docs/domain/L2_VALIDITY_V1_ADJUDICATION.md`
- `docs/domain/L2_VALIDITY_V1_CONTENT_REVIEW.md`
- `docs/domain/L2_VALIDITY_V1_DISPOSITION.json`
- `docs/domain/L2_VALIDITY_V3_COVERAGE_CENSUS_METHODOLOGY.md`
- `docs/domain/census/L2_DP4_LEGACY_ESSAYS_CENSUS_v1.0.0.json`
- `docs/domain/census/dp4_census.py`
- `docs/domain/census/inspect_schema.py`
- `docs/domain/census/verify_artifacts.py`
- `docs/integration/L2_D22_CENSUS_AND_V1_REPORT.md`
- `docs/integration/L2_DISCOURSE_ORGANIZATION_FEASIBILITY_SPIKE.md`
- `docs/integration/L2_EVIDENCE_PREP_REPORT.md`
- `docs/integration/L2_PREREQUISITE_RESOLUTION.md`
- `docs/integration/L2_PREREQ_REMAINING_REPORT.md`
- `docs/integration/L2_VALIDITY_EVIDENCE_REPORT.md`

This freeze record is intentionally untracked and unstaged. The Goal Packet restricts the immutable candidate commit to the exact 23 gate-qualified files above; adding this post-commit evidence record to that commit would violate its scoped inventory.

## 6. Outcome boundary

The L2 Domain Pack v1 candidate is frozen and integration-qualified. It is not promoted. Any promotion requires a separate exact-SHA user authorization under the existing Wave-5 promotion process.
