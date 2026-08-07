# v0.9.7-D Aggregate Release Verification - Controlled Student UI/UX Rollout and Consolidation

**Status:** COMPLETE, VERIFIED, AND CLOSED - WU1-WU4 complete; the frozen
Student design system is applied consistently across Writing, Feedback,
Revision, Practice, and Journey; the next planned phase is v0.9.7-E.
**Date:** 2026-08-07

## 1. v0.9.7-D goal

Apply the frozen Student design system ("Calm ledger", validated on the
Journey reference page) consistently across the learning workflow
Writing -> Feedback -> Revision -> Practice -> Journey, while preserving
all verified functional, data, ownership, persistence, navigation, and
learning-semantics contracts from v0.9.7-B and v0.9.7-C.

## 2. WU1-WU4 summary

- **WU1 (Writing + Feedback)**: keyed L2/L3/focused surfaces, verbatim
  evidence before interpretation, priority prominent but not score-like,
  honest no-priority/insufficient-evidence, saved-success panel; focused
  39, regression 286, matrix 4 combos x 5 states (exit 0). GREEN.
- **WU2 (Revision + Practice)**: source-context/priority-task/observation/
  next-action cards, target/priority/evidence/exercise/attempt-saved
  surfaces, dashed evaluation-unavailable and legacy notices, stable
  target selection and completion flows preserved; focused 40, WU5 38,
  regression 286, matrix 4 combos x 6 states (exit 0). GREEN.
- **WU3 (Cross-page consolidation)**: grouped keyed-container CSS
  (12 rules -> 3 groups), CSS guard test, cross-page audit (no raw hex, no
  page styles, no !important growth, no unused imports), MiniMax
  cross-page review PASS WITH MINOR FINDINGS (one WU1 evidence-integrity
  finding fixed); focused 101, regression 286, matrices re-run green.
  GREEN.
- **WU4 (Final integration + closure)**: full end-to-end browser workflow
  per combination (Writing -> Feedback -> Revision -> Practice -> Journey),
  28/28 state records clean, full-reload re-entry zero writes, exact
  scenario deltas, full non-live core 1237/8/0, launcher PASS twice,
  locale 600/600, Research smoke 6/6, fresh-index impact review, MiniMax
  final verdict READY TO CLOSE WITH DOCUMENTED LIMITATIONS. GREEN.

## 3. Model routing

- Global orchestrator: deepseek-v4-flash contract (this session) - task
  packets, gates, parent verification of every claim, commits.
- UI leads: `opencode-go/minimax-m3` (WU1 plan + WU2 implementation review,
  WU3 cross-page review, WU4 final verdict).
- Engineering executors: `opencode-go/mimo-v2.5` (WU1 implementation +
  repairs; WU2 initial implementation).
- Because the sub-agent runtime could not execute the project interpreter
  (sandbox boundary), the orchestrator executed all mechanical repairs and
  verification directly, with every claim re-verified on the real runtime
  (recorded in `.agent-workflow/v0.9.7-d-controlled-rollout/progress.md`).

## 4. Verification results

| Gate | Result |
|---|---|
| Focused v0.9.7-D | 174 passed / 0 failed |
| v0.9.7-B/C continuity + affected regression | 286 passed / 0 failed (+ WU5 38) |
| Full non-live core (canonical env) | **1237 passed / 8 skipped / 0 failed / exit 0** |
| `run.bat --verify` | PASS twice (migration 13; config-v0.9.0; isolated DB) |
| Rendered matrices | WU1 (5 states x 4), WU2 (6 states x 4), WU4 (7 states x 4 + re-entry) - all exit 0, 0 exceptions, no overflow, no raw keys, no forbidden wording, no console/page errors, no remote requests, zero render writes |
| Locale parity | 600/600 |
| Research smoke | 6/6 |
| Impact review | fresh GitNexus index; production delta = 4 student pages + components + pixel_art + design doc |
| `git diff --check` | clean (scoped) |
| Migration | 13 unchanged; no migration 14 |

## 5. Commits

WU1: `9810f4c` feat, `644c7c8` test, `a9d471e` docs.
WU2: `1e7ffde` feat, `a5f8b11` test, `fee5709` docs.
WU3: `c24bb39` refactor, `7b91a27` test, `347de7c` docs.
WU4: `test(v0.9.7-d): verify final Student workflow end to end` and
`docs(v0.9.7-d): close work unit 4 and v0.9.7-D`.

Ending HEAD: the v0.9.7-D closure commit (hash in the final chat report).

## 6. Protected and user-owned files

`AGENTS.md`, `.claude/`, `CLAUDE.md`, `RUN_VERIFICATION_V0.7.md`,
`RUN_VERIFICATION_V0.8.2.md`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`,
`data/demo_journey_manifest.json`, `diagnostics/`, and the v0.9.7-a run
logs were never modified, staged, or committed. No push or pull request.

## 7. Known limitations

- Completed Practice panel renders flat (documented application rule,
  design doc section 21; Streamlit AppTest artifact, real runtime
  unaffected).
- v0.9.7-E deferrals (design doc section 15): full mobile redesign, dark
  mode, animation, illustration/branding, full accessibility remediation,
  Research UI, collapsible Journey cycles, Home workflow-step restyle and
  spinner unification, O1 copy touch, KB-09 mono learner-ID role, KB-13
  mobile type-scale compression.
- Corpus intelligence begins in v0.9.8-A, not v0.9.7-D.

## 8. Final decision

All four Work Unit gates are GREEN; no release blocker remains;
user-owned files untouched; no push or pull request performed.

> **v0.9.7-D is complete, verified, and closed. The frozen Student design
> system has been applied consistently across Writing, Feedback, Revision,
> Practice, and Journey without changing the verified learning, ownership,
> persistence, or navigation contracts. The next planned phase is
> v0.9.7-E: Responsive, Mobile, and Accessibility.**
