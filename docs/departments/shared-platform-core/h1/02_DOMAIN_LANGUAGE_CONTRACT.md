# Domain/Language Contract

**Version**: 1.0 (H1)
**Decision references**: D-01, D-17, D-21, D-22, D-28, D-36
**Status**: Active — shared-platform-core H1

---

## 1. Closed-Set Vocabulary

### Domain

| Value | Status | Description |
|---|---|---|
| `l2` | **Functional (default)** | L2 English writing feedback. Only functional product domain in H1. |
| `academic` | **Reserved (NOT functional)** | Academic writing. Reserved for future use; must NOT be exposed as a functioning product domain. |

- `legacy_unclassified` is task_type semantics (D-22), NOT a domain value.
- All current workflow surfaces derive `l2`.
- The domain vocabulary is a closed `str` enum; unknown values are rejected.

### Language

| Value | Status | Description |
|---|---|---|
| `en` | **Functional (default)** | English submission language. Only verified pipeline language in H1. |

- Distinct from UI locale and learner L1.
- The language vocabulary is a closed `str` enum; unknown values are rejected.

---

## 2. Server-Side Derivation

**Attribution rule**: `domain-attribution-v0.1.0` (version `0.1.0`)

All submissions are attributed server-side. The derivation is deterministic:

| Surface | Domain | Language |
|---|---|---|
| submissions | l2 | en |
| revisions | l2 | en |
| practice | l2 | en |
| research | l2 | en |

No re-attribution branch is reachable in H1 (no Academic surface exists).

---

## 3. Client Advisory Fields

The `POST /api/v1/submissions` request accepts optional advisory fields:

```json
{
  "advisory_domain": "l2",
  "advisory_language": "en"
}
```

- Both fields are optional (defaults to `null`).
- Advisory values are validated against the server-derived attribution.
- **Mismatch or invalid → 422 rejection** with the canonical error envelope.
- Client advisory NEVER overrides server derivation (D-36).

### Advisory validation rules

| Scenario | Result |
|---|---|
| Both absent (`null`) | Accepted silently |
| `advisory_domain=l2`, `advisory_language=en` | Accepted (matches derived) |
| `advisory_domain=academic` | **422** — domain mismatch |
| `advisory_domain=nonexistent` | **422** — invalid domain |
| `advisory_language=zh` | **422** — invalid language |
| `advisory_language=fr` | **422** — invalid language |

---

## 4. Response Serialization

Every successful `POST /api/v1/submissions` response includes:

```json
{
  "domain": "l2",
  "language": "en",
  "domain_attribution_rule": "domain-attribution-v0.1.0",
  "domain_attribution_version": "0.1.0"
}
```

- These fields are additive (present on all new responses).
- Legacy payloads (without advisory fields) are still accepted.
- GET `/api/v1/submissions/{id}` does not include domain fields (POST-only attribution).

---

## 5. Validation

`validate_domain_scope(value)` accepts only values in the closed-set vocabulary.
Used by future export wiring (Research Evaluation owns wiring; utility provided).

---

## 6. Client Cannot Relabel

- Advisory mismatch is rejected at POST time (422).
- No endpoint accepts client domain as authoritative for existing records.
- Historical records retain their original server-derived attribution.

---

## 7. Examples

### Missing advisory (legacy payload)

```json
POST /api/v1/submissions
{
  "student_id": "STU-001",
  "writing_prompt": "Write an essay.",
  "essay_text": "..."
}

→ 201 Created
{
  "domain": "l2",
  "language": "en",
  "domain_attribution_rule": "domain-attribution-v0.1.0",
  "domain_attribution_version": "0.1.0",
  ...
}
```

### Matching advisory

```json
POST /api/v1/submissions
{
  "student_id": "STU-002",
  "writing_prompt": "Write about technology.",
  "essay_text": "...",
  "advisory_domain": "l2",
  "advisory_language": "en"
}

→ 201 Created (same as above)
```

### Mismatched advisory (rejected)

```json
POST /api/v1/submissions
{
  "student_id": "STU-003",
  "writing_prompt": "Write about education.",
  "essay_text": "...",
  "advisory_domain": "academic"
}

→ 422 Unprocessable Entity
{
  "error": {
    "category": "invalid_request",
    "message_key": "error_invalid_request",
    "operation": "request",
    "http_status": 422,
    "detail": "domain mismatch: client advisory 'academic' differs from server-derived 'l2'"
  }
}
```

---

## 8. Migration Decision

**No migration 14 in H1.** See `07_MIGRATION_DECISION.md` for justification.
Per-row persistence is deferred with documented design for Architecture & Integration review.

## 9. Language drop option (D-28)

Per D-28, if no real consumer for the language discriminator emerges by the
end of Horizon 1, the field is dropped (YAGNI). Expansion of the closed
language vocabulary requires the shared-contract change process.