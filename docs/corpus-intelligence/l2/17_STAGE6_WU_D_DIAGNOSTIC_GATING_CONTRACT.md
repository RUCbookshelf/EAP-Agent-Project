# 17 — Stage 6 WU-D: Diagnostic Gating Contract (CORPUS ↔ LEARNER)

**Goal:** `CORPUS-WUD-CONTRACT` — WU-D diagnostic gating contract with
Feedback & Learner Intelligence (D3-O2 + D-08 qualified).
**Owner:** CORPUS (Corpus & NLP)
**Worktree:** `A:\EAP Agent Project\worktrees\corpus` (branch `dept/corpus`)
**Baseline:** `09264abbd93cdc6b62b83cefd94b3b640319ac9b` (promoted master)
**Date:** 2026-08-09
**Contract status:** DESIGN / CONTRACT ONLY — no learner-facing UI
implementation, no product code changes, no persistence/API changes.

---

## 1. Purpose and boundary

WU-D (Stage-6 implementation handoff, `10_STAGE6_IMPLEMENTATION_HANDOFF.md`:
"diagnostic gating design (availability, min-N, fallback disclosure) with
Feedback & Learner Intelligence") defines the contract under which a
governed/versioned corpus aggregate MAY support diagnostic computation for
the LEARNER department, and the exposure class every artifact carries.

This document is a contract and design record. It does NOT implement the
diagnostic algorithm, does NOT change product code, does NOT create API
routes, persistence, or UI surfaces, and does NOT touch raw SWECCL.

Scope boundaries:

- The diagnostic *algorithm*, threshold selection, band method (quantile vs
  SD), and any inference procedure are NOT defined here — they belong to
  future LEARNER/L2 work under Research Evaluation review (D4; policy
  `stage6-evidence-admissibility-policy-v0.1.0` section 6; decision
  inventory A-24).
- CORPUS contributes the gating contract and governed aggregates; LEARNER
  owns feedback-policy application, learner evidence, and recommendation
  semantics (ARCH-14 D-37; architecture doc `08_FEEDBACK_LEARNER_INTELLIGENCE.md`).
- `displayable` exposure remains theoretical until a display policy exists;
  no learner-facing corpus content is authorized by this contract.

## 2. Normative inputs (binding sources)

| # | Source | Establishes |
| --- | --- | --- |
| N1 | `program-control/researcher-decisions/RD-D3-UD06-approved.json` (APPROVED 2026-08-09) | O1 research_only default; O2 diagnostic_only_aggregate gated on ALL of: permitted-use/licensing classification; NON-RECONSTRUCTIVE AGGREGATE; anonymization/privacy; provenance completeness; evidence-admissibility; D-08 display-policy compatibility; diagnostic-contract qualification. O1 default whenever qualification incomplete. |
| N2 | `program-control/researcher-decisions/RD-D08-approved.json` (APPROVED 2026-08-09) | Exposure classes research_only / diagnostic_only / displayable / hidden / unavailable; never-expose list (raw text, reconstructive derivatives, paths/handles, unsupported normative labels, proficiency/mastery classifications, learning-gain claims); uncertainty/availability exposed, never hidden behind false precision. |
| N3 | `docs/corpus-intelligence/l2/10_STAGE6_IMPLEMENTATION_HANDOFF.md` | WU-D definition; Stage-6 MUST NOT emit proficiency/mastery/learning-gain vocabulary, expose learner-facing corpus content (D-08), or use LLM for corpus statistics (I5). |
| N4 | `docs/corpus-licensing/CORPUS-LICENSING-REVIEW.md` + `.decision.json` (UD-04) | Artifact classes RAW SOURCE / NON-RECONSTRUCTIVE AGGREGATE / TEXTUAL-RECONSTRUCTIVE DERIVATIVE; 12-category permitted-use matrix; learner-facing display of any corpus content (incl. WU-D output) FAIL-CLOSED until D-08 display policy + licensing/anonymization gate + D3 model. |
| N5 | `docs/corpus-intelligence/l2/data/stage6_artifact_register.json` | Machine-checkable artifact-class register; rule: any future Stage-6 artifact not listed fails closed until classified and re-reviewed (this Goal classifies its own artifacts in `data/wu_d_diagnostic_gating_contract.json`). |
| N6 | `docs/departments/research-evaluation-governance/foundation/08_STAGE6_EVIDENCE_ADMISSIBILITY.md` (RD-POL-008) | ADMISSIBLE / LIMITED / UNAVAILABLE / INVALID; required admissibility record; precedence INVALID → UNAVAILABLE → LIMITED. |
| N7 | `docs/departments/research-evaluation-governance/foundation/07_MEASUREMENT_CLAIM_POLICY.md` (RD-POL-007) | Evidence classes L0–L3 with permitted/prohibited statements; downgrade-only invariant; banned vocabulary; HISTORY_LIMITATION; validated-measurement gate. |
| N8 | `docs/architecture/writing-intelligence-platform/14_ARCHITECTURE_DECISIONS.md` D-07/D-08/D-09 (canonical register) | Bands/percentiles are observed descriptive evidence (D-07); learner-facing corpus citations disabled by default (D-08); four-layer epistemic taxonomy with downgrade-only display (D-09). |
| N9 | `docs/corpus-intelligence/l2/07_CORPUS_INTELLIGENCE_QUERY_BOUNDARY.md` | Query boundary: every result `learner_exposure="research_only"`; no raw text; no unrestricted examples; explicit failure/unavailable states. |
| N10 | `docs/corpus-intelligence/l2/04_REFERENCE_GROUP_POLICY.md`, `06_REFERENCE_DISTRIBUTIONS.md` | min-N = 30 effective; fallback hierarchy with disclosure; 1,050 distribution records; missingness never imputed. |
| N11 | `docs/architecture/writing-intelligence-platform/08_FEEDBACK_LEARNER_INTELLIGENCE.md` (learner worktree) | LEARNER mandate; FeedbackPolicy contract (D-03); evidence-status vocabulary; epistemic taxonomy; validated-measurement gate for corpus-grounded diagnosis. |

## 3. Exposure classes (D-08 classes, D3-O2/O1 qualified)

Every corpus-derived artifact carries exactly one exposure class. The class
is computed at artifact creation and must be attached to the artifact and
its machine record; it is never inferred by the consumer.

| Class | Semantics (D-08 / D3) | Learner-facing? | Permitted epistemic layers | Transition |
| --- | --- | --- | --- | --- |
| `research_only` | Default state (O1); supports authorized internal research/evaluation only; never automatically learner-facing | No | L0 observed_descriptive; L1 gated_inference (internal research evaluation, with gate records) | Enter from `hidden` after licensing/permitted-use classification (G1); default whenever qualification incomplete |
| `diagnostic_only` | Qualified internal diagnostic computation (O2); not automatically displayable | No (internal pipeline; not a display class) | L0; L1 gated_inference with gate version + verified evidence ids + limitation wording | Enter from `research_only` ONLY when ALL O2 gates G1–G7 pass (section 6) |
| `displayable` | Explicit display-policy qualification; descriptive/non-normative language only | Yes — only after the D-08 display policy + licensing/anonymization gate | L0 only (canonical claim templates, N7); L1/L2/L3 NOT permitted on corpus-derived content | Enter from `diagnostic_only` ONLY via explicit display-policy qualification (Researcher decision + display policy + licensing/anonymization gate; D-08) |
| `hidden` | Internal pipeline only (intermediate computation states, pre-classification) | No | L0/L1 intermediate values never surfaced | Initial class for any newly produced aggregate; must resolve to `research_only`, `unavailable`, or a qualified class before use |
| `unavailable` | Fail closed; never fabricated, substituted, or silently widened (I4) | No | none (terminal) | Terminal for unqualified/unknown/version-mismatched/inadmissible artifacts; no widening |

Rules:

1. `research_only` is the default for every corpus-derived artifact (O1;
   N1, N9). Qualification incomplete ⇒ the artifact stays `research_only`
   (or `hidden` pre-classification) — never a higher class.
2. `diagnostic_only` is a *computation* class, not a display class
   (N2). It authorizes internal diagnostic computation by the named
   consumer (LEARNER foundation) under the qualification record; it does
   not authorize any learner-facing output.
3. `displayable` requires the full D-08 opt-in path: Researcher decision +
   display policy + licensing/anonymization gate (N4, N8). No artifact in
   this Goal carries `displayable`; the class is defined for the contract
   only.
4. Downgrade is always permitted (D-09 downgrade-only invariant; N7/N8);
   upgrade requires the corresponding gate evidence.
5. `unavailable` is terminal for that artifact version (N6): no widening,
   no substitution, no imputation.

## 4. Anonymization and privacy requirements

Before any governed aggregate may support diagnostic computation
(`diagnostic_only`) — and mandatory for any future `displayable` use:

| # | Requirement | Basis |
| --- | --- | --- |
| P1 | Aggregate-only content: reference statistics/distributions over effective samples with min-N = 30 effective documents and complete-case N ≥ 30; never per-document text or per-learner records in artifacts | N10, L2-04/06; licensing category 4/5 |
| P2 | No raw SWECCL text, no excerpts, no examples, no paraphrases, no reconstructive derivatives of any kind in any artifact (including example indices) | N4 categories 6/7-text/9-text/10-text/11; N2 never-expose |
| P3 | No corpus paths or handles in artifacts or machine records (ADR-06 raw-path/raw-handle denial) | N4 E16; `program-control/qualified-adrs/ADR-06` |
| P4 | No PII propagation: corpus contains no learner IDs (WECCL limitation); artifacts must not add or carry identifiers that could re-identify corpus documents beyond registered document_ids used for provenance | C-06; N3; corpus-readiness handoff |
| P5 | Learner text never written into the corpus (I2); numeric per-document snapshots stay outside git under `PREPARED/`; no learner text retained in governed artifacts | ARCH-07 I2; N3 |
| P6 | No cross-domain leakage: L2 diagnostic evidence and Academic research evidence never merge; same-domain predicate required for any comparison; domain-scoped export default (D-19) | N11; decision inventory A-11/A-19 |
| P7 | Missingness and uncertainty are exposed, never hidden behind false precision (unavailable states first-class; missingness flags reported; never imputed) | N2 note; N6; N10 |
| P8 | Anonymization gate: before any `displayable` class, a documented anonymization/privacy review must pass (part of the D-08 licensing/anonymization gate, N4) | N4; N8 D-08 |
| P9 | Export discipline: internal descriptive reporting only; no external redistribution, no external API upload, no public release of any corpus-derived artifact | N4 categories 10/11 |

## 5. Evidence-admissibility mapping (four layers, never merged)

The frozen invariant (I6; ARCH-07:32; program invariants): observed evidence
≠ diagnostic inference ≠ feedback recommendation ≠ learning outcome. Corpus
distance is never proficiency, mastery, or learning gain (I1).

| Layer | Epistemic status | What it is | Admissible exposure classes | Permitted statement (canonical template) | Prohibited statement |
| --- | --- | --- | --- | --- | --- |
| L0 | `observed_descriptive` | Observed feature value; reference comparison (percentile/position within declared group) | `research_only`, `diagnostic_only`, `displayable` (displayable only with claim-template qualification) | "This feature value is X (unit; feature_set_version; evidence id)." / "This feature value is near the upper part of this reference distribution (group RG-..., versions, n_effective=N, disclosure)." | "The learner has advanced proficiency." / "The learner is a good/weak writer." (any ability/quality/level judgment; direct learner-to-learner comparison) |
| L1 | `gated_inference` | Diagnostic inference from verified evidence through a declared gate | `research_only`, `diagnostic_only` (internal computation); NOT automatically displayable | "Signal X passed the Diagnostic Gate v0.6.1 with verified evidence at L (priority score = workflow ranking only)." / "This is a transparent prototype rule, not a validated ability judgment." | "The learner has a stable weakness in X." (trait attribution); any claim that a gated signal measures an ability |
| L2 | `recommendation` | Feedback recommendation; practice activity | Not a corpus-derived layer — LEARNER-owned via FeedbackPolicy; corpus contract contributes evidence only | (LEARNER policy) "Priority: revise ... (evidence ids; provenance)." / "Practice activity completed (activity only)." | "Completing this practice means you mastered X." / any outcome/ability claim attached to a recommendation |
| L3 | `outcome_claim` | Learning outcome (reserved) | None — reserved; only validated measurement models may write, and the outcome-layer gate is not enabled | Nothing | Proficiency/mastery/learning-gain reporting; CEFR assignment; rankings; any norm-referenced ability interpretation (permanently out of scope without full psychometric validation + external criteria) |

Admissibility-status mapping (N6 section 3):

| Admissibility status | Meaning for the contract | Exposure consequence |
| --- | --- | --- |
| `ADMISSIBLE` | All record fields present/correct; versions match (I3); group ELIGIBLE; no validity flags; no fallback; reproducible under same feature contract; descriptive wording; research_only default | Eligible for `diagnostic_only` qualification (with all O2 gates) |
| `LIMITED` | Admissible with validity flags, fragile group, or fallback disclosure attached | Usable descriptively with disclosure and limitation attached to the artifact; `diagnostic_only` only with the limitation carried into the computation record; never presented without the disclosure |
| `UNAVAILABLE` | Terminal record-level failure (unknown/version mismatch, N < 30, missing record, fallback-analyzer, license-restricted) | Maps to exposure class `unavailable`; no widening, no substitution |
| `INVALID` | Prohibited use (normative wording, cross-version comparison, 270-block circular use, score fields, learner-facing exposure without D-08 gate, silent defaults, imputed missingness, missing fallback disclosure) | Never usable; artifact must not enter any diagnostic computation |

Precedence (N6 F14): INVALID evaluated first, then UNAVAILABLE, then LIMITED.

## 6. Diagnostic-contract qualification criteria (O2 gates)

A governed aggregate MAY support diagnostic computation (`diagnostic_only`)
only when ALL of the following gates hold. Each gate requires a persisted,
evidence-backed record; an absent record is a failed gate (fail closed).

| Gate | Criterion | Evidence required |
| --- | --- | --- |
| G0 | Named consumer + authorization: the consuming capability (LEARNER foundation) is declared and the Goal's authorization scope covers the diagnostic use | Goal packet/authorization record; named consumer in the contract record |
| G1 | Permitted-use/licensing classification: artifact class is NON-RECONSTRUCTIVE AGGREGATE; use category permitted (CU-01/CU-02/CU-03 scope; internal research pipeline, `research_only` exposure) | Licensing review matrix classification + decision (N4) |
| G2 | NON-RECONSTRUCTIVE AGGREGATE: artifact contains statistics/distributions/numeric snapshots only; no text, no excerpts, no reconstructive derivative | Artifact-class register entry (N5) + machine check |
| G3 | Anonymization/privacy: section 4 requirements P1–P9 satisfied for the artifact and its consumers | Privacy review record / P-requirements checklist attached to the artifact |
| G4 | Provenance completeness: 7-field provenance (source package + manifest hash, FeatureSetVersion, ReferenceGroupVersion, DistributionVersion, processing/algorithm versions, effective N, availability) | Admissibility record (N6 section 2) |
| G5 | Evidence-admissibility: record status ADMISSIBLE or LIMITED-with-disclosure; never UNAVAILABLE/INVALID | `assess_admissibility(record)` result (N6 section 5) |
| G6 | D-08 display-policy compatibility: exposure class assigned per section 3; all wording follows canonical claim templates (N7 section 2); no normative labels; banned vocabulary absent; uncertainty exposed | Claim-template validation + banned-token check on artifact fields/strings |
| G7 | Diagnostic-contract qualification: construct-registry entries exist for every involved signal; declared reference group recorded; validated-measurement status recorded for any normative interpretation (L1 and above); FeedbackPolicy compatibility declared with LEARNER (evidence-eligibility, gate rules, no-priority semantics, claims constraints) | Construct registry entries; declared-group record; validated-measurement status; LEARNER FeedbackPolicy declaration (N11) |

Rules:

1. O2 (`diagnostic_only`) progresses ONLY when G1–G7 ALL pass (N1). Any
   failed or missing gate ⇒ the aggregate remains `research_only` (O1
   default).
2. `displayable` additionally requires the D-08 display-policy
   qualification (section 3 rule 3) — no display in this Goal.
3. Gate records are versioned with the artifact; a later artifact version
   re-qualifies from scratch (no inherited qualification).

## 7. Fail-closed rules

| # | Rule |
| --- | --- |
| F1 | Default exposure is `research_only` (O1); higher classes require completed gates. |
| F2 | Qualification incomplete, missing, or stale ⇒ O1; never inferred. |
| F3 | Unknown artifact, unknown corpus/feature/group, wrong manifest hash, corrupt resource ⇒ `unavailable` (never fabricated or substituted). |
| F4 | FeatureSetVersion mismatch between student side and corpus side ⇒ comparison UNAVAILABLE, never "best-effort comparable" (I3). |
| F5 | Fallback group resolution always disclosed (requested vs resolved group); silent widening forbidden (I4). |
| F6 | Fallback-analyzer-produced features and cross-version comparisons ⇒ INVALID (never usable). |
| F7 | Banned vocabulary (I1) or risky ability phrases in any corpus-derived field/string ⇒ INVALID (explicit prohibition text exempted per F1 resolution). |
| F8 | No LLM computation of corpus statistics (I5); deterministic local math only; LLM only fills verified claim slots. |
| F9 | No learner-facing corpus content of any kind without Researcher decision + display policy + licensing/anonymization gate (D-08; CU-05/CU-10). |
| F10 | No raw SWECCL path/handle through generic runtime, retrieval, Skill, MCP, UX, L2, ACAD, or LEARNER pathways (ADR-06). |
| F11 | No proficiency/mastery/ability/learning-gain/CEFR claims; no causal or transfer claims; no cross-learner comparison; no outcome claims without the validated-measurement gate. |
| F12 | No circular use of the 270 scored block; score fields never appear in artifacts (EP-06); partitions never split duplicate groups (EP-04/EP-05). |
| F13 | No external redistribution, export of text, or public release of any corpus-derived artifact (CU-04/CU-06/CU-08/CU-09/CU-12). |
| F14 | Learner evidence families never merged; L2 diagnostic evidence never merged with Academic research evidence; HISTORY_LIMITATION accompanies all longitudinal output. |
| F15 | Missingness never imputed; evaluation-unavailable states are first-class and never replaced by zero or inference. |

## 8. Downstream LEARNER foundation input requirements

What LEARNER needs to consume this contract (input envelope per
artifact/result; machine-checkable):

1. **Exposure-class envelope** — fields `exposure_class` (section 3) and
   `learner_exposure` (default `research_only`) on every artifact and
   result object; no consumer may assume a class the record does not state.
2. **Admissibility record** — the full N6 section-2 record with status
   (`ADMISSIBLE`/`LIMITED`/`UNAVAILABLE`/`INVALID`) and reasons; LEARNER
   must reject artifacts without a record.
3. **Epistemic-status fields** — L0–L3 taxonomy (N7/N8) with downgrade-only
   invariant; LEARNER stores/renders the stated layer, never an upgraded one.
4. **Canonical claim templates** — verified-slot wording per N7 section 2
   (deterministic, I5); LEARNER may only emit statements matching the
   templates for the artifact's layer.
5. **Construct registry + declared reference group** — construct-registry
   entries for involved signals, declared requested/resolved group,
   versions, effective N, disclosure; the validated-measurement gate
   remains LEARNER/GOV shared (N11 section 7).
6. **FeedbackPolicy compatibility declaration** — policy_id/version, gate
   rules, priority limits, evidence-eligibility rules,
   no-priority/insufficient-evidence semantics, claims constraints,
   optional domain pre-gate hooks (D-03; N11 section 2); the diagnostic
   computation must be expressible as evidence-eligible input to a
   FeedbackPolicy instance.
7. **Versioned consumption contract** — same FeatureSetVersion both sides
   (I3); ReferenceGroupVersion/DistributionVersion/comparison algorithm
   version recorded on every comparison; cross-version consumption is
   rejected.
8. **Provenance chain** — 7-field provenance (N6 section 2) so LEARNER can
   trace any diagnostic input to its governed artifact.
9. **N/min/missingness reporting** — n_effective, n_raw, complete-case N,
   missingness flags per artifact; LEARNER must not treat aggregates below
   the eligibility floor as supporting diagnostic computation.
10. **Failure/unavailable semantics** — explicit unavailable reasons; no
    silent defaults; `unavailable` never substituted by zero or by another
    group.

What LEARNER must NOT consume from CORPUS: raw corpus text, examples or
excerpts, reconstructive derivatives, corpus paths/handles, normative
labels, proficiency/mastery classifications, learning-gain claims,
cross-domain merged evidence, or any artifact without an exposure-class +
admissibility record. LEARNER remains responsible for its own feedback
policy application and never attributes feedback to outcomes (A-23).

## 9. Explicit exclusions

This contract explicitly excludes and keeps fail-closed:

1. **Textual/reconstructive derivatives** — excerpts, quotations, examples,
   paraphrases, near-verbatim reproductions, derived text files, example
   indices, and any artifact from which original wording can be recovered
   (N4 categories 6, 7-text, 9-text, 10-text, 11). No such artifact may
   gain diagnostic exposure.
2. **Proficiency/mastery/learning-gain claims** — no level/score/ability/
   mastery/gain/CEFR interpretation of corpus distance; no normative
   labels; no learner ranking; no outcome claims (L3 reserved; N1, N2,
   N7).
3. **Learner-facing UI implementation** — no UI, no learner-facing display,
   no UX work in this Goal (D-08; UX-owned later, gated).
4. **Product code changes** — no app code, tests, persistence, API routes,
   composition-root, or run.bat changes; contract/design only.
5. **Diagnostic algorithm / thresholds / band method** — LEARNER/L2 +
   Research Evaluation (D4 open; N6 section 6; A-24).
6. **LLM-computed corpus statistics** — deterministic local math only (I5).
7. **Raw corpus access** — unchanged: CORPUS-owned, read-only, Goal-scoped
   (I2; N4 category 12).

## 10. Verification (this Goal)

Contract-only verification performed:

| Check | Result | Evidence |
| --- | --- | --- |
| Git preflight (root/branch/HEAD/worktree) | PASS | worktree `A:/EAP Agent Project/worktrees/corpus`; branch `dept/corpus`; HEAD `09264abbd93cdc6b62b83cefd94b3b640319ac9b` = assigned baseline; pre-existing dirty/untracked files preserved |
| Normative inputs read (N1–N11) | PASS | RD-D3-UD06, RD-D08, Stage-6 handoff, licensing review + decision, artifact register, admissibility + claim policies, query boundary, reference-group policy, LEARNER architecture doc — read verbatim |
| Exposure classes present (5/5) | PASS | section 3; mirrored in machine artifact |
| O2 qualification gates present (G0–G7) | PASS | section 6; mirrored in machine artifact |
| Fail-closed rules present (F1–F15) | PASS | section 7; mirrored in machine artifact |
| Evidence-admissibility mapping (4 layers × statuses) | PASS | section 5; mirrored in machine artifact |
| LEARNER input requirements present (10 items) | PASS | section 8; mirrored in machine artifact |
| Explicit exclusions present (7 items) | PASS | section 9; mirrored in machine artifact |
| Machine artifact valid JSON | PASS | parsed via PowerShell `ConvertFrom-Json` (see `CORPUS-WUD-CONTRACT-20260809.md`) |
| Artifact-class register for this Goal (NON-RECONSTRUCTIVE AGGREGATE only) | PASS | `data/wu_d_diagnostic_gating_contract.json` `artifact_classification`; no TEXTUAL class |
| Banned-vocabulary scan of new artifacts | PASS | prohibited vocabulary appears only as explicit prohibition/exclusion text (F1-exempt documentation context), matching N7 convention |
| Write boundary | PASS | only new files under `docs/` in the authorized worktree; no commit/push/PR |

No code tests were run: this Goal is contract/design only (no product code
was touched).

## 11. Artifacts

- This contract: `docs/corpus-intelligence/l2/17_STAGE6_WU_D_DIAGNOSTIC_GATING_CONTRACT.md`
- Machine-readable contract: `docs/corpus-intelligence/l2/data/wu_d_diagnostic_gating_contract.json`
- Goal handoff report: `docs/integration/CORPUS-WUD-CONTRACT-20260809.md`
- Machine handoff: `docs/integration/CORPUS-WUD-CONTRACT-20260809.handoff.json`

## 12. Status, dependencies, and uncertainty

- **Status:** DEPARTMENT GREEN for the contract itself. WU-D *diagnostic
  computation* remains gated on LEARNER-side consumption (LEARNER is WAIT),
  D-08 display-policy opt-in (none exists), and remaining Researcher
  decisions (D4 band method + normative min-N justification, D8 feature-set
  scope, D12 UI exposure, final corpus exclusion/duplicate policy
  ratification, CLAWS4 mapping).
- `displayable` is defined but intentionally unpopulated: no display policy
  exists, and learner-facing corpus content is FAIL-CLOSED (N4, N8).
- This contract does not authorize any learner-facing exposure; it is the
  design record that future authorized work must satisfy.
