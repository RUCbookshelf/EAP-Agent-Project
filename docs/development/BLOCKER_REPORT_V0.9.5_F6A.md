# v0.9.5-F6A Blocker Report — RevisionService Runtime Repository Narrowing

**Date:** 2026-08-02
**Status:** BLOCKED — approved target contradicts source at HEAD `b766284`
**Baseline:** `b766284` (v0.9.5-F5B verification); F2-F5B commits are
ancestors.
**Specification:** `docs/development/V0.9.5_F6A_SPEC.md` (not created; see
below)

## 1. Summary

F6A cannot be implemented within its approved composition-only scope.
The approved target requires every active `RevisionService` to receive the
existing facade-owned `SQLiteRevisionRepository` instance as its runtime
repository, but at HEAD that repository does not implement two of the nine
methods `RevisionService` directly calls (`get_submission_bundle`,
`get_latest_analysis_run`). Only the broad `Database` facade provides them
today. Every change that could close the gap is explicitly forbidden by the
F6A stop conditions, so the stage stops and this blocker is created.

## 2. Missing requirement (contradiction between spec and source)

The F6A specification states the approved current architecture includes:

```text
SQLiteRevisionRepository already composed with existing Submission and
Analysis readers
```

and the approved target:

```text
RevisionService
    └── existing SQLiteRevisionRepository
          ├── existing SQLiteConnectionManager
          ├── existing Submission Bundle reader
          └── existing Analysis Run reader
```

Source at HEAD `b766284` contradicts this:

`app/infrastructure/sqlite/repositories/revision.py` (153 lines) defines
exactly one internal reader Protocol, `_SubmissionBundleReader`
(`get_submission_bundle` only), and the repository implements exactly ten
methods:

```text
normalize_revision_stage
create_revision_group
link_revision
get_revision_group
get_revision_group_for_submission
list_revision_candidates
save_revision_snapshot
list_revision_snapshots
get_latest_revision_snapshot
```

`get_submission_bundle` and `get_latest_analysis_run` are absent from
`SQLiteRevisionRepository`. The facade composes it with only the Submission
reader:

```python
# app/database/repository.py
self._revision_repository = SQLiteRevisionRepository(
    self._connection_manager, self._submission_repository
)
```

The central `RevisionRepository` Protocol
(`app/repositories/protocols.py`) declares all ten methods including the two
missing ones, but the only two runtime implementations are the `Database`
facade (delegating `get_latest_analysis_run` to `SQLiteAnalysisRepository`)
and `SQLiteRevisionRepository` (missing both).

## 3. Direct RevisionService call set at HEAD (verified from source)

`app/services/revision.py` calls through `self.repository`:

```text
get_submission_bundle        validate_relationship (3 sites), _calculate (2),
                             trajectory (1 per member)
get_latest_analysis_run      _calculate (2 sites)
create_revision_group        create_relationship (1)
link_revision                create_relationship (1)
get_revision_group           group (1)
list_revision_candidates     candidates (1)
save_revision_snapshot       recalculate (1)
list_revision_snapshots      history (1)
get_latest_revision_snapshot latest (1)
```

Nine direct calls, in agreement with the F6A specification's "known direct
RevisionService call set". The two missing repository methods are therefore
required, not optional.

## 4. Empirical evidence

Runtime probe against a fresh temporary database (no production data
touched):

```text
instance type: SQLiteRevisionRepository
has get_submission_bundle: False
has get_latest_analysis_run: False
reader attrs: ['_connection_manager', '_submission_reader']
PROBE validate_relationship -> AttributeError 'SQLiteRevisionRepository'
    object has no attribute 'get_submission_bundle'
facade has methods: True True
```

`RevisionService(repository._revision_repository)` therefore fails on the
first direct repository call; behavior cannot be preserved with the
approved runtime object.

## 5. Why every completion path is forbidden by the approved scope

1. Adding `get_submission_bundle` / `get_latest_analysis_run` to
   `SQLiteRevisionRepository` — forbidden: "Do not modify: repository
   implementations" and stop if completion requires "changing
   `SQLiteRevisionRepository`".
2. Injecting an Analysis Run reader into `SQLiteRevisionRepository` —
   forbidden: stop if completion requires "changing either internal reader",
   and "Do not: replace either reader; reconstruct the readers".
3. Keeping the `Database` facade as the runtime object for
   `RevisionService` — contradicts the approved target ("no active
   production RevisionService receives the broad Database facade").
4. Moving Submission/Analysis reads out of the repository into
   `RevisionService` — forbidden: "Do not give `RevisionService` separate
   Submission or Analysis read Ports", "move Submission Bundle reads out of
   `SQLiteRevisionRepository`", "move Analysis Run reads out of
   `SQLiteRevisionRepository`".
5. Changing the central `RevisionRepository` Protocol — forbidden: "Do not
   modify: `RevisionRepository`", "Do not create a new Revision Port".
6. Splitting `RevisionService` into multiple readers — forbidden: "The
   target is one already-composed Revision repository, not three separate
   Service dependencies".
7. Constructing a second repository graph or adapter — forbidden.

The F6A stop conditions explicitly name this situation: "Also stop if: an
active production RevisionService cannot receive the existing facade-owned
Revision repository; an active caller requires unrelated facade methods
through the RevisionService repository; ... a necessary production change
exceeds the pre-authorized composition-only scope."

## 5a. Conclusive structural evidence

- Exactly one `SQLiteRevisionRepository` class exists in the repository
  (`app/infrastructure/sqlite/repositories/revision.py:14`); no adapter,
  proxy, wrapper, or second implementation exists anywhere.
- No `__getattr__` or other dynamic delegation exists in production code;
  the E-parity guard even asserts its absence
  (`tests/test_v095e_repository_modularization.py`,
  `verification/v0.9.5-e/compare_repository_parity.py`).
- The `_AnalysisRunReader` Protocol named by the F1 audit
  (`SERVICE_REPOSITORY_DEPENDENCY_AUDIT_V0.9.5_F1.md` line 133,
  `app/infrastructure/sqlite/repositories/learner.py:12-14`) exists, but it
  is a **Learner-owned** reader consumed by `SQLiteLearnerRepository`
  (`learner.py:22,207`). It is not wired into `SQLiteRevisionRepository`
  (whose constructor accepts only `connection_manager` and
  `submission_reader`, `revision.py:15-18`), and the facade passes only
  `self._submission_repository`
  (`app/database/repository.py`, `_revision_repository` wiring).
- The F1 audit's claim (lines 113 and 187) that `SQLiteRevisionRepository`
  is "composed with `_SubmissionBundleReader` + `_AnalysisRunReader` (already
  wired in the facade)" is therefore factually incorrect at HEAD `b766284`:
  the Analysis Run reader was never wired into the Revision repository.

## 6. Root cause

The v0.9.5-E repository extraction produced a `SQLiteRevisionRepository`
that owns only the Revision aggregate's own methods and one Submission
Bundle reader, while the `RevisionRepository` Protocol retained the two
cross-aggregate reads (`get_submission_bundle`, `get_latest_analysis_run`)
that `RevisionService` needs. The F1 audit narrative
(`SERVICE_REPOSITORY_DEPENDENCY_AUDIT_V0.9.5_F1.md`, Section 4.1) describes a
"`_AnalysisRunReader` ... already wired in the facade" that does not exist
in the extracted code at HEAD. The runtime swap therefore cannot be a pure
composition change: the narrowed repository is not a structural superset of
the Service's call set.

## 7. Minimal proposed options (owner decision required)

Option A — authorise a repository-completion exception for F6A:

- add `get_submission_bundle` (delegating to the existing
  `_submission_reader`) and `get_latest_analysis_run` to
  `SQLiteRevisionRepository`;
- add an Analysis Run reader dependency (facade-owned
  `SQLiteAnalysisRepository`) to `SQLiteRevisionRepository.__init__` and the
  facade composition;
- keep all SQL, transaction boundaries, and delegation identical to the
  facade's current behavior.

This is the only path that achieves the approved F6A target, but it changes
a repository implementation, its internal reader composition, and the
facade constructor wiring, all of which the current F6A scope forbids.

Option B — defer F6A: keep `RevisionService` on the broad facade (current
behavior) and record the repository-completion gap as a prerequisite for a
future stage.

Option C — rescope F6A: approve the two-method repository completion as the
stage itself (with its own spec and verification), then run the runtime
swap as a follow-up stage.

## 8. State at blocker creation

- No F6A implementation exists; no production or test file was changed for
  F6A; the worktree contains only the pre-existing preserved user-owned
  paths (`AGENTS.md`, `RUN_VERIFICATION_V0.7.md`,
  `RUN_VERIFICATION_V0.8.2.md` modified; `.claude/`,
  `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`, `CLAUDE.md`,
  `data/demo_journey_manifest.json` untracked).
- Development database untouched: SHA-256 `340E0F...AFF4`, size 8,298,496,
  mtime `2026-08-02T11:02:25.887+08:00`.
- Ports 8000/8501 free.
- GitNexus index synced to `b766284` (refreshed for Phase 0); CRG CLI defect
  remains (uv trampoline, one attempt, not repaired).
- The F6A specification (`V0.9.5_F6A_SPEC.md`) was not created because Phase
  0 inventory and the runtime probe already disprove the approved target;
  this blocker report records the required facts instead.

## 9. Requested decision

Owner to choose Option A (authorise the repository-completion exception),
Option B (defer), or Option C (rescope) before F6A can proceed.


## 10. Resolution (2026-08-02)

The owner authorized **Option C**: v0.9.5-F6A remains formally blocked, and
a separate prerequisite stage **v0.9.5-F6A0 — Revision Repository Capability
Completion** (`docs/development/V0.9.5_F6A0_SPEC.md`) makes the existing
facade-owned `SQLiteRevisionRepository` structurally satisfy the central
`RevisionRepository` contract (adding `get_submission_bundle` and
`get_latest_analysis_run` delegations plus the facade-owned Analysis reader
wiring). The original F6A runtime narrowing may be rebaselined and resumed
only after F6A0 is complete and separately authorized; F6A0 itself performs
no runtime narrowing.

## 11. Resolution completed (2026-08-02)

F6A0 completed and verified (`693ff48`, `b4d37af`), and the owner authorized
resuming F6A on the new baseline. v0.9.5-F6A itself is now complete and
verified (`8e20730` refactor + verification commit; see
`RUN_VERIFICATION_V0.9.5_F6A.md`): every active `RevisionService` receives
the existing facade-owned `SQLiteRevisionRepository`, the three-sequential-
commit workflow and Essay-update ownership are unchanged, and no repository,
SQL, transaction, or Protocol change was required beyond F6A0.
