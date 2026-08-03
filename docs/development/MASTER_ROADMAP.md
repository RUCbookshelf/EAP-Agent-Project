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
| v0.9.5-H2B Rename Active Configuration Repository Contract | implementation complete; focused+launcher PASS; full-core closure pending |

| v0.9.5-H1 Persistence Protocol Inventory and Consolidation Plan (read-only) | completed |
| v0.9.5-G Database Facade Contraction | completed and verified |
| v0.9.5-F6D Practice Write-Boundary Narrowing | completed and verified |
| v0.9.5-F6C SubmissionService Persistence Dependency Narrowing | completed and verified |
| v0.9.5-F6B AdminReanalysisService Persistence Dependency Narrowing | completed and verified |
| v0.9.5-F6A RevisionService Runtime Repository Narrowing | completed and verified |
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
