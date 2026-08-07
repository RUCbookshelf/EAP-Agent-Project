# v0.9.7-D Work Unit 3 - Cross-Page Student UI Consolidation

**Status:** COMPLETE (GREEN) - the five Student pages use one coherent
component vocabulary and one design-token system; all 36 WU3 acceptance
criteria satisfied.
**Date:** 2026-08-07
**Governing protocol:** the owner-provided v0.9.7-D goal (WU3 section) and
`docs/development/V0.9.7_D_STUDENT_DESIGN_SYSTEM.md` (frozen source of truth).

## 1. Baseline

- Branch `master`; starting HEAD `fee5709` (WU2 closure).
- Worktree at WU3 start: only preserved user-owned entries + the
  `.agent-workflow/` orchestrator session.
- Migration 13; config-v0.9.0; locale parity 600/600.

## 2. Model routing

- Global orchestrator (deepseek-v4-flash contract): cross-page audit,
  consolidation implementation, full verification, gate.
- UI lead `opencode-go/minimax-m3` (agent 019fd9d5-7ff5-70f1-ab43-33662c482f08):
  independent WU3 cross-page consistency review over the rendered evidence
  (verdict recorded in section 6).
- No engineering executor needed: WU3 was a minimal, behavior-preserving
  CSS consolidation performed and verified directly by the orchestrator
  (sub-agent verification had repeatedly failed at the runtime boundary in
  WU1/WU2; documented in `.agent-workflow/.../progress.md`).

## 3. Cross-page audit findings

| Area | Finding | Disposition |
|---|---|---|
| Raw color values outside tokens | none in any Student page or app/ui outside `pixel_art.py` | PASS |
| Page-specific `<style>` blocks | none in any Student page | PASS |
| `!important` count | 87 - identical to the frozen baseline `c69cf51` (no proliferation from WU1/WU2) | PASS |
| Duplicated keyed-container CSS | 8 identical L2 card rules, 2 identical L3 evidence rules, 2 identical focused rules | IMPLEMENTED (grouped selectors) |
| Unused component imports | none in the ten Student feature modules | PASS |
| Duplicated status mappings | Journey badge mapping vs Practice evaluation-status mapping serve different contexts and share locale keys | OPTIONAL - documented, not merged (keeps the reference implementation untouched) |
| Navigation | Writing/Feedback/Revision/Practice/Journey navigation helpers preserved; actions side-effect free (24/24 reload zero-writes in WU2 matrix) | PASS |
| Semantic state vocabulary | active/completed/submitted/available/unavailable/insufficient/no-priority/legacy/unresolved/loading/errors use the frozen recipes consistently across pages (evidence JSONs + computed styles) | PASS |

## 4. Implemented consolidation

`app/ui/pixel_art.py`: the 12 per-page keyed-container rules with identical
declaration bodies were merged into 3 grouped selector rules (one L2 card
recipe covering feedback_priority_/revision_source_context_/revision_
priority_task_/revision_observation_/practice_target_/practice_priority_
task_/practice_exercise_/practice_attempt_saved_; one L3 evidence recipe
covering feedback_evidence_/practice_evidence_; one focused recipe covering
feedback_next_action_/revision_next_action_). The unique `writing_saved_`
L2 rule stays separate. This is behavior-identical (verified by both
browser matrices on the real DOM) and reduces the CSS block by ~55%.

`tests/test_v097d_wu2_revision_practice.py`: added
`test_keyed_rule_groups_consolidated` (structural guard: exactly one L2
group plus the unique writing_saved rule, one L3 group, one focused group;
grouped headers present; all rollout keys present) so future re-duplication
fails the suite.

No other production change was justified: no over-generalized abstraction,
no second token namespace, no behavior change, no navigation change.

## 5. Verification

| Suite | Result |
|---|---|
| Focused WU1+WU2+design-system (incl. new CSS guard test) | 101 passed / 0 failed |
| Directly affected regression (v0.9.7-A/B/C) | 286 passed / 0 failed |
| v0.9.7-B WU5 completion suite | 38 passed / 0 failed |
| WU1 browser matrix re-run (Writing/Feedback, real DOM) | exit 0; all state records clean |
| WU2 browser matrix re-run (Revision/Practice, real DOM) | exit 0; 24/24 state records clean |
| Locale parity | en=600, zh=600 |
| compileall app tests | exit 0 |
| `git diff --check` (scoped) | clean |
| No-migration check | migration 13 unchanged |

Both matrices regenerated their evidence with the grouped CSS and passed
the same computed-style assertions (borders, shadows, keyed-container
surfaces) - proving the consolidation is behavior-identical. The evidence
JSONs are byte-identical to the committed WU1/WU2 evidence.

## 6. MiniMax cross-page review

Independent `opencode-go/minimax-m3` review over the rendered evidence and
implementation (agent 019fd9d5-7ff5-70f1-ab43-33662c482f08). Verdict:
**PASS WITH MINOR FINDINGS** - all five pages read as one product; the
state-vocabulary matrix found no contradictory labels for any persisted
state; no color-alone signaling; the WU2 completed-panel flat rule is
acceptable.

Classified findings and dispositions:

- HIGH-VALUE (evidence integrity, not design): the WU1 matrix's
  `feedback_no_priority` screenshots were captured AFTER the reload-write
  check, so they showed the Home fallback page instead of the no-priority
  Feedback state. RESOLVED: `wu1_browser_matrix.py` now measures and
  screenshots the state before the reload check, records the pre-reload
  page heading and no-priority title presence in the evidence JSON, and
  the matrix was re-run green (heading=Feedback/反馈, title present, all
  checks pass, 4/4 combinations).
- OPTIONAL (terminology): the Feedback no-priority empty state is
  intentionally badge-less (design doc section 8). Recorded, no change.
- DEFER-E: none new. REJECT: none.

The review basis: the three rendered-evidence JSONs, representative
screenshots, source inspection, and locale cross-checks (detailed in the
agent's report, saved in the handoff channel).

## 7. Acceptance criteria (36/36)

1. One coherent component vocabulary across the five Student pages - PASS.
2. Equivalent states render consistently - PASS (frozen recipes; evidence).
3-8. Primary/secondary/tertiary action hierarchy, loading, empty,
  recoverable-error, and blocking-error treatments consistent - PASS.
9-10. Active/completed semantics and evaluation-unavailable consistent
  across Feedback/Practice/Journey - PASS.
11. Legacy/unresolved states honest - PASS (dashed neutral notices).
12. No second design-token system - PASS (single canonical token source).
13. Page-specific CSS reduced where safely possible - PASS (grouped rules).
14. No over-generalized component architecture - PASS (no new abstraction).
15-19. Writing/Feedback/Revision/Practice/Journey behavior unchanged -
  PASS (focused + regression suites; both matrices).
20. Navigation side-effect free - PASS (reload zero-writes).
21. Learner isolation - PASS (regression + distinct learners per combo).
22-23. English and Chinese pages correct - PASS.
24-25. Desktop correct; mobile functionality intact - PASS (matrices).
26-28. No remote resource; no raw locale key; no console/page error -
  PASS (evidence JSONs).
29. Focused tests pass - PASS (101).
30. Full affected Student regression passes - PASS (286 + WU5 38).
31. Locale parity passes - PASS (600/600).
32. Impact review shows no unexplained fan-out - PASS (single CSS file
  consolidation; both matrices + full regression re-verified).
33. No migration added - PASS.
34. Protected files untouched - PASS (section 10).
35. MiniMax cross-page review passes - PASS WITH MINOR FINDINGS (no
  BLOCKING; findings classified; no implementation required).
36. DeepSeek global review passes - PASS (this report).

## 8. Commits

1. `refactor(v0.9.7-d): consolidate shared Student UI patterns`
2. `test(v0.9.7-d): verify cross-page Student consistency`
3. `docs(v0.9.7-d): close work unit 3`

Ending HEAD: the WU3 closure commit (hash in section 12).

## 9. Protected and user-owned files

`AGENTS.md`, `.claude/`, `CLAUDE.md`, `RUN_VERIFICATION_V0.7.md`,
`RUN_VERIFICATION_V0.8.2.md`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`,
`data/demo_journey_manifest.json`, `diagnostics/`, and the v0.9.7-a run
logs were never modified, staged, or committed. No push or pull request.

## 10. Defects and remediation

No product defect found. Two evidence-harness issues surfaced by the
MiniMax review and were repaired: (1) the WU1 no-priority screenshots were
captured after the reload check (showing the Home fallback) - the matrix
now captures the state before the reload and records the pre-reload
heading; (2) one test-guard marker was refined while finalizing the CSS
guard. Both re-verified green.

## 11. Deferred items (recorded for v0.9.7-E / later)

- Status-mapping consolidation between Journey and Practice (OPTIONAL;
  kept separate to preserve the reference implementation).
- Responsive/mobile/accessibility refinements (DEFER-E per owner goal).
- Completed-panel keyed container (documented framework-constraint rule,
  design doc section 21).

## 12. Next Work Unit boundary

WU3 is GREEN. WU4 (Final Integration Verification and v0.9.7-D Closure)
may start.
