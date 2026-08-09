# L2-DOMAIN-PACK-V1 — Execution Report

**Goal:** `L2-DOMAIN-PACK-V1` — L2 Domain Pack v1 implementation (without
`discourse_organization`)
**Owner:** L2 Writing Domain
**Date:** 2026-08-09
**Baseline / Branch / Worktree:** `09264abbd93cdc6b62b83cefd94b3b640319ac9b` /
`dept/l2-writing` / `A:\EAP Agent Project\worktrees\l2-writing`
**Status:** DEPARTMENT COMPLETE with targeted integration-lane repairs
(AMBER; not integration GREEN; not promoted)

---

## 1. Preflight

- Worktree root, branch (`dept/l2-writing`), and HEAD (`09264ab`) verified
  against the Goal Packet and `WORKSTREAM_REGISTRY.json`; all match.
- Pre-existing untracked files preserved untouched (`docs/domain/*` prior
  content, `docs/integration/*.md` prior reports, `handoff*.json`).
- Program-control artifacts read: `WORKSTREAM_REGISTRY.json`,
  `PROGRAM_STATUS.md`, `DEPENDENCY_GRAPH.md`, `PROMOTION_HISTORY.md`,
  `WORKTREE_REGISTRY.md`; Context Bundle `L2-DOMAIN-PACK-V1__complex__...`
  (identity capsule, current state, goal packet, dependency digests,
  verification contracts).
- Governing records read: `DOMAIN-PACK-V1-conditional-auth.json`,
  `RD-D22-approved.json`, `L2-VALIDITY-scoped-disposition.json`; taxonomy
  contract v1.0.0; V1 disposition + adjudication (A-1..A-8); qualified D-22
  manifest; DP-4 census; D-L2-02 / D-L2-09 / D-L2-10; D-26/D-30 architecture
  decisions; `app/shared/task_type_registry.py`;
  `app/services/learner_model.py:332-345` (removed inference site).

## 2. Implementation (all writes inside the authorized worktree)

### 2.1 Domain Pack v1 content (`app/configuration/domain_packs/l2/v1.0.0/`)

| File | Content |
| --- | --- |
| `manifest.json` | Pack `l2-core-v1.0.0`; five `supported_task_types`; availability `available`; metadata-only note; D-L2-03 dimension NR; discourse_organization EXCLUDED |
| `task_types.json` | Five-type definitions; en labels (contract §1) + zh_CN labels (D-L2-09); canonical display order `opinion → argumentative → discussion → problem_solution → general_eap` |
| `trigger_dictionaries.json` | G5 trigger dictionaries: per-type groups, en + zh_CN phrase lists, composition (full-match) rules, normalization/matching semantics |
| `conflict_pairs.json` | G5 conflict-pair table: v1 enumerates exactly `(argumentative, discussion)` (canonical A-3 pair); chain documented |
| `legacy_genre_mapping.json` | Qualified D-22 manifest v1.0.0 embedded with provenance (approvals RD-D22/DP-4, rules M0-M4, census summary, non-claims) |

### 2.2 Deterministic services (new)

- `app/services/task_type_classifier.py` — closed rule-based classifier:
  NFC/casefold/whitespace-collapse normalization; word-boundary (en) and
  substring (zh_CN) phrase matching; full-match predicates per the G5
  composition rules; precedence chain; conflict-pair rule; general_eap §7
  conditions; declared-task-metadata validation; provenance (taxonomy +
  dictionary versions, matched triggers, reason codes).
- `app/services/legacy_genre_mapping.py` — explicit-only D-22 manifest
  application: exact normalized-value matching (no substring/similarity/
  definition inference); M1/M1-zh → `argumentative`; M2/M2-zh/M3/M3-zh/M4/M0
  → `legacy_unclassified` with reason codes; write-time provenance record
  (manifest id, rule id, rule version, approvals).

### 2.3 Mechanism/content integration (modified)

- `app/shared/task_type_registry.py` — registers the five types plus the
  `legacy_unclassified` sentinel under the `l2` namespace (taxonomy contract
  §8.7); sentinel metadata now references the qualified manifest.
- `app/services/learner_model.py` — the legacy substring inference
  (`purpose = "argument" if "argument" in genre ...`, former lines 333-344)
  is REMOVED; the cluster key derives purpose from the deterministic lane
  (persisted `task_type` if present, else D-22 manifest mapping); cluster
  rule version bumped to `task-cluster-v0.8.0` (new rule version, 06 §4).
- `app/core/longitudinal_models.py`, `app/api/schemas.py` — mirrored
  `task-cluster-v0.8.0` defaults (D-29 independent version streams).
- `locales/en.json`, `locales/zh_CN.json` — five `task_type_*` keys each
  (D-L2-09 labels); parity 600/600 → 605/605.

### 2.4 Migration design note (STOP rule respected)

`docs/domain/D-L2-02_MIGRATION_14_DESIGN_NOTE.md` — additive column design
(`task_type`, `task_type_taxonomy_version`, `task_type_provenance_json`),
write-time provenance contract, gates, rollback. NO migration implemented.

## 3. Verification — direct evidence

### 3.1 Targeted suites (all green)

`pytest tests/test_task_type_classifier_v1.py tests/test_legacy_genre_mapping_v1.py
tests/test_learner_model_task_type_v1.py tests/shared/test_domain_pack_v1_content.py
tests/shared/test_registry_domain_policy.py tests/shared/test_domain_packs.py
tests/test_v097d_design_system.py tests/test_learner_model_v07.py
tests/test_design_tokens_v094a.py` → **239 passed**.

Coverage:
- classification determinism + normalization invariance (repeated calls
  identical; whitespace/case/punctuation variants identical);
- opinion-vs-argumentative distinction (contract §3 examples; stance +
  evidence wins over the word "opinion"; viewpoint-only stays opinion);
- precedence chain (A-1 `discussion`+`opinion` → discussion; A-4
  `problem_solution` > `argumentative`; §4 full chain);
- conflict rule (canonical `argumentative`+`discussion` → unclassified /
  `ambiguous_precedence_conflict`; never coerced);
- problem_solution scope (A-7: effects-only never matches; causes+effects
  matches on cause content);
- general_eap fallback (§7 a/b; `not_eap` and `no_prompt` reason codes;
  no coercion);
- legacy mapping (M0-M4 incl. zh_CN; no-inference cases: substring and
  near-miss values → `legacy_unclassified`; provenance fields; census
  distribution reproduced: 26×M1 + 3×M1-zh = 29 `argumentative`);
- locale parity (605/605; task_type keys resolve; pack labels == locale
  values); registry content parity; pack content schema checks
  (disjointness, zh phrase length, conflict-pair validity);
- learner-model cluster key: `writing_purpose` from the deterministic lane;
  persisted `task_type` wins; genre variants still separate clusters
  (frozen `test_case_f` behavior); rule version v0.8.0.

### 3.2 D-22 behavior-diff gate (over the DP-4 census snapshot)

`test_learner_model_task_type_v1.py::TestBehaviorDiffGate`:
- old (frozen v0.7 substring) vs new (D-22 mapping) cluster keys over a
  232-row grid spanning the census genre distribution × timed × tool × mode:
  **same-cluster (comparability) relation IDENTICAL before/after**;
- documented label transitions: `argumentative essay` `argument →
  argumentative`; `议论文` `exposition → argumentative`; `expository essay`
  `exposition → legacy_unclassified`; `narrative essay`
  `narration → legacy_unclassified`;
- census aggregation reproduced: 29/29 rows typed `argumentative`.

### 3.3 Full-suite regression (D-30 evidence)

`pytest -q` → **2009 passed, 14 failed, 8 skipped, 3 errors** (16:11).

Failures attributable to this Goal (integration-lane, precisely scoped):

1. `tests/test_shared_core_drift.py::test_current_module_set_matches_manifest`
   — two new L2 modules under `app/` are unrecorded in the frozen shared
   module-set manifest. Established pattern: INT registers merged department
   modules (`chore(integration)` commits for academic/governance). Required
   manifest additions: `services/task_type_classifier.py`,
   `services/legacy_genre_mapping.py`.
2. `tests/test_v095h2d2_api_dependency_bindings.py::test_openapi_and_dependency_graph_unchanged`
   — frozen OpenAPI snapshot predates the two version-provenance defaults.
   Verified diff is EXACTLY `TaskCluster.rule_version` and
   `VersionResponse.task_cluster_version` (`task-cluster-v0.7.0` →
   `task-cluster-v0.8.0`), additive-only; snapshot regeneration follows the
   shared-core pattern (`test(shared-core): regenerate API contract
   snapshots`).

Failures NOT caused by this Goal (environmental / pre-existing at baseline;
none of the involved files/systems were touched):

3. `scripts/corpus_readiness/...::test_derived_roundtrip_sample` — requires
   `CORPUS_ROOT` env var (SWECCL corpus root); unset in this environment.
4-9. `tests/live/test_v09_playwright.py` (6) and
   `tests/live/test_v0921_playwright.py` (3 errors) — Playwright browser
   binaries not installed.
10-11. `tests/test_research_governance_v01.py` (2) — policy-artifact hash
   pins (docs/departments/research-evaluation-governance/*) vs the frozen
   validator tables at this baseline.
12. `tests/test_v095e_repository_modularization.py` — git `dubious
   ownership` failure inside the parity subprocess (git config environment).
13-14. `verification/v0.9.6-dp0/...` (2) — `provider_call_budget.json`
   missing `direct_diagnostic_calls` key; `app/migrations` path assumption.

## 4. Gate status

- Five-type registry pack: DONE (metadata-only; no comparability predicate).
- G5 trigger dictionaries + conflict-pair table: DONE (content record
  `docs/domain/L2_DOMAIN_PACK_V1_CONTENT.md`).
- D-L2-09 zh_CN labels + canonical display order: DONE (locales + pack +
  registry; parity tests updated 600/600 → 605/605 per D-L2-09 §4.1).
- Deterministic classification per qualified criteria + V1 adjudication
  outcomes: DONE (A-1..A-8 implemented and tested).
- Legacy mapping via qualified D-22 manifest, explicit-only: DONE
  (no-inference tests; provenance preserved).
- `discourse_organization` EXCLUDED: DONE (not in pack/registry/locales;
  declared-type rejection tested).
- No schema migration: DONE (design note produced; no migration code).
- Behavior-diff gate: DONE for the DP-4 census snapshot (zero change in
  comparability classifications); D-30 full-suite evidence recorded.
- Cross-Department Contract Gate: REQUIRED for registry/domain-pack content
  (this handoff) + the two shared-artifact registrations.

## 5. Artifacts

- Pack content: `app/configuration/domain_packs/l2/v1.0.0/*` (5 files).
- Services: `app/services/task_type_classifier.py`,
  `app/services/legacy_genre_mapping.py`.
- Content record: `docs/domain/L2_DOMAIN_PACK_V1_CONTENT.md`.
- Migration design note: `docs/domain/D-L2-02_MIGRATION_14_DESIGN_NOTE.md`.
- Tests: `tests/test_task_type_classifier_v1.py`,
  `tests/test_legacy_genre_mapping_v1.py`,
  `tests/test_learner_model_task_type_v1.py`,
  `tests/shared/test_domain_pack_v1_content.py`.

*Produced by the L2 execution agent under Goal L2-DOMAIN-PACK-V1, 2026-08-09.
Department closure record; integration and promotion remain separate
authorized actions.*
