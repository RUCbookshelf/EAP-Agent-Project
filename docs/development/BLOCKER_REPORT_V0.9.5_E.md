# v0.9.5-E Blocker Report — Development Database Safety Gate

**Date:** 2026-08-02<br>
**Status:** RESOLVED BY OWNER AUTHORIZATION — the modified development
database was accepted as disposable and isolated from all later verification<br>
**Triggered stop condition:** v0.9.5-E explicitly requires a blocker report if
verification writes to `data/writing_feedback.db` or cannot prove that every
write-capable test uses a newly created temporary database.

## What happened

The focused persistence/Service selection completed with **174 passed**. Its
outer guard used a newly created fallback path, removed `DATABASE_URL`, set
`DATABASE_PATH` to the fallback database, and forced `LLM_PROVIDER=local`.
However, the development-database SHA-256 guard failed after pytest exited.

No further tests, runtime smoke, full regression, `run.bat --verify`, commit,
or database access was performed after the failed safety gate.

## Direct evidence

| Evidence | Before focused suite | After focused suite |
|---|---|---|
| Path | `A:\EAP Agent Project\writing-feedback-mvp\data\writing_feedback.db` | same |
| Size | 8,298,496 bytes | 8,298,496 bytes |
| Modified UTC | `2026-08-02T01:48:29.0496487Z` | `2026-08-02T03:02:25.8870088Z` |
| SHA-256 | `5575DA268311490300ECFDB3E4A9A689C19F088F111A26D97DF68A347B527291` | `340E0F3739FEFFD3DEF87BB6E711CB6F90A8478E7E18D833C715EDCFAB03AFF4` |

The pre-change and earlier focused invocations had proved the original hash
unchanged. The 174-test invocation reported
`development_database_hash_unchanged=False` and removed its fallback temporary
directory successfully.

The database has not been opened to inspect the mutation and no automatic
restore, copy, migration, truncation, or backup operation has been attempted.

## Static root-cause evidence

The project `.env` defines `DATABASE_URL` (presence checked without printing
its value). `app/config/settings.py:46-52` calls
`load_dotenv(..., override=False)` and gives `DATABASE_URL` precedence over
`DATABASE_PATH`. Removing `DATABASE_URL` from the process therefore allowed
python-dotenv to repopulate it from `.env`.

The focused selection included `tests/test_v095b_router_contract.py`.
`make_prod_app_with_business_routers()` calls `create_app()` without explicit
settings at `tests/test_v095b_router_contract.py:51-56`; multiple tests create a
`TestClient` for that production-mode app. Its lifespan loads default settings
at `app/api/main.py:96-100`, constructs `Database(settings.database_path)`, and
calls `repository.initialize()` at `app/api/main.py:112-117`.

This provides a concrete path by which the `.env` database can be opened for
write despite the shell-level fallback. It is the smallest confirmed isolation
defect; no schema, SQL, repository, Service, API, or UI behavior change is
proposed as a repair.

## Work completed before the stop

- Phase 0 inventory: 86 public methods; all signatures, owners, callers,
  Protocol coverage, SQL fingerprints, and transaction behavior recorded.
- Pre-change fresh database: Migration 12; 33 tables; 17 named indexes; 23
  foreign-key definitions; schema fingerprint
  `9a73c4e1693bcdff441127427eb502f6956c8516ea27d297cea417f779206c31`;
  nine-owner CRUD; integrity `ok`; zero FK violations.
- Targeted baseline: 16 passed; development database unchanged.
- SQLite connection extraction: five focused tests passed.
- Nine aggregate repository modules and explicit 86-method `Database` facade
  implemented in the worktree.
- Static parity: 86 before/after; zero missing/added methods; zero signature,
  delegation, implementation-signature, or SQL-fingerprint drift; no dynamic
  delegation; no facade imports in child repositories; frozen `SCHEMA` and
  migrations unchanged; all 33 tables have one documented owner.
- Post-change fresh database matched the complete pre-change schema, columns,
  indexes, foreign keys, empty state, representative CRUD results, row counts,
  integrity, and FK checks exactly.
- Bounded repository slices passed: System/Configuration 6, Analysis/CALF 2,
  Revision 2, Learner 2, Practice 2, Research 2, Submission 2; facade contract
  3.
- Broader focused selection: 174 passed, but its results are not accepted as a
  safety-valid gate because the development database changed.

## Work not performed

- controlled backend runtime smoke and restart/persistence check;
- full non-live core suite;
- exact `cmd /c "run.bat --verify"`;
- implementation or verification commits;
- final documentation/state/roadmap/changelog updates;
- v0.9.5-E completion report.

## Required decision before continuation

The owner must decide how to handle the already modified development database:

1. accept it as disposable for this stage and authorize continuation without
   restoration; or
2. restore/replace it through an explicitly authorized recovery action.

Any continuation must also authorize a test-only isolation repair that prevents
python-dotenv from rehydrating `.env` during production-mode test builders. The
minimal candidate is to disable `.env` loading for the verification subprocess
while keeping `DATABASE_URL` absent and `DATABASE_PATH` pointed at the asserted
temporary database, then prove the resolved and actually opened path before
running write-capable tests.

No Service dependency narrowing, facade contraction, schema cleanup, Migration
13, SQL change, UI work, or historical-data migration has begun.

## Resolution and continuation evidence

The owner authorized continuation with the modified development database
accepted as disposable and expressly prohibited any further access, repair,
replacement, migration, or write to it. No restoration or compatibility work
was performed.

Every subsequent write-capable run disabled python-dotenv, removed
`DATABASE_URL`, set `DATABASE_PATH` to a fresh path inside a unique temporary
directory, forced `LLM_PROVIDER=local`, printed and asserted the resolved path,
and proved migration 12, 33 tables, `config-v0.9.0`, integrity, foreign keys,
and the expected empty initial state before the test workload.

Accepted continuation results:

- hardened focused suite: 175 passed;
- controlled runtime/restart smoke: PASS;
- full non-live regression: 469 passed, 8 skipped;
- exact `run.bat --verify`: PASS.

After every run, related connections/processes were closed, ports were clean,
and the temporary database/directory was removed. The development database
remained at SHA-256
`340E0F3739FEFFD3DEF87BB6E711CB6F90A8478E7E18D833C715EDCFAB03AFF4`.
v0.9.5-E therefore resumed and completed without broadening scope.
