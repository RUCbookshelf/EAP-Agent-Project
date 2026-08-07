# 14 — Architecture Decisions (Canonical Register)

**Status:** FROZEN (2026-08-07). **Scope:** decisions D-01..D-37.
**Canonical and self-contained:** this document is the authoritative decision register for the Writing Intelligence Platform architecture. It does not depend on planning-session files. Session provenance (noncanonical): the working deliberation register lived under `.agent-workflow/writing-intelligence-platform-architecture/` during the planning Goal and is not required to read or govern this baseline.

## 1. Goal and process decisions

| Date | Decision | Rationale | Alternatives Rejected | Decided By |
| --- | --- | --- | --- | --- |
| 2026-08-07 | Planning-only Goal; no production implementation, no migrations, no UI redesign, no repo split | Goal sections 1, 42; verified repo state v0.9.7-D closed | (none) | Global Architecture Chair |
| 2026-08-07 | Council Round 1 dispatched as 7 parallel independent agents with PLANNING_DISABLED=1, each writing only its own handoff | Goal sections 6, 16; skill model-routing/cost-control; independence prevents anchoring | Serial council chat | Global Architecture Chair |
## 2. Round 3 disagreement register — full records (D-01..D-20)

### D-01 Default domain attribution of existing records
- Issue: Which domain do the current verified system and all legacy rows belong to?
- Option A: Domain B (L2) - the product's character is L2-formative (bilingual en/zh_CN UI, L2 category map, three L2 exercise types) (A, Round 2 pair 3).
- Option B: `academic` - treat existing rows as Academic/English defaults (E section 2.2).
- Evidence: `app/practice/mapping.py` category map; `app/practice/schemas.py` exercise types; locale 600/600 en/zh_CN; Goal section 2 ("The current product is closer to this domain"); E open decision E section 9.1.
- Trade-off: Option A keeps product identity truthful but means the L2 pack is the default domain; Option B avoids renaming but mislabels the verified product.
- Decision: **Domain B (L2) is the current verified system and the default domain; legacy rows belong to L2.**
- Reason: Direct evidence of L2-formative character outweighs the convenience of an `academic` default; a truthful default prevents domain misattribution in history/journey/exports from day one.

### D-02 WritingProfile: formalize now vs defer
- Issue: Should the shared learner-profile abstraction be named and bounded now?
- Option A: ADOPT as formalized evolution of the existing snapshot contract (domain-tagged, observation-only, never-merged; no new table) (A section 5.1).
- Option B: Defer until a second domain's evidence sections are specified; reject merged profiles (E sections 5/6.3).
- Evidence: Existing snapshot v2 + `history_evidence_registry` + LearnerModelEngine (migration 8); two real requirements: L2 longitudinal evidence (verified) and Domain A source/citation-integrity evidence (mandate); E's rejected object is the *merged* profile, not A's constrained one.
- Trade-off: Naming now costs little and gives Domain A a seam; deferring avoids premature formality.
- Decision: **ADOPT the constrained WritingProfile contract (documentation-level now; no schema change; implementation with Domain A work).**
- Reason: The abstraction is an extension of an existing verified contract, not new machinery; bounding it now prevents Domain A from designing evidence sections without a seam. Merged/proficiency profiles remain prohibited.

### D-03 FeedbackPolicy: named type vs configuration sections
- Issue: Should feedback rules be a first-class named policy object?
- Option A: First-class versioned FeedbackPolicy with minimal interface (A section 5.2).
- Option B: Domain rules stay sections of the single configuration payload (E section 9.4).
- Evidence: Gate/priority semantics exist implicitly in `app/calibration/service.py` + ConfigurationPayload; both preserve single-active/rollback/audit machinery; Domain A needs a citation/source-verification pre-gate.
- Trade-off: Named type gives a stable contract; configuration sections avoid a new object.
- Decision: **ADOPT the FeedbackPolicy contract (documented minimum interface, hosted on configuration/audit machinery); the named-type implementation form is decided when the second policy instance (Domain A) is designed.**
- Reason: Two real policy instances will exist; the contract must be frozen before Domain A design, while the implementation form should follow the configuration-model decision.

### D-04 Task identity: shared registry vs question-anchored identity
- Issue: Is typed task identity a shared abstraction, and does it apply to Academic?
- Option A: Shared TaskTypeRegistry + additive `task_type` reused by both domains (C section 3, D-L2-07).
- Option B: Academic identity is ResearchProject + ResearchQuestion anchored; no task-type concept (B sections 2/5).
- Evidence: L2 comparability currently uses free-text genre equality + substring inference (`app/learner/history.py`, `app/services/learner_model.py:333-344`); Academic work is one deepening question-driven project; Round 2 pair 1 disagreement 1.
- Trade-off: One enum would conflate cross-task typing (L2) with within-paper structure (Academic) and damage both pedagogies.
- Decision: **ADOPT a namespace-scoped TaskTypeRegistry as shared mechanism; L2 registers non-research task types; Academic registers paper/section kinds in a separate namespace; never one merged enum.**
- Reason: The registry solves L2's comparability defect; namespaces preserve each domain's distinct learning function; `task_type` and paper/section context remain semantically distinct additive fields.

### D-05 Where the shared core ends
- Issue: Which new abstractions enter Shared Core?
- Option A: TaskTypeRegistry + FeedbackDimensionRegistry + corpus/resource descriptor in core; everything else content (C section 3).
- Option B: No core additions; Academic entities stay domain-specific; loop semantics shared (B sections 3/5).
- Evidence: Round 2 pair 1 agreements 4/6; both treat domain knowledge as versioned content; the disagreement is boundary placement, not mechanism.
- Trade-off: More in core -> shared honesty patterns; less in core -> fewer shared contracts to govern.
- Decision: **Shared mechanisms in core (task-type registry, feedback-dimension envelope, corpus/resource descriptor, epistemic/evidence-status vocabularies); all contents domain-owned.**
- Reason: The mechanisms serve both domains (two real requirements each); contents are domain instances and must not be governed centrally.

### D-06 Feedback-dimension granularity and evidence-kind separation
- Issue: Can one dimension registry serve L2 availability states and Academic provenance-bound feedback?
- Option A: L2 local-feature availability states only (C).
- Option B: Academic feedback binds to provenance artifacts (EvidenceUnit/CitationLink IDs) (B section 2.5).
- Evidence: Round 2 pair 1 "only appears similar" (evidence/argument/discourse); "two separate evidence kinds, never merged" (B); L2 excludes source integration (C section 6).
- Trade-off: One schema would silently merge draft-internal evidence with research evidence.
- Decision: **One registry, two binding kinds kept separate; internal diagnostic evidence and research evidence never share a schema; Academic evidence referenced by ID only.**
- Reason: Same-word traps (`evidence`, `claim`, `discourse`) have different referents and integrity obligations; separation is a research-validity requirement.

### D-07 Reference bands: pre-validation descriptive vs gated norm-referenced output
- Issue: What artifact class is a reference band/percentile before construct validation?
- Option A: Observed, descriptive, task-conditioned reference evidence with provenance (D sections 3/10 P9).
- Option B: Norm-referenced output gated behind validated-measurement status (G sections 2.4/5).
- Evidence: Round 2 pair 2 disagreement 1; both prohibit the terminal normative claim; D invariants I1/I6; G construct registry gate.
- Trade-off: D enables corpus grounding sooner; G avoids any pre-validation normative surface.
- Decision: **Bands/percentiles are observed, descriptive reference evidence (Option A artifact class), released only with full provenance, min-N/coverage eligibility, feature-version match, and the I1 naming contract; any normative interpretation remains blocked by the validated-measurement gate.**
- Reason: The artifact itself carries no ability claim; the interpretive claim is what requires validation. G structural guarantees are adopted separately (D-09).

### D-08 Learner-facing corpus citations: default posture
- Issue: May corpus excerpts appear in learner feedback once verification exists?
- Option A: Opt-in after validator-checked slots exist (D sections 5 A6-A7).
- Option B: Disabled by default; separate Researcher decision before any grounding verifier ships (G D5).
- Evidence: Round 2 pair 2 disagreement 2; licensing/privacy risk; no authorized corpus exists.
- Trade-off: Earlier learner value vs validity/privacy safety.
- Decision: **Disabled by default; Research surfaces first; any learner-facing corpus excerpt requires a Researcher decision, display policy, and licensing/anonymization gate.**
- Reason: No authorized corpus exists; the safe default is no learner exposure, with an explicit documented path to opt-in.

### D-09 Structural epistemic-status enforcement (G guarantees vs D omission)
- Issue: Must the observed/inference/recommendation/outcome separation be typed and persisted?
- Option A: Persisted epistemic-status enum with downgrade-only invariant on artifacts and API schemas (G sections 2.1-2.2, D1).
- Option B: Naming contracts + gates + slot schemas suffice (D section 2.3).
- Evidence: Round 2 pair 2 disagreement 3; current separation enforced by convention only (G section 1); feedback audit sampling absent from D (disagreement 4).
- Trade-off: Persisted enum adds migration surface; convention-only risks silent layer collapse.
- Decision: **ADOPT the four-layer epistemic taxonomy as a shared vocabulary and target design: additive typed status on persisted artifacts and API schemas; downgrade-only display invariant; feedback audit sampling adopted as a shared evaluation-of-evaluation design. Persistence migration deferred and gated (`Researcher decision required` on exact form); compute-at-boundary is the interim option.**
- Reason: The taxonomy is the structural tripwire preventing corpus-grounded diagnosis from being displayed as outcome; audit sampling closes the circular-evaluation gap. Both complement D invariants, not replace them.

### D-10 Domain as first-class UI concept
- Issue: Should domain selection be an explicit workspace-level UI concept?
- Option A: Workspace selector above the page list when Academic ships (F section 2).
- Option B: Domain stays inside content/typed metadata; no UI delta (C D-L2-10).
- Evidence: Round 2 pair 4 disagreement 5; L2 MVP needs no selector; entry model has no account concept.
- Trade-off: Explicit selector clarifies mental model; delayed selector keeps L2 byte-identical.
- Decision: **Hybrid: L2 remains the default path byte-identical; a domain-workspace selector appears only when the Academic workspace ships; selection is session-scoped like the learner ID (persistence `NR`).**
- Reason: UI change must be driven by a real second domain surface; until then domain is metadata.

### D-11 Academic Journey extension timing
- Issue: May Academic add paper-milestone/source-use journey events in MVP?
- Option A: Configured journey event set/stage order per domain now (F sections 2/4).
- Option B: No new raw event types in MVP; paper aggregation deferred (B sections 4/9, C section 6).
- Evidence: Round 2 pair 4 disagreement 1; journey is a read-time projection with frozen event vocabulary.
- Trade-off: Richer Academic journey vs frozen event vocabulary and L2 stability.
- Decision: **MVP keeps existing event types unchanged for both domains; paper-anchored aggregation and domain-configured journey stages are Horizon 2 Academic decisions requiring B/G definitions.**
- Reason: Journey event vocabulary is a frozen shared contract; extension must be additive and evidence-driven.

### D-12 Whole-paper feedback surface in MVP
- Issue: Does Academic MVP include a whole-paper feedback view?
- Option A: Explicit whole-paper feedback view over section feedback + paper-scope evidence (F section 4).
- Option B: MVP paper view = persisted-structure facts only; feedback granularity `NR` (B sections 2.2/9).
- Evidence: Round 2 pair 4 disagreement 2; research-validity risk of implied quality claims.
- Trade-off: Richer surface vs validity risk and undefined evidence semantics.
- Decision: **MVP = persisted-structure facts only (Option B); any whole-paper feedback view is deferred until Council G sign-off and an evidence-bound design.**
- Reason: Whole-paper quality aggregation is methodologically fragile; prototype observations cannot support it.

### D-13 Academic practice targets
- Issue: Do Academic practice targets derive from section priorities through the same loop?
- Option A: Reuse as default assumption (F D-6).
- Option B: Deferred decision; no new Academic target kinds in MVP (B section 9; C D-L2-05).
- Evidence: Round 2 pair 4 disagreement 3; no user-research evidence for Academic exercise kinds.
- Trade-off: Reuse is cheap; forcing reuse could distort Academic pedagogy.
- Decision: **Same loop and `PRIO-{...}` provenance apply; Academic exercise/target kinds are a deferred `Researcher decision required`; no new kinds in MVP.**
- Reason: Practice mechanics are shared; content is domain-owned and requires deterministic evaluators or explicit provenance.

### D-14 Abstraction ownership: DomainDescriptor vs Domain Pack vs app/academic modules
- Issue: How do the UI descriptor, the L2 domain pack, and Academic modules coexist without parallel configuration systems?
- Option A: Static `DomainDescriptor` registry covering page map/task form/journey config/action contract (F section 3).
- Option B: L2 Domain Pack on configuration-version machinery + `app/academic` modules (C D-L2-08; B section 4).
- Evidence: Round 2 pair 4 disagreement 4; existing configuration-version machinery (SHA-256, single-active).
- Trade-off: One mechanism avoids duplication; strict separation needs clear ownership.
- Decision: **Three-layer separation: (1) DomainDescriptor = UI/workflow configuration only; (2) task identity/dimension/corpus content = shared registries with domain-owned contents carried by the existing configuration-version machinery (Domain Pack); (3) domain logic/entities = `app/academic` modules (future). No parallel configuration mechanisms.**
- Reason: Each layer owns a distinct concern; C pack and F descriptor are not competitors once scoped.

### D-15 Learner multi-domain identity
- Issue: May one learner hold submissions in both domains?
- Option A: One learner namespace; domain derived from essays; comparability requires same-domain + conditions (E sections 4.1/9.2).
- Option B: Separate learner records per domain.
- Evidence: Learner isolation contract; A open decision 1; cross-domain merging prohibited.
- Trade-off: Shared namespace enables legitimate reuse; separate records maximize isolation.
- Decision: **One learner namespace; domain derived from submissions; same-domain predicate added to history comparability, journey, revision, exports; cross-domain evidence merging prohibited; multi-domain learner profile views deferred.**
- Reason: The isolation contract is about evidence, not identity; derivation avoids redundant columns and keeps isolation at the boundary where it matters.

### D-16 L2 feedback schema version
- Issue: Does L2 reuse `structured-feedback-v0.7.1`?
- Option A: Reuse v0.7.1 for L2 (frozen contract) (E section 4.3).
- Option B: New `structured-feedback-l2-v0.1.0` now.
- Evidence: v0.7.1 is the verified contract; no L2-specific defect identified; Academic may need its own schema later.
- Trade-off: Reuse preserves the frozen contract; a new version is additive but unneeded today.
- Decision: **L2 keeps `structured-feedback-v0.7.1`; any new schema version is decided with the domain that needs it, additively.**
- Reason: No evidence of an L2-specific requirement; silent mutation is prohibited.

### D-17 Domain vocabulary, API surface, configuration model, migration-14 policy
- Issue: Closed vocabulary, API field placement, configuration payload shape, migration defaults/rollback.
- Option A: Additive body/query field; closed whitelist; single configuration payload with domain sections; additive columns with defaults; keep one-step rollback (E section 9).
- Option B: Path prefixes; per-domain configuration families; schema CHECK now; extended rollback.
- Evidence: Frozen endpoint contract (106 classified tuples, `api_surface_contract.py`); single-active/rollback machinery.
- Trade-off: Additive field preserves the contract; per-domain families complicate governance.
- Decision: **`domain` as an additive body/query field (no path changes), closed vocabulary at app layer first, schema CHECK with the future migration; one configuration payload with domain sections; migration 14 additive with defaults and preserved one-step non-destructive rollback; no data backfill.**
- Reason: The frozen API surface is the freeze mechanism; additive-only migration protects the verified DB state.

### D-18 students.domain vs derived
- Issue: Persist domain on learners?
- Option A: Derive from essays (E section 4.1).
- Option B: Add `students.domain` now.
- Evidence: Multi-domain learner policy deferred (D-15); YAGNI.
- Trade-off: Derived avoids redundancy; a column helps multi-domain queries.
- Decision: **Derive from essays; revisit only with a multi-domain learner requirement.**
- Reason: No current consumer needs a learner-level domain; derivation is truthful and cheap.

### D-19 Export/dataset-split domain scoping
- Issue: Are research exports domain-scoped by default?
- Option A: Domain-scoped by default (E section 9.9).
- Option B: Cross-domain flag for corpus work.
- Evidence: Research-validity boundaries; PII/review gates.
- Trade-off: Scoping prevents contamination; a flag enables cross-domain research.
- Decision: **Domain-scoped by default; cross-domain exports are a future Researcher decision.**
- Reason: Cross-domain evidence mixing is the highest-priority research-validity risk (E risk 1).

### D-20 Version single-sourcing
- Issue: Should version constants be consolidated?
- Option A: Adopt single version source before domain work (E section 5.5).
- Option B: Keep current constants.
- Evidence: Stale `0.8.0`/`10` vs migration 13; duplicated wiring blocks; domain-versioned manifests will double surface.
- Trade-off: Refactor cost vs compounding drift.
- Decision: **ADOPT version single-sourcing as a Horizon 1 prerequisite (debt fix, not new abstraction).**
- Reason: The audit trail already under-reports; a second domain makes drift worse.


## 3. Round 4 red-team resolutions — full records (D-21..D-37)

### D-21 (RT-02, BLOCKING) — Domain-attribution authority
- Issue: D-15 said "domain derived from submissions" while D-17 froze `domain` as a client body field; repo convention treats client input as untrusted (`app/practice/mapping.py`).
- Option A: client-asserted body field; Option B: server-derived attribution from workflow/route/workspace identity.
- Evidence: `app/practice/mapping.py` docstring; red-team RT-02; cross-domain merge risk to history/journey/revision/exports.
- Trade-off: server derivation needs a defined rule; client assertion is simple but unsafe.
- Decision: **`domain` is server-derived at write time from workflow/route/workspace identity; any client assertion is advisory only (validated against the request, rejected/ignored on mismatch, and recorded). Attribution provenance (rule + validator version) persists with the submission. Contract test: a request claiming `domain=l2` through the Academic workflow surface is rejected or re-attributed; no evidence table ever holds a domain conflicting with its workflow origin.**
- Reason: evidence isolation is the architecture's core guarantee; classification-critical fields cannot be client-trusted. D-17's API field is thereby amended to "optional advisory field" (additive, no path change).

### D-22 (RT-01, HIGH) — task_type comparability semantics
- Issue: adding `task_type` to comparability would silently change legacy behavior (Python None==None conflates; SQL NULL demotes comparable->not_comparable).
- Evidence: `app/learner/history.py::_classify`; legacy rows have no task_type; frozen contracts (longitudinal event evidence, Journey cycles, insufficient-evidence states).
- Decision: **`task_type` is metadata-only (persisted, displayed, versioned) and participates in NO comparability predicate until the legacy mapping decision; NULL is modeled as explicit `legacy_unclassified` with mapping provenance; the change is validated by a behavior-diff test over a snapshot of the real legacy database (before/after comparability classifications).**
- Reason: zero behavior change for L2 is a hard gate; comparability semantics are frozen contracts.

### D-23 (RT-03, HIGH) — Domain threading surface
- Issue: "all gain a domain equality predicate" left the 33-table surface unspecified.
- Decision: **Domain is derived through submission ancestry for all learner-evidence tables via ONE resolver service (no per-module reimplementation); additive columns only where no ancestry exists; a table-by-table map is published in deliverable 04; isolation contract tests per consumer boundary (history, journey, revision candidates, practice provenance, exports, learner-level endpoints).**
- Reason: a single un-filtered query silently mixes evidence; one resolver keeps semantics uniform.

### D-24 (RT-04, HIGH) — S-CIC scope downgrade
- Issue: freezing an intelligence core with zero consumers/corpora contradicts YAGNI.
- Decision: **The frozen architecture contains only the corpus boundary contract + resource-pack descriptor (versioned, read-only, provenance-tracked). Reference groups, distributions/bands, comparison service, and example index are DEFERRED design units gated on (a) an authorized corpus, (b) a named consumer, (c) licensing, (d) D-07 min-N/coverage rules.**
- Reason: matches Member A section 6.2; prevents framework-building against unverified requirements.

### D-25 (RT-05, HIGH) — CALF/corpus boundary
- Issue: S-CIC band/distribution scope would duplicate CALF measurement/band machinery.
- Evidence: `app/calf/registry.py` (specs, eligibility, `REF-LD-SOPHISTICATION-PENDING`); MetricRegistry; algorithm registry.
- Decision: **CALF/measurement registries own measurement specifications, resource requirements, and band eligibility; corpus distribution/band content is versioned data consumed through CALF's `resource_requirement`; one band-provenance record per normative output.**
- Reason: one measurement surface, one provenance chain (D-07).

### D-26 (RT-06, HIGH) — Registry content layout
- Issue: domain content currently lives inline in shared Python modules; parallel domain work would collide.
- Decision: **Freeze a registry-content layout in Horizon 1: versioned JSON/config data files under per-domain namespaces (e.g., `app/configuration/domain_packs/{domain}/{version}/...`); Python registry modules reduced to mechanism only; registry-content tests validate each domain pack loads under its own namespace.**
- Reason: "never code forks" needs an implementation home; per-domain namespaces make parallel development conflict-free.

### D-27 (RT-07, HIGH) — Duplicate-file hygiene gate
- Issue: 12 untracked `*-冲突-Rain_Win11.py` files (incl. stale `app/services/factory-冲突-Rain_Win11.py`) unaddressed.
- Decision: **Horizon 1 prerequisite: inventory all sync-conflict/duplicate files; freeze a canonical module-set manifest; define a quarantine/exclusion policy (move out of `app/` or document exclusions) with user approval for removal; add a drift check that fails verification on any `-冲突-`/`-Copy`/`-副本` file appearing under `app/`.**
- Reason: module-version ambiguity precedes any measurement-version claim; files are user-owned, so removal requires approval.

### D-28 (RT-09, MEDIUM) — language discriminator semantics
- Decision: **`language` = submission language (closed vocabulary), explicitly distinct from UI locale (bilingual contract untouched) and from learner L1 (per-submission declared context per Council G). If no real consumer emerges during Horizon 1, the field is dropped (YAGNI).**
- Reason: three different semantics must not collide; locale is frozen.

### D-29 (RT-10, MEDIUM) — Version single-sourcing scope
- Decision: **Single source of truth for app/package/API identity ONLY; all artifact/evidence version streams (prompt, calibration, gate/priority, migration, journey, configuration) remain independent and recorded at write time; contract test asserts API-reported version equals the single source.**
- Reason: merging evidence-bearing streams would destroy per-artifact provenance.

### D-30 (RT-11, MEDIUM) — Zero-change regression gate
- Decision: **Horizon 1 acceptance gate: full core suite green; `api_surface_contract.py` regenerated with additive-only diff; locale parity 600/600; golden-submission behavior diff (before/after consolidation over representative persisted submissions incl. history/journey/revision outputs); migration version stays 13 with no data mutation.**
- Reason: "zero behavior change" is a claim; it needs a procedure.

### D-31 (RT-12, MEDIUM) — Domain-isolation invariant list
- Decision: **Frozen invariants: (1) no cross-domain submission appears in another domain's history/journey/revision-candidates/practice provenance; (2) exports domain-scoped by default and reject mixed input; (3) learner-level endpoints filter by domain; (4) revision candidate selection requires domain equality; (5) each invariant is a named contract test.**
- Reason: isolation guarantees must not be invented per department.

### D-32 (RT-13, MEDIUM) — Citation verification record
- Decision: **Academic evidence model gains a versioned verification-rule manifest and an append-only verification record per CitationLink (rule id/version, source revision hash, matched spans, run time, result); `verification_unavailable` semantics frozen when no source text exists; verification remains deterministic and local-only.**
- Reason: `verified` without a verification artifact is un-auditable; never-fabricate requires proof of comparison.

### D-33 (RT-14, MEDIUM) — Calibration ownership boundary
- Decision: **Calibration machinery and registries: Shared Platform & Core / Feedback & Learner Intelligence; threshold and eligibility CONTENT: domain packs (versioned config) via the shared-contract change process, with methodological review for any threshold change (AGENTS.md section 1.11).**
- Reason: thresholds are domain content but their change is governed; L2's calibration curve stays frozen-behavior.

### D-34 (RT-16, MEDIUM) — Office process bounds
- Decision: **Architecture & Integration convenes only for cross-department contract gates and migration coordination by default; ADRs required only for shared-contract changes (internal implementation stays departmental); drift triggers are concrete: contract-test failure, version/registry audit failure, sync-conflict-file drift check (D-27).**
- Reason: process overhead must scale to a single-app repo; IDLE default enforced.

### D-35 (RT-25, MEDIUM) — Test parametrization scope
- Decision: **Core suite stays single-domain (L2) as-is; only domain-seam contracts (discriminator, registries, equality predicates, exports) are parametrized, and only once Domain A content exists; revisit full parametrization at Horizon 2.**
- Reason: parametrizing a second domain with no content would mask the seam and blur suite identity.

### D-36 (RT-26, MEDIUM) — Schema CHECK timing
- Decision: **`CHECK (domain IN ('l2','academic'))` and `DEFAULT 'l2'` ship in the same additive migration 14 that adds the columns (still additive, no backfill); until the migration exists, export-time validation rejects or quarantines unknown domain values.**
- Reason: exports are the most expensive failure surface; invalid values must never silently land in a domain scope.

### D-37 (LOW findings RT-15/RT-17/RT-18/RT-19/RT-20) — Dispositions
- RT-15: charters state S-CIC (when activated) owns mechanisms + feature contract; domains own admissible features, group-selection policy, wording; availability computation shared with Feedback & Learner Intelligence.
- RT-17: FeedbackDimensionRegistry splits into `availability` and `learner_exposure` (`student | research_only`) axes.
- RT-18: deliverable 12 annotates every Horizon 2 item with its required Researcher decisions and blocked-until markers.
- RT-19: contract regeneration (additive-only diff) is a named Horizon 1 step (folded into D-30).
- RT-20: Academic workspace carries an explicit honest state "academic journey unavailable in MVP"; paper-anchored journey stays in the open-decision log.
- REJECTED findings RT-21/RT-22 (not reproducible at HEAD), RT-23 (unsupported), RT-24 (duplicates the candidate's own stance): recorded, no action.


## 4. Red-team resolution status

- BLOCKING: RT-02 → resolved (D-21).
- HIGH: RT-01 (D-22), RT-03 (D-23), RT-04 (D-24), RT-05 (D-25), RT-06 (D-26), RT-07 (D-27) → all resolved.
- MEDIUM: RT-09 (D-28), RT-10 (D-29), RT-11 (D-30), RT-12 (D-31), RT-13 (D-32), RT-14 (D-33), RT-16 (D-34), RT-25 (D-35), RT-26 (D-36) → all resolved.
- LOW: RT-15/17/18/19/20 → dispositions in D-37. REJECTED: RT-21/22/23/24 → no action (evidence examined).
- Accepted risks (explicit): governance process bounds (D-34) accepted as the operating model; corpus deferral accepted; legacy-genre reconciliation stays NR until a Researcher decision; sync-conflict-file removal requires user approval (D-27).

## 5. Freeze audit — 32/32 criteria PASS

All 32 architecture-freeze criteria (Goal section 47) were audited and passed on 2026-08-07. The full audit record is the final freeze decision below; the planning-session runtime log is not required to establish the freeze.

| # | Criterion | Result |
| --- | --- | --- |
| 1 | Actual repository architecture inspected | PASS |
| 2 | Current verified contracts identified | PASS |
| 3 | All Round 1 proposals completed | PASS |
| 4 | Required cross-reviews completed | PASS |
| 5 | Material disagreements recorded | PASS |
| 6 | Chair produced a synthesis | PASS |
| 7 | Independent red-team review completed | PASS |
| 8 | Every BLOCKING issue resolved | PASS |
| 9 | Every HIGH issue resolved or explicitly accepted | PASS |
| 10 | Final product shape defined | PASS |
| 11 | Shared Core boundary defined | PASS |
| 12 | L2 Writing boundary defined | PASS |
| 13 | Academic Writing boundary defined | PASS |
| 14 | Corpus/NLP boundary defined | PASS |
| 15 | Feedback/Learner Intelligence boundary defined | PASS |
| 16 | Frontend/Product Experience boundary defined | PASS |
| 17 | Research Evaluation/Data Governance boundary defined | PASS |
| 18 | Data ownership defined | PASS |
| 19 | Interface ownership defined | PASS |
| 20 | Department ownership defined | PASS |
| 21 | Architecture & Integration Office defined | PASS |
| 22 | Department autonomy rules defined | PASS |
| 23 | Shared-contract governance defined | PASS |
| 24 | ADR policy defined | PASS |
| 25 | Migration coordination defined | PASS |
| 26 | Dependency ordering defined | PASS |
| 27 | Parallel-development rules defined | PASS |
| 28 | DEPARTMENT GREEN and INTEGRATION GREEN defined | PASS |
| 29 | Integration checkpoints defined | PASS |
| 30 | First recommended development Goal for every department identified | PASS |
| 31 | Deferred decisions explicit | PASS |
| 32 | No production architecture accidentally implemented | PASS |
## 6. Final decision

**ARCHITECTURE FROZEN FOR DEPARTMENTAL DEVELOPMENT.**

This was a planning-only architecture Goal; no production implementation occurred. New ADRs append to the Architecture & Integration persistent session (`.agent-workflow/architecture-integration/`, runtime session — noncanonical) in the Goal section 36 format; material shared-contract changes update this canonical register through the shared-contract process.