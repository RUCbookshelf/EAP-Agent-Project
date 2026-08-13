# RETRY-2 Checkpoint 009 — Worker D Terminal / Parent Scope Audit

- Goal/run: `PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__RETRY-2__20260811T164118Z__8c8d39`
- Worker: `D` — API composition / Wave-2 compatibility
- Dispatch route: `codex exec` direct prompt; model `deepseek/deepseek-v4-flash`; reasoning effort `ultra`; `PLANNING_DISABLED=1`; `fork_context=false` equivalent direct isolated prompt; sandbox `danger-full-access` because the authorized workspace-write child surface returned `windows sandbox: helper_unknown_error: setup refresh had errors`.
- Session: `34645`
- Worktree: `A:\EAP Agent Project\worktrees\learner`
- Branch/HEAD: `dept/feedback-learner` / `7a9e4b470c41c0453a3795233f1bdd5c483d80ae` (unchanged)
- Terminal state: `DONE` with two reported unowned blockers; no retry or closure action taken.

## Parent actual-diff audit

Tracked modifications attributable to RETRY-2 are limited to:

- `app/api/main.py`: one acknowledgement-router registration, two service-graph keys, one state-assignment point, and a fail-closed process-local placeholder store.
- `app/api/deps.py`: two app-state dependency getters.
- `app/journey/service.py`: Worker B's additive `get_practice_history` and `get_authentic_application` methods only.
- `tests/test_composition_root.py`: additive service-key/state assertions.

New RETRY-2 learner-owned source/tests are the A/B/C files plus:
`tests/learner/test_wu2_api_composition.py`. The parent audit found no CORE,
L2, UX, INT, Program Control, migration, or other worktree path in the
status output. Existing dirty/untracked learner files remain present.

Composition inspection returned:

```text
total_method_path_pairs: 102
duplicate_pairs: []
ack_registrations_in_business_routers: 1
single_database: True
shared_conn_mgr: True
bridge_core_is_none: True
ack_evidence_port_is_none: True
journey_additive_methods: True True
```

## D evidence

- WU2 focused composition: `121 passed, 2 warnings` (40 A + 51 C + 18 B + 12 D).
- Composition/router/Wave-2 pin set: `28 passed, 2 failed`.
  - New expected failure: the old `test_v095b` exact route pin lacks the two
    required acknowledgement route pairs.
  - Baseline failure: `test_v095d_api_contract.py` expected 81 endpoints but
    observed 100 before D and 102 after D.
- Journey/Wave-2/learner regression: `396 passed, 2 warnings`.
- Practice/narrowing sweep: `251 passed, 2 warnings`.
- Final D sanity: `17 passed, 2 warnings` for composition plus composition-root tests.

## Reported blockers and boundary

1. Journey route exposure for the two B projections would require editing
   `app/api/routers/journey.py`, outside D's packet scope. The service-level
   projection is composed and fail-closed, but the two API routes are not
   exposed.
2. The acknowledgement router grows the runtime surface by exactly two
   method/path pairs. Updating the pinned route contract and regenerating the
   approved API contract are unowned cross-cutting edits; they were not made.

Acknowledgement POST remains fail-closed with `503 evidence_unavailable`
until INT composes a production evidence lookup and durable persistence. The
CORE review bridge remains fail-closed with `core_review_service_missing`.
No commit, push, PR, merge, promotion, reset, clean, restore, rebase, or
Program Control write occurred.

## Next action

Run the parent-owned required regression against the final RETRY-2 learner
worktree, then dispatch the fresh independent V1 read-only verifier through
the exact same `deepseek/deepseek-v4-flash` / `ultra` / `PLANNING_DISABLED=1`
route. Preserve the two blockers in the final handoff unless V1 identifies a
more severe finding.
