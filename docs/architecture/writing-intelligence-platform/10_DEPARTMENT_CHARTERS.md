# 10 — Department Charters

Seven departments (evaluated per Goal section 22; no merge/split — each owns a distinct contract surface) plus the Architecture & Integration Office (charter in `11_ARCHITECTURE_INTEGRATION_OFFICE_CHARTER.md`).

---

## 1. Shared Platform & Core

- **Department:** Shared Platform & Core
- **Mission:** Keep the verified single-pipeline platform intact and extend it with the domain seam and shared contracts so that domain departments can work independently.
- **Owned concepts:** pipeline skeleton; `domain`/`language` discriminator; registries (analyzer/metric/CALF/configuration/prompt/task-type/feedback-dimension); learner history + snapshots; Journey projection; Revision; Practice mechanics + provenance; locale/error/lifecycle/PII; API surface; version single-sourcing; composition root; epistemic/evidence-status vocabularies; WritingProfile and FeedbackPolicy contracts (mechanisms).
- **Owned modules (current + planned):** `app/services`, `app/api`, `app/journey`, `app/revision`, `app/learner`, `app/repositories`, `app/infrastructure/sqlite`, `app/configuration`, `app/errors.py`, `app/lifecycle.py`, `app/ui` shell (tokens/locale/ports/client) jointly with Frontend; `app/version.py` (future).
- **Inputs:** domain content registrations from domain departments; ADR-approved contract changes.
- **Outputs:** frozen shared interfaces; versioned registries; migration stream; verification evidence for shared contracts.
- **Frozen interfaces:** repository adapter signatures; `POST /api/v1/submissions` shape; `ErrorCategory` envelope; journey event vocabulary + dedup key; `PRIO-{...}` grammar; configuration single-active/hash; `PRAGMA user_version` + `schema_migrations`; locale key contract.
- **Upstream dependencies:** none (foundation).
- **Downstream consumers:** all other departments.
- **Things it must not own:** L2/Academic domain content, corpus statistics, feedback wording, pedagogy, UI pages, research instruments.
- **Local test responsibilities:** shared-core suite (existing 1237/8/0); contract tests (`api_surface_contract.py`); migration tests; domain-isolation tests.
- **Integration responsibilities:** owns the integration seams that other departments cross; supports Architecture & Integration gates.
- **Current priorities:** Horizon 1 (composition-root consolidation; version single-sourcing; domain/language discriminator; registry domain-selection policy; shared vocabularies; corpus boundary contract).
- **Future priorities:** maintain shared contracts; additive evolution under governance.
- **Blocking dependencies:** none for Horizon 1; Academic module work depends on this department's Horizon 1 outputs.

---

## 2. L2 Writing Domain

- **Department:** L2 Writing Domain
- **Mission:** Deliver the L2 Writing Development Agent as the preserved, evolving default domain without changing any frozen v0.9.7 contract.
- **Owned concepts:** non-research task types; per-type expectation packs; feedback-dimension availability contents; L2 target-code eligibility; L2 locale labels; L2 comparability rules; L2 Domain Pack content.
- **Owned modules (planned):** L2 Domain Pack configuration versions + resources; task-type registry contents; dimension-envelope contents; practice catalog entries.
- **Inputs:** shared registries and contracts; Research Evaluation sign-off on dimension availability; authorized corpus profiles (future).
- **Outputs:** versioned L2 pack; typed task metadata; dimension availability states; evidence for L2 longitudinal rules.
- **Frozen interfaces:** all v0.9.7 contracts (unchanged); task-type vocabulary (additive); dimension-envelope states.
- **Upstream dependencies:** Shared Platform & Core (registries, discriminator); Feedback & Learner Intelligence (envelope contract); Research Evaluation (availability sign-off).
- **Downstream consumers:** Frontend (L2 surfaces); Feedback & Learner Intelligence (dimension states).
- **Things it must not own:** Academic entities/sources/citations; proficiency/CEFR/level constructs; task banks; corpus statistics.
- **Local test responsibilities:** pack validation; comparability rule-version tests; legacy-genre reconciliation tests (explicit mapping, no inference); locale parity for new labels.
- **Integration responsibilities:** domain-isolation tests with Shared Core; milestone gates with Frontend.
- **Current priorities:** Horizon 2 — typed task identity + L2 Domain Pack v1 + dimension envelope (feasibility spike for discourse-organization evidence).
- **Future priorities:** corpus profiles for L2; organization evidence (if spike passes); new exercise kinds (Researcher-gated).
- **Blocking dependencies:** Horizon 1 discriminator/registry work; task-type enumeration decision (`Researcher decision required`).

---

## 3. Academic Writing Domain

- **Department:** Academic Writing Domain
- **Mission:** Design and deliver the Academic Writing Agent that guides rather than fabricates, layered on the shared loop.
- **Owned concepts:** ResearchProject; ResearchQuestion; Source; EvidenceUnit; Claim; PaperSection; CitationLink; four provenance chains; local citation verification; academic-integrity guardrails; Academic task/paper/section kinds (separate namespace).
- **Owned modules (planned):** `app/academic/` (project, sources, claims, citation, integrity sub-domains) behind repository protocols; additive section context on submissions.
- **Inputs:** shared loop contracts; Horizon 1 discriminator; Research Evaluation validity rules; corpus profiles (future).
- **Outputs:** Academic entity schemas (design); provenance/verification states; integrity-guardrail service design; academic FeedbackPolicy instance design.
- **Frozen interfaces:** shared loop contracts (additive only); academic evidence referenced by ID only (never merged with diagnostic evidence).
- **Upstream dependencies:** Shared Platform & Core; Feedback & Learner Intelligence (FeedbackPolicy contract); Research Evaluation (citation/validity policy).
- **Downstream consumers:** Frontend (paper/section/sources surfaces); Corpus & NLP (academic corpus profiles).
- **Things it must not own:** L2 content; shared pipeline orchestration; Journey mechanics; researcher tooling; plagiarism detection (NA).
- **Local test responsibilities:** provenance-chain tests; verification-state tests; integrity-guardrail tests (never-fabricate); schema `extra="forbid"` discipline.
- **Integration responsibilities:** section-submission integration with shared pipeline; milestone gates with Frontend/Corpus.
- **Current priorities:** Horizon 2 — MVP entity design, provenance chains, local citation verification, section workflow (implementation after Horizon 1).
- **Future priorities:** paper-level structure views; rhetorical-move guidance; academic corpus profiles.
- **Blocking dependencies:** Horizon 1; source-verification pre-gate design approval (D-03); Research Evaluation citation policy.

---

## 4. Corpus & NLP Intelligence

- **Department:** Corpus & NLP Intelligence
- **Mission:** Provide versioned, provenance-tracked, read-only corpus intelligence that feeds diagnostic evidence without ever implying proficiency/mastery/learning-gain.
- **Owned concepts:** S-CIC (manifests, reference groups, distributions/bands, example index, feature contract, comparison); domain corpus profiles (selection/interpretation); feature versions; `TaskSignature` matching.
- **Owned modules (planned):** corpus manifest/distribution/comparison services + tables (future additive migration); profile registries.
- **Inputs:** authorized corpora (Researcher decision); student NLP snapshots from Shared Core; domain taxonomies from L2/Academic departments.
- **Outputs:** `ReferencePatternMatch` artifacts; availability states; corpus-grounded evidence slots; version/provenance records.
- **Frozen interfaces:** I1–I6 invariants; feature contract; naming contract (banned tokens); corpus boundary contract.
- **Upstream dependencies:** Shared Platform & Core (snapshots, metrics, CALF statuses); Research Evaluation (licensing, display policy); L2/Academic (taxonomies).
- **Downstream consumers:** Feedback & Learner Intelligence (diagnostic evidence); Frontend (research surfaces first).
- **Things it must not own:** learner data; diagnosis semantics; feedback wording; pedagogy; domain taxonomies.
- **Local test responsibilities:** distribution eligibility (min-N/coverage); version-mismatch refusal; fallback-analyzer refusal; I1 naming checks.
- **Integration responsibilities:** corpus-slot validation with Feedback; research-first exposure gates.
- **Current priorities:** Horizon 2 — corpus boundary contract implementation, manifest/profile scaffolding, deterministic extraction pipeline design (no authorized corpus yet; contents `NR`).
- **Future priorities:** authentic-example index; academic corpus profiles; longitudinal band evidence.
- **Blocking dependencies:** authorized corpus selection (D1) and licensing (D3); band method + min-N (D4); feature-set scope (D8).

---

## 5. Feedback & Learner Intelligence

- **Department:** Feedback & Learner Intelligence
- **Mission:** Own the shared feedback-selection shape, learner-evidence semantics, and the epistemic/evidence-status enforcement across the whole loop.
- **Owned concepts:** FeedbackPolicy contract; evidence-status vocabulary; epistemic-status taxonomy; learner evidence families; feedback audit sampling; validated-measurement gate mechanics; construct & measurement registry mechanics.
- **Owned modules (current + planned):** `app/calibration`, `app/feedback` (validator/reliability), `app/learner/history.py`, `app/practice` evaluations/completion; audit-sampling design (future).
- **Inputs:** gated signals; domain FeedbackPolicy instances; corpus evidence slots; construct registry contents (domain-owned).
- **Outputs:** feedback policy instances; epistemic-status enforcement; audit samples; release-gate recommendations.
- **Frozen interfaces:** feedback schema v0.7.1 (L2); gate/priority versions; honest-state semantics; `HISTORY_LIMITATION`.
- **Upstream dependencies:** Shared Platform & Core (pipeline, registries); Corpus & NLP (slots); domain departments (policy contents).
- **Downstream consumers:** Frontend (feedback/practice/journey surfaces); Research Evaluation (audit data).
- **Things it must not own:** domain feedback content/dimensions; learner-outcome claims; corpus statistics.
- **Local test responsibilities:** gate/priority tests; validator tests; epistemic-status invariant tests; audit-sampling criteria tests.
- **Integration responsibilities:** slot validation with Corpus; policy-activation gates.
- **Current priorities:** Horizon 1 — evidence-status vocabulary; Horizon 2 — audit sampling; FeedbackPolicy instances.
- **Future priorities:** validated-measurement gate operation for Horizon 3 capabilities.
- **Blocking dependencies:** none for vocabulary work; audit sampling needs Research Evaluation staffing.

---

## 6. Frontend & Product Experience

- **Department:** Frontend & Product Experience
- **Mission:** Preserve the frozen Student experience and deliver domain-appropriate workflow architecture for both domains.
- **Owned concepts:** entry model; workspace structure; navigation (StableReferenceNav); DomainDescriptor (UI scope); journey stage configuration; interaction patterns; next-action contract; locale presentation.
- **Owned modules:** `app/ui/**` (shell, pages, features, components, tokens, locale, client, ports, contracts).
- **Inputs:** domain definitions (B/C/A), data contracts (E), validity rules (G).
- **Outputs:** rendered surfaces; workflow architecture; locale additions (parity-tested).
- **Frozen interfaces:** D1.3 tokens; 600/600 locale parity; HTTP-only client; side-effect-free reads; stable navigation.
- **Upstream dependencies:** Shared Platform & Core; L2/Academic domain definitions; Research Evaluation (validity wording).
- **Downstream consumers:** learners and researchers (users).
- **Things it must not own:** domain logic; backend schemas; corpus/feedback content semantics.
- **Local test responsibilities:** rendered matrix; locale parity; navigation-preset tests; role-separation smoke tests; Playwright live tests.
- **Integration responsibilities:** end-to-end workflow tests with domains; milestone gates.
- **Current priorities:** v0.9.7-E (responsive/mobile/accessibility) sequencing; no academic UI before contracts.
- **Future priorities:** Academic workspace surfaces (paper/sections/sources) after domain contracts.
- **Blocking dependencies:** domain data contracts (B/E); whole-paper feedback decision (D-12) and G sign-off.

---

## 7. Research Evaluation & Data Governance

- **Department:** Research Evaluation & Data Governance
- **Mission:** Guard research validity, evaluate evaluation, and govern data use across the platform.
- **Owned concepts:** construct & measurement registry mechanics; corpus provenance/fit and licensing policy; reference-group policy; feedback audit operation; dataset splitting; PII/review gates; domain-scoped exports; genre taxonomy authority; methodological review.
- **Owned modules (current + planned):** `app/research` (scanner/service/schemas), human reviews, exports; audit-sampling operation (future); registry governance.
- **Inputs:** construct definitions (domains); corpus manifests (Corpus dept); export requests; audit samples.
- **Outputs:** validity-evidence records; release-gate rulings; export datasets; methodology decisions; `NR`/`Unclear`/`Researcher decision required` resolutions.
- **Frozen interfaces:** research-validity boundaries (no proficiency/mastery/learning-gain claims); AGENTS.md section 1.11; PII handling.
- **Upstream dependencies:** all departments (artifacts to govern).
- **Downstream consumers:** all departments (gates and rulings).
- **Things it must not own:** feature implementation; feedback generation; UI implementation; corpus statistics.
- **Local test responsibilities:** split integrity; PII scanning; export schema tests; audit criteria tests.
- **Integration responsibilities:** milestone validity gates; release-level rulings.
- **Current priorities:** Horizon 1 — genre taxonomy authority decision; validity-evidence storage decision; Horizon 2 — audit sampling operation; construct registry governance.
- **Future priorities:** validated-measurement gate for Horizon 3; cross-domain export policy (Researcher decision).
- **Blocking dependencies:** researcher staffing; domain construct submissions.

## Charter amendments (Round 4 red team; decisions D-21..D-37)

- Shared Platform & Core additionally owns: the domain-attribution resolver service (server-derived `domain`, D-21); the registry-content layout mechanism (`domain_packs` namespaces, D-26); the canonical module-set manifest + duplicate-file drift check (D-27); version single-sourcing for app/package/API identity only (D-29); the Horizon 1 zero-change regression gate (D-30); domain-isolation invariant contract tests (D-31).
- L2 Writing Domain: `task_type` metadata-only until the legacy mapping decision (`legacy_unclassified` semantics, D-22); dimension envelope uses separate `availability` and `learner_exposure` axes (D-37/RT-17).
- Academic Writing Domain: citation verification requires the append-only verification record + verification-rule manifest (D-32); "academic journey unavailable in MVP" honest state (D-37/RT-20).
- Corpus & NLP Intelligence: frozen scope = corpus boundary contract + resource-pack descriptor; S-CIC machinery deferred and gated (D-24); band/distribution content consumed through CALF `resource_requirement` — one band-provenance record per normative output (D-25); owns mechanisms + feature contract; domains own admissible features/group selection/wording; availability computation shared with Feedback & Learner Intelligence (D-37/RT-15).
- Feedback & Learner Intelligence: owns calibration machinery; thresholds/eligibility content lives in domain packs with methodological review (D-33); operates `availability`/`learner_exposure` axes.
- Research Evaluation & Data Governance: export-time validation rejects/quarantines unknown domain values until the schema CHECK exists (D-36); Horizon 2 gate annotations owned here for Researcher decisions.