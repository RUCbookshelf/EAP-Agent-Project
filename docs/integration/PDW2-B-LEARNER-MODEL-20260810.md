# PDW2-B-LEARNER-MODEL — Longitudinal Learner Model v1 (department handoff)

Owner: LEARNER · Worktree: `A:\EAP Agent Project\worktrees\learner` ·
Branch: `dept/feedback-learner` · Starting baseline: `59500127`

Goal packet: `PDW2-B-LEARNER-MODEL` (Wave-2 Goal B). TDD (failing tests
first), new files only, no in-place modification of existing app modules, no
promotion/push/PR/reset/clean/rebase. Verdict: **AMBER** — functional and
evidence scope GREEN; integration-time mechanical repairs required (shared
module-set manifest refresh), consistent with the CORE PDW2-A precedent.

## Scope delivered

New module `app/learner/wave2/` (longitudinal model services):

- `models.py` — typed observation contracts: `ObservationRecord`,
  `OccurrenceEntry`, `SubmissionSample`, `RevisionBehavior` with
  observation-only `RevisionResponseState`
  (corrected_after_feedback / persisted_after_revision / reappeared_later /
  no_revision_evidence), `ProficiencyContext` with `ExternalAnchor`
  (CET-4/CET-6/IELTS/TOEFL/OTHER) guarded by an invariant that
  `derived_from_corpus` can never be True, and computed views
  (`ObservationStatusView`, `RecurringDifficulty`, `StrengthView`,
  `StableObservation`, `ProficiencyContextView`, list/envelope models) with
  first-class `HistoryState` (sufficient / insufficient_history + reasons).
- `repository.py` — locally-defined `ObservationRepository` protocol plus
  `InMemoryObservationRepository` (test/branch-local default). It does NOT
  import CORE-branch-only persistence (`app.infrastructure...wave2`,
  migration-14 DDL).
- `sqlite_repository.py` — self-contained `SqliteObservationRepository`
  (TEST-ONLY) that creates its own `wave2_learner_*` tables inside a
  caller-provided test database (pytest tmp_path); not wired into the
  composition root.
- `services.py` — `LongitudinalLearnerService` implementing the acceptance
  queries: has this observation appeared before (prior_occurrence_count /
  appeared_before), how often in qualified recent writing
  (`QualifiedFrequency` over the last N qualified samples), in which
  contexts, was it addressed in a prior revision, what is stable recently
  (repeated strength history + previously recurring issue no longer observed
  across recent qualified samples, with `min_qualified_recent` gate), what
  current evidence exists (admissible, provenance-complete only), plus
  recurring difficulties (occurrence history, recency, revision response)
  and strengths.

New router `app/api/routers/wave2_modules/learner_api.py` (directory created
only; CORE's `wave2_modules/__init__.py` lands at integration) exposing a
module-level `router` with:

- `GET /api/v1/wave2/learner/observations`
- `GET /api/v1/wave2/learner/observations/{observation_id}`
- `GET /api/v1/wave2/learner/difficulties`
- `GET /api/v1/wave2/learner/strengths`
- `GET /api/v1/wave2/learner/stable`
- `GET /api/v1/wave2/learner/proficiency-context`
- `GET /api/v1/wave2/learner/evidence`

`main.py`, `app/api/routers/wave2.py` and every existing module are
untouched. Tests under `tests/learner/test_wave2_*.py` (plus the shared
`wave2_helpers.py` builder). Report: this file.

## Non-normative language guarantees

All outputs carry `claims_status: "observation_only"` and limitations
stating the prohibition (WU-D F11; documentation-mode scanned). Claim-bearing
strings (labels, statements) scan clean under the strict
`NormativeClaimsScanner`; the synthetic and API tests assert both modes.
Revision behavior states describe what was observed across revisions only;
stability means "not observed in recent qualified samples", never ability or
learning-gain. Proficiency context anchors are declared external references
and are never converted from corpus statistics (enforced by model
validator). Insufficient-history states are explicit everywhere history is
thin (single occurrence, fewer than 2 qualified recent samples, no context
record, no anchors).

## Synthetic learner demonstration

`tests/learner/test_wave2_synthetic_learner.py` seeds one learner
(`L-SYN-001`) with 5 submissions (S-001..S-005), 2 revision events, a
recurring difficulty (subject-verb agreement, 2 occurrences, corrected after
feedback then reappeared later), a second recurring difficulty present in the
recent window (not stable), a single-occurrence difficulty (explicit
insufficient history), a strength with 3 positive occurrences, external
anchors (CET-4 learner-declared, IELTS external certificate), 8 admissible
evidence records with provenance chains and 1 LIMITED record excluded. The
same scenario runs against both the in-memory and the self-contained SQLite
repositories (fixture parameterization).

## Test evidence

| Suite | Result |
| --- | --- |
| TDD red phase (5 wave2 test modules) | FAIL as designed — `ModuleNotFoundError: app.learner.wave2`, `app.api.routers.wave2_modules` |
| Wave-2 tests (models/repository/service/synthetic/API) | 65 passed |
| tests/learner + tests/shared + tests/contracts regression | 383 passed |
| Repo-wide smoke (excludes tests/live) | 2212 passed, 8 skipped, 7 failed (all pre-existing baseline-class, see below) |

Repo-wide failures classified as pre-existing at baseline `59500127` (none
caused by in-place changes; this Goal added files only):

1. `test_shared_core_drift.py::test_current_module_set_matches_manifest` —
   module-set manifest drift: pre-existing `corpus/seccl.py` (documented
   program follow-up D-27) plus the new wave2 modules. Manifest refresh is
   an integration-time mechanical repair owned by the shared-contract change
   process (CORE PDW2-A documented the identical class as its AMBER
   blocking finding).
2. `test_environment_drift.py::test_no_absolute_developer_specific_python_paths`
   — corpus-owned test literals `tests/corpus/test_seccl.py`,
   `tests/corpus/test_seccl_artifacts.py` (untouched by this Goal).
3. `test_learner_model_task_type_v1.py` (2) and
   `test_legacy_genre_mapping_v1.py` (2) — missing L2-domain census artifact
   `docs/domain/census/L2_DP4_LEGACY_ESSAYS_CENSUS_v1.0.0.json`, absent at
   baseline HEAD (verified via `git ls-tree`).

## Resource hygiene

- `git status`: only new files (app/learner/wave2/*, learner_api.py,
  tests/learner/test_wave2_*.py, wave2_helpers.py, this report) plus the
  pre-existing preserved untracked evidence (3 prior integration docs,
  `tests/learner/__init__.py`).
- `git diff --check` clean; no forbidden paths touched
  (app/database, app/infrastructure, app/services, app/corpus, app/revision,
  main.py, wave2.py); `__pycache__` ignored by repository .gitignore.
- No push, PR, promotion, reset, clean, rebase, or other-destination writes.

## Integration notes

- `app/api/routers/wave2_modules/learner_api.py` merges cleanly with CORE's
  `wave2_modules/__init__.py` and is mountable by CORE's `wave2.py` assembly
  (module-level `router`; verified importable as a namespace package).
- The branch-local default service uses the in-memory repository; the
  composition-root wiring and the shared migration-14 persistence land at
  integration (CORE PDW2-A dependency, AMBER).
- Integration-time mechanical repairs: module-set manifest refresh
  (record 7 wave2 paths), census artifact availability (L2 domain), corpus
  path-literal cleanup (CORPUS-owned), D-27 follow-up.

## Blocking findings

- Shared module-set manifest must record the new wave2 modules before
  integration qualification (integration-time repair; not promotion-blocking
  for this department handoff).
