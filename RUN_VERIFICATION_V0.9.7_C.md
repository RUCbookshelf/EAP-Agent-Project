# v0.9.7-C Aggregate Release Verification - Student Journey Functional Completion

**Status:** COMPLETE, VERIFIED, AND CLOSED - WU1-WU4 complete; the next
planned phase is v0.9.7-D (not started).
**Date:** 2026-08-05
**Final release HEAD:** the closure commit `docs(v0.9.7-c): close Student
Journey functional completion` on `master` (exact hash recorded in the
final chat report).

## 1. v0.9.7-C goal

Transform the technically accurate raw Journey event projection into a
student-understandable, cycle-based, actionable Learning Journey:
learner-owned writing-cycle grouping, honest stage and activity states,
accurate Writing/Feedback/Revision/Practice relationships, safe explicit
navigation to existing records, persistence-backed re-entry - without
mastery, proficiency, CEFR, learning-gain, causal, or automatic-sequencing
claims.

## 2. WU1-WU4 summary

- **WU1** (cycle model + completion state): `app/journey/cycles.py`
  learner-owned read-time cycle view (writing cycles, revision-root
  resolution, feedback stages, Practice activities with validated priority
  provenance, activity/completion states, raw-order chronology); additive
  `cycles`/`cycles_version` response keys; one additive projection read
  (`list_exercise_instances`). Focused 29.
- **WU2** (safe navigation): `available_actions` descriptors
  (open_revision/open_practice, stable references only), navigation
  helpers, fail-safe destination guards on Revision and Practice pages
  (stale/cross-learner presets render honest notes), 2 locale keys.
  Focused 17.
- **WU3** (functional UI closure): grouped cycle rendering on the Journey
  page (cycle cards, original/revision distinction, feedback/priority,
  Practice states, safe action buttons, honest empty/error/legacy
  handling); 26 locale keys (600/600 parity); fixed the pre-existing
  missing `render_api_error` import. Focused 21.
- **WU4** (final verification + closure): 8 release tests, full UI
  end-to-end matrix (4 combinations), Research smoke, full release gates,
  fresh-index impact review, release-state reconciliation and closure.
  Focused 8.

## 3. Final architecture

- Raw projection: unchanged (12 event types, dedup keys, ordering,
  read-time, learner-scoped).
- Cycle view: `JourneyService.get_journey` returns the raw response plus
  additive `cycles` (JourneyCycle[]) and `cycles_version`
  (`journey-cycle-v0.9.7-c`); cycles are derived from the same persisted
  records in the same read pass - no writes, no persistence, no migration.
- Grouping: anchor = resolved root submission through persisted revision
  linkage; broken chains form controlled unlinked cycles; Practice
  attaches via the target's source submission with validated priority
  provenance (valid/legacy/unresolved, never fabricated).
- States: writing (submitted/analyzed/feedback_available/
  feedback_without_priority/insufficient_evidence/revision_submitted) and
  practice (available/attempted/evaluation_available/
  evaluation_unavailable/completed/unavailable) describe persisted
  activity only.
- Navigation: cycle actions carry stable references; destinations validate
  learner ownership; stale/cross-learner references fail safely with
  honest notes; navigation never writes and never creates records; target
  selection stays stable across reruns.
- UI: grouped cycle rendering with honest completion wording and safe
  actions; the raw undifferentiated timeline is no longer the primary view
  when grouping data exists (defensive fallback retained).

## 4. Verification results

- Focused: WU1 29, WU2 17, WU3 21, WU4 8 (v0.9.7-C total 75).
- Combined continuity (WU1-WU4 + v0.9.7-B WU2-WU6 + Journey + contracts):
  510 passed / 0 failed.
- Full non-live core (canonical env, 33-entry allowlist):
  **1132 passed / 8 skipped / 0 failed / exit 0**.
- `run.bat --verify`: PASS twice (200/200/200; migration 13;
  config-v0.9.0; isolated temp DB).
- Final matrix: EN/ZH x 1280x900/390x844 full UI end-to-end cycles with
  grouped-Journey verification - all PASS, 0 console/page errors, 0
  remote requests, no overflow/raw keys, mobile controls >= 44px, zero
  writes, no unsupported learning claims.
- Locale parity: 600/600; Research smoke: 6/6.
- Fresh-index impact review: GitNexus indexed at the final implementation
  tree (11,184 nodes; lastCommit `5d950dc`); detect-changes from the
  v0.9.7-C baseline: 29 files / 454 symbols / 205 affected processes;
  production delta limited to the cycle model, service read surface, four
  student UI files, and locales.
- `git diff --check c4fba8b..HEAD`: clean; no migration 14; no new raw
  event; no push/pull request.

## 5. Migration decision

**No migration.** The cycle view, states, provenance validation, and
navigation are derived entirely from existing persisted records
(migration 13 unchanged).

## 6. Known limitations

- Fixed conservative copy on the Journey page mentions "passed the
  Diagnostic Gate" (no-priority description) and "stable transfer"
  (all-descriptive disclaimer); these are gate/limitation statements, not
  learner claims.
- Repository-wide malformed-row repair (G9) and API-level exercise-instance
  idempotency (G10) remain deferred.
- GitNexus FTS search extension unavailable; vision sidecar unavailable
  (DOM/text/write-count evidence is the basis; screenshots retained).

## 7. Deferred v0.9.7-D/E work

- v0.9.7-D (next): Student UI/UX consolidation.
- v0.9.7-E: responsive, mobile, and accessibility refinement.

## 8. Detailed reports and evidence

- `RUN_VERIFICATION_V0.9.7_C_WU1.md`, `RUN_VERIFICATION_V0.9.7_C_WU2.md`,
  `RUN_VERIFICATION_V0.9.7_C_WU3.md`, `RUN_VERIFICATION_V0.9.7_C_WU4.md`.
- Living spec: `docs/development/V0.9.7_C_SPEC.md`.
- Matrix evidence: `verification/v0.9.7-c/v0.9.7-c-wu2-20260805-r1/`,
  `verification/v0.9.7-c/v0.9.7-c-wu3-20260805-r1/`,
  `verification/v0.9.7-c/v0.9.7-c-wu4-20260805-r1/`.
- Test logs: `C:\tmp\wu4-affected\affected_final.txt`,
  `C:\tmp\wu4-fullcore\full_core_final_output.txt`,
  `C:\tmp\wu4-launcher\launcher_run1.txt`, `launcher_run2.txt`,
  `C:\tmp\wu4-impact\detect_changes_clean.txt`.

## 9. Final decision

All WU1-WU4 acceptance criteria are satisfied; no release blocker remains;
user-owned files remain untouched and uncommitted; no push or pull request
was performed.

> **v0.9.7-C is complete, verified, and closed. Student Journey now
> presents the verified learning record as coherent, learner-owned writing
> and Practice cycles with honest activity states and safe navigation. The
> next planned phase is v0.9.7-D.**
