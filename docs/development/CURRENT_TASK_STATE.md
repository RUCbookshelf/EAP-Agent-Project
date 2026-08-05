**Date:** 2026-08-05
**Current task:** v0.9.7-B Work Unit 6 - Journey Integration Verification,
Final Product Matrix, and Release Closure
**Status:** COMPLETE - all 80 WU6 acceptance criteria satisfied; WU1-WU6
complete; **v0.9.7-B is complete, verified, and closed**; the next planned
phase is v0.9.7-C (NOT started; see RUN_VERIFICATION_V0.9.7_B_WU6.md and
RUN_VERIFICATION_V0.9.7_B.md).

- Journey: the existing read-time projection (app/journey/service.py) was
  verified for the complete priority-derived cycle - 12 event types with
  exact dedup keys; completion creates no event (status flows through
  `research_detail.status`); provenance/dedup/ordering deterministic;
  repeated reads, reloads, locale switches, Feedback/Revision re-entry,
  target reuse, and repeated completion never duplicate events; Journey
  reads perform no writes (whole-DB row counts); evaluation-unavailable
  and legacy records project honestly; no new Journey event types.
- Release gates: focused WU6 18 passed; combined WU2-WU6 197 passed;
  affected regression 569 passed / 0 failed; full non-live core 1057
  passed / 8 skipped / exit 0; `run.bat --verify` PASS twice; locale
  parity 572/572; Research smoke 6/6; fresh-index GitNexus impact review
  (0 production symbols changed); `git diff --check` clean.
- Matrix: EN/ZH x 1280x900/390x844 main cycles + evaluation-unavailable,
  no-priority, and legacy scenarios all PASS independently (fresh isolated
  DB + distinct learner each; 0 console/page errors; 0 remote requests;
  no overflow/raw keys; mobile controls >= 44px; no mastery wording).
- Metadata: WU5 closure roles reconciled in the WU5 report (`01115ba`
  functional/evidence HEAD; `b9e030d` closure HEAD); WU6 implementation
  baseline `b0f16b5` (protocol-freeze commit); no migration 14; no
  production code change in WU6.
- Next: v0.9.7-C (Student Journey Functional Completion). Do not begin
  v0.9.7-C in this stage.

**Date:** 2026-08-04
**Date:** 2026-08-05
**Date:** 2026-08-05
**Current task:** v0.9.7-B Work Unit 4 - Focused Practice Task and Attempt
Loop
**Status:** COMPLETE - all 36 WU4 acceptance criteria satisfied; WU5
(evaluation semantics + completion) is the next planned work unit;
v0.9.7-B as a whole is NOT complete (see RUN_VERIFICATION_V0.9.7_B_WU4.md).

- Explicit entry: Feedback per-priority "Practice this priority" actions and
  Revision completion Open Practice transfer only reference components;
  the Practice page resolves them server-side through WU3 create-or-reuse
  (no render-time fabrication; stale/cross-learner presets ignored).
- Focused task: learner-owned read-only context endpoint re-resolves the
  persisted priority context; one current exercise reused or created and
  seeded from the evidence quote; the task shows priority, why, direction,
  evidence, instruction, and response field.
- Attempt loop: server-side ownership validation (cross-student 403, zero
  writes), shared pending guard (one action -> at most one attempt), input
  preserved on failure, explicit saved state with attempt reference, and
  rerun/refresh/re-entry recovery from persistence. Evaluation unchanged;
  no COMPLETED status; no WU5 Finish/Continue actions.
- Verification: focused 32 passed; combined WU2-WU4 141 passed; affected
  regression 638 passed / 1 skipped; full non-live core 1000 passed /
  8 skipped / exit 0; `run.bat --verify` PASS; rendered matrix (en/zh x
  1280x900/390x844) PASS; locale parity 563/563.
- Next: v0.9.7-B WU5 (evaluation/completion semantics). Do not begin WU6 or
  v0.9.7-C in this stage.

**Date:** 2026-08-05
**Current task:** v0.9.7-B Work Unit 3 - Idempotent Priority Practice Target
Creation and Reuse
**Status:** COMPLETE - all 20 WU3 acceptance criteria satisfied; WU4 is the
next planned work unit; v0.9.7-B as a whole is NOT complete (see
RUN_VERIFICATION_V0.9.7_B_WU3.md).

- WU2 (mapping + provenance) is complete; WU3 consumed the frozen contract
  without redesigning it.
- WU3 implemented: prefix-length-safe `_next_practice_id` repair with
  BEGIN IMMEDIATE serialized allocation (FET/WTR/PSS no longer collide),
  `PracticeTargetCreationService` create-or-reuse on
  (student_id, source_submission_id, source_priority_id), migration 13
  (additive partial unique index on the persisted JSON priority key),
  unified ownership/evidence validation for priority-derived and legacy
  creation, and the `FeedbackEngagementTrace.created_at` schema fix.
- No Practice UI, answer submission, evaluation, completion, or Journey
  change; no WU4/WU5 functionality; locale parity preserved (555/555).
- Verification: focused 33 passed; affected regression 562 passed; full
  non-live core 969 passed / 8 skipped / exit 0; `run.bat --verify` PASS;
  demo smoke PASS (migration 13 + index).
- Next: v0.9.7-B WU4 (focused Practice task and attempt loop). Do not begin
  WU5-WU6 or v0.9.7-C in this stage.

**Date:** 2026-08-05
**Current task:** v0.9.7-B Work Unit 2 - Priority-to-Practice Mapping and
Provenance
**Status:** COMPLETE - all 24 WU2 acceptance criteria satisfied; WU3
(idempotent target creation and reuse) is the next planned work unit;
v0.9.7-B as a whole is NOT complete (see RUN_VERIFICATION_V0.9.7_B_WU2.md).

- WU1 (audit + protocol freeze) is complete: docs/development/
  V0.9.7_B_PRACTICE_WORKFLOW_AUDIT.md and V0.9.7_B_SPEC.md at HEAD `7fdf875`.
- WU2 implemented the production mapping + provenance contract: stable
  zero-based priority reference `PRIO-{feedback_id}-{priority_index}`,
  production category map (lexical_repetition -> lexical_repetition_local,
  connective_use -> connective_overuse, sentence_length_pattern ->
  long_sentence; demo script imports the production map), validated
  `PriorityTargetContract`, `source_priority_id`/`evidence_ids` forwarded
  through the API and persisted, and ownership/source validation before any
  priority-derived write (cross-student 403; missing source 404; malformed/
  stale/fabricated/unsupported/conflicting 422; zero writes on failure).
- No schema or migration change (evidence-based); no Student UI automatic
  target creation; no idempotency, completion, or Journey change; locale
  parity 555/555.
- Verification: focused 76 passed; affected regression 408 passed; full
  non-live core 936 passed / 8 skipped / exit 0 (one pre-existing readiness-
  gate timing flake documented in the report; clean on identical-env re-run);
  `run.bat --verify` PASS; demo smoke PASS on an isolated DB.
- Next: v0.9.7-B WU3 (idempotent target creation and reuse). Do not begin
  WU4-WU6 or v0.9.7-C in this stage.

**Date:** 2026-08-04
**Current task:** v0.9.7-A Priority-Guided Learning Cycle Completion
**Status:** COMPLETE - v0.9.7-A is closed; all 15 acceptance criteria
satisfied; closure HEAD `209a8a8` (five focused commits; see
RUN_VERIFICATION_V0.9.7_A.md and verification/v0.9.7-a/v0.9.7-a-20260804-r1/)

- The priority-guided revision cycle is complete: Feedback transfers the
  naturally generated priority into Revision (Open Revision primary action),
  Revision displays the active priority task from the persisted source
  feedback (with one-active-priority selection when several exist), the
  student submits one linked revision, and an explicit completion state
  provides the priority addressed, the record reference, and clear next
  steps (Finish This Revision Cycle -> Home; Open Practice with the accurate
  no-auto-target note; Open Learning Journey).
- Re-entry after refresh shows the completed state for a source that already
  has a revision (no blank form, no uncontrolled duplicate). UI + session
  state only: no migration/schema/API/domain/service/prompt change; locale
  parity 555/555.
- Verification: focused 14 passed; affected regression 293 passed; full
  non-live core 860 passed / 8 skipped / exit 0; `run.bat --verify` PASS;
  rendered-page matrix (all four locale/viewport combinations) PASS with
  0 console/page errors and 0 remote requests.
- Next: v0.9.7-B Practice Target Generation and Practice Workflow (not
  started). Do not begin v0.9.7-B or later stages in this phase.
**Date:** 2026-08-04
**Current task:** v0.9.6-D0-R Frozen Priority Path Production Validity Audit
**Status:** COMPLETE - primary classification D0-R-C (downstream capability
incomplete but non-blocking); v0.9.6 stabilization CLOSED (see
RUN_VERIFICATION_V0.9.6_D0_R.md and verification/v0.9.6-d0-r/)

- Resumed from the original D0 stop point with the repaired real DeepSeek
  provider: all five frozen corpus essays submitted through the normal
  production path on a fresh isolated audit database plus two byte-identical
  repeats (7 submissions / 7 provider attempts, budget 9/12).
- Live provider 7/7 successes, 0 corrections, 0 fallback, 0 timeout, 0
  truncation, finish_reason=stop on every call. D0-01/D0-04 selected
  lexical_repetition D001; D0-02 selected connective_use D001; D0-03
  preregistered no-priority probe met; D0-05 legitimate no-priority control.
- Evidence integrity 3/3 source-faithful, 0 fabricated, 0 semantic mismatch;
  repeatability STABLE (byte-identical evidence quotes); Feedback/Home
  CONSUMABLE; Revision and Practice PARTIALLY_CONSUMABLE with accurate
  state reporting (no automatic practice-target creation - v0.9.7-B item).
- Targeted verification 131 passed, exit 0; full core not rerun (824/8/0/0
  preserved); launcher not rerun; dev DB byte-identical (F78A6CEA...);
  exports 776/388 zero delta.
- Next: v0.9.7-A Priority-Guided Learning Cycle Completion (approved
  planning stage; not started). Do not create additional v0.9.6
  stabilization stages for non-blocking findings.
**Date:** 2026-08-04
**Current task:** v0.9.6-DP0-V2 Verification Safety Incident Closure
**Status:** COMPLETE - incident closed; launcher verification isolation
hardened; v0.9.6-DP0 formally and finally closed (see
RUN_VERIFICATION_V0.9.6_DP0.md V2 section and verification/v0.9.6-dp0-v2/)

- Incident: the invalid first launcher attempt (DATABASE_PATH-only, no
  process DATABASE_URL; .env supplies DATABASE_URL=sqlite:///data/
  writing_feedback.db) changed the development-database byte fingerprint
  62615C6C... -> F78A6CEA...; read-only audit proved only the routine
  system_versions.recorded_at refresh changed (integrity ok, 0 FK
  violations, migration 12, 33 tables, config-v0.9.0 active, all
  user/domain counts consistent). Classification V2-DB-A; current database
  retained and adopted as the new baseline; no backup restored.
- Guard: run.bat --verify delegates to scripts/verify_launcher.py before
  any migration/API startup; explicit unsafe DATABASE_URL refuses before
  startup; no DATABASE_URL auto-provisions a fresh temporary database
  (removed after verification); DATABASE_PATH-only can never fall back to
  the development database; normal non-verify behavior unchanged.
- Verification: guard tests 22 passed; database/migration/config contract
  tests 31 passed; negative DATABASE_PATH-only probe safely auto-isolated;
  exact cmd /c "run.bat --verify" PASS exit 0 (auto-provisioned temp DB,
  200/200/200, migration 12, 33 tables, config-v0.9.0,
  feedback-prompt-v0.7.1); full core NOT rerun (accepted 824/8/0/0
  preserved); no live provider call; exports 776/388 zero delta.
- Next: v0.9.6-D0-R resume the frozen priority path audit (separately
  approved). v0.9.6-D1 not started.
# Current Task State
**Date:** 2026-08-04
**Current task:** v0.9.6-DP0-V1 Full-Core Verification Closure
**Status:** COMPLETE - formal DP0 regression closure achieved (see RUN_VERIFICATION_V0.9.6_DP0.md closure section and verification/v0.9.6-dp0-v1/)

- The prior DP0 full-core run (821 passed/8 skipped/2 failed/1 error, exit 1)
  was not accepted; failures classified: parity test without the documented
  SERVICE_API_DIFF_ALLOWLIST env, documented router-contract lifecycle
  flake, transient Chromium launch timeout - each passes in isolation.
- Canonical environment frozen from the source-authoritative runner
  (v0.9.5-h2a): LLM_PROVIDER=local, fresh DATABASE_PATH, 26-entry
  G_ALLOWLIST unchanged.
- Final full non-live core (exactly once): 824 passed, 8 skipped, 0 failed,
  0 errors, exit 0. Launcher PASS exit 0 (isolated DB, 200/200/200).
- Safety: exports 776/388 restored; dev DB byte fingerprint changed during
  the invalid first launcher attempt (62615C6C... -> F78A6CEA...; only the
  routine system_versions.recorded_at refresh detected; closed in
  v0.9.6-DP0-V2 with the current database adopted as the new baseline).
- v0.9.6-DP0 formally closed. Next: owner decision for v0.9.6-D0-R (resume
  the frozen priority path audit). v0.9.6-D1 not started.

**Date:** 2026-08-04
**Current task:** v0.9.6-DP0 Production Provider Reliability
**Status:** COMPLETE - DP0-A diagnosis owner-accepted; DP0-B repair and
verification closed (see RUN_VERIFICATION_V0.9.6_DP0.md and
docs/development/V0.9.6_DP0_PROVIDER_RELIABILITY.md)

- Root cause (proven): deepseek-v4-pro defaults to thinking mode; the
  request omitted the toggle; reasoning consumed 72% of the 1800-token
  output budget, truncating JSON (inish_reason=length) and timing out
  the correction attempt at 30s; LocalDemo fallback followed.
- Fix (owner-approved change set): 	hinking={"type":"disabled"} on the
  structured-feedback path; sanitized provider metadata capture; explicit
  provider_output_truncated / provider_json_invalid classifications.
  Timeout kept at 30s; model, prompt, schema, gate, max tokens, fallback,
  and the 180s client timeout unchanged.
- Live: 4 consecutive normal production submissions (frozen D0-01/D0-02/
  D0-05) - deepseek/deepseek-v4-pro, finish_reason=stop, 0 corrections,
  0 fallback, 0 timeout, 0 truncation; max provider call 21.7s.
- Verification: 101 + 103 + 24 focused/regression passed; full core single
  attempt 821 passed, 8 skipped (3 anomalies isolated-classified, none
  DP0-B-related, not rerun per protocol); 
un.bat --verify PASS.
- Safety: development database unchanged; research exports 776/388; call
  budget 6 of 12 attempts used; D0 workspace preserved.
- Next: owner decision gate on the DP0-B report; recommended next stage
  v0.9.6-D0-R (resume the frozen priority path audit). v0.9.6-D1 not started.

**Date:** 2026-08-04
**Current task:** v0.9.6-D0 Priority Path Production Validity Audit
**Status:** BLOCKED at the live-provider preflight (classification D0-E); audit-only, no production code changed (see RUN_VERIFICATION_V0.9.6_D0.md and BLOCKER_REPORT_V0.9.6_D0.md)

- The configured real provider (DeepSeek deepseek-v4-pro) failed the
  bounded preflight: both approved attempts returned truncated JSON on
  attempt 0 and timed out at the frozen 30 s transport timeout on the
  correction attempt; both fell back to LocalDemo. Fallback is not counted
  as live-provider success.
- The non-provider production pipeline worked under the isolated audit
  database: spacy-analyzer-v0.8.0, 24 metric results, Diagnostic Gate
  selected lexical_repetition (D001, 0.6649, verified) on both attempts.
- Protocol and corpus were preregistered and frozen before any live
  submission (five newly authored synthetic essays, four issue-targeted +
  one control).
- Targeted verification: 155 passed, 0 failed, 0 errors, exit 0.
  Development database unchanged (hash/size/mtime); research exports
  unchanged (776/388, zero delta); no production source changed.
- Primary classification: D0-E. Recommended next stage (separately
  approved): v0.9.6-DP0 Production Provider Reliability. Do not begin
  v0.9.6-D1 or any priority-generation/downstream repair stage.
- Next: owner decision gate at the blocker report.




**Date:** 2026-08-04
**Current task:** v0.9.6-C No-Priority Workflow Completion and Sidebar
Control Repair
**Status:** completed and fully verified - C1 and C2 were manually accepted
by the owner; C3 ran the combined closure (see
`RUN_VERIFICATION_V0.9.6_C.md`)

- C1 incident (Submission #28, learner S02): no-priority Feedback was a
  dead end; the loop cause was stale Writing-submitted session state with
  no terminal action, no Feedback actions, and no Home acknowledgement
  for a finished cycle. Fix: `Revise This Draft` / `Finish This Feedback
  Cycle` actions, session acknowledgement for the exact submission, fresh
  `1 Write` Home/Writing state, actionable Revision/Practice no-priority
  states, neutral passage section (no unsupported Strength), 12 new
  locale keys (540/540).
- C2: the pixel-art base typography rule overrode Streamlit native
  `stIconMaterial` spans (sidebar arrows and the Writing-page Genre
  expander chevrons); fixed with a common exclusion plus visible-before-
  hover pinning of the two native sidebar controls. Browser-verified in
  all states and viewports.
- Verification: C1 focused 20 passed; C2 focused 29 passed; student-page
  suites 52 passed, 3 skipped; A/B reliability 51 passed; UI client/
  locale contracts 36 passed; full non-live core 809 passed, 8 skipped,
  exit 0; `run.bat --verify` PASS; API 77 pairs unchanged; Database
  public methods 2; client 53; development database unchanged; research
  exports restored to 776/388.
- Next: continue v0.9.6 user-visible feature development under a new
  owner-authorized goal.


**Date:** 2026-08-03
**Current task:** v0.9.6-B First Draft and Unified Submission Reliability
**Status:** completed and fully verified (see `RUN_VERIFICATION_V0.9.6_B.md`)

- Incident classified C by read-only database inspection: first draft
  essay 27 completed after the UI timeout (30.46 s provider call); no
  duplicate first draft in the incident; duplicate risk reproduced
  deterministically.
- Fix: `submit()` and `submit_linked_revision()` share the private
  `_submit_long_running` transport (LONG_SUBMIT_TIMEOUTS, one POST, no
  retry); shared UI reliability helper; writing-page pending guard and
  bounded read-only exact reconciliation; accurate en/zh messages
  (parity 528/528); linked-revision behavior preserved.
- Verification: focused 30 + 21 passed; relevant regression 242 passed,
  3 skipped; full non-live core 760 passed, 8 skipped, exit 0;
  `run.bat --verify` PASS; API 77 pairs unchanged; Database public
  methods 2; client 53; development database unchanged; research
  exports restored to 776/388.
- Next: continue v0.9.6 user-visible feature development.



**Date:** 2026-08-03
**Current task:** v0.9.6-A Linked Revision Submission Reliability
**Status:** completed and fully verified (see `RUN_VERIFICATION_V0.9.6_A.md`)

- Incident classified C by read-only database inspection: the timed-out
  linked revision was durably completed server-side after the UI timeout;
  a byte-identical duplicate pair showed the double-POST mechanism.
- Fix: dedicated 180 s timeout for the linked-revision submit path only;
  pending-state submit guard; no automatic POST retry; bounded read-only
  reconciliation through existing GET APIs (CONFIRMED_SUCCESS /
  STILL_PROCESSING / UNCONFIRMED); accurate en/zh messages; locale parity
  524/524.
- Verification: focused 21 passed; relevant suite 212 passed, 3 skipped;
  full non-live core 730 passed, 8 skipped, exit 0; `run.bat --verify`
  PASS; API 77 pairs unchanged; Database public methods 2; development
  database unchanged; research exports restored to 776/388.
- Next: continue v0.9.6 user-visible feature development.



**Date:** 2026-08-03
**Current task:** v0.9.5-H2E Architecture Freeze
**Status:** completed - v0.9.5 architecture optimization is COMPLETE and
frozen; repository ready for v0.9.6 user-visible feature development (see
`docs/development/V0.9.5_H2E_ARCHITECTURE_FREEZE.md`)

- Documentation and evidence only: final architecture inventory captured
  (`verification/v0.9.5-h2e/architecture_freeze.json`), freeze document
  created, project-state documents updated; no test executed during H2E;
  no production/test file changed.
- Frozen state: Database 2; API 77 (73 explicit OpenAPI pairs + 4
  auto-HEAD GET entries); client 52; locale 520/520; migration 12; tables
  33; `config-v0.9.0`; `feedback-prompt-v0.7.1`; contracts 41/41/0;
  Protocol 41; runtime-checkable 36; API Ports 10/10/0; ConfigurationPort
  Protocol; AnalysisRunReader definitions 1.
- H1-H2E all COMPLETE. Next stage: v0.9.6 feature development.



**Date:** 2026-08-03
**Current task:** v0.9.5-H2D2-V1 Full-Core Verification Closure
**Status:** completed - v0.9.5-H2D2 is COMPLETE and fully verified (one fresh
full non-live core run: exit code 0, 709 passed, 8 skipped, 2 warnings, zero
failures/errors; see `RUN_VERIFICATION_V0.9.5_H2D2_V1.md`)

- Exactly one full-core run on a fresh isolated database
  (`C:\Users\16073\AppData\Local\Temp\v095h2a-g__xwr8r\h2a.db`), exact
  command `pytest -q -p no:cacheprovider --ignore=tests/live tests`: exit
  code 0, zero failures, zero errors; 709 passed, 8 skipped, 2 warnings.
- Research-export baseline restored exactly (8 run-generated dirs / 16 files
  removed via the exact guard allowlist; 776 files / 388 dirs, all retained
  paths and hashes unchanged); development database unchanged
  (SHA-256/size/mtime); ports 8000/8501 free; no production/test change.
- Next: H2E (architecture freeze) in the same authorized goal, pending this
  closure commit.



**Date:** 2026-08-03
**Current task:** v0.9.5-H2D2 Bind API Ports to Production Dependency Accessors
**Status:** implementation and focused verification complete; final full-core closure pending (see `RUN_VERIFICATION_V0.9.5_H2D2.md`)

- Bound the ten v0.9.5-G API-owned Ports as exact production return
  annotations on the ten matching `app/api/deps.py` accessors (type-only);
  all annotations resolve at runtime; all ten facade-owned repositories
  structurally satisfy their Ports; accessor bodies, Routers, `Depends(...)`,
  app-state, composition, Port definitions, OpenAPI, and dependency graph
  unchanged.
- Focused contract suite 243 passed, 2 warnings; OpenAPI/dependency-graph
  parity 0 differences; exact `run.bat --verify` PASS; contract counts frozen
  (41/41/0; Protocol 41; runtime-checkable 36); API Ports with production
  references 0 -> 10.
- Full non-live core: **NOT CLEAN** - one fresh run exited 1 with
  `test_v095b_router_contract.py::test_live_and_ready_unchanged` (documented
  pre-existing lifecycle-race flake; passes in isolation 1 passed/2.03s);
  708 passed, 8 skipped otherwise. Per stage spec the full-core is not called
  clean; final verification pending.
- Research-export baseline restored to 776 files / 388 dirs after every
  write-capable layer; development database unchanged.
- Next: H2E (contract freeze) under separate authorization.



**Date:** 2026-08-03
**Current task:** v0.9.5-H2D1-V1 Research Export Verification Cleanup Closure
**Status:** completed - v0.9.5-H2D1 is COMPLETE and fully verified; research-export verification side effects CLEANED; approved pre-H2D1 export baseline restored (see `RUN_VERIFICATION_V0.9.5_H2D1.md`)

- Identified with exact ownership evidence (content signature, fixture match,
  git-commit-anchored verification window, complete-delta accounting) the 11
  export directories / 22 files (22,943 bytes) generated by the H2D1 focused
  and full-core suites through the pre-existing research-export tests.
- Removed only that exact allowlisted set (dry run PASS; every candidate
  re-verified before deletion); `research_exports/` restored from 798 to 776
  files; 1,164 retained entries path- and hash-identical; root preserved;
  zero unexpected deletions; no pre-existing export modified or deleted.
- No production/test change; no tests rerun; no application process started;
  ports 8000/8501 free; development database unchanged.
- Evidence: `verification/v0.9.5-h2d1/export_cleanup_*.json` and
  `cleanup_research_exports.py`.
- Next: H2D2 and H2E each under separate authorization.



**Date:** 2026-08-03
**Current task:** v0.9.5-H2D1 Formalize ConfigurationPort as a Structural Protocol
**Status:** completed and fully verified (full-core exit 0; see `RUN_VERIFICATION_V0.9.5_H2D1.md`)

- Formalized the active `ConfigurationPort` contract
  (`app/services/configuration.py`) from a plain structural class to a
  structural `typing.Protocol` (same name/module; seven methods preserved;
  not `@runtime_checkable`; no alias; no instantiation/subclass/runtime-check
  dependency).
- Focused contract suite 230 passed, 2 warnings; exact `run.bat --verify`
  PASS (migration 12, 33 tables, `config-v0.9.0`, prompt
  `feedback-prompt-v0.7.1`, health/docs/Streamlit 200); Database public
  methods 2, API 77, client 52, locale 520/520; development database
  unchanged.
- Full non-live core: one fresh run, exit code 0, **696 passed, 8 skipped,
  2 warnings** (683 H2C baseline + 13 new H2D1 tests); zero failed, zero
  errors; the documented `test_v095b_router_contract` lifecycle-race flake
  did not occur.
- Next: H2D2 and H2E each under separate authorization.



**Date:** 2026-08-03
**Current task:** v0.9.5-H2C Canonicalize Duplicate `_AnalysisRunReader` Infrastructure Contract
**Status:** completed and fully verified (full-core exit 0; see `RUN_VERIFICATION_V0.9.5_H2C.md`)

- Canonicalized the exact duplicate infrastructure reader pair
  `_AnalysisRunReader` (revision.py:14, learner.py:12) into one shared
  `AnalysisRunReader` Protocol in
  `app/infrastructure/sqlite/repositories/contracts.py`; both consumers use
  it for the existing `analysis_reader` annotation only; both former local
  definitions removed; no alias; `_AnalysisRunReader` absent from `app/**`;
  H2A/H2B diffs and all other active contracts intact.
- Focused contract suite 217 passed, 2 warnings; exact `run.bat --verify`
  PASS (migration 12, 33 tables, `config-v0.9.0`, prompt
  `feedback-prompt-v0.7.1`, health/docs/Streamlit 200); Database public
  methods 2, API 77, client 52, locale 520/520; development database
  unchanged.
- Full non-live core: one fresh run, exit code 0, **683 passed, 8 skipped,
  2 warnings** (669 H2B baseline + 14 new H2C tests); zero failed, zero
  errors; the documented `test_v095b_router_contract` lifecycle-race flake
  did not occur.
- Next: H2D and H2E each under separate authorization.



**Date:** 2026-08-03
**Current task:** v0.9.5-H2B Rename Active Configuration Repository Contract
**Status:** completed and fully verified (full-core closure exit 0; see `RUN_VERIFICATION_V0.9.5_H2B.md`)

- Renamed the active local configuration contract `ConfigurationRepository`
  to `ConfigurationPort` (consumer-owned boundary; naming-only). Seven
  methods preserved exactly; `SQLiteConfigurationRepository` still satisfies
  it; no alias/duplicate; old name absent from `app/**`; H2A removal diff and
  all 42 active contracts intact.
- Focused contract suite 203 passed, 2 warnings; exact `run.bat --verify`
  PASS (migration 12, 33 tables, `config-v0.9.0`, prompt
  `feedback-prompt-v0.7.1`, health/docs/Streamlit 200); Database public
  methods 2, API 77, client 52, locale 520/520; development database
  unchanged.
- Full non-live core: closure run (v0.9.5-H2B-V1) exit code 0, **669
  passed, 8 skipped, 2 warnings** (the two prior attempts each failed once
  on the documented pre-existing `test_v095b_router_contract`
  lifecycle-race flake, which passes in isolation and in the closure run);
  full-core regression PASS.
- Next: H2C-H2E each under separate authorization.


**Status:** completed and fully verified (full-core closure exit 0; see `RUN_VERIFICATION_V0.9.5_H2A.md`)

- Removed exactly the 13 H1-approved unused contracts: legacy
  `SubmissionRepository`, 11 stale central Protocols, and the
  `SubmissionRepositories` alias; obsolete imports, bases, docstrings,
  re-exports, and `__all__` entries removed; `app/repositories` now exports
  only `RevisionRepository`; zero replacement contracts; total
  persistence-related contracts 55 -> 42, active persistence contracts
  42 -> 42, unused legacy contracts 13 -> 0 (H1 artifacts remain
  historical evidence).
- No active contract, Repository implementation, Service constructor, Router
  dependency, composition path, SQL, transaction, API, schema, provider,
  prompt, UI, or localization change; local 7-method `ConfigurationRepository`
  unchanged (collision resolved via stale central removal).
- Focused contract suite 197 passed, 2 warnings; full non-live core 663
  passed + 8 skipped, 2 warnings, exit code 0 (closure run; the original H2A
  full-core run exited 1 on the documented pre-existing
  `test_v095b_router_contract` lifecycle-race flake, which passes in
  isolation and in the closure run); exact `run.bat --verify` PASS
  (migration 12, 33 tables, `config-v0.9.0`, prompt
  `feedback-prompt-v0.7.1`, health/docs/Streamlit 200); Database public
  methods 2, API 77, client 52, locale 520/520; development database
  unchanged.
- Next: H2B-H2E each require separate authorization; H2B (rename active
  local `ConfigurationRepository`) is the next candidate.

**Date:** 2026-08-03
**Current task:** v0.9.5-H1 Persistence Protocol Inventory and Consolidation Plan
**Status:** completed (read-only audit; see `docs/development/PROTOCOL_CONSOLIDATION_AUDIT_V0.9.5_H1.md`)

- Inventoried 55 persistence-related contracts at HEAD `fc2e8e9` (52
  Protocols, `SubmissionRepositories` union alias, local plain-class
  `ConfigurationRepository`, legacy combined-class `SubmissionRepository`);
  A=37, B=1, C=4, G=13; active=42, unused candidates=13; 3 same-name
  collisions; 29 methods with >1 declaration; method-level overlap matrix,
  consumer matrix, and 5-unit H2 plan produced as JSON artifacts under
  `verification/v0.9.5-h1/`.
- Legacy `SubmissionRepository` confirmed removable without replacement
  (zero production consumers); central `ConfigurationRepository`
  (ping/migration_version) confirmed stale with the local 7-method contract
  authoritative for `ConfigurationService`; API-owned Ports exact but
  test-referenced only; Practice read/write separation intentional;
  `_AnalysisRunReader` exact infra duplicate pair.
- Focused F2-F6D+G contract tests: 187 passed, 2 warnings (isolated
  temporary database; `SERVICE_API_DIFF_ALLOWLIST` G-era value); development
  database unchanged (SHA-256/size/mtime); no production or test file
  modified.
- Next: recommended H2A (remove 13 unused legacy contracts) may begin only
  under separate authorization.

**Date:** 2026-08-03
**Current task:** v0.9.5-G Database Facade Contraction
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_G.md`)

- The `Database` public surface is `connect` and `initialize`; the 84 removed
  business-delegation methods are in the exact G removal ledger with
  replacement paths; the `SQLiteRepository` alias is removed; one connection
  manager and one Repository graph remain.
- Zero production Router uses `Depends(get_repository)`; ten API-owned Ports
  compose facade-owned Repositories on app state; `require_student` uses
  `StudentLookupPort`; FeedbackPipeline, scripts, and tests use facade-owned
  aggregate Repositories; no Repository implementation, SQL, or transaction
  boundary changed.
- Focused 437 PASS; full core 653 passed + 8 skipped; exact `run.bat
  --verify` PASS; migration 12, 33 tables, `config-v0.9.0`, prompt
  `feedback-prompt-v0.7.1`, API 77, client 52, locale 520/520, Database public
  methods 2; development database unchanged.
- Next: no further stage without separate authorization.

**Date:** 2026-08-02
**Current task:** v0.9.5-F6D Practice Write-Boundary Narrowing
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_F6D.md`)

- The Practice Router now depends on `PracticeSubmissionReadPort`,
  `PracticeReadPort`, `PracticeWritePort`, the preserved `require_student`
  guard, and the pure `PracticeService()`; no `Depends(get_repository)`
  remains in the Router; `PracticeService` has no persistence dependency or
  field.
- Both app paths compose facade-owned Submission/Practice repositories and
  the pure Service on `app.state`; five narrow dependency accessors added;
  Attempt-first/Evaluation-best-effort semantics, all eight Practice
  endpoints, schemas, status codes, and error behavior are unchanged.
- Focused 187 PASS; accumulated contracts 253 PASS; full core 638 passed +
  8 skipped; exact `run.bat --verify` PASS; migration 12, 33 tables,
  `config-v0.9.0`, prompt `feedback-prompt-v0.7.1`, facade 86, API 77,
  client 52, locale 520/520 unchanged; development database unchanged.
- Next: v0.9.5-G Database facade contraction only under separate
  authorization.

**Date:** 2026-08-02
**Current task:** v0.9.5-F6C SubmissionService Persistence Dependency Narrowing
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_F6C.md`)

- `SubmissionService` now depends on `SubmissionSystemPort`,
  `SubmissionDataPort`, `SubmissionAnalysisPort`, `SubmissionCalibrationPort`
  and the existing non-persistence collaborators; no broad or untyped
  persistence dependency remains; both CALF `hasattr` guards removed; legacy
  `SubmissionRepository` retained only as Protocol-consolidation debt.
- `build_submission_service` takes seven required keyword-only facade-owned
  repositories; both app paths, FeedbackPipeline, and all active callers pass
  the existing facade-owned instances (same connection manager, one graph);
  constructor `record_versions`, submit and regenerate-feedback order, write
  counts, and partial-commit behavior are preserved.
- Focused 282 PASS; accumulated contracts 233 PASS; full core 618 passed +
  8 skipped; exact `run.bat --verify` PASS; migration 12, 33 tables,
  `config-v0.9.0`, prompt `feedback-prompt-v0.7.1`, facade 86, API 77,
  client 52, locale 520/520 unchanged; development database unchanged.
- Next: v0.9.5-F6D Practice write-boundary work only under separate
  authorization.

**Date:** 2026-08-02
**Current task:** v0.9.5-F6B AdminReanalysisService Persistence Dependency Narrowing
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_F6B.md`)

- `AdminReanalysisService` now depends on `AdminConfigurationReadPort`,
  `AdminSubmissionReadPort`, `AdminAnalysisPort`, the unchanged central
  `RevisionRepository`, and the existing settings/Service collaborators; no
  broad or untyped persistence dependency remains.
- All six direct calls route to approved owners; both app paths use the
  existing facade-owned repositories (same connection manager, one graph);
  `configurations.active()`, `submission_service.regenerate_feedback`, and
  the embedded `RevisionService` are unchanged; preview is zero-write;
  Analysis save count/order, feedback conditions, and partial-commit
  behavior are preserved.
- Focused 154 PASS; accumulated contracts 204 PASS; full core 589 passed +
  8 skipped; exact `run.bat --verify` PASS; migration 12, 33 tables,
  `config-v0.9.0`, prompt `feedback-prompt-v0.7.1`, facade 86, API 77,
  client 52, locale 520/520 unchanged; development database unchanged.
- Next: v0.9.5-F6C SubmissionService narrowing only under separate
  authorization.

**Date:** 2026-08-02
**Current task:** v0.9.5-F6A RevisionService Runtime Repository Narrowing
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_F6A.md`)

- Every active `RevisionService` receives the existing facade-owned
  `SQLiteRevisionRepository` (both app paths, Submission factory, Admin
  Reanalysis embedded composition, FeedbackPipeline, operational callers);
  no broad facade runtime remains; no new Port, fallback, proxy, or shared
  transaction; the central `RevisionRepository`, Revision writes, SQL, and
  the three-sequential-commit workflow are unchanged; F6A0 remains the
  completed capability prerequisite.
- Focused 155 PASS; accumulated contracts 188 PASS; full core 573 passed +
  8 skipped; exact `run.bat --verify` PASS; migration 12, 33 tables,
  `config-v0.9.0`, prompt `feedback-prompt-v0.7.1`, facade 86, API 77,
  client 52, locale 520/520 unchanged; development database unchanged.
- Next: v0.9.5-F6B and later stages only under separate authorization.

**Date:** 2026-08-02
**Current task:** v0.9.5-F6A0 Revision Repository Capability Completion
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_F6A0.md`)

- `SQLiteRevisionRepository` exposes `get_submission_bundle` and
  `get_latest_analysis_run` as direct delegations; the facade wires the
  existing Submission and Analysis repository instances into it (one
  connection manager, one graph). Central `RevisionRepository`,
  `RevisionService`, all construction sites, Revision writes, SQL, and
  transactions unchanged; no F6A runtime narrowing performed.
- Focused 53 PASS; accumulated contracts 161 PASS; full core 559 passed +
  8 skipped; exact `run.bat --verify` PASS; migration 12, 33 tables,
  `config-v0.9.0`, prompt `feedback-prompt-v0.7.1`, facade 86, API 77,
  client 52, locale 520/520 unchanged; development database unchanged.
- Next: v0.9.5-F6A runtime narrowing only after a separate rebaseline and
  authorization.

**Date:** 2026-08-02
**Current task:** v0.9.5-F5B ResearchDataService Dependency Narrowing
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_F5B.md`)

- `ResearchDataService` narrowed to three explicit consumer-owned Ports
  (`ResearchSubmissionReadPort`, `ResearchReviewPort`,
  `ResearchExportReadPort`); all six `hasattr` capability checks removed;
  both app paths compose it from the existing facade-owned Submission and
  Research repositories (same Research instance for both Research Ports);
  the five Research test sites and the one verification-helper site
  received constructor-only updates.
- Router-level best-effort `save_export_job` persistence unchanged and
  outside the Service.
- Focused 97 PASS; contract inventory 141 PASS; full core 546 passed + 8
  skipped; exact `run.bat --verify` PASS; migration 12, 33 tables,
  `config-v0.9.0`, prompt `feedback-prompt-v0.7.1`, facade 86, API 77,
  client 52, locale 520/520 unchanged; development database unchanged;
  235 pre-existing user exports untouched.
- Next: any later stage only under a separate authorization.

**Date:** 2026-08-02
**Current task:** v0.9.5-F5A CALF Service Dependency Narrowing
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_F5A.md`)

- `CalfService` narrowed to four explicit consumer-owned Ports
  (`CalfDataPort`, `CalfSubmissionReadPort`, `CalfAnalysisReadPort`,
  `CalfStudentReadPort`); both app paths compose it from the existing
  facade-owned CALF/Submission/Analysis/Learner repositories; the one
  operational-script caller received a constructor-only update.
- Focused 63 PASS; contract inventory 123 PASS; full core 526 passed + 8
  skipped; exact `run.bat --verify` PASS; migration 12, 33 tables,
  `config-v0.9.0`, facade 86, API 77, client 52, locale 520/520
  unchanged; development database unchanged.
- Next: v0.9.5-F5B only under a separate authorization.

**Date:** 2026-08-02
**Current task:** v0.9.5-F4 Reanalysis and Journey Dependency Narrowing
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_F4.md`)

- Two Services narrowed: `ReanalysisService` (`SubmissionBundleReadPort`
  + `AnalysisRunWritePort`) and `JourneyService`
  (`JourneyStudentReadPort` + eight-method `JourneyProjectionReadPort`).
- Both app paths compose the Services from the existing facade-owned
  Submission/Analysis/Learner/Practice repositories; JourneyService is
  stored on app state and the Journey router consumes
  `get_journey_service`; the two `scripts/demo_journey.py` construction
  sites are the owner-authorized operational-script exception.
- Focused 118 PASS; contract inventory 84 PASS; full core 508 passed + 8
  skipped; exact `run.bat --verify` PASS; migration 12, 33 tables,
  `config-v0.9.0`, facade 86, API 77, client 52, locale 520/520
  unchanged; development database unchanged.
- Next: v0.9.5-F5 only under a separate authorization.

**Date:** 2026-08-02
**Current task:** v0.9.5-F3 Learner Read-Model Dependency Narrowing
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_F3.md`)

- Three Services narrowed: `ProgressService` (`LearnerProgressPort` +
  `ActiveConfigurationPort`), `LearnerProfileService` (`LearnerProfileReadPort`
  + injected `ProgressService`), and `DashboardService` (`DashboardReadPort` +
  injected `ProgressService`). The inactive `list_longitudinal_records`
  fallback and relevant `hasattr` branches were removed only from
  `ProgressService`.
- Both application paths and `build_submission_service` supply the
  facade-owned extracted Learner/Configuration repositories; the legacy
  `FeedbackPipeline` received the one authorized composition exception.
- Focused 96 PASS; contract inventory 36 PASS; full core 492 passed + 8
  skipped; exact `run.bat --verify` PASS; migration 12, 33 tables,
  `config-v0.9.0`, facade 86, API 77, client 52, locale 520/520 unchanged;
  development database unchanged.
- Next: v0.9.5-F4 only under a separate authorization.

**Date:** 2026-08-02
**Current task:** v0.9.5-F2 Low-Risk Service Repository Dependency Narrowing
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_F2.md`)

- Exactly two Service dependencies narrowed: `ConfigurationService` receives
  the existing `SQLiteConfigurationRepository` instance in both
  application-construction paths; `LearnerHistoryService` declares the
  one-method `PriorRecordsPort` with an unchanged runtime object.
- `DashboardService`, `ProgressService`, `LearnerProfileService`, and all other
  Services, repositories, facade surface, SQL, transactions, migration 12,
  `config-v0.9.0`, API (77), client (52), and locale (520/520) contracts
  unchanged.
- 53 focused tests PASS; full non-live core 480 passed + 8 skipped; exact
  `run.bat --verify` PASS; development database unchanged.
- Next: v0.9.5-F3 only under a separate authorization.

**Date:** 2026-08-02
**Current task:** v0.9.5-E SQLite Repository Modularization (Facade-first)
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_E.md`)

- Explicit 86-method `Database` facade and `SQLiteRepository` alias retained.
- One shared SQLite connection manager and nine aggregate repositories own all
  persistence methods; all 33 tables have one documented implementation owner.
- SQL/schema/signature/transaction/return-shape parity preserved; migration 12
  and active configuration `config-v0.9.0` unchanged.
- Hardened focused suite 175 passed; runtime/restart smoke PASS; full regression
  469 passed + 8 skipped; exact `run.bat --verify` PASS.
- All accepted write-capable evidence used fresh guarded temporary databases;
  the earlier development-database incident and dotenv isolation hardening are
  disclosed in the verification report.
- Service Dependency Narrowing, facade contraction, schema cleanup, Migration
  13, UI/API/domain changes, and historical-data compatibility remain deferred.
- Next: Service Dependency Narrowing only under a separate authorization.

**Date:** 2026-08-02
**Current task:** v0.9.5-D Frontend Contract Hardening and API Client Port Isolation
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_D.md`)

- Twelve narrow feature API Ports (`app/ui/ports/`); features typed only
  against their Port; `WritingFeedbackApiClient` remains the sole concrete
  client with unchanged method bodies.
- Approved endpoint/client/feature contract (77 endpoints, 52 client methods)
  under `tests/contracts/` with AST enforcement; unwrapped/unused surfaces
  documented.
- Practice and Research UI contracts parity-tested; facade private-helper
  test imports migrated; compatibility exports retained and deprecated.
- 19 new tests; focused frontend 220+3; 4/4 renders; 465+8 core;
  `run.bat --verify` PASS; dev DB unchanged; locale 520/520.
- Next: v0.9.5-E (not started) under a separate goal.
**Date:** 2026-08-02
**Current task:** v0.9.5-C Frontend Feature Extraction and UI Boundary Restoration
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_C.md`)

- Twelve feature modules (six Student, six Research) under `app/ui/features/`;
  old page modules reduced to thin re-export facades; renderer names,
  signatures, page order, session/widget keys, and locale keys unchanged.
- Practice and Research Data backend-schema imports removed via
  `app/ui/contracts/`; prohibited-import static test added.
- Inventory parity 13/13, 32/32, 24/24, 7/7, 6/6, 32/32, 98/98; 24/24
  browser renders; 446+8 core; `run.bat --verify` PASS; dev DB unchanged.
- Next: v0.9.5-D (not started) under a separate goal.
**Date:** 2026-08-02
**Current task:** v0.9.5-B API Router Decomposition and Health Contract Reconciliation
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.5_B.md`)

- Feature routers under `app/api/routers/`; `app/api/main.py` reduced to a
  composition root; one canonical lifecycle-based `/api/v1/system/health`;
  unreachable duplicate lifecycle-route code removed.
- Route parity 77/77; operation IDs and response models unchanged; 274+3
  focused API tests; 431+8 core tests; runtime smoke PASS; `run.bat --verify` PASS.
- No schema, service, repository, database, UI, or API-client change. Next:
  v0.9.5-C (not started) under a separate goal.



**Date:** 2026-08-01
**Current task:** v0.9.4-B Student Experience Redesign
**Status:** completed and verified (see `RUN_VERIFICATION_V0.9.4_B.md`)

- Home, Writing, Feedback, Practice, Revision, and Learning Journey redesigned
  on Hybrid Pixel System 2.0 with shared purpose/context/steps/action structure.
- Locale parity 520/520; 720px Student width; responsive stacking; accessible
  `#0f6dbd` focus; backend/API/database/domain/Research IA unchanged.
- Verification: 95+1 affected, 130+2 Student, 421+8 core; isolated cross-page
  flow PASS; 24/24 Student renders; 6/6 Research smoke; legacy Playwright,
  lifecycle/recovery, and exact launcher PASS.
- One pre-existing WTR ID-allocation collision is documented and remains an
  out-of-scope backend task.
- v0.9.4-C/D and v1.0 remain not started. This task stops after the second
  bounded verification/documentation commit.

**Date:** 2026-08-01
**Current task:** v0.9.4-A Hybrid Design System Foundation
**Status:** completed (see RUN_VERIFICATION_V0.9.4_A.md)

- Hybrid Pixel System 2.0 foundation implemented (canonical tokens,
  generated CSS, Streamlit theme, sans body + constrained mono, AA primary
  action red `#e00047`, shared geometry/spacing/focus/status/density/
  responsive tokens, local SVG icons, shared component primitives).
- Minimal production adoption + the two hardcoded Chinese-mode Research Data
  strings localized; locale parity 382/382.
- Verified: core pytest 394+8; live A–G 20; legacy Playwright PASS; lifecycle
  PASS; `run.bat --verify` PASS; zh probe 3/3; representative 24/24; final
  48/48 browser renders; migration 12; config-v0.9.0.
- Next: v0.9.4-B (Student Experience Redesign) under a separate goal;
  v0.9.4-C not before B.

**Date:** 2026-07-31
**Current version:** v0.9.3 (A + B + C)
**Status:** completed

**Date:** 2026-08-01
**Current task:** v0.9.3-C product journey hardening
**Status:** completed

## Completed (v0.9.3-C)
- Learning Journey hardened (UX-001): read-time derivation from authoritative
  source records; event contract, ordering, deduplication, versioning,
  limitations; no render/locale/refresh events.
- Accurate empty-state taxonomy (UX-002, DATA-001); Student ID normalization
  and learner-state consistency (UX-003); loading states (ERR-003).
- Practice and revision idempotency; practice evaluation persisted;
  conservative revision-response semantics; no unsupported learning claims.
- Deterministic demo journey (synthetic DEMO-001): idempotent setup, scoped
  cleanup, local provider only, DB backups (scripts/demo_journey.py).
- Journey browser verification incl. S02 regression, API-restart recovery,
  and four locale/viewport combinations (verification/v0.9.3-c/).
- pytest: 324 passed, 8 skipped; Cases A-R + live validation: 130 passed;
  legacy Playwright harnesses PASS; run.bat --verify PASS x3; migration 12;
  config-v0.9.0.

## Completed (v0.9.3-B)
- Eight broken Research endpoints repaired (export schema/preview/run/history/
  manifest/status, data-quality, pii-candidates/pii-review, human reviews,
  dataset split)
- Canonical error taxonomy (app/errors.py)
- Server-side error mapping with request IDs
- Client-side classification + centralized timeouts + bounded GET-only retries
- Role-appropriate error presentation + 295-key locale parity
- Research Data 8-subsection workflow verified via HTTP and browser
- 25 new tests (tests/test_request_reliability_v093b.py); 314 passed, 8 skipped
- Cases A-R: 110 passed; legacy harnesses PASS as designed
- run.bat --verify: PASS; migration 12; config-v0.9.0

## Completed (pre-v0.9.4 UI/UX exploration)
- Live 12-page interface audit in 4 combinations (en/zh_CN x 1280x900/390x844)
  with real interaction; zero console errors/exceptions/overflow on 48 page
  renders
- ui-ux-pro-max skill searches (9 runs) recorded under
  verification/design/pre-v0.9.4/uiuxpro-results/
- Sanitized current-interface screenshots under
  verification/design/pre-v0.9.4/current-ui/
- Six design decision documents in docs/design/ (audit, directions,
  component inventory, token options, page recommendations, decision matrix)
- Recommended direction: B — Hybrid Pixel System 2.0 (pending user decision)

## Pre-v0.9.4 status
- No design direction has yet been approved.
- No implementation has started.
- v0.9.3-C is complete; v0.9.4 remains separate and unimplemented.

## Next
- User decision on pre-v0.9.4 design direction (A / B / C)
- v1.0 corpus work (not started)
