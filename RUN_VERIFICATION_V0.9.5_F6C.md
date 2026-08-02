# v0.9.5-F6C Verification - SubmissionService Persistence Dependency Narrowing

**Date:** 2026-08-02
**Status:** PASS
**Baseline commit:** `3f1a923` (v0.9.5-F6B verification); F2-F6B commits are
ancestors
**Implementation commit:** `refactor(v0.9.5-f6c): narrow submission service dependencies`
**Verification commit:** `test(v0.9.5-f6c): verify submission service contracts`
**Specification:** `docs/development/V0.9.5_F6C_SPEC.md`
**Authorization:** Owner-authorized F6C stage (pasted instruction file).

## Scope (SubmissionService persistence dependency narrowing only)

Removed the broad, inherited `SubmissionRepository` dependency from the active
`SubmissionService` constructor and runtime state and replaced it with four
owner-aligned, consumer-owned structural Ports (`SubmissionSystemPort`,
`SubmissionDataPort`, `SubmissionAnalysisPort`, `SubmissionCalibrationPort`).
Both CALF persistence `hasattr` capability guards were removed. Every
analyzer, configuration, learner-history, learner-profile, Revision,
feedback, baseline, comparability, and calibration collaborator boundary, all
read/write order, independent commits, and failure-after-partial-success
behavior are preserved. No Repository implementation, SQL statement,
transaction boundary, API contract, schema, prompt, provider, domain rule, UI
behavior, or persistence result changed.

## Source-reconciled direct persistence method set (HEAD `3f1a923`)

Eleven direct methods through a SubmissionService persistence field:

```text
record_versions                (constructor-time, one call per construction)
save_essay
save_analysis_run
save_analysis
prior_records                  (direct in the calibrator branch; also backs
                                LearnerHistoryService through the same port)
save_diagnosis
save_diagnostic_calibration    (hasattr guard removed)
save_feedback
save_history
get_submission_bundle
get_diagnostic_calibration     (hasattr guard removed)
```

No fifth Repository owner exists (AST proof: exactly these eleven via the four
port fields). `prior_records` remains a direct call in the `if self.calibrator:`
branch and is therefore in `SubmissionDataPort`.

## Four new consumer-owned Ports

Defined in `app/services/submission.py` (`typing.Protocol` +
`@runtime_checkable`), signatures copied from current HEAD source:

```text
SubmissionSystemPort      -> record_versions(versions: dict[str, str]) -> None
SubmissionDataPort        -> save_essay(submission, *, synthetic=False) -> int
                             prior_records(submission) -> list[dict[str, Any]]
                             get_submission_bundle(essay_id) -> dict[str, Any] | None
                             save_feedback(essay_id, result, analysis_version) -> None
                             save_history(student_id, essay_id, history) -> None
SubmissionAnalysisPort    -> save_analysis_run(essay_id, analysis) -> AnalysisResult
                             save_analysis(essay_id, analysis) -> None
                             save_diagnosis(essay_id, diagnosis) -> None
SubmissionCalibrationPort -> save_diagnostic_calibration(essay_id, calibration)
                             -> DiagnosticCalibrationResult
                             get_diagnostic_calibration(essay_id)
                             -> DiagnosticCalibrationResult | None
```

Concrete satisfiers: `SQLiteSystemRepository`, `SQLiteSubmissionRepository`,
`SQLiteAnalysisRepository`, `SQLiteCalfRepository`. Exact signature parity
verified by inspect; no cross-port method; no broad Protocol inheritance; no
`Database` or concrete SQLite import in the Service module.

## Constructor before and after

Before: `(repository: SubmissionRepository, analyzer, diagnoser, router,
learner_profile_service=None, revision_service=None, calibrator=None,
calf_configuration=None)`.

After: `(system_repository: SubmissionSystemPort, submission_repository:
SubmissionDataPort, analysis_repository: SubmissionAnalysisPort,
calibration_repository: SubmissionCalibrationPort, analyzer, diagnoser,
router, learner_profile_service=None, revision_service=None, calibrator=None,
calf_configuration=None)`.

No broad `repository` parameter or `self.repository`/`self.repo` field
remains; no fallback, `hasattr`, dynamic discovery, concrete implementation
check, `Database` import, or SQLite import exists. `self.history =
LearnerHistoryService(submission_repository)` (satisfies the F2
`PriorRecordsPort`).

## Legacy SubmissionRepository and capability-guard decisions

- The legacy local inherited `SubmissionRepository` declaration remains in
  `app/services/submission.py` as Protocol-consolidation debt; it is no
  longer the active constructor type, no longer a field type, and no longer
  required by `build_submission_service` (factory signature has no
  `repository` parameter) or any active caller.
- Both CALF `hasattr` guards were removed after every active path was
  confirmed able to supply the facade-owned `SQLiteCalfRepository`:
  `submit` calls `calibration_repository.save_diagnostic_calibration` when
  `calibration is not None`; `regenerate_feedback` calls
  `calibration_repository.get_diagnostic_calibration` unconditionally. The
  branch conditions deciding whether calibration runs are unchanged.

## Constructor side effect

`record_versions` remains inside `SubmissionService.__init__` (one call per
construction, same arguments, same timing, same independent repository
commit); failure propagates from the constructor. Proved by minimal-stub and
failure tests, factory construction, both application paths, and
FeedbackPipeline construction.

## Submit call order (recorder-proven)

Initial submission (factory service with calibrator, learner, Revision):

```text
save_essay -> save_analysis_run -> save_analysis -> prior_records (calibrator)
-> save_diagnosis -> save_diagnostic_calibration -> prior_records (history)
-> recalculate (learner) -> generate (router) -> save_feedback -> save_history
```

Write counts: essays 1, analysis_runs 1, diagnoses 1,
diagnostic_calibrations 1, feedback_records 1, learner_history 1. Revised
submission adds `validate_relationship -> create_relationship` (which
internally re-validates) `-> group_summary -> trajectory`; the three
independent Revision commits are preserved (revision_groups 1,
revision_snapshots 1). FeedbackPipeline (no calibrator) performs a single
`prior_records` call and zero calibration writes, proving the calibration
branch condition is preserved.

## Regenerate-feedback call order (recorder-proven)

```text
get_submission_bundle -> latest_or_recalculate (learner)
-> get_diagnostic_calibration -> generate (router) -> save_feedback
```

Missing submission raises `LookupError` before any call; missing stored
diagnosis raises `ValueError`; public signature unchanged; F6B Admin
regeneration tests pass unchanged.

## Failure and partial-commit results

Failure injected at each active direct write boundary
(`save_essay`, `save_analysis_run`, `save_analysis`, `save_diagnosis`,
`save_diagnostic_calibration`, `save_feedback`, `save_history`) proves: the
recorder stops exactly at the failing boundary (no later call begins), the
exception propagates unchanged, and the committed rows are exactly the
earlier successful writes (e.g. `save_analysis_run` failure leaves essays 1 /
runs 0; `save_diagnosis` failure leaves runs committed but no diagnosis;
`save_feedback` failure leaves diagnosis and calibration committed but no
feedback/history; `save_history` failure leaves feedback committed but no
learner history). `save_essay` failure commits nothing. Regenerate-feedback
`save_feedback` failure preserves the existing committed feedback row. No
compensation, retry, or shared transaction exists; `record_versions`
constructor failure propagates.

## Verification layers

### Layer 1 - Static

- `py_compile` of all changed/new modules: PASS.
- Imports of all four Ports, `SubmissionService`, `build_submission_service`,
  both application paths, and `FeedbackPipeline`: PASS (no circular imports);
  constructor and factory signatures confirmed by probe.
- Task-scoped `git diff --check`: PASS (user-owned `AGENTS.md` excluded).
  UTF-8/replacement scan: 0 defects in all changed files.

### Layer 2 - Dependency contracts

- Exact four Port method sets and source-signature parity: PASS (inspect).
- No broad active `SubmissionRepository` dependency (constructor AST, factory
  signature); no `Database`/SQLite import; no persistence `hasattr`; no
  fallback; no unrelated Service constructor changed; no Repository
  implementation, SQL, or migration file changed (git path diff empty).

### Layer 3 - Runtime identity

Both application paths, the factory, and FeedbackPipeline prove:

```text
system_repository        is repository._system_repository
submission_repository    is repository._submission_repository
analysis_repository      is repository._analysis_repository
calibration_repository   is repository._calf_repository
history.database         is repository._submission_repository
learner_profile_service.repository is repository._learner_repository
revision_service.repository        is repository._revision_repository
```

All share `repository._connection_manager`; the Revision repository's
internal readers are the exact facade-owned instances (one repository graph,
no second Database/connection manager/instance, no wrapper/proxy/adapter).

### Layer 4 - Behavior

Command (F6C isolation runner):

```
pytest -q tests/test_v095f6c_submission_service_narrowing.py
       tests/test_database.py
       tests/test_history.py
       tests/test_diagnostic_calibration_v061.py
       tests/test_revision_v05.py
       tests/test_v06_configuration_dashboard.py
       tests/test_v095f6a_revision_runtime_narrowing.py
       tests/test_v095f6a0_revision_capability_completion.py
       tests/test_v095f6b_admin_reanalysis_narrowing.py
       tests/test_v095f2_service_narrowing.py
       tests/test_v095f3_learner_read_model_narrowing.py
       tests/test_journey_v093c.py
       tests/test_research_v082.py
       tests/test_v071_reliability_ui.py
       tests/test_v095f5a_calf_service_narrowing.py
       tests/test_v095f5b_research_service_narrowing.py
       tests/test_v095e_repository_modularization.py
       tests/test_v095b_router_contract.py
```

Result: **282 passed, 2 warnings** (29 new F6C tests + existing submission,
history, calibration, revision, learner, journey, research, reliability,
admin-regeneration, F2-F6B, and v0.9.5-E behavior).

### Layer 5 - Ordering and failure semantics

See submit/regenerate call orders and failure results above. Existing F6A
three-sequential-commit failure tests run unchanged and pass.

### Layer 6 - Accumulated architecture contracts

Command:

```
pytest -q tests/test_v095f2_service_narrowing.py
       tests/test_v095f3_learner_read_model_narrowing.py
       tests/test_v095f4_reanalysis_journey_narrowing.py
       tests/test_v095f5a_calf_service_narrowing.py
       tests/test_v095f5b_research_service_narrowing.py
       tests/test_v095f6a0_revision_capability_completion.py
       tests/test_v095f6a_revision_runtime_narrowing.py
       tests/test_v095f6b_admin_reanalysis_narrowing.py
       tests/test_v095f6c_submission_service_narrowing.py
       tests/test_v095e_repository_modularization.py
       tests/test_v095d_api_contract.py
       tests/contracts/api_surface_contract.py
       tests/test_v095d_parity.py
       tests/test_design_tokens_v094a.py
       tests/test_v095c_feature_extraction.py
       tests/test_v095b_router_contract.py
```

Result: **233 passed, 2 warnings** (204 F2-F6B accumulated + 29 new F6C
tests) - F2/F3/F4/F5A/F5B/F6A0/F6A/F6B dependency and transaction contracts
pass; v0.9.5-E repository facade parity passes (86 methods, 33 table owners,
zero drift) under the exact F6C `SERVICE_API_DIFF_ALLOWLIST` (accumulated
F2-F6C approved diff, no wildcards); API contract 77 path+method pairs;
frontend client 52 public methods; locale parity 520/520; migration 12;
active configuration `config-v0.9.0`. One documented pre-existing lifecycle
race flake (`test_v095b_router_contract.py::test_live_and_ready_unchanged`)
appeared once inside the large set and passed in isolation (2.07s) and on the
rerun; it is unrelated to F6C and out of scope.

### Full non-live core regression (fresh isolated database)

Command: `pytest -q --ignore=tests/live`

Result: **618 passed, 8 skipped, 2 warnings** in 291.10s (589 baseline from
the completed F6B verification + 29 new F6C tests; the Playwright/live-stack
suite was not run per scope).

### Exact launcher verification (fresh isolated database, dotenv disabled)

Command: `cmd /c "run.bat --verify"`

Result: PASS (exit 0):

- Migration **12**; **33** tables; active configuration **config-v0.9.0**;
  prompt **feedback-prompt-v0.7.1**; provider local.
- FastAPI `/api/v1/system/health` **200**; `/docs` **200**; Streamlit **200**.
- All application processes stopped; ports 8000/8501 free afterward.

## Database safety

Every write-capable run used a fresh unique temporary database with
`PYTHON_DOTENV_DISABLED=1`, `DATABASE_URL` absent, `DATABASE_PATH` inside
the temporary directory, `LLM_PROVIDER=local`, resolved-path assertions, and
cleanup. The development database was checked by SHA-256, size, and mtime
before and after every run and did not change; it was never opened. All
temporary databases and directories were removed; no listeners remain; no
user export was created or modified.

- Focused run DB: `C:\Users\16073\AppData\Local\Temp\v095f6c-zwi85aou\run.db`
- Contract run DB: `C:\Users\16073\AppData\Local\Temp\v095f6c-93_kd8pe\run.db`
- Full core run DB: `C:\Users\16073\AppData\Local\Temp\v095f6c-i46g_g6j\run.db`
- Launcher run DB:
  `C:\Users\16073\AppData\Local\Temp\v095f6c-runbat-0c2090ec\runbat-verify.db`
- Development DB: `data/writing_feedback.db` - SHA-256
  `340E0F3739FEFFD3DEF87BB6E711CB6F90A8478E7E18D833C715EDCFAB03AFF4`, size
  8,298,496 bytes, mtime `2026-08-02T11:02:25.887+08:00` before and after
  all runs (unchanged; never opened).

## Impact review and limitations

The complete F6C diff (Service narrowing, factory, both app paths,
FeedbackPipeline legacy composition, 9 script sites, the E-era capture
helper, and test updates) was reviewed; only the approved files changed.
GitNexus impact analysis on `SubmissionService`: LOW risk, exact, 25 impacted
nodes, 4 direct importers, 0 affected processes. The inactive conflict file
`app/services/factory-冲突-Rain_Win11.py` was left untouched. The CRG CLI
defect remains (uv trampoline, documented in prior stages; not repaired). The
documented lifecycle-race flake is noted above; out of scope. User-owned
paths (`AGENTS.md`, `RUN_VERIFICATION_V0.7.md`, `RUN_VERIFICATION_V0.8.2.md`,
`.claude/`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`, `CLAUDE.md`,
`data/demo_journey_manifest.json`, `data/writing_feedback.db`) were preserved
untouched.

## Decision

v0.9.5-F6C is complete and verified. `SubmissionService` depends on exactly
`SubmissionSystemPort`, `SubmissionDataPort`, `SubmissionAnalysisPort`,
`SubmissionCalibrationPort`, and the existing non-persistence collaborators;
no broad or untyped persistence dependency or capability guard remains; all
eleven direct calls route to approved owners; constructor `record_versions`,
submit and regenerate-feedback order, write counts, and partial-commit
behavior are unchanged; F2-F6B boundaries remain intact; the development
database was never opened or modified; no F6D or later-stage work was
started.
