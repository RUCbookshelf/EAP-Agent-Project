# LEARNER WU5 Consent/Acknowledgement Read-Boundary Repair — Report

Goal: `PDW3-WU5-INT-CONSOLIDATED-WAVE3-INTEGRATION-GATE__REPAIR`

Owner: LEARNER · Worktree: `A:\EAP Agent Project\worktrees\learner` ·
Branch: `dept/feedback-learner` · HEAD: `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`

Run: `program-control\runs\PDW3-WU5-INT-CONSOLIDATED-WAVE3-INTEGRATION-GATE__REPAIR__20260812T153733Z__c80d41`

Status after submission: **HANDOFF_PENDING_ACCEPTANCE** for INT re-gate.

## 1. Authorization and scope

The bounded repair packet (schema 1.1.0) was dispatched by PROGRAM after
ingesting the parent INT WU5 AMBER handoff
(`PDW3-WU5-INT-CONSOLIDATED-WAVE3-INTEGRATION-GATE__20260812T153000Z__a5adbe`).
The packet authorizes exactly:

- `app/infrastructure/sqlite/repositories/acknowledgement.py` — bounded
  read-side discrimination of acknowledgement rows from tutor-consent rows
  (no schema change, no data deletion);
- `tests/learner/test_wu5_consent_ack_boundary.py` — new regression coverage;
- `docs/integration/pdw3-wu5-learner-consent-ack-repair-20260812/` — this
  report and the canonical handoff;
- `verification/pdw3-wu5-learner-consent-ack-repair-20260812/` — fresh focused
  evidence and transient verification artifacts.

Forbidden scope (not touched): all other department/master product code,
migrations, acknowledgement semantics, API routes, CORE/L2/UX code, Program
Control files, INT contract pins, raw SWECCL, promotion/merge/push/PR, and
destructive Git operations.

## 2. Preflight

Live checks from the authorized worktree:

```text
git rev-parse --show-toplevel -> A:/EAP Agent Project/worktrees/learner
git branch --show-current    -> dept/feedback-learner
git rev-parse HEAD           -> 7a9e4b470c41c0453a3795233f1bdd5c483d80ae
```

- HEAD equals the promoted master `7a9e4b4` and the packet candidate ref
  `dept/feedback-learner@7a9e4b4`.
- `WORKSTREAM_REGISTRY.json` shows LEARNER `goal_readiness: READY`,
  `PDW3_WU2_LEARNER_AMBER_CLOSURE_REPAIR_AUTHORIZED`, and the active repair
  Goal; `LEARNER.current.json` lists this Goal as RUNNING.
- `PROGRAM_STATUS.md` / `DEPENDENCY_GRAPH.md` / `PROMOTION_HISTORY.md` /
  `WORKTREE_REGISTRY.md` were read and match the packet snapshot.
- The worktree carries the pre-existing WU2 modified/untracked candidate
  (including the acknowledgement repository itself); every file is preserved
  except the single packet-authorized product file.

## 3. Defect reproduction (RED)

The parent INT AMBER handoff's blocking finding was reproduced at the real
composition boundary: a migration-16 `learner_acknowledgements` table
containing a durable `tutor_consent` row (the L2 WU3 consent-store row family
written by the composed `SQLiteTutorConsentStore`) breaks the LEARNER WU2
acknowledgement listing for the same learner.

Reproduction command (before the repair):

```powershell
& '.venv\Scripts\python.exe' -m pytest tests/learner/test_wu5_consent_ack_boundary.py `
  -p no:cacheprovider --basetemp 'verification\pdw3-wu5-learner-consent-ack-repair-20260812\basetemp-red' -q
```

Result: `2 failed, 1 passed, exit 1` with
`ValueError: 'tutor_consent' is not a valid AcknowledgementSourceKind` raised
in `app/infrastructure/sqlite/repositories/acknowledgement.py:132`
(`_from_row`) through `list_for_learner:220` (the HTTP listing path, which
would return 500) and through `get:211`. The WU2 control test (no tutor
consent row) passed, confirming the failure is caused by the shared row
family, exactly as INT recorded.

## 4. Root cause

`SQLiteAcknowledgementRepository` reads every row of the single
architecture-compliant migration-16 table and parses each one as an
`AcknowledgementRecord`:

```python
source_kind=AcknowledgementSourceKind(row["source_kind"]),
```

`tutor_consent` is not a member of `AcknowledgementSourceKind`, so the parse
raises `ValueError` instead of treating the row as a non-acknowledgement
consent row. The table is a shared durable home by design (one database, one
ledger), so the repair must discriminate on read, not relocate or delete the
consent rows.

## 5. Repair (smallest LEARNER-owned read-side change)

File: `app/infrastructure/sqlite/repositories/acknowledgement.py` (only
product file touched).

Added:

```python
_ACKNOWLEDGEMENT_SOURCE_KIND_VALUES = frozenset(
    kind.value for kind in AcknowledgementSourceKind
)

def _is_acknowledgement_row(row: sqlite3.Row) -> bool:
    return row["source_kind"] in _ACKNOWLEDGEMENT_SOURCE_KIND_VALUES
```

Changed `get()`:

```python
if row is None or not _is_acknowledgement_row(row):
    return None
return _from_row(row)
```

Changed `list_for_learner()`:

```python
return [_from_row(row) for row in rows if _is_acknowledgement_row(row)]
```

Effect: non-acknowledgement consent rows are never parsed as
`AcknowledgementRecord` values; genuine acknowledgement rows remain fully
readable; durable tutor-consent data is preserved untouched. No migration,
no schema change, no row deletion, no acknowledgement-semantics change, no
API/route/composition-root change, and no INT-owned code change.

## 6. Regression coverage (new)

`tests/learner/test_wu5_consent_ack_boundary.py` reproduces the real
composition boundary: real `Database`, real `SQLiteAcknowledgementRepository`,
real FastAPI app and HTTP router, one genuine acknowledgement written through
the real service gates, and one durable `tutor_consent` row inserted with the
exact column/value shape of the composed L2 `SQLiteTutorConsentStore`. It
proves:

- the listing returns 200 and excludes non-acknowledgement rows while both row
  families remain in the same single SQLite database (2 rows total, 1
  consent row preserved);
- repository `get` returns `None` (not `ValueError`) for a tutor-consent row;
- WU2 behavior without tutor consents stays intact (200 with the genuine
  acknowledgement).

## 7. Verification results

| Suite | Command | Result | Exit |
| --- | --- | --- | --- |
| Focused WU5 regression (new) | `python -m pytest tests/learner/test_wu5_consent_ack_boundary.py -q` | 3 passed | 0 |
| Decisive LEARNER WU2 (six `test_wu2_*` files) | `python -m pytest tests/learner/test_wu2_acknowledgement.py tests/learner/test_wu2_persistence_evidence.py tests/learner/test_wu2_journey_routes.py tests/learner/test_wu2_journey_history_transfer.py tests/learner/test_wu2_api_composition.py tests/learner/test_wu2_practice_review_evidence.py -q` | 161 passed | 0 |
| Full `tests/learner` sweep | `python -m pytest tests/learner -q` | 330 passed | 0 |

All runs used the worktree-local `.venv` (Python 3.12.13, pytest 9.1.1) with
`-p no:cacheprovider` and per-run `--basetemp` routed under the packet
verification scope (transient scratch removed after runs). Logs:

- `verification\pdw3-wu5-learner-consent-ack-repair-20260812\logs\pytest-wu5-focused.log`
- `verification\pdw3-wu5-learner-consent-ack-repair-20260812\logs\pytest-wu2-focused.log`
- `verification\pdw3-wu5-learner-consent-ack-repair-20260812\logs\pytest-learner-sweep.log`

The WU2 suite count (161) matches the parent INT gate's WU2 focused suite, and
the learner sweep is the prior 327 plus the 3 new boundary tests.

## 8. Scope and preservation compliance

- All pre-existing dirty/untracked WU2 files are preserved; the git-status
  delta from the packet start is limited to the new test file and the two new
  packet-scoped evidence/documentation directories.
- No Git mutation of any kind (no commit, stage, push, PR, merge, promotion,
  reset, clean, restore, rebase, force update).
- No Program Control file was written; no other worktree was touched; no raw
  SWECCL access.
- `HEAD` unchanged: `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`
  (`starting_sha == final_sha`; candidate remains uncommitted by packet
  design).

## 9. Route note (recorded honestly)

The packet mandated the opencode-go/deepseek-v4-flash/ultra route. No
deepseek-v4-flash subagent runtime was available in this execution
environment, so the bounded packet was executed directly by the Codex
executor with PLANNING_DISABLED semantics. No provider substitution occurred
(mimo or any other model was not used); the requested-vs-actual routing
discrepancy is recorded here and in the canonical handoff.

## 10. Handoff and next steps

This handoff remains **HANDOFF_PENDING_ACCEPTANCE** for INT re-gate. The
repair is DEPARTMENT-qualified only; `DEPARTMENT GREEN` is not
`INTEGRATION GREEN` and no promotion is authorized. INT should re-run the
composed Wave-3 boundary (real CORE ReviewService + L2 consent persistence +
LEARNER acknowledgement listing) and confirm the listing returns 200 while
excluding `tutor_consent` rows with durable consent data preserved.

Remaining dependencies (unchanged by this repair): INT consolidated Wave-3
re-gate; INT regeneration of the `test_wave2_router_assembly.py` +8 WU3 pin
(separately authorized, out of this packet's scope); CORE review-router
surface decision; exact-SHA promotion decision remains WAITING_USER.

## 11. Artifacts

- This report:
  `docs/integration/pdw3-wu5-learner-consent-ack-repair-20260812/LEARNER-WU5-CONSENT-ACK-REPAIR-REPORT.md`
- Canonical handoff:
  `docs/integration/pdw3-wu5-learner-consent-ack-repair-20260812/LEARNER-WU5-CONSENT-ACK-REPAIR-CANONICAL-HANDOFF.json`
- Evidence facts:
  `verification/pdw3-wu5-learner-consent-ack-repair-20260812/reproduction_and_run_facts.json`
- Test logs under `verification/pdw3-wu5-learner-consent-ack-repair-20260812/logs/`
- Regression test:
  `tests/learner/test_wu5_consent_ack_boundary.py`
