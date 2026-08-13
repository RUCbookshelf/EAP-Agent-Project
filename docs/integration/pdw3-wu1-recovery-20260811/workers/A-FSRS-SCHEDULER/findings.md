# Worker A Findings — FSRS/scheduler audit (READ-ONLY)

- task_id: PDW3-WU1-DECOMP-RECOVERY__A-FSRS-SCHEDULER
- parent_work_unit: PDW3-WU1-CORE-DECOMPOSITION-RECOVERY-20260811 / Phase 1
- task_class: REVIEW
- worktree: `A:\EAP Agent Project\worktrees\shared-core`
- branch / HEAD: `dept/shared-core` @ `7a9e4b470c41c0453a3795233f1bdd5c483d80ae` (matches packet)
- date: 2026-08-11
- verdict: **PASS**
- blocker: None

## Scope

Read-only audit of the preserved CORE WU1 partial implementation for FSRS
scheduler correctness against the real installed `fsrs==6.3.2` API and the
rating/state lifecycle. No product file, Program Control file, or git state
was modified. Only this file and `evidence/` were written.

## Files inspected (path:line)

In-scope (app/review):

- `app/review/models.py:47-57` (`Rating` StrEnum + `RATING_ORDINALS`
  again=1/hard=2/good=3/easy=4); `:141-158` (`SchedulerStateSnapshot`:
  card_id/state/step/stability/difficulty/due/last_review); `:160-170`
  (`SchedulingResult`); `:173-181` (`SchedulerIdentity`); `:184-199`
  (`SchedulerStateRecord`); `:203-241` (`ReviewEvent` with three separate
  rating channels + version/provenance); `:22-43` fixed boundary statements.
- `app/review/protocols.py:39-55` (`SchedulerProtocol`:
  identity/new_state/review); `:24-36` (`ReviewRepositoryProtocol`);
  `:58-62` (`LearningItemReaderProtocol`).
- `app/review/rating_policy.py:19` (`RATING_RULE_VERSION =
  "rating-rule-v1.0.0"`); `:22-34` (`resolve_final_rating` conservative
  minimum of the two channels; no learner -> system; never a weighted
  average).
- `app/review/scheduler.py:38-43` (`_library_version` via
  importlib.metadata); `:44-53` state name mapping; `:60-65`
  (`_identity_parameters` = JSON-safe `Scheduler.to_dict()`); `:67-98`
  (`FSRSSchedulerAdapter.__init__` constructs the real `Scheduler` with
  `enable_fuzzing=False` and rejects `enable_fuzzing=True`); `:100-108`
  (`new_state` -> real `Card(card_id, due)`); `:110-120` (`to_card`);
  `:122-136` (`from_card`); `:138-163` (`review` -> real
  `Scheduler.review_card(card, rating, review_datetime)` returning
  `(new_state, SchedulingResult)`).
- `app/review/service.py:37-41` (`_stable_card_id` deterministic sha256 ->
  int); `:43-54` (`_coerce_rating` fail-closed); `:97-111`
  (`_require_learning_item`); `:132-215` (`record_review`: validation,
  state load/new, `resolve_final_rating`, `scheduler.review`,
  `ReviewEvent` with identity+parameters+rating-rule version, atomic
  event+state persistence); `:218-227` (`get_schedule`).
- `app/review/__init__.py` public surface.

Scheduling-relevant contracts outside app/review:

- `app/l2/wave2/models.py:352-370` (LearningItem v1 keeps its no-FSRS
  contract); `app/infrastructure/sqlite/repositories/wave2.py:349-374`
  (`LearningItem` no-FSRS/no-practice notes).
- `pyproject.toml:14` (`"fsrs==6.3.2"`); `uv.lock:249-257` (fsrs 6.3.2,
  pypi, hashes); `uv.lock:1494` (specifier `==6.3.2`).
- Installed package: `.venv\Lib\site-packages\fsrs\__init__.py` (+
  `fsrs/scheduler.py`, `fsrs/card.py`, `fsrs/rating.py`,
  `fsrs/review_log.py`, `fsrs/state.py`), version 6.3.2.

Read-only wiring checks (Worker B/C surface, used only to judge scheduler
wiring):

- `app/api/main.py:187-191` (single `ReviewService` + single
  `FSRSSchedulerAdapter()` in the one composition root).
- `app/database/migrations.py:975-1070` (Migration 15: additive
  `practice_activities`, `review_events` with three distinct rating
  columns + CHECK constraints, `learning_item_scheduler_states` ONE row
  per LearningItem; `PRAGMA user_version = 15`); `app/version.py:22-29`
  (`PLATFORM_DATABASE_MIGRATION_VERSION = 15`).
- `app/infrastructure/sqlite/repositories/review.py:64-137`
  (`record_review_event`: atomic insert/upsert, JSON state/identity,
  event id generation).
- `app/api/routers/review.py` (thin router; no scheduler logic; 404/422
  mapping for `ReviewError`).
- `app/learning_items/` — **directory does not exist** in this worktree;
  packet scope item is N/A. The scheduling-relevant LearningItem contract
  is `LearningItemReaderProtocol` (`app/review/protocols.py:58-62`) wired
  to the Wave-2 repository; LearningItem v1 has no FSRS fields.

## Tests run (command, result, evidence path)

1. `python -m pytest -p no:cacheprovider --basetemp <evidence>/pytest-tmp -q
   tests/review/test_scheduler_determinism.py
   tests/review/test_rating_policy.py tests/review/test_review_service.py`
   -> **23 passed** (8.81s).
   Evidence: `evidence/pytest-targeted-001.log`
2. Full review suite: `python -m pytest -p no:cacheprovider --basetemp
   <evidence>/pytest-tmp-full -q tests/review`
   -> **53 passed, 2 warnings** (37.23s; warnings are third-party
   deprecations, not review-code issues).
   Evidence: `evidence/pytest-review-suite-002.log`
3. Packet-mandated version probe `import fsrs; print(fsrs.__version__)`
   -> AttributeError (fsrs 6.3.2 has no `__version__`); authoritative
   check `importlib.metadata.version("fsrs")` -> **6.3.2**.
   Evidence: `evidence/01-fsrs-version-check.txt`
4. Installed fsrs API signature dump (inspect) vs adapter usage.
   Evidence: `evidence/02-fsrs-api-signatures.txt`
5. Raw fsrs 6.3.2 direct vector computation (no app code) cross-checked
   against the adapter's asserted vectors -> exact match on all values.
   Evidence: `evidence/03-raw-fsrs-vector-crosscheck.txt`
6. Fail-closed probes on `_coerce_rating` (9 probes: valid strings/members
   pass; `'excellent'`, `'3'`, `3`, `None`, foreign `fsrs.Rating` enum,
   `''`, `'GOOD'` all rejected).
   Evidence: `evidence/04-failclosed-rating-probes.txt`
7. Git state + single-composition scan.
   Evidence: `evidence/05-git-and-composition-evidence.txt`

All commands ran with `PYTHONDONTWRITEBYTECODE=1`; tests used temp
databases under `<evidence>/pytest-tmp*` only; repository, git state, and
Program Control untouched.

## Findings

### A — Complete / coherent

- A1. **Real fsrs 6.3.2 API with correct signatures.** The adapter calls
  `Scheduler.review_card(card, rating, review_datetime)` with a real
  `Card` rebuilt from the snapshot and a real `Rating` enum member
  (`app/review/scheduler.py:110-120,138-163`). Verified member-by-member
  against the installed package (`evidence/02`): `Card.__init__`,
  `ReviewLog.__init__`, `Scheduler.__init__` (default 21 parameters,
  learning_steps 60/600s, relearning_steps 600s, max interval 36500),
  `Rating`/`State` values. The adapter does not use any removed/renamed
  API (e.g. no `Scheduler.next`, which does not exist in 6.3.2).
- A2. **Deterministic vectors match real fsrs.** `enable_fuzzing=False` is
  forced and `enable_fuzzing=True` raises (`scheduler.py:70-82`).
  `test_scheduler_determinism.py` asserts exact stability/difficulty/due
  values that were independently reproduced against raw fsrs 6.3.2
  (`evidence/03`): first Good -> Learning/step 1/2.3065/2.118103970459016/
  +600s; second Good -> Review/2.111214235785395/+2d; Again -> Relearning
  step 0/difficulty > 7/stability < 1; Easy -> Review immediately;
  identical repeat vectors; snapshot round-trip through a real `Card`.
- A3. **State transitions and rating mappings correct.** New -> Learning
  (step progression) -> Review -> Relearning (Again on Review) -> Review.
  The full state machine is executed by the real `review_card`; the
  adapter only maps the 4 app ratings to the fsrs `Rating` enum
  (`scheduler.py:144-152`) and the 3 state names to `State`
  (`scheduler.py:44-53`); ordinal equality is asserted by
  `test_rating_policy.py` (`RATING_ORDINALS == {again:1, hard:2, good:3,
  easy:4}`).
- A4. **Three rating channels distinct.** `ReviewEvent` keeps
  `system_provisional_rating`, `learner_self_rating`,
  `final_scheduler_rating` as separate fields (`models.py:203-241`);
  `resolve_final_rating` is a conservative minimum, never a weighted
  average and always one of the two input channels
  (`rating_policy.py:22-34`; `test_rating_policy.py`); Migration 15
  stores them as three distinct columns with CHECK constraints
  (`migrations.py:1025-1042`); `test_review_service.py::test_case_c`
  verifies the raw SQLite row keeps `("good","hard","hard")`.
- A5. **Provenance versioned and persisted.** `SchedulerIdentity`
  (implementation `py-fsrs`, library version `6.3.2` from
  importlib.metadata, algorithm `FSRS`, full JSON-safe parameters
  incl. `enable_fuzzing=False`, `desired_retention=0.9`,
  `learning_steps=[60,600]`, `relearning_steps=[600]`, 21 parameters) +
  `rating_rule_version="rating-rule-v1.0.0"` are stored on every
  `review_events` row and on `learning_item_scheduler_states`
  (`scheduler.py:83-98`, `service.py:132-215`, `migrations.py:1040-1068`,
  `repositories/review.py:64-137`). Deterministic reconstruction is
  proven: `test_case_d` replays the real scheduler on stored
  `state_before` + `final_scheduler_rating` + `reviewed_at` and requires
  an exact match with stored `state_after`.
- A6. **Fail-closed inputs.** `_coerce_rating` rejects every value outside
  the 4-value space (probes in `evidence/04`; also rejects the foreign
  `fsrs.Rating` enum and numeric/uppercase/empty inputs); unknown
  LearningItem -> `ReviewError("learning_item_not_found")` with no write;
  invalid `authentic_evidence_status` -> `ReviewError`; Pydantic
  `extra="forbid"` everywhere; `SchedulerStateSnapshot` state is a
  Literal and `step >= 0`; naive/non-UTC `reviewed_at` is rejected by
  fsrs itself before any write.
- A7. **No semantic leakage.** `SchedulerStateSnapshot` fields are exactly
  {card_id, state, step, stability, difficulty, due, last_review};
  `FSRS_STATE_IS_SCHEDULING` / `NO_TRANSFER_IMPLICATION` /
  `PRACTICE_ACTIVITY_LIMITATION` fixed statements; AST-level scan in
  `tests/review/test_semantic_boundaries.py` forbids
  mastery/proficiency/learning_gain identifiers in app/review; scheduler
  state is persisted outside LearningItem v1 (no-FSRS contract preserved
  in wave2). No ability/score/percentage naming found in app/review.
- A8. **One scheduler, one runtime.** Exactly one `FSRSSchedulerAdapter()`
  and one `ReviewService` exist, in the single composition root
  (`app/api/main.py:187-191`); no other fsrs import/Scheduler usage
  exists anywhere in `app/` outside `app/review/`; the router is thin and
  stateless; Migration 15 and `PLATFORM_DATABASE_MIGRATION_VERSION=15`
  are single-sourced (`app/version.py:22-29`, test_migration_15.py).

### B — Implemented but unverified

- B1. Regression beyond `tests/review` (the broader suite, e.g. the
  1837-test wave-1 gate) was not re-run in this worker; per packet scope,
  only the review tests and the scheduler wiring were verified here.
- B2. `fsrs.__version__` does not exist in fsrs 6.3.2, so the packet's
  literal probe command fails with AttributeError even though the package
  is correctly installed (6.3.2 via importlib.metadata). The adapter
  itself reads the version correctly (`scheduler.py:38-43`). This is a
  verification-script nuance, not a code defect; orchestration should use
  `importlib.metadata.version("fsrs")`.

### C — Incomplete

- C1. `app/learning_items/` does not exist in this worktree (packet scope
  item N/A). Scheduling-relevant LearningItem contracts are satisfied
  through `LearningItemReaderProtocol` and the Wave-2 repository, so no
  functional gap was found; flagged so the orchestrator knows the scope
  item mapped to a different path.

### D — Incorrect / contract-incompatible

- D1. None found.

### E — Out-of-scope drift (observations only, handed to Worker B/C)

- E1. `INSERT OR REPLACE` is used for `review_events` and
  `learning_item_scheduler_states` in `app/infrastructure/sqlite/
  repositories/review.py`; a client-supplied event id that already exists
  would silently overwrite a historical event. Service-generated ids make
  this unlikely, but the persistence audit (Worker B) should confirm the
  intended uniqueness/append-only semantics.
- E2. The API router maps only `ReviewError` to 404/422; a naive/non-UTC
  `reviewed_at` reaching the service raises the library's `ValueError`
  before any write, but the router would surface it as a 500 rather than
  a 4xx. Fail-closed (nothing persisted) but worth a router-level
  validation decision (Worker B/C).

## Blocker

None.

## Verdict

**PASS.** The preserved WU1 review/scheduling implementation calls the
real installed fsrs 6.3.2 API with correct signatures, produces
deterministic vectors that exactly match raw library computations, keeps
the three rating channels distinct with versioned conservative resolution
and persisted provenance, fails closed on invalid ratings/states/identity,
shows no semantic leakage, and exists as exactly one scheduler in one
composition root. The only actionable items (packet probe command nuance;
`app/learning_items` path mapping; persistence/router observations) are
non-blocking and belong to orchestration or Workers B/C.
