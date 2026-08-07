# 03 -- Versioning Contract (D-29 Scope)

> **Document owner:** shared-platform-core department  
> **Baseline:** v0.9.7-D single-sourcing integration  
> **Status:** D-29 scope (app/package/API identity only)

## Purpose

This document defines which version strings are centrally managed
under the **shared platform identity** and which belong to independent
subsystem streams that must remain decoupled.

## Version streams

### 1. Platform application identity (CENTRALISED)

| Constant | Module | Current value | Consumers |
|---|---|---|---|
| `PLATFORM_APPLICATION_VERSION` | `app/version.py` | `0.9.7-d` | `Settings`, `FastAPI`, `SubmissionService.record_versions`, `ExportManifest`, API `/health` and `/version` |
| `PLATFORM_API_VERSION` | `app/version.py` | `v1` | `Settings`, lifecycle `health_dict`, API responses |
| `PLATFORM_DATABASE_MIGRATION_VERSION` | `app/version.py` | `13` | `Settings`, drift-tested against `migrations.LATEST_MIGRATION_VERSION` |

**Rule:** Every consumer that reports or records the application-level
platform identity MUST import from `app.version`. No hardcoded literals
(`"0.8.0"`, `"0.8.2"`, etc.) are permitted for these fields.

### 2. Subsystem versions (INDEPENDENT)

Each subsystem owns its own version constant and stream. These are
**not** centralised in `app/version.py` and must not be confused with
the platform identity.

| Subsystem | Example constant | Current value |
|---|---|---|
| spaCy analyzer | `spacy-analyzer-v0.8.0` | `spacy-analyzer-v0.8.0` |
| Feedback prompt | `feedback-prompt-v0.7.1` | `feedback-prompt-v0.7.1` |
| Diagnostic calibration | `diagnostic-calibration-v0.6.1` | `diagnostic-calibration-v0.6.1` |
| Structured feedback schema | `structured-feedback-v0.7.1` | `structured-feedback-v0.7.1` |
| Metric registry | `metric-registry-v0.8.0` | `metric-registry-v0.8.0` |
| CALF construct registry | `calf-construct-registry-v0.8.0` | `calf-construct-registry-v0.8.0` |
| Configuration schema | `configuration-schema-v0.8.0` | `configuration-schema-v0.8.0` |
| Learner profile | `learner-profile-v0.7.0` | `learner-profile-v0.7.0` |
| Journey / config | `journey-*`, `config-v*` | independent |
| Corpus features | `corpus-features-v*` | independent |
| Reference groups | `reference-groups-v*` | independent |
| Reference distributions | `reference-distributions-v*` | independent |

**Rule:** A subsystem version bump changes only its own module.
It does NOT require a platform version change, and vice versa.

### 3. Domain-pack / corpus-resource / feature-set / policy versions

These follow the same independent-stream principle. They are reported
through their own registries and are not part of the platform
identity contract.

## Drift-test contract

The tests in `tests/shared/test_version_single_sourcing.py` enforce:

1. **Consumer resolution:** Every app-identity consumer imports from
   `app.version` and resolves to the same constant value.
2. **Migration consistency:** `migrations.LATEST_MIGRATION_VERSION`
   equals `PLATFORM_DATABASE_MIGRATION_VERSION`.
3. **API-reported version:** The `/api/v1/system/health` and
   `/api/v1/system/version` endpoints return the platform constant
   values.
4. **Negative probe:** A monkeypatched wrong value is caught, proving
   that drift detection is live.

If any consumer drifts from the single source, the drift tests fail.

## D-29 scope boundary

This contract covers **app/package/API identity only**. It does NOT
cover:

- Subsystem version bumps (handled by respective modules)
- Schema or migration changes
- API shape changes
- UI or frontend changes
- Domain discriminator changes

## Version rationale (v0.9.7-d)

The application version is set to `0.9.7-d` to correct stale `0.8.0`
/ `0.8.2` literals that no longer reflect the closed v0.9.7-D baseline.
The trailing `-d` tag marks the development / single-sourcing
integration pass.
