# 12 — Next-Wave Decision Handoff

**Gate:** WU14 — 2026-08-08
**Office:** Architecture & Integration (Wave-1 Integration Gate)

## 1. Decision basis

These classifications are based on the actual integrated evidence (dependency matrix `01`, merge record `03`, convergence `04`, isolation `05`, migration decision `06`, policy integration `07`, corpus compatibility `08`, academic state `09`, verification `10`), not on assumptions.

## 2. Goal readiness

| Goal | Classification | Prerequisites | Notes |
| --- | --- | --- | --- |
| Corpus Stage 6 | READY_WITH_PREREQUISITES | Wave-1 Integration GREEN (this gate); Shared Core discriminator/vocabularies present; Research Governance admissibility + eligibility policies available (FOUNDATION-AVAILABLE); authorized corpus + licensing decisions still open (RD) | Stage-6 diagnostic comparison must consume `stage6-evidence-admissibility-policy-v0.1.0`; `research_only` learner exposure default; D-08 default (no learner-facing excerpts without Researcher decision). Corpus authorization (D1) and licensing (D3) remain open Researcher decisions. |
| Feedback & Learner Intelligence foundation | WAIT | Stage-6 diagnostic contracts must exist first (this architecture makes corpus-grounded feedback depend on Stage-6 admissibility + learner exposure policy) | Do not start before Corpus Stage 6 has a diagnostic contract; EvaluationProtection/Leakage policies already ratified for its design. |
| Academic persistence implementation | READY_WITH_PREREQUISITES (gated) | Migration-14 design review + A&I coordination (`06_MIGRATION_14_DECISION.md`); owner: Shared Platform & Core for migration; Academic implements repository adapters over the frozen protocols | Trigger: this Goal starts. Migration 14 is a formal NEXT-WAVE prerequisite, NOT required for Wave-1 GREEN. |
| Academic API implementation | WAIT | Academic persistence first; server-derived attribution seam (D-21) and composition-root registration (both present) | No production Academic surface may exist without persistence + domain safety. |
| Frontend Academic work | WAIT | Stable Academic data/API contracts; domain-workspace selector (D-10) only when the Academic workspace ships; locale additive keys | "academic journey unavailable in MVP" honest state required (D-37/RT-20). |

## 3. Explicitly NOT approved

- No Stage-6 implementation, no corpus-grounded learner feedback, no Feedback & Learner Intelligence foundation, no Academic production surface, no new reference groups, no new research decisions, no proficiency/mastery/learning-gain models, no dashboards/exercise-transfer loops/WeChat/cloud deployment (AGENTS.md and Goal section 23).

## 4. Open Researcher decisions that gate future waves (unchanged, no inference)

Corpus authorization (D1), licensing model (D3), band method + normative min-N (D4), task taxonomy (D5), feature-set scope (D8), embeddings (D9), comparison persistence (D10), frequency resource (D11), UI exposure (D12), epistemic-status persistence form, cross-domain exports, learner multi-domain profile views, genre taxonomy authority, audit-sampling final parameters, duplicate handling for model development, CLAWS4 mapping, migration-14 timing.

## 5. Owner follow-ups recorded at this gate

| Follow-up | Owner | Trigger |
| --- | --- | --- |
| Policy-artifact hash robustness to checkout line endings (`.gitattributes -text` or documented LF requirement) | Research Evaluation & Data Governance | before any further policy-hash-sensitive environment runs |
| Export-time domain validation wiring (`validate_domain_scope` into export paths) | Research Evaluation (utility from Shared Core) | first persisted domain column (migration 14) or any Academic row |
| Canonical Python 3.11 re-run of the full regression | Platform/Infrastructure (environment) | when a working 3.11 interpreter is available |
