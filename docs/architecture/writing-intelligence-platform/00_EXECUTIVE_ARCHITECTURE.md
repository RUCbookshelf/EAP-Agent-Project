# 00 — Executive Architecture
**Writing Intelligence Platform — Product Architecture (Frozen)**
**Date:** 2026-08-07 | **Status:** Planning-only Goal (no production implementation)

## 1. Purpose

This document set freezes the next-generation architecture of `writing-feedback-mvp` (v0.9.7-D, verified and closed) so that future development can proceed through multiple semi-independent departmental Goals while remaining one coherent product. The architecture answers the Goal section 4 questions: what stays shared, what is domain-specific, which abstractions are genuinely required, how Corpus Intelligence and NLP evidence integrate, how learner evidence is represented, how Academic Writing joins without contaminating L2, and how departments work independently under governance.

## 2. Product shape (Goal section 17) — HYBRID of Options A and B

**One application, one process, one SQLite database, one API namespace, one composition root; domains are an additive, discriminated dimension of the existing verified pipeline.**

- Option A (one app + configurable domain profiles) is used for its single-shell mechanics, but NOT for generic configurable profiles — the domain seam is a small, versioned registry + discriminator, never a workflow engine.
- Option B (shared core + separate domain application modules) is used for structure: Domain A (`app/academic`, future) and Domain B (current system, default) are modules inside one app.
- Option C (shared services/data + largely independent products) is rejected: no repo split, no separate runtimes, no microservices. Evidence: single verified pipeline with 1237/8/0 tests, 600/600 locale parity, SQLite migration 13, and one learner-isolation contract (see `01_CURRENT_STATE_MAP.md`).

## 3. What stays shared

Pipeline orchestration (submission → analysis → calibration gate → evidence-verified Feedback → Revision → Practice → Journey); repository protocols and SQLite adapters; all registries (analyzer/metric/CALF/configuration/prompt); LLM router/provider/validator/reliability; learner history and snapshot machinery; read-time Journey projection; Practice provenance (`PRIO-{feedback_id}-{priority_index}`); locale/error/lifecycle/PII/research services; UI shell, tokens (D1.3), ports, HTTP-only client; research-validity guardrails.

New shared-core mechanisms (planned only): `domain`/`language` discriminator; TaskTypeRegistry (namespace-scoped); FeedbackDimensionRegistry (availability states); FeedbackPolicy contract; WritingProfile contract (evolution of the learner snapshot contract); corpus boundary contract + resource-pack descriptor; epistemic-status vocabulary; evidence-status vocabulary; feedback audit sampling design.

## 4. What is domain-specific

- **Domain B — L2 Writing Development Agent:** the current verified system remains byte-identical as the default domain; typed task identity, dimension availability states, domain pack content (task-type definitions, expectations, target-code eligibility, locale labels) as versioned data.
- **Domain A — Academic Writing Agent (designed, not implemented):** research-project workspace; seven entities (ResearchProject, ResearchQuestion, Source, EvidenceUnit, Claim, PaperSection, CitationLink); four independent provenance chains (source, evidence, citation, claim–evidence); local-only deterministic citation verification; academic-integrity guardrails. MVP paper view = persisted-structure facts only.

**Evidence-kind separation (non-negotiable):** L2 internal diagnostic evidence and Academic research evidence are two evidence kinds; they never share a schema; Academic evidence is referenced by ID only.

## 5. Intelligence architecture

Shared Corpus Intelligence Core (S-CIC, planned): manifests/versions, reference groups, distributions/bands, authentic-example index, feature contract, deterministic comparison. Domain corpus profiles (L2, Academic): taxonomy mapping, group selection, admissible features, wording, display policy. Invariants: corpus distance is never proficiency/mastery/learning-gain; corpus read-only; same feature contract both sides; explicit unavailable states; deterministic math + LLM wording inside verified slots; observed evidence ≠ diagnostic inference ≠ feedback recommendation ≠ learning outcome. Learner-facing corpus content disabled by default; Research surfaces first.

## 6. Learner evidence (Goal section 21)

Distinct families: submission evidence; revision response; practice response; within-task observation; later-task observation; recurring pattern (TraceStatus). No mastery score, proficiency score, or learning-gain score exists or may be introduced without a separately validated measurement model. `HISTORY_LIMITATION` semantics extend to all longitudinal output.

## 7. Departments and governance

Seven departments (Shared Platform & Core; L2 Writing Domain; Academic Writing Domain; Corpus & NLP Intelligence; Feedback & Learner Intelligence; Frontend & Product Experience; Research Evaluation & Data Governance) plus the permanent, small Architecture & Integration Office (IDLE by default; owns shared-contract governance, ADRs, dependency coordination, integration gates — not feature implementation). Autonomy: internal implementation owned locally; shared contracts governed centrally. Two-level GREEN: DEPARTMENT GREEN ≠ INTEGRATION GREEN.

## 8. Roadmap (dependency-based, no dates)

- **Horizon 1 — Platform Foundation:** composition-root consolidation; version single-sourcing; `domain`/`language` discriminator (additive migration 14+); registry domain-selection policy; frozen shared contracts and vocabularies; corpus boundary contract. Shared profiles are NOT a prerequisite.
- **Horizon 2 — Independent Domain Intelligence:** L2 Domain Pack; Academic domain module; corpus manifests/profiles; academic UI surfaces; feedback audit sampling.
- **Horizon 3 — Advanced Personalization:** longitudinal personalization, recurring-pattern detection, adaptive practice, cross-task learner modeling — gated on validated measurement infrastructure. Proficiency/mastery/learning-gain reporting permanently out of scope.

## 9. Freeze status

Decision: **ARCHITECTURE FROZEN FOR DEPARTMENTAL DEVELOPMENT.** All 32 architecture-freeze criteria were audited and passed (2026-08-07; audit summary in `14_ARCHITECTURE_DECISIONS.md` section 5, baseline record `17_ARCHITECTURE_FREEZE_BASELINE.md`). This was a planning-only architecture Goal with no production implementation.

## 10. Evidence references

- Current-state baseline: `01_CURRENT_STATE_MAP.md`
- Decision register (D-01..D-37, canonical and self-contained): `14_ARCHITECTURE_DECISIONS.md`
- Red-team review: `16_ARCHITECTURE_RED_TEAM_REVIEW.md`
- Department charters: `10_DEPARTMENT_CHARTERS.md`
- Architecture & Integration Office charter: `11_ARCHITECTURE_INTEGRATION_OFFICE_CHARTER.md`
- Integration and governance: `13_INTEGRATION_AND_GOVERNANCE.md`
- Department goal handoffs: `DEPARTMENT_GOAL_HANDOFFS.md`
- Freeze baseline record: `17_ARCHITECTURE_FREEZE_BASELINE.md`
- Companion documents: 02–16 in this directory.
- Session provenance (noncanonical): planning-session deliberation files under `.agent-workflow/writing-intelligence-platform-architecture/` are not required to read or govern the canonical baseline.