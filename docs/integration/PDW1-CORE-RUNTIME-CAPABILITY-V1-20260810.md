# PDW1-CORE-RUNTIME-CAPABILITY-V1 — Existing-Runtime Agent Capability Execution v1 (CORE)

- Goal: `PDW1-CORE-RUNTIME-CAPABILITY-V1` — Product Delivery Wave 1, Outcome C
- Owner: CORE
- Executor: opencode-go/deepseek-v4-flash (ultra reasoning), PLANNING_DISABLED=1
- Completed: 2026-08-10
- Baseline: `b6fce9a500502c6929fe0a0e8da4748348967426` (promoted master)
- Worktree: `A:\EAP Agent Project\worktrees\shared-core` / `dept/shared-core`
- Verdict: **AMBER** — functional/evidence GREEN for the candidate; targeted
  repair required for one shared-contract guard (module-set manifest), plus
  documented pre-existing baseline failures (see Findings).

## Scope delivered (additive only)

| Path | Purpose |
| --- | --- |
| `app/runtime/__init__.py` | Package exports and provenance identity. |
| `app/runtime/errors.py` | Runtime error taxonomy (denied/unavailable/request/registration/validation/not-found). |
| `app/runtime/manifest.py` | `CapabilityManifest` schema: identity, semver version, owner, domain eligibility, operation scope, data-access scope, source, enablement, audit flag (ADR-01/02/08 fields). |
| `app/runtime/registry.py` | `CapabilityRegistry`: additive-only, versioned, duplicate registration rejected, latest-version resolution, stable listing. |
| `app/runtime/executor.py` | `CapabilityExecutor`: synchronous in-process dispatch with eligibility/scope checks, explicit `success`/`unavailable`/`ineligible`/`error` states, exception isolation, provenance + append-only in-process audit. |
| `app/runtime/capabilities.py` | Two real domain capability adapters (below). |
| `app/runtime/bootstrap.py` | `create_runtime()` default wiring (registry + executor). |
| `tests/runtime/` | 41 tests covering all acceptance scenarios. |
| `docs/integration/PDW1-CORE-RUNTIME-CAPABILITY-V1-20260810.md` | This report. |

No existing app module was modified (import-only). `app/api/main.py`, other
worktrees, raw SWECCL, and Program Control artifacts were not touched. No
parallel runtime, orchestrator, event bus, second composition root, or
runtime database was introduced — the executor is plain synchronous code.

## Required real capabilities (both wired, real, and tested)

1. **L2 task-type classification** — `l2.task_type_classifier` v1.0.0
   (owner `L2`, eligibility `["l2"]`, operations `classify_task_definition`,
   `list_task_types`) delegates to `app.services.task_type_classifier`
   (`classify_task_definition`, Domain Pack v1 G5 dictionaries). It classifies
   registered task definitions only, never learner output, and carries the
   honest `unclassified` states (`not_eap`, `ambiguous_precedence_conflict`,
   `declared_type_mismatch`, `no_prompt`).
2. **Governed corpus_query** — `corpus.query_distribution` v1.0.0
   (owner `CORPUS`, eligibility `["l2","academic","learner","corpus"]`,
   operations `query_distribution`, `corpus_version`,
   `distribution_availability`) delegates to
   `app.corpus.intelligence.CorpusIntelligence`. Every result preserves
   `learner_exposure="research_only"`; raw SWECCL path/handle injection is
   denied fail-closed (reserved keys and value markers) before the CORPUS
   boundary is touched (ADR-06 / raw-corpus rule). `CorpusUnavailableError`
   maps to the explicit `unavailable` state; `CorpusInvalidRequestError` is
   an isolated `error` state.

## DeepTutor mechanism reference (READ-ONLY, exact files/lines inspected)

DeepTutor source at `A:\DeepTutor-1.5.10` was inspected for mechanism
reference only. No code was copied; the local implementation is a thin,
domain-specific adaptation required by the Goal Packet.

| File | Lines | Mechanism noted |
| --- | --- | --- |
| `deeptutor/core/capability_protocol.py` | 21–28 | `CapabilityManifest` dataclass: name, description, stages, tools_used, cli_aliases, request_schema, config_defaults (manifest-first metadata). |
| `deeptutor/core/capability_protocol.py` | 33–40, 55–59 | `BaseCapability` ABC: static `manifest` attribute + `run` (manifest-first registration pattern). |
| `deeptutor/capabilities/registry.py` | 13–19, 22–25 | `LOOP_CAPABILITIES` tuple and `active_loop_capabilities()` — registry with stable order and per-context activation. |
| `deeptutor/capabilities/protocol.py` | 22–40 | `LoopCapability` protocol: `name`, `owned_tools`, `is_active` (declared identity/ownership). |
| `deeptutor/core/agentic/tool_dispatch.py` | 78–100 | `dispatch_tool_calls` — registry resolution at dispatch time. |
| `deeptutor/core/agentic/tool_dispatch.py` | 279–310 | `_reject_if_args_missing` — pre-dispatch structured rejection (missing required args) instead of an unhandled failure. |
| `deeptutor/core/agentic/tool_dispatch.py` | 436–441, 540–548 | `execute_tool_call` — structured result dict and `except Exception` isolation so one tool failure never crashes the loop. |

Local mappings (ADR-01): manifest → `CapabilityManifest`; registry →
`CapabilityRegistry` (additive, no replacement of `TaskTypeRegistry` or
domain-pack content); dispatch-time authorization → executor eligibility +
scope checks; structured result → `CapabilityResult` with provenance/audit.

## Design decisions

- **Deny-by-default (ADR-08):** `caller_domain` is mandatory; unknown
  capability → `unavailable`; disabled capability → `unavailable`;
  domain/operation outside declared eligibility/scope → `ineligible`.
- **Duplicate rejection (ADR-02):** same `(identity, version)` registration
  raises `CapabilityRegistrationError`; same identity with a new version is
  allowed and latest wins.
- **Exception isolation (ADR-01):** the executor never raises for capability
  execution; every outcome is a structured `CapabilityResult`.
- **Provenance/audit:** every dispatch appends an in-process audit record
  (request_id, capability_id/version, owner, caller_domain, operation,
  status, started_at/ended_at, duration_ms, error) and the result carries a
  provenance block including `runtime="existing-runtime-capability-execution-v1"`.
- **No fabrication:** `unavailable` is only produced for unregistered/
  disabled capabilities or a domain-reported unavailable artifact;
  `ineligible` only for eligibility/scope/raw-source denial; classifier
  `unclassified` states are passed through verbatim.

## Test evidence

Environment: worktree-local `.venv` via `uv sync` (85 packages, Python
3.12.13, `ENVIRONMENT READY` per `scripts/dev/run_tests.ps1` bootstrap;
spaCy `en_core_web_sm` PASS). Tests run with `python -m pytest -p
no:cacheprovider` through `uv run` (uv cache lives under the user profile;
the sandbox cannot initialize it — recorded environment limitation).

| Suite | Result | Evidence |
| --- | --- | --- |
| `tests/runtime` (41 tests) | PASS | `41 passed in 1.05s` (initial), `51 passed` with `tests/test_environment_drift.py` after literal fix |
| `tests/corpus tests/contracts` | PASS | `113 passed in 12.18s` |
| Full canonical suite (`run_tests.ps1 -Full`, isolated runner, live excluded) | 2103 passed, 8 failed, 8 skipped | failures attributed below; candidate adds no green→red regression |

`tests/runtime` covers every required scenario: successful invocation of both
real capabilities; unavailable (unregistered + disabled); ineligible
(missing caller domain, wrong domain, operation out of scope, raw SWECCL
path/handle denial); duplicate registration rejection; exception isolation;
provenance/audit fields; structured `to_dict()`; mixed-failure survival.

## Findings (baseline and candidate)

1. **Module-set manifest drift (candidate + baseline; targeted repair
   required).** `verification/shared-core-h1/module_set_manifest.json`
   (200 entries) does not record 12 modules now under `app/`: 5 were already
   tracked on master `b6fce9` before this goal (`corpus/comparison.py`,
   `corpus/student.py`, `corpus/tasksignature.py`,
   `services/legacy_genre_mapping.py`, `services/task_type_classifier.py`)
   and 7 are added by this goal (`runtime/*`). The drift guard
   `tests/test_shared_core_drift.py::TestModuleSetManifest` therefore fails.
   The repair is a shared-contract manifest update at
   `verification/shared-core-h1/module_set_manifest.json` (add the 12 paths,
   bump contract version per the shared-contract change process), which is
   outside this packet's `write_scope`; CORE must be authorized for it.
2. **Census artifact absent from master (pre-existing baseline).**
   `docs/domain/census/L2_DP4_LEGACY_ESSAYS_CENSUS_v1.0.0.json` does not
   exist in master `b6fce9` (`git cat-file -e` fails) and is untracked in the
   L2 worktree; 4 tests (`TestBehaviorDiffGate` ×2,
   `TestCensusParity` ×2) fail on any master-aligned worktree. Not caused by
   this candidate. Repair owner: L2/CORPUS artifact provisioning goal.
3. **OpenAPI snapshot stale vs promoted master (pre-existing baseline).**
   `verification/v0.9.5-h2d2/openapi_before.json` was last regenerated at
   `32b7927` (2026-08-07); wave-5 promotions added `app/api/schemas.py`,
   `app/services/learner_model.py` and corpus modules (2026-08-09), so
   `test_v095h2d2_api_dependency_bindings.py::TestFastAPIParity` fails on
   master. Not caused by this candidate. Repair owner: INT snapshot
   regeneration maintenance goal.
4. **Git dubious-ownership failure is an execution-environment artifact.**
   `test_v095e_repository_modularization.py::test_static_owner_sql_dependency_and_ddl_parity_contract`
   spawns `git` and failed only under the escalated executor, which runs as a
   different Windows user (RID …-1001) than the repository owner
   (…-1004). In-sandbox git operations (this run's preflight) succeed as the
   owning user. No global `safe.directory` was added (policy); command-scoped
   `git -c safe.directory` is the sanctioned mitigation for gate runs.

## Resource hygiene

- No background workers, sub-agents, or long-lived processes were started;
  the single full-suite process exited normally.
- No `.lock` files in `.git` or worktree gitdir; no temp DBs left by the
  isolated runner (before/after dev DB digest: None).
- Worktree-local `.venv` and `.pytest_cache` are gitignored development
  artifacts per the environment contract; no other temp artifacts remain.

## Candidate commit

Committed on `dept/shared-core` (starting `b6fce9a…`); final SHA recorded in
the structured handoff. No push, no PR, no promotion, no rebase/reset/clean.
Pre-existing untracked files (ADR-01/02/08 docs, D-09 design, align report)
preserved untouched.

## Handoff boundary

- `integration_required`: true (INT gate after repair/qualification).
- `promotion_eligible`: false (no promotion authority in this packet).
- `user_decision_required`: true — manifest update scope authorization.
- `repair_owner`: CORE (module-set manifest update); baseline repairs listed
  under findings with their owners.
