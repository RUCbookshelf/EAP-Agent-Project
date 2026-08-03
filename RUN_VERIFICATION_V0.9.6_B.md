# v0.9.6-B Verification - First Draft and Unified Submission Reliability

**Status:** **PASS - v0.9.6-B is COMPLETE and fully verified.**

## User-visible defect

First-draft submission still used the old generic 30 s POST timeout and
displayed "The request took too long and was stopped. Please try again.
(while submit)" while the backend continued and committed - the same
false-failure and duplicate-submission risk proven for linked revisions in
v0.9.6-A.

## Incident classification (Phase 0, read-only database inspection)

- Window: 2026-08-03 19:00-19:15 +08:00 (11:00-11:15 UTC).
- Classification: **C - first draft completed after the UI timeout**.
- Real first draft found: essay 27 (student S02, first draft, submitted
  19:10:32 +08:00) with analysis AR000026, 24 metric results, diagnosis,
  learner history, and feedback record 26 (`fallback_success`) ending
  19:11:03 +08:00 = the development-database mtime. The deepseek provider
  call took 30.46 s (11:10:32.69 -> 11:11:03.15 UTC) before the local-demo
  fallback - just past the old 30 s client write timeout.
- Duplicate first draft: **not found** in the incident window (essay 27's
  text equals essay 26, an earlier linked revision with a different mode and
  non-close timestamps - not a duplicate pair). The duplicate risk itself
  was reproduced deterministically.
- No incident records were repaired.

## Old first-draft path

`writing_submit_primary` -> `WritingFeedbackApiClient.submit` -> POST
`/api/v1/submissions` with `DEFAULT_TIMEOUTS` `(connect=2.0, write=30.0)`;
timeout -> `error_request_timeout` + "(while submit)" + Retry button; no
pending guard; no reconciliation. `submit()` had exactly one active call
site (writing.py), covering first drafts and writing-page revisions.

## Unified final path

```text
submit() / submit_linked_revision()
        -> WritingFeedbackApiClient._submit_long_running (private shared transport)
                one POST /api/v1/submissions
                LONG_SUBMIT_TIMEOUTS (connect 2.0 / read 180.0 / write 180.0)
                no automatic POST retry
        -> mode-specific reconciliation (FIRST_DRAFT / LINKED_REVISION)
```

- Shared UI reliability helper: `app/ui/features/student/submit_reliability.py`
  (pending-state entry/release, queued-click consumption, outcome storage and
  rendering, per-mode message mapping; no backend dependency).
- First-draft reconciliation: pre-submit baseline (one bounded GET of the
  existing revision-candidates endpoint; newest server submitted_at of
  same-mode rows); after a final timeout re-fetch and require exactly one
  same-mode row with `submitted_at > baseline`, then the submission bundle
  with student + exact essay text equality; feedback present ->
  CONFIRMED_SUCCESS, else STILL_PROCESSING; zero/multiple/read failure/
  mismatch -> UNCONFIRMED. Never POSTs, never recurses, no fuzzy or
  latest-only matching.
- Linked-revision reconciliation and messages are unchanged (v0.9.6-A
  regression freeze); only the pending/outcome mechanics were extracted to
  the shared helper with behaviorally identical session keys.

## Timeout values

- Long-running essay submission (both modes): connect 2.0 / read 180.0 /
  write 180.0 (`LONG_SUBMIT_TIMEOUTS`, unchanged constant).
- Ordinary GETs, health, docs, and non-submission requests: unchanged
  (`DEFAULT_TIMEOUTS` 30 s write, GET read 10 s, lifecycle 5 s).
- No global timeout increase.

## No-POST-retry rule

Both POST entries issue exactly one POST; no automatic retry after any
timeout (retry applies only to GET). The UI pending guard consumes queued
clicks; no Retry button on ambiguous submission timeouts.

## Measured controlled timings (fresh temporary databases, local provider)

| Case | Measurement |
| --- | --- |
| First draft below old timeout | 0.141 s |
| First draft exceeds old timeout (client write 3.0 s vs 6.0 s backend) | timeout at 3.015 s; backend completed +3.313 s, fully durable (classification C reproduced) |
| Two identical first-draft POSTs | two byte-identical durable first drafts (duplicate risk reproduced) |
| Slow first draft with the shared 180 s timeout | 31.5 s provider: success (focused integration test) |
| Real-API slow first draft (5 s provider) | 5.12 s, exactly one first draft |

## Before/after retry and duplicate-click behavior

- Before: client never auto-retried, but the writing page had no pending
  guard; after the old timeout message a second click issued a second POST
  (AppTest: 1 -> 2) and two durable duplicates were created at the API level.
- After: one POST per logical submit; queued clicks consumed by the guard
  (AppTest: post_count stays 1); guard releases after success or after the
  outcome is consumed; no duplicate first draft or linked revision in
  controlled tests.

## First-draft reconciliation inputs

student ID, submission mode (first draft: `revision_of_submission_id` NULL;
writing-page revision: source ID), server submitted_at baseline (pre-submit),
existing submission list (same GET the page already uses), submission bundle,
exact submitted text held in UI memory (compared, never persisted).

## Reconciliation result states

CONFIRMED_SUCCESS (exact one match + complete downstream artifacts),
STILL_PROCESSING (exact one match + downstream incomplete), UNCONFIRMED
(zero/multiple matches, read failure, or identity mismatch). CONFIRMED_FAILURE
is not asserted because a client timeout carries no exact rejection evidence.

## English/Chinese messages

Four new first-draft keys in both locales (pending / confirmed success /
still processing / unconfirmed); parity 528/528. Linked-revision messages
unchanged. No "Please try again" and no Retry button on ambiguous first-draft
timeouts.

## Test evidence

- Focused: `tests/test_v096b_first_draft_submission.py` 30 passed;
  `tests/test_v096a_linked_revision_submission.py` 21 passed (two policy
  assertions updated for the unified timeout).
- Contract rerun (api/port/locale/submission files): 72 passed.
- Relevant regression set (API-client, first-draft, linked-revision,
  submission, revision, UI, reliability, locale, contract tests):
  242 passed, 3 skipped, 0 failed.
- Targeted user flows (`user_flows_after.json`): Flow A first-draft success
  (1 POST, saved state); Flow B timeout + backend completion -> confirmed
  success (1 POST, no Retry button); Flow C unconfirmed (text preserved,
  no blind retry); Flow D linked-revision regression (1 POST, saved state);
  real-API slow first draft (5.12 s, exactly one draft).
- Full non-live core (one fresh run): **760 passed, 8 skipped, 0 failed,
  0 errors, exit code 0** (401.93 s).
- Launcher: exact `cmd /c "run.bat --verify"` -> **PASS (exit 0)** on a fresh
  isolated database; migration 12; tables 33; `config-v0.9.0`;
  `feedback-prompt-v0.7.1`; health/docs/Streamlit 200.

## Contracts and invariants

API path+method pairs 77 unchanged; Database public methods 2; frontend
client public methods **53** (no new public method; `submit_linked_revision`
and `submit` both delegate to the private `_submit_long_running`);
`StudentWritingApiPort` gained `get_submission` (used by first-draft
reconciliation; feature-driven ledger update); locale parity **528/528**;
migration 12; tables 33; `config-v0.9.0`; `feedback-prompt-v0.7.1`. No
backend production file changed; no schema, migration, or transaction
boundary changed.

## Database and export safety

- Development database before/after every write-capable run: SHA-256
  `646B6555A67EAF6D3F63B6D175948A660890C942F4A73BFFDB6AB5DB54E1C39B`,
  size 9,854,976 bytes, mtime `2026-08-03T19:11:03.178+08:00` - unchanged;
  the Phase-0 inspection was the only access and was read-only (SQLite
  `mode=ro`).
- Research exports: 10 run-generated dirs / 20 files removed through the
  exact guard allowlist; final state **776 files / 388 dirs with all
  baseline paths and hashes unchanged**.

## Residual limitation

The 180 s bound is client-side; a submission whose backend pipeline exceeds
it surfaces the bounded reconciliation outcomes (CONFIRMED_SUCCESS /
STILL_PROCESSING / UNCONFIRMED) instead of a fabricated failure. A genuinely
asynchronous design remains out of scope by authorization.
