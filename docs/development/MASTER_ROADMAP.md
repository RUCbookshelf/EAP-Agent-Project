## v0.9.7 roadmap - 2026-08-04

| Item | Status |
|---|---|
| v0.9.7-A Priority-Guided Learning Cycle Completion | COMPLETE and verified (focused 14 passed; affected regression 293 passed; full non-live core 860 passed / 8 skipped / exit 0; `run.bat --verify` PASS; rendered matrix all four locale/viewport combinations PASS; evidence verification/v0.9.7-a/v0.9.7-a-20260804-r1/) |
| v0.9.7-B Practice Target Generation and Practice Workflow | WU1-WU3 COMPLETE (RUN_VERIFICATION_V0.9.7_B_WU2.md + WU3.md); WU4 focused Practice task and attempt loop COMPLETE (RUN_VERIFICATION_V0.9.7_B_WU4.md; explicit entry intent + create-or-reuse, learner-owned context endpoint, seeded current exercise, attempt ownership + pending guard, saved-state recovery; focused 32 passed; affected 638 passed / 1 skipped; full non-live core 1000 passed / 8 skipped / exit 0; `run.bat --verify` PASS; rendered matrix en/zh x desktop/mobile PASS); WU5 (evaluation + completion semantics) next; v0.9.7-B overall NOT complete |
| v0.9.7-C Student Journey Functional Completion | not started |
| v0.9.7-D Student UI/UX Redesign and Visual Polish | not started |
| v0.9.7-E Responsive, Mobile, and Accessibility Refinement | not started |

**v0.9.7-A (2026-08-04):** the priority-guided learning cycle is complete and
verified. Revision now consumes the Feedback priority as an active task,
submission produces an explicit completion state with safe end-of-cycle and
existing-Practice continuation, and re-entry never treats a saved revision as
unsubmitted. Automatic Priority-to-Practice target generation remains a
v0.9.7-B item. All 15 acceptance criteria are satisfied; closure HEAD
`209a8a8` (five focused commits). v0.9.7-A is complete, verified, and
closed. Stop before v0.9.7-B.

**v0.9.7-B WU1-WU2 (2026-08-05):** WU1 froze the practice-workflow audit and
specification (docs/development/V0.9.7_B_PRACTICE_WORKFLOW_AUDIT.md,
V0.9.7_B_SPEC.md; HEAD `7fdf875`). WU2 implemented the production
priority-to-practice mapping and provenance contract: one persisted Feedback
priority resolves into a validated Practice-target creation payload with a
stable `PRIO-{feedback_id}-{priority_index}` reference, the production
category map (demo now imports it), `source_priority_id`/`evidence_ids`
forwarding through the API, and ownership/source validation before any
priority-derived write (see RUN_VERIFICATION_V0.9.7_B_WU2.md). No schema or
migration change; no UI automatic target creation; no idempotency/completion.
WU3 (idempotent target creation and reuse) is the next planned work unit;
v0.9.7-B as a whole is not yet complete. Do not begin v0.9.7-C.

**v0.9.7-B WU3 (2026-08-05):** idempotent priority practice target creation
and reuse is complete and verified: prefix-length-safe `_next_practice_id`
repair (BEGIN IMMEDIATE serialized allocation; FET/WTR/PSS collision defect
closed), `PracticeTargetCreationService` create-or-reuse on the logical key
(student_id, source_submission_id, source_priority_id), migration 13
(additive partial unique index on the persisted JSON priority key;
one-step rollback), unified ownership/evidence validation for all creation
paths, and the `FeedbackEngagementTrace.created_at` schema fix. Focused 33
passed; affected regression 562 passed; full non-live core 969 passed /
8 skipped / exit 0; `run.bat --verify` PASS; evidence
RUN_VERIFICATION_V0.9.7_B_WU3.md. WU4 (focused Practice task and attempt
loop) is the next planned work unit; v0.9.7-B is not yet complete. Do not
begin v0.9.7-C.

**v0.9.7-B WU4 (2026-08-05):** the focused Practice task and attempt loop is
complete and verified: Feedback per-priority and Revision-completion entry
actions transfer explicit intents that the Practice page resolves
server-side through WU3 create-or-reuse (never on render), a learner-owned
read-only context endpoint re-resolves the persisted priority context, one
current exercise is reused or created and seeded from the evidence quote,
the focused task renders priority/why/direction/evidence/instruction, and
attempt submission is ownership-validated with a shared pending guard and
explicit saved-state recovery from persistence. Evaluation remains the
existing unchanged side effect; no COMPLETED status and no WU5 actions.
Focused 32 passed; affected regression 638 passed / 1 skipped; full non-live
core 1000 passed / 8 skipped / exit 0; `run.bat --verify` PASS; rendered
matrix (en/zh x 1280x900/390x844) PASS; evidence
RUN_VERIFICATION_V0.9.7_B_WU4.md. WU5 (evaluation semantics + completion) is
the next planned work unit; v0.9.7-B is not yet complete. Do not begin
v0.9.7-C.

# Master roadmap

## v0.9.5 roadmap - 2026-08-02

| Item | Status |
|---|---|
| v0.9.5-A Architecture Coupling Audit (read-only) | completed |
| v0.9.5-B API Router Decomposition + Health Contract Reconciliation | completed and verified |
| v0.9.5-C Frontend Feature Extraction + UI Boundary Restoration | completed and verified |
| v0.9.5-D Frontend Contract Hardening + API Client Port Isolation | completed and verified |
| v0.9.5-E Database Repository Decomposition | completed and verified |
| v0.9.5-F1 Service-Repository Dependency Audit (read-only) | completed |
| v0.9.5-F2 Low-Risk Service Repository Dependency Narrowing | completed and verified |
| v0.9.5-F3 Learner Read-Model Dependency Narrowing | completed and verified |
| v0.9.5-F4 Reanalysis and Journey Dependency Narrowing | completed and verified |
| v0.9.5-F5A CALF Service Dependency Narrowing | completed and verified |
| v0.9.5-F5B ResearchDataService Dependency Narrowing | completed and verified |
| v0.9.5-F6A0 Revision Repository Capability Completion | completed and verified (F6A prerequisite) |
| v0.9.5-H1 Persistence Protocol Inventory and Consolidation Plan (read-only) | completed |
| v0.9.5-H2A Remove Unused Legacy Persistence Contracts | completed and verified |
| v0.9.5-H2B Rename Active Configuration Repository Contract | completed and verified |
| v0.9.5-H2C Canonicalize Duplicate AnalysisRunReader Infrastructure Contract | completed and verified |
| v0.9.5-H2D1 Formalize ConfigurationPort as a Structural Protocol | completed and verified |
| v0.9.5-H2D2 Bind API Ports to Production Dependency Accessors | completed and verified (H2D2-V1 full-core closure: exit 0, 709 passed, 8 skipped, 2 warnings) |
| v0.9.5-H2D2-V1 Full-Core Verification Closure | completed and verified |
| v0.9.5-H2E Architecture Freeze | completed - v0.9.5 architecture optimization COMPLETE and frozen |

| v0.9.5-H1 Persistence Protocol Inventory and Consolidation Plan (read-only) | completed |
| v0.9.5-G Database Facade Contraction | completed and verified |
| v0.9.5-F6D Practice Write-Boundary Narrowing | completed and verified |
| v0.9.5-F6C SubmissionService Persistence Dependency Narrowing | completed and verified |
| v0.9.5-F6B AdminReanalysisService Persistence Dependency Narrowing | completed and verified |
| v0.9.5-F6A RevisionService Runtime Repository Narrowing | completed and verified |
## v0.9.6 roadmap - 2026-08-03

| Item | Status |
|---|---|
| v0.9.6-A Linked Revision Submission Reliability | completed and verified (dedicated long-operation timeout, pending guard, no duplicate POST, bounded reconciliation; full core 730 passed / 8 skipped, launcher PASS) |
| v0.9.6-B First Draft and Unified Submission Reliability | completed and verified (shared long-submit transport, pending guard, no duplicate POST, exact first-draft reconciliation; full core 760 passed / 8 skipped, launcher PASS) |
| v0.9.6-C No-Priority Workflow Completion and Sidebar Control Repair | completed and fully verified (C1/C2 owner-accepted; full core 809 passed / 8 skipped, launcher PASS) |
| v0.9.6-D0 Priority Path Production Validity Audit | BLOCKED at live-provider preflight (classification D0-E, audit-only); targeted verification 155 passed; recommended next: v0.9.6-DP0 Production Provider Reliability (separately approved) |
| v0.9.6-DP0 Production Provider Reliability | COMPLETE and verified (DP0-A diagnosis owner-accepted; live 4 consecutive deepseek-v4-pro successes, 0 corrections/fallback/timeouts; focused 101+103+24 passed; full core 821 passed/8 skipped with 3 isolated-classified anomalies; launcher PASS; exports 776/388) |
| v0.9.6-DP0-V1 Full-Core Verification Closure | COMPLETE and fully verified (canonical environment frozen; full non-live core 824 passed/8 skipped/0 failed/0 errors, exit 0, run once; launcher PASS exit 0; exports 776/388) |
| v0.9.6-DP0-V2 Verification Safety Incident Closure | COMPLETE and fully verified (incident V2-DB-A closed; current DB adopted as new baseline; launcher verification isolation guard; guard tests 22 passed + contract tests 31 passed; launcher PASS exit 0; exports 776/388; full core preserved, not rerun) |
| v0.9.6-D0-R Frozen Priority Path Production Validity Audit | COMPLETE - classification D0-R-C (downstream capability incomplete but non-blocking); v0.9.6 stabilization CLOSED; 7/7 live provider successes, 3 valid priorities + 2 valid no-priorities, 0 fabricated evidence, repeatability STABLE, targeted 131 passed; next v0.9.7-A/B |

Next stage: **v0.9.6 user-visible feature development** (v0.9.6-C is
complete; the next goal must deliver a user-visible or
research-workflow-visible functional outcome; no further generic
architecture audit or cleanup is authorized).

**v0.9.6-D0 (2026-08-04):** the priority-path production validity audit
stopped at its preregistered preflight blocker (D0-E - provider path
unreliable). The evidence-based next stage is a separately approved
v0.9.6-DP0 Production Provider Reliability goal; v0.9.6-D1 and all
priority-generation/downstream repair stages remain not started.

**v0.9.6-DP0 (2026-08-04):** provider reliability is repaired and verified. The recommended next stage is a separately approved
v0.9.6-D0-R goal that resumes the frozen priority-path production validity audit; v0.9.6-D1 remains not started.

**v0.9.6-DP0-V2 (2026-08-04):** the verification safety incident is formally
closed (V2-DB-A; current development database adopted as the new baseline)
and launcher verification isolation is hardened. v0.9.6-DP0 is formally and
finally closed.

**v0.9.6-D0-R (2026-08-04):** the frozen priority-path production validity
audit is COMPLETE with classification D0-R-C. The repaired real provider
generated valid, source-faithful priorities for all targeted cases
(lexical_repetition and connective_use), the preregistered
sentence-structure probe produced its expected no-priority result, evidence
integrity was clean, repeatability was STABLE, and Feedback/Home consumed
priorities correctly. Revision and Practice are partially consumable
(priority-family display on fresh source and automatic practice-target
creation are v0.9.7 feature items). v0.9.6 stabilization is CLOSED. Next
approved planning stage: v0.9.7-A; v0.9.7 implementation is not started.

## v0.9.6 -> v0.9.7 transition (2026-08-04)

The stabilization cycle ends with DP0-V2. The only remaining mandatory
pre-feature task is the frozen-corpus audit; after it, the project moves into
v0.9.7 feature development. Only blocker-grade defects (reproducible
data-loss, security, startup, submission, or core-path issues) may interrupt
this transition; non-blocking limitations move to the v0.9.7 feature
roadmap.

```text
v0.9.6-DP0-V2  Verification safety incident closure
      |
      v
v0.9.6-D0-R  Final frozen-corpus production-validity audit
      |
      v
v0.9.7-A  Priority-Guided Learning Cycle Completion
      |
      v
v0.9.7-B  Practice Target Generation and Practice Workflow
      |
      v
v0.9.7-C  Student Journey Functional Completion
      |
      v
v0.9.7-D  Student UI/UX Redesign and Visual Polish
      |
      v
v0.9.7-E  Responsive, Mobile, and Accessibility Refinement
```

## v0.9.4 roadmap - 2026-08-01

| Item | Status |
|---|---|
| v0.9.4-A Hybrid Pixel System 2.0 foundation | completed |
| v0.9.4-B six-page Student Experience Redesign | completed and verified |
| v0.9.4-B core/browser/lifecycle/launcher verification | completed |
| v0.9.4-C Research Experience Redesign | not started |
| v0.9.4-D | not started |
| v1.0 | not started |

v0.9.4-B closes after its verification/documentation commit. It does not
authorize Research redesign, backend persistence repair, external-provider
work, corpus/ML work, or a pilot.

## v0.9.3 (A + B + C) — 2026-08-01

| Item | Status |
|---|---|
| Runtime reliability (REL-001) + lifecycle | completed (v0.9.3-A) |
| Research API integrity + error taxonomy (ERR-001/002, PERF-001) | completed (v0.9.3-B) |
| Product journey hardening (UX-001, DATA-001, UX-002/003, ERR-003) | completed (v0.9.3-C) |
| Journey event contract + accurate empty states + demo journey | completed (v0.9.3-C) |
| Integrated verification (pytest 320+8, Cases A-R 110, run.bat PASS x3, browser journeys) | completed |
| Migration 12 / config-v0.9.0 | unchanged |
| v0.9.4-A Hybrid Pixel System 2.0 foundation (tokens, theme, typography, components, localization) | completed |
| v0.9.4-B Student Experience Redesign | completed and verified (Student pages only) |
| v0.9.4-C Research Experience Redesign | not_started |
| v1.0 | not_started |



## v0.9.1 UI Completion & Usability Refinement — 2026-07-31

| Item | Status |
|---|---|
| Role-based navigation (Student + Research Views) | completed |
| Progressive disclosure and reusable components | completed |
| Responsive layout (desktop to 390x844) | completed |
| 271 i18n keys (en + zh_CN parity) | completed |
| Playwright verification (6 scenarios) | completed |
| pytest: 271 passed, 8 skipped | completed |
| Backend (migration 12, config-v0.9.0) | unchanged |
| v1.0 | not_started |


## v0.8 CALF Measurement Foundation — 2026-07-30

| Item | Status |
|---|---|
| Registries, MTLD/HD-D, syntax/error/timing foundations | completed |
| Migration 10 / config-v0.8.0 / APIs / research UI | completed |
| Automated and live A–D verification | completed |
| Accuracy automation, validated syntax measures, CALF total, CEFR | not started / excluded |
| v0.9 feedback–exercise–transfer loop | not started |

This authorization ends after v0.8 verification, documentation, and one isolated commit.


## v0.7.1 bounded repair — 2026-07-30

| Item | State |
|---|---|
| Longitudinal reliability and field-level repair | completed |
| Provider execution status | completed |
| Within-task trajectory and Streamlit UI polish | completed |
| Migration 9 / config-v0.7.1 | completed |
| v0.8 and new measurement constructs | not started |

This authorization ends after the v0.7.1 verification, documentation, and independent commit. It does not authorize v0.8.


## v0.7 authorized release state — 2026-07-30

| Item | State |
|---|---|
| v0.7 Learner Model 2.0 | completed |
| Database | migration 8, additive |
| Active configuration | `config-v0.7.0`, parent `config-v0.6.2` preserved |
| Prompt/schema | `feedback-prompt-v0.7.0` / `structured-feedback-v0.7.0` |
| Snapshot | `learner-profile-v0.7.0` |
| v0.8 and CALF | `not_started` |

The v0.7 boundary is a task-aware descriptive evidence model. It does not estimate proficiency, mastery, causal learning, CEFR, CALF, or an overall score. Completion requires the v0.7 verification report and one isolated Git commit; work then stops.

---

Last updated: 2026-07-29.

| Item | Current value |
|---|---|
| Current project version | 0.6.1 (completed; human calibration review pending) |
| v0.2 status | completed |
| v0.3 status | completed; human continuation authorization received in the v0.4-v0.6 goal |
| v0.4 status | completed |
| v0.5 status | completed; 121 passed, 1 skipped; migration 5; verification PASS |
| v0.6 status | completed; 149 passed, 1 skipped; migration 6; verification PASS |
| v0.3 implementation commit | `0ce8f1a` |
| v0.6.1 status | completed; 183 passed, 2 skipped; migration 7; live DeepSeek and verification PASS |
| Database migration version | 7 |
| Active configuration | `config-v0.6.2`; parent `config-v0.6.1` preserved |
| Prompt version | `feedback-prompt-v0.6.1`; compatible earlier prompts retained |
| Feedback Schema version | `structured-feedback-v0.6.1` |
| API version | v1 |
| Current blocker | none |
| Next step | Stop; conduct `V0.6.1_HUMAN_REVIEW_GUIDE.md`; v0.7 requires separate authorization |


## Version sequence

- v0.2 — local API-first cloud-ready architecture: `completed`
- v0.3 — longitudinal analysis engine: `completed`
- v0.4 — NLP Analyzer 2.0: `completed`
- v0.5 — Revision-aware Feedback: `completed` (`75117ac`)
- v0.6 — Progress Visualization and Versioned Configuration: `completed`
- v0.6.1 — Diagnostic Calibration: `completed`
- v0.7 — Learner Model 2.0: `completed`
- v0.7.1 — Longitudinal Reliability & UI Polish: `completed`
- full CALF measurement: `not_started`

“Cloud-ready” means separable interfaces and configuration; it does not mean cloud deployment. The current authorization ends after v0.7.1; v0.8 and full CALF work remain `not_started`.
