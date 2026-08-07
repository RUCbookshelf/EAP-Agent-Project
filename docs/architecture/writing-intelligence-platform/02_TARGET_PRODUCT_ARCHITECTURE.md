# 02 — Target Product Architecture

## 1. One platform, two domains, one pipeline

```text
Writing Intelligence Platform
├── Shared Platform & Core (one app, one DB, one API, one composition root)
│   ├── pipeline skeleton: submit -> analyze -> calibrate/gate -> Feedback -> Revision -> Practice -> Journey
│   ├── registries (analyzer, metric, CALF, configuration, prompt, task-type, feedback-dimension)
│   ├── domain seam: `domain`/`language` discriminator + Domain Descriptor (UI scope)
│   ├── learner history/snapshot/WritingProfile contract, evidence-status + epistemic-status vocabularies
│   ├── corpus boundary contract (S-CIC planned)
│   └── research-validity guardrails (all domains)
├── Domain B — L2 Writing Development Agent (default; current verified system)
│   └── typed task identity, dimension envelope, L2 Domain Pack (content as versioned data)
├── Domain A — Academic Writing Agent (designed; `app/academic` future module)
│   ├── ResearchProject / ResearchQuestion / Source / EvidenceUnit / Claim / PaperSection / CitationLink
│   ├── four provenance chains + local citation verification + integrity guardrails
│   └── whole-paper scaffold; section-level drafting on the shared loop
├── Corpus & NLP Intelligence (planned)
│   ├── Shared Corpus Intelligence Core (manifests, reference groups, distributions, feature contract, comparison)
│   └── L2 / Academic corpus profiles (selection + interpretation only)
├── Feedback & Learner Intelligence
│   ├── FeedbackPolicy contract; evidence-status and epistemic-status enforcement
│   └── feedback audit sampling (evaluation-of-evaluation)
├── Frontend & Product Experience
│   └── shared shell/tokens/locale/navigation; domain-workspace selector when Academic ships
└── Research Evaluation & Data Governance
    └── construct & measurement registry, dataset splitting, PII/review gates, domain-scoped exports
```

## 2. Domain seam mechanics

- `domain` closed vocabulary: `l2` (default) / `academic`; additive body/query field on the frozen API surface; app-layer validation first, schema CHECK with the future additive migration (D-17).
- Registries gain domain-eligibility metadata + `select_for_domain`; the pipeline skeleton stays domain-neutral (D-05).
- Domain content = versioned data/config (analyzers, prompts, calibration weights, exercise specs, task types, corpus profiles) — never code forks (D-04, D-14).
- Evidence isolation at boundaries: history comparability, Journey projection, revision candidate selection, research exports/splits gain a same-domain predicate; cross-domain evidence merging prohibited (D-15, D-19).

## 3. Workflow architecture

- **L2 (unchanged):** task-centric loop — one prompt + one draft → Feedback → Revision → Practice → Journey timeline of task loops.
- **Academic (future):** project-centric hierarchy — Paper → Sections (each a task loop) → Sources/evidence workspace; whole-paper view = persisted-structure facts only; paper-level feedback view deferred until Research Evaluation sign-off (D-12).
- Shared interactions: evidence-first priority cards; no-priority honesty; persisted-feedback-authoritative Revision; priority-derived Practice with provenance; evaluation-unavailable states; activity completion; stable navigation; side-effect-free reads; bilingual Student UI (frozen).

## 4. Versioned interfaces to freeze before parallel development

1. `domain`/`language` contract (values, defaults, validation)
2. TaskTypeRegistry + FeedbackDimensionRegistry schemas (namespaces, availability states)
3. FeedbackPolicy contract (minimum interface; implementation form later)
4. WritingProfile contract (observation-only, domain-tagged, never-merged)
5. Epistemic-status vocabulary (`observed_descriptive` / `gated_inference` / `recommendation` / `outcome_claim`)
6. Evidence-status vocabulary (`verified` / `candidate` / `insufficient` / `suppressed` / `not_applicable` / `unavailable` / `legacy` / `unresolved`)
7. Corpus boundary contract (read-only, versioned, provenance-tracked)
8. API surface contract additions (additive only; endpoint classification contract is the freeze mechanism)
9. Journey event vocabulary (frozen; additive extension only via ADR)

## 5. Module dependency rules

- Dependency direction unchanged: UI → API → services → ports → repositories.
- Domain modules may depend on Shared Core interfaces only; direct domain-to-domain access is prohibited; shared modules must not import domain logic.
- One composition root (`build_platform(settings, domains)` after consolidation); version single-sourcing (D-20).

## 6. What is explicitly NOT in the target architecture

No repo split; no microservices; no per-domain databases/namespaces; no workflow engine/DAG; no event sourcing/CQRS/ORM; no graph database; no web/DOI citation lookup; no auto-citation/bibliography generation; no proficiency/mastery/CEFR/learning-gain constructs; no corpus ingestion/search infrastructure; no plugin framework; no auth/SSO; no visual redesign; no per-domain design tokens.