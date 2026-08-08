# 12 — Integration Handoff

**Department:** Research Evaluation & Data Governance
**Package:** `research-governance-foundation-v0.1.0`
**Date:** 2026-08-07
**Status:** HANDOFF COMPLETE — DEPARTMENT GREEN, NOT Integration GREEN.
**To:** Architecture & Integration Office (`.agent-workflow/architecture-integration/`, ARCH-11/13), Corpus & NLP, Shared Platform & Core, Feedback & Learner Intelligence.

## 1. Which Stage-5 decisions are RATIFIED (versioned Research decisions)

| Stage-5 decision | Ratified by | Research decision |
| --- | --- | --- |
| Duplicate policy `effective_sample_excludes_non_canonical_duplicate_members` (canonical = lexicographically smallest id) | 05_DUPLICATE_POLICY.md §4.1-4.3 | RD-POL-005 (per-purpose: descriptive statistics keep all documents; reference distributions use effective membership; evaluation isolates; model development NOT settled) |
| min-N = 30 effective for v0.1 reference distributions | 06_REFERENCE_GROUP_ELIGIBILITY_POLICY.md §2 | RD-POL-006 (general feature-independent descriptive floor; NOT a validity claim; normative use blocked by D-07) |
| Fallback hierarchy prompt+timed → prompt → genre+timed → genre → UNAVAILABLE with disclosure | 06 §5 | RD-POL-006 |
| 75 approved groups; ARG13/ARG19 standalone unavailable; documents remain in broader groups | 06 §4 | RD-POL-006 |
| Score linkage (270 WEXP ↔ exp.xls/exp.sav, set equality) | 01 D-05; 04 | RD-POL-004 (evaluation-readiness evidence only) |
| 270 scored expository block protection (no development use without approval; never split; no final partitions) | 04_EVALUATION_PROTECTION_POLICY.md | RD-POL-004 |
| License status `PARTIALLY_DOCUMENTED`; external use REQUIRES_REVIEW | 03_CORPUS_USE_AND_LICENSE_POLICY.md | RD-POL-003 |

## 2. Which Stage-5 decisions are MODIFIED

**None.** No Stage-5 decision was modified, and no Corpus implementation or data
artifact was changed. The two methodology-review documentation conditions (duplicate
fold wording in L2-03; group decomposition in L2-04) were already applied by the
Corpus department before this goal; this foundation cites the corrected wording.

## 3. Which decisions remain PROVISIONAL

| Item | Status | Owner |
| --- | --- | --- |
| Feature-set scope (D8) | `NR`; v0.1 ratified as engineering reference contract only | Researcher decision |
| CLAWS4↔spaCy mapping vs re-tagging | Deferred; no cross-tag comparison without mapping contract | Corpus & NLP + Research Evaluation |
| Duplicate handling for model development | Not settled (05 §4.4) | Researcher decision |
| Band method (quantile vs SD) and normative min-N justification (D4) | Open; descriptive floor only | Researcher decision |
| Reference-group selection per domain profile | Domain-owned (D-37/RT-15); must pass 06 eligibility | L2/Academic domains |
| Comparison persistence location (D10) | `Unclear`; recommendation append-only `student_corpus_comparisons` | Researcher decision |
| Corpus comparison UI exposure (D12) | `Unclear`; recommendation Research first | Researcher decision |
| Frequency-resource authorization (D11) | Open; blocks lexical_sophistication | Researcher decision |
| Corpus authorization (D1) and licensing model (D3) | Open; `UNKNOWN` operations stay blocked | Researcher decision |
| Epistemic-status persistence form | Open; compute-at-boundary interim | Researcher decision |
| Genre taxonomy authority; validity-evidence storage | Open (Horizon 1 charter priorities) | Researcher decision |
| Audit-sampling rate/criteria/reviewer pool | Defaults fixed in 09; final values open | Researcher decision |
| Final corpus exclusion policy (WARG2081 etc.) | Draft candidates only | Researcher decision |
| Entry-year 2003/2007 and other limited groups | `LIMITED` per 06 §3 | Policy applies |
| Stage-5 review LOW findings L1-L5 | Corpus-department documentation follow-ups | Corpus & NLP |

## 4. Which items require CORPUS changes

None required by this foundation. Recommended (Corpus & NLP decision, not ours):
fallback disclosure human-readable reason; `complete-case N` field in distribution
metadata (methodology review non-blocking recommendations). Any change must keep
artifact determinism and the effective-sample policy.

## 5. Which items require SHARED CORE support

| Item | Requirement | Architecture basis |
| --- | --- | --- |
| Domain-scoped exports + export-time domain validation | Export paths reject/quarantine unknown domain values until migration-14 CHECK | D-19, D-36 (ARCH-14:176-183, 269-272) |
| Epistemic-status typing | Persisted additive typed status or compute-at-boundary enforcement seam | D-09 |
| Version single-sourcing | App/package/API identity single source (evidence streams stay independent) | D-20, D-29 |
| Domain-isolation contract tests | Named invariants once discriminator lands | D-31 |

## 6. Which Stage-6 rules are now BINDING

1. 08_STAGE6_EVIDENCE_ADMISSIBILITY.md — every diagnostic comparison needs an
   admissibility record; ADMISSIBLE/LIMITED/UNAVAILABLE/INVALID.
2. 07_MEASUREMENT_CLAIM_POLICY.md — permitted/prohibited statements per evidence
   class; banned vocabulary; downgrade-only display.
3. 06_REFERENCE_GROUP_ELIGIBILITY_POLICY.md — eligibility criteria and fallback
   disclosure for any reference use.
4. 04_EVALUATION_PROTECTION_POLICY.md — the 270 block rules and circularity
   prevention.
5. 05_DUPLICATE_POLICY.md — per-purpose duplicate handling; evaluation isolation.
6. 10_EVALUATION_LEAKAGE_POLICY.md — partition constraints and validator.
7. 09_FEEDBACK_AUDIT_SAMPLING.md — sampling framework for future learner-facing
   feedback evaluation.

## 7. Which issues remain Researcher decisions

See 01 §8 and 12 §3: corpus authorization (D1), licensing model (D3), band method +
normative min-N (D4), task taxonomy (D5), proficiency-annotated metadata (D6),
feature-set scope (D8), embeddings (D9), comparison persistence (D10), frequency
resource (D11), UI exposure (D12), genre taxonomy authority, validity-evidence
storage, audit-sampling final parameters, final corpus exclusion policy, final
duplicate handling for model development, CLAWS4 mapping, epistemic-status
persistence form, cross-domain exports, learner multi-domain profile views. None
were resolved by inference.

## 8. Which policies are VERSIONED

`policies/policy_registry.json` (registry v0.1.0) lists 8 ratified policies with
SHA-256 artifact hashes: `corpus-use-policy-v0.1.0`, `evaluation-protection-policy-v0.1.0`,
`duplicate-handling-policy-v0.1.0`, `reference-group-eligibility-policy-v0.1.0`,
`measurement-claim-policy-v0.1.0`, `stage6-evidence-admissibility-policy-v0.1.0`,
`feedback-audit-sampling-policy-v0.1.0`, `evaluation-leakage-policy-v0.1.0`, plus the
versioning framework itself (`evaluation-policy-versioning-v0.1.0`). Change control:
02 §5.

## 9. Which tests Architecture Integration must run

1. `tests/test_research_governance_v01.py` — 28 governance validator tests
   (department-owned; deterministic; read-only).
2. Full non-live core regression (canonical environment) — must stay green;
   the foundation adds code only under `app/research/governance/**` and tests.
3. Corpus Stage-5 focused suite `tests/corpus` (36) — unchanged, must stay green.
4. At milestone integration: cross-boundary suites for any Stage 6 / Shared Core
   Horizon-1 work consuming these policies (admissibility records, exports,
   domain isolation, partitions) plus `api_surface_contract.py` regeneration if
   any API surface changes (none here).
5. `git diff --check` and repository hygiene (no raw corpus text; no secrets).

## 10. Ownership and boundary statement

- This foundation changes nothing outside `docs/departments/research-evaluation-governance/`,
  `app/research/governance/**`, `tests/test_research_governance_v01.py`, and the
  department planning directory `.agent-workflow/research-evaluation-governance-foundation/`.
- No other department contract was silently changed; no migration; no push/PR;
  branch stays `dept/research-governance-foundation`.
- DEPARTMENT GREEN does not imply Integration GREEN.

## 11. Handoff evidence locations

- Decision inventory: 01_DECISION_INVENTORY.md
- Policy versioning: 02_POLICY_VERSIONING.md + `policies/`
- Verification: 11_VERIFICATION.md
- Independent methodology review: `evidence/methodology_review.md` (all F1-F14 conditions resolved; verdict READY_WITH_CONDITIONS closed to READY)