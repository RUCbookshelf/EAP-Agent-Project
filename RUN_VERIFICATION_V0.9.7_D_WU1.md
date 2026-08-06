# v0.9.7-D Work Unit 1 - Writing and Feedback Consolidation

**Status:** COMPLETE (GREEN) - the frozen Student design system is applied
to the Writing and Feedback pages; all 28 WU1 acceptance criteria satisfied.
**Date:** 2026-08-06
**Governing protocol:** the owner-provided v0.9.7-D goal (WU1 section) and
`docs/development/V0.9.7_D_STUDENT_DESIGN_SYSTEM.md` (frozen source of truth;
Journey = reference implementation).

## 1. Baseline

- Branch `master`; starting HEAD `c69cf51` (design-system freeze closure).
- Worktree at WU1 start: only preserved user-owned entries
  (`AGENTS.md`, `RUN_VERIFICATION_V0.7.md`, `RUN_VERIFICATION_V0.8.2.md`
  modified; `.claude/`, `CLAUDE.md`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`,
  `data/demo_journey_manifest.json`, `diagnostics/`, v0.9.7-a run logs
  untracked) plus the new `.agent-workflow/` orchestrator session.
- Migration 13; config-v0.9.0; locale parity baseline 600/600.

## 2. Model routing and nested calls

- Global orchestrator: deepseek-v4-flash contract (this session) - baseline
  verification, task packets, gate, parent verification.
- UI lead: `opencode-go/minimax-m3` (agent 019fd63e-46a7-7b51-940a-8970f50f25fa):
  interpreted the frozen system and produced the WU1 application plan
  (`.agent-workflow/v0.9.7-d-controlled-rollout/findings_wu1_ui_lead.md`).
- UI implementation executor: nested `opencode-go/mimo-v2.5` (via the UI
  lead; handoff `.agent-workflow/.../handoffs/wu1-executor-handoff.md`).
- Repairs 1-3: `opencode-go/mimo-v2.5` engineering executors
  (019fd684-1ae6-7b11-a86b-55b862ecba27, 019fd6cf-e423-7cc3-b39d-b3917edd1ee6)
  for the gate findings below.
- Final authoritative verification: run directly by the orchestrator
  (focused suites, affected regression, matrix re-run, static checks).

## 3. Implemented scope

### Writing (`app/ui/features/student/writing.py`)

- Saved-success panel wrapped in the L2 keyed container
  `st.container(border=True, key="writing_saved_panel")` so the frozen
  `st-key-writing_saved_` card recipe (2px ink border, shadow-sm, 20px pad)
  applies; the panel keeps learner + prompt context, success notice,
  complete-state action block, submission reference caption, and the single
  primary Review Feedback action.
- Limitation disclaimer footer (`all_descriptive`) added after the submit
  block, matching the Journey reference composition.
- All session keys, button keys, submission/reliability/validation logic,
  navigation helpers, and business behavior preserved unchanged.

### Feedback (`app/ui/features/student/feedback.py`)

- Keyed containers for the frozen surface recipes:
  `feedback_priority_<index>` (L2 card), `feedback_evidence_<index>`
  (L3 evidence block), `feedback_next_action` (focused next-step block) in
  both priority and no-priority branches.
- Direct student-text evidence (`evidence_quote`) rendered verbatim in the
  L3 block BEFORE the diagnosis explanation inside each priority card;
  evidence, diagnosis, and suggested action are visually distinct.
- Priority card title lightened to the `.px-card-title` role
  (`app/ui/components.py`): the action red is reserved for primary CTAs;
  the priority is prominent but never score-like (no numeric badge, no
  pass/fail, no grade).
- Exactly one primary action per view; per-priority Practice actions stay
  secondary; no-priority renders the neutral empty state + primary Revise +
  secondary Finish; insufficient-evidence stays neutral (never error red).
- All session keys, button keys, navigation helpers, and business behavior
  preserved unchanged.

### Shared foundations (`app/ui/pixel_art.py`)

- Four keyed-container CSS rules added, scoped exactly like the Journey
  rules (never hashed): `st-key-writing_saved_` (L2), `st-key-feedback_
  priority_` (L2), `st-key-feedback_evidence_` (L3), `st-key-feedback_
  next_action_` (focused). No new tokens, no global CSS, no new geometry.

### Verification artifacts (new)

- `tests/test_v097d_wu1_writing_feedback.py` (39 focused tests).
- `verification/v0.9.7-d/v0.9.7-d-wu1-20260806-r1/`:
  `wu1_browser_matrix.py`, `rendered_wu1_matrix_evidence.json`, screenshots.

## 4. Tests

| Suite | Result |
|---|---|
| Focused WU1 (`test_v097d_wu1_writing_feedback.py`) | 39 passed / 0 failed |
| Focused WU1 + design-system (`+ test_v097d_design_system.py`) | 63 passed / 0 failed |
| Directly affected regression (v0.9.7-A/B/C focused suites) | 286 passed / 0 failed |
| Locale parity | en=600, zh=600, no missing/empty values |
| compileall app | exit 0 |
| `git diff --check` (scoped app/tests/locales) | clean (only the preserved user-owned AGENTS.md has pre-existing trailing whitespace) |
| No-migration check | no migration file added; migration 13 unchanged |

Logs: `.agent-workflow/v0.9.7-d-controlled-rollout/logs/` (`wu1-focused.txt`,
`wu1-regression.txt`, `wu1-orchestrator-*`).

## 5. Rendered matrix (real production stack, local provider, isolated DB)

Per combination (en/zh x 1280x900/390x844, distinct seeded learner):
Writing default, Writing saved-success (real UI submit), Feedback priority,
Feedback no-priority (real UI submit), Feedback no-session.

| Check | Result |
|---|---|
| Writing default: 3 section headers, 4px/2px page-title rule, one primary | PASS (all 4 combos) |
| Writing saved: L2 keyed panel with 2px border + shadow, primary Review Feedback | PASS (all 4) |
| Feedback priority: L2 priority cards + L3 evidence containers (computed styles), verbatim evidence quote visible (3 quotes), exactly one primary, per-priority secondary Practice | PASS (all 4) |
| Feedback no-priority: neutral empty state (no error styling), one primary Revise, secondary Finish, no Practice landing | PASS (all 4) |
| Feedback no-session: empty state, no errors | PASS (all 4) |
| No horizontal overflow, no raw locale keys, no console/page errors, no remote requests, no unsupported claims after limitation normalization | PASS (all 4) |
| Reload/re-render zero writes (whole-DB counts unchanged per state) | PASS (20/20 states) |
| Scenario writes: exactly the expected essay rows from the two real UI submits per combination | PASS (db_essays_delta=1 per submit, no unexpected table deltas) |

Evidence: `rendered_wu1_matrix_evidence.json` (exit 0 on the final
orchestrator re-run), screenshots under `verification/v0.9.7-d/
v0.9.7-d-wu1-20260806-r1/screenshots/`.

## 6. Gate result: AMBER -> GREEN

Initial UI-team delivery was evaluated AMBER by the orchestrator:

1. `st-key-writing_saved_` CSS rule was dead code (saved panel not wrapped)
   - fixed by Repair-1 (keyed container wired; no behavior change).
2. Browser matrix covered only Writing default + Feedback no-session -
   fixed by Repair-1/2 (5 states per combination on the real DOM).
3. Zero-write evidence was not render-scoped - fixed by Repair-2
   (per-state reload whole-DB zero-write checks; expected scenario writes
   recorded and asserted separately).
4. Evidence-recording artifacts (post-reload `evidence_quotes_visible`,
   provider disclaimer sentence tripping the forbidden-word check) - fixed
   by Repair-3 (pre-reload measurement; limitation-normalization list
   extended with the exact rendered disclaimer sentences; recording
   fields completed for all states).

After the repairs, the orchestrator independently re-ran the matrix
(exit 0), the focused suites (63 passed), the affected regression
(286 passed), locale parity (600/600), compileall (exit 0), and the scoped
diff check (clean). No rendering defect was found in the implementation;
all findings were verification-evidence artifacts.

## 7. Acceptance criteria (28/28)

1-3. Writing and Feedback use the frozen design language and look like one
  product - PASS (rendered + computed-style evidence).
4. Writing remains the dominant task surface - PASS (no cards around every
  control; form controls unchanged; sectioned by task/prompt/draft).
5. Submit action hierarchy clear - PASS (one primary; action block).
6. Evidence distinguished from interpretation - PASS (L3 quote block
  verbatim before the diagnosis; distinct surfaces).
7. Priority prominent but not score-like - PASS (`.px-card-title`, no
  numeric/grade semantics; action red reserved).
8. No-priority honest - PASS (neutral empty state; explicit copy).
9. Insufficient evidence honest - PASS (neutral notice; never error red).
10-11. Existing Writing/Feedback behavior unchanged - PASS (session keys,
  button keys, helpers, submission/reliability/validation logic preserved;
  focused + regression suites).
12. Supported navigation correct - PASS (Review Feedback, Open Revision,
  per-priority Practice, Revise This Draft, Finish Cycle all verified).
13. Unsupported navigation not fabricated - PASS (no Practice landing CTA;
  asserted).
14-17. en/zh desktop + mobile smoke pass - PASS (all 4 combinations).
18. No remote UI resource - PASS (0 remote requests per state).
19. No raw locale key - PASS (empty raw-key lists).
20. No horizontal overflow - PASS (overflow false per state).
21. No console/page error - PASS (empty lists; 0 exceptions).
22. No unintended database write - PASS (20/20 reload zero-writes;
  expected scenario writes only).
23. Focused tests pass - PASS (39).
24. Directly affected regression passes - PASS (286 + design-system).
25. No migration added - PASS.
26. Protected files untouched - PASS (section 9).
27. MiniMax design review passes - PASS (plan + rendered-state review in
  the UI-lead findings; the plan's application rules match the frozen
  contract; rendered states verified on the real DOM).
28. DeepSeek global contract review passes - PASS (this report; owner-goal
  sections 7-8 contracts unchanged; no unsupported claims).

## 8. Commits

1. `feat(v0.9.7-d): consolidate Student Writing and Feedback interfaces`
2. `test(v0.9.7-d): verify Writing and Feedback rollout`
3. `docs(v0.9.7-d): close work unit 1`

Ending HEAD: the WU1 closure commit (hash in section 11).

## 9. Protected and user-owned files

`AGENTS.md`, `.claude/`, `CLAUDE.md`, `RUN_VERIFICATION_V0.7.md`,
`RUN_VERIFICATION_V0.8.2.md`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`,
`data/demo_journey_manifest.json`, `diagnostics/`, and the v0.9.7-a run
logs were never modified, staged, or committed. No push or pull request.

## 10. Defects and remediation

No production defect found in the implementation. Four verification-evidence
gaps were repaired (section 6); all repaired and re-verified by the
orchestrator directly.

## 11. Next Work Unit boundary

WU1 is GREEN. WU2 (Revision and Practice Consolidation) may start.
