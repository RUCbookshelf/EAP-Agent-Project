# 09 — Architecture & Integration Handoff
**Department:** Shared Platform & Core | **Goal:** Horizon 1 Foundation | **Date:** 2026-08-07

## Starting baseline

- Worktree: `A:\EAP Agent Project\worktrees\shared-core-h1`, branch `dept/shared-core-h1`.
- On first check the branch was at `0588eee`, 2 commits BEHIND the mandated baseline `b171cce` (Stage-5 corpus work absent). Fast-forwarded `0588eee..b171cce` (branch was 0 ahead; clean tree; additive only). Starting baseline for all H1 work: **b171cce**.

## Final branch HEAD

- Final HEAD after this Goal's commits: recorded in the final report (`git rev-parse HEAD`); branch `dept/shared-core-h1`, working tree clean except untracked runtime planning state (`.agent-workflow/`, `.venv/`).

## Shared contracts changed (all additive; D-37/RT-19 recorded)

1. `POST /api/v1/submissions` request schema: optional advisory `advisory_domain` / `advisory_language` (client hints only; server-derived values authoritative; mismatch or invalid → 422 in the canonical error envelope).
2. `SubmissionResponse`: additive server-derived `domain`, `language`, `domain_attribution_rule` (`domain-attribution-v0.1.0`), `domain_attribution_version`.
3. Platform version identity: new `app/version.py` (`PLATFORM_APPLICATION_VERSION=0.9.7-d`, `PLATFORM_API_VERSION=v1`, `PLATFORM_DATABASE_MIGRATION_VERSION=13`); all app-identity consumers (Settings, FastAPI, lifecycle health, submission `record_versions`, research ExportManifest) now import it; stale 0.8.0/0.8.2/10 literals corrected (D-20/D-29).
4. API contract snapshots regenerated (D-37/RT-19): `verification/v0.9.5-h2d2/openapi_before.json` (+6 properties, info.version), `dependency_graph_before.json` (4 line shifts in submissions.py); runtime-checkable protocol count 36→39 (3 new shared protocols).

## Shared contracts intentionally unchanged

All v0.9.7 contracts: endpoint paths/methods and 106 endpoint classification; `ErrorCategory` envelope; journey event vocabulary + dedup keys (verified: 0 new event types); `PRIO-{feedback_id}-{priority_index}` grammar; configuration single-active/hash machinery; locale contract (600/600; no locale files touched); `PRAGMA user_version` + `schema_migrations` (migration 13); repository adapter signatures; research-validity boundaries; Corpus Stage-5 boundary (app/corpus untouched).

## Migration status

- **No migration created.** Migration 13 remains the authority.
- Justification (full text: `07_MIGRATION_DECISION.md`): D-01 (all legacy rows are L2 by default attribution; absence of a column exactly represents this); D-30 gate requires migration version stays 13; 04 §6 / 12 §1 / 13 §4 reserve migration 14+ for a future implementation Goal with Architecture & Integration review; D-36 anticipates the pre-migration state (app-layer + export-time validation reject unknown values).
- Deferred design FOR ARCHITECTURE & INTEGRATION REVIEW (not created): additive `essays.domain TEXT NOT NULL DEFAULT 'l2' CHECK (domain IN ('l2','academic'))` + `essays.language TEXT NOT NULL DEFAULT 'en'`; no backfill; one-step non-destructive rollback. Per-row persistence of attribution provenance is deferred to that migration.

## New shared vocabulary

- Domain: `l2` (default, functional) / `academic` (reserved, NOT functional). `legacy_unclassified` is task_type semantics (D-22), not a domain value.
- Language: `en` (only verified pipeline language; distinct from UI locale and learner L1; D-28 drop option documented).
- EpistemicStatus: `observed_descriptive` / `gated_inference` / `recommendation` / `outcome_claim` (D-09).
- EvidenceStatus: `verified` / `candidate` / `insufficient` / `suppressed` / `not_applicable` / `unavailable` / `legacy` / `unresolved`.
- AvailabilityStatus: `available` / `insufficient_evidence` / `not_applicable`; LearnerExposure: `student` / `research_only` (D-37/RT-17).
- ResourceStatus (corpus boundary I4): `corpus_not_registered` / `no_reference_group` / `insufficient_corpus_data` / `feature_incompatible` / `license_restricted`.
- Banned shared status values: `mastery`, `proficiency`, `ability_level`, `learning_gain` (drift-test enforced).
- Attribution rule id: `domain-attribution-v0.1.0`.

## Domain discriminator semantics

Server-derived at write time from workflow-surface identity (all current surfaces → `l2`); client assertion advisory only (absent → accepted; matching → accepted; mismatch or invalid → 422, recorded in the error envelope); no client path can relabel historical records; attribution provenance returned additively on responses. Academic value exists in the vocabulary but NO academic workflow surface exists (test-enforced).

## Language discriminator semantics

Submission language, closed vocabulary `en`, server-derived; explicitly distinct from UI locale (frozen bilingual contract) and learner L1 (not modeled); expansion or drop requires the D-28 shared-contract process.

## Registry behavior

- `TaskTypeRegistry`: namespace-scoped mechanism (namespaces `l2`, `academic`); entries metadata-only (D-22, no comparability predicate); `legacy_unclassified` sentinel; content EMPTY (D-L2-01 blocked).
- `FeedbackDimensionRegistry`: entries carry `availability` + `learner_exposure` axes; content only where directly evidenced; otherwise empty (D-L2-03 blocked).
- `select_for_domain(entries, domain)` / `select_calf_for_domain` / `select_resource_requirement`: additive wrappers; existing registry lookup behavior unchanged; H1 semantics: untagged entries are l2-compatible, academic selection returns empty.
- Mechanism/content split per D-05/D-26: Shared Core = mechanism; domain departments = content (through the shared-contract process).

## Domain-pack mechanism

`app/configuration/domain_packs/{domain}/{version}/manifest.json` + `app/configuration/domain_packs_loader.py` (`load_pack`, `domain_exists`, `list_available_packs`; namespace/version/manifest validation). H1 ships `l2/v0.1.0` with EMPTY content lists and explicit NR/blocked status notes. No academic pack exists (explicit not-registered state). Rides alongside (not inside) the configuration-version machinery — no parallel configuration system (D-14).

## Composition-root changes

`app/api/main.py`: two parallel service-graph constructions (`_run_startup` production path and `_build_full_app` test path) consolidated into ONE parameterized builder `_build_services(settings, *, repository, submission_service)` + `_apply_service_state(api, services)`; both runtime paths and `create_app` use it; `api.state.*` reference names unchanged; facade private-attribute reads preserved (repository refactor out of scope, noted); Corpus Intelligence remains optional/additive (not wired; app boots without corpus modules); Academic can register a domain surface without a second composition root.

## Corpus Stage-5 compatibility result

COMPATIBLE — 7/7 boundary checks PASS (resource descriptor; version/provenance; I4 availability semantics; no raw-corpus leakage; no direct corpus dependency in unrelated flows; CALF `resource_requirement` alignment — empty lists are H2 content state, not a defect; tests 36/36). No shared-contract change breaks Stage 5; no escalation required.

## Known risks

- Per-row domain/language persistence does not exist until migration 14 (attribution is API-layer); any consumer needing query-by-domain must wait for migration 14 + A&I review. Do not ship an Academic surface before that.
- Export-time domain validation mechanism (`validate_domain_scope`) is provided; Research Evaluation wires it into exports (its charter WU2; D-36).
- LOW findings recorded from WU3 review: persisted audit record (deferred to migration 14), rule-version string duplication, workflow-surface map currently informational, GET-response field / empty-string test gaps, hygiene items — all non-blocking.
- `tests/live` suite (requires a running app) and `run.bat --verify` under Python 3.11 were not executable in this environment (no 3.11 interpreter); `scripts.verify_launcher` equivalent PASS. Re-run on the canonical 3.11 environment at integration.

## Files likely to conflict with other departments

- `app/api/schemas.py`, `app/api/routers/submissions.py`, `app/api/main.py` (shared-owned composition/serialization).
- `app/version.py`, `app/config/settings.py`, `app/lifecycle.py`, `app/services/submission.py`, `app/research/schemas.py` (version identity; Research exports manifest value changed to 0.9.7-d).
- `tests/test_v095h2d2_api_dependency_bindings.py`, `verification/v0.9.5-h2d2/*` (contract snapshots regenerated).
- `tests/shared/*`, `app/shared/*`, `app/domain/*`, `app/configuration/domain_packs*` (new shared-owned modules; additive, low conflict risk).
- `tests/contracts/api_surface_contract.py` (unchanged; regeneration tooling if extended).

## Recommended merge order

1. Shared Platform & Core H1 (this branch) — foundation for all departments.
2. Research Evaluation (export-time domain validation; open-decision register) — consumes `validate_domain_scope`.
3. L2 Writing Domain (registry/domain-pack CONTENT) — consumes namespaces; blocked items D-L2-01/D-L2-03 remain Researcher decisions.
4. Corpus & NLP (boundary contract implementation) — no change needed for Stage 5.
5. Academic Writing Domain — ONLY after migration 14 is designed/reviewed and the discriminator has a persisted column.
6. Frontend — additive fields only; no UI change in H1.

## Required integration tests (Architecture & Integration Gate)

- Cross-Department Contract Gate on the additive submission fields: clients sending legacy payloads; advisory match/mismatch/invalid; server-derived fields present.
- D-31 domain-isolation invariants as named contract tests (history, journey, revision candidates, practice provenance, exports domain-scope, learner-level endpoint filtering).
- Export domain-scope validation wiring (Research Evaluation WU2) against `validate_domain_scope`.
- Migration-14 review (design in 07_MIGRATION_DECISION.md) before any second-domain persistence.
- Golden-submission behavior diff re-run at integration (D-30) on the canonical Python 3.11 environment.
- Locale parity 600/600 and full non-live core re-run on the canonical environment.