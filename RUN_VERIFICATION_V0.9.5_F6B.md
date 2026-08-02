# v0.9.5-F6B Verification - AdminReanalysisService Persistence Dependency Narrowing

**Date:** 2026-08-02
**Status:** PASS
**Baseline commit:** `bdd31bb` (v0.9.5-F6A verification); F2-F6A commits are
ancestors
**Implementation commit:** `refactor(v0.9.5-f6b): narrow admin reanalysis dependencies`
**Verification commit:** `test(v0.9.5-f6b): verify admin reanalysis contracts`
**Specification:** `docs/development/V0.9.5_F6B_SPEC.md`
**Authorization:** Owner-authorized F6B stage (pasted instruction file).

## Scope (AdminReanalysisService persistence dependency narrowing only)

Removed the broad, untyped `repository` dependency from
`AdminReanalysisService` and replaced it with three exact consumer-owned
structural Ports (`AdminConfigurationReadPort`, `AdminSubmissionReadPort`,
`AdminAnalysisPort`), retaining the existing required keyword-only
`revision_repository: RevisionRepository` dependency introduced by F6A. All
six direct persistence calls route to approved owners; the
`ConfigurationService`, `SubmissionService`, and embedded `RevisionService`
collaborations and all preview/run/failure/partial-commit semantics are
unchanged. No Repository implementation, SQL, transaction boundary, API,
schema, domain rule, prompt, provider, or UI behavior changed.

## Three new consumer-owned Ports

Defined in `app/services/admin_reanalysis.py` (`typing.Protocol` +
`@runtime_checkable`), signatures copied from current HEAD source:

```text
AdminConfigurationReadPort  -> get_configuration(configuration_id_or_version: str) -> ConfigurationVersion | None
AdminSubmissionReadPort    -> get_submission_bundle(essay_id: int) -> dict[str, Any] | None
                              list_student_submissions(student_id: str) -> list[dict[str, Any]]
AdminAnalysisPort          -> get_analysis_run(analysis_run_id: str) -> dict[str, Any] | None
                              save_analysis_run(essay_id: int, analysis: AnalysisResult) -> AnalysisResult
```

No Revision method appears in the three Ports; no broad Protocol inheritance;
no `Database` or concrete SQLite import in the Service module.

## Retained RevisionRepository

The central `RevisionRepository` is unchanged (F6A0/F6A result) and continues
to (a) serve the direct `get_revision_group` read and (b) back the embedded
`RevisionService`. No second Revision argument, no new Revision Port, no
replacement of the central Protocol.

## Constructor before and after

Before:

```python
def __init__(self, repository, settings: Settings, configurations: ConfigurationService,
             submission_service: SubmissionService, *,
             revision_repository: RevisionRepository) -> None:
```

After:

```python
def __init__(
    self,
    settings: Settings,
    configuration_reader: AdminConfigurationReadPort,
    submission_reader: AdminSubmissionReadPort,
    analysis_repository: AdminAnalysisPort,
    configurations: ConfigurationService,
    submission_service: SubmissionService,
    *,
    revision_repository: RevisionRepository,
) -> None:
```

No broad `repository` parameter or `self.repository`/`self.repo` field
remains; `revision_repository` remains required and keyword-only; no fallback,
`hasattr`, dynamic discovery, concrete implementation check, `Database`
import, or SQLite import was added.

## All active construction sites (Phase 0 inventory, current source)

1. `app/api/main.py` `_run_startup` - explicit keyword arguments with the
   facade-owned `_configuration_repository`, `_submission_repository`,
   `_analysis_repository`, `_revision_repository`
2. `app/api/main.py` `_build_full_app` - same
3. `tests/test_v06_configuration_dashboard.py:204`
4. `tests/test_v06_configuration_dashboard.py:222`
5. `tests/test_v06_configuration_dashboard.py:244`
6. `tests/test_v06_configuration_dashboard.py:268`
7. `tests/test_v095f6a_revision_runtime_narrowing.py:122`

No operational script constructs the Service directly. Every active instance
receives the existing facade-owned repositories; no active instance receives
the broad facade.

## Six method-to-owner mappings

```text
get_configuration        -> AdminConfigurationReadPort (SQLiteConfigurationRepository)
get_submission_bundle    -> AdminSubmissionReadPort   (SQLiteSubmissionRepository)
list_student_submissions -> AdminSubmissionReadPort   (SQLiteSubmissionRepository)
get_analysis_run         -> AdminAnalysisPort         (SQLiteAnalysisRepository)
save_analysis_run        -> AdminAnalysisPort         (SQLiteAnalysisRepository)
get_revision_group       -> RevisionRepository        (SQLiteRevisionRepository)
```

AST-based proof: the Service's direct persistence calls are exactly this six-
method set; no seventh method and no dynamic method name exists.

## Preview call order and zero-write result

Preview (read-only): `_scope` (submission -> `get_submission_bundle`; student
-> `list_student_submissions`; revision_group -> `get_revision_group`;
analysis_run -> `get_analysis_run`), then `configurations.active()` (when no
explicit version) or `get_configuration(version)`, then analyzer registry
lookup. Recorder tests prove preview performs zero calls to
`save_analysis_run`, `regenerate_feedback`, or any Revision write method, and
preserves the exact read sequence (`bundle` -> `active` for the default path).

## Run call order result

`preview` (re-read) -> `get_configuration` (validated configuration) ->
analyzer lookup -> per essay: `get_submission_bundle` ->
`analyzer.analyze` -> `save_analysis_run` (exactly one per essay) -> (if
`call_llm`) `regenerate_feedback` -> per essay bundle read for
`revision_group_id` -> per group: `revisions.group` then
`revisions.recalculate`. Recorder test proves the exact ordered sequence
`bundle, active, get_configuration, bundle, save_analysis_run, bundle` for a
single submission scope with feedback disabled; feedback-enabled test proves
exactly `save_analysis_run, regenerate_feedback` per essay.

## Failure and partial-commit results

- Failure before `save_analysis_run` (bundle row missing `essay_text`): zero
  Analysis writes; exception propagates unchanged.
- Failure in `save_analysis_run`: exception propagates; zero
  `regenerate_feedback` calls; zero Revision recalculation; no Analysis row
  added.
- Failure after a successful `save_analysis_run` (feedback regeneration
  fails): the committed Analysis Run remains visible; no compensation.
- Failure in the Revision collaborator after Analysis persistence
  (`revisions.recalculate` fails): both committed Analysis Runs remain
  visible; the pre-existing Revision snapshot count is unchanged; exception
  propagates; no compensation.
- Feedback disabled: exactly zero `regenerate_feedback` calls (run success
  recorder test).

## Verification layers

### Layer 1 - Static

- `py_compile` of all changed/new modules: PASS.
- Imports of all three Ports, `AdminReanalysisService`, and both
  application-construction paths: PASS (no circular imports); constructor
  signature confirmed by probe.
- Task-scoped `git diff --check`: PASS (scoped to F6B files; pre-existing
  trailing whitespace in the user-owned `AGENTS.md` was excluded and not
  touched). UTF-8/replacement scan: 0 defects in all changed files.

### Layer 2 - Dependency contracts

- Exact Port method sets and source-signature parity with the concrete SQLite
  repositories: PASS (inspect-based).
- Central `RevisionRepository` unchanged; no `Database`/SQLite import, no
  `hasattr`, no fallback, no broad or untyped persistence parameter in the
  Service; no Repository implementation, SQL, or migration file changed
  (git path diff empty).

### Layer 3 - Runtime identity

Both application-construction paths prove:

```text
configuration_reader is repository._configuration_repository
submission_reader    is repository._submission_repository
analysis_repository  is repository._analysis_repository
revision_repository  is repository._revision_repository
revisions.repository is repository._revision_repository
```

All four repositories share `database._connection_manager`; the Revision
repository's internal Submission/Analysis readers are the exact facade-owned
instances (one repository graph, no second `Database`/connection
manager/instance).

### Layer 4 - Behavior

Command (F6B isolation runner):

```
pytest -q tests/test_v095f6b_admin_reanalysis_narrowing.py
       tests/test_v06_configuration_dashboard.py
       tests/test_v095f6a_revision_runtime_narrowing.py
       tests/test_v095f6a0_revision_capability_completion.py
       tests/test_revision_v05.py
       tests/test_v095f2_service_narrowing.py
       tests/test_v095f3_learner_read_model_narrowing.py
       tests/test_v095f5a_calf_service_narrowing.py
       tests/test_v095f5b_research_service_narrowing.py
       tests/test_v095e_repository_modularization.py
       tests/test_v095b_router_contract.py
```

Result: **154 passed, 2 warnings** (16 new F6B tests + existing Admin
Reanalysis preview/run/scope/API behavior, F2-F6A dependency contracts,
Revision behavior and transaction/failure contracts, and v0.9.5-E facade
parity).

### Layer 5 - Failure and partial commits

See Failure and partial-commit results above; existing F6A
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
       tests/test_v095e_repository_modularization.py
       tests/test_v095d_api_contract.py
       tests/contracts/api_surface_contract.py
       tests/test_v095d_parity.py
       tests/test_design_tokens_v094a.py
       tests/test_v095c_feature_extraction.py
       tests/test_v095b_router_contract.py
```

Result: **204 passed, 2 warnings** (188 F2-F6A accumulated + 16 new F6B
tests) - F2/F3/F4/F5A/F5B/F6A0 dependency contracts pass; v0.9.5-E repository
facade parity passes (86 methods, 33 table owners, zero drift) under the
exact F6B `SERVICE_API_DIFF_ALLOWLIST` (accumulated F2-F6B approved diff, no
wildcards); API contract 77 path+method pairs; frontend client 52 public
methods; locale parity 520/520; migration 12; active configuration
`config-v0.9.0`.

### Full non-live core regression (fresh isolated database)

Command: `pytest -q --ignore=tests/live`

Result: **589 passed, 8 skipped, 2 warnings** in 268.71s (573 baseline from
the completed F6A verification + 16 new F6B tests; the Playwright/live-stack
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

- Focused run DB: `C:\Users\16073\AppData\Local\Temp\v095f6b-8mtuqop_\run.db`
- Contract run DB: `C:\Users\16073\AppData\Local\Temp\v095f6b-b_ktdb_7\run.db`
- Full core run DB: `C:\Users\16073\AppData\Local\Temp\v095f6b-mpsd0_tj\run.db`
- Launcher run DB:
  `C:\Users\16073\AppData\Local\Temp\v095f6b-runbat-3268fedd\runbat-verify.db`
- Development DB: `data/writing_feedback.db` - SHA-256
  `340E0F3739FEFFD3DEF87BB6E711CB6F90A8478E7E18D833C715EDCFAB03AFF4`, size
  8,298,496 bytes, mtime `2026-08-02T11:02:25.887+08:00` before and after
  all runs (unchanged; never opened).

## Impact review and limitations

The complete F6B diff (Service narrowing, both app-construction paths, five
test construction sites, new focused test file, runner, and documentation)
was reviewed; only the approved files changed. GitNexus impact analysis on
`AdminReanalysisService`: LOW risk, exact, 19 impacted nodes, 2 direct
importers; GitNexus was synchronized to HEAD `bdd31bb` before Phase 0. The
CRG CLI defect remains (uv trampoline, documented in prior stages; not
repaired). The pre-existing `test_v095b_router_contract` lifecycle flake is
documented and was not present in the F6B runs; out of scope. User-owned
paths (`AGENTS.md`, `RUN_VERIFICATION_V0.7.md`, `RUN_VERIFICATION_V0.8.2.md`,
`.claude/`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`, `CLAUDE.md`,
`data/demo_journey_manifest.json`, `data/writing_feedback.db`) were preserved
untouched.

## Decision

v0.9.5-F6B is complete and verified. `AdminReanalysisService` depends on
exactly `AdminConfigurationReadPort`, `AdminSubmissionReadPort`,
`AdminAnalysisPort`, the unchanged central `RevisionRepository`, and the
existing settings/Service collaborators; no broad or untyped persistence
dependency remains; all six direct calls route to approved owners; preview is
zero-write; Analysis persistence count/ordering, feedback conditions,
partial-commit behavior, and the F2-F6A boundaries are unchanged; the
development database was never opened or modified; no F6C or later-stage work
was started.
