# PDW2-C-L2-REVISION-SCAFFOLD — Wave-2 Goal C Report (L2)

Goal: Context-Aware Revision Loop v1 + Personalized Learning Bridge
(`revision_api`, `personalized_api`).

| Field | Value |
| --- | --- |
| Goal ID | `PDW2-C-L2-REVISION-SCAFFOLD` |
| Owner | L2 |
| Worktree | `A:\EAP Agent Project\worktrees\l2-writing` |
| Branch | `dept/l2-writing` |
| Starting SHA | `59500127ca2cf798ae730cee2a5a3e16707c320c` |
| Status | DEPARTMENT GREEN (functional + resource hygiene) |
| Promotion / push / PR | none (promotion authority false) |

## Scope delivered (NEW files only)

- `app/l2/wave2/` — new L2 module:
  - `models.py` — two-level task model (`task_type` five-type taxonomy
    unchanged + `writing_context` genre with optional metadata), version
    records, revision observations, historical feedback, priority plan,
    scaffold contracts, LearningItem v1.
  - `repository.py` — locally-defined `RevisionLoopRepository` protocol +
    in-memory implementation (mirrors CORE migration-14 semantics: tasks,
    submission revisions with ancestry/timestamps/task-context/analysis/
    feedback links, learning items).
  - `sqlite_repository.py` — self-contained TEST-ONLY SQLite implementation.
  - `corpus_routing.py` — locally-defined written-corpus routing
    protocol/fake (written default -> WECCL20; SECCL spoken+secondary,
    excluded unless explicit spoken opt-in; research_only; descriptive_only;
    no import of the CORPUS routing module which lands at integration).
  - `pipeline.py` — `WritingPipelinePort` + `ExistingWritingPipeline`
    adapter over the existing composition-root services
    (`SubmissionService.submit`, `ReanalysisService.run`,
    `SubmissionService.regenerate_feedback`).
  - `revision_loop.py` — `RevisionLoopService` (task creation with
    deterministic classification provenance, append-only V1/V2/V3
    submission versions through the real pipeline, ancestry, bounded
    revision observation, reanalysis) + `build_revision_observation`.
  - `personalized.py` — `PersonalizedBridgeService` (historical feedback
    states grounded in stored submissions; priority plan; 7-level
    progressive scaffold, default SCAFFOLD FIRST; scaffold history;
    LearningItem v1 lifecycle).
- `app/api/routers/wave2_modules/revision_api.py` — `/api/v1/wave2/revision/`
  (tasks, submit, revise, versions, observation, reanalysis).
- `app/api/routers/wave2_modules/personalized_api.py` —
  `/api/v1/wave2/personalized/` (priority-plan, scaffold, learning-items).
- `tests/test_wave2_l2_*.py` + `tests/wave2_l2_pipeline.py` — 71 wave2 tests.

No existing app module was modified (`git diff --stat` empty; only new
untracked files added). Pre-existing untracked L2 evidence (domain docs,
integration reports, census) is preserved byte-identically.

## Key semantics

1. **Two-level task model** — `task_type` is fixed to the qualified
   five-type taxonomy (opinion, argumentative, discussion, problem_solution,
   general_eap) plus the D-22 `legacy_unclassified` sentinel (test asserts
   identity with the registry l2 namespace). `writing_context` is the second
   level (cet4/cet6/ielts_task2/toefl_style/course_essay/email/application/
   reflective_journal/other) with optional metadata (audience, purpose,
   word constraint, assessment environment, genre expectations). Task
   prompt + context are preserved on every submission version and stored
   submission row.
2. **Revision versioning** — WritingTask -> V1 -> V2 -> V3 with ancestry,
   timestamps, task-context snapshot, analysis-run/feedback-record links and
   essay-text hashes. Each revision calls the EXISTING pipeline (which
   itself persists revision groups/snapshots); a new submission row is
   always created — prior versions are never overwritten (tested with three
   revisions and byte-level text preservation).
3. **Revision observation** — bounded observational language: what changed
   (token diff), which feedback areas appear addressed/remaining, newly
   observed areas, apparent independent corrections (source-diagnosis areas
   not covered by prior feedback that are no longer observed), plus an
   explicit no-intent-inference statement. No causation claims.
4. **Reanalysis** — re-enters the real pipeline: existing
   `ReanalysisService.run` (real analyzer, append-only run) then existing
   `SubmissionService.regenerate_feedback` (real feedback path). Version
   records are updated with the new run/feedback links and an auditable
   `reanalysis_events` list.
5. **Written-corpus routing** — locally defined protocol/fake; written
   requests route to WECCL20 (research_only, descriptive_only, secondary
   False); SECCL is never a written candidate; spoken requests require
   `allow_secondary=True` + `l2_speaking` domain. The module does not
   import the CORPUS routing module (asserted by test).
6. **Personalized bridge** — local observations (current draft), global
   bounded whole-text observations (mean length/lexical diversity/
   connective density + basic organization observation with explicit
   "discourse_organization validated measurement NOT established"
   limitation), historical feedback derived from stored submission bundles
   (recurring/stable/reappeared/first_observed/insufficient-history;
   supporting submission ids + evidence refs; never fabricated for learners
   without stored history). Priority plan: <= 3 actionable items,
   recurrence/context/revision-success aware, explicitly NOT a
   learner-performance ranking. Scaffold: 7 progressive levels, default
   SCAFFOLD FIRST (level 1), deterministic templates that help the learner
   revise and never write the essay; scaffold events recorded. LearningItem
   v1: durable learning target linked to learner/originating evidence/
   feedback reference/revision history/task context/status; explicit
   no-FSRS and no-practice/tutor notes.
7. **Non-normative language** — composed outputs are scanned with the
   shared `NormativeClaimsScanner` (strict) and rejected structurally
   (HTTP 500) on any violation; request free-text with unsupported
   normative/mastery claims is rejected (HTTP 422). Explicit
   insufficient-history states are first-class in every personalized
   output.

## TDD evidence

- Red phase: all six new test modules failed with
  `ModuleNotFoundError: No module named 'app.l2'` before implementation.
- Green phase: `71 passed` across models, corpus routing, repository
  (in-memory + TEST-ONLY SQLite), revision loop (real pipeline), personalized
  bridge (returning-learner fixture through the real pipeline), and both
  router modules (TestClient).
- Regression subset: `177 passed` including `test_writing_intelligence_slice`,
  `test_task_type_classifier_v1`, `test_revision_v05`, `test_learner_model_v07`,
  `test_composition_root`, `test_v095d_parity`, `test_legacy_genre_mapping_v1`,
  `test_environment_drift`.

## Baseline-class failures (not regressions)

- `test_shared_core_drift::test_current_module_set_matches_manifest` —
  the frozen module-set manifest does not record the new wave2 module paths
  (same documented integration-time repair class as CORE PDW2-A and LEARNER
  PDW2-B; manifest refresh owned by INT at integration).
- `test_environment_drift::test_no_absolute_developer_specific_python_paths`
  — pre-existing corpus path-literal hits in CORPUS-owned test files
  (`tests/corpus/test_seccl.py`, `tests/corpus/test_seccl_artifacts.py`);
  untouched by this Goal (same baseline class as documented in CORE/LEARNER
  Wave-2 handoffs).

## Resource hygiene

- Only the authorized L2 worktree was written; no other worktree, no raw
  SWECCL, no `app/database/`, `app/infrastructure/`, `app/services/`,
  `app/learner/`, `app/corpus/`, `app/revision/`, `main.py` or `wave2.py`
  touched.
- No reset/clean/rebase/push/PR/promotion. Pre-existing untracked evidence
  preserved (verified via `git status`).
- Leak scan over new code: no raw corpus paths, no API keys, no
  `app.corpus.routing` import in module source.
- Environment note: the worktree `.venv\pyvenv.cfg` pointed at a deleted
  interpreter home; repaired to the working `C:\Users\16073\.uv-python\...`
  3.12.13 home (backup kept at `pyvenv.cfg.pre-l2wave2.bak`; local
  environment state only, not repository content).

## Integration handoff notes

- `wave2_modules/` is a namespace package on this branch (no `__init__.py`);
  CORE contributes `wave2_modules/__init__.py` and the Wave-2 assembly
  (`app/api/routers/wave2.py`) at integration, as for LEARNER PDW2-B.
- The routers' default dependencies consume `app.state.submission_service`
  and `app.state.reanalysis` from the existing composition root; integration
  wiring replaces the branch-local in-memory repository with the CORE
  migration-14 repository implementing `RevisionLoopRepository`
  (writing_tasks / submission_revisions / learning_items semantics).
- CORPUS PDW2-E's real `app/corpus/routing.py` can replace the local
  `LocalWrittenCorpusRouter` at integration behind `CorpusRoutingProtocol`.
- Manifest refresh (module set + census parity) is an INT repair item.
