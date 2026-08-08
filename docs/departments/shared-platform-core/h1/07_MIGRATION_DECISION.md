# Migration Decision: NO Migration 14 in H1

**Version**: 1.0 (H1)
**Decision references**: D-01, D-30, D-36
**Status**: Active — shared-platform-core H1

---

## Decision

**NO migration 14 in H1.** The current migration level stays at 13.

---

## Justification

1. **D-01 — All rows are l2**: Every existing row in the database represents an L2 submission. There is no data to migrate; the default domain (`l2`) and language (`en`) are implicit in all historical records.

2. **D-30 — Migration gate stays at 13**: The migration version gate is frozen at 13 for H1. Adding a migration would require re-running all verification gates (focused, affected regression, full core, launcher).

3. **Migration authority (04 §6)**: Migration 13 remains the authority; migration 14+ is reserved for a future implementation Goal with Architecture & Integration review. No schema change is needed for domain/language attribution in H1 because the attribution is server-derived and not persisted per-row.

4. **D-36 — Pre-migration validation**: The domain/language discriminator operates at the API layer (server derivation + advisory validation). It does not require database columns because:
   - All submissions are attributed server-side on creation.
   - The attribution is included in the API response.
   - No query-by-domain or filter-by-language is needed in H1.

5. **Additive-only scope**: The H1 deliverable is a minimal additive discriminator. Adding database columns (migration 14) would expand scope beyond the approved task.

---

## Deferred Migration-14 Design (FOR ARCHITECTURE & INTEGRATION REVIEW)

The following design is explicitly deferred and NOT created in H1.

### Proposed schema (for future review)

```sql
ALTER TABLE essays ADD COLUMN domain TEXT NOT NULL DEFAULT 'l2'
    CHECK (domain IN ('l2', 'academic'));
ALTER TABLE essays ADD COLUMN language TEXT NOT NULL DEFAULT 'en';
```

### Properties

- **Default**: `domain = 'l2'`, `language = 'en'` (all existing rows backfilled by default)
- **Backfill**: No backfill needed; `DEFAULT` handles all existing rows.
- **Rollback**: One-step rollback (`ALTER TABLE essays DROP COLUMN domain; ALTER TABLE essays DROP COLUMN language;`)
- **Validation**: `CHECK` constraint enforces closed-set vocabulary at the database level.

### When to create migration 14

- When per-row domain/language persistence is needed for export filtering.
- When Academic Writing becomes a functioning product domain.
- When the Architecture & Integration team reviews and approves this design.

---

## Implications

- Domain/language attribution remains API-layer only in H1.
- No database schema change; no migration; no backfill.
- The discriminator is fully functional at the API level without persistence.
