# v0.9.7-B Aggregate Release Verification - Priority-to-Practice Target Generation and Practice Workflow

**Status:** COMPLETE, VERIFIED, AND CLOSED - WU1-WU6 complete; the next
planned phase is v0.9.7-C (not started).
**Date:** 2026-08-05
**Final release HEAD:** the closure commit `docs(v0.9.7-b): close
priority-guided practice cycle` on `master` (exact hash recorded in the
final chat report).

## 1. v0.9.7-B goal

Complete the learning loop from a persisted Feedback priority to a
traceable Practice target, a focused and reliably persisted Practice
attempt, honest formative evaluation, an explicit completion state, safe
re-entry, and an accurate existing Journey projection - without mastery,
proficiency, CEFR, learning-gain, or causal claims.

## 2. WU1-WU6 summary

- **WU1** (audit + protocol): practice-workflow audit and frozen SPEC
  (`docs/development/V0.9.7_B_PRACTICE_WORKFLOW_AUDIT.md`,
  `docs/development/V0.9.7_B_SPEC.md`).
- **WU2** (mapping + provenance): production priority-to-practice mapping
  with the stable `PRIO-{feedback_id}-{priority_index}` reference,
  category map, provenance forwarding, and ownership/source validation;
  focused 76.
- **WU3** (idempotent creation/reuse): prefix-safe allocator repair,
  create-or-reuse on the logical key, migration 13 (additive partial
  unique index), unified ownership validation; focused 33.
- **WU4** (focused task + attempt loop): entry intents from
  Feedback/Revision, read-only priority-context resolver, one seeded
  exercise, ownership-validated pending-guarded attempt persistence,
  saved-state recovery; focused 32.
- **WU5** (evaluation + completion): learner-owned evaluation read path
  with available/unavailable/malformed states, explicit idempotent
  ACTIVE -> COMPLETED transition (code-only enum, JSON-only `updated_at`,
  no migration 14), persistence-backed completed-state re-entry, bounded
  next steps; focused 38.
- **WU6** (Journey verification + release closure): read-time Journey
  projection verified for the complete cycle (no new events on
  completion; provenance, dedup, ordering, side-effect-free reads, legacy
  and evaluation-unavailable honesty), final EN/ZH x desktop/mobile matrix,
  full release gates, metadata reconciliation, and closure; focused 18.

## 3. Final implemented workflow

```text
Writing Submission
-> Structured Feedback
-> Persisted Feedback Priority
-> Priority-Guided Revision (linked submission)
-> Explicit Revision Completion
-> Priority-Derived Practice Target (create-or-reuse, one per key)
-> Focused Practice Exercise (seeded from the evidence quote)
-> Persisted Practice Attempt (one per explicit submit)
-> Formative Evaluation or Honest Unavailable State
-> Explicit Practice-Cycle Completion (ACTIVE -> COMPLETED, terminal)
-> Bounded Post-Practice Navigation (Feedback / Journey / other active
   target, explicit only)
-> Existing Learning Journey Projection (read-time, accurate, no writes)
```

## 4. Migration history relevant to v0.9.7-B

- Migration 12: Practice persistence tables (pre-existing).
- Migration 13 (WU3): additive partial unique index
  `ux_practice_targets_active_priority_key` (ACTIVE targets, non-NULL
  persisted priority key); one-step rollback; existing rows preserved.
- **No migration 14** (WU5/WU6 decision): completion uses the existing
  `status` TEXT column + `target_json` (+ JSON-only `updated_at`).

## 5. Final API/service/UI changes (high level)

- API surface: 80 GET/POST routes (78 -> 80 in WU5: learner-owned
  evaluation read endpoint + completion endpoint; WU4 added the read-only
  target-context endpoint); 56 client methods.
- Services: `app/practice/mapping.py`, `target_creation.py`,
  `task_context.py`, `evaluations.py`, `completion.py`; atomic conditional
  status update in the repository; canonical allowlist 32 entries.
- UI: Feedback per-priority and Revision-completion entry intents;
  focused Practice task with priority context; pending-guarded submission;
  evaluation available/unavailable views; completed state with bounded
  next steps; stable learner-scoped target selection.
- Journey: **unchanged** (verification only; no new event types).

## 6. Final test and matrix results

- Focused: WU2 76, WU3 33, WU4 32, WU5 38, WU6 18 (combined WU2-WU6
  **197 passed**).
- Affected regression: **569 passed / 0 failed / exit 0**.
- Full non-live core (canonical env): **1057 passed / 8 skipped / 0 failed
  / exit 0**.
- `run.bat --verify`: **PASS twice** (200/200/200; migration 13;
  config-v0.9.0; isolated temp DB).
- Rendered matrix: EN/ZH x 1280x900/390x844 main cycles + evaluation-
  unavailable, no-priority, and legacy scenarios: **all PASS**, 0 console/
  page errors, 0 remote requests, no overflow/raw keys, mobile controls
  >= 44px, no mastery wording, Journey event count unchanged by
  completion, Journey navigation writes nothing.
- Locale parity: 572/572; Research smoke: 6/6.
- Fresh-index impact review (GitNexus, index at the final implementation
  tree): 90 changed symbols - all WU6 verification/test/docs; 0 production
  symbols; no unexpected fan-out in production code.

## 7. Known limitations

- Malformed `*_json` rows on a tampered database raise a stable
  repository-level read error on the Journey path (audit G9); not
  reachable through the verified product path; repair deferred.
- `practice_targets` has no relational `updated_at` column (completion
  timestamp in `target_json`).
- GitNexus FTS search extension unavailable; CRG MCP transport unavailable
  (CLI used). Vision sidecar unavailable for screenshot inspection.
- The Journey timeline's fixed `feedback_without_priority` description
  contains "no priority passed the Diagnostic Gate" (gate description, not
  a learner-pass claim).
- Pre-existing readiness-gate timing flake documented in WU2/WU3; not
  observed in WU6 runs.

## 8. Deferred scope

- v0.9.7-C (next planned): Student Journey functional completion
  (e.g., target-completed event/state extension, Journey chronology).
- v0.9.7-D: Student UI/UX consolidation; v0.9.7-E: responsive, mobile, and
  accessibility refinement.
- Later/other: repository-wide malformed-row repair (G9), API-level
  exercise-instance idempotency (G10), mastery/adaptive/CEFR/LLM-evaluation
  work.

## 9. Detailed reports and evidence

- `RUN_VERIFICATION_V0.9.7_B_WU2.md`, `RUN_VERIFICATION_V0.9.7_B_WU3.md`,
  `RUN_VERIFICATION_V0.9.7_B_WU4.md`, `RUN_VERIFICATION_V0.9.7_B_WU5.md`,
  `RUN_VERIFICATION_V0.9.7_B_WU6.md`.
- Matrix evidence: `verification/v0.9.7-b/v0.9.7-b-wu4-20260805-r1/`,
  `verification/v0.9.7-b/v0.9.7-b-wu5-20260805-r1/`,
  `verification/v0.9.7-b/v0.9.7-b-wu6-20260805-r1/` (evidence JSON +
  screenshots; isolated DBs and logs gitignored under `isolated/` and
  `logs/`).
- Test logs: `C:\tmp\wu6-affected\affected_final_output.txt`,
  `C:\tmp\wu6-fullcore\full_core_final_output.txt`,
  `C:\tmp\wu6-launcher\launcher_run1.txt`, `launcher_run2.txt`,
  `C:\tmp\wu6-impact\detect_changes_clean_full.txt`.

## 10. Final decision

All 80 WU6 acceptance criteria and all prior WU acceptance criteria are
satisfied; no release blocker remains; user-owned files remain untouched
and uncommitted; no push or pull request was performed.

> **v0.9.7-B is complete, verified, and closed. The priority-guided
> revision and Practice cycle is operational end to end, and the next
> planned phase is v0.9.7-C.**
