# 01 — Shared Core Gap Map
**Department:** Shared Platform & Core | **Horizon:** 1
**Inspected:** 2026-08-07 | **HEAD:** b171cce | **Branch:** dept/shared-core-h1
**Baseline:** v0.9.7-D closed (core 1237/8/0, locale 600/600, migration 13, 33 tables)
**Evidence log:** `.agent-workflow/shared-core-h1/logs/wu1-inspection.log`

---

## Section 6 — Current Shared-Core Map

### 1. Composition Root

| Location | Role | Evidence |
|---|---|---|
| `app/api/main.py:create_app()` L508 | Public entry; dispatches on `settings` presence | L508–530 |
| `app/api/main.py:_run_startup()` ~L91 | Production composition (background thread) | L91–210 |
| `app/api/main.py:_build_full_app()` ~L378 | Test composition (immediate) | L378–430 |

**Current state:** Two parallel composition paths construct identical service graphs with duplicated code. `_run_startup` accesses `repository._learner_repository` (facade private attributes) ~15 times. `_build_full_app` mirrors the same construction. Both store ~30 service references on `api.state.*`. No single parameterized builder exists.

### 2. Registries

| Registry | Module | Domain-aware? | Evidence |
|---|---|---|---|
| `AnalyzerRegistry` | `app/analysis/registry.py` | No | L1–20; `get(analyzer_id)` only |
| `MetricRegistry` | `app/analysis/registry.py` | No | L22–48; `get(metric_id, version)` only |
| `AlgorithmRegistry` | `app/analysis/registry.py` | No | L50–60; list/register only |
| `CalfRegistry` | `app/calf/registry.py` | No (has `resource_requirement` filter) | L49–80; `list_specifications()` filters by `resource_requirement` |
| `ConfigurationRegistry` | `app/configuration/registry.py` | No | L30–35; wraps prompt/metric/algorithm/analyzer |
| `PromptRegistry` | `app/configuration/registry.py` | No | L10–28; `get(prompt_version)` only |

**Current state:** None of the 5 registry families have `select_for_domain` or any domain-aware selection policy. The CALF registry has `resource_requirement` filtering on `MeasurementSpecification` but no domain dimension.

### 3. Config Loading

| Item | Evidence |
|---|---|
| `app/config/settings.py:Settings` dataclass | L19–47; frozen, no domain field |
| `app/config/settings.py:load_settings()` | L50–81; reads `.env`, no domain config |
| `app/configuration/schemas.py:ConfigurationPayload` | L22–120; `extra="forbid"`, no domain field |
| `app/configuration/schemas.py:ConfigurationVersion` | L130–146; no domain column |
| `configuration_versions` table | `migrations.py` migration 6; no domain column |

**Current state:** Configuration is single-active/hash with no domain dimension. `ConfigurationPayload` uses `extra="forbid"` so adding a domain field requires a schema version bump.

### 4. Version Constants

| Location | Value | Evidence |
|---|---|---|
| `app/config/settings.py:25` | `application_version = "0.8.0"` | settings.py L25 |
| `app/config/settings.py:26` | `database_migration_version = 10` (stale; actual = 13) | settings.py L26 |
| `app/api/main.py:452` | `FastAPI(title=..., version="0.8.0")` hardcoded | main.py L452 |
| `app/api/main.py:523` | `FastAPI(title=..., version="0.8.0")` | main.py L523 |
| `app/services/submission.py:100` | `"application": "0.8.0"` hardcoded | submission.py L100 |
| `app/analysis/spacy_analyzer.py:22` | `version = "spacy-analyzer-v0.8.0"` | spacy_analyzer.py L22 |
| `app/calf/schemas.py:79` | `construct_version = "0.8.0"` | schemas.py L79 |
| `app/research/schemas.py:158` | `application_version = "0.8.2"` | schemas.py L158 |

**Current state:** Version is scattered across 8+ locations with inconsistent values (0.8.0 vs 0.8.2 vs stale migration_version=10). No `app/version.py` or single-source version constant exists.

### 5. Submission Identity

| Item | Evidence |
|---|---|
| `app/models/schemas.py:EssaySubmission` | L35–72; the canonical submission model |
| `app/api/schemas.py:SubmissionCreateRequest` | L17; `class SubmissionCreateRequest(EssaySubmission)` |
| `app/api/routers/submissions.py:22` | `POST /api/v1/submissions` accepts `SubmissionCreateRequest` |
| `essays` table schema | `repository.py` SCHEMA; `essay_id AUTOINCREMENT`, `student_id`, `writing_prompt`, `genre`, `draft_stage`, `timed`, `time_limit_minutes`, `tool_use`, `essay_text`, `submitted_at` + revision/timing columns |

**Current state:** Submission identity is `essay_id` (autoincrement). `genre` is free-text. No `domain` or `language` field on the model or in the table. No `task_type` field.

### 6. Task Metadata (genre/task_type)

| Item | Evidence |
|---|---|
| `app/models/schemas.py:EssaySubmission.genre` | L38; `genre: str = "argumentative essay"` (free-text) |
| `app/services/learner_model.py:333–344` | `_cluster_key()` infers `purpose` from genre substring |
| `app/learner/history.py:90–107` | `_classify()` uses `genre` for comparability; free-text equality |

**Current state:** Genre is free-text with substring-based purpose inference (`"argument" in genre`). No `TaskTypeRegistry` exists. No typed task identity. D-22 notes this as a known inference to be replaced.

### 7. Language Metadata

| Item | Evidence |
|---|---|
| `app/config/settings.py:34` | `spacy_model = "en_core_web_sm"` (hardcoded default) |
| `app/analysis/spacy_analyzer.py:22` | `version = "spacy-analyzer-v0.8.0"` (English spaCy) |
| `app/analyzer/basic.py` | `[A-Za-z]` regex, English connectives/stopwords |
| `app/config/settings.py:25` | `application_version = "0.8.0"` (English-centric) |

**Current state:** System is English-centric with no language discriminator. `en_core_web_sm` is hardcoded default. No language-aware analyzer selection. No `language` field on submissions or in schema.

### 8. Repository Interfaces/Protocols

| Location | Evidence |
|---|---|
| `app/repositories/protocols.py` | Vestigial; only `RevisionRepository` (10 methods) |
| `app/api/ports.py` | 9 consumer-owned Protocol classes |
| `app/infrastructure/sqlite/repositories/` | 9 adapter modules; no domain column in any table |

**Current state:** Repository protocols are split between vestigial `repositories/protocols.py` and consumer-owned `api/ports.py`. No protocol references domain or language. All SQLite adapters operate on the existing 33-table schema.

### 9. API/Application Boundaries

| Item | Evidence |
|---|---|
| `app/api/routers/` | 10 routers (admin, analysis, calf, journey, practice, research, revisions, students, submissions, system) |
| `tests/contracts/api_surface_contract.py` | 106 classified endpoint tuples |
| `app/api/schemas.py` | `SubmissionCreateRequest`, `SubmissionResponse`, `SubmissionRecordResponse`, `HealthResponse`, `VersionResponse` |
| `app/ui/api_client.py` | HTTP-only client (~64 methods); no domain references |

**Current state:** API surface is stable with 106 endpoints. No domain-scoped endpoints exist. `POST /api/v1/submissions` is the primary additive touch point for the domain discriminator. Contract classification is 'A' (additive-only).

### 10. Corpus Intelligence Integration Points

| Item | Evidence |
|---|---|
| `app/corpus/resource.py` | `CorpusResourceDescriptor` with provenance; `get_corpus_resource()` cached accessor |
| `app/corpus/features.py` | Feature extraction (14 features, `corpus-features-v0.1.0`) |
| `app/corpus/groups.py` | Reference group membership (75 groups) |
| `app/corpus/distributions.py` | Feature distributions (1,050 records) |
| `app/corpus/intelligence.py` | `get_feature_distribution()` query interface |
| `app/calf/registry.py:60–76` | `resource_requirements` field on `MeasurementSpecification`; filterable via `list_specifications(resource_requirement=...)` |

**Current state:** Corpus intelligence is Stage 5 complete (SWECCL2 package). CALF has `resource_requirements` field but all specs have empty lists. No domain-scoped corpus profile. Corpus is domain-agnostic at this layer. Boundary contract is in place but not domain-aware.

### 11. L2 Default Assumptions

| Assumption | Evidence |
|---|---|
| English-centric NLP | `en_core_web_sm` default; `BasicAnalyzer` `[A-Za-z]` regex |
| Genre free-text with substring inference | `learner_model.py:333–344` |
| No explicit L2 domain declaration | L2 is the implicit default everywhere |
| Single-domain pipeline | No domain discriminator; all code assumes one domain |

**Current state:** The entire system operates as L2 English Writing by assumption, never by declaration. This is the known debt that Horizon 1 addresses.

---

## Section 7 — Horizon-1 Item Classification

### Item 1: Composition-Root Consolidation
**Classification: IMPLEMENT**

**Evidence:** `app/api/main.py` has two parallel composition paths (`_run_startup` ~L91 and `_build_full_app` ~L378) that construct identical service graphs with duplicated code. Both access `repository._learner_repository` (facade private attributes). `create_app()` ~L430 dispatches on `settings` presence but does not unify the builder. No single parameterized builder exists.

**Gap:** Consolidation into a single parameterized builder that both production and test paths use. This is prerequisite for adding domain dimension to the composition.

### Item 2: Version Single-Sourcing
**Classification: IMPLEMENT**

**Evidence:** Version constants are scattered across 8+ locations: `settings.py:25` (`"0.8.0"`), `settings.py:26` (`database_migration_version=10`, stale), `main.py:432` (`"0.8.0"` hardcoded), `main.py:378` (`"0.8.0"` hardcoded), `submission.py:100` (`"0.8.0"`), `spacy_analyzer.py:22` (`"spacy-analyzer-v0.8.0"`), `calf/schemas.py:79` (`"0.8.0"`), `research/schemas.py:158` (`"0.8.2"`). No `app/version.py` exists. `database_migration_version` in Settings is stale (10 vs actual 13).

**Gap:** Create `app/version.py` (or equivalent) as single source of truth for `application_version`, `database_migration_version`, and other version constants. Update all consumers to import from it.

### Item 3: Additive Domain Discriminator (Vocabulary Decision)
**Classification: IMPLEMENT**

**Evidence:** No `domain` field exists anywhere: not on `EssaySubmission` (`app/models/schemas.py:35–72`), not in `essays` table (`app/database/repository.py:27` SCHEMA), not in any migration (`app/database/migrations.py`), not on `SubmissionCreateRequest` (`app/api/schemas.py:17`), not in `ConfigurationPayload` (`app/configuration/schemas.py:22`). No `domain` discriminator concept exists in the codebase.

**Gap:** Vocabulary decision (D-01, D-17) → additive migration 14+ → API additive field on `POST /api/v1/submissions` → schema CHECK constraint. Touch points: `app/models/schemas.py:EssaySubmission`, `app/api/schemas.py:SubmissionCreateRequest`, `app/api/schemas.py:SubmissionRecordResponse`, `app/api/routers/submissions.py`, `essays` table, `app/ui/api_client.py`. Design is additive-only; no existing behavior changes.

### Item 4: Additive Language Discriminator
**Classification: IMPLEMENT**

**Evidence:** No `language` field exists anywhere in the codebase. All NLP is English-centric: `en_core_web_sm` default (`settings.py:34`), `BasicAnalyzer` `[A-Za-z]` regex (`analyzer/basic.py`), English connectives/stopwords. No language-aware analyzer selection.

**Gap:** Additive `language` field alongside `domain`. Touch points same as Item 3 plus: analyzer selection logic, configuration payload, connective resources. D-28 notes this as "language semantics decision or drop" — decision deferred to department Goal.

### Item 5: Server-Derived Domain Attribution
**Classification: IMPLEMENT**

**Evidence:** No domain attribution exists. `POST /api/v1/submissions` (`app/api/routers/submissions.py:22`) passes `SubmissionCreateRequest` directly to `submission_service.submit()` with no server-side domain derivation. No resolver concept exists.

**Gap:** Server-side domain attribution resolver (D-21) that derives domain from submission metadata when not explicitly provided. Must be additive and not change existing submission behavior for missing domain.

### Item 6: Registry Domain-Selection Policy
**Classification: IMPLEMENT**

**Evidence:** All 5 registries lack domain-aware selection:
  - `AnalyzerRegistry.get(analyzer_id)` (`app/analysis/registry.py:14–17`)
  - `MetricRegistry.get(metric_id, version)` (`app/analysis/registry.py:32–38`)
  - `CalfRegistry.list_specifications()` (`app/calf/registry.py:49–80`) — has `resource_requirement` filter but no domain filter
  - `ConfigurationRegistry` (`app/configuration/registry.py:30–35`) — wraps other registries; no domain policy
  - `PromptRegistry.get(prompt_version)` (`app/configuration/registry.py:19–22`)

**Gap:** Add `select_for_domain` (or equivalent) to each registry so domain departments can scope their implementations. Prerequisite: Item 3 vocabulary decision.

### Item 7: TaskTypeRegistry Namespace/Domain Readiness
**Classification: IMPLEMENT**

**Evidence:** No `TaskTypeRegistry` exists anywhere. No `FeedbackDimensionRegistry` exists. Current registries: `AnalyzerRegistry`, `MetricRegistry`, `AlgorithmRegistry`, `CalfRegistry`, `PromptRegistry`, `ConfigurationRegistry`. Task type is free-text `genre` field on `EssaySubmission`. No typed task identity.

**Gap:** Design and implement `TaskTypeRegistry` (namespace-scoped per D-26) and `FeedbackDimensionRegistry` (with availability/learner_exposure axes). Content deferred to domain departments; schema/structure is Shared Platform & Core.

### Item 8: Shared Epistemic-Status Vocabulary
**Classification: IMPLEMENT**

**Evidence:** No shared epistemic-status vocabulary exists. Ad-hoc usage:
  - `app/journey/service.py:37`: `CONFIRMED_RECORD = "confirmed_record"` (journey events)
  - `app/models/schemas.py:154`: `HistoryEvidence.evidence_status: str | None = None` (loose string)
  - `app/core/longitudinal_models.py:250`: `evidence_status: Literal["verified", "partially_verified", "insufficient_evidence"]` (scoped to longitudinal)
  - No `epistemic_status` field exists anywhere.

**Gap:** Define shared epistemic-status vocabulary (taxonomy). Persistence form is `Researcher decision required` per D-30. No persistence change needed yet; vocabulary document + type alias.

### Item 9: Shared Evidence-Status Vocabulary
**Classification: IMPLEMENT**

**Evidence:** Evidence-status values are scattered:
  - Journey: `"confirmed_record"` (`journey/service.py:37`)
  - HistoryEvidence: `str | None` (`models/schemas.py:154`)
  - Longitudinal: `Literal["verified", "partially_verified", "insufficient_evidence"]` (`core/longitudinal_models.py:250`)
  - UI: `evidence_status: str = ""` (`ui/components.py:409`)
  - No shared type or vocabulary.

**Gap:** Define shared evidence-status vocabulary. Consolidate ad-hoc values into a shared type. Persistence form: `Researcher decision required`.

### Item 10: Domain-Pack Boundary
**Classification: IMPLEMENT**

**Evidence:** No `domain_packs` directory exists. No domain-pack-related code exists. `03_SHARED_CORE_AND_DOMAIN_BOUNDARIES.md` references `domain_packs` per D-26. Configuration payload (`app/configuration/schemas.py`) has no domain-pack concept.

**Gap:** Define domain-pack boundary contract (read-only, versioned, provenance-tracked per D-26). Layout under `domain_packs/` directory. Shared Platform & Core owns the boundary; domain departments own content.

### Item 11: Submission Ancestry/Domain Resolver
**Classification: IMPLEMENT**

**Evidence:** `SubmissionCreateRequest` inherits `EssaySubmission` which has `revision_of_submission_id: int | None` (`models/schemas.py:64`) for revision linkage but no domain resolver. `app/revision/` handles revision alignment but not domain attribution. No ancestry-based domain derivation exists.

**Gap:** Domain resolver that can derive domain from submission ancestry (revision chain) when not explicitly provided. Must be additive and not change existing revision behavior.

### Item 12: Shared Resource/Boundary Compatibility with Stage-5 Corpus Intelligence
**Classification: ALREADY SATISFIED**

**Evidence:** `app/corpus/resource.py` provides `CorpusResourceDescriptor` with provenance tracking and `get_corpus_resource()` cached accessor. `app/calf/registry.py:60–76` has `resource_requirements` field on `MeasurementSpecification` filterable via `list_specifications(resource_requirement=...)`. Corpus boundary contract is in place (read-only, versioned, provenance-tracked). Stage 5 corpus intelligence (features, groups, distributions, intelligence) is complete.

**Current state:** The boundary contract exists. Domain-scoped corpus profiles are a Horizon 2 concern (blocked until corpus authorization D1, licensing D3, band method D4, feature-set scope D8). No additional Shared Platform & Core work needed for the boundary itself.

### Item 13: Architecture-Drift Checks Relevant to Shared Contracts
**Classification: IMPLEMENT**

**Evidence:**
  - 12 sync-conflict files referenced in `01_CURRENT_STATE_MAP.md` §5 (not present in this worktree; may be in main repo or cleaned)
  - `app/api/main.py` duplicated composition blocks (~L91 vs ~L378) accessing facade private attributes
  - Version constants scattered across 8+ locations with inconsistent values
  - DDL split between `repository.SCHEMA` and `migrations.py`
  - No module-set manifest or quarantine/exclusion policy exists (D-27)
  - No API-surface contract regeneration with additive-only diff (D-37/RT-19)
  - No domain-isolation invariant list (D-31)

**Gap:** Create canonical module-set manifest, quarantine/exclusion policy, sync-conflict drift check, API-surface contract regeneration, and domain-isolation invariant list.

---

## Section 8 — Classification Summary

| # | Horizon-1 Item | Classification | Key Gap |
|---|---|---|---|
| 1 | Composition-root consolidation | **IMPLEMENT** | Two parallel paths; no parameterized builder |
| 2 | Version single-sourcing | **IMPLEMENT** | 8+ scattered locations; stale `database_migration_version` |
| 3 | Additive domain discriminator | **IMPLEMENT** | No domain field anywhere; vocabulary decision pending |
| 4 | Additive language discriminator | **IMPLEMENT** | No language field; English-centric; D-28 decision pending |
| 5 | Server-derived domain attribution | **IMPLEMENT** | No resolver concept exists |
| 6 | Registry domain-selection policy | **IMPLEMENT** | 5 registries lack `select_for_domain` |
| 7 | TaskTypeRegistry namespace/domain readiness | **IMPLEMENT** | No registry exists; genre is free-text |
| 8 | Shared epistemic-status vocabulary | **IMPLEMENT** | No shared vocabulary; ad-hoc strings only |
| 9 | Shared evidence-status vocabulary | **IMPLEMENT** | Scattered across 4+ locations with inconsistent types |
| 10 | Domain-pack boundary | **IMPLEMENT** | No directory, no contract, no code |
| 11 | Submission ancestry/domain resolver | **IMPLEMENT** | No resolver concept; only revision linkage exists |
| 12 | Shared resource/boundary compat with Stage-5 | **ALREADY SATISFIED** | Boundary contract in place; domain profiles are H2 |
| 13 | Architecture-drift checks | **IMPLEMENT** | No manifest, no quarantine policy, no invariant list |

**Counts:** IMPLEMENT = 12, ALREADY SATISFIED = 1, DEFER = 0, ARCHITECTURE ESCALATION = 0

---

## Section 9 — Migration-Relevant Storage Facts

| Fact | Evidence |
|---|---|
| Current PRAGMA user_version | 13 (`migrations.py:LATEST_MIGRATION_VERSION = 13`) |
| schema_migrations table | Present; tracks applied migrations |
| `domain` column on `essays` | **Does not exist** |
| `language` column on `essays` | **Does not exist** |
| CHECK constraint on domain | **Does not exist** |
| Export-time domain validation | **Does not exist** |
| `ConfigurationPayload.extra` | `"forbid"` — additive domain field requires schema version bump |
| Additive domain storage feasibility | **Safe via ALTER TABLE ADD COLUMN** with `DEFAULT 'l2'` (additive, non-destructive). Requires migration 14+. Decision left to orchestrator. |

**Key constraint:** Migration 14+ must be additive only (CHECK + DEFAULT, no backfill per D-17/D-36). Existing rows get default domain value. No destructive changes to frozen schema.

---

## Section 10 — API Surface Touch Points for Additive Domain Field

| Touch Point | Current State | Additive Impact |
|---|---|---|
| `POST /api/v1/submissions` body | `SubmissionCreateRequest(EssaySubmission)` — no domain field | Additive field on `EssaySubmission`; backward-compatible |
| `app/api/schemas.py:SubmissionRecordResponse` | No domain field | Additive field for round-trip |
| `app/ui/api_client.py` | No domain references | Additive field if needed |
| `tests/contracts/api_surface_contract.py` | 106 endpoints classified | Contract regeneration with additive-only diff (D-37/RT-19) |
| `app/models/schemas.py:EssaySubmission` | Source model for API shape | Additive field here propagates to API |

**Note:** All touch points are additive-only. No existing endpoint behavior changes. Contract regeneration is a named Horizon 1 step per D-37/RT-19.

---

## Section 11 — Sync-Conflict/Duplicate File Inventory

| Pattern | Count in Worktree | Notes |
|---|---|---|
| `*冲突*` | 0 | Referenced in `01_CURRENT_STATE_MAP.md` §5 as12 files in main repo |
| `*Copy*` | 0 | Not present |
| `*副本*` | 0 | Not present |

**Note:** The current state map references12 `*-冲突-Rain_Win11.py` sync-conflict files. These are not present in this worktree (`dept/shared-core-h1`). They may exist in the main repo or have been cleaned. D-27 requires a canonical module-set manifest and drift check before any measurement-version claim.

---

## Section 12 — Concrete Gaps (No Invented Abstractions)

1. **Composition root duplication:** Two parallel service-graph constructions in `main.py` (~L91 and ~L378) with identical code accessing facade private attributes.
2. **Version fragmentation:** 8+ hardcoded version strings with stale `database_migration_version=10` in Settings.
3. **No domain dimension:** Zero domain fields in models, API, schema, configuration, or storage.
4. **No language dimension:** English-centric assumptions hardcoded in analyzer, config, and NLP defaults.
5. **No registry domain policy:** All 5 registries lack domain-aware selection methods.
6. **Free-text genre:** `EssaySubmission.genre` is free-text with substring inference; no typed task identity.
7. **No shared vocabularies:** Epistemic-status and evidence-status are ad-hoc strings scattered across 4+ locations.
8. **No domain-pack boundary:** No directory, contract, or code for domain-scoped content.
9. **No drift checks:** No module-set manifest, quarantine policy, or contract regeneration tooling.
10. **No domain resolver:** No server-side domain attribution from submission metadata or ancestry.

---

## Section 13 — Acceptance Criteria Verification

| Criterion | Status | Evidence |
|---|---|---|
| 1. Deliverable at `docs/departments/shared-platform-core/h1/01_SHARED_CORE_GAP_MAP.md` | ✅ | This file |
| 2. All 13 items classified with file:line evidence | ✅ | Section 7 |
| 3. Section-6 map covers full list | ✅ | Section 6 (11 subsections) |
| 4. Concrete gaps only; YAGNI respected | ✅ | Section 12 |
| 5. Migration storage facts section | ✅ | Section 9 |
| 6. No production/test file modified | ✅ | `git status` clean except `.agent-workflow/` |
