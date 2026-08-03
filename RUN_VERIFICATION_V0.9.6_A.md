# v0.9.6-A Verification - Linked Revision Submission Reliability

**Status:** **PASS - v0.9.6-A is COMPLETE and fully verified.**

## User-visible defect

A linked revision submitted through the Student Revision page timed out in the
UI ("The request took too long and was stopped. Please try again. (while
submit)") while the backend continued and durably committed the full linked
revision.

## Incident classification (Phase 0, read-only database inspection)

- Window: 2026-08-03 16:30-16:40 +08:00 (08:30-08:40 UTC).
- Classification: **C - complete linked revision created after the UI
  timeout** (essay 26 with snapshot RS000012, analysis AR000025, diagnosis,
  learner history, feedback record 25 `fallback_success` ending 08:34:04 UTC
  = the development-database mtime).
- The timed-out real revision **was found**: essay 26 (revision of essay 25,
  group RG000005, sequence 3).
- Additional evidence: essays 24 and 25 are byte-identical linked revisions
  (same parent 13, same sequence 2) created 37 s apart - a duplicate POST in
  the same window.
- Incident records were not repaired.

## Exact timeout source

Frontend only: `app/ui/api_client.py::WritingFeedbackApiClient.submit` POSTs
`/api/v1/submissions` with `DEFAULT_TIMEOUTS` `(connect=2.0, write=30.0)`;
`requests.ReadTimeout` maps to `ErrorCategory.REQUEST_TIMEOUT` and renders
`error_request_timeout` + "(while submit)" plus a Retry button. The backend
sync endpoint keeps running after the client disconnect and commits
(essay/analysis/diagnosis/revision relationship are saved before
`router.generate`; feedback and history after it).

## Measured controlled timings (fresh temporary databases, local provider)

| Case | Measurement |
| --- | --- |
| Normal completion | 0.203 s |
| Old-timeout reproduction (client write 3.0 s vs 6.0 s provider) | timeout at 3.031 s |
| Backend completion after client timeout | +3.297 s, fully durable (classification C reproduced) |
| Duplicate POSTs (two identical sequential POSTs) | 2 byte-identical linked revisions |
| Controlled slow revision with dedicated 180 s timeout | 31.5 s provider: success (focused integration test) |
| Real-API slow success (5 s provider) | 5.17 s, exactly one revision |

## Chosen bounded fix

- Dedicated long-operation timeout `LONG_SUBMIT_TIMEOUTS` (2.0 / 180.0 /
  180.0) used only by the new `submit_linked_revision` client method; the
  generic `submit()` and all ordinary requests keep the 30 s profile.
- No automatic POST retry (unchanged `_request` rule: retry only ever applies
  to GET; the new method passes no retry flag).
- Pending-state submit guard in the revision page (session state): the button
  click is consumed without a second POST while a submit is in flight or its
  terminal outcome is pending display; the guard clears after success,
  outcome consumption, or an ordinary error.
- Bounded read-only reconciliation after a final timeout, using only existing
  GET APIs: newest server `submitted_at` baseline for the source captured at
  render; re-fetch `GET /api/v1/students/{student_id}/revision-candidates`;
  exact match = `revision_of_submission_id == source` and `submitted_at >
  baseline`; then `GET /api/v1/submissions/{essay_id}` to distinguish
  CONFIRMED_SUCCESS (feedback present) from STILL_PROCESSING (essay saved,
  feedback not yet) and UNCONFIRMED (no exact match / read failure). Never
  POSTs, never recurses, at most two short GETs.
- Accurate localized messages (en + zh_CN, parity preserved) with no blind
  "try again" instruction and no Retry button on the timeout path.

## Duplicate-submission behavior

- Before: the client never auto-retried, but the page had no pending guard;
  after a timeout the Retry button / form allowed a second POST, creating a
  duplicate (incident essays 24/25; reproduced in
  `reproduction_before_ui.json`: 1 -> 2 POSTs).
- After: exactly one POST per click; a queued second click is consumed by the
  guard (AppTest: post_count stays 1); the guard releases after the outcome
  is consumed; no duplicate revision in the controlled timeout case.

## Reconciliation result states

CONFIRMED_SUCCESS, STILL_PROCESSING, UNCONFIRMED (see focused tests and
`user_flow_after.json`).

## Test evidence

- Focused `tests/test_v096a_linked_revision_submission.py`: **21 passed,
  0 failed** (dedicated timeout; generic timeout unchanged; single POST; no
  automatic retry; pending guard; guard release; controlled slow success
  above the old timeout; reconciliation confirmed/still-processing/
  unconfirmed; no blind retry; linkage identity; no duplicate revision;
  locale parity; original `submit()` unchanged).
- Relevant regression set (revision, submission, API-client, reliability,
  UI, locale, architecture contract tests incl. `test_v095d_api_contract`,
  `test_v095d_port_contract`, `test_v095h2d2`, `test_v095g`, `test_v095h2a`):
  **212 passed, 3 skipped, 0 failed**.
- Targeted user-flow verification (`verification/v0.9.6-a/user_flow_after.py`):
  UI success flow (1 POST, saved state, pending cleared), UI timeout flow
  (1 POST, UNCONFIRMED message, queued click consumed, guard released, no
  Retry button), real-API slow flow (5 s provider, success, exactly one
  revision in history).
- Full non-live core (one fresh run): **730 passed, 8 skipped, 0 failed,
  0 errors, exit code 0** (351.65 s).
- Launcher: exact `cmd /c "run.bat --verify"` -> **PASS (exit 0)** on a fresh
  isolated database; migration 12; tables 33; `config-v0.9.0`;
  `feedback-prompt-v0.7.1`; health/docs/Streamlit 200.

## Contracts and invariants

- API path+method pairs: **77** unchanged (`test_v095d` runtime set).
- Database public methods: **2** unchanged.
- Frontend client public methods: **52 -> 53** (`submit_linked_revision`
  added; feature-driven update of the frozen `tests/contracts/
  api_surface_contract.py` ledger per the v0.9.5 change policy).
- Locale parity: **524/524** (four new keys in both files).
- Migration 12; tables 33; `config-v0.9.0`; `feedback-prompt-v0.7.1`.
- No schema/migration/transaction/analysis/prompt/provider/Router/Service
  change; no production backend change.

## Database and export safety

- Development database before/after every write-capable run: SHA-256
  `1DD4B42DB339BBCE3C6A7E0A05749DDDCF07B588770A65AEE84973272109381B`, size
  9,404,416 bytes, mtime `2026-08-03T16:34:04.205+08:00` - unchanged; the
  Phase-0 inspection was the only access and was read-only (SQLite `mode=ro`).
- Research exports: relevant suite generated 2 dirs / 4 files and full core
  generated 8 dirs / 16 files; each delta was removed through the exact guard
  allowlist; final state **776 files / 388 dirs with all baseline paths and
  hashes unchanged** (guard `--check` PASS).

## Residual limitation

The dedicated 180 s bound is a client-side wait, not an asynchronous job
system; a linked revision whose backend pipeline exceeds 180 s still surfaces
the bounded reconciliation outcomes (CONFIRMED_SUCCESS / STILL_PROCESSING /
UNCONFIRMED) instead of a fabricated failure. A genuinely asynchronous design
remains out of scope by authorization.
