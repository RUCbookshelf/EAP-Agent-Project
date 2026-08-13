# RETRY-2 Worker C findings — Positive Longitudinal Acknowledgement / Safety

- run_id: `PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__RETRY-2`
- worker: C (positive longitudinal acknowledgement / safety)
- model: `deepseek/deepseek-v4-flash` (no substitution)
- reasoning: ultra (proxy-injected; worker run is the source of truth)
- environment: `PLANNING_DISABLED=1`
- worktree / branch / HEAD: `A:\EAP Agent Project\worktrees\learner` /
  `dept/feedback-learner` @ `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`
  (baseline verified before and after; no commit created)
- verdict: **DONE** — 51/51 focused tests green; no-write behavior asserted
  on every failure path

## 1. Result

Implemented the positive longitudinal acknowledgement contract over already
admitted learner evidence, plus a learner-owned router that resolves the
service from `request.app.state.acknowledgement_service`. The slice is
additive-only: no tracked file was modified, no database/migration/scheduler/
runtime was introduced, no second persistence authority was invented (the
append-only store and evidence lookup are injected Protocol ports; tests use
in-memory doubles).

## 2. Changed files (owned scope only)

- `app/learner/acknowledgement_contracts.py` (new): `LearnerConsent`,
  `AcknowledgementRequest`, `AcknowledgementRecord`, `AcknowledgementResult`,
  `AcknowledgementSourceKind` (source event / observed evidence / diagnostic
  inference / feedback recommendation / practice activity / practice result /
  history signal / outcome claim), `ACKNOWLEDGEABLE_SOURCE_KINDS`
  (observed evidence, practice activity, practice result, history signal),
  `ACKNOWLEDGEMENT_LIMITATION`, consent scope/version constants. Records are
  structurally non-claiming: `epistemic_status` locked to
  `observed_descriptive`, `outcome_claim` locked to `"none"`, span order
  validated, extra fields forbidden.
- `app/learner/acknowledgement.py` (new): `AcknowledgementError` (stable
  kinds), `AcknowledgementStorePort` (append-only), `AcknowledgementEvidencePort`
  (learner-scoped lookup), `CAUSAL_LANGUAGE_TERMS`, `AcknowledgementService`
  (fail-closed gates in fixed order), deterministic `_stable_acknowledgement_id`
  (sha256-derived, like CORE WU1's stable card id).
- `app/api/routers/acknowledgement.py` (new): additive
  `POST/GET /api/v1/students/{student_id}/acknowledgements`; dependency
  reads `request.app.state.acknowledgement_service` (503 when not composed);
  stable status mapping for every error kind. `main.py`/`deps.py` untouched
  (Worker D wires the composition root).
- `tests/learner/test_wu2_acknowledgement.py` (new): 51 focused tests.
- `docs/integration/pdw3-wu2-learner-20260812/workers/C/findings.md` (this file).

No other file was touched. Pre-existing untracked evidence and Workers A/B
outputs remain byte-preserved.

## 3. Contract boundaries enforced

- Acknowledgement is descriptive and learner-facing only: it is not mastery,
  proficiency, writing ability, learning gain, score, ranking, diagnosis,
  recommendation, or causal transfer attribution. Enforced by the epistemic
  layer lock, the `outcome_claim="none"` literal, the source-kind
  discriminator (diagnostic inference / feedback recommendation / outcome /
  raw source events are not acknowledgeable), and the frozen limitation.
- Consent: missing, denied, revoked, wrong scope, learner-mismatched, or
  future-dated consent fails closed with no write
  (`consent_missing/denied/revoked/scope_mismatch/learner_mismatch/invalid`).
- Evidence: non-empty source evidence IDs; learner ownership verified through
  the injected evidence port (`evidence_not_found` / `cross_student`);
  admission status must be ADMISSIBLE; observed evidence must be L0
  (`observed_descriptive`) and not exposure-unavailable; practice records
  must be activity-only (`outcome_claim="none"`), COMPLETED, and (for
  practice result) evaluation-backed; history signals must be
  evidence-type/limitation carrying with no outcome claim
  (`invalid_source_record`).
- Provenance/version/status: stable provenance required and completeness-
  checked (`missing_provenance`); record version plus at least one of
  policy/model/config version required (`missing_version`); only VERIFIED
  evidence status is acknowledgeable (`invalid_evidence_status`).
- Language: the existing `NormativeClaimsScanner` runs strict on supplied
  acknowledgement text (`normative_language`) plus a frozen causal/change-
  language list (`causal_language`: improved/progress/decline/transfer/led
  to/resulted in/due to + Chinese equivalents). The assembled record is
  rescanned in documentation mode before append (limitations are F1-exempt
  prohibition text).
- Duplicate/conflict: identical evidence-set acknowledgements are rejected
  (`duplicate_acknowledgement`); explicit id reuse with different content is
  rejected (`conflict`). Both 409, no write.
- Persistence: no new database, migration, scheduler, or runtime; append-only
  store port injected; the service writes exactly one record only after all
  gates pass.

## 4. Fail-closed paths with no-write assertions

Consent (missing/denied/revoked/scope/learner/future), missing evidence
reader, unknown evidence, cross-student evidence, missing provenance,
missing policy/model/config versions, invalid evidence status (7 statuses),
non-acknowledgeable source kinds (4 kinds), invalid/limited admission,
gated-inference evidence, unavailable exposure, practice result without
evaluation, invalid practice admission, normative text (mastery,
proficiency), causal text (improved, led to transfer), duplicate,
conflicting id, malformed payloads (blank ids, extra fields, blank text,
missing record version, non-descriptive epistemic status, inverted span,
blank consent scope/version, outcome claim tampering). Every failed case
asserts the append-only store is empty (or unchanged).

## 5. Exact verification commands and counts

```text
.venv\Scripts\python.exe -m pytest tests/learner/test_wu2_acknowledgement.py -q --no-header
=> 51 passed, 1 warning (StarletteDeprecationWarning from fastapi.testclient)

.venv\Scripts\python.exe -m pytest tests/learner -q --no-header
=> 250 passed, 1 warning

.venv\Scripts\python.exe -m pytest tests/shared tests/wave2 -q --no-header
=> 265 passed, 2 warnings
```

TDD sequence: focused tests written first (RED: `ModuleNotFoundError: No
module named 'app.api.routers.acknowledgement'`), then contracts, service,
and router implemented (GREEN 51/51). Two defects found and fixed during the
green pass: (1) the test helper dropped the `epistemic_status` override, so
the gated-inference evidence path did not exercise the service check; (2)
explicit acknowledgement-id conflict was shadowed by the evidence-key
duplicate check — conflict is now evaluated before the duplicate key.

## 6. Boundaries and notes for Worker D / INT

- The router depends solely on `request.app.state.acknowledgement_service`;
  Worker D must compose `AcknowledgementService(store, evidence_port=...)`
  in `main.py` and attach it to app state (503 otherwise).
- Learner-facing *display* of corpus-derived content remains gated by
  `app/learner/exposure.py` (D-08 opt-in still FAIL-CLOSED); this slice does
  not bypass that gate and only rejects exposure-unavailable evidence at the
  source-record level.
- The evidence lookup port verifies ownership and admission; production
  implementations (learner evidence / practice records / history signals)
  are Worker D's composition decision.
- No commit/push/PR/merge/promotion; no Program Control write; no other
  worktree touched; baseline `7a9e4b47` re-verified.

