# 06 — Migration 14 Decision

**Gate:** WU10 GREEN — 2026-08-08
**Office:** Architecture & Integration (Wave-1 Integration Gate)
**Status:** Architecture decision recorded; no migration created.

## 1. Known facts (all verified on the integrated baseline)

| Fact | Verification |
| --- | --- |
| Migration 13 remains authoritative | `PLATFORM_DATABASE_MIGRATION_VERSION = 13`; `schema_migrations`/`PRAGMA user_version` untouched; no migration file added by any merged branch |
| Shared Core provides API-layer domain/language attribution | `derive_attribution` + advisory validation in the submission route; attribution returned on responses |
| Academic Foundation uses in-memory repositories only | `app/academic/repositories.py` — 8 protocols + `InMemoryRepositories`; zero SQLite/sqlite references |
| Academic has no production API or UI | zero `app.*` imports in `app/academic`; no FastAPI/Streamlit wiring; no router registration |
| Academic has no persisted submission workflow | no persistence adapters; no migration |
| Academic is not a functional product surface | `WORKFLOW_SURFACE_DOMAIN` contains no `academic` surface; domain pack absent; advisory `academic` rejected |

## 2. Disposition

**B. DEFERRED_PREREQUISITE_FOR_NEXT_WAVE** (Goal section 15 option B).

Migration 14 is NOT required to make the current integrated baseline safe, and it IS a required prerequisite for the future Academic persistence path — therefore it is not "not required by the current architecture" (option C) and not "required now" (option A).

## 3. Conditions for acceptance of disposition B (all satisfied)

| Condition (Goal section 15) | Status |
| --- | --- |
| Academic remains non-production/unregistered | PASS — no surface, no API, no pack |
| No Academic row requires persistence | PASS — in-memory only; zero persisted Academic entities |
| No cross-domain persisted query is required | PASS — no domain column exists; no query-by-domain consumer |
| Existing L2 semantics remain safe | PASS — zero L2 module edits; resolver defaults `l2`; migration 13 unchanged; full regression green |
| Future Academic persistence is explicitly gated on migration review | PASS — Shared Core `07_MIGRATION_DECISION.md` ("When to create migration 14": A&I review) + Academic handoff section 13 (migration coordinated through A&I) |

## 4. Exact trigger that makes migration 14 mandatory

Migration 14 becomes mandatory when ANY of the following first occurs:

1. An Academic persistence implementation Goal starts (first persisted Academic row/table); or
2. Any production query-by-domain or cross-domain persisted query is required (export filtering by domain, learner-level domain aggregation); or
3. Academic Writing becomes a functioning product domain surface.

## 5. Deferred design (coordination record)

The Shared Platform & Core H1 branch already produced the deferred additive design, reviewed here as the coordination baseline (no implementation):

```sql
ALTER TABLE essays ADD COLUMN domain TEXT NOT NULL DEFAULT 'l2'
    CHECK (domain IN ('l2', 'academic'));
ALTER TABLE essays ADD COLUMN language TEXT NOT NULL DEFAULT 'en';
```

Properties: additive; DEFAULT covers existing rows (no backfill); one-step non-destructive rollback (`DROP COLUMN`); CHECK enforces the closed vocabulary at DB level (D-36). Attribution provenance per row is deferred with the same migration.

Owner when triggered: **Shared Platform & Core** (default owner, Goal section 15); Architecture & Integration retains migration coordination, contract review, and integration sequencing. No speculative migration, no content-based domain inference, no destructive backfill.

## 6. Gate statement

**WU10 GREEN** — the decision is architecture-consistent: migration 14 does not exist and does not need to exist for Wave-1 integration GREEN; it is a formally recorded NEXT-WAVE prerequisite with an explicit trigger and owner.
