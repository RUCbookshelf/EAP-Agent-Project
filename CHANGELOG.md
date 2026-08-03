## v0.9.5-H2D1-V1 (2026-08-03)

### Changed
- Workspace-safety closure of the H2D1 verification runs: identified and
  removed the exact 11 export directories / 22 files (22,943 bytes) that the
  H2D1 focused and full-core suites generated through the pre-existing
  research-export tests (`run_export` writing to `research_exports/`).
  `research_exports/` restored from 798 to the approved pre-H2D1 baseline of
  776 files with every retained path and SHA-256 unchanged; the root
  directory and all pre-existing exports were preserved.
- Ownership was proven per path with exact classification (content signature,
  fixture match, git-commit-anchored verification window, complete-delta
  accounting); no test rerun, no production/test change, no export-behavior
  change; deletion used an exact allowlist manifest with a passing dry run.
- Added `verification/v0.9.5-h2d1/export_cleanup_before.json`,
  `export_cleanup_candidates.json`, `export_cleanup_after.json`,
  `export_cleanup_closure.json`, and `cleanup_research_exports.py`
  (verification-only tool; not part of application runtime).

### Verified
- Post-cleanup: 776 files / 388 directories; 1,164 retained entries compared
  path-by-path and hash-by-hash with zero differences; ambiguous candidates 0;
  unexpected deletions 0; development database unchanged; ports free.
- v0.9.5-H2D1 is COMPLETE and fully verified. Research-export verification
  side effects: CLEANED. Approved pre-H2D1 export baseline restored.


## v0.9.5-H2D1 (2026-08-03)

### Changed
- Formalized the active `ConfigurationPort` contract in
  `app/services/configuration.py` from a plain structural class to a
  structural `typing.Protocol` (same name, same module, same seven methods,
  not `@runtime_checkable`). Production diff is two lines only: the
  `from typing import Protocol` import and the `(Protocol)` base class.
- Zero runtime behavior change: `ConfigurationService` still resolves its
  `repository` annotation to `ConfigurationPort`; `SQLiteConfigurationRepository`
  still structurally satisfies all seven methods without explicit inheritance;
  application composition, configuration workflows, SQL, transactions, API,
  UI, and localization unchanged. Contract-kind transition: typing.Protocol
  40 -> 41, plain structural 1 -> 0; total/active contracts remain 41;
  runtime-checkable count unchanged (36).
- Added `tests/test_v095h2d1_configuration_port_protocol.py` (13 focused
  tests): Protocol representation, no alias/instantiation/subclass/runtime
  check, signature parity vs the before-state artifact, structural
  satisfaction by deterministic signature inspection, configuration runtime
  flows, and application construction with the same facade-owned Repository.
  Before/after evidence: `verification/v0.9.5-h2d1/configuration_port_before.json`
  and `configuration_port_after.json`.

### Verified
- Focused F2-H2D1 contract suite 230 passed, 2 warnings (isolated DB, local
  provider); exact `run.bat --verify` PASS (migration 12, 33 tables,
  `config-v0.9.0`, prompt `feedback-prompt-v0.7.1`, health/docs/Streamlit
  200); Database public methods 2; API 77; client 52; locale 520/520;
  development database unchanged (SHA-256/size/mtime).
- Full non-live core: **PASS** - one fresh run, exit code 0,
  **696 passed, 8 skipped, 2 warnings** (683 H2C baseline + 13 new H2D1
  tests); zero failed, zero errors, complete collection; the documented
  `test_v095b_router_contract` lifecycle-race flake did not occur. v0.9.5-H2D1
  is COMPLETE and fully verified.


## v0.9.5-H2C (2026-08-03)

### Changed
- Canonicalized the exact duplicate infrastructure reader pair
  `_AnalysisRunReader` (app/infrastructure/sqlite/repositories/revision.py:14
  and learner.py:12) into one shared infrastructure-owned `AnalysisRunReader`
  Protocol in the new module
  `app/infrastructure/sqlite/repositories/contracts.py`; both consumers
  (`SQLiteRevisionRepository`, `SQLiteLearnerRepository`) now import the
  canonical contract and use it for the existing `analysis_reader` constructor
  annotation only. Both former local definitions are removed; no compatibility
  alias exists; `_AnalysisRunReader` is absent from all `app/**` source.
- Zero runtime behavior change: constructor parameter names/order/defaults,
  stored collaborator attributes, concrete Repository identity, connection
  manager, SQL, query order, result ordering, missing-record behavior,
  exceptions, transactions, composition, Services, Routers, APIs, and UI
  unchanged. Active persistence contracts reduced by exactly one (42 -> 41);
  unused legacy contracts remain 0.
- Added `tests/test_v095h2c_analysis_run_reader_contract.py` (14 focused
  tests) and mapped the two historical `_AnalysisRunReader` H1-inventory
  entries to the canonical contract in
  `tests/test_v095h2a_removed_contracts.py` (historical H1/H2A/H2B artifacts
  untouched). Before/after evidence:
  `verification/v0.9.5-h2c/reader_contract_before.json` and
  `reader_contract_after.json`.

### Verified
- Focused F2-H2C contract suite 217 passed, 2 warnings (isolated DB, local
  provider); exact `run.bat --verify` PASS (migration 12, 33 tables,
  `config-v0.9.0`, prompt `feedback-prompt-v0.7.1`, health/docs/Streamlit
  200); Database public methods 2; API 77; client 52; locale 520/520;
  development database unchanged (SHA-256/size/mtime).
- Full non-live core: **PASS** - one fresh run, exit code 0,
  **683 passed, 8 skipped, 2 warnings** (669 H2B baseline + 14 new H2C
  tests); zero failed, zero errors, complete collection; the documented
  `test_v095b_router_contract` lifecycle-race flake did not occur. v0.9.5-H2C
  is COMPLETE and fully verified.


## v0.9.5-H2B (2026-08-03)

### Changed
- Renamed the active local configuration contract `ConfigurationRepository` to
  `ConfigurationPort` in `app/services/configuration.py` (definition +
  `ConfigurationService.__init__` annotation only). The name now matches the
  consumer-owned Port convention and removes the last repository-layer naming
  ambiguity after H2A deleted the stale central `ConfigurationRepository`.
- No method, signature, return annotation, implementation, repository, SQL,
  transaction, migration, API, UI, or runtime dependency changed; no
  compatibility alias or duplicate name remains; the old name is absent from
  all `app/**` source.
- Added `tests/test_v095h2b_configuration_contract_rename.py` (6 focused
  tests) and updated `tests/test_v095h2a_removed_contracts.py` with an
  H1-inventory rename map so the 42-active-contract preservation proof stays
  valid; the E-parity allowlist in the H2A isolation runner now covers the
  H2B-touched file.

### Verified
- Focused contract suite 203 passed, 2 warnings (isolated DB, local
  provider); exact `run.bat --verify` PASS (migration 12, 33 tables,
  `config-v0.9.0`, prompt `feedback-prompt-v0.7.1`, health/docs/Streamlit
  200); Database public methods 2; API 77; client 52; locale 520/520;
  development database unchanged (SHA-256/size/mtime).
- Full non-live core: **PASS** - v0.9.5-H2B-V1 closure run exit code 0,
  669 passed, 8 skipped, 2 warnings (the two prior attempts each exited 1
  with exactly one failure, both instances of the documented pre-existing
  `test_v095b_router_contract` lifecycle-race flake, which passes in
  isolation and in the closure run). v0.9.5-H2B is COMPLETE and fully
  verified.



### Removed
- Exactly the 13 persistence contracts proven unused by the v0.9.5-H1 audit:
  the legacy `SubmissionRepository` combined class (`app/services/submission.py`),
  the 11 stale central Protocols (`StudentRepository`, `EssayRepository`,
  `MetricRepository`, `ErrorAnnotationRepository`, `DiagnosisRepository`,
  `FeedbackRepository`, `ExerciseRepository`, `LearnerHistoryRepository`,
  `LearnerProfileRepository`, central `ConfigurationRepository`,
  `SystemVersionRepository`), and the `SubmissionRepositories` typing union
  alias (`app/repositories/protocols.py`), plus their obsolete imports,
  bases, docstrings, re-exports, and `__all__` entries
  (`app/repositories/__init__.py` now exports only `RevisionRepository`).
- No replacement contract was introduced; no active contract (42 A/B/C),
  Repository implementation, Service constructor, Router dependency,
  composition path, SQL, transaction, API, schema, prompt, provider, UI, or
  localization file changed. The Configuration same-name collision is
  resolved only through stale central-contract removal; the active local
  7-method `ConfigurationRepository` is untouched.

### Added
- `tests/test_v095h2a_removed_contracts.py` (10 focused tests: removed names
  absent, re-exports absent, no source import of a removed name, all 42
  H1-active contracts defined with exact method sets, concrete Repositories
  still satisfy active contracts, SubmissionService's four F6C Ports,
  local ConfigurationRepository unchanged, Practice read/write separation
  unchanged, API-owned Ports unchanged).
- `docs/development/V0.9.5_H2A_SPEC.md`, `RUN_VERIFICATION_V0.9.5_H2A.md`,
  and `verification/v0.9.5-h2a/` artifacts (removal manifest, remaining
  contract inventory, isolated pytest runner).

### Verified
- Focused contract suite 197 passed, 2 warnings (isolated DB, local
  provider); full non-live core 663 passed + 8 skipped, 2 warnings, exit
  code 0 (closure run; the original H2A full-core run exited 1 on the
  documented pre-existing `test_v095b_router_contract` lifecycle-race flake,
  which passes in isolation and in the closure run); exact
  `run.bat --verify` PASS (migration 12, 33 tables,
  `config-v0.9.0`, prompt `feedback-prompt-v0.7.1`, health/docs/Streamlit
  200); Database public methods 2; API 77; client 52; locale 520/520;
  development database unchanged (SHA-256/size/mtime).

## v0.9.5-H1 (2026-08-03)

### Added
- Read-only persistence-Protocol inventory and consolidation plan: 55
  contracts inventoried (52 Protocols, 1 union alias, 1 plain structural
  class, 1 legacy combined class) with consumer and implementation matrices,
  method-level overlap matrix (29 methods), 3 same-name collisions, and a
  5-unit H2 implementation plan; artifacts under `verification/v0.9.5-h1/`
  and `docs/development/PROTOCOL_CONSOLIDATION_AUDIT_V0.9.5_H1.md`.
- Confirmed the legacy `SubmissionRepository` and 11 stale central Protocols
  plus the `SubmissionRepositories` alias have no production consumer
  (H2A removal candidates); confirmed the central `ConfigurationRepository`
  (ping/migration_version) is stale while the local 7-method contract is
  authoritative for `ConfigurationService`; confirmed the ten API-owned Ports
  are exact but test-referenced only; confirmed Practice read/write Ports
  must stay separate; confirmed `_AnalysisRunReader` is an exact
  infrastructure duplicate pair.

### Verified
- Focused F2-F6D+G Protocol/Port contract tests 187 passed, 2 warnings under
  an isolated temporary database; all JSON artifacts parse and reconcile; no
  production or test file changed; development database unchanged
  (SHA-256/size/mtime). H2 implementation remains unauthorized.

## v0.9.5-G (2026-08-03)

### Changed
- Contracted the `Database` public facade from 86 methods to the
  evidence-supported infrastructure surface (`connect`, `initialize`);
  removed all 84 business-delegation methods, each recorded in the exact G
  removal ledger with a replacement access path (facade-owned aggregate
  Repository or an exact API Port) or a zero-caller proof. `Database`
  continues owning one `SQLiteConnectionManager` and one Repository graph.
- Migrated all remaining production broad-facade callers: zero
  `Depends(get_repository)` in production Routers (analysis, calf, research,
  revisions, students, submissions, system now use ten exact API-owned Ports
  from new `app/api/ports.py` composed on app state with narrow dependency
  accessors); `require_student` uses the new `StudentLookupPort`; main.py
  lifecycle and FeedbackPipeline use facade-owned aggregate Repositories;
  Research export-job best-effort behavior preserved.
- Removed the `SQLiteRepository = Database` alias and its export
  (`app/database/__init__.py` now exports `Database`,
  `LATEST_MIGRATION_VERSION`, `rollback`, `upgrade`); operational scripts,
  verification helpers, and ~24 test files migrated from broad-facade
  convenience to facade-owned aggregate Repositories; the v0.9.5-E parity
  verification updated to the G-era contract (historical E inventory JSON
  preserved unchanged).
- No Repository implementation, SQL, DDL, migration, transaction boundary,
  API contract, schema, prompt, provider, UI, or localization change;
  transaction-preservation matrix (Submission independent commits, Revision
  three-commit workflow, Admin partial commits, Practice Attempt-first/
  Evaluation-best-effort, Research best-effort, learner atomicity, CALF
  guards) verified unchanged.
- Added 15 focused G facade-contraction tests, the G isolation runner, the
  G SPEC/verification documentation, the removal ledger, and the before/after
  facade inventory.

### Verified
- Focused G set 437 PASS; full non-live core 653 passed + 8 skipped; exact
  `run.bat --verify` PASS (migration 12, 33 tables, `config-v0.9.0`, prompt
  v0.7.1, health/docs/Streamlit 200); API 77; client 52; locale 520/520;
  Database public methods 2; development database unchanged
  (SHA-256/size/mtime).

## v0.9.5-F6D (2026-08-02)

### Changed
- Narrowed the Practice Router persistence boundary: removed every active
  `Depends(get_repository)` dependency on the broad `Database` facade and
  replaced it with three consumer-owned Ports (`PracticeSubmissionReadPort`
  one Submission read, `PracticeReadPort` seven Practice reads,
  `PracticeWritePort` four Practice writes) defined in new
  `app/practice/ports.py`; the same facade-owned `SQLitePracticeRepository`
  satisfies the read and write Ports.
- Removed the dormant Repository dependency from `PracticeService`
  (constructor now `PracticeService()`); it remains a pure domain service.
  Both application paths compose facade-owned Submission/Practice (and the
  Learner reader backing the preserved `require_student` guard) plus the pure
  Service on `app.state`; five narrow application-state dependency accessors
  were added to `app/api/deps.py`.
- Router ownership of the Attempt-first/Evaluation-best-effort orchestration
  is unchanged: Attempt persists once and independently before Evaluation;
  any Evaluation failure leaves the committed Attempt authoritative with
  `evaluation: None`; no compensation, retry, or shared transaction. All
  eight Practice endpoints, schemas, status codes, domain calculations, and
  error behavior are unchanged; no new Practice writer workflow was added.
- Added 20 focused F6D Port/identity/Router/transaction tests, the F6D
  isolated pytest runner, and the F6D SPEC/verification documentation.

### Verified
- Focused F6D set 187 PASS; accumulated architecture contracts 253 PASS
  (F2-F6C + F6D, E parity 86/33, API 77, client 52, locale 520/520); full
  non-live core 638 passed + 8 skipped; exact `run.bat --verify` PASS
  (migration 12, 33 tables, `config-v0.9.0`, prompt v0.7.1,
  health/docs/Streamlit 200); development database unchanged
  (SHA-256/size/mtime).

## v0.9.5-F6C (2026-08-02)

### Changed
- Narrowed `SubmissionService` persistence dependencies: removed the broad,
  inherited `SubmissionRepository` constructor dependency and replaced it
  with four owner-aligned consumer-owned Ports (`SubmissionSystemPort`,
  `SubmissionDataPort`, `SubmissionAnalysisPort`,
  `SubmissionCalibrationPort`); the legacy `SubmissionRepository`
  declaration remains only as Protocol-consolidation debt and is not used by
  active composition.
- Removed both CALF persistence `hasattr` capability guards; the facade-owned
  `SQLiteCalfRepository` always supplies the capabilities. The eleven direct
  persistence calls route to approved owners (System 1, Submission 5,
  Analysis 3, CALF 2); `build_submission_service` now takes seven required
  keyword-only facade-owned repositories (no broad-facade fallback); both
  application paths, FeedbackPipeline legacy composition, and all active
  operational/test callers pass the existing facade-owned instances (same
  connection manager, one repository graph).
- Constructor `record_versions` timing/arguments, submit and
  regenerate-feedback call order, write counts, Repository-owned multi-table
  operations, learner/Revision/Admin collaborator boundaries, and
  partial-commit behavior are unchanged; no Repository implementation, SQL,
  transaction, API, schema, domain, prompt, provider, or UI change.
- Added 29 focused F6C contract/behavior tests, the F6C isolated pytest
  runner, and the F6C SPEC/verification documentation.

### Verified
- Focused F6C set 282 PASS; accumulated architecture contracts 233 PASS
  (F2-F6B + F6C, E parity 86/33, API 77, client 52, locale 520/520); full
  non-live core 618 passed + 8 skipped; exact `run.bat --verify` PASS
  (migration 12, 33 tables, `config-v0.9.0`, prompt v0.7.1,
  health/docs/Streamlit 200); development database unchanged
  (SHA-256/size/mtime).

## v0.9.5-F6B (2026-08-02)

### Changed
- Narrowed `AdminReanalysisService` persistence dependencies: removed the
  broad, untyped `repository` parameter and replaced it with three
  consumer-owned structural Ports (`AdminConfigurationReadPort`,
  `AdminSubmissionReadPort`, `AdminAnalysisPort`) plus the unchanged central
  `RevisionRepository` (`revision_repository`, required keyword-only).
- The six direct persistence calls route to approved owners
  (`get_configuration` -> Configuration reader; `get_submission_bundle` /
  `list_student_submissions` -> Submission reader; `get_analysis_run` /
  `save_analysis_run` -> Analysis repository; `get_revision_group` ->
  existing RevisionRepository); both application-construction paths pass the
  existing facade-owned repository instances (same connection manager, one
  repository graph); no Repository implementation, SQL, transaction
  boundary, API, schema, domain rule, prompt, provider, or UI behavior
  changed.
- `ConfigurationService.active()`, `SubmissionService.regenerate_feedback`,
  and the embedded `RevisionService` collaborations are unchanged; preview
  remains read-only; Analysis write count/order, feedback conditions, and
  partial-commit behavior are preserved.
- Added 16 focused F6B contract/behavior tests, the F6B isolated pytest
  runner, and the F6B SPEC/verification documentation.

### Verified
- Focused F6B set 154 PASS; accumulated architecture contracts 204 PASS
  (F2-F6A + F6B, E parity 86/33, API 77, client 52, locale 520/520); full
  non-live core 589 passed + 8 skipped; exact `run.bat --verify` PASS
  (migration 12, 33 tables, `config-v0.9.0`, prompt v0.7.1,
  health/docs/Streamlit 200); development database unchanged
  (SHA-256/size/mtime).

## v0.9.5-F6A (2026-08-02)

### Changed
- Replaced the broad `Database` facade runtime repository of
  `RevisionService` with the existing facade-owned `SQLiteRevisionRepository`
  instance at every active direct and indirect construction path: both
  application-construction paths, `build_submission_service` (new required
  keyword-only `revision_repository` input), `AdminReanalysisService`
  (new required keyword-only `revision_repository` injection for its
  embedded Revision composition), and the legacy `FeedbackPipeline`
  composition line. Operational callers (demo and live-verification
  scripts, the E capture helper) and relevant tests received
  constructor/factory-argument-only updates.
- No new Revision Port, no `RevisionService` fallback, no Protocol change,
  and no repository, SQL, or transaction change; `RevisionService` remains
  typed against the unchanged central `RevisionRepository`. The
  three-sequential-commit relationship workflow and Essay-update ownership
  are preserved. F6A0 (`693ff48`/`b4d37af`) remains the completed
  capability prerequisite and resolved the original blocker.
- Added 14 focused F6A runtime tests, the F6A isolated pytest runner, and
  the F6A SPEC/verification documentation.

### Verified
- Focused F6A set 155 PASS; accumulated architecture contracts 188 PASS
  (F2-F6A0, E parity 86/33, API 77, client 52, locale 520/520); full
  non-live core 573 passed + 8 skipped; exact `run.bat --verify` PASS
  (migration 12, 33 tables, `config-v0.9.0`, prompt v0.7.1,
  health/docs/Streamlit 200); development database unchanged
  (SHA-256/size/mtime).

## v0.9.5-F6A0 (2026-08-02)

### Changed
- Completed the facade-owned Revision repository capabilities: the
  existing `SQLiteRevisionRepository` now exposes `get_submission_bundle`
  and `get_latest_analysis_run` as direct delegations to its injected
  readers and is wired by the `Database` facade with the existing
  facade-owned Submission and Analysis repository instances (same
  connection manager, one repository graph). The central
  `RevisionRepository` Protocol, `RevisionService`, all construction
  sites, Revision write methods, SQL, and transaction boundaries are
  unchanged; this is the capability prerequisite for the still-blocked
  v0.9.5-F6A runtime narrowing.
- Added 13 focused F6A0 contract tests, the F6A0 isolated pytest runner,
  and the F6A0 SPEC/verification documentation; the F6A blocker report
  records the owner-authorized Option C resolution.

### Verified
- Focused F6A0 set 53 PASS; accumulated architecture contracts 161 PASS
  (F2-F5B, E parity 86/33, API 77, client 52, locale 520/520); full
  non-live core 559 passed + 8 skipped; exact `run.bat --verify` PASS
  (migration 12, 33 tables, `config-v0.9.0`, prompt v0.7.1,
  health/docs/Streamlit 200); development database unchanged
  (SHA-256/size/mtime).

## v0.9.5-F5B (2026-08-02)

### Changed
- Replaced the broad, untyped persistence dependency of
  `ResearchDataService` with three explicit consumer-owned
  `typing.Protocol` Ports defined in `app/research/service.py`:
  `ResearchSubmissionReadPort` (`list_all_submissions`,
  `list_student_submissions`, `get_submission_bundle`),
  `ResearchReviewPort` (`save_human_review`, `list_human_reviews`,
  `apply_pii_review`), and `ResearchExportReadPort` (`list_export_jobs`,
  `get_export_job`). Removed all six repository-capability `hasattr`
  branches associated with the eight approved methods; the Service now
  has no broad repository field, no untyped persistence parameter, no
  compatibility fallback, and no `Database`/SQLite imports.
- Both application-construction paths (`_run_startup`, `_build_full_app`)
  construct `ResearchDataService` with explicit keyword arguments from
  the existing facade-owned `SQLiteSubmissionRepository` and the same
  `SQLiteResearchRepository` instance (both Research-owned Ports share
  one instance and one connection manager; no second Database or
  repository graph). `tests/test_research_v082.py` (five sites) and
  `verification/v0.9.5-e/capture_prechange_fresh_database.py` (one site)
  received constructor-only updates.
- Router-level best-effort `save_export_job` persistence is unchanged:
  `ResearchDataService.run_export` still never writes Export Job rows;
  the Research router still attempts the best-effort audit-row write
  after a successful export.
- Added 20 focused F5B contract tests, the F5B isolated pytest runner,
  and the F5B SPEC/verification documentation.
- Preserved public Service methods, export contents/ordering/file names/
  formats, API paths/schemas, repository SQL, transactions, migration 12,
  33 tables, `config-v0.9.0`, prompt `feedback-prompt-v0.7.1`, facade 86
  methods, client 52 methods, and locale 520/520.

### Verified
- Focused F5B set 97 PASS; frozen-contract inventory 141 PASS; full
  non-live core 546 passed + 8 skipped; exact `run.bat --verify` PASS
  (migration 12, 33 tables, `config-v0.9.0`, prompt v0.7.1,
  health/docs/Streamlit 200); development database unchanged
  (SHA-256/size/mtime); all 235 pre-existing user exports untouched.

## v0.9.5-F5A (2026-08-02)

### Changed
- Replaced the broad, untyped persistence dependency of `CalfService`
  with four explicit consumer-owned `typing.Protocol` Ports defined in
  `app/services/calf.py`: `CalfDataPort` (`list_analysis_units`,
  `list_error_annotations`, `save_error_annotations`),
  `CalfSubmissionReadPort` (`get_submission_bundle`,
  `list_student_submissions`), `CalfAnalysisReadPort`
  (`get_latest_analysis_run`), and `CalfStudentReadPort` (`get_student`).
  The Service now has no broad repository field, no untyped persistence
  parameter, no compatibility fallback, no `hasattr` capability
  discovery, and no `Database`/SQLite imports.
- Both application-construction paths (`_run_startup`, `_build_full_app`)
  construct `CalfService` with explicit keyword arguments from the
  existing facade-owned `SQLiteCalfRepository`,
  `SQLiteSubmissionRepository`, `SQLiteAnalysisRepository`, and
  `SQLiteLearnerRepository` instances (same connection-manager graph; no
  second Database or repository graph). `scripts/verify_live_deepseek_v08.py`
  received the one minimal constructor-only operational-caller update.
- `save_error_annotations` remains exactly one repository-owned call with
  the Essay-existence guard inside `SQLiteCalfRepository`; no shared
  transaction is introduced.
- Added 18 focused F5A contract tests, the F5A isolated pytest runner,
  and the F5A SPEC/verification documentation.
- Preserved public Service methods, API paths/schemas, repository SQL,
  transactions, migration 12, 33 tables, `config-v0.9.0`, facade 86
  methods, client 52 methods, and locale 520/520.

### Verified
- Focused F5A set 63 PASS; frozen-contract inventory 123 PASS; full
  non-live core 526 passed + 8 skipped; exact `run.bat --verify` PASS
  (migration 12, 33 tables, `config-v0.9.0`, health/docs/Streamlit 200);
  development database unchanged (SHA-256/mtime).

## v0.9.5-F4 (2026-08-02)

### Changed
- Narrowed two more Service dependencies with consumer-owned Ports:
  `ReanalysisService` now depends on `SubmissionBundleReadPort`
  (`get_submission_bundle`) plus `AnalysisRunWritePort`
  (`save_analysis_run`); `JourneyService` now depends on
  `JourneyStudentReadPort` (`get_student`) plus the eight-method
  `JourneyProjectionReadPort`. Both Services no longer import or type
  against `Database`, concrete SQLite repositories, or any broad
  repository annotation.
- Both application-construction paths compose the two Services from the
  existing facade-owned `SQLiteSubmissionRepository`,
  `SQLiteAnalysisRepository`, `SQLiteLearnerRepository`, and
  `SQLitePracticeRepository` instances. JourneyService is stored on
  `app.state.journey_service` and exposed through the narrow
  `get_journey_service` API dependency; the Journey router no longer
  constructs the Service from the facade. `scripts/demo_journey.py`
  received the owner-authorized two-line operational-script exception.
- Added 17 focused F4 contract tests, the F4 isolated pytest runner, and
  the F4 SPEC/blocker-resolution/verification documentation.
- Preserved public Service methods, API paths/schemas, repository SQL,
  transactions, migration 12, 33 tables, `config-v0.9.0`, facade 86
  methods, client 52 methods, and locale 520/520.

### Verified
- Focused F4 set 118 PASS; frozen-contract inventory 84 PASS; full
  non-live core 508 passed + 8 skipped; exact `run.bat --verify` PASS
  (migration 12, 33 tables, `config-v0.9.0`, health/docs/Streamlit 200);
  development database unchanged (SHA-256/mtime).

## v0.9.5-F3 (2026-08-02)

### Changed
- Narrowed the Learner read-model chain to consumer-owned Ports:
  `ProgressService` now depends on `LearnerProgressPort` and
  `ActiveConfigurationPort`; `LearnerProfileService` depends on
  `LearnerProfileReadPort` plus an injected `ProgressService`;
  `DashboardService` depends on `DashboardReadPort` plus an injected
  `ProgressService`. The inactive `list_longitudinal_records` fallback and the
  relevant `hasattr` capability discovery were removed only from
  `ProgressService`; no facade or repository method was deleted.
- Both application-construction paths, `build_submission_service`, and the
  legacy `FeedbackPipeline` now compose the three Services explicitly from the
  existing facade-owned `SQLiteLearnerRepository` and
  `SQLiteConfigurationRepository` instances. `FeedbackPipeline` composition is
  the single production-file exception explicitly authorized for this stage.
- Added 12 focused F3 contract tests, the F3 isolated pytest runner, and the
  F3 SPEC/blocker-resolution/verification documentation.
- Preserved public Service methods, API paths/schemas, repository SQL,
  transactions, migration 12, 33 tables, `config-v0.9.0`, facade 86 methods,
  client 52 methods, and locale 520/520.

### Verified
- Focused F3 set 96 PASS; frozen-contract inventory 36 PASS; full non-live
  core 492 passed + 8 skipped; exact `run.bat --verify` PASS (migration 12,
  33 tables, `config-v0.9.0`, health/docs/Streamlit 200); development
  database unchanged (SHA-256/mtime).

## v0.9.5-F2 (2026-08-02)

### Changed
- Narrowed exactly two Service dependencies without behavior change:
  `ConfigurationService` now receives the existing `SQLiteConfigurationRepository`
  instance composed by the `Database` facade (both application-construction
  paths), and `LearnerHistoryService` now declares a consumer-owned one-method
  `PriorRecordsPort` instead of the broader central `LearnerHistoryRepository`.
- Added the one-method `PriorRecordsPort` in `app/learner/history.py` and the
  focused F2 contract test file; the v0.9.5-E static parity script gained a
  default-off `SERVICE_API_DIFF_ALLOWLIST` so its unchanged parity test can
  run under the F2-approved composition change.
- Preserved public Service names/methods, constructor compatibility, API
  paths/schemas, repository SQL, transactions, migration 12, 33 tables, and
  `config-v0.9.0`.

### Verified
- 53 focused tests PASS (11 new); full non-live core 480 passed + 8 skipped;
  exact `run.bat --verify` PASS (migration 12, 33 tables, `config-v0.9.0`,
  health/docs/Streamlit 200); API 77 pairs, client 52 methods, locale 520/520;
  development database unchanged (SHA-256/mtime).

## v0.9.5-E (2026-08-02)

### Changed
- Replaced the monolithic SQLite repository implementation with one shared
  connection manager and nine aggregate-owned repository modules behind the
  unchanged explicit 86-method `Database` facade.
- Preserved public imports, signatures, SQL/schema behavior, return shapes,
  transactions, IDs, migration 12, 33 tables, and `config-v0.9.0`.
- Added machine-readable pre/post inventories, parity checks, isolated database
  guards, focused facade tests, and a restart/persistence runtime smoke.

### Verified
- Static/signature/delegation/SQL/schema/CRUD parity PASS; 175 focused tests.
- Runtime smoke PASS; full suite 469 passed + 8 skipped; exact
  `run.bat --verify` PASS; all accepted write-capable evidence used fresh
  temporary databases and left no processes or ports.
- Disclosed the earlier development-database incident and hardened all later
  runs against `.env` rehydration; the accepted disposable database was not
  changed again.

## v0.9.5-D (2026-08-02)

### Changed
- Defined twelve narrow feature-owned `typing.Protocol` API Ports under
  `app/ui/ports/` (six Student, six Research); each feature is annotated only
  with its own Port, and `WritingFeedbackApiClient` remains the sole concrete
  HTTP client (structural conformance, unchanged method bodies).
- Created a machine-readable Endpoint-Client-Feature ownership contract
  (`tests/contracts/api_surface_contract.py`) classifying all 77 endpoint
  contracts and all 52 public client methods, with documented reasons for
  intentionally unwrapped endpoints and retained-but-unused methods.
- Hardened Practice and Research UI-safe contracts with backend-parity tests.
- Migrated repository tests from facade private-helper imports to
  feature-owner modules; compatibility exports retained and deprecated in
  comments; a static test prohibits new facade private-helper imports.

### Verified
- Port contracts: 12/12 Ports, feature calls == Port methods, no unused Port
  methods, no cross-feature method gains, signatures compatible with the
  concrete client.
- Endpoint contract: 24 wrapped+used, 27 wrapped+unused, 26 intentionally
  unwrapped (22 business + 4 docs); client methods: 24 used, 27 retained, 1
  obsolete candidate (`lifecycle_state`).
- 19 new contract/parity tests; focused frontend set 220+3; 4/4 representative
  browser renders; 465+8 core tests; exact `cmd /c "run.bat --verify"` PASS;
  migration 12; `config-v0.9.0`; locale parity 520/520; dev DB unchanged.
## v0.9.5-C (2026-08-02)

### Changed
- Extracted the six Student features and six Research features out of
  `app/ui/pages/student_pages.py` and `app/ui/pages/research_pages.py` into
  one module per visible page under `app/ui/features/student/` and
  `app/ui/features/research/`; the old page modules are now thin explicit
  re-export facades with unchanged renderer names and signatures.
- Removed the two UI-to-backend-schema boundary violations: Student Practice
  now uses the UI-safe `app/ui/contracts/practice.py` instruction contract,
  and Research Data builds its export payload with
  `app/ui/contracts/research.py` (exact backend serialization shape).
- Added a static prohibited-UI-import architecture test and extraction
  compatibility tests.

### Verified
- Contract inventory parity: renderers 13/13, definitions 32/32, API calls
  24/24, write-capable calls 7/7, session keys 6/6, widget keys 32/32,
  locale keys 98/98; zero missing/added.
- 15 new boundary/extraction tests; 200+3 focused frontend set; 24/24
  representative browser renders (en desktop + zh mobile); 446+8 core tests;
  exact `cmd /c "run.bat --verify"` PASS; migration 12; `config-v0.9.0`;
  dev database fingerprint unchanged; locale parity 520/520.
## v0.9.5-B (2026-08-02)

### Changed
- Split the centralized FastAPI business-route registration into feature-owned
  router modules under `app/api/routers/` (system, submissions, analysis,
  students, revisions, practice, journey, research, calf, admin); `app/api/main.py`
  is now an application composition root.
- `/api/v1/system/health` now has exactly one canonical lifecycle-based handler
  with identical production/test semantics; the duplicate business health handler
  and the unreachable duplicate lifecycle-route block in `create_app` were removed.
- Production and test builders now populate the same lifecycle analyzer/NLP
  facts, fixing production health reporting of the spaCy model.

### Verified
- Route inventory parity: 77 unique path+method pairs before and after; zero
  missing/added endpoints; no duplicate path+method; operation IDs unchanged.
- 274 passed + 3 skipped focused API tests; 431 passed + 8 skipped core tests
  (+10 new contract tests); minimal runtime smoke PASS; exact
  `cmd /c "run.bat --verify"` PASS; migration 12; `config-v0.9.0`.
## v0.9.4-B (2026-08-01)

### Added
- Shared Student presentation primitives for page purpose, task steps, learner
  context, and one clearly ranked action.
- Focused verification for all six Student pages and one isolated cross-page
  write flow; 520/520 English/Chinese locale parity.

### Changed
- Redesigned Home, Writing, Feedback, Practice, Revision, and Learning Journey
  around learner context, current task, evidence, next action, and explicit
  limits. Student content width is 720px with mobile control stacking and
  44px touch targets.
- Accessible focus token updated to 3px `#0f6dbd` (5.33:1 on white, 4.84:1
  on the surface, 3.16:1 on the dark boundary).
- Legacy v0.9.2.1 Playwright isolation now respects `DATABASE_PATH` and the
  current focus-token contract.

### Verified
- 95 passed + 1 skipped affected tests; 130 passed + 2 skipped Student
  regression; 421 passed + 8 skipped core tests.
- Controlled cross-page flow PASS; 24/24 required Student renders; 6/6
  required Research smoke renders; legacy Playwright PASS; lifecycle and
  exact `cmd /c "run.bat --verify"` PASS.
- Migration 12, `config-v0.9.0`, Research IA, API/schema/domain contracts, and
  read-time Journey semantics unchanged.

## v0.9.4-A (2026-08-01)

### Added
- Hybrid Pixel System 2.0 foundation: canonical `DESIGN_TOKENS` in
  `app/ui/pixel_art.py` with generated CSS; Streamlit theme
  (`.streamlit/config.toml`) aligned via parity tests.
- Readable local/system sans body stack; monospace constrained to
  technical/brand roles; shared spacing, geometry, focus, semantic status,
  density, and responsive tokens.
- Local accessible SVG icon primitive (`app/ui/pixel_art.py::icon`).
- Shared primitives in `app/ui/components.py`: `field_error`, `loading_box`,
  `data_table`, `technical_caption`, `validate_writing_form`; stable
  `data-testid` attributes on existing notices/badges/empty states.
- 80 new tests (`tests/test_design_tokens_v094a.py`,
  `tests/test_hybrid_components_v094a.py`) and
  `scripts/design_system_audit_v094a.py`.

### Changed
- Primary action red `#ff004d` → `#e00047` (measured 4.93:1 white-on-red for
  normal/hover/active); `#ff004d` retained as decorative non-text accent.
- Writing page blocks empty Writing prompts with a localized field error
  before the API call (server validation and payloads unchanged).
- Research Data: "Target ID" and "Export:" success prefix routed through
  locale keys; Run Export shows a loading state; Learning Process Journey
  counts render as a compact table.
- Repaired: `render_research_overview` undefined `exc`; CSS selectors
  updated for the Streamlit 1.60 DOM (buttons carry `data-testid`, tabs are
  `[role="tab"]`, radios use `stRadioGroup`).

### Verified
- 394 passed, 8 skipped (core, excluding live); live A–G 20 passed; legacy
  Playwright suites PASS; lifecycle PASS; `run.bat --verify` PASS; focused
  zh-navigation probe 3/3; representative suite 24/24; final acceptance
  matrix 48/48 renders.
- Migration 12 and config-v0.9.0 unchanged.

## v0.9.3-C (2026-08-01)

### Fixed
- UX-001: Learning Journey no longer appears permanently empty. Journey
  events are derived at read time from authoritative source records
  (app/journey/service.py); every event maps to a real record and no event is
  created by page rendering, navigation, locale switching, or refresh.
- DATA-001: empty-state messages are now accurate per missing record type
  (learner not found, no submissions, no analysis, gate-suppressed priority,
  no practice target, no attempt, no evaluation, no revision, no response
  observation); errors are never shown as empty states.
- UX-003: Student ID is normalized and shared across Student pages; switching
  learners clears learner-scoped state.
- ERR-003: Journey/Practice fetches show a loading state.
- Practice Evaluation flow was unwired (service/repository existed, no API/UI
  caller); valid attempts are now evaluated with the existing conservative
  rule-based evaluator and persisted.

### Added
- Journey event semantic contract with stable types, source traceability,
  deduplication keys, event versioning, and conservative limitations.
- GET /api/v1/students/{student_id}/journey; read-only practice endpoints
  (exercises by target, attempts by exercise).
- Deterministic demo journey: `python scripts/demo_journey.py
  --setup|--status|--cleanup` for synthetic learner DEMO-001 (idempotent,
  scoped cleanup, local provider only, DB backup before setup).
- 28 journey tests (tests/test_journey_v093c.py).

### Changed
- Student Home derives latest status/next action from the journey endpoint
  (replaces the empty engagement-trace dependency).
- Research Learning Process shows the journey trace with source IDs.
- Locale keys: 368 en/zh_CN parity (journey + practice states).

### Notes
- No schema change; migration stays 12; config-v0.9.0 unchanged.
- FeedbackEngagementTrace retained but not written by the journey; page
  display is never engagement.
- No mastery/learning-gain/causal/transfer/proficiency/CEFR claim is created.

## v0.9.3-B (2026-07-31)

### Fixed
- ERR-001: all eight broken Research endpoints repaired. Missing service
  methods (apply_pii_review), missing repository persistence (save_human_review,
  list_human_reviews), route ordering (export/history shadowed by /{export_id}),
  and missing routes (dataset-split, export manifest) restored.
- ERR-002: generic API-unavailable mapping replaced by a canonical error
  taxonomy (app/errors.py) with 14 stable categories, message keys, HTTP
  statuses, and retryability flags.
- PERF-001: centralized timeout profiles (connect 2s, read 10s, write 30s,
  long-read 60s, lifecycle 5s); no unclassified long wait remains.
- Request correlation: X-Request-ID generated/propagated, added to response
  headers and canonical error bodies, and logged in sanitized request lines.

### Added
- Canonical error model app/errors.py (ApiError, ErrorCategory).
- Server-side exception mapping (validation, not-found, conflict, privacy,
  degraded, internal) with request IDs.
- Client-side classification (connect/read timeout, refused, interrupted,
  4xx/5xx, malformed response) in app/ui/api_client.py.
- Bounded safe retry: GET-only, at most 1 retry, retryable categories only;
  state-changing writes never auto-retried.
- Role-appropriate error presentation (render_api_error): Student plain
  language + Retry only when safe; Research shows category/operation/request
  ID/status/retryable/detail.
- 24 new locale keys (en + zh_CN; 295 keys each, parity preserved).
- Research Data: export history, manifest, status, dataset split, PII review,
  human review persistence all working through real HTTP.
- 25 new tests in tests/test_request_reliability_v093b.py.
- TestLiveG_MobileViewport updated to the v0.9.1+ role-based navigation.

### Backend
- Migration 12 preserved; config-v0.9.0 preserved.
- No CALF/diagnosis/practice/learner-model/privacy/dataset-split semantics changed.
- pytest: 314 passed, 8 skipped; Cases A-R: 110 passed.

## v0.9.3-A (2026-07-31)

### Fixed
- REL-001: Intermittent FastAPI startup hang eliminated. Heavy initialization
  (spaCy, database, services) moved from module-level import to FastAPI lifespan
  context manager. Server now responds to liveness checks immediately.
- API client timeout reduced from 90s to 15s for faster failure detection.

### Added
- Service lifecycle model (app/lifecycle.py): ServiceState enum, ServiceLifecycle
  thread-safe singleton with stage timing and sanitized health info.
- Liveness endpoint: GET /api/v1/system/live -- confirms process is alive.
- Readiness endpoint: GET /api/v1/system/ready -- confirms all required deps available.
- Stale process cleanup in run_local.py (kill_port_processes).
- Lifecycle-aware Streamlit UI: distinguishes API starting from unavailable.
- New locale keys: app_api_starting, app_api_failed (en + zh_CN).

### Changed
- app/api/main.py: create_app() uses FastAPI lifespan for production mode.
  Backward-compatible with tests via optional settings/repository parameters.
- scripts/run_local.py: bounded readiness polling with 60s deadline.
- scripts/service_processes.py: added kill_port_processes().
- app/ui/api_client.py: timeout 90s -> 15s; added live(), ready(), lifecycle_state().
- Health endpoint enhanced with lifecycle_state and startup_elapsed_ms.

### Backend
- Migration 12 preserved. Active configuration config-v0.9.0 preserved.
- All existing backend behavior unchanged after readiness is reached.
- pytest: 289 passed, 8 skipped (baseline: 271 passed, 8 skipped).
﻿
## v0.9.2.1 (2026-07-31)

### Added
- Playwright 1.61.0 + Chromium 149 browser testing dependency
- Comprehensive v0.9.2.1 Playwright verification suite (4 locale/viewport
  combos, 12 pages, console/overflow/focus/styles/role-separation/screenshots)
- Static Pixel Art style audit script (scripts/pixel_art_style_audit.py)
- Pixel Art design system reference (docs/design/PIXEL_ART_DESIGN_SYSTEM.md)
- v0.9.2.1 specification (docs/development/V0.9.2.1_SPEC.md)
- 13 deterministic screenshots at verification/screenshots/v0.9.2.1/

### Fixed
- Role-separation: global header no longer exposes analyzer version and
  provider details to Student View
- Navigation: sidebar page labels fully localized (en + zh_CN) via locale
  system; no English leakage in Chinese mode
- Decorative single-side accent borders (.px-notice-limitation, .px-quote)
  changed to full 4px borders per design rules

### Verification
- Playwright: 4 locale/viewport combos (EN desktop, ZH desktop,
  EN mobile 390x844, ZH mobile 390x844), all 12 pages PASS
- Console errors: 0; page exceptions: 0; horizontal overflow: none
- Focus: visible blue outline (rgb(41,173,255) solid 3px, offset 2px)
- Role separation: PASS (no prohibited content in Student View)
- Static style audit: 0 violations
- Computed-style audit: all zero radius, no gradients/blur/soft shadows,
  zero transitions, no animations
- Rerun idempotency: no duplicate exercise instances
- pytest: 271 passed, 8 skipped; Cases A-R: 110 passed
- run.bat --verify: PASS (migration 12, config-v0.9.0, all HTTP 200)
- Security: no tracked credentials; .env gitignored; clean screenshots
- Backend: no changes (migration 12, config-v0.9.0 preserved)

### Backend
- No changes to migration 12, config-v0.9.0, or any backend code
## v0.9.2 (2026-07-31)

### Changed
- Complete Pixel Art UI redesign with centralized CSS token system
- Square corners, hard offset shadows (2px/4px/8px), solid colors, no gradients
- Canonical 7-color palette: #1a1c2c, #ffffff, #f4f4f4, #ff004d, #00e436, #29adff, #ffec27
- Monospace typography stack (ui-monospace, Cascadia, Consolas, SFMono, Menlo, etc.)
- All transitions set to none; immediate hard state changes for hover/active/focus
- Reusable component library redesigned: page_header, section_header, metric_card,
  feedback_priority_card, timeline_event, status_badge, notices (warning/error/
  success/info/limitation), empty_state, audit_record, table_container, divider
- Global application shell with pixel-art sidebar, borders, and typography
- All 12 pages (6 Student + 6 Research) redesigned with pixel-art cards and layouts
- Streamlit form controls restyled: square corners, thick borders, blue focus outlines
- Responsive: smaller borders and shadow offsets on mobile (<=640px)
- prefers-reduced-motion: explicit animation/transition disable
- Nested cards eliminated; replaced with flat sections, separators, and rows

### Backend
- No changes to migration 12, config-v0.9.0, or any backend code
- 271 pytest passed, 8 skipped (unchanged from v0.9.1 baseline)

### Design references
- Token files archived at docs/design/reference/pixel-art/
## v0.9.1 (2026-07-31)

### Added
- Role-based navigation: Student View (6 pages) and Research View (6 pages)
- Reusable UI component system (status_badge, metric_card, evidence_quote, etc.)
- Progressive disclosure rules hiding internal IDs from Student View
- Visual design system with responsive CSS (desktop to 390x844 mobile)
- 61 new i18n keys (271 total, en + zh_CN parity)
- Expanded Playwright tests (6 scenarios: desktop, research, mobile, Chinese, keys, home)

### Changed
- Complete Streamlit UI rewrite with modular page architecture
- Sidebar navigation: language switcher, role selector, page navigation
- Student Home page with task summary, status, and next-action recommendations
- Student Writing page with grouped field sections
- Student Feedback page with strengths, max 2 priorities, evidence, next step
- Student Revision page with draft chain, changes, priorities, uptake
- Student Learning Journey with chronological timeline events
- Research Overview with system status and data quality
- Research Evidence with submission/analysis/diagnosis audit
- Research CALF Measures with grouped metric cards
- Research Learning Process with complete evidence chain
- Research Data with 8 organized subsections
- Research System Audit with diagnostic, learner model, reanalysis, admin

### Fixed
- All UI strings now routed through locale system
- No raw locale keys appear in user-facing text
- BOM stripped from all new source files

### Backend
- No changes to migration 12, config-v0.9.0, or any backend code


# Changelog

## 0.9.0 — 2026-07-30
- Added Practice Target, Exercise Instance, Exercise Attempt, Practice Evaluation, Feedback Engagement Trace, Within-task Response Candidate, and Transfer Evidence Candidate infrastructure with migration 12 and config-v0.9.0.
- Implemented deterministic exercise generation with three exercise types and conservative rule-based evaluation without mastery/scoring language.
- Added Streamlit Practice, Learning Journey, and Practice Audit pages with sidebar navigation.
- Added 20-case Live A-G controlled validation suite and desktop/mobile Playwright verification (1280×900 and 390×844).
- Added 210 locale keys in en and zh_CN for all practice UI text.
- All practice records are append-only with generated IDs; DeepSeek practice generation disabled by default.
- No mastery, proficiency, CEFR, scoring, or causal claims introduced.


## 0.8.1 — 2026-07-30
- Added English/Simplified Chinese multilingual UI with locale files in `locales/`; all user-facing labels, status descriptions, and metric explanations are internationalized.
- Refactored CALF display with classified metric cards showing construct grouping, unified status labels (Research metric/Descriptive proxy/Automatic candidate/Unavailable), confidence, analysis unit, and version per measure.
- Reorganized result tabs by view mode with role-based information isolation; student view hides technical metadata.
- Added sidebar language picker supporting runtime switching without restart.
- No new measurements, scoring, CEFR, or v0.9 functionality introduced.

## 0.8.0 — 2026-07-30
- Added versioned CALF construct, measurement-specification, and analysis-unit registries; deterministic MTLD/HD-D; research-only syntactic candidates; append-only error annotations; and actual-duration-only writing output rate.
- Added migration 10, `config-v0.8.0`, CALF APIs/research UI, Cases A–M, opt-in live A–D verification, and explicit prompt/diagnosis/longitudinal isolation.
- Accuracy, lexical sophistication, validated clause/T-unit measures, CALF totals, writing scores, ability/proficiency/CEFR claims, and v0.9 remain unavailable or out of scope.

## 0.7.1 — 2026-07-30

- Added backend-owned `longitudinal_assessment`, conservative field-level repair, positive-finding ability-inference guardrails, and auditable provider execution status.
- Added migration 9 and `config-v0.7.1` without deleting historical data; logical rollback reactivates `config-v0.7.0`.
- Added within-task revision trajectory, first-to-latest and pairwise comparisons, explained empty-state codes, and backward-compatible API fields.
- Refined Streamlit into Feedback, Revision, Progress, Evidence, and Research Audit tabs with Student/Research audit modes and explicit independent-task/revision entry.
- Added Cases 1–10 regression coverage, live DeepSeek A–C verification, and desktop/mobile Playwright QA. No v0.8, scoring, CEFR, model training, cloud deployment, or frontend rewrite was introduced.

## 0.7.0 — 2026-07-30

- Added immutable Learner Profile Snapshot v2, task clustering, four revision representative strategies, explicit Data Sufficiency, version-separated Metric/Diagnostic Trajectory v2, current learning targets, strength patterns, and append-only History Evidence.
- Added migration 8 and active `config-v0.7.0` as a child of preserved `config-v0.6.2`; historical essays, analysis runs, diagnoses, revisions and snapshots remain readable.
- Added screened `feedback-prompt-v0.7.0`, Learner Model APIs/UI, Case A–I fixtures, and an opt-in three-task live DeepSeek test.
- No CALF/CEFR/overall score, causal learning claim, cloud deployment, paid embedding service, or v0.8 feature was added.

## 0.6.1 — 2026-07-29

- Added versioned Metric Confidence with reproducible lexical measurement metadata.
- Added an append-only Diagnostic Gate, transparent Priority Score, and evidence-relevance validation.
- Calibrated distributed lexical repetition, necessary task terms, and connective-location requirements.
- Separated verified strengths from descriptive signals and calibrated parser-candidate names/counts.
- Restricted FeedbackContext and exercise generation to evidence-verified selected priorities; zero priorities are valid.
- Added migration 7, active `config-v0.6.2`, researcher audit API/UI, fixed first/revised-draft fixtures, and live DeepSeek verification.
- Preserved the one-retry/3,600-token correction path, exact quotations, redaction, Pydantic validation, and LocalDemo fallback.

## Unreleased fixes

- Fixed the timed-writing form so the time limit can be edited before submission; the value is persisted only for timed writing.
- Made DeepSeek schema failures actionable without recording response content or secrets.
- Corrected the retry instruction so invalid evidence quotations are replaced with exact essay substrings.
- Doubled the output budget only for the single correction attempt, preventing complete structured feedback from being truncated while retaining the configured first-call budget.
- Added visible provider configuration and sanitized fallback diagnostics to the Streamlit page.

## 0.6.0 — 2026-07-29

- Added API-sourced student timelines, issue trajectories, comparability summaries and version-separated metric series.
- Added dedicated Streamlit progress, revision-comparison and local-researcher administration pages.
- Added append-only non-sensitive configuration versions with validation, activation, rollback, content hashes and audit records.
- Added Analyzer, Metric, Algorithm, Prompt and Configuration registries and comprehensive version transparency.
- Added scoped reanalysis preview/run for submission, revision group, student and AnalysisRun; local-only by default.
- Removed the legacy one-feedback-per-essay constraint so explicitly confirmed LLM regeneration is append-only.
- Added migration 6 and CALF extension seams without any CALF total or proficiency field.

## 0.5.0 — 2026-07-29

- Added explicit Revision Groups and validated first/revised/final draft chains.
- Added deterministic paragraph, sentence and token alignment with major-rewrite detection.
- Added observed metric changes, diagnosis trajectories and non-causal feedback-uptake candidates.
- Added append-only Revision Snapshots, revision APIs and a Streamlit revision workflow.
- Default longitudinal trends use one representative draft per Revision Group: final, otherwise latest.
- Added Prompt/Schema v0.5 evidence-ID validation and explicit exercise-source metadata.

## 0.4.0 — 2026-07-29

- 新增可注册的 `SpacyAnalyzer` 与显式 `BasicAnalyzer` 回退，固定 spaCy 3.8.7 / en_core_web_sm 3.8.0。
- 新增输入质量提醒、词元和内容词分析、题目关键词降权、MATTR、lexical density、连接表达位置/功能分类及原型句法候选。
- 数据库迁移 4 新增 append-only AnalysisRun、MetricResult 与分析 Artifact；单篇重分析不覆盖旧结果且默认不调用 LLM。
- Prompt v0.4 仅向 Provider 暴露结构化 NLP 证据，并继续执行 Pydantic、诊断 ID、历史 ID 和逐字引文验证。
- health/API/Streamlit/run.bat 同步显示 NLP 资源、活动 Analyzer 和显式回退状态。

## 0.1.0 — 2026-07-29

- 建立分层 Streamlit、SQLite、Pydantic MVP。
- 实现基础 Analyzer 和谨慎的启发式 Diagnosis。
- 实现 DeepSeekProvider、LocalDemoProvider 与自动回退。
- 实现三类诊断关联练习。
- 实现历史读取、可比性检查和纵向描述。
- 加入 3 名虚拟学生、9 篇作文和完整闭环验证脚本。
- 加入 12 项 pytest 测试、实际 Streamlit HTTP 启动测试和项目文档。
- 新增新电脑安装指南与 Windows 一键安装/启动脚本。
- 扩大 Git 忽略规则，排除虚拟环境、密钥文件、Python 缓存和全部 SQLite 数据库。
- 使用全新的临时 Python 3.11 环境完成从零安装与启动验证。

## 0.1.1 — 2026-07-29

- 模块化并固化 Prompt 模板、版本、SHA-256 manifest 和 fail-closed 漂移检查。
- 为诊断与历史证据增加稳定 ID，并严格验证反馈引用、逐字作文证据、练习关联和无历史措辞。
- 增加 DeepSeek 一次纠错重试、LocalDemo 自动回退和逐次调用审计；无效主模型输出不会保存为正式反馈。
- 完成同一虚拟学生两次真实 DeepSeek 提交：第二次请求包含 2 条历史证据并返回有效 `H001`、`H002`，无重试、无回退。
- 普通测试最终结果为 42 passed、1 个默认跳过的可选 live test；`run.bat --verify` 返回 Streamlit HTTP 200。

## 0.2.0 — 2026-07-29

- 增加 FastAPI v1 统一后端，提供健康、版本、提交、学生、历史、profile 和 progress 接口。
- 将 Streamlit 改为纯 HTTP API 客户端，不再构造业务服务或访问 SQLite、Analyzer、Diagnoser、Prompt、Provider。
- 增加框架无关的 `SubmissionService`、命名 Repository 协议和 SQLite 实现扩展点。
- 引入 `PRAGMA user_version` + `schema_migrations` 的可重复非破坏迁移；支持空库、v0.1.1 旧库和重复升级。
- `run.bat` 现会迁移数据库、启动 FastAPI、轮询 health，再启动 Streamlit；`--verify` 同时探测 health、`/docs` 与 Streamlit。
- 保留 v0.1.1 Prompt、证据 ID、引文校验、Pydantic、重试和回退链路。

## 0.3.0 — 2026-07-29

- 增加版本化 ComparabilityResult、BaselineProfile、MetricTrend、IssueTrajectory、PriorityCandidate 和 LearnerProfileSnapshot。
- 增加可解释的可比较性、个人描述性基线、线性趋势、相对变化、波动性和保守置信度规则。
- 使用结构化诊断追踪 persistent、recurring、inconsistent、recently_reduced 和 insufficient_evidence。
- 数据库迁移 3 新增 append-only `learner_profile_snapshots`；重算不覆盖旧 Snapshot。
- progress/profile API 返回真实 v0.3 结构，并支持 metric、日期、comparable_only 和 analysis_version 查询。
- Prompt 升级至 `feedback-prompt-v0.3.0`；只发送筛选后的 Snapshot，纵向评论仍必须绑定经验证的 H 证据 ID。
- 增加四类纯虚拟纵向场景和完整回归/纵向/API/持久化测试。


