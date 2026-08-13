# LEARNER WU2 RETRY-2 Canonical Handoff

- Handoff ID: `LEARNER-WU2-RETRY2-CANONICAL-HANDOFF-20260812T015841+0800`
- Goal/run: `PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__RETRY-2__20260811T164118Z__8c8d39`
- Owner: `LEARNER`
- Worktree: `A:\EAP Agent Project\worktrees\learner`
- Branch: `dept/feedback-learner`
- Starting/final SHA: `7a9e4b470c41c0453a3795233f1bdd5c483d80ae` / unchanged
- Verdict: **AMBER** — the Learner departmental slice and executable parent
  regression are evidenced; integration/contract decisions remain open.
- Gate authority: `INT`
- Returned: `2026-08-12T01:58:41+08:00`

## Delivered within the authorized Learner scope

Workers A, B, C, and D completed through the exact route
`deepseek/deepseek-v4-flash` with `reasoning_effort=ultra` and
`PLANNING_DISABLED=1`. The final parent audit found four additive tracked
files and the authorized new Learner source/tests only:

- practice/review structural bridge with separate system-provisional,
  learner-self, and CORE scheduler rating channels plus rating-rule/scheduler
  provenance;
- separate practice-history and authentic-writing-application projections,
  with descriptive comparability/status and no causal transfer inference;
- positive longitudinal acknowledgement contracts/service/router with
  explicit consent, provenance/version, evidence status/source-kind gates,
  L0-only descriptive semantics, and no-write failure paths;
- one composition root with one database/connection-manager authority,
  one acknowledgement-router registration, and a typed optional CORE review
  injection boundary.

No `app/review` implementation was copied into Learner. No migration,
scheduler, second runtime/database, CORE/L2/UX/INT source, Program Control
file, commit, push, PR, merge, promotion, reset, clean, restore, or rebase
was performed. The five pre-existing dirty/untracked Learner paths remain
present; the four paths with recorded WU0 fingerprints remain byte-identical.

## Verification evidence

All parent commands used the Learner worktree `.venv`,
`PYTHONDONTWRITEBYTECODE=1`, and `-p no:cacheprovider`.

| Verification | Result |
|---|---|
| WU2 focused (`test_wu2_practice_review_evidence`, `test_wu2_acknowledgement`, `test_wu2_journey_history_transfer`, `test_wu2_api_composition`) | **121 passed**, 2 warnings |
| Journey/Wave-2/Learner regression | **396 passed**, 2 warnings |
| Practice/narrowing regression | **251 passed**, 2 warnings |
| Composition/router/Wave-2 pins | **28 passed, 2 failed** — the two failures below are recorded unowned contract pins |
| V1 independent verifier | **CONCERNS**: static verification passed; pytest could not start in the enforced read-only sandbox because no writable temporary directory was available |

The V1 result is preserved in
`docs/integration/pdw3-wu2-learner-20260812/workers/V1/last-message.txt`.
Its limitation does not invalidate the parent executable regression, but it
prevents claiming an independently executed V1 test run.

## Blocking findings / remaining decisions

1. Worker B's two projections are service-level and composition-reachable,
   but not API-route-exposed. Adding
   `GET /api/v1/students/{student_id}/journey/practice-history` and
   `GET /api/v1/students/{student_id}/journey/authentic-application` requires
   editing `app/api/routers/journey.py`, which was outside D's authorized
   packet. This remains a separate owner/INT decision.
2. Including the required acknowledgement router adds exactly two method/path
   pairs. The unmodified `tests/test_v095b_router_contract.py` exact-route pin
   therefore fails. The unmodified `tests/test_v095d_api_contract.py` still
   pins 81 endpoints although the parent baseline already observed 100 and
   the final runtime observes 102. Updating/regenerating those cross-cutting
   contract pins was not authorized in this Goal.
3. Acknowledgement POST is intentionally fail-closed with
   `503 evidence_unavailable` because no production evidence lookup or
   durable acknowledgement persistence is composed. The CORE review bridge is
   intentionally fail-closed with `core_review_service_missing` until INT
   injects the existing CORE service as-is.

## Handoff boundary

- `integration_required`: **true**.
- `promotion_eligible`: **false**.
- `user_decision_required`: **true** for the two unowned route/contract
  decisions and the INT-gated service/persistence composition.
- `researcher_decision_required`: **true** for accepting the AMBER boundary
  or authorizing the separate repair Goal.
- `repair_owner`: `INT` for cross-cutting composition/contract decisions;
  no repair was performed here.

This is a departmental handoff for controlled INT review, not an integration,
promotion, or product-activation claim.
