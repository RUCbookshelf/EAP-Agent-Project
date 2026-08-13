# PDW3-WU2 LEARNER — CHECKPOINT 001: Preflight & Bounded Decomposition (durable)

- run_id: `PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__20260811T162236Z__5b4bbd`
- goal_id: `PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812`
- owner: LEARNER (Feedback & Learner Intelligence)
- worktree: `A:\EAP Agent Project\worktrees\learner`
- branch: `dept/feedback-learner`
- starting_sha: `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`
- checkpoint written: 2026-08-12 (Asia/Shanghai), before any product write
- Authority: PROGRAM LIVE WAVE-3 WU2 OVERRIDE (executor-prompt.md, read first) + Goal Packet. Model route for parent and all workers: `deepseek/deepseek-v4-flash`, reasoning `ultra`; nested workers `PLANNING_DISABLED=1`. No provider/reasoning substitution.

## 1. Mandatory Git preflight — COMPLETE, GREEN

Commands run from `A:\EAP Agent Project\worktrees\learner` with command-scoped `-c safe.directory` (no global config change):

| Check | Result |
| --- | --- |
| `git rev-parse --show-toplevel` | `A:/EAP Agent Project/worktrees/learner` — matches identity block and Goal Packet |
| `git branch --show-current` | `dept/feedback-learner` — matches identity block and `WORKSTREAM_REGISTRY.json` |
| `git rev-parse HEAD` | `7a9e4b470c41c0453a3795233f1bdd5c483d80ae` — exact promoted baseline in override and packet |
| `git status --short` | exactly 5 untracked entries, zero tracked modifications (see 1a) |
| `git worktree list` | learner at `7a9e4b4 [dept/feedback-learner]`; topology matches `WORKTREE_REGISTRY.md` |

### 1a. Pre-existing untracked evidence (preserved, NOT touched)

- `docs/integration/LEARNER-FOUNDATION-FREEZE-20260809.md`
- `docs/integration/PDW1-ALIGN-LEARNER-B6FCE9-20260809.md`
- `docs/integration/PDW2-ALIGN-LEARNER-59500127-20260810.md`
- `docs/integration/PDW3-ALIGN-LEARNER-7A9E4B-20260811.md`
- `tests/learner/__init__.py`

Fingerprints were captured by the WU0 alignment report (`PDW3-ALIGN-LEARNER-7A9E4B-20260811.md`) and remain unchanged per the status output above. No reset/clean/restore/stage/move/delete was performed.

## 2. Program Control artifacts read (required context)

- `runs/PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__20260811T162236Z__5b4bbd/executor-prompt.md` (live override + Goal Packet)
- `runs/.../run-state.json` (dispatch record; legacy model note superseded by the override)
- `program-control/WORKSTREAM_REGISTRY.json` (LEARNER `goal_readiness: READY`, `PDW3_WU2_LEARNER_READY_AFTER_CORE_WU1_GREEN`)
- `program-control/PROGRAM_STATUS.md`, `DEPENDENCY_GRAPH.md`, `PROMOTION_HISTORY.md`, `WORKTREE_REGISTRY.md`
- `program-control/schemas/handoff.schema.json` (required handoff shape)
- CORE WU1 handoff (JSON + Markdown): `program-control/handoffs/CORE/PDW3-WU1-...-ad2fdd.handoff.json` and `worktrees/shared-core/docs/integration/pdw3-wu1-recovery-20260811/CORE-WU1-DEPARTMENT-HANDOFF.md`
- `worktrees/learner/AGENTS.md` and `worktrees/learner/docs/integration/PDW3-ALIGN-LEARNER-7A9E4B-20260811.md`

## 3. Bounded read-only decomposition — COMPLETE (phase 1 inventory)

No product file was modified. The inventory below was produced by read-only inspection of the learner worktree and the CORE WU1 candidate surface in `worktrees/shared-core`.

### 3a. Existing LEARNER (Wave-2) surface to preserve and extend

- `app/practice/`: target creation/mapping/completion/evaluations/task context; Migration-14 tables `practice_targets`, `exercise_instances`, `exercise_attempts`, `practice_evaluations`, `feedback_engagement_traces`, `within_task_response_candidates`, `transfer_evidence_candidates`, `practice_state_snapshots`; existing 422/404/403 fail-closed routing patterns.
- `app/journey/`: `JourneyService` + `build_cycles` projections over essays/analysis/feedback/practice targets/attempts/evaluations/transfer candidates.
- `app/learner/`: evidence admission/provenance (`evidence.py`), exposure/O2 gating (`exposure.py`), feedback policy (`feedback_policy.py`), history (`history.py`), practice provenance (`practice_provenance.py`), normative-claim scanner (`normative.py`), Wave-2 longitudinal model/repository/services.
- `app/api/`: single composition root `main.py` (`_BUSINESS_ROUTERS`, `_build_services`); routers `practice.py`, `journey.py`, `wave2_modules/learner_api.py` (Wave-2 F-1 duck-typed shared-store consumption + local fallback).
- `app/infrastructure/sqlite/repositories/`: `SQLitePracticeRepository`, `SQLiteLearnerRepository`, `SQLiteWave2Repository`, etc.; `repositories/__init__.py` exports.
- `tests/learner/`: 152 existing test functions (Wave-2 regression), including shared-store consumption and WU-D contract mirror patterns.

### 3b. Inherited CORE WU1 contract surface (read-only, uncommitted candidate in shared-core)

- `app/review/models.py`: `Rating` (again/hard/good/easy, ordinals 1-4), `PracticeActivity` (evidence_kind literal `"practice"`), `ReviewEvent` (three separate rating channels), `SchedulerStateSnapshot/SchedulingResult/SchedulerIdentity/SchedulerStateRecord`; explicit no-mastery/no-transfer limitation strings.
- `app/review/protocols.py`: `ReviewRepositoryProtocol`, `SchedulerProtocol`, `LearningItemReaderProtocol`, `ReviewRepositoryConflictError` (404/409/403/422 fail-closed signals).
- `app/review/service.py` (`ReviewService`, `ReviewError`), `rating_policy.py` (`resolve_final_rating`), `scheduler.py` (real py-fsrs 6.3.2 adapter, deterministic vectors), `app/api/routers/review.py` (5 routes), `app/infrastructure/sqlite/repositories/review.py` (`SQLiteReviewRepository`).
- Migration 15 (strictly additive: 3 tables + 5 indexes after Migration 14; version single-source = 15); 82 tests under `tests/review/`; 206/206 Wave-2 reconciled surface.

### 3c. Consumption decision (recorded for INT)

Following the Wave-2 F-1 precedent (`PDW2-WU2-F1-LEARNER-REPOSITORY-CONSUME-20260811.md`): LEARNER WU2 adds **no migration and no `app/review` copy**. Learner-owned modules define structural ports mirroring the CORE contracts; adapters consume the CORE-composed shared review store when present (e.g. `request.app.state.review_repository` at integration) and use in-memory fakes for standalone tests. Final composition-root wiring and CORE-candidate merge remain INT's consolidated Wave-3 gate responsibility.

## 4. Slice inventory (disjoint file ownership)

Every worker is dispatched as `deepseek/deepseek-v4-flash` + ultra with `PLANNING_DISABLED=1`; a failed bounded slice gets at most one retry of that slice only.

| Slice | Scope (disjoint) | Status |
| --- | --- | --- |
| A practice/review dual-channel evidence + rating reconciliation | `app/practice/**` evidence orchestration; `app/learner/**` review ports/contracts; `app/infrastructure/**` adapters; `tests/learner/test_practice_review_evidence*` | PENDING_DISPATCH |
| B practice history + authentic-application observation projections | `app/journey/**`; `tests/learner/test_journey_history_transfer*` | PENDING_DISPATCH |
| C positive longitudinal acknowledgement + provenance/version + consent + fail-closed + semantic safety | `app/learner/**`; `app/api/routers/**` learner-owned routes; `tests/learner/test_acknowledgement*`, semantic-safety regression | PENDING_DISPATCH |
| D API composition/wiring + Wave-2 regression | `app/api/**` (learner wiring only); `tests/wave2/**` + affected root tests | PENDING_DISPATCH |
| V1 independent read-only verifier | evidence-only, read-only sandbox; no product writes | PENDING_DISPATCH |

## 5. Dispatch status and exact current state

- This session exposes **no multi-agent spawn tool** (`multi_agent_v1__spawn_agent` absent from the toolset; no tool_search; `opencode`/`ocx run` not on PATH). This matches the known tool-availability variance recorded in prior rollouts.
- The local opencodex proxy (`127.0.0.1:10100`) is live and advertises `deepseek/deepseek-v4-flash`; `ocx agent status` reports `injection.model: opencode-go/deepseek-v4-flash`, `injection.effort: ultra`, matching the override's worker contract.
- Candidate real-agent dispatch path: official `codex` CLI (0.145.0) through the opencodex shim/proxy. Verification of that path was interrupted before completion; **no subprocess was launched** by this run.
- Blocking finding: **none at this checkpoint**. Decomposition is complete; the immediate next bounded step is verifying the real-agent dispatch path with a minimal smoke test, then dispatching slices A-D and V1.
- If the runtime cannot dispatch `deepseek/deepseek-v4-flash` + ultra workers, the parent will record a terminal RED handoff with exact provider/model/effort errors rather than silently substituting a provider or reasoning mode.

## 6. Resource hygiene

- Zero product writes; zero Git mutations; zero Program Control writes; no raw SWECCL access; no other worktree touched; no subprocess launched.
- All pre-existing dirty/untracked state preserved.
