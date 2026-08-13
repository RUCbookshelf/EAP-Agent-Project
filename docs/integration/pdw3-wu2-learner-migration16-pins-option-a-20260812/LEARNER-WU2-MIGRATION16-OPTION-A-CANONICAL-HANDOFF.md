# PDW3-WU2 LEARNER Migration 16 Option A - Canonical Handoff

Status: HANDOFF_PENDING_ACCEPTANCE

- handoff_id: PDW3-WU2-LEARNER-MIGRATION16-PINS-OPTION-A-20260812__20260812T045022Z__d2c40f
- goal_id: PDW3-WU2-LEARNER-MIGRATION16-PINS-OPTION-A-20260812
- owner: LEARNER (continuation of Darwin; parent remains open)
- worktree / branch / HEAD: A:\EAP Agent Project\worktrees\learner / dept/feedback-learner @ 7a9e4b470c41c0453a3795233f1bdd5c483d80ae
- starting_sha == final_sha: 7a9e4b47... (no commit created)
- verdict: GREEN (LEARNER-owned scope; DEPARTMENT GREEN is not INTEGRATION GREEN or promotion)
- schema: handoff.schema.json 1.0.0 (validated with jsonschema)

## 1. What was delivered (user-authorized Option A)

One shared global integer migration ledger in the LEARNER-composed product path:

- Global Migration 15 = review_scheduling_foundation, CORE-owned. The body is consumed byte-identical from the accepted CORE candidate (PDW3-WU2-CORE-GLOBAL-LEDGER-GUARD-OPTION-A-20260812) - SHA-256 67a55c1708d8cccd5f98cffec932eb3649255ba4e6907c0295444528b447a08a, 5975 chars on both worktrees (AST-extracted function bodies; hash includes the terminal newline).
- Global Migration 16 = learner_acknowledgement_persistence, LEARNER-owned (former 15 lane renumbered; body unchanged).
- LATEST_MIGRATION_VERSION = 16 (app/database/migrations.py:45) and PLATFORM_DATABASE_MIGRATION_VERSION = 16 (app/version.py:42).
- CORE-15 consumer seam (not duplicated): GLOBAL_MIGRATION_LEDGER_OWNER/VERSION_15/VERSION_15_NAME + assert_global_migration_15_identity() + assert_global_migration_16_identity() at migrations.py:1177-1258, backed by the single MIGRATIONS registry and app.database.upgrade/rollback on one sqlite3 connection. No second runner, store, scheduler, or composition root; no CORE ReviewService internals copied.

## 2. Upgrade / rollback / idempotence evidence (probe + tests)

The independent probe (evidence/probe_migration16_option_a.py, 22/22 checks passed, PROBE_OK, PROBE_EXIT=0) ran on real migrations with transient SQLite files outside product data:

- Fresh upgrade() lands at 16; ledger rows exact: 14 wave2_revision_loop_and_learner_model, 15 review_scheduling_foundation, 16 learner_acknowledgement_persistence; CORE review families + learner_acknowledgements present.
- A genuine v14-era database (real migrations 1..14 only, Wave-2 rows, user_version=14, no review/ack tables) upgrades 14-15-16 without missing-key or duplicate-identity failure; Wave-2 rows survive (WT000001, LI000001).
- Logical rollback 16-15-14: ledger-only, non-destructive - CORE review tables and the acknowledgement table/data (ACK-PROBE-1) preserved; exact ledger rows removed at each step; non-adjacent rollback rejected (one-step guard).
- Idempotent re-apply 14-15-16 restores exactly one row at 15 and one at 16 with data intact.
- Composed guards return (15, review_scheduling_foundation) and (16, learner_acknowledgement_persistence).

## 3. Stale pin repair

All 12 current-version-stale ==14 sites in 8 root test files (INT adjudication Section 5.1) are replaced with the governed latest source in the exact CORE WU1 R2 form, including the added rollback(connection, 14) one-step steps in test_calf_v08.py, test_v071_reliability_ui.py, and test_v097b_wu3_target_creation.py. tests/test_wave2_migration_v14.py is rewritten to LATEST=16 semantics (fresh ledger rows 14/15/16, v14-era rollback chain 16-15-14, legacy-DB upgrade, DEFAULT coverage). Historical post-rollback and fixture-safe ==14/==15 literals are retained literally (enumerated in WU2-CHANGED-FILES.md Section 3; re-audited live, matching INT Section 5.2). No stale current-latest ==15 pins remain.

## 4. Tests and results (all from the worktree root, transient basetemp)

- Option-A ledger suite: 7 passed (new tests/learner/test_migration_16_option_a_global_ledger.py).
- Migration/ledger/pin family (14 files incl. composition root and version single-sourcing): 190 passed, exit 0.
- Acknowledgement persistence/evidence/route (six-file WU2 suite as in the ACK-ROUTES packet): 161 passed, exit 0.
- Full tests/learner sweep: 327 passed, exit 0.
- Logs: evidence/pytest-ledger-pins-option-a.log, evidence/pytest-wu2-ack-evidence-routes.log, evidence/pytest-learner-sweep.log.

## 5. Seam and composition boundary

LEARNER consumes the CORE-15 seam exactly as the accepted CORE guard handoff prescribes (its dependencies_unlocked: LEARNER implements acknowledgement persistence as global Migration 16 against the same MIGRATIONS registry and app.database.upgrade/rollback, using the CORE guard as the seam). No CORE implementation is copied; the acknowledgement body and its evidence-lookup/repository composition remain LEARNER-owned from the accepted ACK-ROUTES repair candidate. Physical ReviewService injection and the merged-ledger integration gate remain INT-owned.

## 6. Remaining risks / dependencies (INT-owned)

- INT consolidated Wave-3 integration gate; physical composition of the CORE ReviewService through create_app(core_review_service=...).
- INT regeneration/qualification of the unowned cross-cutting route-contract pins (test_v095b_router_contract.py, test_v095d_api_contract.py).
- Learner memory foundation lane (learner_observed_evidence / learner_record_lifecycle) remains separately gated; observed-evidence acknowledgements fail closed until then.
- Exact-SHA promotion decision: WAITING_USER; no promotion authority.

## 7. Resource hygiene

- HEAD unchanged; no commit, stage, push, PR, merge, promotion, reset, clean, restore, rebase; no Program Control write; no other worktree touched; no raw SWECCL access.
- Every pre-existing dirty/untracked WU2 file preserved (git status delta is only the new bounded evidence directory).
- pytest basetemp and probe SQLite files used the writable transient scratch location outside product data (C:\Users\16073\.codex\visualizations\2026\08\11\019ff07f-0388-7433-80f3-92e0b2ee496d). Recursive cleanup of those scratch directories was attempted but the sandbox approval-review backend failed with a provider error; per policy the deletion was not routed around, so the scratch directories (pdw3-wu2-mig16-basetemp*, pdw3-wu2-mig16-probe-tmp) remain there containing only transient test SQLite files - safe to delete by the user or a later approved run. No stray processes.
- Executor route: deepseek-v4-flash with ultra (Darwin continuation); nested workers, if any, run with PLANNING_DISABLED=1.

## 8. Artifacts

- LEARNER-WU2-MIGRATION16-OPTION-A-CANONICAL-HANDOFF.json (schema-valid)
- LEARNER-WU2-MIGRATION16-OPTION-A-CANONICAL-HANDOFF.md (this file)
- WU2-CHANGED-FILES.md
- evidence/probe_migration16_option_a.py + probe-migration16-option-a.log
- evidence/pytest-ledger-pins-option-a.log
- evidence/pytest-wu2-ack-evidence-routes.log
- evidence/pytest-learner-sweep.log
