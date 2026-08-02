# v0.9.5-F1 Service-Repository Dependency Audit

**Audit type:** Read-only architecture audit (Service Dependency Narrowing planning)
**Date:** 2026-08-02
**Repository:** `writing-feedback-mvp` (`A:\EAP Agent Project\writing-feedback-mvp`)
**Approved baseline:** `769e6d8` (v0.9.5-D verification), `773bd3d` (v0.9.5-E implementation), `7868b68` (v0.9.5-E verification, HEAD)
**Evidence:** Static source inspection, AST/text search, Git state, existing reports and inventories, Code Review Graph and GitNexus bounded queries. No runtime, no database access, no tests executed.
**Constraints honored:** No production code, test, configuration, database, migration, Protocol, factory, or existing documentation file was changed. The only artifact created is this report.

---

## 1. Executive conclusion

**Current coupling pattern.** `app.database.repository.Database` remains an explicit 86-method compatibility facade over nine aggregate SQLite repositories (`app/infrastructure/sqlite/repositories/*`). Every production Service receives the facade instance through constructor injection but is typed against Protocol-style structural contracts (central `app/repositories/protocols.py`, service-local re-declarations, or no annotation at all). No Service imports `app.database`; the architecture test `tests/test_architecture_v02.py:18-21` enforces that `app/services` never imports `app.database`, `sqlite3`, `streamlit`, or `fastapi`. Direct `Database` import is confined to the composition root, the legacy `FeedbackPipeline`, and operational scripts.

- Active persistence-consuming components: **13 production Service/component classes** (11 top-level services + embedded `ProgressService` and `LearnerHistoryService`) plus router-level facade consumers.
- Depending directly on `Database` (module import): **2 production modules** (`app/api/main.py`, `app/feedback/service.py`) plus **10 operational scripts**. All other consumers receive the facade instance via dependency injection.
- Already using narrow Protocol annotations: **7 of 11 top-level services** are annotated with Protocol-style contracts (`SubmissionService`, `RevisionService`, `ConfigurationService`, `DashboardService`, `ReanalysisService`, `LearnerProfileService`, `ProgressService`); the remaining 4 (`CalfService`, `AdminReanalysisService`, `ResearchDataService`, `JourneyService`) use untyped `repository` parameters, and `PracticeService` holds an unused `repository` attribute.
- Major transaction risks: no Service operation uses one shared transaction across aggregate repositories today. Every repository method owns its own single-connection implicit transaction; `Database.transaction()` is unused in production. The real risk is the opposite direction: preserving the current per-method commit behavior while changing which repository object owns each call, and not accidentally making practice attempt/evaluation or revision-group/essay writes atomic or independent in a different way.
- Recommended next stage: **v0.9.5-F2 - low-risk single-repository narrowing** for `ConfigurationService`, `DashboardService`, and `LearnerHistoryService`, keeping the facade for all cross-owner services (Section 12, Section 15).

## 2. Baseline and scope

| Item | Value | Source |
|---|---|---|
| HEAD | `7868b68317de42b25dfd0e2abd7159a6b967f846` | `git rev-parse HEAD` |
| Branch | `master` | `git branch --show-current` |
| v0.9.5-D verification | `769e6d8` (ancestor of HEAD - Confirmed) | `git merge-base --is-ancestor` |
| v0.9.5-E implementation | `773bd3d` (ancestor of HEAD - Confirmed) | `git merge-base --is-ancestor` |
| v0.9.5-E verification | `7868b68` (HEAD - Confirmed) | `git log -10 --oneline` |
| Migration | 12 | `RUN_VERIFICATION_V0.9.5_E.md` |
| Tables | 33 | `RUN_VERIFICATION_V0.9.5_E.md`; `V0.9.5_E_SPEC.md` Section 3 |
| Active configuration | `config-v0.9.0` | `RUN_VERIFICATION_V0.9.5_E.md` |
| API contract | 77 path+method pairs | `RUN_VERIFICATION_V0.9.5_E.md` |
| Frontend client contract | 52 public methods | `RUN_VERIFICATION_V0.9.5_E.md` |
| Core baseline | 469 passed, 8 skipped | `RUN_VERIFICATION_V0.9.5_E.md` |
| Locale parity | 520/520 | `RUN_VERIFICATION_V0.9.5_E.md` |
| Facade surface | 86 public methods (55 reads, 27 writes, 3 infrastructure write-capable, 1 pure) | `verification/v0.9.5-e/prechange_repository_inventory.json` |

**Repository state.** `git status --short` at audit start:

```text
 M AGENTS.md
 M RUN_VERIFICATION_V0.7.md
 M RUN_VERIFICATION_V0.8.2.md
?? .claude/
?? ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md
?? CLAUDE.md
?? data/demo_journey_manifest.json
```

`data/writing_feedback.db` and database backups are git-ignored and were not accessed. All listed paths are preserved user-owned changes and were not staged, edited, moved, or committed by this audit.

**No Service Dependency Narrowing work exists.** No commit or file references `v0.9.5-f1`/`SERVICE_REPOSITORY` before this report; `docs/development/` contains no F1 spec; no F1 production or test file has been changed (Confirmed via `git log --all --grep` and `git status`).

**Graph-index state (recorded at audit time; no refresh performed):**

| Index | Last index | HEAD match |
|---|---|---|
| GitNexus `EAP-Agent-Project` | 2026-08-02T04:59:03Z, lastCommit `7868b68` | Confirmed |
| Code Review Graph (`.code-review-graph`) | 2026-08-02T12:56:17Z, built_at_sha `7868b68`, head_matches_build true | Confirmed |

Both indexes are synchronized to `7868b68`; refresh was not required.

**Graph limitations (recorded):** GitNexus reports "FTS indexes missing - keyword search degraded", and its query results were not symbol-precise for this inventory (mostly registry/UI processes); Code Review Graph semantic search returned `search_mode: none` for the completeness query (no matching embeddings). Two bounded graph rounds were used (initial dependency query + final completeness check). **Source code at HEAD is authoritative for every conclusion in this report.**

**Evidence sources read:** `AGENTS.md`, `CLAUDE.md`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`, `RUN_VERIFICATION_V0.9.5_E.md`, `docs/development/V0.9.5_E_SPEC.md`, `docs/development/BLOCKER_REPORT_V0.9.5_E.md`, `app/database/repository.py`, `app/database/__init__.py`, `app/repositories/protocols.py`, `app/repositories/__init__.py`, `app/infrastructure/sqlite/connection.py`, all nine `app/infrastructure/sqlite/repositories/*.py` modules, all Service modules and constructors, `app/services/factory.py`, `app/api/main.py`, `app/api/deps.py`, all ten `app/api/routers/*.py` modules, `app/lifecycle.py`, `app/feedback/service.py`, `app/journey/service.py`, `app/practice/service.py`, `app/research/service.py`, `app/calibration/service.py`, `app/learner/history.py`, `app/configuration/registry.py`, `verification/v0.9.5-e/prechange_repository_inventory.json` and `postchange_repository_inventory.json`, and targeted symbol searches of tests/scripts.

## 3. Service and persistence-consumer inventory

Classification labels: **A** = active production consumer, **B** = test-only consumer, **C** = legacy but still reachable, **D** = apparently unused.

| Consumer | Source | Class. | Constructor dependency | Composition source | Read/write | Production callers |
|---|---|---|---|---|---|---|
| `SubmissionService` | `app/services/submission.py:39-50` | A | `repository: SubmissionRepository` (local union of 6 central Protocols, `submission.py:26-33`) | `build_submission_service` (`app/services/factory.py:60-75`); `FeedbackPipeline` (`app/feedback/service.py:36-38`) | Mixed | API `submissions.py` POST; `AdminReanalysisService.run` (via `regenerate_feedback`); `admin.py` mutates its internals |
| `LearnerProfileService` | `app/services/learner_profile.py:9-13` | A | `repository: LongitudinalRepository` (from `progress.py:23`) | `build_submission_service` (factory), `app/api/main.py:126,304` | Mixed (writes via `ProgressService` on persist) | `submissions` router (via `SubmissionService`), `students.py` profile/learner-model endpoints |
| `RevisionService` | `app/services/revision.py:15-19` | A | `repository: RevisionRepository` (central) | `app/api/main.py:131,308`; factory (inside `build_submission_service`); `AdminReanalysisService.__init__` (`admin_reanalysis.py:36`); `FeedbackPipeline` | Mixed | `revisions.py` router; `SubmissionService.submit`; `AdminReanalysisService.run` |
| `ConfigurationService` | `app/services/configuration.py:24-27` | A | `repository: ConfigurationRepository` (LOCAL 7-method re-declaration, `configuration.py:14-22`) | `app/api/main.py:128-129,306-307` | Mixed | `admin.py` router; `system.py` version endpoint; `AdminReanalysisService` |
| `DashboardService` | `app/services/dashboard.py:18-23` | A | `repository: DashboardRepository` (local 1-method, `dashboard.py:10-15`) | `app/api/main.py:130,308` | Read (snapshot computed with `persist=False`) | `students.py` dashboard endpoint |
| `ReanalysisService` | `app/services/reanalysis.py:16-19` | A | `repository: ReanalysisRepository` (local, `EssayRepository`+`MetricRepository`) | `app/api/main.py:130,307` | Mixed (Analysis write + Submission read) | `analysis.py` POST, `calf.py` reanalyze |
| `CalfService` | `app/services/calf.py:11-13` | A | `repository` (untyped) | `app/api/main.py:132,309` | Mixed | `calf.py` router (report, trajectories, import) |
| `AdminReanalysisService` | `app/services/admin_reanalysis.py:31-37` | A | `repository` (untyped) + `settings`, `configurations`, `submission_service` | `app/api/main.py:139-141` | Mixed | `admin.py` preview/run endpoints |
| `ResearchDataService` | `app/research/service.py:47-48` | A | `repository` (untyped) | `app/api/main.py:133,310` | Mixed | `research.py` router |
| `JourneyService` | `app/journey/service.py:104-106` | A | `repository: Any` | Constructed per-request in `app/api/routers/journey.py:10` | Read-only | `journey.py` GET endpoint |
| `PracticeService` | `app/practice/service.py:19-21` | A (no persistence calls) | `repository` (untyped; attribute never used) | Constructed per-request in `app/api/routers/practice.py:24,38,61` | None (pure domain; router persists) | `practice.py` router |
| `ProgressService` (embedded) | `app/services/progress.py:30-33` | A | `repository: LongitudinalRepository` | Constructed inside `LearnerProfileService` and `DashboardService` | Mixed | `LearnerProfileService.recalculate`; `DashboardService.build` |
| `LearnerHistoryService` (embedded) | `app/learner/history.py:25-26` | A | `database: LearnerHistoryRepository` | Constructed inside `SubmissionService.__init__` (`submission.py:52`) | Read-only | `SubmissionService.submit`/`regenerate_feedback` |
| `FeedbackPipeline` | `app/feedback/service.py:15-38` | C (legacy, reachable) | `database: Database \| None`; **defaults to `Database(settings.database_path)`**; calls `initialize()` and `record_versions()`; delegates to `SubmissionService`/`LearnerProfileService`/`RevisionService` | Not constructed by `app/api` or `app/services`; constructed by `scripts/seed_demo_data.py:19`, `scripts/verify_closed_loop.py:18`, `scripts/verify_live_deepseek.py:28`, and tests | Mixed | Scripts/tests only (`test_architecture_v02.py:43` asserts production UI never references it) |
| `LearnerModelEngine` | `app/services/learner_model.py:18-23` | B (pure; no persistence) | `configuration: ConfigurationPayload` | `ProgressService.create_snapshot` | None | - |
| `BaselineService`, `ComparabilityService`, `DiagnosticCalibrationService`, registries | `app/services/baseline.py`, `app/services/comparability.py`, `app/calibration/service.py`, `app/configuration/registry.py` | B (pure) | no repository dependency | - | None | - |

**Non-service production facade consumers** (full detail in Section 9): `app/api/main.py` composition root (`_run_startup` lines 96-154, `_build_full_app` lines 298-349); `app/api/deps.py:34-39` `require_student`; nine routers via `Depends(get_repository)`; `app/services/factory.py:61-67` (`get_active_configuration` guard); ten operational scripts.

**Note on `PracticeService`:** it is an active, router-reachable service, but it performs **no** persistence - every write in the practice flow is executed by the router directly against the facade. It is therefore not a persistence consumer; its `repository` parameter is a dormant dependency (Confirmed: `self.repo` is assigned at `practice.py:20` and never referenced again in the module).

## 4. Existing Protocol inventory

Repository-related Protocol/ABC/structural-contract definitions at HEAD (excluding analyzer Protocols and git-ignored `*-冲突-Rain_Win11.py` copies, which are covered as duplicates below). Classification: **A** reusable as-is, **B** reusable after relocation only, **C** too broad, **D** incomplete for current consumer, **E** duplicate/overlapping, **F** apparently unused.

### 4.1 Central `app/repositories/protocols.py`

| Protocol | Source | Methods | Consumers | Concrete impl. | Class. | Overlap/duplication notes |
|---|---|---|---|---|---|---|
| `StudentRepository` | `protocols.py:11-13` | `get_student` | none in production | `Database` structurally satisfies | F | Only in `SubmissionRepositories` union; `require_student`/`CalfService`/`JourneyService` call the method without this annotation |
| `EssayRepository` | `protocols.py:15-19` | `save_essay`, `get_submission_bundle`, `list_student_submissions` | `SubmissionService` (via `SubmissionRepository`), `ReanalysisService` (via `ReanalysisRepository`) | `Database`; `SQLiteSubmissionRepository` | C | `get_submission_bundle` duplicated in `RevisionRepository` (Section 4.4) |
| `MetricRepository` | `protocols.py:21-27` | `save_analysis`, `save_analysis_run`, `list_analysis_runs`, `get_latest_analysis_run`, **`list_analysis_units`** | `SubmissionService`, `ReanalysisService` | `Database`; `SQLiteAnalysisRepository` | C | `list_analysis_units` is CALF-owned (`SQLiteCalfRepository.list_analysis_units`, `calf.py:48-66`); `get_latest_analysis_run` duplicated in `RevisionRepository` |
| `ErrorAnnotationRepository` | `protocols.py:29-32` | `save_error_annotations`, `list_error_annotations` | none (CalfService is untyped) | `SQLiteCalfRepository` | F | No production consumer annotates with it |
| `DiagnosisRepository` | `protocols.py:34-36` | `save_diagnosis` | `SubmissionService` | `Database`; `SQLiteAnalysisRepository` | A | - |
| `FeedbackRepository` | `protocols.py:38-40` | `save_feedback` | `SubmissionService` | `Database`; `SQLiteSubmissionRepository` | A | - |
| `ExerciseRepository` | `protocols.py:42-44` | `get_exercises` | none | - | F | Method `get_exercises` has no production caller (Section 10) |
| `LearnerHistoryRepository` | `protocols.py:46-50` | `prior_records`, `save_history`, `list_student_history` | `LearnerHistoryService` (`prior_records` only), `SubmissionService` (`prior_records`, `save_history`) | `Database`; `SQLiteSubmissionRepository` | C | Spans Submission owner (`prior_records`, `save_history`) and Learner owner (`list_student_history`, `SQLiteLearnerRepository.list_student_history`) |
| `LearnerProfileRepository` | `protocols.py:52-59` | `get_latest_learner_profile`, `save_learner_profile_snapshot`, `list_learner_profile_snapshots`, `list_longitudinal_records`, `list_visualization_records`, `list_history_evidence` | `ProgressService`/`LearnerProfileService` (via `LongitudinalRepository`); `students.py` router calls `list_history_evidence`/`list_learner_profile_snapshots` directly | `Database`; `SQLiteLearnerRepository` | A | `list_visualization_records` also declared by local `DashboardRepository` (Section 4.2) |
| `RevisionRepository` | `protocols.py:61-72` | `get_submission_bundle`, `get_latest_analysis_run`, `create_revision_group`, `link_revision`, `get_revision_group`, `get_revision_group_for_submission`, `list_revision_candidates`, `save_revision_snapshot`, `list_revision_snapshots`, `get_latest_revision_snapshot` | `RevisionService` (matches its call set exactly) | `Database`; `SQLiteRevisionRepository` (+ injected `_SubmissionBundleReader`, `_AnalysisRunReader` at composition) | C | Spans Submission/Analysis owners; `get_submission_bundle` overlaps `EssayRepository`, `get_latest_analysis_run` overlaps `MetricRepository` |
| `ConfigurationRepository` | `protocols.py:74-77` | `ping`, `migration_version` | none | `Database` | F/E | **Name collision**: real `ConfigurationService` uses the local 7-method `ConfigurationRepository` (Section 4.2); this central definition has System-owned methods and no consumer |
| `SystemVersionRepository` | `protocols.py:79-81` | `record_versions`, `get_system_versions` | `SubmissionService` (`record_versions` only) | `Database`; `SQLiteSystemRepository` | C | `get_system_versions` has no production caller (Section 10) |
| `SubmissionRepositories` (union) | `protocols.py:84-88` | - | none (declared only) | - | F | Overlaps the local `SubmissionRepository` contract; no import found anywhere (`rg SubmissionRepositories` -> definition only) |

### 4.2 Service-local Protocol-like definitions

| Protocol | Source | Methods | Consumers | Class. | Notes |
|---|---|---|---|---|---|
| `SubmissionRepository` | `app/services/submission.py:26-33` | inherits `EssayRepository` + `MetricRepository` + `DiagnosisRepository` + `FeedbackRepository` + `LearnerHistoryRepository` + `SystemVersionRepository` | `SubmissionService`, `build_submission_service` (factory), `FeedbackPipeline` | A | Exact for `SubmissionService` except `MetricRepository.list_analysis_units` (never called) and `LearnerHistoryRepository.list_student_history` (never called); useful as a documented union but inherits overbreadth |
| `ReanalysisRepository` | `app/services/reanalysis.py:10` | `EssayRepository` + `MetricRepository` | `ReanalysisService` | C | Inherits unused `save_essay`, `list_analysis_units`; needs only `get_submission_bundle` + `save_analysis_run` |
| `LongitudinalRepository` | `app/services/progress.py:23-27` | subclass of `LearnerProfileRepository`; re-declares `list_longitudinal_records`, `save_learner_profile_snapshot`, `list_learner_profile_snapshots` | `ProgressService`, `LearnerProfileService` | A/B | Relocatable into the learner bounded context |
| `DashboardRepository` | `app/services/dashboard.py:10-15` | `list_visualization_records` | `DashboardService` | A/E | Duplicate declaration of `LearnerProfileRepository.list_visualization_records` |
| `ConfigurationRepository` (local) | `app/services/configuration.py:14-22` | 7 configuration methods | `ConfigurationService` | A | **Authoritative** for configuration narrowing; the central same-named Protocol is stale |

### 4.3 Infrastructure-internal reader Protocols

| Protocol | Source | Methods | Class. | Notes |
|---|---|---|---|---|
| `_SubmissionBundleReader` | `app/infrastructure/sqlite/repositories/revision.py:12-14` | `get_submission_bundle` | B | Satisfied by `SQLiteSubmissionRepository`; needed to compose `SQLiteRevisionRepository` |
| `_AnalysisRunReader` | `app/infrastructure/sqlite/repositories/learner.py:12-14` | `get_latest_analysis_run` | B | Satisfied by `SQLiteAnalysisRepository` |
| `_DiagnosticCalibrationReader` | `app/infrastructure/sqlite/repositories/learner.py:17-19` | `get_diagnostic_calibration` | B | Satisfied by `SQLiteCalfRepository` |

### 4.4 Duplicate/overlapping definitions (exact)

| Overlap group | Exact methods | Difference | Locations | Appears authoritative | Migration risk |
|---|---|---|---|---|---|
| `get_submission_bundle` | `get_submission_bundle(self, essay_id: int) -> dict[str, Any] \| None` | identical signature | `EssayRepository` (`protocols.py:16`), `RevisionRepository` (`protocols.py:62`), `_SubmissionBundleReader` (`revision.py:12`) | `EssayRepository` (Submission owner) | Low - one read, three declarations |
| `get_latest_analysis_run` | `get_latest_analysis_run(self, essay_id: int) -> dict[str, Any] \| None` | identical signature | `MetricRepository` (`protocols.py:24`), `RevisionRepository` (`protocols.py:63`), `_AnalysisRunReader` (`learner.py:12`) | `MetricRepository` (Analysis owner) | Low |
| `list_analysis_units` | in `MetricRepository` (`protocols.py:26`) | CALF-owned method in an Analysis contract | `protocols.py` only | `SQLiteCalfRepository.list_analysis_units` (`calf.py:48`) | Low - relocation only |
| `list_visualization_records` | in `LearnerProfileRepository` (`protocols.py:57`) and `DashboardRepository` (`dashboard.py:11`) | identical signature | central + dashboard.py | `LearnerProfileRepository` | Low |
| `ConfigurationRepository` name | central: `ping`, `migration_version`; local: 7 configuration methods | disjoint method sets | `protocols.py:74-77` vs `configuration.py:14-22` | local (matches `SQLiteConfigurationRepository`) | Medium - same name, wrong central set; consolidation must keep the 7-method contract |
| `SubmissionRepositories` union vs local `SubmissionRepository` | overlapping member Protocols | local is a class union; central is a typing union alias | `protocols.py:84-88` vs `submission.py:26-33` | local (used) | Low |
| Conflict-file copies | `app/repositories/protocols-冲突-Rain_Win11.py` (11 Protocols) and other `*-冲突-Rain_Win11.py` copies | git-ignored, unimported, pre-split versions | `app/repositories/` | canonical `protocols.py` | None (hygiene) |

No final replacement is chosen in this audit beyond recording that the local `ConfigurationRepository` (7 methods) and `DashboardRepository` are exact fits for their consumers, and the central `RevisionRepository` exactly matches `RevisionService`.

## 5. Service -> method -> repository map

Owner abbreviations: Sys=System, Sub=Submission, Ana=Analysis, Calf=CALF, Rev=Revision, Lea=Learner, Pra=Practice, Res=Research, Con=Configuration. R=read, W=write, I=infrastructure write-capable, P=pure. "Current Protocol" names the annotation the Service actually declares (central C / local L / none). Method lists are the exact static call sets at HEAD; type-declared-but-uncalled methods are excluded.

| Service | Called method (owner, R/W) | Current Protocol | Evidence |
|---|---|---|---|
| `SubmissionService` | `record_versions` (Sys, W); `save_essay` (Sub, W); `save_analysis_run` (Ana, W); `save_analysis` (Ana, W); `prior_records` (Sub, R, cross); `save_diagnosis` (Ana, W); `save_diagnostic_calibration` (Calf, W, hasattr-guarded); `get_submission_bundle` (Sub, R, cross); `get_diagnostic_calibration` (Calf, R, hasattr-guarded); `save_feedback` (Sub, W); `save_history` (Sub, W) | `SubmissionRepository` (L, union of C) | `submission.py:54` (record_versions), `:76` (save_essay), `:84-85` (save_analysis_run/save_analysis), `:88-96` (prior_records), `:102` (save_diagnosis), `:103-105` (save_diagnostic_calibration), `:185` (get_submission_bundle), `:201` (get_diagnostic_calibration), `:180` (save_feedback), `:181` (save_history); hasattr guards at `:103`,`:201` |
| `RevisionService` | `get_submission_bundle` (Sub, R, cross); `create_revision_group` (Rev, W, cross); `link_revision` (Rev, W, cross); `get_latest_analysis_run` (Ana, R); `save_revision_snapshot` (Rev, W); `get_revision_group` (Rev, R, cross); `get_latest_revision_snapshot` (Rev, R); `list_revision_snapshots` (Rev, R); `list_revision_candidates` (Rev, R, cross) | `RevisionRepository` (C) | `revision.py:24,30,46,48,64-65,137` (bundle), `:60` (create_revision_group), `:61` (link_revision), `:72,74` (get_latest_analysis_run), `:62` (save_revision_snapshot), `:92` (get_revision_group), `:97` (get_latest_revision_snapshot), `:101` (list_revision_snapshots), `:87` (list_revision_candidates) |
| `ConfigurationService` | `list_configurations` (Con, R); `get_configuration` (Con, R); `get_active_configuration` (Con, R); `create_configuration` (Con, W); `set_configuration_validation` (Con, W); `activate_configuration` (Con, W); `list_configuration_audit` (Con, R) | `ConfigurationRepository` (L) | `configuration.py:31,33,35,37,62,76,80,84,86` |
| `DashboardService` | `list_visualization_records` (Lea, R, cross); via `ProgressService.create_snapshot(persist=False)`: `get_active_configuration` (Con, R, hasattr) | `DashboardRepository` (L) | `dashboard.py:27` (records), `:135` (create_snapshot); `progress.py:42-48` (hasattr branch) |
| `ReanalysisService` | `get_submission_bundle` (Sub, R, cross); `save_analysis_run` (Ana, W) | `ReanalysisRepository` (L) | `reanalysis.py:22,30` |
| `CalfService` | `get_submission_bundle` (Sub, R, cross); `get_latest_analysis_run` (Ana, R); `list_error_annotations` (Calf, R); `list_analysis_units` (Calf, R, cross); `get_student` (Lea, R, cross); `list_student_submissions` (Sub, R); `save_error_annotations` (Calf, W, cross) | none | `calf.py:17,27,33,37,106,113,131,139` |
| `AdminReanalysisService` | `get_configuration` (Con, R); `get_submission_bundle` (Sub, R, cross); `save_analysis_run` (Ana, W); `list_student_submissions` (Sub, R); `get_revision_group` (Rev, R, cross); `get_analysis_run` (Ana, R); plus `configurations.active()` (ConService) and `submission_service.regenerate_feedback` | none | `admin_reanalysis.py:44,60-61,80,96,115,118-119,123,127` |
| `ResearchDataService` | `list_all_submissions` (Sub, R); `list_student_submissions` (Sub, R); `get_submission_bundle` (Sub, R, cross); `save_human_review` (Res, W, hasattr); `list_human_reviews` (Res, R, hasattr); `apply_pii_review` (Res, W, hasattr); `list_export_jobs` (Res, R, hasattr); `get_export_job` (Res, R, hasattr) | none | `research/service.py:71,73,81-83,172,195,200-211`; `run_export` never calls `save_export_job` (the router does) |
| `JourneyService` | `get_student` (Lea, R, cross); `list_essays_by_student` (Pra, R, cross); `list_analysis_runs_for_student` (Pra, R, cross); `list_feedback_records_for_student` (Pra, R, cross); `list_practice_targets` (Pra, R); `list_exercise_attempts_by_student` (Pra, R); `list_practice_evaluations_by_student` (Pra, R); `list_within_task_responses` (Pra, R); `list_transfer_evidence_candidates` (Pra, R) | `Any` | `journey/service.py:107-117` |
| `PracticeService` | none (pure domain) | none | `practice/service.py` - `self.repo` unused |
| `ProgressService` | `list_visualization_records` (Lea, R, cross, hasattr); `list_longitudinal_records` (Lea, R, cross, fallback branch); `get_active_configuration` (Con, R, hasattr); `save_learner_profile_snapshot` (Lea, W, persist) | `LongitudinalRepository` (L, subclass of C) | `progress.py:42-43,46-48,172` |
| `LearnerProfileService` | `get_latest_learner_profile` (Lea, R); `list_learner_profile_snapshots` (Lea, R) | `LongitudinalRepository` (L) | `learner_profile.py:18,25` |
| `LearnerHistoryService` | `prior_records` (Sub, R, cross) | `LearnerHistoryRepository` (C) | `learner/history.py:31` |
| `FeedbackPipeline` | `initialize` (Sys, I); `record_versions` (Sys, W); delegates to `SubmissionService`, `LearnerProfileService`, `RevisionService` | `Database` (direct) | `feedback/service.py:26,29,36-38` |

**Distinctions recorded:** All of the above are direct Service calls. Methods called by another Service that the first Service invokes (e.g., `SubmissionService` -> `RevisionService` -> facade; `SubmissionService` -> `LearnerProfileService` -> `ProgressService` -> facade) are listed on the inner Service's row. Methods only referenced in tests (e.g., `get_exercises`, `ping`, `transaction`) are excluded from Service rows. No dynamically resolved method names were found (all calls are literal attributes; the only dynamic patterns are `hasattr` guards, listed above).

## 6. Proposed Service Ports

Consumer-owned ports only; **none are created in this stage**. Method sets are exact current call sets from Section 5. "Implementation" is the current concrete owner; "Database satisfies structurally" is true for every row because the facade delegates to all owners.

| Service | Proposed Port | Exact methods | Implementation | Adapter required | Transaction notes |
|---|---|---|---|---|---|
| `ConfigurationService` | `ConfigurationPort` (= local `ConfigurationRepository`, 7 methods) | `list_configurations`, `get_configuration`, `get_active_configuration`, `create_configuration`, `set_configuration_validation`, `activate_configuration`, `list_configuration_audit` | `SQLiteConfigurationRepository` directly | No | Single-owner; activation/rollback remain one-connection methods |
| `DashboardService` | `DashboardReadPort` (= local `DashboardRepository`) | `list_visualization_records` | `SQLiteLearnerRepository` | No | Read-only |
| `LearnerHistoryService` | `PriorRecordsPort` | `prior_records` | `SQLiteSubmissionRepository` | No | Read-only; port is one method |
| `LearnerProfileService` / `ProgressService` | `LearnerPort` + narrow config read | `get_latest_learner_profile`, `list_learner_profile_snapshots`, `save_learner_profile_snapshot`, `list_longitudinal_records`, `list_visualization_records`, `list_history_evidence`; plus `get_active_configuration` (Configuration-owned) | `SQLiteLearnerRepository` + `SQLiteConfigurationRepository` (one read) | One small read port or one injected callable for `get_active_configuration` | Snapshot write is one connection (snapshot + evidence registry) |
| `ReanalysisService` | `AnalysisWritePort` + bundle read | `save_analysis_run` (Ana); `get_submission_bundle` (Sub, read) | `SQLiteAnalysisRepository` + `SQLiteSubmissionRepository` (read) | Yes - one read port for the bundle | Append-only; no cross-owner transaction |
| `CalfService` | `CalfPort` (use-case read+write) | `list_analysis_units`, `save_error_annotations`, `list_error_annotations` (Calf); `get_submission_bundle` (Sub, read); `get_latest_analysis_run` (Ana, read); `get_student`, `list_student_submissions` (Lea/Sub, reads) | `SQLiteCalfRepository` + injected readers | Yes - composition mirrors the facade's current wiring | `save_error_annotations` keeps its essay-existence guard and one-connection batch write |
| `ResearchDataService` | `ResearchPort` (use-case) | `save_human_review`, `list_human_reviews`, `apply_pii_review`, `save_export_job`, `list_export_jobs`, `get_export_job` (Res); `list_all_submissions`, `list_student_submissions`, `get_submission_bundle` (Sub, reads) | `SQLiteResearchRepository` + `SQLiteSubmissionRepository` (reads) | Yes - read port for submission lists | Export-job persistence is router-level and best-effort today |
| `JourneyService` | `JourneyReadPort` | `get_student` (Lea); `list_essays_by_student`, `list_analysis_runs_for_student`, `list_feedback_records_for_student`, `list_practice_targets`, `list_exercise_attempts_by_student`, `list_practice_evaluations_by_student`, `list_within_task_responses`, `list_transfer_evidence_candidates` (Pra-owned projections) | `SQLiteLearnerRepository` (1 method) + `SQLitePracticeRepository` (8 methods) | Yes - composition of two readers | Read-only; no transaction implications |
| `RevisionService` | `RevisionPort` (= central `RevisionRepository`) | 10 methods listed in Section 4.1 | `SQLiteRevisionRepository` composed with `_SubmissionBundleReader` + `_AnalysisRunReader` (already wired in the facade) | No adapter if composed like the facade; adapter only if the reader wiring is re-exposed | `create_revision_group`/`link_revision` each write revision rows AND `essays` in one connection; must not be split |
| `SubmissionService` | Defer (F4) - `SubmissionWorkflowPort` would need 10+ methods across Sys/Sub/Ana/Calf | see Section 5 row | multi-owner | Yes | **Transaction ownership must be decided first** (Section 8) |
| `AdminReanalysisService` | Defer (F4) - use-case port | `get_configuration`, `get_submission_bundle`, `save_analysis_run`, `list_student_submissions`, `get_revision_group`, `get_analysis_run` | multi-owner | Yes | Multi-write orchestration; per-method commits today |
| `PracticeService` | none (no persistence) | - | - | - | Router remains the persistence owner |
| `FeedbackPipeline` | Retain facade temporarily or remove | - | - | - | Legacy; removal is a deferred decision |

No broad interfaces (`ServiceRepository`, `ApplicationRepository`, `DatabasePort`, `GeneralRepository`) are proposed; no source evidence makes a broad dependency unavoidable.

## 7. Cross-aggregate reads

All 17 cross-aggregate facade methods (Confirmed against `verification/v0.9.5-e/prechange_repository_inventory.json` `cross_aggregate=true` and `V0.9.5_E_SPEC.md` Section 4).

| Method | Owner | Consuming Service/router | Tables/repositories involved | Ownership rationale | Narrowing recommendation |
|---|---|---|---|---|---|
| `counts` | System | scripts only (operational) | 16 tables across all aggregates | operational projection | Keep as System-owned facade/script method; no Service port needed |
| `prior_records` | Submission | `LearnerHistoryService`, `SubmissionService` | `essays`, `metrics`, `diagnoses` (Submission+Analysis read) | use-case-owned read for history/comparability | Keep as Submission-owned repository method; expose via `PriorRecordsPort` |
| `get_submission_bundle` | Submission | `SubmissionService`, `RevisionService`, `ReanalysisService`, `CalfService`, `AdminReanalysisService`, `ResearchDataService`, routers | `essays`, `metrics`, `diagnoses`, `feedback_records`, `learner_history` | use-case-owned composite read | Keep as Submission-owned method; expose read-only through narrow ports |
| `list_analysis_units` | CALF | `CalfService`, calf router | `analysis_units`, `analysis_runs` | use-case-owned read (CALF domain) | Keep as CALF-owned method |
| `save_error_annotations` | CALF | `CalfService` | `error_annotations` + essay-existence guard on `essays` | use-case-owned write with guard | Keep as CALF-owned method (guard stays inside the method) |
| `get_student` | Learner | `deps.require_student`, `CalfService`, `JourneyService` | `students`, `essays` (count) | use-case-owned lookup | Keep as Learner-owned method |
| `list_all_students` | Learner | none | `essays` | legacy projection | No production consumer; keep in Learner repo or retire |
| `list_longitudinal_records` | Learner | `ProgressService` (fallback branch) | `essays`, `metrics`, `diagnoses` | reusable aggregate query (legacy path) | Keep as Learner-owned method |
| `list_visualization_records` | Learner | `DashboardService`, `ProgressService` | `essays`, `metrics`, `diagnoses`, `analysis_runs` (via readers), `diagnostic_calibrations` | reusable read-model query | Keep as Learner-owned method; `DashboardReadPort` consumes it |
| `create_revision_group` | Revision | `RevisionService` | `revision_groups`, `essays` | use-case-owned write (revision semantics) | Keep as Revision-owned method with essay update inside one connection |
| `link_revision` | Revision | `RevisionService` | `essays`, `revision_groups` | use-case-owned write | Same as above |
| `get_revision_group` | Revision | `RevisionService`, `AdminReanalysisService` | `revision_groups`, `essays` (members) | aggregate read | Keep as Revision-owned method |
| `get_revision_group_for_submission` | Revision | revisions router | `essays`, `revision_groups` | use-case lookup | Keep as Revision-owned method |
| `list_revision_candidates` | Revision | `RevisionService` | `essays` | use-case read | Keep as Revision-owned method |
| `list_essays_by_student` | Practice | `JourneyService` | `essays` | Journey projection (owned by Practice per v0.9.5-E) | Keep as Practice-owned projection; Journey read port consumes it |
| `list_analysis_runs_for_student` | Practice | `JourneyService` | `analysis_runs`, `essays` | Journey projection | Same as above |
| `list_feedback_records_for_student` | Practice | `JourneyService` | `feedback_records`, `essays` | Journey projection | Same as above |

**Conclusion:** Every cross-aggregate read is a use-case-owned or reusable aggregate query; none is a generic reporting query that belongs to a new shared read-model layer. During narrowing they should remain single repository methods and be consumed through consumer-owned read ports; none should be split into per-table queries.

## 8. Transaction-boundary matrix

`SQLiteConnectionManager` (`app/infrastructure/sqlite/connection.py:26-40`) is the only transaction owner: `transaction()` opens one connection, `BEGIN` -> yield -> commit / rollback-and-reraise -> close. Every repository method instead opens its own connection via `with self._connection_manager.connect() as connection:` (sqlite3 context manager auto-commits on clean exit). **No Service uses `Database.transaction()`; the facade `transaction()` has no production caller (test-only, `tests/test_repository_v02.py:32`).**

| Operation | Service | Repositories/owners involved | Current transaction owner | Commit/rollback location | Narrowing risk | Required safeguard |
|---|---|---|---|---|---|---|
| Submission creation + analysis + diagnosis + calibration + feedback + history (`submit`) | `SubmissionService` | Sub, Ana, Calf, Sys, (Lea, Rev via embedded services) | each repository method (single connection) | implicit commit at each `with connect()` exit; rollback on exception per method | **High** - 11+ independent commits; a future Unit-of-Work could change failure semantics | Preserve per-method commits during narrowing; defer any single-transaction redesign to a dedicated stage; pin behavior with the existing submission integration tests |
| Feedback persistence (`save_feedback`) | `SubmissionService` | Sub only (feedback_records + exercises + llm_call_records) | `SQLiteSubmissionRepository.save_feedback` (one connection) | method-level commit | Low | Keep the three-table write inside one repository method |
| Reanalysis (`run`) | `ReanalysisService` | Ana (write), Sub (read) | `save_analysis_run` (one connection) | method-level commit | Low | Append-only; no cross-owner write |
| Revision relationship creation (`create_relationship`) | `RevisionService` | Rev (group/link/snapshot), Sub (essays updated inside Revision methods), Ana (read) | each Revision repository method (one connection each) | 3 sequential commits (group, link, snapshot) | **High** - if the essay UPDATE in `create_revision_group`/`link_revision` is moved out of the Revision method, the update would commit separately | Keep essay UPDATEs inside `SQLiteRevisionRepository` methods; do not split |
| Practice attempt + evaluation (router `submit_exercise_attempt`) | practice router (+ `PracticeService`) | Pra (attempt, evaluation), Sub (bundle read) | each repository method (one connection each) | attempt commits, then evaluation commits (best-effort `try/except` at `practice.py:66-76`) | Medium - currently non-atomic; narrowing must not make it atomic without approval | Preserve best-effort evaluation semantics; add a focused test on attempt-then-evaluation ordering |
| Learner-model rebuild (`recalculate(persist=True)`) | `ProgressService` | Lea (read+write), Con (read) | `save_learner_profile_snapshot` (one connection: snapshot + evidence registry) | method-level commit | Low-Medium | Keep snapshot+evidence write inside `SQLiteLearnerRepository.save_learner_profile_snapshot` |
| Research review/export persistence | `ResearchDataService` + research router | Res (write), Sub (read) | each method (one connection); `save_export_job` is router-level best-effort | method-level commit; export row failure is swallowed (`research.py:48-58`) | Medium - export itself already succeeded before row insert | Keep best-effort persistence; document the gap |
| Configuration activation / rollback | `ConfigurationService` | Con only | `activate_configuration` (one connection: two UPDATEs + audit INSERT) | method-level commit | Low | Keep multi-statement activation inside one method |
| `Database.transaction()` | - | - | `SystemRepository.transaction` | unused in production | n/a | Not part of narrowing; leave untouched |

**Direct answer:** no Service operation currently depends on one shared transaction across multiple aggregate repositories. The "shared transaction" risk is prospective: any future narrowing that introduces a Unit of Work, or any split of a single repository method's multi-statement writes, would change failure semantics. The current contract is per-method single-connection transactions.

## 9. Direct Database consumers

Every production import, construction, or type dependency on `Database` / `SQLiteRepository` / `app.database.repository.Database` (Confirmed by full-text scan of `app/` and `scripts/`):

**A. Composition root**
- `app/api/main.py:36,115` (`_run_startup`): constructs `Database(settings.database_path)`, `initialize()` (116), `migration_version()` (117), `get_active_configuration()` (163).
- `app/api/main.py:310-311,327` (`_build_full_app`): same construction + `initialize()` + `migration_version()`.
- `app/api/deps.py:67` `require_student`: `repository.get_student()` - facade consumed through DI.
- `app/services/factory.py:61-67` `build_submission_service`: `repository.get_active_configuration()` (hasattr guard).

**B. Service dependency**
- All 13 service classes receive the facade instance but import no `app.database` symbol (type-checked only). `FeedbackPipeline` (`app/feedback/service.py:5,20`) is the single Service-layer module that imports `Database` and constructs it - **legacy** (C).

**C. Infrastructure/lifecycle dependency**
- `app/database/repository.py:449` (`SQLiteRepository = Database` alias, definition); `app/database/__init__.py:2-4` (exports); `app/database/migrations.py:21` (imports `SCHEMA`).

**D. API/router dependency (facade consumed through DI)**
- Routers with `Depends(get_repository)`: `system.py:85` (`migration_version`), `submissions.py:43,45,53`, `analysis.py:15,17`, `calf.py:60,63,68,70,80,82`, `revisions.py:27,80` (+ `require_student`), `students.py:44,45,155,161,171` (+ `require_student`), `practice.py:16,31,37,43,49,51,56,59,64,68,71,74,82,84,90,96`, `journey.py:10` (constructs `JourneyService(repository)`), `research.py:49` (`save_export_job`).

**E. Legacy production dependency (operational scripts - reachable, not part of the running app)**
- `scripts/audit_live_verification.py:6,16`; `scripts/demo_journey.py:34,73` (+ `save_within_task_response_candidate` at 205); `scripts/initialize_project.py:7,28`; `scripts/migrate_database.py:6,11`; `scripts/seed_demo_data.py:9` (via `FeedbackPipeline`); `scripts/seed_longitudinal_data.py:9,40`; `scripts/verify_closed_loop.py:8` (via `FeedbackPipeline`); `scripts/verify_live_deepseek.py:10`, `scripts/verify_live_deepseek_v061.py:10,27`, `scripts/verify_live_deepseek_v071.py:11,60,72,95`, `scripts/verify_live_deepseek_v08.py:11,78,108`.

**F. Test-only dependency**
- 20+ test files import `from app.database import Database` directly (e.g., `test_database.py:1`, `test_calf_v08.py:20`, `test_journey_v093c.py:22,35`, `test_practice_v09.py:236-237,252-253`, `test_research_v082.py:11,36,260,270`, `test_revision_v05.py:11,32`, `test_v06_configuration_dashboard.py:15,34`, `test_v095e_repository_modularization.py:9-13`). These tests construct the facade against `tmp_path` databases and are the main obstruction to facade contraction.

**G. Apparently unused**
- No import of `Database` was found with no use; all imports are exercised in one of the categories above.

**Guidance:** composition root and `FeedbackPipeline` should remain facade users until contraction (G). Services can move to narrow ports in F2-F4. No production module should ever instantiate the aggregate repositories directly (facade and tests currently are the only construction sites). Test helpers that may obstruct contraction: every test constructing `Database` directly (list above) - future stages must introduce per-repository construction in tests or keep them on the facade until G.

## 10. Facade-method usage classification

Classification is **informational only**; no method is deleted, deprecated, or renamed. "No caller found" (E) is a static result, not a proof of dead code.

**Totals (86 public methods):**

| Class | Count |
|---|---|
| A - used by active production code | **67** |
| B - used only through another facade method (internal delegation) | **4** |
| C - used only by tests or verification | **1** |
| D - legacy but still reachable (operational scripts) | **5** |
| E - no caller found (static) | **9** |

**Category B (4):** `connect`, `normalize_revision_stage`, `get_metric_results` (internal to `get_latest_analysis_run`, `analysis.py:118`), `get_analysis_artifact` (internal to `get_latest_analysis_run`, `analysis.py:117`; also directly exercised by `test_analysis_runs_v04.py:43`).

**Category C (1):** `transaction` (only `tests/test_repository_v02.py:32`).

**Category D (5, with evidence):**
- `counts` - `scripts/seed_demo_data.py:29`, `scripts/verify_closed_loop.py:52` (also tests).
- `get_feedback_record` - `scripts/audit_live_verification.py:20-21`, `scripts/verify_live_deepseek.py:77`.
- `get_llm_calls` - `scripts/audit_live_verification.py:26`.
- `get_history_record` - `scripts/audit_live_verification.py:24`.
- `save_within_task_response_candidate` - `scripts/demo_journey.py:205` (no router/Service caller; creation endpoints for within-task responses do not exist in the API).

**Category E (9, listed explicitly):** `ping`, `get_system_versions`, `get_exercises`, `list_all_students`, `list_practice_evaluations` (attempt/target variant; `_by_student` variant is active via JourneyService), `save_feedback_engagement_trace`, `save_transfer_evidence_candidate`, `save_practice_state_snapshot`, `list_practice_state_snapshots`. Verified: no caller in `app/` or `scripts/`, and no direct caller in `tests/` for these names.

**Reading of the table:** "no caller found" (E) is supported by static search only; "proven unused" is not claimed. Methods in E that are write-capable practice writers (`save_feedback_engagement_trace`, `save_transfer_evidence_candidate`, `save_practice_state_snapshot`, `list_practice_state_snapshots`) have matching read endpoints in the API but no creation endpoint, so their production callers would only appear if the API grows writers.

## 11. Risk classification

**Category 1 - single-repository, low risk**

| Service | Risk | Reason | Future stage |
|---|---|---|---|
| `ConfigurationService` | Low | Methods all belong to Configuration owner; local 7-method Protocol is exact; `SQLiteConfigurationRepository` satisfies it directly | F2 |
| `DashboardService` | Low | Single read (`list_visualization_records`); local `DashboardRepository` is exact | F2 |
| `LearnerHistoryService` (embedded) | Low | Single read (`prior_records`); one-method port | F2 |
| `ReanalysisService` | Low | One owner write (Analysis) + one cross read (`get_submission_bundle`); no transaction | F2/F3 |

**Category 2 - multi-repository, read-only (or single-owner write + multi-owner reads)**

| Service | Risk | Reason | Future stage |
|---|---|---|---|
| `LearnerProfileService`/`ProgressService` | Low-Medium | Learner reads + one Configuration read; snapshot write is single-owner | F3 |
| `JourneyService` | Low-Medium | Wide read surface across Learner + Practice projections; read-only | F3 |
| `CalfService` | Medium | Reads across Sub/Ana/Lea + CALF write with essay guard | F3 |
| `ResearchDataService` | Medium | Reads Submission tables + Research writes; export flow best-effort | F3 |

**Category 3 - multi-repository write orchestration**

| Service | Risk | Reason | Future stage |
|---|---|---|---|
| `SubmissionService` | High | Writes across Sys/Sub/Ana/Calf + embedded Lea/Rev writes; 11+ independent commits; hasattr-guarded optional methods | F4 |
| `RevisionService` | High | Revision writes update `essays` inside two repository methods; 3 sequential commits per relationship | F4 |
| `AdminReanalysisService` | High | Orchestrates Configuration read + Analysis append + Revision recalculation + optional feedback regeneration | F4 |
| Practice router attempt flow | Medium-High | attempt + best-effort evaluation persistence across connections; bundle read | F4 (router-level) |

**Category 4 - infrastructure or legacy coupling**

| Component | Risk | Reason |
|---|---|---|
| `FeedbackPipeline` | Medium | Direct `Database` construction; legacy parallel submission path; scripts/tests only |
| `app/api/main.py` composition root | Low | Correct home for facade construction today |
| API routers via `Depends(get_repository)` | Medium | 9 routers call the facade directly; should route through services or narrow ports in F3 |
| `deps.require_student` | Low | Single `get_student` read; natural narrow read port |
| Operational scripts | Low | 10 scripts construct `Database`; unaffected by Service narrowing |

**Service risk counts (11 top-level services):** low = 3 (`ConfigurationService`, `DashboardService`, `ReanalysisService`); medium = 4 (`LearnerProfileService`, `JourneyService`, `CalfService`, `ResearchDataService`); high = 3 (`SubmissionService`, `RevisionService`, `AdminReanalysisService`); special = 1 (`PracticeService`, not a persistence consumer).

## 12. Recommended implementation sequence

Each stage is independently executable; each stops before the next begins. Approximate blast radius is in touched constructor/factory/wiring files.

### v0.9.5-F2 - Low-risk single-repository Service narrowing

- **Included Services:** `ConfigurationService`, `DashboardService`, `LearnerHistoryService`.
- **Excluded:** everything else; the facade remains the supplied instance for all other services.
- **Exact dependency changes:**
  - `ConfigurationService`: constructor switches from the facade to `SQLiteConfigurationRepository` (or a consumer-owned `ConfigurationPort`); keep the local 7-method contract. Update `app/api/main.py` composition (both startup paths) and `app/services/factory.py` only if it composes ConfigurationService (it does not today).
  - `DashboardService`: constructor receives `SQLiteLearnerRepository` (satisfies `DashboardRepository.list_visualization_records`); update main composition.
  - `LearnerHistoryService`: constructor receives a `prior_records`-capable reader (Submission repository slice); update `SubmissionService` composition only if the writer is constructed by the service.
- **Transaction risks:** none - single-owner reads/writes; per-method connections unchanged.
- **Blast radius:** 3 service constructors + 2 composition sites (`app/api/main.py:128-130,306-308`); no API/UI/domain change.
- **Focused tests:** for each narrowed service, a constructor test with a stub port asserting the exact called-method set; keep all existing facade-parity tests unchanged.
- **Stop condition:** F2 core suite green (469 baseline + new focused tests), `test_v095e_repository_modularization.py` unchanged and passing, no other Service constructor touched.

### v0.9.5-F3 - Read-only and domain Service narrowing

- **Included Services:** `JourneyService` (read port over Learner + Practice projections), `LearnerProfileService`/`ProgressService` (Learner port + narrow config read), `CalfService` (CALF port + readers), `ResearchDataService` (Research port + submission list read), `ReanalysisService` (Analysis write port + bundle read), and router-level read consumers (`students.py`, `calf.py`, `analysis.py`, `submissions.py`, `revisions.py` reads) moved onto services or narrow read ports.
- **Excluded:** `SubmissionService`, `RevisionService`, `AdminReanalysisService`, practice write flows.
- **Exact dependency changes:** construct each included service with its proposed port composition (Section 6); remove `Depends(get_repository)` from read-only endpoints where a narrow port is available; `deps.require_student` moves to a `StudentLookupPort`.
- **Transaction risks:** none for reads; `save_error_annotations` and `save_learner_profile_snapshot` keep their single-connection guards/writes.
- **Blast radius:** 5 service constructors, ~8 router dependencies, `deps.py`.
- **Focused tests:** per-service port-contract tests asserting exact methods; journey projection parity test; calf annotation guard test.
- **Stop condition:** all F2 + F3 focused tests green; no facade method removed; routers with write flows still receive the facade.

### v0.9.5-F4 - Cross-aggregate write-orchestration narrowing

- **Included Services:** `SubmissionService`, `RevisionService`, `AdminReanalysisService`, practice write flows.
- **Excluded:** facade contraction; transaction redesign; Protocol consolidation (unless evidence-driven).
- **Exact dependency changes:** each service receives a consumer-owned port composed of the repository slices it needs (Section 6), preserving the current wiring pattern where Revision/Learner repositories already receive reader collaborators.
- **Transaction risks:** **highest of the sequence.** `SubmissionService.submit` must keep its per-method commit sequence unless a dedicated transaction-ownership stage is separately approved; `create_revision_group`/`link_revision` must keep the `essays` UPDATE inside the same method; practice attempt/evaluation must stay non-atomic (best-effort).
- **Blast radius:** 3 service constructors + factory + main composition + practice router.
- **Focused tests:** idempotency/ordering tests for submission failure injection, revision-group essay linkage, practice attempt-without-evaluation; assert commit counts unchanged (existing integration tests already pin much of this).
- **Stop condition:** full regression green with facade still 86 methods; no behavior change to failure semantics; transaction boundaries explicitly documented per operation.

### v0.9.5-G - Database facade contraction

- **Included:** facade method removal/contraction after F2-F4; `SQLiteRepository` alias resolution; script/test migration.
- **Excluded (until separately approved):** anything not listed here.
- **Exact dependency changes:** remove facade methods only when no production consumer remains (Section 10 totals inform the backlog); migrate tests off `Database(...)` construction; decide `ping`/`transaction`/`counts` fate.
- **Transaction risks:** none new - all boundaries already moved into repository methods.
- **Blast radius:** entire test suite (20+ files) + scripts.
- **Stop condition:** zero production imports of `app.database.repository.Database` outside `app/database/` itself.

## 13. Deferred decisions

- **Protocol consolidation:** central vs local `ConfigurationRepository` (7-method local is authoritative); `RevisionRepository`/`EssayRepository`/`MetricRepository` overlaps (`get_submission_bundle`, `get_latest_analysis_run`); `MetricRepository.list_analysis_units` relocation; `LearnerHistoryRepository` owner span; unused `StudentRepository`/`ExerciseRepository`/`ErrorAnnotationRepository`/`SubmissionRepositories`; `DashboardRepository` duplicate; git-ignored `*-冲突-Rain_Win11.py` copies.
- **Facade method removal:** the 9 Category E and 5 Category D methods; removal must wait for G and explicit approval.
- **Transaction redesign:** no Unit of Work or shared-transaction introduction without a separate approved stage.
- **Schema cleanup:** DDL split between `repository.SCHEMA` and `migrations.py` (deferred since v0.9.5-E; `V0.9.5_E_SPEC.md` Section 11).
- **WTR collision:** within-task-response candidate ID allocation collision remains a deferred finding (`V0.9.5_E_SPEC.md` Section 11); this audit neither re-confirmed nor resolved it.
- **`export_jobs` writer:** `run_export` still does not insert a row; the router persists best-effort post-export (`research.py:48-58`); implementing/removing the writer is deferred.
- **Legacy pipeline removal:** `FeedbackPipeline` removal (blocked by `scripts/` and tests that use it).
- **Practice writer endpoints:** no production creator exists for engagement traces, within-task responses, transfer evidence, or practice-state snapshots; whether to expose writers is a product decision.

## 14. Audit limitations

- **Static-only evidence:** no application runtime, no database opened, no pytest executed (per task constraints). "No caller found" (Category E) is a static-search result, not proof of dead code.
- **Dynamic dispatch:** `hasattr`-guarded calls (`submission.py:103,201`; `progress.py:42,46`; `research/service.py` hasattr calls) are recorded as conditional; behavior under alternative repository objects is Unresolved.
- **Graph degradation:** GitNexus FTS indexes missing (keyword search degraded) and Code Review Graph semantic search returned no embeddings for the completeness query; both indexes matched HEAD at `7868b68` but were used only for bounded confirmation. Source at HEAD is authoritative.
- **Script reachability:** scripts were classified by import inspection; they were not executed, so reachability is Inferred, not Confirmed.
- **Conflict-file copies** (`*-冲突-Rain_Win11.py`) were excluded from production analysis; they are git-ignored and unimported (Confirmed by import scan).
- **Type annotations are not proof of calls:** every called method was verified by static call-site search; Protocol declarations alone were never treated as usage.
- **`list_longitudinal_records` classification:** referenced by an active production branch (`progress.py:43`) that is inert when the facade provides `list_visualization_records`; its runtime usage under the facade is Unresolved.
- **Test usage is not production usage:** test-only callers (e.g., `transaction`) do not qualify a method as production-active.

## 15. Decision

**v0.9.5-F2 may begin**, with the exact approved scope:

1. Narrow exactly three Services to single-repository dependencies: `ConfigurationService` -> `ConfigurationPort` (7 methods, satisfied directly by `SQLiteConfigurationRepository`); `DashboardService` -> `DashboardReadPort` (`list_visualization_records`, satisfied by `SQLiteLearnerRepository`); `LearnerHistoryService` -> `PriorRecordsPort` (`prior_records`, satisfied by the Submission repository slice).
2. Update only the affected constructors and the composition sites in `app/api/main.py` (both startup paths) that construct those three services; no other Service, router, factory signature, Protocol definition, repository implementation, or facade method changes.
3. Preserve per-method transaction behavior; do not introduce or remove any transaction.
4. Do not consolidate Protocols, do not remove facade methods, do not touch `FeedbackPipeline`, scripts, tests, migrations, schema, or the database.
5. Add focused constructor/port tests for the three narrowed services; the full core suite (469 passed, 8 skipped baseline) and the unchanged `test_v095e_repository_modularization.py` parity contract must pass.
6. Stop before F3 or any cross-owner narrowing.

F3, F4, and G are planned but **not authorized** by this audit. No Service Dependency Narrowing has begun; no code, test, configuration, runtime, or database was changed.
