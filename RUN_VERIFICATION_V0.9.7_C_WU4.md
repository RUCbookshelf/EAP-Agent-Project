# v0.9.7-C Work Unit 4 - Final Verification and v0.9.7-C Release Closure

**Status:** COMPLETE - all 36 WU4 acceptance criteria satisfied (GREEN);
**v0.9.7-C is complete, verified, and closed**; the next planned phase is
v0.9.7-D (not started).
**Date:** 2026-08-05
**Governing protocol:** the owner-provided v0.9.7-C goal (WU4 section) and
`docs/development/V0.9.7_C_SPEC.md`.

## 1. Baseline

- Branch `master`; pre-WU4 HEAD `8c6a277` (WU3 closure). Worktree before
  WU4: only preserved user-owned entries + pre-existing run logs.
- Migration 13; config-v0.9.0; locale parity 600/600 before WU4.

## 2. WU4 deliverable

- `tests/test_v097c_wu4_release.py` (new, 8 release tests): complete
  cycle groups once with safe actions; raw-event contract intact; repeated
  completion creates no duplicates/writes; evaluation-unavailable honest;
  learner isolation; repeated reads/re-entry deterministic; independent
  cycles separate; one completed + one active target.
- Final end-to-end matrix: `verification/v0.9.7-c/v0.9.7-c-wu4-20260805-r1/
  w4_final_matrix.py` (full UI path x 4 combinations + grouped-cycle and
  action-navigation verification) and `w4_research_smoke.py`.
- No production code change was required (verification-first unit; no
  release blocker found).

## 3. Final end-to-end scenario (12.2)

Per combination (fresh isolated DB, distinct learner, local provider):
Writing -> Feedback priority -> linked Revision submit -> explicit
revision completion -> Open Practice -> focused task -> empty validation ->
valid attempt -> evaluation -> Finish This Practice Cycle -> COMPLETED
(column + JSON) -> reload re-entry -> second active target -> Open Learning
Journey -> grouped writing cycle verified -> Revision relationship ->
Practice relationship and completion -> safe Journey destinations (Open
Practice for the active target; Open Revision for the source) -> reload
and re-enter -> no duplicates, no writes.

## 4. Required scenarios (12.3)

- Complete priority-guided cycle: PASS (grouped once, completed state).
- Evaluation unavailable: PASS (WU1/WU2/WU4 suites + WU3 matrix).
- No priority: PASS. Insufficient evidence: PASS.
- Two independent essays: PASS. Linked revision: PASS. Multiple revisions:
  PASS (WU1 chain test).
- Multiple Practice targets: PASS. One active + one completed target:
  PASS (matrix + release tests).
- Legacy Practice: PASS (no fabricated provenance).
- Stale reference: PASS (fail-safe guards).
- Learner isolation: PASS. Empty Journey: PASS.
- Research baseline: PASS (6/6 smoke).

## 5. Final matrix (12.4)

| Combination | Full UI cycle | Grouped Journey | Actions | Reload | Zero writes |
|---|---|---|---|---|---|
| en 1280x900 | PASS | PASS | PASS | PASS | PASS |
| zh_CN 1280x900 | PASS | PASS | PASS | PASS | PASS |
| en 390x844 | PASS | PASS | PASS (>=44px) | PASS | PASS |
| zh_CN 390x844 | PASS | PASS | PASS (>=44px) | PASS | PASS |

0 console errors, 0 page errors, 0 remote requests, no overflow, no raw
keys, no unsupported learning claims (fixed disclaimer wording asserted as
the only occurrences), whole-database counts unchanged across all Journey
renders, reloads, and action navigation. Evidence:
`rendered_page_matrix_evidence.json` + 36 screenshots (7 smoke-run debug
screenshots dropped in a chore commit, matching the WU5 precedent).

## 6. Automated release gates (12.5)

- Focused v0.9.7-C: WU1 29 + WU2 17 + WU3 21 + WU4 8 = **75 passed**.
- Combined continuity (WU1-WU4 + v0.9.7-B WU2-WU6 + Journey + contracts):
  **510 passed / 0 failed / exit 0** (`C:\tmp\wu4-affected\affected_final.txt`).
- Full non-live core (canonical env: PYTHONUTF8=1, PYTHON_DOTENV_DISABLED=1,
  LLM_PROVIDER=local, fresh isolated DATABASE_PATH, DATABASE_URL removed,
  33-entry SERVICE_API_DIFF_ALLOWLIST, `--ignore=tests/live`):
  **1132 passed / 8 skipped / 0 failed / 4 warnings / exit 0**
  (`C:\tmp\wu4-fullcore\full_core_final_output.txt`; 1057 baseline + 75
  v0.9.7-C tests).
- Launcher: `cmd /c "run.bat --verify"` **PASS twice** (exit 0):
  health/docs/streamlit 200/200/200, migration 13, config-v0.9.0, isolated
  auto-provisioned DB, no live provider call
  (`C:\tmp\wu4-launcher\launcher_run1.txt`, `launcher_run2.txt`).
- Locale parity: **600/600**, no missing/empty values (measured).
- Research smoke: established v0.9.4-B subset (Overview, Data, System
  Audit x en desktop / zh mobile) **6/6 PASS**, 0 exceptions/overflow/raw
  keys (`research_smoke_evidence.json`).
- Static: `compileall` OK; `git diff --check c4fba8b..HEAD` clean.

## 7. Fresh-index impact review (12.5)

- Index refreshed with `node .gitnexus/run.cjs analyze` against the final
  WU4 implementation tree (HEAD `5d950dc`): "Repository indexed
  successfully (12.1s)"; 11,184 nodes, 19,432 edges, 324 clusters, 272
  flows; `.gitnexus/meta.json` records lastCommit `5d950dc`, indexedAt
  2026-08-05T11:44:14Z. (FTS extension unavailable - search disabled;
  index build otherwise complete.)
- `gitnexus detect-changes -s compare -b c4fba8b` from a clean detached
  worktree at `5d950dc`: **29 parseable files / 454 changed symbols / 205
  affected processes**. The v0.9.7-C production delta is limited to
  `app/journey/cycles.py` (new), `app/journey/service.py` (one read +
  additive response keys), `app/ui/features/student/{journey,navigation,
  practice,revision}.py` (grouped renderer, navigation helpers, fail-safe
  guards), and `locales/*`; everything else is tests/evidence/docs. The
  graph's "critical" risk heuristic reflects fan-out through shared
  browser/page helpers (same pattern as v0.9.7-B); no architecture-boundary
  violation and no unexplained fan-out - corroborated by the 1132-test full
  core and the direct diff review.

## 8. Release-blocker handling (12.6)

No RED result; no release blocker found; no production fix was required in
WU4 (the only production defect found in v0.9.7-C was the pre-existing
missing `render_api_error` import in the Journey page, fixed and covered in
WU3).

## 9. WU4 acceptance criteria

1. WU1-WU3 criteria remain satisfied - PASS (all suites green).
2-5. Full cycle, multiple cycles, revision and Practice relationships
  group correctly - PASS.
6. Completion remains activity completion only - PASS.
7. Evaluation unavailable honest - PASS.
8-9. Journey reads and navigation side-effect free - PASS (whole-DB
  counts).
10-11. No duplicate raw events or cycles - PASS.
12. No uncontrolled target/exercise/attempt/evaluation - PASS.
13-14. Learner isolation and stale-reference safety - PASS.
15-17. Legacy, no-priority, insufficient-evidence paths pass - PASS.
18. All four final matrix combinations pass - PASS.
19-20. Focused v0.9.7-C (75) and v0.9.7-B continuity pass - PASS (510).
21. Affected regression passes - PASS (510; includes all continuity).
22. Full non-live core passes - PASS (1132/8).
23. Launcher passes - PASS (twice).
24. Locale parity passes - PASS (600/600).
25. Research smoke passes - PASS (6/6).
26. Fresh-index impact review passes - PASS (GitNexus, indexed at the
  final tree; production delta scoped and documented).
27. No unexplained production fan-out - PASS.
28. `git diff --check` clean - PASS.
29. No unrelated changes - PASS (diff review).
30. No migration introduced - PASS (13 unchanged).
31. User-owned files untouched - PASS (section 12).
32. Reports and state documents agree - PASS.
33. No unresolved release blocker - PASS.
34. v0.9.7-C explicitly marked complete, verified, and closed - PASS.
35. v0.9.7-D identified only as next - PASS.
36. No push or pull request - PASS.

## 10. Commits

- `5526b57` `test(v0.9.7-c): add final Student Journey matrix evidence`
  - tests/test_v097c_wu4_release.py (new, 8 tests) + the WU4 matrix and
    research-smoke scripts/evidence/screenshots.
- `5d950dc` `chore(v0.9.7-c): drop WU4 debug screenshots`
  - 7 smoke-run debug screenshots removed from the run directory (moved
    to local trash; recoverable).
- Closure commit (section 13): `docs(v0.9.7-c): close Student Journey
  functional completion`.

No push or pull request was opened (not instructed).

## 11. Known limitations and deferred work

- The Journey timeline's fixed no-priority description and the
  `all_descriptive` disclaimer contain "passed the Diagnostic Gate" and
  "stable transfer" wording; these are conservative gate/limitation
  statements, not learner claims (asserted as the only occurrences).
- v0.9.7-D (next): Student UI/UX consolidation; v0.9.7-E: responsive,
  mobile, and accessibility refinement. Also deferred: repository-wide
  malformed-row repair (G9), API-level exercise-instance idempotency (G10).
- GitNexus FTS search extension unavailable (index build complete); vision
  sidecar unavailable for screenshot inspection (DOM/text/write-count
  evidence is the basis; screenshots retained for the owner).

## 12. User-owned files

`AGENTS.md`, `.claude/`, `CLAUDE.md`, `RUN_VERIFICATION_V0.7.md`,
`RUN_VERIFICATION_V0.8.2.md`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`,
and `data/demo_journey_manifest.json` were never modified, staged,
committed, or deleted by v0.9.7-C.

## 13. Final Git state

- Closure commit: `docs(v0.9.7-c): close Student Journey functional
  completion` (exact hash recorded in the final chat report).
- Final release HEAD: the closure commit on `master`; implementation tree
  HEAD before closure was `5d950dc`.
- `git status --short` after closure: only the preserved user-owned
  entries (modified `AGENTS.md`, `RUN_VERIFICATION_V0.7.md`,
  `RUN_VERIFICATION_V0.8.2.md`; untracked `.claude/`, `CLAUDE.md`,
  `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`, `data/demo_journey_manifest.json`,
  pre-existing v0.9.7-a run logs) plus gitignored WU4 run logs/isolated DB.

## 14. Gate result

**GREEN** - all 36 WU4 acceptance criteria satisfied; v0.9.7-C is complete,
verified, and closed; the next planned phase is v0.9.7-D (not started).
