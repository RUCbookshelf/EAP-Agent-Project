# 12 — Dependency Roadmap

Three horizons ordered by architectural dependency. No arbitrary dates. Every item names its prerequisite; nothing proceeds until its dependencies are DEPARTMENT GREEN and the relevant gates pass.

## Horizon 1 — Platform Foundation

Purpose: the minimal shared surface that lets Academic and L2 development safely diverge. Explicitly NOT assumed: shared profile contracts are NOT a prerequisite (WritingProfile formalization rides on existing snapshot machinery; D-02); corpus infrastructure is NOT a prerequisite (boundary contract only; D-07/D-08).

1. Composition-root consolidation (single parameterized builder; debt fix; E §5.4) — prerequisite for the domain dimension.
2. Version single-sourcing (`app/version.py` or equivalent; D-20) — prerequisite for domain-versioned manifests.
3. `domain`/`language` discriminator: vocabulary decision (D-01, D-17) → additive migration 14+ (planning only until a department Goal) → API additive field → schema CHECK.
4. Registry domain-selection policy (`select_for_domain` on analyzer/metric/CALF/configuration/prompt registries).
5. Shared vocabularies: evidence-status, epistemic-status (vocabulary now; persistence form `Researcher decision required`), TaskTypeRegistry + FeedbackDimensionRegistry schemas (contents later).
6. Corpus boundary contract (read-only, versioned, provenance-tracked; no implementation).
7. Frozen interface list + contract tests (domain-isolation tests; API surface additive-field tests; journey vocabulary freeze confirmation).
8. Debt hygiene gate: inventory/resolve the 12 `*-冲突-Rain_Win11.py` sync-conflict files before any measurement-version claim (Round 2 pair 2; recorded, not implemented here).

Parallel within Horizon 1: 1–2 sequential (composition root before version? both are shared-core debt fixes; can be one work unit); 3–4 sequential after 1; 5–7 can run in parallel once the discriminator vocabulary is decided.

## Horizon 2 — Independent Domain Intelligence

Prerequisites: Horizon 1 GREEN; task-type enumeration decided; feedback-dimension contents decided (feasibility spike for discourse-organization evidence); Research Evaluation policies (genre taxonomy, citation policy, corpus authorization) issued.

- **L2 Writing Domain:** typed task identity + L2 Domain Pack v1 + dimension envelope; comparability rule-version bump; locale additions; no new exercise kinds without Researcher decision.
- **Academic Writing Domain:** MVP entity design (7 entities), four provenance chains, local citation verification, integrity guardrails, section workflow on the shared loop; source-verification pre-gate design approved first (D-03); whole-paper view = persisted-structure facts only (D-12).
- **Corpus & NLP:** corpus boundary contract implementation; manifest/profile scaffolding; deterministic extraction pipeline design; contents `NR` until an authorized corpus exists (D1/D3/D4/D8).
- **Frontend:** L2 surface stays byte-identical; Academic surfaces (paper/sections/sources) only after domain data contracts; domain-workspace selector with Academic.
- **Feedback & Learner Intelligence:** feedback audit sampling; FeedbackPolicy instances (L2 default formalized; Academic instance with pre-gate).
- **Research Evaluation:** construct & measurement registry operation; validity-evidence storage decision (D7); domain-scoped exports; feedback audit operation.
- **Shared Platform & Core:** WritingProfile contract implementation (with Academic evidence sections); epistemic-status persistence decision.

Parallel matrix: L2 Domain Pack ∥ Academic module design ∥ corpus scaffolding (disjoint scopes; shared contracts frozen in H1). Academic UI waits on Academic data contracts. Corpus learner-facing output waits on display policy.

## Horizon 3 — Advanced Personalization

Prerequisites: validated measurement infrastructure (construct registry entries with `validated` status; comparability + data-sufficiency gating; feedback audit sampling operating; epistemic-status L3 gate enabled).

- Longitudinal personalization; recurring-pattern detection (beyond existing TraceStatus semantics); adaptive practice (difficulty/sequencing from inferred state); domain-specific recommendation; cross-task learner modeling.
- Every capability above is gated: no release without the validated-measurement gate; practice remains formative and provenance-tracked; observed-change semantics preserved.
- Permanently out of scope: proficiency/mastery/learning-gain reporting; outcome attribution; any norm-referenced interpretation without validation.

## What must explicitly wait

- Academic implementation → Horizon 1 + Academic policy decisions (D-03, D-12, citation policy).
- Corpus-grounded diagnosis → authorized corpus + band method + construct registry entries + display policy (D1/D4/D8/D12 + G gates).
- Learner-facing corpus content → D2/D3 display and licensing decisions (default: disabled).
- Adaptive/longitudinal personalization → validated measurement models (H3).
- Any migration 14+ → a future implementation Goal with Architecture & Integration review (this Goal created none).
- New Journey event types → ADR + Horizon 2 Academic decision (D-11).

## Horizon amendments (Round 4 red team)

- Horizon 1 additionally includes: registry-content layout freeze (per-domain `domain_packs`, D-26); canonical module-set manifest + quarantine/exclusion policy + `-冲突-`/`-Copy`/`-副本` drift check (D-27); API-surface contract regeneration with additive-only diff as a named step (D-37/RT-19, folded into the D-30 gate); the zero-change regression gate itself (full core green, contract additive-only diff, locale 600/600, golden-submission behavior diff, migration stays 13; D-30); domain-isolation invariant list frozen (D-31); `language` semantics decision or drop (D-28).
- Horizon 2 items are annotated with their required Researcher decisions and blocked-until markers (D-37/RT-18): L2 Domain Pack — blocked until task-type enumeration (D-L2-01) and dimension-envelope membership (D-L2-03); Academic module — blocked until citation policy (G D5), whole-paper surface decision (D-12), source-verification pre-gate approval (D-03); corpus manifests/profiles — blocked until corpus authorization (D1), licensing (D3), band method/min-N (D4), feature-set scope (D8); feedback audit sampling — blocked until audit design (G D6); academic UI — blocked until domain data contracts (B/E).
- Test policy (D-35): the core suite stays single-domain (L2); only domain-seam contracts are parametrized, and only once Domain A content exists.