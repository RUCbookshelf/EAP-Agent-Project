# 02 — Policy Versioning Framework

**Department:** Research Evaluation & Data Governance
**Package:** `research-governance-foundation-v0.1.0`
**Date:** 2026-08-07
**Status:** RATIFIED (framework level)
**Versioning policy id:** `evaluation-policy-versioning-v0.1.0`

## 1. Purpose

This document establishes how research-governance policies are versioned, audited, and
changed. Every policy named here is owned by Research Evaluation & Data Governance
(per the architecture charter, ARCH-10 §7), is human-readable in this foundation
directory, and is machine-checkable through a JSON artifact in `policies/`. Research
policy lives here — never inside Corpus feature code (per D-24 and the goal's
"do not place research policy inside Corpus feature code" rule).

## 2. Policy family and version scheme

- Foundation package id: `research-governance-foundation-v0.1.0` (this directory).
- Policy id format: `<policy-slug>-v<major>.<minor>.<patch>`.
- Version semantics:
  - **major** — change that alters a policy's binding rules, scope, or authorization
    states (breaking change; requires methodological review and, if a shared contract
    is touched, Architecture & Integration review per ARCH-13 §1).
  - **minor** — additive refinement (new evidence, new disclosure field, new statement
    that does not weaken an existing rule).
  - **patch** — clarification/typographical correction with no rule change.
- Policy statuses: `draft` → `ratified` → `amended` → `superseded`. A superseded
  version is never edited or deleted (append-only audit); each new version records
  `supersedes`.
- Every policy carries a ratification decision id `RD-POL-###` recorded in this
  department's decision register (`.agent-workflow/research-evaluation-governance-foundation/decisions.md`)
  and in the policy document itself.

## 3. Policy registry (canonical)

The single machine-readable registry is `policies/policy_registry.json`; it lists every
policy version, its status, effective date, ratification decision id, artifact path, and
content hash (SHA-256 of the JSON artifact bytes). The registry is finalized with the
first ratified policy set in this foundation and is validated by the WU11 validators.

| Policy | Version (this foundation) | Status | Human artifact | Machine artifact | Ratification |
| --- | --- | --- | --- | --- | --- |
| EvaluationPolicyVersion (versioning framework itself) | `evaluation-policy-versioning-v0.1.0` | ratified | 02_POLICY_VERSIONING.md | policies/policy_schema.json | RD-POL-002 |
| CorpusUsePolicy | `corpus-use-policy-v0.1.0` | ratified | 03_CORPUS_USE_AND_LICENSE_POLICY.md | policies/corpus_use_policy.json | RD-POL-003 |
| EvaluationProtectionPolicy | `evaluation-protection-policy-v0.1.0` | ratified | 04_EVALUATION_PROTECTION_POLICY.md | policies/evaluation_protection_policy.json | RD-POL-004 |
| DuplicateHandlingPolicy | `duplicate-handling-policy-v0.1.0` | ratified | 05_DUPLICATE_POLICY.md | policies/duplicate_policy.json | RD-POL-005 |
| ReferenceGroupEligibilityPolicy | `reference-group-eligibility-policy-v0.1.0` | ratified | 06_REFERENCE_GROUP_ELIGIBILITY_POLICY.md | policies/reference_group_eligibility_policy.json | RD-POL-006 |
| MeasurementClaimPolicy | `measurement-claim-policy-v0.1.0` | ratified | 07_MEASUREMENT_CLAIM_POLICY.md | policies/measurement_claim_policy.json | RD-POL-007 |
| Stage6EvidenceAdmissibilityPolicy | `stage6-evidence-admissibility-policy-v0.1.0` | ratified | 08_STAGE6_EVIDENCE_ADMISSIBILITY.md | policies/stage6_evidence_admissibility_policy.json | RD-POL-008 |
| AuditSamplingPolicy | `feedback-audit-sampling-policy-v0.1.0` | ratified | 09_FEEDBACK_AUDIT_SAMPLING.md | policies/audit_sampling_policy.json | RD-POL-009 |
| EvaluationLeakagePolicy | `evaluation-leakage-policy-v0.1.0` | ratified | 10_EVALUATION_LEAKAGE_POLICY.md | policies/evaluation_leakage_policy.json | RD-POL-010 |

## 4. Determinism and auditability

- Content hash: SHA-256 over the exact bytes of each policy JSON artifact, recorded in
  `policy_registry.json`; the WU11 validator recomputes and compares.
- Audit chain: each policy JSON records `supersedes` (null for v0.1.0) and
  `ratification_decision_id`; the registry records effective dates; the department
  decision register records rationale and alternatives.
- Human artifacts and machine artifacts are kept in lockstep: a policy change is not
  effective until both the markdown and the JSON artifact are updated, the registry is
  updated, and the validators pass.

## 5. Change control process

1. **Decision record** — a named change entry in the department decision register
   (rationale, alternatives, affected policies, evidence).
2. **Methodological review** — required for any measurement/threshold/eligibility
   content change (D-33; ARCH-14:257-263) and for any normative interpretation change
   (D-07). Fresh reviewer independent of the proposer.
3. **Architecture & Integration review** — only when the change touches a shared
   contract (ARCH-13 §1: shared API/schema/evidence contracts, Journey vocabulary,
   shared identifiers, cross-domain navigation). Otherwise departmental autonomy
   applies (ARCH-13 §5).
4. **Version bump + artifact update** — per section 2 semantics; update markdown,
   JSON artifact, and registry; superseded versions archived in place.
5. **Verification** — rerun the governance validators (WU11) and the affected
   regression suites.

## 6. Machine-checkable layer

- `policies/policy_schema.json` — JSON Schema (draft-07) that every policy artifact
  must satisfy (policy id/version/status/owner/statements/evidence/ratification).
- `policies/policy_registry.json` — registry with per-version hash.
- WU11 validators: schema validation, hash verification, cross-artifact consistency
  (policy ids referenced in the registry exist; versions match document headers),
  plus the specialized checks described in 03-10.

## 7. Ownership matrix

| Policy | Primary owner | Co-owner / constraint |
| --- | --- | --- |
| EvaluationPolicyVersion | Research Evaluation & Data Governance | Architecture & Integration for shared-contract changes |
| CorpusUsePolicy | Research Evaluation & Data Governance | Corpus & NLP (implementation of boundary), Legal/owner review for any new license evidence |
| EvaluationProtectionPolicy | Research Evaluation & Data Governance | Corpus & NLP (protected-block implementation), Feedback & Learner Intelligence (evaluation design) |
| DuplicateHandlingPolicy | Research Evaluation & Data Governance | Corpus & NLP (data artifacts), Architecture & Integration (partition design changes) |
| ReferenceGroupEligibilityPolicy | Research Evaluation & Data Governance (eligibility); domain profiles (group selection, per D-37/RT-15) | Corpus & NLP (machinery) |
| MeasurementClaimPolicy | Research Evaluation & Data Governance | Feedback & Learner Intelligence (epistemic-status enforcement, D-09) |
| Stage6EvidenceAdmissibilityPolicy | Research Evaluation & Data Governance | Feedback & Learner Intelligence (diagnostic gating), Corpus & NLP (versions/provenance) |
| AuditSamplingPolicy | Research Evaluation & Data Governance (operation); Feedback & Learner Intelligence (design, ARCH-08 §6) | Frontend (rendering) once operating |
| EvaluationLeakagePolicy | Research Evaluation & Data Governance | Shared Platform & Core (domain-isolation contracts D-31), Corpus & NLP (data) |

## 8. Scope

This framework governs research/methodological policies only. Engineering version
streams (prompt, calibration, gate/priority, migration, journey, configuration) remain
independent and recorded at write time per D-29; this framework does not merge them.