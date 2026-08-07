# 08 — Feedback & Learner Intelligence

## 1. Mandate

Feedback & Learner Intelligence owns the shared feedback-selection shape (calibrate → gate → prioritize → suppress → honest states), the learner-evidence semantics, and the epistemic/evidence-status enforcement across analysis → diagnosis → feedback → practice → journey. It does not own domain content (dimension contents, exercise catalogs, prompts are domain-owned) and it never owns learner-outcome claims.

## 2. FeedbackPolicy contract (D-03)

Minimum interface: `policy_id`/version; gate rules; priority limit; evidence-eligibility rules; no-priority/insufficient-evidence semantics; claims constraints; optional domain pre-gate hooks (Domain A: source verification). Hosted on the existing configuration-version machinery (SHA-256, single-active, audit). The named-type implementation form is decided when the second policy instance (Domain A) is designed; L2 keeps the current implicit policy formalized as the default instance with zero behavior change.

## 3. Evidence-status vocabulary (shared)

`verified | candidate | insufficient | suppressed | not_applicable | unavailable | legacy | unresolved` — standardizes scattered statuses (evidence_relevance_status, selection_status, transfer/evaluation states). Vocabulary only; no new store; no forced relabeling of legacy states.

## 4. Epistemic-status taxonomy (D-09)

Four layers with downgrade-only display invariant: `observed_descriptive` (L0) → `gated_inference` (L1) → `recommendation` (L2) → `outcome_claim` (L3, reserved; only validated measurement models may write). Target design: additive typed status on persisted artifacts and API schemas; persistence form `Researcher decision required`; compute-at-boundary interim. This is the structural tripwire preventing corpus-grounded diagnosis or longitudinal patterns from being displayed as outcomes.

## 5. Learner evidence families (Goal section 21)

See `04_DATA_AND_INTELLIGENCE_ARCHITECTURE.md` section 3: submission evidence; revision response; practice response; within-task observation; later-task observation; recurring pattern. Rules: cross-domain evidence merging prohibited; same-domain predicate required for comparability; `not_comparable` is honest; `HISTORY_LIMITATION` ("does not establish language-ability improvement, decline, mastery, or regression") extends to all longitudinal output; practice "completed" = activity completed, never mastery (frozen contract; any drift requires methodological review).

## 6. Feedback audit sampling (evaluation-of-evaluation)

Sample-based human review of feedback outputs against pre-registered criteria (evidence grounding, false positives, pedagogical framing). Lives separately from learner-outcome evaluation to prevent circularity. Design owned by Feedback & Learner Intelligence; operation with Research Evaluation & Data Governance; implementation deferred.

## 7. Validated-measurement gate (release gates for intelligent capabilities)

| Capability | Gate before release |
| --- | --- |
| Corpus-grounded diagnosis | construct-registry entries for involved signals + corpus provenance/fit + declared reference group + validated-measurement status for any normative claim |
| Longitudinal personalization | validated measurement model for the inferred state; comparability + data-sufficiency gating; outcome-layer write permission |
| Adaptive practice (difficulty/sequencing from inferred state) | validated measurement model; practice remains formative and provenance-tracked |
| Proficiency/mastery/learning-gain reporting | never in scope; requires full psychometric validation + external criteria |
| Automated citation generation | grounding verifier (citations only from provided sources, per-statement) or stay disabled |

## 8. Construct & measurement registry

Versioned configuration (not an engine): each metric/signal/trend declares construct, operationalization, text/task conditions, resource versions, validity-evidence status (`none | provisional | validated`), permitted vs forbidden interpretations. Unregistered constructs cannot produce normative output. Contents are domain-owned; mechanics shared.

## 9. Risks owned here

Circular evaluation (feedback metrics reused as outcome metrics) — mitigated by audit sampling and separate evaluation designs; feedback→outcome attribution — prohibited; epistemic-layer collapse — mitigated by the taxonomy; practice-completion semantic drift — frozen; cross-domain learner-history leakage — mitigated by same-domain predicates (department gate: domain-isolation tests).