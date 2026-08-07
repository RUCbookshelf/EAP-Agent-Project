# v0.9.7-D Work Unit 4 - Final Integration Verification and v0.9.7-D Closure

**Status:** COMPLETE (GREEN) - all 50 WU4 acceptance criteria satisfied;
**v0.9.7-D is complete, verified, and closed**; the next planned phase is
v0.9.7-E.
**Date:** 2026-08-07
**Governing protocol:** the owner-provided v0.9.7-D goal (WU4 section).

## 1. Baseline

- Branch `master`; starting HEAD `347de7c` (WU3 closure).
- Migration 13; config-v0.9.0; locale parity 600/600.

## 2. Complete end-to-end flow (13.2)

`verification/v0.9.7-d/v0.9.7-d-wu4-20260807-r1/wu4_e2e_matrix.py` drives the
complete workflow through the real UI per combination (en/zh x
1280x900/390x844, isolated DB, distinct learner):

Select learner -> Writing submit (real UI) -> saved state -> Feedback
priority -> Open Revision (preset) -> linked Revision submit -> Open
Practice (intent) -> active target -> Generate exercise -> attempt submit ->
evaluation available -> Finish -> completed -> Journey grouped cycle ->
sidebar-rerun zero-write checks per state -> full page reload + Journey
re-entry (no duplicates, no writes).

Evidence: `rendered_wu4_matrix_evidence.json` (28/28 state records clean;
`journey_reentry_zero_writes: true` per combination; `scenario_deltas`
exact: 8 essays = 2 per combo (original + revision), 4 revision groups,
4 practice targets, 4 exercise instances, 4 attempts, 4 evaluations,
analysis/feedback/diagnosis rows per submission; no unexpected rows) +
screenshots.

## 3. Required scenarios (13.3) and their evidence

| Scenario | Evidence |
|---|---|
| Standard priority-guided cycle | WU4 matrix full flow (4 combinations) |
| No-priority | WU1 matrix `feedback_no_priority` (corrected pre-reload captures, heading=Feedback) + focused suite |
| Insufficient evidence | WU1 focused suite (neutral, no error red) |
| Evaluation unavailable | WU2 matrix `practice_evaluation_unavailable` (dashed neutral) + WU4 attempt-saved render |
| Active Practice | WU2/WU4 matrices (`practice_active`) |
| Completed Practice | WU2/WU4 matrices (`practice_completed`) |
| Completed re-entry | WU4 full-reload re-entry + WU5 suite |
| Multiple essays | WU4 scenario deltas (2 essays/cycle) + v0.9.7-C release suite |
| Linked revision | WU4 revision flow (revision_groups=4) + v0.9.7-A/B suites |
| Multiple revisions | v0.9.7-A/B regression suites |
| Multiple Practice targets | v0.9.7-B WU5 suite + WU2 matrix (active + completed target) |
| Active plus completed target | WU2 matrix + WU4 flow |
| Legacy/unresolved Practice | WU2 matrix `practice_legacy` (dashed notice) |
| Stale reference | v0.9.7-C WU2 focused suite (preset invalid notes) |
| Cross-learner reference | v0.9.7-C WU2 focused suite (ownership) |
| API error | Focused suites (recoverable/blocking `render_api_error`) |
| Empty states | WU1/WU2 matrices + focused suites |
| Research baseline | Research smoke 6/6 (exit 0) |

## 4. Final rendered matrix (13.4)

Per combination (en/zh x 1280x900/390x844, isolated DB, distinct learner):
writing_saved, feedback_priority, revision_saved, practice_active,
practice_attempt_saved, practice_completed, journey_grouped - all PASS
with 0 exceptions, no overflow, no raw locale keys, no forbidden wording,
no console/page errors, no remote requests, sidebar-rerun whole-DB
zero-writes (28/28), and full-reload Journey re-entry zero-writes (4/4).
Screenshots recorded per state (top + bottom); `scrolled` recorded per
state (bottom-distinct is informational because Streamlit's inner
main-column scroll container keeps the document height at the viewport -
below-fold evidence is covered by the WU1/WU2 matrices and the scrolled
flags).

## 5. Automated verification (13.5)

| Check | Result |
|---|---|
| Focused v0.9.7-D (WU1 39 + WU2 40 + design-system 22 + token guards) | 174 passed / 0 failed |
| v0.9.7-B/C continuity (v097a/b/c focused suites) | 286 passed / 0 failed |
| v0.9.7-B WU5 completion suite | 38 passed / 0 failed |
| Affected regression (Writing/Feedback/Revision/Practice/Journey/API/ports/locale/components/CSS) | covered by the above + WU4 matrix re-renders |
| Full non-live core (canonical env: PYTHONUTF8=1, PYTHON_DOTENV_DISABLED=1, LLM_PROVIDER=local, fresh isolated DATABASE_PATH, DATABASE_URL removed, 33-entry SERVICE_API_DIFF_ALLOWLIST, --ignore=tests/live) | **1237 passed / 8 skipped / 0 failed / 4 warnings / exit 0** |
| Launcher `cmd /c "run.bat --verify"` | PASS twice (exit 0): health/docs/streamlit 200/200/200, migration 13, config-v0.9.0, isolated auto-provisioned DB, no live provider call |
| Locale parity | en=600, zh=600, no missing/empty |
| Research smoke (established 6-scenario subset) | 6/6 PASS (exit 0), ports cleaned |
| Impact review | fresh GitNexus index at the final tree (section 7) |
| compileall app tests | exit 0 |
| `git diff --check` (scoped) | clean |
| No-migration check | migration 13 unchanged; no migration 14 |

Note: the first full-core attempt without the canonical allowlist failed
only the parity-contract env test (1236/1); the canonical re-run passes
1237/8/0.

## 6. Final design review (13.6)

Independent `opencode-go/minimax-m3` verdict (agent 019fda22-c5b3-7c23-b6a3-81247373bc11):
**READY TO CLOSE WITH DOCUMENTED LIMITATIONS** (not NOT READY). The review
confirmed cross-page consistency, information/action hierarchy, state
consistency, bilingual resilience, academic credibility, and token reuse
across the four rendered matrices; limitations recorded: the completed-
Practice flat panel application rule (design doc section 21), the v0.9.7-E
deferral register (section 15), and the informational bottom-distinct
note.

## 7. Impact review (fresh index)

The GitNexus index was refreshed against the final v0.9.7-D implementation
tree (section 9 of this report records the exact HEAD) and detect-changes
was run against the v0.9.7-C baseline. Production delta for v0.9.7-D is
limited to: `app/ui/features/student/{writing,feedback,revision,practice}.py`
(design-system adoption), `app/ui/components.py` (feedback card title),
`app/ui/pixel_art.py` (tokens/selectors/grouped rules), and
`docs/development/V0.9.7_D_STUDENT_DESIGN_SYSTEM.md`; everything else is
tests, verification evidence, and release documentation. No
architecture-boundary violation and no unexplained fan-out (corroborated
by the 1237-test full core and the direct diff review).

## 8. WU4 acceptance criteria (50/50)

1-7. WU1-WU3 remain GREEN; all five pages use the frozen design system and
  appear to belong to one product - PASS (matrices + MiniMax verdict).
8. Full learning workflow succeeds - PASS (WU4 e2e matrix, 4 combinations).
9-13. No business/ownership/persistence/Journey/Practice-completion
  semantic changed - PASS (regression suites + scenario deltas).
14-17. No duplicate target/exercise/attempt/evaluation - PASS (scenario
  deltas exact; WU5 suite).
18. Learner isolation - PASS (distinct learners per combination; suites).
19. Reads and navigation side-effect free - PASS (28/28 + 4/4 zero-writes).
20-23. Evaluation unavailable / no-priority / insufficient-evidence /
  legacy-unresolved honest - PASS (neutral/dashed recipes; matrices).
24-27. en/zh desktop + mobile pass - PASS (WU4 matrix; WU1/WU2 matrices).
28-31. No remote resource; no raw locale key; no horizontal overflow; no
  console/page error - PASS (all matrices).
32. Focused v0.9.7-D tests pass - PASS (174).
33. v0.9.7-B/C continuity passes - PASS (286).
34. Affected regression passes - PASS (286 + WU5 38 + matrices).
35. Full non-live core passes - PASS (1237/8/0).
36. Launcher verification passes - PASS twice.
37. Locale parity passes - PASS (600/600).
38. Research smoke passes - PASS (6/6).
39. Final impact review passes - PASS (section 7).
40. No unexplained production fan-out - PASS.
41. No migration added - PASS.
42. `git diff --check` clean - PASS.
43. No unrelated changes committed - PASS (per-commit staged lists).
44. Protected files untouched - PASS (section 10).
45. Final documentation internally consistent - PASS (reports + state
  docs reconciled in the closure commit).
46. MiniMax verdict not NOT READY - PASS (READY TO CLOSE WITH DOCUMENTED
  LIMITATIONS).
47. No release blocker remains - PASS.
48. v0.9.7-D marked complete, verified, and closed - PASS (this report).
49. v0.9.7-E identified as the next phase - PASS.
50. No push or pull request - PASS.

## 9. Commits

1. `test(v0.9.7-d): verify final Student workflow end to end` (WU4 matrix
   + evidence)
2. `docs(v0.9.7-d): close work unit 4 and v0.9.7-D` (WU4 report + aggregate
   report + state-document reconciliation)

Ending HEAD: the v0.9.7-D closure commit (hash in section 13).

## 10. Protected and user-owned files

`AGENTS.md`, `.claude/`, `CLAUDE.md`, `RUN_VERIFICATION_V0.7.md`,
`RUN_VERIFICATION_V0.8.2.md`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`,
`data/demo_journey_manifest.json`, `diagnostics/`, and the v0.9.7-a run
logs were never modified, staged, or committed. No push or pull request.

## 11. Defects and remediation

No release blocker. One verification-environment issue (the full-core
parity test requires the canonical 33-entry SERVICE_API_DIFF_ALLOWLIST)
was resolved by running the canonical environment; one harness ordering
issue in the WU1 no-priority capture was fixed in WU3 and re-verified.

## 12. Remaining limitations

- Design doc section 21 application rule (completed Practice panel flat).
- v0.9.7-E deferral register (design doc section 15): full mobile redesign,
  dark mode, animation, illustration/branding, full accessibility
  remediation, Research UI, collapsible Journey cycles, Home workflow-step
  restyle and spinner unification, O1 copy touch, KB-09 mono learner-ID
  role, KB-13 mobile type-scale compression.
- v0.9.7-D does not begin corpus intelligence (v0.9.8-A).

## 13. Final decision

All WU4 acceptance criteria satisfied; no release blocker remains;
protected/user-owned files untouched; no push or pull request.

> **v0.9.7-D is complete, verified, and closed. The frozen Student design
> system has been applied consistently across Writing, Feedback, Revision,
> Practice, and Journey without changing the verified learning, ownership,
> persistence, or navigation contracts. The next planned phase is
> v0.9.7-E: Responsive, Mobile, and Accessibility.**
