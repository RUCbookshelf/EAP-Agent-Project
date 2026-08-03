# v0.9.5-H1 - Persistence Protocol Inventory and Consolidation Plan

**Status:** COMPLETE (read-only source-authoritative architecture audit; evidence and plan only)

**Baseline:** branch `master`, HEAD `fc2e8e93b06b5a99ab841e115c8e12570f8f67b8` (v0.9.5-G verification commit)
**Stage scope:** inventory every persistence-related Protocol/ABC/structural contract/type alias/union/infrastructure-internal reader at HEAD; map consumers and concrete implementations; build method-level overlap matrix; assess naming collisions, legacy contracts, API-owned Ports, Practice Ports, infrastructure readers, runtime-checkable usage, and import direction; produce a dependency-ordered H2 implementation plan. No production code, test, Protocol, Repository, SQL, transaction, API, schema, provider, prompt, UI, or localization file was modified.

---

## 1. Method and evidence

Source at HEAD `fc2e8e9` is authoritative. Earlier audits (F1, F6C, G specs/reports) were used only as hypothesis sources and are cross-referenced where they differ.

Evidence forms used (>=2 per conclusion where practical):

- Full AST scan of all 287 non-ignored Python modules (definitions, decorators, imports, annotations, base classes, isinstance/issubclass calls, symbol scopes).
- Text search (`Select-String`) for every contract name across `app/`, `tests/`, `scripts/`, `verification/`.
- Direct source reading of all definition modules and every production composition/consumption site.
- GitNexus bounded graph analysis (2 rounds): `query` (degraded - FTS indexes missing; recorded) and `context(RevisionRepository)`; index confirmed up-to-date at `fc2e8e9`.
- One Code Review Graph CLI attempt: failed with the documented `uv trampoline failed to canonicalize script path` defect; recorded, not repaired; analysis continued with AST/static search, source inspection, and GitNexus.
- Existing focused contract tests (Phase 5) run under mandatory database isolation.

**Excluded by spec** (recorded separately in `protocol_inventory.json -> excluded_definitions`): analyzer/provider Protocols (`AnalyzerProtocol`, `MetricCalculator`, `Analyzer`, `Diagnoser`, `LLMProvider`), frontend contracts (`app/ui/ports/*` 12 ApiPorts), Pydantic schemas, pure domain interfaces, git-ignored `*-冲突-Rain_Win11.py` conflict copies (verified ignored via `git check-ignore`; contain confusingly named `SubmissionRepository`/`ConfigurationRepository` copies), and test-only stubs.

## 2. Baseline record

| Item | Value |
| --- | --- |
| Branch | `master` |
| HEAD | `fc2e8e93b06b5a99ab841e115c8e12570f8f67b8` |
| G implementation / verification ancestry | `b165943` refactor(v0.9.5-g) / `fc2e8e9` test(v0.9.5-g) |
| Database public surface | 2 (`connect`, `initialize`) |
| API contract | 77 unique path+method pairs |
| Frontend client contract | 52 public methods |
| Locale parity | 520/520 |
| Migration / tables | 12 / 33 |
| Active configuration / feedback prompt | `config-v0.9.0` / `feedback-prompt-v0.7.1` |
| Full-core baseline (G verification report) | 653 passed, 8 skipped, 2 warnings |
| F2-F6D dependency contract baseline (G report) | 437 passed, 2 skipped, 2 warnings |
| Development database | SHA-256 `340E0F3739FEFFD3DEF87BB6E711CB6F90A8478E7E18D833C715EDCFAB03AFF4`, size 8,298,496 bytes, mtime 2026-08-02T11:02:25.887+08:00 (unchanged; never opened) |
| Preserved user-owned paths | `AGENTS.md`, `RUN_VERIFICATION_V0.7.md`, `RUN_VERIFICATION_V0.8.2.md`, `.claude/`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`, `CLAUDE.md`, `data/demo_journey_manifest.json` (untouched, uncommitted) |

`git status --short` at baseline (preserved user-owned only):

```text
 M AGENTS.md
 M RUN_VERIFICATION_V0.7.md
 M RUN_VERIFICATION_V0.8.2.md
?? .claude/
?? ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md
?? CLAUDE.md
?? data/demo_journey_manifest.json
```

## 3. Inventory summary

Total persistence-related contracts: **55**.

| Contract kind | Count |
| --- | --- |
| alias | 1 |
| combined_class | 1 |
| plain_class | 1 |
| protocol | 52 |

| Primary classification | Count |
| --- | --- |
| A | 37 |
| B | 1 |
| C | 4 |
| G | 13 |

Classification legend: A = active exact consumer-owned contract; B = active reusable canonical aggregate contract; C = active infrastructure-internal contract; D = exact duplicate with no independent semantic value; E = overlapping but semantically distinct consumer contract; F = broad/inherited beyond call set; G = stale or unused; H = misleading name or ownership location; I = unresolved.

- Active contracts (A/B/C): **42**
- Unused-contract candidates (G): **13**
- Runtime-checkable contracts: **36** (all A/B service/API/Practice Ports; none of the central or infrastructure-internal contracts)
- Infrastructure-internal contracts (C): **4**
- Contracts with no production reference at all: **5**

## 4. Full contract inventory

### 4.1 Central aggregate Protocols - `app/repositories/protocols.py`

| Contract | Line | Methods | Class. | Disposition | Production consumers |
| --- | --- | --- | --- | --- | --- |
| `StudentRepository` | 11 | get_student | **G** | remove (H2A) | app.repositories.__init__ |
| `EssayRepository` | 15 | save_essay, get_submission_bundle, list_student_submissions | **G** | remove (H2A) | app.repositories.__init__, app.services.submission |
| `MetricRepository` | 21 | save_analysis, save_analysis_run, list_analysis_runs, get_latest_analysis_run, list_analysis_units | **G**+H | remove (H2A) | app.repositories.__init__, app.services.submission |
| `ErrorAnnotationRepository` | 29 | save_error_annotations, list_error_annotations | **G** | remove (H2A) | none |
| `DiagnosisRepository` | 34 | save_diagnosis | **G** | remove (H2A) | app.repositories.__init__, app.services.submission |
| `FeedbackRepository` | 38 | save_feedback | **G** | remove (H2A) | app.repositories.__init__, app.services.submission |
| `ExerciseRepository` | 42 | get_exercises | **G** | remove (H2A) | app.repositories.__init__ |
| `LearnerHistoryRepository` | 46 | prior_records, save_history, list_student_history | **G**+H | remove (H2A) | app.repositories.__init__, app.services.submission |
| `LearnerProfileRepository` | 52 | get_latest_learner_profile, save_learner_profile_snapshot, list_learner_profile_snapshots, list_longitudinal_records, list_visualization_records, list_history_evidence | **G** | remove (H2A) | app.repositories.__init__ |
| `RevisionRepository` | 61 | get_submission_bundle, get_latest_analysis_run, create_revision_group, link_revision, get_revision_group, get_revision_group_for_submission, list_revision_candidates, save_revision_snapshot, list_revision_snapshots, get_latest_revision_snapshot | **B** | keep | app.repositories.__init__, app.services.admin_reanalysis, app.services.factory, app.services.revision, tests.test_v095f6a0_revision_capability_completion, tests.test_v095f6b_admin_reanalysis_narrowing |
| `ConfigurationRepository` | 74 | ping, migration_version | **G**+H | remove (H2A) | app.repositories.__init__, app.services.configuration |
| `SystemVersionRepository` | 79 | record_versions, get_system_versions | **G** | remove (H2A) | app.repositories.__init__, app.services.submission |
| `SubmissionRepositories` | 84 | (union alias) | **G** | remove (H2A) | none |

Findings: `RevisionRepository` is the only active central aggregate contract (used by `RevisionService`, `AdminReanalysisService`, `build_submission_service`; unchanged by F6A0/F6A). The other 11 central Protocols and the `SubmissionRepositories` union have no production consumer: they are referenced only by their own re-export (`app/repositories/__init__.py`), the union declaration, and the unused legacy `SubmissionRepository` class. `ErrorAnnotationRepository` is not even re-exported (zero references). `MetricRepository.list_analysis_units` is a CALF-owned method misplaced in an Analysis contract (its active semantics live in `CalfDataPort`/`CalfReadPort`). `LearnerHistoryRepository` spans Submission ownership (`prior_records`, `save_history`) and Learner ownership (`list_student_history`).

### 4.2 API-owned Ports - `app/api/ports.py` (10)

| Contract | Line | Methods | Class. | Runtime satisfier |
| --- | --- | --- | --- | --- |
| `SubmissionBundleReadPort` | 18 | get_submission_bundle | **A** | app.infrastructure.sqlite.repositories.submission::SQLiteSubmissionRepository |
| `StudentLookupPort` | 25 | get_student | **A** | app.infrastructure.sqlite.repositories.learner::SQLiteLearnerRepository |
| `AnalysisRunReadPort` | 32 | list_analysis_runs | **A** | app.infrastructure.sqlite.repositories.analysis::SQLiteAnalysisRepository |
| `CalfReadPort` | 39 | list_analysis_units, list_error_annotations | **A** | app.infrastructure.sqlite.repositories.calf::SQLiteCalfRepository |
| `ResearchExportWritePort` | 48 | save_export_job | **A** | app.infrastructure.sqlite.repositories.research::SQLiteResearchRepository |
| `StudentSubmissionListPort` | 55 | list_student_submissions | **A** | app.infrastructure.sqlite.repositories.submission::SQLiteSubmissionRepository |
| `RevisionGroupLookupPort` | 62 | get_revision_group_for_submission | **A** | app.infrastructure.sqlite.repositories.revision::SQLiteRevisionRepository |
| `StudentLearnerReadPort` | 69 | list_student_history, list_history_evidence, list_learner_profile_snapshots | **A** | app.infrastructure.sqlite.repositories.learner::SQLiteLearnerRepository |
| `SubmissionCalibrationReadPort` | 80 | get_diagnostic_calibration | **A** | app.infrastructure.sqlite.repositories.calf::SQLiteCalfRepository |
| `SystemMigrationPort` | 87 | migration_version | **A** | app.infrastructure.sqlite.repositories.system::SQLiteSystemRepository |

All ten are exact, `@runtime_checkable`, and enforced by `tests/test_v095g_facade_contraction.py`. Production runtime path: `app/api/deps.py` getters return `request.app.state.<reader>` attributes (wired in `app/api/main.py` to the exact facade-owned repositories); Routers never import the Ports. The Port types themselves are currently referenced only in tests - no production annotation references them. Each maps 1:1 to one facade-owned aggregate repository. This is a documentation/enforcement gap (recorded under H2D), not a correctness defect: `Depends(get_repository)` count in production is 0 and no Router receives the broad facade.

### 4.3 Service-owned consumer Ports (24)

| Contract | Module | Methods | Class. | Runtime satisfier |
| --- | --- | --- | --- | --- |
| `CalfDataPort` | app.services.calf | list_analysis_units, list_error_annotations, save_error_annotations | **A** | app.infrastructure.sqlite.repositories.calf::SQLiteCalfRepository |
| `CalfSubmissionReadPort` | app.services.calf | get_submission_bundle, list_student_submissions | **A** | app.infrastructure.sqlite.repositories.submission::SQLiteSubmissionRepository |
| `CalfAnalysisReadPort` | app.services.calf | get_latest_analysis_run | **A** | app.infrastructure.sqlite.repositories.analysis::SQLiteAnalysisRepository |
| `CalfStudentReadPort` | app.services.calf | get_student | **A** | app.infrastructure.sqlite.repositories.learner::SQLiteLearnerRepository |
| `ResearchSubmissionReadPort` | app.research.service | list_all_submissions, list_student_submissions, get_submission_bundle | **A** | app.infrastructure.sqlite.repositories.submission::SQLiteSubmissionRepository |
| `ResearchReviewPort` | app.research.service | save_human_review, list_human_reviews, apply_pii_review | **A** | app.infrastructure.sqlite.repositories.research::SQLiteResearchRepository |
| `ResearchExportReadPort` | app.research.service | list_export_jobs, get_export_job | **A** | app.infrastructure.sqlite.repositories.research::SQLiteResearchRepository |
| `AdminConfigurationReadPort` | app.services.admin_reanalysis | get_configuration | **A** | app.infrastructure.sqlite.repositories.configuration::SQLiteConfigurationRepository |
| `AdminSubmissionReadPort` | app.services.admin_reanalysis | get_submission_bundle, list_student_submissions | **A** | app.infrastructure.sqlite.repositories.submission::SQLiteSubmissionRepository |
| `AdminAnalysisPort` | app.services.admin_reanalysis | get_analysis_run, save_analysis_run | **A** | app.infrastructure.sqlite.repositories.analysis::SQLiteAnalysisRepository |
| `SubmissionSystemPort` | app.services.submission | record_versions | **A** | app.infrastructure.sqlite.repositories.system::SQLiteSystemRepository |
| `SubmissionDataPort` | app.services.submission | save_essay, prior_records, get_submission_bundle, save_feedback, save_history | **A** | app.infrastructure.sqlite.repositories.submission::SQLiteSubmissionRepository |
| `SubmissionAnalysisPort` | app.services.submission | save_analysis_run, save_analysis, save_diagnosis | **A** | app.infrastructure.sqlite.repositories.analysis::SQLiteAnalysisRepository |
| `SubmissionCalibrationPort` | app.services.submission | save_diagnostic_calibration, get_diagnostic_calibration | **A** | app.infrastructure.sqlite.repositories.calf::SQLiteCalfRepository |
| `SubmissionBundleReadPort` | app.services.reanalysis | get_submission_bundle | **A** | app.infrastructure.sqlite.repositories.submission::SQLiteSubmissionRepository |
| `AnalysisRunWritePort` | app.services.reanalysis | save_analysis_run | **A** | app.infrastructure.sqlite.repositories.analysis::SQLiteAnalysisRepository |
| `LearnerProfileReadPort` | app.services.learner_profile | get_latest_learner_profile, list_learner_profile_snapshots | **A** | app.infrastructure.sqlite.repositories.learner::SQLiteLearnerRepository |
| `LearnerProgressPort` | app.services.progress | list_visualization_records, save_learner_profile_snapshot | **A** | app.infrastructure.sqlite.repositories.learner::SQLiteLearnerRepository |
| `ActiveConfigurationPort` | app.services.progress | get_active_configuration | **A** | app.infrastructure.sqlite.repositories.configuration::SQLiteConfigurationRepository |
| `DashboardReadPort` | app.services.dashboard | list_visualization_records | **A** | app.infrastructure.sqlite.repositories.learner::SQLiteLearnerRepository |
| `PriorRecordsPort` | app.learner.history | prior_records | **A** | app.infrastructure.sqlite.repositories.submission::SQLiteSubmissionRepository |
| `JourneyStudentReadPort` | app.journey.service | get_student | **A** | app.infrastructure.sqlite.repositories.learner::SQLiteLearnerRepository |
| `JourneyProjectionReadPort` | app.journey.service | list_essays_by_student, list_analysis_runs_for_student, list_feedback_records_for_student, list_practice_targets, list_exercise_attempts_by_student, list_practice_evaluations_by_student, list_within_task_responses, list_transfer_evidence_candidates | **A** | app.infrastructure.sqlite.repositories.practice::SQLitePracticeRepository |
| `ConfigurationRepository` | app.services.configuration | list_configurations, get_configuration, get_active_configuration, create_configuration, set_configuration_validation, activate_configuration, list_configuration_audit | **A** | app.infrastructure.sqlite.repositories.configuration::SQLiteConfigurationRepository |
| `SubmissionRepository` | app.services.submission |  | **G** | app.infrastructure.sqlite.repositories.submission::SQLiteSubmissionRepository |

All 24 are active, exact consumer-owned contracts: each method set equals the constructor annotation used by its owning Service. `app/services/configuration.py:ConfigurationRepository` is the authoritative 7-method structural contract for `ConfigurationService` (plain class, not a Protocol) and is **not** the same contract as the stale central `ConfigurationRepository` Protocol (see 6.1).

### 4.4 Practice Ports - `app/practice/ports.py` (3)

| Contract | Line | Methods | Class. | Runtime satisfier |
| --- | --- | --- | --- | --- |
| `PracticeSubmissionReadPort` | 14 | get_submission_bundle | **A** | app.infrastructure.sqlite.repositories.submission::SQLiteSubmissionRepository |
| `PracticeReadPort` | 21 | list_practice_targets, get_practice_target, list_exercise_instances, get_exercise_instance, list_exercise_attempts, list_feedback_engagement_traces, list_transfer_evidence_candidates | **A** | app.infrastructure.sqlite.repositories.practice::SQLitePracticeRepository |
| `PracticeWritePort` | 40 | save_practice_target, save_exercise_instance, save_exercise_attempt, save_practice_evaluation | **A** | app.infrastructure.sqlite.repositories.practice::SQLitePracticeRepository |

Read/write separation (`PracticeReadPort` vs `PracticeWritePort`) is intentional per F6D: the Practice Router consumes reads and writes as distinct capabilities and `PracticeService` is pure. The Ports must not be collapsed. `PracticeSubmissionReadPort` is an intentional consumer-owned duplication of the Submission bundle read.

### 4.5 Infrastructure-internal readers (4)

| Contract | Module:Line | Methods | Class. | Injected into |
| --- | --- | --- | --- | --- |
| `_SubmissionBundleReader` | app.infrastructure.sqlite.repositories.revision:10 | get_submission_bundle | **C** | Injected into SQLiteRevisionRepository; same single method as three consumer bundle-read Ports. |
| `_AnalysisRunReader` | app.infrastructure.sqlite.repositories.revision:14 | get_latest_analysis_run | **C** | Exact duplicate of learner.py:_AnalysisRunReader; both injected as readers. |
| `_AnalysisRunReader` | app.infrastructure.sqlite.repositories.learner:12 | get_latest_analysis_run | **C** | Exact duplicate of revision.py:_AnalysisRunReader. |
| `_DiagnosticCalibrationReader` | app.infrastructure.sqlite.repositories.learner:16 | get_diagnostic_calibration | **C** | Injected into SQLiteLearnerRepository. |

`_AnalysisRunReader` is defined twice with identical signatures (`revision.py:14`, `learner.py:12`) - an exact duplicate pair (H2C canonicalization candidate). `_SubmissionBundleReader` and `_DiagnosticCalibrationReader` are single-definition and correctly placed.

### 4.6 Legacy structural contract

`app/services/submission.py:78` defines `SubmissionRepository` (empty class inheriting `EssayRepository`, `MetricRepository`, `DiagnosisRepository`, `FeedbackRepository`, `LearnerHistoryRepository`, `SystemVersionRepository`) as a "Combined structural contract for the atomic submission workflow". It survives F6C but has **no production consumer**: no module imports or instantiates it; `SubmissionService` uses the four F6C Ports; `build_submission_service` and `FeedbackPipeline` use the Ports/facade-owned repositories. `tests/test_v095f6c_submission_service_narrowing.py` asserts its absence from `SubmissionService` annotations, constructor AST, and factory source. It can be deleted without replacement in H2A.

## 5. Concrete implementations and structural satisfaction

| Implementation | Module | Kind | Notes |
| --- | --- | --- | --- |
| `SQLiteConnectionManager` | app.infrastructure.sqlite.connection | connection_manager | public methods: __init__, connect, transaction |
| `SQLiteSystemRepository` | app.infrastructure.sqlite.repositories.system | concrete_repository | public methods: __init__, connect, initialize, record_versions, counts, ping, migration_version, transaction, get_system_versions |
| `SQLiteConfigurationRepository` | app.infrastructure.sqlite.repositories.configuration | concrete_repository | public methods: __init__, _configuration_from_row, list_configurations, get_configuration, get_active_configuration, create_configuration, set_configuration_validation, activate_configuration, list_configuration_audit, _insert_configuration_audit |
| `SQLiteAnalysisRepository` | app.infrastructure.sqlite.repositories.analysis | concrete_repository | public methods: __init__, save_analysis, save_analysis_run, list_analysis_runs, get_latest_analysis_run, get_analysis_run, get_metric_results, get_analysis_artifact, save_diagnosis |
| `SQLiteCalfRepository` | app.infrastructure.sqlite.repositories.calf | concrete_repository | public methods: __init__, save_diagnostic_calibration, get_diagnostic_calibration, list_analysis_units, save_error_annotations, list_error_annotations |
| `SQLiteSubmissionRepository` | app.infrastructure.sqlite.repositories.submission | concrete_repository | public methods: __init__, save_essay, save_feedback, save_history, prior_records, get_feedback_record, get_llm_calls, get_history_record, list_all_submissions, get_submission_bundle, list_student_submissions, get_exercises |
| `SQLiteRevisionRepository` | app.infrastructure.sqlite.repositories.revision | concrete_repository | public methods: __init__, get_submission_bundle, get_latest_analysis_run, normalize_revision_stage, create_revision_group, link_revision, get_revision_group, get_revision_group_for_submission, list_revision_candidates, save_revision_snapshot, list_revision_snapshots, get_latest_revision_snapshot |
| `SQLiteLearnerRepository` | app.infrastructure.sqlite.repositories.learner | concrete_repository | public methods: __init__, get_student, list_all_students, list_student_history, get_latest_learner_profile, save_learner_profile_snapshot, list_history_evidence, list_learner_profile_snapshots, list_longitudinal_records, list_visualization_records |
| `SQLitePracticeRepository` | app.infrastructure.sqlite.repositories.practice | concrete_repository | public methods: __init__, _next_practice_id, save_practice_target, list_practice_targets, get_practice_target, save_exercise_instance, list_exercise_instances, get_exercise_instance, save_exercise_attempt, list_exercise_attempts, save_practice_evaluation, list_practice_evaluations, list_practice_evaluations_by_student, list_essays_by_student... |
| `SQLiteResearchRepository` | app.infrastructure.sqlite.repositories.research | concrete_repository | public methods: __init__, _next_research_id, save_human_review, list_human_reviews, apply_pii_review, save_export_job, list_export_jobs, get_export_job |
| `Database` | app.database.repository | facade | public methods: __init__, connect, initialize, _add_column_if_missing, _migrate_v0_1_to_v0_1_1 |

- `Database` (facade) now exposes only `connect`, `initialize`; it structurally satisfies **no** persistence Port at HEAD (all 55 contracts return `database_still_satisfies=false`). All satisfaction is delegated to the nine facade-owned `SQLite*Repository` instances sharing one `SQLiteConnectionManager`.
- Every active contract (A/B/C) has exactly one intended concrete satisfier among the nine facade-owned repositories; each is asserted at runtime by its stage contract test (`test_v095f2` through `test_v095g_facade_contraction`).
- Stale central Protocols are also structurally satisfied by the same repositories (e.g., `EssayRepository` -> `SQLiteSubmissionRepository`, `MetricRepository` -> `SQLiteAnalysisRepository`/`SQLiteCalfRepository`), which confirms they are removable without replacement.
- Extra methods on concrete repositories are not defects; every consumer contract is minimal and structurally satisfied (missing-method/signature-mismatch count: 0 across the 42 active contracts; verified by the focused stage suites).

## 6. Required rechecks

### 6.1 Configuration naming collision - CONFIRMED (resolved by H2A)

Two contracts named `ConfigurationRepository` still exist with different method sets:

| Definition | Kind | Methods | Status |
| --- | --- | --- | --- |
| `app/repositories/protocols.py:74` | Protocol | `ping`, `migration_version` | Stale: no production or test consumer (re-export + union only) |
| `app/services/configuration.py:14` | plain class | 7 configuration methods | **Authoritative** for `ConfigurationService` (`__init__` annotation at line 25); exactly satisfied by `SQLiteConfigurationRepository` |

Recommended: remove the stale central Protocol in H2A (which eliminates the collision), then rename the local 7-method contract to a `ConfigurationPort`-style name in H2B so no ambiguous `ConfigurationRepository` name remains.

### 6.2 Legacy `SubmissionRepository` - EXISTS, REMOVABLE

- Still exists after F6C at `app/services/submission.py:78` (inherits 6 stale central Protocols).
- No production symbol imports it; no constructor uses it; no script/verification module uses it; no test positively imports it (F6C tests assert its absence).
- Its inherited method set (6 Protocols, 17 methods) far exceeds the active `SubmissionService` Port union (11 methods).
- **Can be deleted in H2A without replacement**, together with the 6 inherited Protocols (and the 5 remaining stale central Protocols + alias).

### 6.3 Revision and cross-aggregate method overlap

`get_submission_bundle` is declared by 10 contracts and `get_latest_analysis_run` by 5; both have identical signatures everywhere. The repetitions are:

- `RevisionRepository` (central aggregate, active) - keep unchanged (F6A0/F6A boundary).
- `_SubmissionBundleReader` / `_AnalysisRunReader` (infrastructure readers injected into `SQLiteRevisionRepository` and `SQLiteLearnerRepository`) - active infrastructure-internal contracts; keep. `_AnalysisRunReader` is the only exact duplicate pair (H2C candidate).
- Consumer-owned Ports (`SubmissionBundleReadPort` x2 - API and reanalysis, `PracticeSubmissionReadPort`, `CalfSubmissionReadPort`, `AdminSubmissionReadPort`, `ResearchSubmissionReadPort`, `SubmissionDataPort`, `CalfAnalysisReadPort`) - intentional bounded-context duplication per the "Port belongs to the consumer" principle; do **not** consolidate.
- Stale central declarations (`EssayRepository`, `MetricRepository`) - removed with H2A.

### 6.4 Metric/CALF ownership

`MetricRepository.list_analysis_units` (Analysis-named contract declaring a CALF-owned method) is confirmed present at HEAD, but `MetricRepository` is stale (no consumer). The active CALF declarations live in `CalfDataPort` (service) and `CalfReadPort` (API). No consolidation is needed beyond removing the stale central Protocol in H2A; the method's ownership question is already resolved by the active CALF Ports.

### 6.5 Learner history ownership

`LearnerHistoryRepository` (stale) spans Submission (`prior_records`, `save_history`) and Learner (`list_student_history`) ownership. The active landscape already separates these: `PriorRecordsPort` + `SubmissionDataPort` (Submission), `StudentLearnerReadPort` (Learner). No active contract spans both owners; H2A removal of the stale Protocol completes the separation.

### 6.6 Dashboard and learner read contracts

`DashboardReadPort.list_visualization_records` duplicates `LearnerProgressPort.list_visualization_records` and the stale central `LearnerProfileRepository.list_visualization_records` with identical signatures. The Dashboard duplication is **intentional consumer ownership** (DashboardService needs exactly one read; ProgressService additionally writes snapshots), and the central declaration is stale (H2A). Keep `DashboardReadPort` and `LearnerProgressPort` separate.

### 6.7 Potentially unused central contracts - CONFIRMED

`StudentRepository`, `ExerciseRepository`, `ErrorAnnotationRepository` have no consumer of any kind; `LearnerProfileRepository`, `EssayRepository`, `MetricRepository`, `DiagnosisRepository`, `FeedbackRepository`, `LearnerHistoryRepository`, `SystemVersionRepository`, central `ConfigurationRepository`, and `SubmissionRepositories` have no production consumer (only re-export/union/legacy-base references). All 13 are H2A removal candidates. `RevisionRepository` remains active.

### 6.8 API-owned Ports - assessed

All ten are exact and each has a live Router dependency path (`deps.get_*` -> `app.state.*` -> facade-owned repository). None is unused; none duplicates a Service Port in a way that should be consolidated (API-owned contract domain is deliberate; G spec). Module location `app/api/ports.py` and import direction (api -> api; no service imports it) are valid. The only finding: the Port types are referenced by tests only, not by production annotations (H2D optional improvement; not required).

### 6.9 Practice Ports - assessed

`PracticeSubmissionReadPort`, `PracticeReadPort`, `PracticeWritePort` are exact, active, and their read/write separation is intentional (F6D). They must not be collapsed and do not duplicate any Service Port beyond the intentional Submission bundle read.

## 7. Method-level overlap matrix (29 methods with >1 declaration)

Full rows are in `verification/v0.9.5-h1/protocol_overlap_matrix.json`. Highlights:

| Method | Declarations | Identical signature | Recommended canonical owner |
| --- | --- | --- | --- |
| `get_active_configuration` | 2 | no | Configuration; ActiveConfigurationPort + local ConfigurationRepository intentional |
| `get_configuration` | 2 | no | Configuration; AdminConfigurationReadPort + local ConfigurationRepository intentional |
| `get_diagnostic_calibration` | 3 | yes | CALF; SubmissionCalibrationPort/SubmissionCalibrationReadPort/_DiagnosticCalibrationReader intentional |
| `get_latest_analysis_run` | 5 | yes | keep consumer-owned; no canonical owner (5 declarations) |
| `get_latest_learner_profile` | 2 | yes | Learner; LearnerProfileReadPort intentional |
| `get_revision_group_for_submission` | 2 | yes | Revision; RevisionRepository + RevisionGroupLookupPort intentional |
| `get_student` | 4 | yes | keep consumer-owned; no canonical owner (4 declarations) |
| `get_submission_bundle` | 10 | yes | keep consumer-owned; no canonical owner (10 declarations, 5 bounded contexts) |
| `list_analysis_runs` | 2 | yes | Analysis; AnalysisRunReadPort + stale MetricRepository (removed H2A) |
| `list_analysis_units` | 3 | yes | CALF-owned canonical owner would be CalfDataPort/CalfReadPort; stale MetricRepository declaration removed in H2A |
| `list_error_annotations` | 3 | yes | CALF; stale ErrorAnnotationRepository removed in H2A |
| `list_history_evidence` | 2 | yes | Learner; StudentLearnerReadPort intentional |
| `list_learner_profile_snapshots` | 3 | yes | Learner; StudentLearnerReadPort/LearnerProfileReadPort intentional |
| `list_practice_targets` | 2 | yes | Practice; PracticeReadPort + JourneyProjectionReadPort intentional |
| `list_student_history` | 2 | yes | Learner; StudentLearnerReadPort intentional |
| `list_student_submissions` | 5 | yes | keep consumer-owned; no canonical owner |
| `list_transfer_evidence_candidates` | 2 | yes | Practice; PracticeReadPort + JourneyProjectionReadPort intentional |
| `list_visualization_records` | 3 | yes | Learner; LearnerProgressPort/DashboardReadPort intentional |
| `migration_version` | 2 | yes | System; SystemMigrationPort + stale central ConfigurationRepository (removed H2A) |
| `prior_records` | 3 | yes | Submission-owned; PriorRecordsPort + SubmissionDataPort intentional |
| `record_versions` | 2 | yes | System; SubmissionSystemPort intentional (single consumer) |
| `save_analysis` | 2 | yes | Analysis; stale MetricRepository removed in H2A |
| `save_analysis_run` | 4 | yes | Analysis; multiple consumer ports intentional (Append-only writer) |
| `save_diagnosis` | 2 | yes | Analysis; stale MetricRepository removed in H2A |
| `save_error_annotations` | 2 | yes | CALF; stale ErrorAnnotationRepository removed in H2A |
| `save_essay` | 2 | yes | Submission; stale EssayRepository removed in H2A |
| `save_feedback` | 2 | yes | Submission; stale FeedbackRepository removed in H2A |
| `save_history` | 2 | yes | Submission; SubmissionDataPort intentional |
| `save_learner_profile_snapshot` | 2 | yes | Learner; LearnerProgressPort intentional |

Contract-level exact-duplicate groups: 4x { `get_student` } -> CalfStudentReadPort, JourneyStudentReadPort, StudentLookupPort, StudentRepository; 4x { `get_submission_bundle` } -> PracticeSubmissionReadPort, SubmissionBundleReadPort, SubmissionBundleReadPort, _SubmissionBundleReader; 3x { `get_latest_analysis_run` } -> CalfAnalysisReadPort, _AnalysisRunReader, _AnalysisRunReader; 2x { `get_diagnostic_calibration` } -> SubmissionCalibrationReadPort, _DiagnosticCalibrationReader; 2x { `get_submission_bundle`, `list_student_submissions` } -> AdminSubmissionReadPort, CalfSubmissionReadPort. Every such group is intentional consumer-owned duplication except the `_AnalysisRunReader` pair (H2C) and the stale central declarations (H2A).

Name collisions: `ConfigurationRepository` (2 definitions: app.repositories.protocols:74, app.services.configuration:14); `SubmissionBundleReadPort` (2 definitions: app.api.ports:18, app.services.reanalysis:11); `_AnalysisRunReader` (2 definitions: app.infrastructure.sqlite.repositories.revision:14, app.infrastructure.sqlite.repositories.learner:12). All three are resolved or narrowed by H2A/H2B/H2C.

## 8. runtime_checkable and runtime-check analysis

- Runtime-checkable contracts: **36** (all consumer-owned Service/API/Practice Ports). Central aggregate Protocols and infrastructure-internal readers are intentionally not runtime-checkable.
- Runtime structural checks (`isinstance`/`issubclass`) against these contracts exist **only in tests** (stage contract tests); no production module performs a runtime structural check against any Port. Removing `@runtime_checkable` would break the focused contract tests; keeping it is required.
- Signature parity is separately asserted by the stage tests (`test_exact_names_methods_and_source_signatures`, `test_concrete_repositories_and_facade_structurally_satisfy_ports` in F4-F6D suites; `test_v095g_facade_contraction` for API Ports).

## 9. Import-direction analysis

- `app/repositories/protocols.py` imports only domain models (`app.core`, `app.models`, `app.revision`, `app.calf`) - no cycle risk; a canonical aggregate module location is valid.
- `app/services/*` import `app.repositories` (Ports) and domain modules; `app/services` never imports `app.database` (enforced by `tests/test_architecture_v02.py`).
- `app/api/ports.py` imports domain models only; `app/api/deps.py` imports no Port (the H2D optional annotation change would keep api -> api).
- `app/infrastructure/sqlite/repositories/*` import domain models + `SQLiteConnectionManager`; a shared `_readers.py` module (H2C) would be infra -> infra, allowed.
- `app/database/repository.py` imports infrastructure; `app/api/main.py` imports `app.database` + services; `app/feedback/service.py` imports `app.database` (composition path). No forbidden cycle exists (services -> api, repositories -> services, infrastructure -> application, domain -> FastAPI, or bounded-context cross-coupling).

## 10. H2 implementation plan (dependency-ordered; NOT authorized)

Ranked units (full fields in `verification/v0.9.5-h1/h2_candidate_plan.json`):

1. **H2A - remove proven-unused legacy contracts** (risk low; removes legacy `SubmissionRepository`, 11 stale central Protocols, `SubmissionRepositories` alias; resolves the `ConfigurationRepository` name collision; 3 production files + 1 focused test; reversible in one commit).
2. **H2B - resolve the remaining naming collision** (rename the authoritative local `ConfigurationRepository` to a consumer-owned `ConfigurationPort` name; annotation-only; 1-2 production files + 1 test).
3. **H2C - canonicalize the exact `_AnalysisRunReader` duplicate** (one shared infrastructure reader module; 2 infra files + 1 test).
4. **H2D - relocate/formalize misplaced active contracts** (optional: annotate `deps.py` helpers with the ten API-owned Ports so they are production-referenced; optionally convert the local plain-class contract to `@runtime_checkable Protocol`).
5. **H2E - final contract freeze and documentation** (post-H2 inventory refresh + frozen-contract checks).

**Recommended first unit: H2A.** Rationale: Independently executable; zero production consumers; no runtime behavior change; bounded file set (3 production files + 1 test); resolves the ConfigurationRepository name collision as a side effect; reversible in one implementation commit; does not touch Repository implementations, SQL, transactions, API contracts, or any active contract.

Not recommended (evidence-based): merging the identical `get_submission_bundle`/`get_student`/`get_latest_analysis_run` Ports across bounded contexts; collapsing Practice read/write Ports; consolidating API and Service Ports solely because methods match; moving all Protocols into one central file.

## 11. Phase 5 focused validation

- All four JSON artifacts parse as UTF-8 with deterministic ordering; counts reconcile (55 contracts = 52 Protocol + 1 alias + 1 plain class + 1 combined class; A=37, B=1, C=4, G=13; active=42, unused candidates=13).
- Every overlap row references inventoried contracts (0 unresolved); every H2 candidate references inventoried contracts; every reported consumer module exists in the AST module registry.
- `git diff --check` on the H1 working tree: PASS (no whitespace errors).
- No production or test file changed: `git status --short` shows only the four new artifacts, the new audit document, the doc-state updates, and the preserved user-owned paths.
- Focused existing Protocol/Port/architecture contract tests executed under isolation (F2-F6D + G contract suites) - see final report for exact command and result.
- Development database SHA-256/size/mtime verified before and after every write-capable run: unchanged.

## 12. Unresolved items

- Whether the ten API-owned Ports should be wired into production annotations (`deps.py` return types) or remain test-enforced documentation contracts: recorded as H2D option; not a blocker.
- Whether the local `ConfigurationRepository` plain class should become a `@runtime_checkable Protocol` during the H2B rename: recorded as an option; not required for correctness.
- Whether the `_AnalysisRunReader` pair should be canonicalized into one shared infra module or kept as two identical module-local readers: recorded as H2C candidate; low value, optional.
- No blocker condition from the H1 stop list was triggered.

## 13. Deliverables

- `docs/development/PROTOCOL_CONSOLIDATION_AUDIT_V0.9.5_H1.md` (this document)
- `verification/v0.9.5-h1/protocol_inventory.json` (55 contracts + implementations + excluded definitions)
- `verification/v0.9.5-h1/protocol_overlap_matrix.json` (29 method rows, 5 exact-duplicate groups, 3 name collisions)
- `verification/v0.9.5-h1/protocol_consumer_matrix.json` (55 contract -> consumer entries with roles and evidence)
- `verification/v0.9.5-h1/h2_candidate_plan.json` (5 ordered units + recommended first unit)

Commit: `docs(v0.9.5-h1): audit persistence protocols`

H2 implementation may begin only under separate owner authorization. This stage stops after the final report.
