# L2-PREREQ-REMAINING — Bounded Decision Report

**Goal:** `L2-PREREQ-REMAINING` — resolve remaining Domain Pack v1 prerequisites
D-L2-02 / D-L2-09 / D-L2-10 with bounded decision records.
**Date:** 2026-08-09
**Owner:** L2 Writing Domain
**Starting SHA:** `5aafe2728d7135212bd675a6975b44bcf99ee099`
**Branch / Worktree:** `dept/l2-writing` / `A:\EAP Agent Project\worktrees\l2-writing`
**Verdict:** GREEN (decision records complete; no researcher-labelled items; no implementation)

## 1. Preflight (verified)

- Git root = authorized worktree; branch = `dept/l2-writing`; HEAD = promoted
  baseline `5aafe27`; worktree list matches `WORKTREE_REGISTRY.md`.
- Pre-existing untracked files (`docs/domain/`, two `docs/integration/` records,
  `handoff.json`) preserved untouched.
- Program artifacts read: `WORKSTREAM_REGISTRY.json`, `PROGRAM_STATUS.md`,
  `DEPENDENCY_GRAPH.md`, `PROMOTION_HISTORY.md`, `WORKTREE_REGISTRY.md`,
  dispatch record, context bundle, `USER_DECISION_BRIEF.json`.

## 2. Decisions delivered

| id | decision | artifact |
| --- | --- | --- |
| D-L2-02 | `task_type` **persisted at write time** (ID + taxonomy version + provenance); display labels derived from pack; derived-on-read rejected; additive migration design with behavior-diff gate; non-destructive rollback | `docs/domain/D-L2-02_TASK_TYPE_PERSISTENCE_DECISION.md` |
| D-L2-09 | zh_CN label proposal (观点类作文 / 议论文 / 讨论类作文 / 问题解决类作文 / 通用学术写作) + fixed non-hierarchical canonical display order (contract §1 order); parity contract applies (600/600 → 605/605 at implementation) | `docs/domain/D-L2-09_ZHCN_LABELS_DECISION.md` |
| D-L2-10 | typed picker **deferred**; when built: Student Writing page, independent tasks only, server-validated declared metadata, revisions/practice inherit, honest unclassified states, no design-system change | `docs/domain/D-L2-10_TASK_TYPE_PICKER_DECISION.md` |

Researcher-item screen: none of D-L2-02 / D-L2-09 / D-L2-10 is a measurement-
validity, scientific-admissibility, or evaluation-policy decision; all three are
resolved as bounded L2 domain records. (Validity evidence for the taxonomy
itself remains open per contract §10 and is tracked by PROGRAM — outside this
Goal's assigned items.)

## 3. Evidence anchors

- `06_L2_WRITING_DOMAIN.md` §3 gap 1 (`learner_model.py:333-344` substring
  inference must not survive), §4 additive typed field, §7 open decisions.
- `14_ARCHITECTURE_DECISIONS.md` D-22 (persisted metadata-only), D-26, D-29,
  D-30.
- `L2_TASK_TYPE_TAXONOMY_CONTRACT.md` Constraints 1.1, 2.4, 5.5, 6.4, 7.2-7.6.
- `07_MIGRATION_DECISION.md` (no migration 14 in H1; A&I review for 14+).
- Locale parity tests (`test_design_tokens_v094a.py`,
  `test_v097d_design_system.py` 600/600, `test_v095c_feature_extraction.py`)
  and `locales/*.json` style.
- `app/ui/features/student/writing.py` (genre selectbox),
  `app/practice/task_context.py`, `app/shared/task_type_registry.py` (mechanism
  only; no task_type surface).

## 4. Verification

| check | result |
| --- | --- |
| Preflight identity (root/branch/HEAD/worktree) | PASS |
| Decision records created under `docs/domain/` | PASS (3 files) |
| Integration report created under `docs/integration/` | PASS (this file) |
| No product/behavior change (only new docs; no `app/`, `locales/`, `tests/` edits) | PASS |
| No researcher-labelled item among the three | PASS (`researcher_decision_required=false`) |
| Handoff JSON valid against `schemas/handoff.schema.json` | PASS |

## 5. Dependencies

Unlocked: D-L2-02, D-L2-09, D-L2-10 prerequisite records → the Domain Pack v1
content-authoring prerequisites for these three items are resolved.

Remaining (tracked by PROGRAM; outside this Goal):

- D-L2-03 dimension-envelope feasibility / Research sign-off (UD-02 DEFER
  accepted; re-spike policy preserved).
- Legacy-genre mapping manifest decision (D-22; Research Evaluation + L2 data-
  governance).
- Domain Pack v1 implementation authorization (separately gated; must exclude
  `discourse_organization` as a v1 measurement dimension per UD-02).

## 6. Boundaries honored

No Domain Pack v1 implementation; no product code; no UI change; no locale
change; no migration; no registry registration; no push/PR; nothing written
outside the L2 worktree; raw SWECCL untouched.

*Report produced by the L2 execution agent under Goal L2-PREREQ-REMAINING,
2026-08-09.*
