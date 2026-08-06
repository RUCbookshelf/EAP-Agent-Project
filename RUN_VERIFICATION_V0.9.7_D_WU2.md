# v0.9.7-D Work Unit 2 - Revision and Practice Consolidation

**Status:** COMPLETE (GREEN) - the frozen Student design system is applied
to the Revision and Practice pages; all 35 WU2 acceptance criteria
satisfied; the midpoint integration checkpoint is GREEN.
**Date:** 2026-08-06
**Governing protocol:** the owner-provided v0.9.7-D goal (WU2 section) and
`docs/development/V0.9.7_D_STUDENT_DESIGN_SYSTEM.md` (frozen source of truth;
Journey = reference implementation; Writing/Feedback adoption from WU1).

## 1. Baseline

- Branch `master`; starting HEAD `a9d471e` (WU1 closure).
- Worktree at WU2 start: only preserved user-owned entries + the
  `.agent-workflow/` orchestrator session.
- Migration 13; config-v0.9.0; locale parity 600/600.

## 2. Model routing and nested calls

- Global orchestrator: deepseek-v4-flash contract (this session) - task
  packet, parent verification of every claim, gate.
- UI lead: `opencode-go/minimax-m3` (agent 019fd70e-75c2-7433-969d-950c0f3abe99):
  application plan + implementation + design review saved to
  `.agent-workflow/.../handoffs/wu2-ui-team.md` (425 lines). Its sandbox could
  not execute the project interpreter, so the orchestrator ran all
  verification directly (see section 6).
- Engineering executor `opencode-go/mimo-v2.5` was used for the WU1 repairs;
  for WU2 the orchestrator executed the mechanical repairs and the full
  verification itself after sub-agent runs repeatedly failed at the sandbox
  boundary (documented in `.agent-workflow/.../progress.md`).

## 3. Implemented scope

### Revision (`app/ui/features/student/revision.py`)

- Keyed containers for the frozen surface recipes: source-context card
  (`revision_source_context_<id>`, L2), priority task card
  (`revision_priority_task_<id>`, L2), observation panel
  (`revision_observation_panel`, L2), next-step action block
  (`revision_next_action`, focused) - applied in the saved-success,
  default-form, and already-revised branches.
- Source context (prompt, draft stage, original text) stays visible and
  distinct from the revised-text input; the original text remains a
  read-only field; the "Revision of #n" relationship and the submission
  reference captions are preserved.
- No-priority sources keep the honest info notice; already-revised re-entry
  keeps the completed state and the bounded next-step actions; pending
  submit keeps the loading + disabled-button behavior.
- All session keys, button keys, navigation helpers, baseline/reliability
  logic, and validation behavior preserved.

### Practice (`app/ui/features/student/practice.py`)

- Keyed containers for the frozen surface recipes: target card
  (`practice_target_<id>`, L2), priority task block
  (`practice_priority_task`, L2), evidence blocks
  (`practice_evidence_priority_<id>` / `practice_evidence_attempt_<id>`,
  L3), exercise card (`practice_exercise_card`, L2), attempt-saved panel
  (`practice_attempt_saved_<id>`, L2).
- Evaluation unavailable now renders the frozen dashed neutral notice
  (`neutral_box(dashed=True)`), never error red.
- Legacy/unresolved provenance now renders an explicit dashed neutral
  notice (reusing the Journey wording keys `student_journey_practice_legacy`
  / `student_journey_practice_provenance_unresolved`) - no fabricated
  provenance.
- Active vs completed vs attempt-saved states remain distinct; completed
  activities remain reviewable (Return to Feedback / Open Learning Journey /
  explicit other active target); completion remains activity completion
  only.
- All session keys, button keys, target-selection stability, attempt/
  completion flows, and validation behavior preserved.

### Shared foundations (`app/ui/pixel_art.py`)

- Added the WU2 keyed-container selectors (revision source/priority/
  observation/next-action; practice target/priority/evidence/exercise/
  attempt-saved) scoped exactly like the WU1/Journey rules. Three selectors
  that had no live container were removed (no dead CSS).

### Documented limitation (AppTest framework artifact)

- The completed Practice panel intentionally renders flat (L1 surfaces)
  rather than inside a keyed container: any keyed container in the
  completed branch triggers a Streamlit AppTest tree-merge artifact (a
  removed button lingers in the element list after the Finish click),
  which breaks the frozen v0.9.7-B completion test. The real runtime is
  unaffected (the browser matrix verifies the completed state renders
  only Return to Feedback / Open Learning Journey); the design-system
  document is updated with this validated application rule/limitation.

## 4. Tests

| Suite | Result |
|---|---|
| Focused WU2 (`test_v097d_wu2_revision_practice.py`) | 39 passed / 0 failed |
| Focused WU2 + WU1 + design-system | 100 passed / 0 failed |
| Directly affected regression (v0.9.7-A/B/C focused suites) | 286 passed / 0 failed |
| v0.9.7-B WU5 completion suite (Practice finish flow) | 38 passed / 0 failed |
| Locale parity | en=600, zh=600, no missing/empty |
| compileall app tests | exit 0 |
| `git diff --check` (scoped app/tests/verification) | clean |
| No-migration check | no migration file; migration 13 unchanged |

Logs: `.agent-workflow/v0.9.7-d-controlled-rollout/logs/` (`wu2-orchestrator-*`).

## 5. Rendered matrix (real production stack, local provider, isolated DB)

`verification/v0.9.7-d/v0.9.7-d-wu2-20260806-r1/` - per combination
(en/zh x 1280x900/390x844, distinct learner): Revision default (real
submission seed), Practice active (real target + exercise via API), Practice
evaluation available (real attempt + evaluation), Practice evaluation
unavailable (persisted attempt without evaluation), Practice completed (real
completion), Practice legacy (legacy target via API).

| Check | Result |
|---|---|
| 6 states x 4 combinations = 24 state records | all PASS |
| Reload/re-render zero writes (whole-DB counts per state) | 24/24 true |
| Exceptions / console errors / page errors | 0 everywhere |
| Horizontal overflow | false everywhere |
| Raw locale keys | none |
| Forbidden wording after limitation normalization | none |
| Keyed-container computed surfaces (target/priority/evidence/exercise/attempt-saved) | verified on the real DOM |
| Dashed neutral notices (evaluation unavailable, legacy) | present, never error red |
| Bottom captures byte-distinct | 24/24 |
| Mobile touch targets | >= 44px (390x844 passes) |
| Scenario writes | expected API writes only (`zero_writes: false` with recorded deltas) |

Evidence: `rendered_wu2_matrix_evidence.json` (exit 0 on the final
orchestrator run) + screenshots under `screenshots/`.

## 6. Gate result: AMBER -> GREEN

The UI team delivered the implementation but could not execute the
verification (sandbox denied the project interpreter), and its initial
matrix/assertions contained several artifacts. The orchestrator verified
every claim directly and repaired:

1. A syntax error in `pixel_art.py` (broken f-string CSS block) - repaired;
   the file had not parsed before the orchestrator ran it.
2. Duplicate `practice_evidence` container keys crashing Practice renders -
   unique keys per block.
3. Missing legacy/unresolved provenance treatment - dashed neutral notice
   added.
4. Evaluation unavailable not using the dashed neutral recipe - fixed.
5. A frozen v0.9.7-B regression failure caused by a Streamlit AppTest
   tree-merge artifact when the completed branch used a keyed container -
   resolved by the documented flat completed-panel rule (section 3).
6. Matrix selector bugs (plain `.st-key-*` class selectors do not match
   suffixed keys; notice classes checked via `inner_text` instead of DOM
   locators) - fixed; the matrix was also extended from 2 to 6 states per
   combination and the scenario writes were made deterministic.

After the repairs the orchestrator independently re-ran the focused suites
(100 passed), the full affected regression (286 passed), the WU5 completion
suite (38 passed), the browser matrix (exit 0), locale parity, compileall,
and the scoped diff check. All WU2 acceptance criteria are satisfied.

## 7. Acceptance criteria (35/35)

1-3. Revision and Practice use the frozen design system and match
  Writing/Feedback/Journey - PASS (rendered + computed-style evidence).
4. Original/revision relationships clear - PASS (source-context card,
  read-only original text, "Revision of #n" captions preserved).
5. Feedback priority context accurate - PASS (priority task card with
  explanation/direction/evidence from the persisted context).
6. Practice provenance accurate - PASS (source submission caption +
  legacy/unresolved dashed notices; nothing fabricated).
7-8. Active and attempted Practice states clear - PASS (badges/notices,
  attempt-saved panel with saved response).
9. Evaluation available clear - PASS (evaluation status rows).
10. Evaluation unavailable honest - PASS (dashed neutral notice; not error).
11. Completed Practice is activity completion only - PASS (wording frozen).
12. Completed activities remain reviewable - PASS (Return to Feedback /
  Open Learning Journey / other active target).
13. Legacy/unresolved never fabricate provenance - PASS (dashed notices).
14. Stable target selection correct - PASS (preset/session-stable rules
  preserved; matrix re-entry stable).
15-18. No duplicate target/exercise/attempt/evaluation - PASS (creation
  flows unchanged; write-count evidence; regression suites).
19. Learner isolation - PASS (regression + distinct learners per combo).
20-21. Revision and Practice rendering cause no unintended writes - PASS
  (24/24 reload zero-writes).
22-25. en/zh desktop + mobile smoke pass - PASS (4 combinations).
26-27. No remote resources; no raw locale keys - PASS.
28. No horizontal overflow - PASS. 29. No console/page errors - PASS.
30. Focused tests pass - PASS (39 + 100 combined).
31. Directly affected regression passes - PASS (286 + WU5 38).
32. No migration added - PASS. 33. Protected files untouched - PASS
  (section 10).
34. MiniMax design review passes - PASS (plan + rendered-state review;
  the documented completed-panel limitation is an implementation
  constraint, not a design deviation).
35. DeepSeek global contract review passes - PASS (owner-goal sections 7-8
  contracts unchanged; this report).

## 8. Midpoint integration checkpoint (11.10)

- WU1 + WU2 focused tests: 100 passed / 0 failed.
- Directly affected Student regression: 286 passed / 0 failed (+ WU5 38).
- Full-cycle rendered smoke basis: WU1 matrix (Writing/Feedback real
  renders) + WU2 matrix (Revision/Practice real renders) + design-system
  suite (Journey) - all green; the complete five-page browser flow is
  exercised end-to-end in WU4.
- Journey/Practice write-count checks: 24/24 reload zero-writes (WU2);
  WU1 matrix zero-writes; whole-DB counts recorded.
- Locale parity 600/600; `git diff --check` clean.
- Result: GREEN - WU3 may start.

## 9. Commits

1. `feat(v0.9.7-d): consolidate Student Revision and Practice interfaces`
2. `test(v0.9.7-d): verify Revision and Practice rollout`
3. `docs(v0.9.7-d): close work unit 2`

Ending HEAD: the WU2 closure commit (hash in section 12).

## 10. Protected and user-owned files

`AGENTS.md`, `.claude/`, `CLAUDE.md`, `RUN_VERIFICATION_V0.7.md`,
`RUN_VERIFICATION_V0.8.2.md`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`,
`data/demo_journey_manifest.json`, `diagnostics/`, and the v0.9.7-a run
logs were never modified, staged, or committed. No push or pull request.

## 11. Defects and remediation

One product defect found and fixed (duplicate `practice_evidence` keys),
one integration defect fixed (pixel_art.py syntax error), one frozen-state
gap fixed (legacy provenance + dashed evaluation notices), one framework
artifact documented with a validated application rule (completed panel
flat). All re-verified by the orchestrator directly.

## 12. Next Work Unit boundary

WU2 is GREEN. WU3 (Cross-Page Student UI Consolidation) may start.
