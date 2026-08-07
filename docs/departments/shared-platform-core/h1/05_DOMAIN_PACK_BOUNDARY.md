# 05 — Domain Pack Boundary

**Status:** Draft (WU6-DOMAIN-PACKS)
**References:** D-14, D-26, D-L2-01, D-L2-03, 04_REGISTRY_DOMAIN_POLICY.md

---

## 1. Purpose

Domain packs are versioned JSON/data files under per-domain namespaces that ship domain-specific content. The Shared Platform Core owns the **mechanism** (layout, loader, validation). Domain departments own the **content**.

This document defines the pack identity fields, namespace layout, ownership boundaries, and relationship to the existing configuration-version machinery.

---

## 2. Namespace Layout

```
app/configuration/domain_packs/
  {domain}/
    {version}/
      manifest.json
      ... (future data files)
```

- `{domain}`: one of `l2` | `academic` (closed set, same as `Domain` enum)
- `{version}`: `vX.Y.Z` format (e.g., `v0.1.0`)
- `manifest.json`: required; contains pack identity and content-status metadata

---

## 3. Pack Identity Fields

| Field | Type | Description |
|-------|------|-------------|
| `pack_id` | string | Unique identifier (e.g., `l2-core-v0.1.0`) |
| `domain` | string | Must match namespace directory |
| `version` | string | Must match version directory; `vX.Y.Z` format |
| `supported_task_types` | list | Task types in this pack (empty in H1) |
| `dimensions` | list | Feedback dimensions in this pack (empty in H1) |
| `resource_requirements` | list | Runtime resources needed (empty in H1) |
| `availability` | string | Pack availability status |
| `content_status` | dict | Per-field NR/blocked notes with decision references |

---

## 4. Ownership

| Layer | Owner | Responsibility |
|-------|-------|----------------|
| Mechanism | Shared Core | Loader, validation, namespace enforcement, manifest schema |
| Content | Domain departments | Task-type enumeration, dimension membership, resource requirements |

Shared Core provides `load_pack(domain, version)` which validates the manifest and returns the data. It does **not** wire packs into product runtime behavior.

---

## 5. L2 Representability

The L2 domain pack (`l2/v0.1.0/manifest.json`) demonstrates that L2 domain behavior is representable under this mechanism without semantic change. Content lists are empty because domain-content decisions are blocked:

- `supported_task_types: []` — blocked by D-L2-01
- `dimensions: []` — blocked by D-L2-01
- `resource_requirements: []` — no domain-specific requirements yet

When D-L2-01 is resolved, the L2 domain department populates these lists. The mechanism remains unchanged.

---

## 6. Academic Exclusion

No academic pack exists under `app/configuration/domain_packs/academic/`. The `domain_exists("academic")` check returns `False`. Attempting to `load_pack("academic", ...)` raises `DomainPackNotFoundError`.

This is intentional: academic is a reserved namespace (D-22) with no functional content in H1. A future academic domain department would create `academic/v0.1.0/manifest.json` when ready.

---

## 7. Blocked Content

| Block | Scope | Status |
|-------|-------|--------|
| D-L2-01 | L2 task-type enumeration, dimensions | Researcher decision required |
| D-L2-03 | Academic task taxonomy | Researcher decision required |

Pack content lists are explicitly empty with NR/blocked notes in `content_status`. This is the H1 baseline; content arrives when decisions are made.

---

## 8. Relationship to Configuration-Version Machinery (D-14)

Domain packs ride the existing configuration machinery. They do **not** introduce a parallel configuration system:

- `ConfigurationPayload` and `ConfigurationVersion` remain the single-active configuration mechanism
- Domain packs are data files loaded by a standalone loader; they do not replace, extend, or conflict with `ConfigurationPayload`
- Pack versioning (`v0.1.0`) is independent of configuration versioning (`config-v0.8.x`)
- Future integration (post-H1) would reference pack versions from configuration, not merge them

The loader is a pure data-access function: read manifest, validate, return. No side effects, no state mutation, no runtime coupling.

---

## 9. Loader API

```python
from app.configuration.domain_packs_loader import load_pack, domain_exists, list_available_packs

# Load a specific pack.
manifest = load_pack("l2", "v0.1.0")

# Check domain existence.
exists = domain_exists("l2")  # True
exists = domain_exists("academic")  # False

# List all available packs.
packs = list_available_packs()  # [{"domain": "l2", "version": "v0.1.0"}]
```

### Error hierarchy

- `DomainPackError` — base
- `DomainPackNotFoundError` — domain or version not found
- `DomainPackValidationError` — manifest schema/content invalid
- `DomainPackNotRegisteredError` — domain exists but no pack registered

---

## 10. Test Coverage

`tests/shared/test_domain_packs.py` covers:

1. L2 pack loads under its own namespace
2. Unknown domain rejected
3. Unknown version rejected
4. Malformed manifest rejected (missing keys, domain mismatch, invalid JSON)
5. Academic namespace returns explicit not-registered state
6. No academic pack exists
7. Pack identity fields valid
8. Content lists empty with explicit NR/blocked status

All 24 tests pass alongside existing shared tests (167 total).
