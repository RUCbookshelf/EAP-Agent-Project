# Worker A Findings — Practice / Review Dual-Channel Evidence (RETRY-2)

- worker: `PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__RETRY-2` / A
- model / reasoning / env: `deepseek/deepseek-v4-flash` / ultra /
  `PLANNING_DISABLED=1`
- worktree / branch / baseline: `A:\EAP Agent Project\worktrees\learner` /
  `dept/feedback-learner` / `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`
- status: **DONE** (focused suite green; no commit / push / PR / Program
  Control write)

## 1. Context read (all five required groups)

1. `docs/integration/pdw3-wu2-learner-20260812/CHECKPOINT-002-RETRY2-DISPATCH-SURFACE.md`
2. `A:\EAP Agent Project\worktrees\shared-core\docs\integration\pdw3-wu1-recovery-20260811\CORE-WU1-DEPARTMENT-HANDOFF.md`
3. CORE `app/review/models.py`, `protocols.py`, `service.py`,
   `rating_policy.py`, plus `app/infrastructure/sqlite/repositories/review.py`
   and `app/api/routers/review.py` (composition pattern)
4. LEARNER `app/practice/service.py`, `ports.py`, `schemas.py`,
   `app/infrastructure/sqlite/repositories/practice.py`, `app/learner/`
   evidence/provenance/normative modules, `app/errors.py`
5. `AGENTS.md` + this Goal Packet

## 2. Design (boundary summary)

The CORE `app/review` package is an uncommitted candidate in the
`shared-core` worktree and is NOT importable from LEARNER. CORE
implementation is not copied here. The bridge is therefore structural:

- `app/learner/review_bridge.py` (new): learner-owned typed records
  (`PracticeActivityRecord`, `ReviewRequestRecord`) that mirror the CORE
  contract field-for-field (same names, types, JSON shape, `extra="forbid"`),
  the narrow `CoreReviewServicePort` Protocol matching the CORE
  `ReviewService` surface LEARNER consumes, the rating-space mirror
  (`Rating`: again/hard/good/easy), fail-closed provenance validation, and
  the stable-kind `ReviewBridgeError`.
- `app/practice/review_transfer.py` (new): `PracticeReviewTransferOrchestrator`
  with two entry points. `record_practice_activity` always labels evidence
  `evidence_kind="practice"` and never triggers a review.
  `record_review` runs only when explicitly requested and forwards the
  system-provisional and learner-self channels separately (never averaged;
  the final scheduler rating is resolved by the CORE versioned rating rule).
  Provenance always carries the CORE `rating_rule_version` and the scheduler
  implementation/version/parameters obtained from the injected service.
- No adapter file (`app/infrastructure/learner_review.py`) was needed: the
  learner records are consumed by the raw CORE `ReviewService`/SQLite
  repository through plain attribute access (`status.value`,
  `occurred_at.isoformat()`, `model_copy`, pydantic `model_dump`), verified
  against the CORE source above. The future INT composition root injects the
  integrated CORE `ReviewService` as-is; no second scheduler, database,
  runtime, or migration exists.

Fail-closed ordering (before any write): missing injected service
(`core_review_service_missing`), non-UTC / naive timestamps
(`invalid_occurred_at` / `invalid_reviewed_at`, enforced at record
construction AND re-checked at runtime because pydantic records are
mutable), invalid rating or activity status (pydantic `ValidationError`),
invalid authentic-evidence status (`invalid_authentic_evidence_status`),
malformed provenance (non-dict, non-JSON-safe, or overriding bridge-owned
keys -> `malformed_provenance`), missing/incomplete scheduler identity
(`invalid_scheduler_identity`), missing rating-rule version
(`invalid_rating_rule_version`). Missing durable LearningItem, ownership
mismatch, missing/foreign practice activity, and append-only
duplicate/conflict are verified by the injected CORE service, which raises
before its write; those stable-kind errors propagate unchanged (never
re-implemented in LEARNER).

Channel separation: practice evidence (`evidence_kind="practice"`,
`source="practice"`, channel provenance `evidence_channel="practice"` /
`authentic_evidence_channel="separate"`) is structurally distinct from
authentic writing evidence (`authentic_evidence_status="present"` only when
explicitly claimed). Practice completion/review never implies authentic
transfer; the CORE limitation wording is carried as prohibition context.

## 3. TDD evidence (exact commands and counts)

RED (before implementation; modules did not exist):

```text
A:\EAP Agent Project\worktrees\learner\.venv\Scripts\python.exe -m pytest tests/learner/test_wu2_practice_review_evidence.py -q --no-header
=> ERROR collecting tests/learner/test_wu2_practice_review_evidence.py
   ImportError: No module named 'app.learner.review_bridge'
   1 error during collection
```

GREEN (after `review_bridge.py` + `review_transfer.py`):

```text
A:\EAP Agent Project\worktrees\learner\.venv\Scripts\python.exe -m pytest tests/learner/test_wu2_practice_review_evidence.py -q --no-header
=> 40 passed in 0.13s
```

Re-verified on later reruns: `40 passed in 0.13s` and `40 passed in 0.11s`
(stable across three runs).

Broader check while the worktree was quiet:

```text
A:\EAP Agent Project\worktrees\learner\.venv\Scripts\python.exe -m pytest tests/learner -q --no-header
=> 250 passed, 1 warning in 2.52s
```

## 4. Coverage (40 focused tests)

- practice labeling: `evidence_kind="practice"` literal (unspoofable),
  `source="practice"`, default `authentic_evidence_status="insufficient"`,
  explicit `"present"` allowed, activity-status vocabulary closed, extras
  rejected
- three rating channels: system provisional + learner self forwarded
  separately (no `final_scheduler_rating` computed or emitted by LEARNER),
  optional learner channel, rating-rule version + scheduler
  implementation/version/parameters carried in provenance, all three
  channels present on the returned event, deterministic provenance across
  identical calls
- delegation: both entry points actually call the injected boundary; a
  review is never implied by a practice-activity call
- fail closed: missing service (both paths), naive and non-UTC datetimes at
  construction and after mutation, invalid rating, invalid
  authentic-evidence status (construction + mutation), malformed
  provenance (non-JSON-safe, reserved-key override on both paths), missing /
  incomplete scheduler identity, missing rating-rule version, and CORE
  rejections propagate with kinds: `learning_item_not_found`,
  `learning_item_owner_mismatch`, `practice_activity_not_found`,
  `practice_activity_owner_mismatch`, `practice_activity_already_exists`,
  `review_event_already_exists` — all with zero writes before the failure
- no normative language: records scan clean in documentation mode; emitted
  payloads scanned in strict mode produce violations only inside the
  prohibition-context `limitations` field (activity) and none at all
  (review kwargs)
- channel separation: channel markers in provenance, no-transfer limitation
  on every practice payload, authentic status forwarded without implying
  transfer

## 5. Changed files (owned scope only)

- `app/learner/review_bridge.py` (new)
- `app/practice/review_transfer.py` (new)
- `tests/learner/test_wu2_practice_review_evidence.py` (new, 40 tests)
- `docs/integration/pdw3-wu2-learner-20260812/workers/A/findings.md` (this
  file)

Not created: `app/infrastructure/learner_review.py` (not needed; see design).
Nothing outside the owned scope was modified. No commit, push, PR, merge,
promotion, reset, clean, restore, rebase, or Program Control write was
performed.

## 6. Risks / observations (for INT / coordinator)

1. **Concurrent worker writes during verification**: parallel workers B
   (journey history transfer) and C (longitudinal acknowledgement) write
   their own files in this same worktree. While they were mid-write, two
   full-directory runs transiently failed in THEIR files (2 failed in
   `test_wu2_acknowledgement.py`, then 15 in
   `test_wu2_journey_history_transfer.py`); each settled once those workers
   finished. Worker A's file is isolated and stable (40/40 every run). The
   final quiet-worktree full run: 250 passed.
2. **CORE-side fail-closed dependency**: LearningItem existence, ownership,
   practice-activity linkage, and append-only conflict checks happen inside
   the injected CORE service before its write. This is by design (LEARNER
   must not duplicate CORE), so the guarantee is as strong as the injected
   service. Verified against CORE `service.py` that all such checks run
   before `record_review_event` / `save_practice_activity`.
3. **Structural consumption verified against CORE source**: the learner
   records use only generic pydantic/datetime surface (`status.value`,
   `isoformat()`, `model_copy`, `model_dump`, attribute access), which is
   exactly what the CORE service and SQLite repository require; no shim was
   needed for either `record_practice_activity` or `record_review`.
4. **Cross-package import**: `app/practice/review_transfer.py` imports
   `app/learner/review_bridge.py`; `tests/test_architecture_v02.py` has no
   rule forbidding this, and the full learner suite passes when quiet.
5. **Return normalization**: results from the injected service are
   normalized to JSON dicts (`model_dump(mode="json")` when the service
   returns a pydantic model) so the public surface is learner-owned dicts.
6. **Scheduler identity validation**: if the injected service ever returns
   an incomplete identity, the bridge fails closed
   (`invalid_scheduler_identity`) rather than emitting degraded provenance.

## 7. Handoff notes for INT composition

To wire the real CORE service later:

```python
orchestrator = PracticeReviewTransferOrchestrator(
    core_review_service=review_service,  # CORE ReviewService instance
)
```

`record_review` takes primitives the CORE service already accepts (rating
strings, UTC `datetime`, provenance dict); `record_practice_activity`
accepts the learner `PracticeActivityRecord` that the CORE service and
repository consume structurally. No second store or adapter is required.
