# PDW1-CORE-RUNTIME-CAPABILITY-V1 REPAIR — CORE Executor Report

- Goal: `PDW1-CORE-RUNTIME-CAPABILITY-V1__REPAIR`
- Owner: CORE
- Dispatch: `program-control\runs\PDW1-CORE-RUNTIME-CAPABILITY-V1__REPAIR__20260809T170005Z__755b1e`
- Authorized worktree: `A:\EAP Agent Project\worktrees\shared-core`
- Branch: `dept/shared-core`
- HEAD (parent candidate): `51e04212ea95e20efef42c3041edf7e6e8a215d2`
- Verdict: GREEN
- Run date: 2026-08-10

## Scope

Program-authorized single-file shared-contract repair: record exactly the 12
documented module paths in
`verification/shared-core-h1/module_set_manifest.json`, then confirm the drift
guard and the runtime suite pass against the committed candidate. No other
file was modified, and no new commit was created (repair rides on the parent
candidate branch state). No promotion, push/PR, reset/clean/rebase.

## Preflight

- `git rev-parse --show-toplevel` → `A:/EAP Agent Project/worktrees/shared-core`
- `git branch --show-current` → `dept/shared-core`
- `git rev-parse HEAD` → `51e04212ea95e20efef42c3041edf7e6e8a215d2`
- Pre-existing untracked files preserved (untouched):
  - `docs/architecture/ADR-01-single-runtime-extension-contract.md`
  - `docs/architecture/ADR-02-registry-federation-contract.md`
  - `docs/architecture/ADR-08-skills-mcp-security-contract.md`
  - `docs/integration/D09-EPISTEMIC-STATUS-MIGRATION-DESIGN.md`
  - `docs/integration/PDW1-ALIGN-CORE-B6FCE9-20260809.md`

## Before evidence

Manifest (baseline `b171cce`, frozen 2026-08-07) did not record the 12 modules.
Drift diff computed against the live `app/` set:

```text
UNRECORDED: ['corpus/comparison.py', 'corpus/student.py',
  'corpus/tasksignature.py', 'runtime/__init__.py', 'runtime/bootstrap.py',
  'runtime/capabilities.py', 'runtime/errors.py', 'runtime/executor.py',
  'runtime/manifest.py', 'runtime/registry.py',
  'services/legacy_genre_mapping.py', 'services/task_type_classifier.py']
STALE: []  DUPLICATES: False
```

Guard before repair:

```text
tests/test_shared_core_drift.py::TestModuleSetManifest
1 failed, 1 passed — test_current_module_set_matches_manifest failed with
"module drift: unrecorded modules under app/: [<the 12 paths>]"
```

## Change applied

`verification/shared-core-h1/module_set_manifest.json` — exactly 12 entries
inserted into the `modules` array, in the existing alphabetical entry format
(all other keys untouched: `format` 1, `frozen_at` 2026-08-07, `baseline`
`b171cce`):

```text
corpus/comparison.py
corpus/student.py
corpus/tasksignature.py
runtime/__init__.py
runtime/bootstrap.py
runtime/capabilities.py
runtime/errors.py
runtime/executor.py
runtime/manifest.py
runtime/registry.py
services/legacy_genre_mapping.py
services/task_type_classifier.py
```

`git diff --stat`: `1 file changed, 12 insertions(+)` — no other file touched.

## After evidence

```text
TOTAL_ENTRIES: 212
UNRECORDED: []  STALE: []  DUPLICATES: False
```

## Acceptance gate tests

```text
tests/test_shared_core_drift.py::TestModuleSetManifest — 2 passed
tests/runtime — 41 passed
```

## Handoff

See the structured handoff returned to PROGRAM
(`handoff_id` `H-PDW1-CORE-RUNTIME-CAPABILITY-V1__REPAIR-755b1e-20260810`).
