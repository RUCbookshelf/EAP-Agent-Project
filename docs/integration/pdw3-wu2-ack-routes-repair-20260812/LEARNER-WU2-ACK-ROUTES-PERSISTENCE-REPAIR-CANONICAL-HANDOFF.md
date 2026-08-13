# LEARNER WU2 ACK-ROUTES-PERSISTENCE REPAIR — Canonical Handoff

- Handoff ID: `LEARNER-WU2-ACK-ROUTES-PERSISTENCE-REPAIR-CANONICAL-HANDOFF-20260812T102708+0800`
- Goal/run: `PDW3-WU2-LEARNER-ACK-ROUTES-PERSISTENCE-REPAIR-20260812`
  / `PDW3-WU2-LEARNER-ACK-ROUTES-PERSISTENCE-REPAIR-20260812__20260812T014849Z__710c45`
- Owner: LEARNER. Gate authority: INT.
- Worktree/branch/HEAD: `A:\EAP Agent Project\worktrees\learner` /
  `dept/feedback-learner` / `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`
  (starting_sha == final_sha; no commit was created).
- Verdict: **GREEN (LEARNER-owned scope)** — every RETRY-2 AMBER gap within
  LEARNER ownership is closed with direct evidence; the remaining items are
  cross-cutting pins and physical CORE injection owned by INT.
- Status after return: **HANDOFF_PENDING_ACCEPTANCE** — the parent context
  stays open until INT/PROGRAM explicitly accepts or rejects this handoff;
  a rejected handoff returns to this same parent for repair.

## What was delivered

1. **Two approved Journey routes** (live ownership confirmed; router is
   learner-owned; no path collisions):
   - `GET /api/v1/students/{student_id}/journey/practice-history`
   - `GET /api/v1/students/{student_id}/journey/authentic-application`
2. **Durable acknowledgement persistence**: additive Migration 15
   `learner_acknowledgement_persistence` (one table + two indexes in the
   single SQLite database) and the append-only
   `SQLiteAcknowledgementRepository` (atomic conflict/duplicate rejection,
   no update/delete surface).
3. **Qualified evidence lookup**: `SQLiteAcknowledgementEvidenceLookup` over
   `history_evidence_registry`, practice tables, and `learning_items`, with
   guarded structural reads of CORE `review_events` and future
   `learner_observed_evidence`; exact status matching only; missing tables
   fail closed.
4. **Acknowledgement record links**: `learning_item_id`,
   `authentic_evidence_status`, `practice_activity_id`, `review_event_id`
   with service link gates (404/403/422) and locked L0 epistemic/outcome
   semantics.
5. **CORE ReviewService typed boundary**: `create_app(core_review_service=...)`
   injection point over `CoreReviewServicePort`; no CORE code copied, no
   second store/runtime/composition root; fail closed until INT injects.
6. **Six stale migration-version pins reconciled** (user-authorized),
   mirroring CORE WU1 R2 semantics.

## Verification evidence (parent-run, worktree `.venv`)

| Suite | Result |
| --- | --- |
| Worker P focused persistence/evidence | 80 passed |
| Worker R routes + journey service (25) + tests/learner (287) | PASS |
| Parent focused WU2 suite | 161 passed |
| Journey/Wave-2/Learner regression | 436 passed |
| Practice/narrowing regression | 250 passed, 1 stale v14-era pin (out of the six authorized) |
| Composition/router pins | 28 passed, 2 unowned stale pins (v095b/v095d) |
| Six authorized migration pins | 18 passed |

Full detail: `CHECKPOINT-003-TEST-EVIDENCE.md` in this directory.

## Blockers / remaining (INT-owned)

- v095b/v095d route contract pins must be regenerated/qualified at runtime
  104 (unowned cross-cutting tests).
- Nine remaining `==14` root migration pins on the learner branch; CORE WU1
  R2 already reconciles the same family on `dept/shared-core`; INT carries
  those fixes.
- Physical CORE ReviewService injection is an INT composition step
  (CORE WU1 candidate is uncommitted in the shared-core worktree); the typed
  boundary is ready and fails closed until injected.

## Resource hygiene

- No commit, push, PR, merge, promotion, reset, clean, restore, rebase,
  Program Control write, or other-worktree change.
- All five pre-existing untracked LEARNER evidence paths and every existing
  WU2 file preserved; temporary parent pytest directories removed.
- Workers P/R used `deepseek/deepseek-v4-flash` + `ultra` +
  `PLANNING_DISABLED=1`; no provider/model substitution.
