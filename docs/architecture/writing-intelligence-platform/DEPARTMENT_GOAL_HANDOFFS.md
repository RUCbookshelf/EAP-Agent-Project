# DEPARTMENT_GOAL_HANDOFFS

Reusable starting briefs for future departmental `/goal` sessions (Goal section 45 format). Paste the relevant block into a new goal; each department's detailed charter is in `10_DEPARTMENT_CHARTERS.md`.

---

## Shared Platform & Core

- **Department:** Shared Platform & Core
- **Current architecture baseline:** product baseline writing-feedback-mvp @ master, HEAD 225181c (v0.9.7-D closed, 1237/8/0 core, locale 600/600, migration 13, 33 tables); architecture baseline = the architecture-freeze commit recorded in `17_ARCHITECTURE_FREEZE_BASELINE.md`; frozen per `docs/architecture/writing-intelligence-platform/` (see 00, 02, 03, 14).
- **Mission:** Keep the verified single-pipeline platform intact; deliver Horizon 1 (domain seam, registries, shared contracts, vocabularies) so domain departments can work independently.
- **Owned scope:** composition root consolidation; version single-sourcing (identity only, D-29); `domain`/`language` discriminator + server-derived attribution resolver (D-21) + additive migration 14 (D-17/D-36); registry domain-selection policy; registry-content layout (`domain_packs`, D-26); TaskTypeRegistry/FeedbackDimensionRegistry schemas; evidence-status + epistemic-status vocabularies (persistence form: Researcher decision required); WritingProfile/FeedbackPolicy contracts; corpus boundary contract; domain-isolation contract tests; duplicate-file manifest + drift check (D-27).
- **Out of scope:** L2/Academic content; corpus statistics; feedback wording; UI pages; research instruments; proficiency/mastery/learning-gain constructs.
- **Frozen contracts:** all v0.9.7 contracts; repository adapter signatures; `POST /api/v1/submissions` shape (additive only); ErrorCategory envelope; journey event vocabulary + dedup key; `PRIO-{...}` grammar; configuration single-active/hash; `PRAGMA user_version` + `schema_migrations`; locale key contract; research-validity boundaries.
- **Upstream dependencies:** none (foundation).
- **Downstream consumers:** all departments.
- **Current development objective:** Horizon 1 per `12_DEPENDENCY_ROADMAP.md`, incl. the D-30 zero-change regression gate.
- **Recommended first Work Units:** WU1 composition-root consolidation + version single-sourcing (golden-submission diff); WU2 domain discriminator vocabulary + attribution resolver + API additive field; WU3 additive migration 14 (CHECK + DEFAULT, no backfill) + registry selection policy; WU4 registry-content layout + vocabularies + isolation contract tests; WU5 duplicate-file manifest + drift check + contract regeneration.
- **Required tests:** full core suite; contract regeneration additive-only diff; locale parity 600/600; golden-submission behavior diff; migration tests (13→14 additive, rollback); domain-isolation invariants (D-31).
- **Integration gate:** Milestone Integration Gate with any domain consuming the discriminator.
- **Stop conditions:** any frozen-contract behavior change without an ADR; any client-trusted domain assertion; any migration beyond additive scope.

---

## L2 Writing Domain

- **Department:** L2 Writing Domain
- **Current architecture baseline:** the current verified system IS the L2 domain (default domain; domain B). Architecture: `06_L2_WRITING_DOMAIN.md`, `03_SHARED_CORE_AND_DOMAIN_BOUNDARIES.md`.
- **Mission:** Deliver the L2 Writing Development Agent as the preserved default domain: typed task identity + L2 Domain Pack v1 + honest dimension envelope, with zero behavior change to frozen contracts.
- **Owned scope:** task-type enumeration decision input; per-type expectation packs; dimension availability/learner-exposure contents; L2 target-code eligibility; L2 locale labels; L2 comparability rule-version bump (after D-22 conditions); Domain Pack content under `domain_packs/l2/`.
- **Out of scope:** Academic entities/sources/citations; proficiency/CEFR/level constructs; task banks; corpus statistics; new Journey event types; UI picker (deferred D-L2-10).
- **Frozen contracts:** all v0.9.7 contracts; `structured-feedback-v0.7.1`; task_type metadata-only until legacy mapping (D-22).
- **Upstream dependencies:** Horizon 1 discriminator/registries; D-L2-01 enumeration decision; D-L2-03 dimension feasibility spike; Research Evaluation availability sign-off.
- **Downstream consumers:** Frontend (L2 surfaces); Feedback & Learner Intelligence (dimension states).
- **Current development objective:** Horizon 2 L2 Domain Pack v1 (blocked until D-L2-01/D-L2-03).
- **Recommended first Work Units:** WU1 task-type vocabulary + registry contents (namespace-scoped); WU2 dimension envelope with availability/learner_exposure axes; WU3 Domain Pack configuration version + resources; WU4 comparability rule-version bump (with legacy behavior-diff test per D-22); WU5 locale additions (parity 600/600).
- **Required tests:** pack validation; comparability before/after behavior-diff over legacy DB snapshot; legacy-genre mapping tests (explicit only, no inference); locale parity; domain-isolation invariants.
- **Integration gate:** Cross-Department Contract Gate for task-type/dimension registry changes; Milestone Gate with Frontend.
- **Stop conditions:** any silent legacy-genre inference; any new dimension without deterministic evidence; any exercise kind without Researcher decision.

---

## Academic Writing Domain

- **Department:** Academic Writing Domain
- **Current architecture baseline:** greenfield (no Academic concepts in repo); design frozen in `05_ACADEMIC_WRITING_DOMAIN.md`, `03_SHARED_CORE_AND_DOMAIN_BOUNDARIES.md`, decisions D-03/D-12/D-13/D-32.
- **Mission:** Deliver the Academic Writing Agent that guides rather than fabricates: research-project workspace on the shared loop with four provenance chains and local citation verification.
- **Owned scope:** seven entities (ResearchProject, ResearchQuestion, Source, EvidenceUnit, Claim, PaperSection, CitationLink); provenance chains; local deterministic citation verification + verification records (D-32); integrity guardrails; academic FeedbackPolicy instance; `app/academic/` module design; section workflow on the shared loop; "academic journey unavailable in MVP" honest state.
- **Out of scope:** whole-paper coherence analysis; web/DOI lookup; auto-citation/bibliography; proficiency/mastery/learning-gain constructs; plagiarism detection (NA); L2 content; researcher tooling.
- **Frozen contracts:** all v0.9.7 contracts (additive section context only); evidence-kind separation (never merged); journey event vocabulary; citation policy default (never by default).
- **Upstream dependencies:** Horizon 1; D-03 pre-gate approval; G citation policy; D-12 whole-paper decision; Research Evaluation taxonomy authority.
- **Downstream consumers:** Frontend (paper/sections/sources surfaces); Corpus & NLP (academic profiles).
- **Current development objective:** Horizon 2 MVP (blocked until citation policy + D-03 + D-12).
- **Recommended first Work Units:** WU1 entity/schema design + provenance-chain contracts (design doc + tests); WU2 local citation-verification service + verification records; WU3 section workflow on the shared loop (additive submission context); WU4 integrity-guardrail service; WU5 academic FeedbackPolicy instance design.
- **Required tests:** provenance-chain tests; verification-record tests; never-fabricate guardrail tests; schema `extra="forbid"` discipline; domain-isolation invariants; academic-journey honest state rendering.
- **Integration gate:** Milestone Integration Gate with Shared Platform & Core and Frontend.
- **Stop conditions:** any auto-generated citation/source content; any merged evidence schema; any proficiency/learning-gain claim.

---

## Corpus & NLP Intelligence

- **Department:** Corpus & NLP Intelligence
- **Current architecture baseline:** corpus layer greenfield; frozen scope = corpus boundary contract + resource-pack descriptor (D-24); design in `07_CORPUS_NLP_ARCHITECTURE.md`, `04_DATA_AND_INTELLIGENCE_ARCHITECTURE.md`.
- **Mission:** Provide versioned, provenance-tracked, read-only corpus intelligence that never implies proficiency/mastery/learning-gain; deliver the deferred S-CIC design units only when gated.
- **Owned scope:** corpus boundary contract implementation; resource-pack descriptors; deferred design units (manifests, reference groups, distributions/bands, feature contract, comparison service, example index) gated on authorized corpus + consumer + licensing + min-N rules; corpus content consumed through CALF `resource_requirement` (D-25); TaskSignature matching (with domain profiles).
- **Out of scope:** learner data; diagnosis semantics; feedback wording; pedagogy; domain taxonomies; corpus ingestion/search infrastructure; learner-facing corpus content (disabled by default, D-08).
- **Frozen contracts:** I1–I6 invariants; naming contract (banned tokens); feature contract; all v0.9.7 contracts.
- **Upstream dependencies:** authorized corpus (D1) + licensing (D3) + band method/min-N (D4) + feature-set scope (D8) + feature-version baseline hygiene (D-27); domain taxonomies from L2/Academic; CALF statuses.
- **Downstream consumers:** Feedback & Learner Intelligence (slots); Frontend (research surfaces first).
- **Current development objective:** Horizon 2 scaffolding (boundary contract + descriptors); all content `NR` until authorization.
- **Recommended first Work Units:** WU1 corpus boundary contract + resource-pack descriptor schema; WU2 manifest/provenance design (hash, license, hygiene); WU3 feature-contract design aligned with CALF; WU4 (gated) reference-group/distribution design once D1/D3/D4 resolve.
- **Required tests:** distribution eligibility (min-N/coverage); version-mismatch refusal; fallback-analyzer refusal; I1 naming checks; provenance-chain tests.
- **Integration gate:** Cross-Department Contract Gate for corpus boundary; Milestone Gate before any corpus-grounded diagnosis.
- **Stop conditions:** any proficiency/level/score output; any LLM-generated corpus claim; any learner-facing exposure without display policy.

---

## Feedback & Learner Intelligence

- **Department:** Feedback & Learner Intelligence
- **Current architecture baseline:** calibration/feedback/learner machinery verified in repo; design in `08_FEEDBACK_LEARNER_INTELLIGENCE.md`, decisions D-03/D-09/D-33.
- **Mission:** Own the shared feedback-selection shape, learner-evidence semantics, and epistemic/evidence-status enforcement across the loop.
- **Owned scope:** FeedbackPolicy contract + instances (L2 default; Academic instance with pre-gate); evidence-status vocabulary; epistemic-status taxonomy (persistence form: Researcher decision required); learner-evidence family semantics; feedback audit sampling design (blocked until G D6); validated-measurement gate mechanics; calibration machinery (threshold CONTENT in domain packs, D-33); dimension registry availability/learner_exposure axes operation.
- **Out of scope:** domain content/dimensions; learner-outcome claims; corpus statistics; feedback wording content.
- **Frozen contracts:** `structured-feedback-v0.7.1` (L2); gate/priority versions; honest-state semantics; `HISTORY_LIMITATION`; activity-only completion.
- **Upstream dependencies:** Shared Platform & Core; Corpus & NLP (slots); domain departments (policy contents).
- **Downstream consumers:** Frontend; Research Evaluation (audit data).
- **Current development objective:** Horizon 2 — audit sampling design + FeedbackPolicy instances.
- **Recommended first Work Units:** WU1 evidence-status vocabulary documentation + status mapping; WU2 epistemic-status taxonomy enforcement design (downgrade-only invariant); WU3 audit-sampling design (with Research Evaluation); WU4 FeedbackPolicy instance formalization (L2 default, behavior-preserving).
- **Required tests:** gate/priority tests; validator tests; epistemic-status invariant tests; audit criteria tests.
- **Integration gate:** Milestone Gate with Corpus & NLP for slot validation.
- **Stop conditions:** any outcome-layer write without validated-measurement gate; any feedback→outcome attribution; any practice-completion semantic drift.

---

## Frontend & Product Experience

- **Department:** Frontend & Product Experience
- **Current architecture baseline:** v0.9.7-D Student UI frozen (D1.3 tokens, 600/600 locale, stable navigation); design in `09_FRONTEND_WORKFLOW_ARCHITECTURE.md`.
- **Mission:** Preserve the frozen Student experience; deliver domain-appropriate workflow architecture (L2 unchanged; Academic surfaces when contracts exist).
- **Owned scope:** entry model; workspace structure; DomainDescriptor (UI scope, static); StableReferenceNav contract; journey stage configuration (deferred D-11); interaction patterns; next-action contract; locale presentation; Academic paper/sections/sources surfaces (blocked until domain data contracts + D-12/G sign-off).
- **Out of scope:** domain logic; backend schemas; visual redesign; per-domain tokens; URL routing/framework swap; auth/SSO; mastery/proficiency displays.
- **Frozen contracts:** D1.3 tokens + parity; 600/600 locale parity; HTTP-only client; side-effect-free reads; stable navigation; learner isolation; role separation.
- **Upstream dependencies:** domain data contracts (B/E); Research Evaluation wording rules; v0.9.7-E sequencing.
- **Downstream consumers:** learners and researchers.
- **Current development objective:** v0.9.7-E sequencing; no Academic UI before contracts.
- **Recommended first Work Units:** WU1 StableReferenceNav contract documentation + tests; WU2 DomainDescriptor design (UI scope) with locale/test impact analysis; WU3 (gated) Academic workspace IA prototype once contracts land.
- **Required tests:** rendered matrix; locale parity; navigation-preset tests; role-separation smoke; Playwright live; academic-journey honest state rendering.
- **Integration gate:** Milestone Integration Gate with Academic/Shared Core.
- **Stop conditions:** any visual redesign of frozen surfaces; any domain logic in UI; any proficiency/mastery display.

---

## Research Evaluation & Data Governance

- **Department:** Research Evaluation & Data Governance
- **Current architecture baseline:** `app/research` verified (splits, PII, exports, human review); governance rules in AGENTS.md section 1.11; design in `08_FEEDBACK_LEARNER_INTELLIGENCE.md`, decisions D-09/D-31/D-36.
- **Mission:** Guard research validity, evaluate evaluation, and govern data use across the platform.
- **Owned scope:** construct & measurement registry mechanics; corpus provenance/fit/licensing policy; reference-group policy; feedback audit operation (with Feedback & Learner Intelligence); dataset splitting; PII/review gates; domain-scoped exports (+ export-time domain validation until CHECK, D-36); genre taxonomy authority; methodological review; Researcher-decision tracking for all open questions in `15_OPEN_QUESTIONS_AND_DEFERRED_DECISIONS.md`.
- **Out of scope:** feature implementation; feedback generation; UI; corpus statistics.
- **Frozen contracts:** research-validity boundaries; PII handling; AGENTS.md section 1.11.
- **Upstream dependencies:** all departments (artifacts to govern); researcher staffing.
- **Downstream consumers:** all departments (gates and rulings).
- **Current development objective:** Horizon 1 — genre taxonomy authority decision; validity-evidence storage decision; Horizon 2 — audit operation; construct registry governance.
- **Recommended first Work Units:** WU1 open-decision register governance + gate annotation maintenance; WU2 export-time domain validation; WU3 audit-sampling criteria + reviewer pool plan; WU4 construct-registry mechanics design.
- **Required tests:** split integrity; PII scanning; export schema tests; audit criteria tests; domain-scope rejection tests.
- **Integration gate:** Milestone validity gates; Release Gate rulings.
- **Stop conditions:** any validity boundary relaxation; any silent resolution of a Researcher decision; any cross-domain export without policy.

---

## Architecture & Integration Office (persistent session)

- Persistent session (runtime, noncanonical): `.agent-workflow/architecture-integration/` — active decisions, shared-contract proposals, cross-department blockers, integration checkpoints, architecture debt, deferred decisions. Charter: `11_ARCHITECTURE_INTEGRATION_OFFICE_CHARTER.md`; operating rules: `13_INTEGRATION_AND_GOVERNANCE.md`.
- First recommended Goal for the office: none (office activates on triggers; no feature work).