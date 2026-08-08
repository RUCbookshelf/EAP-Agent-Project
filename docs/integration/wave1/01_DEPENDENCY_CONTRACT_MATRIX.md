# 01 — Wave-1 Dependency & Contract Matrix

**Gate:** WU1 GREEN — 2026-08-08
**Office:** Architecture & Integration (Wave-1 Integration Gate)
**Method:** constructed from the frozen architecture register (D-01..D-37), the three department handoffs (`09_INTEGRATION_HANDOFF.md` / `12_INTEGRATION_HANDOFF.md` / `10_INTEGRATION_HANDOFF.md`), and the pre-merge branch audit (`02_PREMERGE_BRANCH_AUDIT.md`). No merge was performed before this matrix existed.

## 1. Classification vocabulary

| Disposition | Meaning |
| --- | --- |
| SATISFIED | Contract exists on the integrated baseline with unambiguous owner; no action required beyond verification. |
| SATISFIED_WITH_ADAPTER | Contract exists but needs a documented minimum convergence seam (adapter or contract test) in WU6/WU7. |
| SAFE_TO_DEFER | Explicitly deferred capability; no production surface depends on it; deferral recorded with trigger. |
| REQUIRES_OWNER_FOLLOWUP | Known requirement with an assigned owner outside the current gate (owner listed); does not block Wave-1 GREEN if not production-exposed. |
| BLOCKING | Would prevent INTEGRATION GREEN. (None in this matrix.) |

## 2. Cross-department seam matrix

| # | Seam | Shared Core contract | Research Governance requirement | Academic dependency | Corpus Stage-5 boundary | Frozen decision | Disposition | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Domain discriminator | Closed vocabulary `l2` (functional/default) / `academic` (reserved, non-functional); `Domain` enum; unknown values rejected | Domain-scoped export semantics depend on it (D-19) | Requires `l2`/`academic` values + resolver for future surface (handoff 10) | Domain-agnostic; no corpus dependency | D-01, D-17, D-21, D-22 | SATISFIED (mechanism integrated; academic content intentionally empty) | Shared Platform & Core |
| 2 | Language discriminator | Closed vocabulary `en`; server-derived; distinct from locale/L1 | n/a | n/a (Academic English assumption, no language field dependency in foundation) | n/a | D-28 (drop option if no consumer) | SATISFIED; D-28 drop decision deferred via shared-contract process | Shared Platform & Core |
| 3 | Server-derived attribution | `domain-attribution-v0.1.0`; workflow-surface derivation (all current surfaces to l2); advisory-only client fields; mismatch/invalid to 422; no client relabel | n/a | Requires resolver for future Academic surface; none consumed in foundation | n/a | D-21, D-23, D-36 | SATISFIED | Shared Platform & Core |
| 4 | Domain persistence | NOT implemented (no migration 14; app-layer + export-time validation only) | Export-time validation until migration-14 CHECK (D-36) | Persistence explicitly NOT required in foundation (in-memory only; handoff 7/13) | Unaffected (no schema change) | D-17, D-36; migration decision deferred to WU10 | SAFE_TO_DEFER (trigger: any persisted Academic row / cross-domain persisted query / second-domain persistence) | Shared Platform & Core + A&I (WU10) |
| 5 | Domain-scoped exports | `validate_domain_scope` utility provided (handoff known-risks); export paths not yet wired | Listed as required shared-core support (handoff 5): export paths reject/quarantine unknown values | No Academic export surface exists | Exports unchanged (l2-only data) | D-19, D-36 | REQUIRES_OWNER_FOLLOWUP — wiring decision in WU8; current data is l2-only so wiring is behavior-neutral | Research Evaluation (wiring) + Shared Core (utility); A&I verifies at WU8 |
| 6 | Epistemic-status vocabulary | `EpistemicStatus` (`observed_descriptive/gated_inference/recommendation/outcome_claim`) in `app/shared/vocabularies.py`; downgrade-only semantics | MeasurementClaimPolicy: permitted/prohibited statements; downgrade-only display (RD ratified) | Domain-local mirror in `app/academic/vocabulary.py` marked INTEGRATION_POINT | Stage-5 artifacts use own provenance; no overlap | D-09, D-05, D-37 | SATISFIED_WITH_ADAPTER — WU6 convergence (direct import or contract test proving exact mirror); no semantic collapse | Shared Platform & Core (owner); A&I (WU6 seam) |
| 7 | Evidence-status vocabulary | `EvidenceStatus` (`verified/candidate/insufficient/suppressed/not_applicable/unavailable/legacy/unresolved`) in `app/shared/vocabularies.py` | Policies reference statuses; no mutation | Academic mirror (INTEGRATION_POINT) + `academic_verification_to_shared` mapping | n/a | D-05 | SATISFIED_WITH_ADAPTER — WU6 contract test: Academic verification status != shared evidence status != epistemic status | Shared Platform & Core; A&I (WU6) |
| 8 | Availability / resource status | `AvailabilityStatus`, `LearnerExposure` (`student|research_only`), `ResourceStatus` (corpus I4); `FeedbackDimensionRegistry` dual axes | EvaluationLeakagePolicy + ReferenceGroupEligibility use availability semantics | Not consumed in foundation | Stage-5 I4 semantics verified 7/7 compatible (handoff) | D-37/RT-17, D-24, D-25 | SATISFIED | Shared Platform & Core; Corpus & NLP (content) |
| 9 | Domain-pack registration | `app/configuration/domain_packs/{domain}/{version}/manifest.json` + loader; `l2/v0.1.0` present (empty content, NR/blocked notes); academic pack explicitly absent to not-registered state | n/a | Requires layout for future academic pack (D-26); none created | n/a | D-14, D-26 | SATISFIED | Shared Platform & Core (mechanism); L2/Academic (future content) |
| 10 | Composition root | Single `_build_services(settings, *, repository, submission_service)` builder; both runtime paths + `create_app`; corpus optional/additive; Academic registerable later | n/a | Academic module registration: none until composition-root consolidation (handoff 10) | Corpus not wired; boots without corpus modules | D-05 boundary | SATISFIED | Shared Platform & Core |
| 11 | Version provenance | `app/version.py` single source (`PLATFORM_APPLICATION_VERSION=0.9.7-d`, `API=v1`, `DATABASE_MIGRATION_VERSION=13`); all app-identity consumers import it; evidence streams independent | ExportManifest consumes identity (value changed to 0.9.7-d) | n/a | n/a | D-20, D-29 | SATISFIED (contract test asserts API version = single source) | Shared Platform & Core |
| 12 | Academic verification-state mapping | Shared owns registry-level evidence-status alignment (handoff 15) | Citation policy decision default: never by default | Domain-local distinct verification states (`verified/unverified/verification_unavailable` + D-32 records) | n/a | D-32, D-06 (evidence kinds never merged) | SATISFIED_WITH_ADAPTER — WU6 documents mapping; no collapse of axes | Academic (semantics); Shared Core (alignment); A&I (WU6) |
| 13 | Research measurement-claim guardrails | Banned shared status values (`mastery/proficiency/ability_level/learning_gain`) drift-test enforced | MeasurementClaimPolicy v0.1.0 + deterministic validators (28 tests); ratified | ACAD integrity guardrails (ACAD-RULE-01..07) independently; no claims | n/a | D-09, D-07 | SATISFIED (policy foundation available; runtime learner-facing wiring NOT required in Wave-1 per Goal 13) | Research Evaluation; WU8 documents disposition |
| 14 | Stage-6 admissibility contract | n/a | `stage6-evidence-admissibility-policy-v0.1.0` (ADMISSIBLE/LIMITED/UNAVAILABLE/INVALID) ratified + versioned | n/a | Stage 6 NOT started; contract available for next Corpus Goal | D-24 (deferral), RD ratification | SATISFIED (contract available; no implementation) | Research Evaluation; Corpus & NLP (future consumer) |
| 15 | Corpus learner exposure | `LearnerExposure.research_only` shared axis | EvaluationProtectionPolicy: no development use of 270 block; learner exposure disabled by default | n/a | `research_only` learner exposure + explicit unavailable states; no raw corpus leakage (Stage-5 verified) | D-08 (disabled by default; Researcher decision before any learner-facing excerpt) | SATISFIED | Corpus & NLP; Shared Core (axis) |
| 16 | Migration 14 | Design exists (`07_MIGRATION_DECISION.md`: additive `essays.domain TEXT NOT NULL DEFAULT 'l2' CHECK(...)` + `essays.language TEXT NOT NULL DEFAULT 'en'`; no backfill; one-step rollback); NOT implemented | Export-time validation anticipates it (D-36) | Required for future Academic persistence (handoff 10); no persistence in foundation | No schema change in Stage 5 | D-17, D-36; charter: migration 13 authority until A&I review | SAFE_TO_DEFER — formal disposition in WU10 (`06_MIGRATION_14_DECISION.md`) | Shared Platform & Core (default owner); A&I (coordination/decision) |
| 17 | Academic persistence | Repository protocols provided (shared infra pattern); Academic uses in-memory adapters only | n/a | NO SQLite, NO migration (handoff 7, invariants) | n/a | D-02/D-03 discipline; Academic persistence = next-wave owner Goal | SAFE_TO_DEFER — no production Academic surface depends on absent persistence | Academic Writing (next wave, gated) |
| 18 | Academic API registration | Composition root allows later registration; no registration in H1 | n/a | NO API routing in foundation | n/a | D-21 (server-derived attribution precedes surface) | SAFE_TO_DEFER — no Academic production route; WU11 status decision | Academic Writing (next wave) |
| 19 | Domain isolation | Ancestry resolver (`app/domain/resolver.py`) + discriminator tests; `validate_domain_scope` | D-31 invariants named; exports domain-scope default | Academic entities cannot contaminate L2 history; no L2 evidence reuse | L2-only data; no cross-domain query exists | D-31 (5 frozen invariants), D-23 (one resolver service) | SATISFIED_WITH_ADAPTER — WU7 adds architecture-owned cross-contract tests per consumer boundary | Shared Platform & Core (mechanism); A&I (WU7 contract tests) |
| 20 | Task-type registry (extra seam) | `TaskTypeRegistry` namespace-scoped mechanism; metadata-only (D-22); `legacy_unclassified` sentinel; content empty (D-L2-01/D-L2-03 blocked) | n/a | Academic paper/section kinds = separate namespace, future content | n/a | D-04, D-22, D-35 | SATISFIED | Shared Platform & Core (mechanism); domain departments (content) |
| 21 | Advisory fields contract (extra seam) | `advisory_domain`/`advisory_language` optional on POST; mismatch/invalid to 422 canonical envelope; additive response fields | n/a | n/a | Legacy payloads accepted unchanged | D-17 (additive body fields), D-21 | SATISFIED (legacy-payload + mismatch contract tests in WU12) | Shared Platform & Core |

## 3. Dependency-direction summary (Goal section 6)

- Shared Platform & Core is the sole provider of domain/language attribution, shared vocabularies, registries, domain packs, version identity, composition root, and drift control.
- Research Governance consumes shared mechanisms at export/admissibility seams (future) and owns policy artifacts now.
- Academic depends on shared contracts for its future surface only; the foundation consumes none of them today (in-memory, isolated, unregistered).
- Corpus Stage 5 is a boundary contract only; all three departments verified non-interference (shared-core 7/7, 36/36; research: zero Stage-5 modification; academic: zero corpus overlap).

## 4. Disposition summary

| Disposition | Count | Seams |
| --- | --- | --- |
| SATISFIED | 12 | 1, 2, 3, 8, 9, 10, 11, 13, 14, 15, 20, 21 |
| SATISFIED_WITH_ADAPTER | 4 | 6, 7, 12, 19 (WU6/WU7 convergence work) |
| SAFE_TO_DEFER | 4 | 4, 16, 17, 18 (WU10/WU11 formal dispositions) |
| REQUIRES_OWNER_FOLLOWUP | 1 | 5 (export wiring — Research Evaluation; decision in WU8) |
| BLOCKING | 0 | — |

## 5. Gate statement

**WU1 GREEN.** Every known cross-department dependency has an identified owner and an explicit disposition. No seam is BLOCKING. Four seams require the integration office's own convergence work (WU6 vocabulary adapters, WU7 domain-isolation contract tests); four capabilities are explicitly deferred with triggers (WU10/WU11 formal decisions); one follow-up is owned by Research Evaluation and will be classified at WU8. Merges may proceed in the charter order: Shared Core, Research Governance, Academic.
