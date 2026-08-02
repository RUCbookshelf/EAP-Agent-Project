# v0.9.5-E Verification — SQLite Repository Modularization

**Date:** 2026-08-02
**Status:** PASS
**Implementation commit:** `773bd3d`
**Verification commit:** this commit
**Scope:** facade-first repository modularization only

## Outcome

`app.database.repository.Database` remains the explicit 86-method compatibility
facade and `SQLiteRepository = Database` remains available. The facade composes
one shared `SQLiteConnectionManager` and nine aggregate repositories:

| Owner | Public methods |
|---|---:|
| System | 8 |
| Configuration | 7 |
| Analysis | 8 |
| CALF | 5 |
| Revision | 9 |
| Learner | 9 |
| Practice | 23 |
| Research | 6 |
| Submission | 11 |
| **Total** | **86** |

Seventeen cross-aggregate facade methods retain their previous behavior. No
Service dependency narrowing, facade contraction, schema cleanup, Migration
13, API/UI/domain change, or historical-data migration was performed.

Table ownership is unique across all 33 tables:

- System: 2 (`schema_migrations`, `system_versions`);
- Configuration: 2; Analysis: 4; CALF: 3; Revision: 2; Learner: 2;
- Practice: 8; Research: 3; Submission: 7.

Cross-aggregate reads remain owned by the use-case repository recorded in the
machine-readable inventory; none was split across independent transactions.
Services retain their existing constructors and continue to consume the same
`Database` facade or already-existing Protocols. No child repository imports
the facade; dependency direction remains facade → repositories → connection
manager.

## Static and behavioral parity

- Public method surface: 86 before / 86 after; no added or missing methods.
- Public and implementation signatures: no drift.
- Explicit delegation: no dynamic `__getattr__`; no delegation drift.
- SQL fingerprints: no drift; public facade methods contain no SQL.
- Schema and private migration-helper source: unchanged.
- Table ownership: 33/33 tables assigned once.
- Prohibited imports from repositories to Service/API/UI/domain layers: none.
- Service, API, domain, migration, and UI production files: no task diff.
- Fresh pre/post schema fingerprint:
  `9a73c4e1693bcdff441127427eb502f6956c8516ea27d297cea417f779206c31`.
- Fresh pre/post database state: migration 12, 33 tables, 17 named indexes,
  23 foreign-key definitions, active configuration
  `config-v0.9.0`, expected seed rows only, integrity `ok`, zero foreign-key
  violations, and identical representative CRUD results for all nine owners.

## Verification results

| Gate | Result |
|---|---|
| Targeted baseline before extraction | 16 passed |
| Connection extraction | 5 passed |
| Owner-group slices | 18 passed across nine owners |
| Facade contract | 3 passed |
| Hardened focused suite | 175 passed, 2 warnings |
| Controlled runtime smoke | PASS |
| Full non-live regression | **469 passed, 8 skipped, 2 warnings** in 226.97s |
| Exact `cmd /c "run.bat --verify"` | **PASS** |
| Task-scoped whitespace/import/facade-SQL review | PASS |

The runtime smoke used
`C:\tmp\v095e-runtime-eb9bc77c19c24263924641b1c3fa61aa\runtime.db`.
It verified live/ready/health, two submissions and analyses, feedback,
revision, practice, learner profile/progress/Journey, Research review,
restart persistence, migration 12, 33 tables, integrity `ok`, zero foreign-key
violations, and clean shutdown. The temporary directory was removed.

The full regression used
`C:\tmp\v095e-full-9dc0a93a52b142dfb65a4b4776302898\full-regression.db`.
The launcher verification used
`C:\tmp\v095e-runbat-58f6fbc3772a4c3bb338f58033850388\runbat-verify.db`.
Both began in the asserted empty initial state and were removed after clean
process/port checks.

The exact launcher gate additionally proved FastAPI health 200, docs 200,
Streamlit 200, migration 12, 33 tables, active configuration `config-v0.9.0`,
and local-provider operation. The frozen 77 path+method API contract, 52 public
frontend client methods, and 520/520 locale parity remain covered by the full
regression; no API or UI production file changed in this task.

## Development database incident and isolation hardening

An earlier unhardened 174-test invocation changed
`data/writing_feedback.db`. The process-level wrapper had removed
`DATABASE_URL`, but `.env` reintroduced it through python-dotenv during a
production-mode `TestClient` path; settings prioritize `DATABASE_URL` over
`DATABASE_PATH`. The database hash changed from
`5575DA268311490300ECFDB3E4A9A689C19F088F111A26D97DF68A347B527291` to
`340E0F3739FEFFD3DEF87BB6E711CB6F90A8478E7E18D833C715EDCFAB03AFF4`.

The owner accepted the modified development database as disposable and
prohibited further access or writes. Every later write-capable run used a new
temporary directory and enforced all of the following before execution:

- `DATABASE_URL` absent;
- `DATABASE_PATH` resolved to the fresh temporary directory;
- `PYTHON_DOTENV_DISABLED=1` and `LLM_PROVIDER=local`;
- resolved-path assertion excluding the development database and backups;
- migration 12, 33 tables, active configuration, and expected empty initial
  state assertions.

After each run, connections/processes were closed, ports were checked, the
temporary directory was removed, and the development-database SHA-256 was
rechecked. It remained
`340E0F3739FEFFD3DEF87BB6E711CB6F90A8478E7E18D833C715EDCFAB03AFF4`
through the final gates.

## Impact review and limitations

The complete production diff was reviewed by both repository graphs. The
structural graph reported risk 0.55 across 14 changed files. GitNexus reported
critical blast radius because the intentionally stable `connect` and
`initialize` facade paths participate in 29 execution processes. Focused,
schema, runtime-restart, full-regression, and launcher evidence cover that
surface. The graph's untracked-test association produced conservative test-gap
warnings despite the explicit v0.9.5-E tests.

The repository-wide `git diff --check` remains blocked only by pre-existing
trailing whitespace in user-owned `AGENTS.md`; the task-scoped diff is clean
and that file was not modified or staged by v0.9.5-E.

## Decision

v0.9.5-E is complete and verified. Service Dependency Narrowing may begin only
as a separately authorized next task; it was not started here.
