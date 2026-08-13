# CORE WU2 changed files (bounded write scope only)

Product / shared contracts (all inside `app/api/`, `app/review/`,
`app/infrastructure/sqlite/` write scope):

| File | Change |
| --- | --- |
| `app/api/deps.py` | Added canonical `get_review_service` and `get_review_evidence_lookup` dependency getters (503 fail-closed when not composed). |
| `app/api/main.py` | Imported `SQLiteReviewEvidenceLookup`; composed the shared adapter at the single `_apply_service_state` assignment point (`api.state.review_evidence_lookup`). Existing `review_service` / `review_repository` wiring retained unchanged. |
| `app/api/routers/review.py` | Delegates `get_review_service` to the canonical deps getter (removed the duplicate local implementation; `__all__` export preserved). |
| `app/review/protocols.py` | Added `ReviewEvidenceLookupProtocol` (owner_of / get_record) — shared mechanical evidence-lookup boundary. |
| `app/review/__init__.py` | Exports `ReviewEvidenceLookupProtocol` from the shared package root. |
| `app/infrastructure/sqlite/repositories/review.py` | Added `SQLiteReviewEvidenceLookup` — learner-scoped, fail-closed lookup over `practice_activities` / `review_events` (PA*/RE* ids). |

Tests (all inside `tests/review/` write scope):

| File | Change |
| --- | --- |
| `tests/review/test_review_composition.py` | +4 tests: deps getters resolve composed instances; CORE `ReviewService` satisfies the LEARNER `CoreReviewServicePort` structural mirror; LEARNER-shaped practice record consumed by the shared service; composed evidence lookup is learner-scoped. |
| `tests/review/test_review_repository.py` | +2 tests: evidence-lookup owner/record round trip; close/reopen durability of the lookup on the single SQLite file. |
| `tests/review/test_review_fail_closed_api.py` | +1 test: deps getters fail closed 503 when not composed. |

Evidence (inside `docs/integration/` write scope):

| Path | Purpose |
| --- | --- |
| `docs/integration/pdw3-wu2-core-composition-repair-20260812/evidence/` | Probe script/log, pytest logs, git-status snapshots, this file. |
| `docs/integration/pdw3-wu2-core-composition-repair-20260812/CORE-WU2-DEPARTMENT-HANDOFF.md` | Human-readable handoff report. |
| `docs/integration/pdw3-wu2-core-composition-repair-20260812/CORE-WU2-DEPARTMENT-HANDOFF.json` | Schema-valid machine-readable handoff. |

Not touched: `app/database/`, `app/version.py`, `pyproject.toml`, `uv.lock`,
Program Control, other worktrees, Git history, master, migrations, or any
tracked root test outside `tests/review/`.
