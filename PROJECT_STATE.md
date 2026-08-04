# Project State
## Current v0.9.6-D0 State

- Status: BLOCKED at the live-provider preflight (classification D0-E);
  audit-only; no production code changed (see
  RUN_VERIFICATION_V0.9.6_D0.md and
  docs/development/BLOCKER_REPORT_V0.9.6_D0.md).
- Real provider (DeepSeek deepseek-v4-pro) failed the bounded preflight
  on both approved attempts (truncated JSON, then 30 s timeout); fallback
  results recorded but not counted as live-provider success. Corpus,
  repeatability, and downstream phases not run.
- Non-provider pipeline verified on an isolated audit database
  (spacy-analyzer-v0.8.0; Diagnostic Gate selected lexical_repetition
  D001, 0.6649, verified).
- Targeted verification: 155 passed, exit 0. Development database and
  research exports (776/388) unchanged.
- Recommended next stage (separately approved): v0.9.6-DP0 Production
  Provider Reliability. v0.9.6-D1 remains not started.


# Project State

# Project State

# Project State

# Project State

## Current v0.9.6-C State (no-priority workflow completion and sidebar/icon repair)

- Status: **COMPLETE and fully verified** (C1 and C2 owner-accepted; full
  non-live core exit 0, 809 passed, 8 skipped; launcher PASS; see
  `RUN_VERIFICATION_V0.9.6_C.md`).
- C1: the no-priority Diagnostic Gate result is now a complete actionable
  branch (Submission #28 / learner S02). Root cause of the old
  Writing<->Feedback loop: stale Writing-submitted session state with no
  terminal action, no Feedback actions for no-priority results, and no
  Home acknowledgement for a finished cycle. Fix: `Revise This Draft`
  (existing revision-writing mode, correct source, no fabricated
  priority) and `Finish This Feedback Cycle` (session acknowledgement
  `no_priority_reviewed` = exact submission id; stale panel cleared;
  Home/Writing return to `1 Write`); Revision/Practice explain the absent
  focus/target and stay actionable; neutral `Passage From Your Writing`
  section replaces any unsupported Strength.
- C2: sidebar collapse/expand arrows and the Writing-page Genre expander
  chevrons (Timing, Tools Used) render with Material Symbols Rounded
  again. Root cause: the pixel-art base typography rule overrode
  Streamlit native `stIconMaterial` spans, plus Streamlit stock
  hover-only sidebar visibility. Fix: common exclusion of native icon
  spans from the base rule and visible-before-hover pinning of the two
  native sidebar controls.
- Contracts: API 77 pairs unchanged; Database public methods 2; frontend
  client 53; locale parity 540/540 (12 approved C1 keys added); migration
  12; tables 33; `config-v0.9.0`; `feedback-prompt-v0.7.1`; development
  database unchanged; research exports restored to 776 files / 388 dirs.
- Next: continue v0.9.6 user-visible feature development under a new
  owner-authorized goal.

## Current v0.9.6-B State (first draft and unified submission reliability)

- Status: **COMPLETE and fully verified** (full non-live core exit 0,
  760 passed, 8 skipped; launcher PASS).
- Incident classified C (read-only DB inspection): first draft essay 27
  completed after the UI timeout (30.46 s provider call vs the old 30 s
  client timeout); no duplicate first draft found in the incident.
- Fix: `submit()` and `submit_linked_revision()` share the private
  `_submit_long_running` transport (LONG_SUBMIT_TIMEOUTS 180 s, one
  POST, no retry); shared UI reliability helper; writing-page pending
  guard and bounded read-only exact reconciliation (CONFIRMED_SUCCESS /
  STILL_PROCESSING / UNCONFIRMED); accurate en/zh messages (parity
  528/528). Linked-revision behavior preserved.
- Contracts: API 77 pairs unchanged; Database public methods 2; frontend
  client 53 (no new public method); `StudentWritingApiPort` gained
  `get_submission`; migration 12; tables 33; `config-v0.9.0`;
  `feedback-prompt-v0.7.1`; development database unchanged; research
  exports restored to 776 files / 388 dirs.
- Next: continue v0.9.6 user-visible feature development.

## Current v0.9.6-A State (linked revision submission reliability)

- Status: **COMPLETE and fully verified** (full non-live core exit 0,
  730 passed, 8 skipped; launcher PASS).
- Incident classified C (read-only DB inspection): the timed-out linked
  revision (essay 26) was durably completed after the UI timeout; a
  duplicate pair (essays 24/25) was created by a second POST.
- Fix: dedicated 180 s long-operation timeout for the linked-revision
  submit path only; pending-state submit guard (no duplicate POST); no
  automatic POST retry; bounded read-only reconciliation via existing
  GET APIs with CONFIRMED_SUCCESS / STILL_PROCESSING / UNCONFIRMED
  outcomes; accurate en/zh messages (parity 524/524).
- Contracts: API 77 pairs unchanged; Database public methods 2; frontend
  client 52 -> 53 (feature-driven ledger update); migration 12; tables
  33; `config-v0.9.0`; `feedback-prompt-v0.7.1`; development database
  unchanged; research exports restored to 776 files / 388 dirs.
- Next: continue v0.9.6 user-visible feature development.

## Current v0.9.5-H2E State (architecture freeze)

- Status: **COMPLETE - v0.9.5 architecture optimization is COMPLETE and
  frozen.** H2D2-V1 full-core closure passed (exit 0, 709 passed, 8
  skipped, 2 warnings, zero failures/errors); the freeze captures the final
  source-authoritative inventory and ends generic architecture work.
- Frozen inventory: Database public methods 2; API path+method pairs 77
  (73 explicit OpenAPI pairs + 4 auto-HEAD GET entries); frontend client
  52; locale 520/520; migration 12; tables 33; `config-v0.9.0`;
  `feedback-prompt-v0.7.1`; persistence contracts 41/41/0; Protocol 41;
  plain structural 0; runtime-checkable 36; API-owned Ports 10,
  production bindings 10, unbound 0; ConfigurationPort = typing.Protocol;
  AnalysisRunReader definitions 1.
- H1 COMPLETE; H2A COMPLETE; H2B COMPLETE; H2C COMPLETE; H2D1 COMPLETE;
  H2D2 COMPLETE; H2E COMPLETE.
- Next stage: **v0.9.6 feature development** (user-visible or
  research-workflow-visible functional outcome; no generic architecture
  audit or cleanup).

## Current v0.9.5-H2D2 State

- Status: **COMPLETE and fully verified** (H2D2-V1 full non-live core
  closure: exit code 0, 709 passed, 8 skipped, 2 warnings, zero
  failures/errors).
- Bound the ten v0.9.5-G API-owned persistence Ports as exact production
  return annotations on their ten dependency accessors in `app/api/deps.py`
  (type-only: import block + ten annotations). Accessor bodies, parameters,
  app-state attributes, Routers, `Depends(...)`, composition, Port
  definitions, OpenAPI, and the dependency graph are unchanged; all ten
  annotations resolve at runtime; all ten facade-owned repositories
  structurally satisfy their Ports.
- API Ports with production references 0 -> 10; contract counts frozen
  (41/41/0; Protocol 41; plain structural 0; runtime-checkable 36); Database
  public methods 2; API 77; client 52; locale 520/520; migration 12; 33
  tables; `config-v0.9.0`; `feedback-prompt-v0.7.1`.
- Verification: focused contract suite 243 passed, 2 warnings; OpenAPI and
  dependency-graph parity 0 differences; exact `run.bat --verify` PASS;
  H2D2-V1 full non-live core closure **exit code 0, 709 passed, 8 skipped,
  2 warnings, zero failures/errors**; research_export baseline restored to
  776 files / 388 dirs after every layer (8 dirs / 16 files removed from the
  closure run via the exact guard allowlist); development database unchanged
  (SHA-256/size/mtime).
- Next: H2E (architecture freeze) - authorized in the same goal, pending the H2D2-V1 closure commit.

## Current v0.9.5-H2D1 State (incl. v0.9.5-H2D1-V1 workspace cleanup)

- Status: **COMPLETE and fully verified** (full non-live core run: exit code
  0, 696 passed, 8 skipped, 2 warnings).
- Formalized the active `ConfigurationPort` contract
  (`app/services/configuration.py`) from a plain structural class to a
  structural `typing.Protocol` (same name/module; seven methods, signatures,
  and behavior unchanged; not `@runtime_checkable`; no alias).
- Contract-kind transition: typing.Protocol 40 -> 41; plain structural
  1 -> 0; total/active contracts 41 -> 41; runtime-checkable 36 -> 36.
- Verification: focused contract suite 230 passed, 2 warnings; exact
  `run.bat --verify` PASS; full non-live core run **exit code 0, 696 passed,
  8 skipped, 2 warnings**; Database public methods 2; API 77; client 52;
  locale 520/520; migration 12; 33 tables; `config-v0.9.0`;
  `feedback-prompt-v0.7.1`; development database unchanged
  (SHA-256/size/mtime).
- v0.9.5-H2D1-V1 workspace-safety closure: the 22 files / 11 export
  directories generated by the H2D1 verification runs through the
  pre-existing research-export tests were identified with exact ownership
  evidence and removed; `research_exports/` restored to the approved
  pre-H2D1 baseline of 776 files; all retained paths and hashes unchanged;
  no production/test change; no tests rerun. Research-export verification
  side effects: CLEANED.
- Next: H2D2 and H2E each require separate authorization.

## Current v0.9.5-H2D1 State

- Status: **COMPLETE and fully verified** (full non-live core run: exit code
  0, 696 passed, 8 skipped, 2 warnings).
- Formalized the active `ConfigurationPort` contract
  (`app/services/configuration.py`) from a plain structural class to a
  structural `typing.Protocol` (same name/module; seven methods, signatures,
  and behavior unchanged; not `@runtime_checkable`; no alias).
- Zero runtime behavior change: `ConfigurationService` annotation resolves to
  `ConfigurationPort`; `SQLiteConfigurationRepository` structurally satisfies
  the Protocol without explicit inheritance; application composition,
  configuration workflows, SQL, transactions, API, UI unchanged.
  Contract-kind transition: typing.Protocol 40 -> 41; plain structural
  1 -> 0; total/active contracts 41 -> 41; runtime-checkable 36 -> 36.
- Verification: focused contract suite 230 passed, 2 warnings; exact
  `run.bat --verify` PASS; full non-live core run **exit code 0, 696 passed,
  8 skipped, 2 warnings**; Database public methods 2; API 77; client 52;
  locale 520/520; migration 12; 33 tables; `config-v0.9.0`;
  `feedback-prompt-v0.7.1`; development database unchanged
  (SHA-256/size/mtime).
- Next: H2D2 and H2E each require separate authorization.

## Current v0.9.5-H2C State

- Status: **COMPLETE and fully verified** (full non-live core run: exit code
  0, 683 passed, 8 skipped, 2 warnings).
- Canonicalized the exact duplicate infrastructure reader pair
  `_AnalysisRunReader` (revision.py:14, learner.py:12) into one shared
  infrastructure-owned `AnalysisRunReader` Protocol in the new module
  `app/infrastructure/sqlite/repositories/contracts.py`; both consumers
  (`SQLiteRevisionRepository`, `SQLiteLearnerRepository`) use the canonical
  contract for the existing `analysis_reader` constructor annotation only.
  Both former local definitions removed; no alias; old name absent from
  `app/**`.
- Zero runtime behavior change: constructor parameter names/order/defaults,
  stored attributes, concrete Repository identity, connection manager, SQL,
  transactions, composition, Services, Routers, APIs, and UI unchanged.
  Active persistence contracts 42 -> 41; unused legacy 0 -> 0.
- Verification: focused contract suite 217 passed, 2 warnings; exact
  `run.bat --verify` PASS; full non-live core run **exit code 0, 683 passed,
  8 skipped, 2 warnings**; Database public methods 2; API 77; client 52;
  locale 520/520; migration 12; 33 tables; `config-v0.9.0`;
  `feedback-prompt-v0.7.1`; development database unchanged
  (SHA-256/size/mtime).
- Next: H2D and H2E each require separate authorization.

## Current v0.9.5-H2B State

- Status: **COMPLETE and fully verified** (v0.9.5-H2B-V1 closure full-core run:
  exit code 0, 669 passed, 8 skipped, 2 warnings).
- Renamed the active local configuration contract `ConfigurationRepository`
  to `ConfigurationPort` (naming-only, `app/services/configuration.py`
  definition + `ConfigurationService` annotation). Seven methods, signatures,
  repository implementation, SQL, transactions, API, UI, and runtime behavior
  unchanged; no alias or duplicate name; old name absent from `app/**`.
- Verification: focused contract suite 203 passed, 2 warnings; exact
  `run.bat --verify` PASS; full non-live core closure run (v0.9.5-H2B-V1)
  **exit code 0, 669 passed, 8 skipped, 2 warnings** (the two prior runs each
  failed once on the documented pre-existing `test_v095b_router_contract`
  lifecycle-race flake, which passes in isolation and in the closure run);
  Database public methods 2; API 77; client 52; locale 520/520; migration 12;
  33 tables; `config-v0.9.0`; `feedback-prompt-v0.7.1`; development database
  unchanged (SHA-256/size/mtime).
- Next: H2C (`_AnalysisRunReader` canonicalization), H2D, H2E each require
  separate authorization.



- Status: completed and fully verified (full-core closure exit 0); exactly 13 unused persistence contracts
  removed (legacy `SubmissionRepository`, 11 stale central Protocols,
  `SubmissionRepositories` union alias) with zero runtime consumers and no
  replacement contracts; obsolete imports, bases, and re-exports removed.
- Total persistence-related contracts now 42 (was 55); active persistence
  contracts 42 (unchanged); unused legacy contracts 13 -> 0;
  `app/repositories` exports only
  `RevisionRepository`; the Configuration same-name collision is resolved by
  stale central-contract removal while the active local 7-method
  `ConfigurationRepository` is unchanged; all F2-G dependency boundaries,
  Repository implementations, SQL, transactions, API, schema, provider,
  prompt, UI, and localization unchanged.
- Verification: focused contract suite 197 passed, 2 warnings; full non-live
  core 663 passed + 8 skipped, 2 warnings, exit code 0 (closure run; the
  original run exited 1 on the documented pre-existing
  `test_v095b_router_contract` lifecycle-race flake, which passes in
  isolation and in the closure run); exact
  `run.bat --verify` PASS; Database public methods 2; API 77; client 52;
  locale 520/520; migration 12; 33 tables; `config-v0.9.0`;
  `feedback-prompt-v0.7.1`; development database unchanged
  (SHA-256/size/mtime).
- Next: H2B (rename the active local `ConfigurationRepository`), H2C
  (`_AnalysisRunReader` canonicalization), H2D (API Port production
  annotations), and H2E (contract freeze) each require separate
  authorization.

## Current v0.9.5-H1 State

- Status: completed (read-only source-authoritative audit; evidence and plan
  only - see `docs/development/PROTOCOL_CONSOLIDATION_AUDIT_V0.9.5_H1.md`).
- Inventory: 55 persistence-related contracts (52 Protocols, 1 typing union
  alias, 1 plain structural class, 1 legacy combined class); classifications
  A=37, B=1, C=4, G=13; active=42; unused candidates=13; 3 same-name
  collisions (`ConfigurationRepository`, `SubmissionBundleReadPort`,
  `_AnalysisRunReader`); 29 methods declared by more than one contract.
- Findings: the legacy `SubmissionRepository` (inherits 6 stale central
  Protocols) has no production consumer and can be removed without
  replacement; the central `ConfigurationRepository` (ping/migration_version)
  is stale while the local 7-method `ConfigurationRepository` is the
  authoritative `ConfigurationService` contract; the ten API-owned Ports are
  exact but currently referenced only by contract tests (runtime path is
  `deps.get_*` -> `app.state.*`); Practice read/write separation is
  intentional; `_AnalysisRunReader` is an exact infra duplicate pair.
- H2 plan: 5 dependency-ordered units (H2A remove unused legacy contracts ->
  H2B resolve remaining collision -> H2C canonicalize infra duplicate ->
  H2D formalize misplaced contracts -> H2E freeze); recommended first unit
  H2A. H2 is NOT authorized.
- Verification: focused F2-F6D+G Protocol/Port contract tests 187 passed, 2
  warnings under isolated DB; all four JSON artifacts parsed and reconciled;
  no production, test, Repository, SQL, transaction, API, schema, provider,
  prompt, UI, or localization file changed; development database unchanged
  (SHA-256/size/mtime).
- Next: H2 implementation only under separate authorization.

## Current v0.9.5-G State

- Status: completed and verified; Database facade contraction scope closed;
  core v0.9.5 modularization and persistence decoupling complete.
- The `Database` public surface is `connect`, `initialize` (evidence-supported
  infrastructure); all 84 removed business-delegation methods are recorded in
  the exact G removal ledger with replacements (aggregate Repositories or API
  Ports) or zero-caller proofs; the `SQLiteRepository` alias and export are
  removed; one connection manager and one Repository graph remain.
- Zero production Router uses `Depends(get_repository)`; ten exact API-owned
  Ports (`app/api/ports.py`) compose facade-owned Repositories on app state;
  `require_student` uses `StudentLookupPort`; FeedbackPipeline and scripts use
  facade-owned aggregate Repositories; Research export-job best-effort
  behavior unchanged.
- Verification: focused 437 PASS; full non-live core 653 passed + 8 skipped;
  exact `run.bat --verify` PASS; migration 12; 33 tables; `config-v0.9.0`;
  prompt `feedback-prompt-v0.7.1`; API 77; client 52; locale 520/520;
  Database public methods 2; development database unchanged
  (SHA-256/size/mtime).
- Next: no further v0.9.5 stage without separate authorization; Protocol
  consolidation, legacy `SubmissionRepository` removal, FeedbackPipeline
  removal, WTR collision, and export-job redesign remain deferred.

## Current v0.9.5-F6D State

- Status: completed and verified; Practice write-boundary narrowing scope
  closed; final v0.9.5-F6 dependency-narrowing stage.
- The Practice Router depends on exactly `PracticeSubmissionReadPort`,
  `PracticeReadPort`, `PracticeWritePort` (new `app/practice/ports.py`), the
  preserved `require_student` guard (facade-owned Learner reader), and the
  pure `PracticeService()`; no broad `Database` dependency remains.
- `PracticeService` is persistence-free (constructor `PracticeService()`);
  both app paths compose facade-owned Submission/Practice repositories and
  the Service on `app.state`; five narrow dependency accessors added;
  Attempt-first/Evaluation-best-effort semantics, all eight endpoints, and
  the 77-pair API contract are unchanged; no new Practice writer workflow.
- Verification: focused 187 PASS; accumulated contracts 253 PASS; full
  non-live core 638 passed + 8 skipped; exact `run.bat --verify` PASS;
  migration 12; 33 tables; `config-v0.9.0`; prompt `feedback-prompt-v0.7.1`;
  facade 86; API 77; client 52; locale 520/520; development database
  unchanged (SHA-256/size/mtime).
- Next: v0.9.5-G Database facade contraction only under separate
  authorization; Protocol consolidation, `require_student` narrowing, and
  FeedbackPipeline cleanup remain deferred.

## Current v0.9.5-F6C State

- Status: completed and verified; SubmissionService persistence dependency
  narrowing scope closed.
- `SubmissionService` depends on exactly `SubmissionSystemPort`,
  `SubmissionDataPort`, `SubmissionAnalysisPort`, `SubmissionCalibrationPort`,
  and the existing analyzer/diagnoser/router, learner-history, learner-profile,
  Revision, and calibration collaborators; the broad inherited
  `SubmissionRepository` is no longer used by active composition (legacy
  declaration retained as Protocol-consolidation debt).
- Both CALF `hasattr` guards removed; the eleven direct persistence calls
  route to approved owners; `build_submission_service` takes seven required
  keyword-only facade-owned repositories; both app paths, FeedbackPipeline,
  and all active callers pass the existing facade-owned instances (one
  connection manager, one graph); constructor `record_versions`, submit and
  regenerate-feedback order, write counts, and partial-commit behavior are
  preserved; F2-F6B boundaries unchanged.
- Verification: focused 282 PASS; accumulated contracts 233 PASS; full
  non-live core 618 passed + 8 skipped; exact `run.bat --verify` PASS;
  migration 12; 33 tables; `config-v0.9.0`; prompt `feedback-prompt-v0.7.1`;
  facade 86; API 77; client 52; locale 520/520; development database
  unchanged (SHA-256/size/mtime).
- Next: v0.9.5-F6D Practice write-boundary work only under separate
  authorization; facade contraction and Protocol consolidation remain
  deferred.

## Current v0.9.5-F6B State

- Status: completed and verified; AdminReanalysisService persistence
  dependency narrowing scope closed.
- `AdminReanalysisService` depends on exactly `AdminConfigurationReadPort`,
  `AdminSubmissionReadPort`, `AdminAnalysisPort`, the unchanged central
  `RevisionRepository`, and the existing settings/Service collaborators; the
  broad, untyped `repository` dependency is removed.
- All six direct calls route to approved owners; both app paths pass the
  existing facade-owned repositories (one connection manager, one graph);
  `ConfigurationService.active`, `SubmissionService.regenerate_feedback`,
  and the embedded `RevisionService` are unchanged; preview is zero-write;
  Analysis save count/order, feedback conditions, and partial-commit
  behavior are preserved; F2-F6A boundaries unchanged.
- Verification: focused 154 PASS; accumulated contracts 204 PASS; full
  non-live core 589 passed + 8 skipped; exact `run.bat --verify` PASS;
  migration 12; 33 tables; `config-v0.9.0`; prompt `feedback-prompt-v0.7.1`;
  facade 86; API 77; client 52; locale 520/520; development database
  unchanged (SHA-256/size/mtime).
- Next: v0.9.5-F6C SubmissionService narrowing only under separate
  authorization; F6D and later stages remain unstarted.

## Current v0.9.5-F6A State

- Status: completed and verified; RevisionService runtime repository
  narrowing scope closed (F6A0 prerequisite completed first).
- Every active `RevisionService` now receives the existing facade-owned
  `SQLiteRevisionRepository` instance (both app paths, the Submission
  factory, AdminReanalysisService embedded composition, FeedbackPipeline,
  and operational callers); no active instance receives the broad `Database`
  facade. No new Revision Port, no fallback, no proxy, no shared
  transaction; the central `RevisionRepository`, `RevisionService`, Revision
  write methods, SQL, and the three-sequential-commit workflow are
  unchanged.
- Verification: focused 155 PASS; accumulated contracts 188 PASS; full
  non-live core 573 passed + 8 skipped; exact `run.bat --verify` PASS;
  migration 12; 33 tables; `config-v0.9.0`; prompt `feedback-prompt-v0.7.1`;
  facade 86; API 77; client 52; locale 520/520; development database
  unchanged (SHA-256/size/mtime).
- Next: v0.9.5-F6B (Admin Reanalysis persistence narrowing) and later
  stages only under separate authorization.

## Current v0.9.5-F6A0 State

- Status: completed and verified; Revision repository capability completion
  scope closed (prerequisite for the still-blocked v0.9.5-F6A).
- `SQLiteRevisionRepository` now exposes `get_submission_bundle` and
  `get_latest_analysis_run` as direct reader delegations and receives the
  existing facade-owned Submission and Analysis repository instances from
  the `Database` facade (same connection manager, one repository graph).
  The central `RevisionRepository` Protocol, `RevisionService`, all
  construction sites, Revision write methods, SQL, and transaction
  boundaries are unchanged; no F6A runtime narrowing was performed.
- Verification: focused 53 PASS; accumulated contracts 161 PASS; full
  non-live core 559 passed + 8 skipped; exact `run.bat --verify` PASS;
  migration 12; 33 tables; `config-v0.9.0`; prompt `feedback-prompt-v0.7.1`;
  facade 86; API 77; client 52; locale 520/520; development database
  unchanged (SHA-256/size/mtime).
- Next: v0.9.5-F6A runtime narrowing only after a separate rebaseline and
  authorization; F6B and later stages remain unstarted.

## Current v0.9.5-F5B State

- Status: completed and verified; ResearchDataService dependency narrowing
  scope closed (one Service narrowed to three explicit consumer-owned
  Ports).
- `ResearchDataService` -> `ResearchSubmissionReadPort`
  (`list_all_submissions`, `list_student_submissions`,
  `get_submission_bundle`) + `ResearchReviewPort` (`save_human_review`,
  `list_human_reviews`, `apply_pii_review`) + `ResearchExportReadPort`
  (`list_export_jobs`, `get_export_job`). All six repository-capability
  `hasattr` branches were removed; no broad repository field, no untyped
  persistence parameter, no compatibility fallback, and no
  `Database`/SQLite imports remain in the Service module.
- Both application paths reuse the existing facade-owned Submission
  repository and the same Research repository instance for both
  Research-owned Ports; the five `tests/test_research_v082.py` sites and
  the one `capture_prechange_fresh_database.py` site received
  constructor-only updates. Router-level best-effort `save_export_job`
  persistence is unchanged and remains outside the Service.
- Verification: focused 97 PASS; contract inventory 141 PASS; full
  non-live core 546 passed + 8 skipped; exact `run.bat --verify` PASS;
  migration 12; 33 tables; `config-v0.9.0`; prompt `feedback-prompt-v0.7.1`;
  facade 86; API 77; client 52; locale 520/520; development database
  unchanged (SHA-256/size/mtime); 235 pre-existing user exports untouched.
- Next: any later stage (e.g., write-orchestration narrowing) only under a
  separate authorization.

## Current v0.9.5-F5A State

- Status: completed and verified; CALF Service dependency narrowing scope
  closed (one Service narrowed to four explicit consumer-owned Ports).
- `CalfService` -> `CalfDataPort` (`list_analysis_units`,
  `list_error_annotations`, `save_error_annotations`) +
  `CalfSubmissionReadPort` (`get_submission_bundle`,
  `list_student_submissions`) + `CalfAnalysisReadPort`
  (`get_latest_analysis_run`) + `CalfStudentReadPort` (`get_student`). No
  broad repository field, no untyped persistence parameter, no
  compatibility fallback, no `hasattr`, and no `Database`/SQLite imports
  in the Service module.
- Both application paths reuse the existing facade-owned CALF,
  Submission, Analysis, and Learner repository instances with explicit
  keyword arguments; the one operational-script caller
  (`scripts/verify_live_deepseek_v08.py`) uses the same four repositories
  of its own facade. No second connection manager, repository graph,
  proxy, or singleton was introduced.
- Verification: focused 63 PASS; contract inventory 123 PASS; full
  non-live core 526 passed + 8 skipped; exact `run.bat --verify` PASS;
  migration 12; 33 tables; `config-v0.9.0`; facade 86; API 77; client
  52; locale 520/520; development database unchanged (SHA-256/mtime).
- Next: v0.9.5-F5B only under a separate authorization; Research
  narrowing, write-orchestration narrowing, facade contraction, and
  schema cleanup remain deferred.

## Current v0.9.5-F4 State

- Status: completed and verified; Reanalysis and Journey dependency
  narrowing scope closed (two Services narrowed, one authorized
  operational-script exception).
- `ReanalysisService` -> `SubmissionBundleReadPort` +
  `AnalysisRunWritePort`; `JourneyService` -> `JourneyStudentReadPort` +
  eight-method `JourneyProjectionReadPort`. No broad repository field,
  no `Any` persistence annotation, no internal construction, no
  `Database`/SQLite imports in either Service module.
- Both application paths reuse the facade-owned extracted Submission,
  Analysis, Learner, and Practice repository instances; JourneyService
  lives on `app.state.journey_service` and the Journey router consumes
  the narrow `get_journey_service` dependency. The two demo-script
  construction sites are the owner-authorized exception; no second
  connection manager, repository graph, proxy, or singleton was
  introduced.
- Verification: focused 118 PASS; contract inventory 84 PASS; full
  non-live core 508 passed + 8 skipped; exact `run.bat --verify` PASS;
  migration 12; 33 tables; `config-v0.9.0`; facade 86; API 77; client
  52; locale 520/520; development database unchanged (SHA-256/mtime).
- Next: v0.9.5-F5 only under a separate authorization; Calf/Research
  narrowing, write-orchestration narrowing, facade contraction, and
  schema cleanup remain deferred.

## Current v0.9.5-F3 State

- Status: completed and verified; Learner read-model dependency narrowing
  scope closed (three Services narrowed, one authorized composition exception).
- `ProgressService` -> `LearnerProgressPort` + `ActiveConfigurationPort`;
  `LearnerProfileService` -> `LearnerProfileReadPort` + injected
  `ProgressService`; `DashboardService` -> `DashboardReadPort` + injected
  `ProgressService`. No `hasattr` capability discovery remains in the chain;
  the inactive `list_longitudinal_records` fallback was removed only from
  `ProgressService`.
- Both application paths, `build_submission_service`, and the legacy
  `FeedbackPipeline` reuse the facade-owned extracted Learner and
  Configuration repository instances; no second connection manager,
  repository graph, proxy, or singleton was introduced.
- Verification: focused 96 PASS; contract inventory 36 PASS; full non-live
  core 492 passed + 8 skipped; exact `run.bat --verify` PASS; migration 12;
  33 tables; `config-v0.9.0`; facade 86; API 77; client 52; locale 520/520;
  development database unchanged (SHA-256/mtime).
- Next: v0.9.5-F4 (write-orchestration narrowing) only under a separate
  authorization.

## Current v0.9.5-F2 State

- Status: completed and verified; low-risk Service dependency narrowing scope
  closed (exactly two Services narrowed).
- `ConfigurationService` receives the existing `SQLiteConfigurationRepository`
  instance in both application-construction paths; the 86-method facade is no
  longer passed to it.
- `LearnerHistoryService` depends on the one-method `PriorRecordsPort`
  (`prior_records(submission)`); its runtime object and all behavior are
  unchanged.
- `DashboardService`, `ProgressService`, `LearnerProfileService`, and all other
  Services untouched; facade surface 86 methods; migration 12; 33 tables;
  `config-v0.9.0`; API 77 pairs; client 52 methods; locale 520/520.
- Verification: 53 focused PASS; full core 480 passed + 8 skipped; exact
  `run.bat --verify` PASS; development database unchanged (SHA-256/mtime).
- Next: v0.9.5-F3 (Dashboard/Progress/LearnerProfile and read-only domain
  narrowing) only under a separate authorization.

## Current v0.9.5-E State

- Status: completed and verified; facade-first SQLite repository
  modularization scope closed.
- Explicit 86-method `Database` facade and `SQLiteRepository` alias preserved.
- One shared connection manager and nine aggregate repositories now own the
  persistence implementation; 33/33 tables have a single owner.
- SQL, schema, signatures, return shapes, transactions, IDs, migration 12,
  active configuration `config-v0.9.0`, API/client contracts, and locale
  parity remain unchanged.
- Verification: static and fresh-database parity PASS; 175 focused; runtime
  restart smoke PASS; 469 passed + 8 skipped; exact `run.bat --verify` PASS.
- All accepted write-capable evidence used guarded fresh temporary databases.
  The development-database incident and isolation hardening are recorded in
  `RUN_VERIFICATION_V0.9.5_E.md`.
- Service Dependency Narrowing remains separately gated and was not started.

## Current v0.9.5-D State

- Status: completed and verified; frontend contract hardening scope closed.
- Twelve feature-owned API Ports under `app/ui/ports/`; each feature depends
  only on its Port; `WritingFeedbackApiClient` is the sole concrete client.
- Endpoint-Client-Feature contract under `tests/contracts/`: 77 endpoints and
  52 client methods fully classified (24 A / 27 B / 26 C endpoints; 24 A /
  27 B / 1 C methods) with documented reasons; AST enforcement tests.
- Practice and Research UI contracts parity-tested against backend schemas.
- Tests migrated off facade private-helper imports; compatibility exports
  retained and marked deprecated (comments only).
- Verification: 19 new tests; focused frontend 220+3; 4/4 renders; 465+8 core;
  `run.bat --verify` PASS; migration 12; `config-v0.9.0`; locale 520/520.
- No API/backend/schema/service/repository/database/UI-content/visual change.
  v0.9.5-E remains not started.
## Current v0.9.5-C State

- Status: completed and verified; frontend feature extraction scope closed.
- Six Student feature modules (`home`, `writing`, `feedback`, `practice`,
  `revision`, `journey`) and six Research feature modules (`overview`,
  `evidence`, `calf`, `learning_process`, `data`, `system_audit`) under
  `app/ui/features/`; shared student helpers owned once by `navigation.py`,
  `formatting.py`, `session.py`.
- `app/ui/pages/student_pages.py` and `research_pages.py` are thin re-export
  facades; renderer names/signatures, page order, session/widget keys,
  data-testids, locale keys, API calls, and payloads unchanged.
- UI boundaries restored: Practice uses `app/ui/contracts/practice.py`;
  Research Data uses `app/ui/contracts/research.py`; a static
  prohibited-import test guards the boundary.
- Verification: inventory parity (13/13, 32/32, 24/24, 7/7, 6/6, 32/32,
  98/98); 15 new tests; focused frontend 200+3; 24/24 browser renders;
  446+8 core; `run.bat --verify` PASS; migration 12; `config-v0.9.0`.
- No API/backend/schema/service/repository/database/UI-content/visual change.
  v0.9.5-D remains not started.
## Current v0.9.5-B State

- Status: completed and verified; API router decomposition scope closed.
- Feature routers exist under `app/api/routers/`; `app/api/main.py` is the
  composition root (creation, lifespan, middleware, error handlers, service
  construction, router inclusion).
- `/api/v1/system/health` is registered exactly once with lifecycle-based
  semantics identical in production and tests; `/live` and `/ready` unchanged.
- Route inventory parity: 77 unique path+method pairs before/after; operation
  IDs, response models, and declared status codes unchanged.
- Verification: 274+3 focused API tests; 431+8 core; minimal runtime smoke PASS;
  exact `run.bat --verify` PASS; migration 12; `config-v0.9.0`.
- Schemas, services, repositories, database, UI, API client, and domain
  semantics unchanged. v0.9.5-C remains not started.
## Current v0.9.4-B State

- Status: completed and verified; Student-only redesign scope closed.
- Six Student pages now share a 720px learner-focused structure: purpose,
  context, steps, evidence, one primary next action, and interpretation limits.
- Writing, Practice, and Revision preserve field-local validation,
  authoritative write paths, saved-state locks, and idempotency. Feedback and
  Journey remain read-oriented; page rendering and navigation create no data.
- English/Simplified Chinese locale parity is 520/520. Focus is 3px `#0f6dbd`;
  desktop/mobile behavior and 44px touch targets are browser-verified.
- Verification: affected 95+1, Student 130+2, core 421+8; controlled
  cross-page flow PASS; Student renders 24/24; Research smoke 6/6; legacy
  Playwright, lifecycle/recovery, and exact `run.bat --verify` PASS.
- Backend/API/database/domain/Research IA unchanged: migration 12,
  `config-v0.9.0`. v0.9.4-C/D and v1.0 remain not started.
- Known out-of-scope backend defect: multi-row `WTR` identifier allocation can
  collide; recorded in `docs/KNOWN_LIMITATIONS.md`.

## Current v0.9.4-A State

- Status: completed (foundation stage; page redesigns deferred to v0.9.4-B/C).
- Hybrid Pixel System 2.0 foundation implemented: canonical `DESIGN_TOKENS`
  (app/ui/pixel_art.py) with generated CSS; Streamlit theme aligned
  (`.streamlit/config.toml`, parity-tested); readable system sans body with
  constrained monospace; primary action red `#e00047` (measured 4.93:1);
  shared spacing/geometry/focus/status/density/responsive tokens; local
  accessible SVG icons; shared component primitives with stable testids.
- Minimal production adoption: Writing required-prompt validation, Run
  Export loading state, Journey-counts table, mono technical captions; two
  hardcoded Chinese-mode Research Data strings localized (382/382 parity).
- No backend/API/database/journey change; migration 12; config-v0.9.0.
- Verified: core pytest 394 passed, 8 skipped; live A–G 20; legacy Playwright
  PASS; lifecycle PASS; run.bat --verify PASS; zh probe 3/3; representative
  24/24; final 48/48 browser renders.
- Design direction recorded: Hybrid Pixel System 2.0 (Direction B).

## Current v0.9.3-C State

- Status: completed; database migration 12; active configuration config-v0.9.0 preserved.
- Learning Journey hardened (UX-001): read-time derivation from authoritative
  source records; no render/locale/refresh events; accurate empty-state
  taxonomy; Student ID normalization + learner-state consistency; practice
  and revision idempotency; conservative revision-response semantics.
- Deterministic demo journey for synthetic learner DEMO-001
  (scripts/demo_journey.py --setup|--status|--cleanup; idempotent; scoped
  cleanup; local provider only; DB backups recorded).
- pytest: 324 passed, 8 skipped; Cases A-R + live validation: 130 passed;
  legacy Playwright harnesses PASS; run.bat --verify PASS (3 cold starts);
  recovery check PASS; 4 locale/viewport combinations clean.
- Journey output makes no mastery/learning-gain/causal/transfer/proficiency/
  CEFR claim.

## Current v0.9.3-B State

- Status: completed; database migration 12; active configuration config-v0.9.0 preserved.
- All eight broken Research endpoints repaired (ERR-001).
- Canonical request-error taxonomy (app/errors.py) with 14 categories.
- Client-side error classification; centralized timeout profiles; bounded GET-only retries.
- Request IDs in responses, error bodies, and sanitized logs.
- Role-appropriate Student/Research error presentation; 295 locale keys en/zh parity.
- pytest: 314 passed, 8 skipped; Cases A-R: 110 passed.
- run.bat --verify: PASS. Legacy live harnesses: PASS when run as designed.

v1.0 remains not_started.


---

# Project State

## Current v0.9.3-A State

- Status: in_progress; database migration 12; active configuration config-v0.9.0 preserved.
- Lifecycle-aware startup: FastAPI lifespan replaces module-level create_app(). Heavy
  initialization (spaCy, DB, services) runs after server is live.
- New endpoints: /api/v1/system/live (liveness), /api/v1/system/ready (readiness).
- Health endpoint enhanced with lifecycle_state and startup_elapsed_ms.
- API client timeout: 90s -> 15s. Stale process cleanup on startup.
- Streamlit shows lifecycle state (starting vs unavailable).
- pytest: 289 passed, 8 skipped (v0.9.2.1 baseline: 271 passed, 8 skipped).
- REL-001 (startup hang) fixed. Backend unchanged after readiness.

v1.0 remains not_started.


---

# Project State

## Current v0.9.2 State

- Status: in_progress; database migration 12; active configuration config-v0.9.0 preserved.
- Pixel Art UI: complete redesign with centralized CSS token system, 7-color palette,
  hard offset shadows, square corners, monospace typography, no transitions.
- Role-based UI: Student View (6 pages) + Research View (6 pages) with progressive disclosure.
- Reusable component library redesigned with pixel-art styling.
- 271 locale keys (en + zh_CN), identical sets, all UI strings localized.
- pytest: 271 passed, 8 skipped (identical to v0.9.1 baseline).
- All backend APIs, practice-domain behavior, migration, and configuration unchanged.

v1.0 remains not_started.


---

# Project State

## Current v0.9.1 State

- Status: completed; database migration 12; active configuration config-v0.9.0 preserved.
- Role-based UI: Student View (6 pages) + Research View (6 pages) with progressive disclosure.
- Reusable component system, responsive layout (desktop to 390x844 mobile), accessible contrast.
- 271 locale keys (en + zh_CN), identical sets, all UI strings localized.
- pytest: 271 passed, 8 skipped (3 v0.9.1 skips for restructured AppTest UI tests).
- Playwright: desktop + mobile role-based navigation, locale switching, console/horizontal-overflow checks.
- All backend APIs, practice-domain behavior, migration, and configuration unchanged from v0.9.

v1.0 remains not_started.
