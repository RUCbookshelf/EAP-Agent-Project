# 00 — Governance Executive Summary

**Department:** Research Evaluation & Data Governance
**Foundation package:** `research-governance-foundation-v0.1.0`
**Date:** 2026-08-07
**Status:** DEPARTMENT GREEN (foundation scope) — NOT Integration GREEN.
**Baseline:** branch `dept/research-governance-foundation`, HEAD `b171cce921975f5ac8491e9bb344a06043eecd69` (goal-declared common Wave-1 baseline).

## 1. Why this foundation exists

The Writing Intelligence Platform architecture is frozen (D-01..D-37) and the Corpus
Stage-5 package is implemented, but the research rules embedded in both were owned by
engineering by default. This foundation makes the methodological decisions governable:
every existing research/methodological decision is inventoried with an owner class
(01_DECISION_INVENTORY.md), the department-owned policies are versioned
(02_POLICY_VERSIONING.md and policies 03-10), Stage-6 evidence-admission rules exist
before any Stage-6 implementation (08), and lightweight deterministic validators keep
the policies machine-checkable (11 + validators).

## 2. Core scientific principle (preserved verbatim)

```text
observed evidence
≠ diagnostic inference
≠ feedback recommendation
≠ learning outcome
```

```text
corpus distance ≠ proficiency
corpus distance ≠ mastery
corpus distance ≠ learning gain
```

No measurement claim may exceed its evidence model (architecture I1-I6, D-07/D-09;
ARCH-07:27-32). This foundation operationalizes that principle into a versioned claim
policy (07) and admissibility rules (08).

## 3. Headline results

1. **Decision inventory (WU1):** 61 inventoried decision rows across architecture,
   product services, Corpus Readiness, Corpus Stage 5, and tests; 35 frozen, 7
   department-policy, 13 temporary engineering decisions awaiting ratification, 4
   rows whose primary class is an open Researcher decision (plus 2 mixed-class rows
   with open components), 1 deferred, 1 evidence record. No Stage-5 choice was
   blindly ratified.
2. **Versioned policy framework (WU2):** one foundation package
   `research-governance-foundation-v0.1.0`; seven named policies each with a versioned
   id, status, owner, and machine-readable artifact.
3. **Corpus use and licensing (WU3):** `license_status = PARTIALLY_DOCUMENTED`
   canonicalized; authorization-state model `ALLOWED / REQUIRES_REVIEW / PROHIBITED /
   UNKNOWN` with per-state evidence; no invented legal rights.
4. **270-text protection (WU4):** the 270 scored expository texts are one protected
   block; permitted and prohibited uses are explicit; circular evaluation is prevented
   by the conservative rule that the same scored block is never used both to construct
   the target signal and to evaluate that signal; reproducible protection keys;
   no irreversible partition.
5. **Duplicate governance (WU5):** physical N, logical N, effective N,
   duplicate-group identity, representative selection, and evaluation isolation are
   defined; the Stage-5 policy is ratified per purpose with a versioned Research
   decision; no source record is deleted; no Corpus implementation changed.
6. **Reference-group eligibility (WU6):** min-N=30 is classified and justified (not as
   a round-number validity claim); eligible/limited/unavailable/requires-review
   criteria are explicit; ARG13/ARG19 status is preserved; the fallback hierarchy is
   ratified with its disclosure contract.
7. **Measurement claim policy (WU7):** permitted and prohibited statements are defined
   per evidence class (observed feature, reference comparison, diagnostic inference,
   feedback recommendation, longitudinal evidence, learning outcome); machine-checkable
   banned-vocabulary guardrails provided.
8. **Stage-6 admissibility (WU8):** `ADMISSIBLE / LIMITED / UNAVAILABLE / INVALID`
   criteria require FeatureSetVersion, ReferenceGroupVersion, DistributionVersion,
   requested/resolved group disclosure, effective N, availability, reproducible feature
   value, missingness, descriptive direction, and prohibit unsupported inference. No
   diagnostic algorithm is defined.
9. **Audit sampling foundation (WU9):** sampling unit/trigger/rate/risk strata/evidence/
   human-review fields/failure categories/version provenance are specified for future
   learner-facing feedback evaluation; isolated deterministic sampler provided.
10. **Leakage framework (WU10):** duplicate groups never split; same-prompt leakage
    controlled; 270 block protected; unknown learner IDs acknowledged; versioned
    partition logic; reusable deterministic validation logic provided.
11. **Validators (WU11):** department-owned lightweight validators and tests pass;
    full core suite remains green.

## 4. Department GREEN criteria (goal section 20)

| Criterion | Status |
| --- | --- |
| Decision ownership is clear | PASS — 01_DECISION_INVENTORY.md |
| Policy versions exist | PASS — 02 + policies/ artifacts |
| Corpus-use governance is explicit | PASS — 03 |
| License restrictions are preserved | PASS — 03 (PARTIALLY_DOCUMENTED; REQUIRES_REVIEW preserved) |
| 270-text protection is explicit | PASS — 04 |
| Duplicate policy is research-owned | PASS — 05 |
| Reference-group eligibility is justified | PASS — 06 |
| Measurement claims are bounded | PASS — 07 |
| Stage-6 admissibility criteria exist | PASS — 08 |
| Audit sampling framework exists | PASS — 09 |
| Leakage policy exists | PASS — 10 |
| Validators/tests pass | PASS — 11_VERIFICATION.md + tests |
| Stage-5 facts remain traceable | PASS — 01 §9; evidence locations cited throughout |
| No other department contract silently changed | PASS — zero changes outside department scope; 12_INTEGRATION_HANDOFF.md lists dependencies |
| Integration handoff is complete | PASS — 12_INTEGRATION_HANDOFF.md |

This is **DEPARTMENT GREEN**, not Integration GREEN. Architecture & Integration must run
the cross-department verification listed in 12 before any milestone claim.

## 5. Integration posture

- **Ratified Stage-5 decisions** (with versioned Research decisions): duplicate policy
  per purpose (05), min-N=30 descriptive floor + fallback disclosure (06), score
  linkage as evaluation-ready evidence (01 D-05), 270 protection (04).
- **Integration dependencies (no silent change):** export-time domain validation
  (D-36) and domain-scoped exports (D-19) need Shared Core Horizon 1; Corpus-department
  documentation follow-ups (Stage-5 review L1-L5); CLAWS4 mapping decision; feature-set
  scope (D8); any future partition must satisfy 10.
- **Binding Stage-6 rules:** 08 (admissibility) and 07 (claim bounds) bind future
  Stage 6/7 work.
- **Open Researcher decisions:** recorded in 01 §8 and 12; none resolved by inference.

## 6. Repository location

All foundation deliverables live under `docs/departments/research-evaluation-governance/foundation/`
(00-12) with machine-readable policy artifacts in `policies/`; validators and tests are
department-owned under the research governance namespace (see 11_VERIFICATION.md).
