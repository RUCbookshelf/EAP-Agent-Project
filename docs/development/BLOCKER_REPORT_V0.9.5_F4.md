# v0.9.5-F4 Blocker Report — Out-of-Scope JourneyService Construction Site

**Date:** 2026-08-02
**Stage:** v0.9.5-F4 Phase 0 (baseline and call-site confirmation)
**Status:** RESOLVED — owner authorized the two-line operational-script
exception on 2026-08-02
**Baseline commit:** `256b172` (approved v0.9.5-F3 verification)

## Resolution

The owner selected Option 1 and granted an explicit v0.9.5-F4 scope exception
limited to the two existing `JourneyService` construction sites in
`scripts/demo_journey.py` (approximately lines 105 and 241). The old broad
construction `JourneyService(repository)` is replaced with

```python
JourneyService(
    repository._learner_repository,
    repository._practice_repository,
)
```

matching the implemented two-Port constructor order
(`student_reader`, `projection_reader`). No other script logic, CLI
argument, output, ordering, exception handling, database initialization, or
cleanup behavior changes. The exception is limited to those two lines; no
other script, router, Service, or dependency helper may access facade-owned
private repositories.

## Blocker

`scripts/demo_journey.py` is an active JourneyService construction site that
depends on the old single-broad-dependency constructor:

- `scripts/demo_journey.py:105` — `journey = JourneyService(repository)`
- `scripts/demo_journey.py:241` — `journey = JourneyService(repository).get_journey(DEMO_LEARNER)`

`repository` is the 86-method `Database` facade. The v0.9.5-F4 spec requires
changing `JourneyService` to exactly two explicit read Ports
(`JourneyStudentReadPort`, `JourneyProjectionReadPort`) and forbids:

- keeping the broad `Any`/`Database` dependency;
- adding a compatibility fallback inside the narrowed Service;
- constructing the Service from the facade outside the composition root.

The same spec explicitly lists `modify operational scripts` under
**Do not modify**, and `scripts/demo_journey.py` is not among the allowed
production changes (`app/services/reanalysis.py`, `app/journey/service.py`,
`app/api/main.py`, `app/api/deps.py`, `app/api/routers/journey.py`, minimal
`__init__.py` export updates).

Therefore the spec's own stop condition applies:

> If an additional active production construction site exists outside the
> approved file scope, stop and document it before editing.

## Impact of proceeding without a decision

If `JourneyService.__init__` is narrowed to two Ports and the script is left
unchanged:

- `scripts/demo_journey.py --setup/--status` breaks at runtime
  (`TypeError` on the old one-argument constructor);
- `tests/test_journey_v093c.py::test_setup_status_cleanup_scope` executes the
  script through `subprocess` and would fail in the full core regression.

No permitted implementation choice (two-Port constructor, no fallback, no
script edit) leaves the script working, so this cannot be repaired within the
approved file scope.

## Options for the owner (pick one)

1. **Authorize a minimal operational-script update (recommended).** Change the
   two construction lines in `scripts/demo_journey.py` to supply the
   facade-owned repositories, e.g.
   `JourneyService(repository._learner_repository, repository._practice_repository)`
   — the same private-access pattern already used by the F2/F3 composition
   root (`app/api/main.py`). No other script behavior changes.
2. **Explicitly declare the demo script out of scope and accept that it is
   frozen as a known-broken legacy caller** (not recommended; violates the
   preserved-behavior requirement and would fail the core regression).
3. **Abort v0.9.5-F4** and return to the previous stage.

## Phase 0 evidence collected before stopping

- HEAD `256b172` confirmed; F2 (`7927ca7`) and F3 (`a24312a`, `256b172`)
  commits are ancestors.
- GitNexus index refreshed to `256b172` (up-to-date). Code Review Graph CLI is
  unavailable in this environment (uv trampoline broken; installed tool
  directory missing), so its index could not be refreshed; static source at
  HEAD remains authoritative.
- ReanalysisService construction sites: `app/api/main.py:175` (`_run_startup`)
  and `app/api/main.py:360` (`_build_full_app`); no test or script constructs
  it directly; routers consume it from application state via
  `get_reanalysis`.
- JourneyService construction sites: `app/api/routers/journey.py:16`
  (per-request; approved for change), `scripts/demo_journey.py:105,241`
  (blocker), `tests/test_journey_v093c.py:47,396,439` (approved for minimal
  constructor updates).
- Reanalysis uses exactly the two approved methods: `get_submission_bundle`
  (read-only connection) then `save_analysis_run` (independent Analysis
  repository transaction); no shared transaction exists.
- Journey uses exactly the nine approved methods (`get_student` plus the eight
  Practice-owned projections); it performs no writes.
- Dev database SHA-256
  `340E0F3739FEFFD3DEF87BB6E711CB6F90A8478E7E18D833C715EDCFAB03AFF4`
  (mtime 2026-08-02T11:02:25+08:00) unchanged; ports 8000/8501 free.

## Decision required

Choose option 1, 2, or 3 above. No F4 production file has been edited and no
test has been changed.
