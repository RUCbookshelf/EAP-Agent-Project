# 09 — Feedback Audit Sampling Foundation

**Department:** Research Evaluation & Data Governance (operation); design shared with Feedback & Learner Intelligence (ARCH-08:23-25)
**Policy id:** `feedback-audit-sampling-policy-v0.1.0`
**Ratification:** RD-POL-009 (2026-08-07)
**Status:** RATIFIED (framework; operation deferred)
**Supersedes:** none (first canonical version)

## 1. Purpose

Sample-based human review of feedback outputs (evaluation-of-evaluation) against
pre-registered criteria: evidence grounding, false positives, pedagogical framing
(ARCH-08:23-25). This foundation defines the audit framework for future learner-facing
feedback. It lives separately from learner-outcome evaluation to prevent circularity.
No learner-facing Feedback is built here; the framework is designed for future
evaluability.

## 2. Sampling unit

- **Primary unit:** one feedback delivery instance = one persisted `feedback_id`
  (evidence-validated feedback record for one submission).
- **Secondary unit:** one practice evaluation (`practice_evaluation_id`) when feedback
  audit covers practice outcomes.
- A sampled unit is audited as a whole (record + its evidence chain), never a partial
  excerpt.

## 3. Sampling trigger

1. **Systematic:** every Nth unit by stable hash (deterministic, reproducible).
2. **Risk-stratified override:** 100% sampling of high-risk strata (section 5).
3. **On-demand:** targeted investigation samples for reported issues, provider
   fallback/repair events, or PII review outcomes — each on-demand sample records its
   reason and is capped.

## 4. Sampling rate and policy

- Default rate: **5%** systematic (deterministic hash selection), with a minimum
  sample size of 1 per batch and a documented cap: **cap = 50 records per batch**
  (systematic) and **20 per event type** (on-demand) (F9 resolution).
- The rate, criteria, and reviewer pool remain a **Researcher decision** (ARCH-15:63);
  this policy fixes defaults and the change path (02 §5): any rate change = policy
  amendment + methodological review, recorded in `policy_registry.json`.
- Selection is deterministic: `hash(feedback_id) % 100 < rate_percent` (stable hash,
  versioned sampler rule `audit-sampler-v0.1.0`); reruns reproduce the same sample.
- **Stratum combination (F9 resolution):** the audit sample is the union of the
  systematic selection and the 100% high-risk/special strata, de-duplicated by
  feedback id, with high-risk records prioritized and the batch cap applied
  (`apply_stratum_sampling`); a record in the systematic sample that also falls in a
  100% stratum is counted once.

## 5. Risk strata

| Stratum | Definition | Sampling |
| --- | --- | --- |
| HIGH | Feedback containing strength claims, corpus-grounded output (future Stage 6), longitudinal statements, admitted low-confidence signals, or fallback-resolved comparisons | 100% |
| MEDIUM | Standard feedback with selected priorities, verified evidence | 5% default |
| LOW | No-priority / insufficient-evidence / evaluation-unavailable states | 2% default |
| SPECIAL | Provider fallback/repair events, PII review outcomes, learner-reported issues | 100% (capped per event type) |

Stratum assignment is recorded per sampled unit with its reason; strata are versioned
with the sampler rule.

## 6. Evidence required per sampled unit

Feedback record (full payload + schema version `structured-feedback-v0.7.1`),
submission id, analysis run id, diagnosis record (gate/priority versions v0.6.1),
evidence quote ids, configuration version, prompt version, provider execution metadata
(provider id, model, finish reason, fallback/repair flags), learner_exposure,
sampling reason/stratum, sampler version, guideline version, PII review status for the
submission. Missing evidence makes the unit `not_auditable` (recorded, never inferred).

## 7. Human-review fields

Reuse the existing research review contracts (`app/research/schemas.py`):
`reviewer_id`, `decision` (correct / partially_correct / incorrect / uncertain /
not_reviewed / not_applicable), `confidence`, `reason_code`, `comment`,
`guideline_version` (`human-review-v0.1` baseline), `target_type=FEEDBACK`,
`source_system_result_snapshot` (frozen copy of the audited record).

## 8. Failure categories (closed vocabulary)

| Category | Meaning |
| --- | --- |
| `evidence_not_grounded` | Quote/evidence does not support the statement |
| `unsupported_claim` | Statement exceeds its evidence class (07 policy) |
| `claim_template_violation` | Prohibited vocabulary or non-template claim (07 §4) |
| `fabricated_evidence` | Invented quote/statistic/citation |
| `attribution_error` | Feedback→outcome or causal attribution |
| `unavailability_mishandled` | Missing/insufficient evidence presented as a finding |
| `leakage_or_domain_violation` | Cross-domain mixing or partition leakage (10) |
| `pii_exposure` | Unredacted PII in output |
| `provenance_missing` | Required version/evidence id absent |
| `other` | Anything else, with free-text detail |

Each audit result may carry multiple categories; `no_failure` is an explicit outcome.

## 9. Version provenance

Every audit sample and result records: audit-sampling policy version
(`feedback-audit-sampling-policy-v0.1.0`), sampler rule (`audit-sampler-v0.1.0`),
guideline version, feedback schema version, and the full pipeline version chain of the
sampled unit (section 6). Audit results are append-only with supersede semantics
(reuse `HumanReviewStatus`).

## 10. Isolation and future operation

- The sampler is deterministic, read-only, and isolated (department-owned module with
  tests; no production Feedback/Corpus code is touched).
- Operation (human review workflows, reviewer pool, dashboard) is deferred to Horizon 2
  (ARCH-12:29) and requires the Researcher decision on rate/criteria/pool.
- Audit outcomes feed policy amendments (02 §5) and the validated-measurement gate
  (ARCH-08:27-34); they never become learner-outcome measures.

## 11. Machine artifact and harness

`policies/audit_sampling_policy.json` mirrors sections 2-8 and validates against
`policies/policy_schema.json` (WU11). A deterministic sampler function
(`select_sample`, hash-based, versioned) is implemented in the department-owned
validator package with tests (11_VERIFICATION.md).