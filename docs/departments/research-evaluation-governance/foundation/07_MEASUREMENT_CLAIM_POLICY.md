# 07 — Measurement Claim Policy

**Department:** Research Evaluation & Data Governance
**Policy id:** `measurement-claim-policy-v0.1.0`
**Ratification:** RD-POL-007 (2026-08-07)
**Status:** RATIFIED
**Supersedes:** none (first canonical version)

## 1. Purpose

This policy defines which statements the platform may and may not make from each
evidence class. It is the operational form of the core scientific principle
(observed evidence ≠ diagnostic inference ≠ feedback recommendation ≠ learning outcome;
corpus distance ≠ proficiency/mastery/learning gain), of D-07 (bands are descriptive),
D-09 (epistemic layers, downgrade-only), and of the frozen product wording contracts
(HISTORY_LIMITATION, D-031). It is a critical input to Stage 6 and to Feedback & Learner
Intelligence.

## 2. Evidence classes and permitted/prohibited statements

### 2.1 Observed feature (L0 `observed_descriptive`)

| Permitted | Prohibited |
| --- | --- |
| "This feature value is X (unit; feature_set_version; analysis_run/evidence id)." | "The learner has advanced proficiency." |
| "Word count is 342; connective density is 39.0 per 1000 tokens." | "The learner is a good/weak writer." |
| "The draft contains a local repetition of lemma X at sentence 3 (quote id)." | Any ability, quality, mastery, or level judgment about the learner. |

Rule: state the value, the unit, the version, and the evidence location; never the
meaning of the learner. Banned tokens apply (section 4).

### 2.2 Reference comparison (D-07; band/percentile)

| Permitted | Prohibited |
| --- | --- |
| "This feature value is near the upper part of this reference distribution (group `RG-...`, `reference-groups-v0.1.0`, `reference-distributions-v0.1.0`, n_effective=N, disclosure: none/fallback)." | "The learner has advanced proficiency." |
| "Value is at percentile p of the reference group (observed, descriptive)." | "The learner mastered this skill." |
| "The value moved from band A to band B between comparable submissions (observed change only)." | "The learner improved." / "The learner is above grade level." / "The learner outperforms peers." (direct learner-to-learner comparison is forbidden; ARCH-04 §3 cross-student comparison) / "Level/score/ability/mastery/gain/CEFR" language applied to the learner or to corpus-derived fields. |

Rule: any reference comparison must carry the resolved group, versions, effective N,
availability, and fallback disclosure (08 policy); any normative interpretation is
blocked by the validated-measurement gate (D-07; ARCH-14:68-75).

### 2.3 Diagnostic inference (L1 `gated_inference`)

| Permitted | Prohibited |
| --- | --- |
| "Signal X passed the Diagnostic Gate v0.6.1 with verified evidence at location L; priority score P (workflow ranking only)." | "The learner has a stable weakness in X." |
| "The signal was monitored, not selected (reason)." | "The learner is a repetitive writer." (trait attribution) |
| "This is a transparent prototype rule, not a validated ability judgment." | Any claim that a gated signal measures an ability or trait. |

Rule: gate version, evidence ids, and limitation wording are mandatory; strength
patterns never imply a stable learner trait (D-016).

### 2.4 Feedback recommendation (L2 `recommendation`)

| Permitted | Prohibited |
| --- | --- |
| "Priority: revise lexical repetition at sentence 3 (evidence ids; PRIO provenance)." | "Completing this practice means you mastered X." |
| "Practice activity completed (activity only)." | "This feedback shows your writing level." |
| "Evaluation unavailable; no claim is made." | Any outcome/ability claim attached to a recommendation. |

Rule: recommendations carry evidence and provenance; practice completion is activity
completion only (frozen contract; ARCH-08:43); evaluation-unavailable states are
first-class and never replaced by zero or by inference.

### 2.5 Longitudinal evidence

| Permitted | Prohibited |
| --- | --- |
| "Descriptive metric change: word_count 220 -> 260 across 2 comparable submissions (same task conditions)." | "The learner improved." |
| "Pattern label: persistent/recurring/recently_reduced (TraceStatus, descriptive)." | "The learner's ability grew." / "Regression in X." |
| HISTORY_LIMITATION verbatim: "This evidence is produced by prototype heuristic metrics and diagnoses; it does not establish language-ability improvement, decline, mastery, or regression." | Any causal feedback attribution or revision-quality score (D-021). |

Rule: HISTORY_LIMITATION (or its architecture extension, ARCH-07:32) must accompany all
longitudinal output; within-task and cross-task evidence stay separate (D-021); min 2
comparable independent tasks for cross-task assessment.

### 2.6 Learning outcome (L3 `outcome_claim` — reserved)

| Permitted | Prohibited |
| --- | --- |
| Nothing, until a validated measurement model exists and the outcome-layer gate is enabled (D-09; ARCH-08:27-34). | Proficiency/mastery/learning-gain reporting; CEFR assignment; rankings; any norm-referenced ability interpretation. Permanently out of scope without full psychometric validation + external criteria (ARCH-08:31-32). |

## 3. Downgrade-only invariant

Display may downgrade a statement to a weaker layer (e.g., show a gated inference as
observed evidence), never upgrade it (D-09; ARCH-14:86-95). A row's epistemic status is
set at write time; compute-at-boundary is the interim persistence form (open Researcher
decision).

## 4. Machine-checkable guardrails (WU11)

1. **Banned vocabulary (word-boundary):** `level`, `score`, `ability`, `mastery`,
   `gain`, `cefr` in corpus-derived field names and UI strings (ARCH-07:27; the
   `availability` substring exception is documented — word-boundary matching only).
   Exemptions (F2 resolution): the frozen product term **"priority score"** (field
   `priority_score`, `app/calibration/service.py`) is a documented product field name,
   not a corpus-derived field, and is exempt from the token check.
2. **Risky ability phrases:** the configuration contract list
   (`positive_finding_risky_ability_phrases`, `app/configuration/schemas.py:72-80`:
   `advanced proficiency`, `mastery`, `native-like`, `superior writing ability`, `high
   rhetorical awareness`, `excellent command of English`, `sophisticated writer`,
   `high-level writer`, `superior ability`, `strong linguistic control`) plus the
   documented policy additions `mastered`, `the learner improved`, `the learner
   declined` — prohibited in learner-directed statements.
3. **Explicit-prohibition-text exception (F1 resolution):** mandated disclaimer text
   such as `HISTORY_LIMITATION` ("does not establish language-ability improvement,
   decline, mastery, or regression") is validated with the prohibition-exemption path
   (`validate_disclaimer_text`), per I1's "except explicit prohibition text" exception.
4. **Permitted templates:** the exact statement patterns in section 2 are the canonical
   templates; WU11 provides `contains_prohibited_claim(text)`,
   `validate_disclaimer_text(text)`, and `validate_claim_template(text, evidence_class)`
   (required measurement anchors per class plus learner-quality assertion patterns) as
   department-owned utilities for Stage 6 reuse (not injected into Corpus/Feedback
   code). Known limitation (F12 resolution): negation is handled only through the
   explicit-prohibition path; ordinary claim text is not parsed for negation.
5. **Verification targets (read-only):** the policy JSON artifacts, governance
   documents' claim examples, and — for Stage-6 readiness — the corpus distribution
   artifact keys (`docs/corpus-intelligence/l2/data/*` field names) for banned tokens.
6. **Never-merge rule:** L2 diagnostic evidence and Academic research evidence never
   share a schema (D-06; ARCH-04 evidence-kind separation); claim templates are
   domain-neutral and apply to L2 only until an Academic instance is designed.

## 5. Boundaries to other policies

- Reference comparisons: 06 (eligibility) + 08 (admissibility).
- Corpus exposure: 03 (license) + 04 (protection).
- Learner-facing corpus content: disabled by default (D-08; 03 CU-05).
- Stage-6 evidence requirements: 08.
- Feedback audit sampling: 09 (claims are audited against these templates).

## 6. Change control

Changing a permitted template or adding an evidence class = major policy change with
methodological review; wording changes affecting learner-facing copy additionally
require Feedback & Learner Intelligence review. Banned-token list changes require
Architecture & Integration review (naming contract is a frozen shared contract).

## 7. Machine artifact

`policies/measurement_claim_policy.json` mirrors section 2 and validates against
`policies/policy_schema.json` (WU11).