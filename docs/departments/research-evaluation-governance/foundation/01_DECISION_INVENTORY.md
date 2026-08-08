# 01 — Research & Methodological Decision Inventory

**Department:** Research Evaluation & Data Governance
**Package:** research-governance-foundation-v0.1.0
**Date:** 2026-08-07
**Status:** WU1 GREEN — ownership and status explicit for every inventoried decision.

## 1. Purpose and method

This inventory records every current research/methodological decision embedded in the
Writing Intelligence Platform baseline (architecture freeze, Corpus Readiness, Corpus
Stage 5, existing research services, CALF/eligibility logic, calibration/history
services, configuration, and tests). Each item is classified by ownership class and
carries the exact evidence location. Classification is explicit and conservative:
where a source is silent, the item is marked `RESEARCH DECISION REQUIRED` or
`DEFERRED`; nothing is repaired by inference.

### Classification legend

| Class | Meaning |
| --- | --- |
| `FROZEN ARCHITECTURE` | Binding architecture/contract decision (canonical register D-01..D-37, invariants I1-I6, charters, frozen product contracts). Change requires the shared-contract process (Architecture & Integration). |
| `DEPARTMENT POLICY` | Research-governance policy owned by Research Evaluation & Data Governance. Some pre-existing constraints are canonicalized here; the rest are created by WU2-WU10 of this foundation. |
| `TEMPORARY ENGINEERING DECISION` | Implementation choice made without research authority; reviewable; must be ratified, revised, or flagged before it becomes policy. |
| `RESEARCH DECISION REQUIRED` | Open decision with a named human/researcher owner; must not be resolved by engineering. |
| `DEFERRED` | Explicitly deferred; not resolved in this goal. |

### Source naming

- `ARCH-07` = `docs/architecture/writing-intelligence-platform/07_CORPUS_NLP_ARCHITECTURE.md`
- `ARCH-14` = `docs/architecture/writing-intelligence-platform/14_ARCHITECTURE_DECISIONS.md`
- `ARCH-04/08/10/12/15` = the corresponding architecture documents.
- `L2-0N` = `docs/corpus-intelligence/l2/0N_*.md`; `RD-0N` = `docs/corpus-readiness/sweccl2/0N_*.md`.
- Code paths are relative to the repository root.

## 2. Architecture-level research governance (frozen or open)

| ID | Decision / rule | Evidence | Class | Disposition |
| --- | --- | --- | --- | --- |
| A-01 | I1 — corpus distance is never proficiency; banned tokens `level/score/ability/mastery/gain/CEFR`; naming `reference_band/percentile_rank/distance_metric` | ARCH-07:27 | FROZEN ARCHITECTURE | Binding; WU7 + WU11 enforce machine-checkable banned-vocabulary guardrails. |
| A-02 | I2 — corpus is read-only reference data; learner text never written into corpus | ARCH-07:28 | FROZEN ARCHITECTURE | Binding; no Corpus mutation by any department. |
| A-03 | I3 — same feature contract both sides; version mismatch ⇒ comparison unavailable | ARCH-07:29 | FROZEN ARCHITECTURE | Binding; WU8 admissibility requires FeatureSetVersion equality. |
| A-04 | I4 — explicit unavailable states; silent group widening forbidden | ARCH-07:30 | FROZEN ARCHITECTURE | Binding; WU6 eligibility + WU8 admissibility operationalize. |
| A-05 | I5 — deterministic math; LLM only wording in verified slots | ARCH-07:31 | FROZEN ARCHITECTURE | Binding; no LLM-generated corpus statistics ever. |
| A-06 | I6 — observed evidence ≠ diagnostic inference ≠ feedback recommendation ≠ learning outcome; band movement observed only | ARCH-07:32 | FROZEN ARCHITECTURE | Binding; WU7 claim policy is the operational form. |
| A-07 | Prohibited: proficiency/mastery/CEFR/learning-gain projection; causal/transfer claims; LLM-invented quotes; cross-version or fallback-analyzer comparisons; fuzzy widening; global per-metric distributions; outcome claims without validated-measurement gate; validating a measure against the corpus that generated its norm (circularity) | ARCH-07:45 | FROZEN ARCHITECTURE | Binding; WU4/WU7/WU10 operationalize; circularity rule is the basis of 270-block protection. |
| A-08 | D-07 — bands/percentiles are observed, descriptive reference evidence; normative interpretation blocked by validated-measurement gate | ARCH-14:68-75 | FROZEN ARCHITECTURE | Ratified as binding; WU6/WU7/WU8 apply. |
| A-09 | D-08 — learner-facing corpus citations disabled by default; research surfaces first; any learner exposure requires Researcher decision + display policy + licensing/anonymization gate | ARCH-14:77-84 | FROZEN ARCHITECTURE (default) + RESEARCH DECISION REQUIRED (any opt-in) | WU3/WU7 record the opt-in path; no learner-facing corpus content in this goal. |
| A-10 | D-09 — epistemic-status taxonomy L0 observed_descriptive → L1 gated_inference → L2 recommendation → L3 outcome_claim; downgrade-only display; persistence form Researcher decision required; compute-at-boundary interim | ARCH-14:86-95; ARCH-08:15-21 | FROZEN ARCHITECTURE (vocabulary) + RESEARCH DECISION REQUIRED (persistence form) | WU7 claim policy aligns statements to layers; persistence form stays open. |
| A-11 | D-19 — exports domain-scoped by default; cross-domain exports are a future Researcher decision | ARCH-14:176-183; ARCH-04:18,91 | FROZEN ARCHITECTURE | Binding; WU10 leakage policy includes export scoping; code enforcement is an integration dependency (no domain column until migration 14). |
| A-12 | D-24 — S-CIC frozen scope = corpus boundary contract + resource-pack descriptor; reference groups/distributions/comparison are deferred units gated on authorized corpus + named consumer + licensing + D-07 min-N/coverage rules | ARCH-14:216-220 | FROZEN ARCHITECTURE | Stage-5 implemented registration + query boundary within this scope; WU6/WU8 keep eligibility rules department-owned, not Corpus feature code. |
| A-13 | D-25 — corpus distribution/band content consumed through CALF `resource_requirement`; one band-provenance record per normative output | ARCH-14:221-226 | FROZEN ARCHITECTURE | WU8 admissibility includes DistributionVersion + provenance; WU2 versioning aligns. |
| A-14 | D-31 — domain-isolation invariants (5 named contract tests) | ARCH-14:249-256 | FROZEN ARCHITECTURE | WU10 leakage policy incorporates; tests owned by Shared Core at implementation time. |
| A-15 | D-33 — threshold/eligibility CONTENT is domain-pack content requiring methodological review; calibration machinery shared | ARCH-14:257-263 | FROZEN ARCHITECTURE | min-N=30 and calibration thresholds fall under this rule; this department is the methodological-review owner. |
| A-16 | D-36 — export-time validation rejects/quarantines unknown domain values until migration-14 CHECK | ARCH-14:269-272; ARCH-10:152 | FROZEN ARCHITECTURE | Department-owned duty; not implemented (no domain column yet) ⇒ integration dependency for Shared Core Horizon 1 + this department. |
| A-17 | D-37/RT-15 — corpus mechanisms + feature contract = Corpus & NLP; admissible features, reference-group selection, wording = domain departments; availability computation shared with Feedback & Learner Intelligence | ARCH-14:273+; ARCH-07 amendment | FROZEN ARCHITECTURE | Eligibility *policy* (min-N, availability, coverage) = this department; group *selection* = domain profiles; kept separate. |
| A-18 | Charter §7 — Research Evaluation owns construct & measurement registry mechanics, corpus provenance/fit + licensing policy, reference-group policy, feedback audit operation, dataset splitting, PII/review gates, domain-scoped exports, genre taxonomy authority, methodological review | ARCH-10:127-152 | FROZEN ARCHITECTURE | This foundation is the first canonical implementation of these owned concepts. |
| A-19 | Learner evidence families never merged; no mastery/proficiency/learning-gain score without a separately validated measurement model | ARCH-04:31-39 | FROZEN ARCHITECTURE | WU7 claim policy bounds each family. |
| A-20 | Corpus pipeline P1-P13: P1 registration incl. license (with Research Evaluation); P2 min-N/coverage eligibility; P9 deterministic comparison only; P13 observed band movement only | ARCH-04:41-89 | FROZEN ARCHITECTURE | WU6/WU8/WU10 operationalize P2/P9/P13. |
| A-21 | Feedback audit sampling = evaluation-of-evaluation, separate from learner-outcome evaluation; design = Feedback & Learner Intelligence; operation = Research Evaluation; implementation deferred | ARCH-08:23-25 | FROZEN ARCHITECTURE (design split) | WU9 creates the department-owned sampling foundation for future operation. |
| A-22 | Validated-measurement gate: corpus-grounded diagnosis / longitudinal personalization / adaptive practice gated; proficiency/mastery/learning-gain reporting never in scope | ARCH-08:27-34 | FROZEN ARCHITECTURE | WU7/WU8 enforce claim bounds; gate mechanics shared with Feedback dept. |
| A-23 | Risks owned by Feedback dept: circular evaluation (mitigated by audit sampling + separate evaluation designs); feedback→outcome attribution prohibited; epistemic-layer collapse; practice-completion semantic drift frozen; cross-domain history leakage | ARCH-08:43 | FROZEN ARCHITECTURE | WU4 (circularity), WU9 (audit), WU10 (leakage) build on these. |
| A-24 | Corpus-grounded diagnosis blocked until authorized corpus + band method + construct registry entries + display policy (D1/D4/D8/D12 + G gates); Research Evaluation policies are a Horizon-2 prerequisite | ARCH-12:22,45,54 | FROZEN ARCHITECTURE | WU8 admissibility rules are the Stage-6 gate; no Stage-6 implementation in this goal. |
| A-25 | Open questions D1 corpus authorization; D3 licensing model; D4 band method + min-N; D5 task taxonomy; D6 proficiency-annotated metadata; D8 feature-set scope; D9 embeddings (NR); D10 comparison persistence (Unclear); D11 frequency-resource authorization; D12 UI exposure; genre taxonomy authority; reference-group policy; feedback audit sampling design; validity-evidence storage | ARCH-15:40-64 | RESEARCH DECISION REQUIRED / DEFERRED | Tracked in this inventory and in 02 policy versioning; none resolved silently. |

## 3. Product-level measurement and validity decisions (existing verified system)

| ID | Decision / rule | Evidence | Class | Disposition |
| --- | --- | --- | --- | --- |
| B-01 | Diagnostic Gate + priority thresholds: priority threshold 0.52; repetition count 4 / density 0.025; prompt-term penalty 1.0; necessary-term penalty 0.7; max selected priorities 2; exercise maxima 3/2/1; gate/calibration/priority versions v0.6.1; "transparent prototype rules, not validated educational or ability judgments" | `app/configuration/schemas.py:36-47`; `app/calibration/service.py:16-18,80,117`; DECISION_LOG D013 | TEMPORARY ENGINEERING DECISION (versioned config; methodological review required per D-33) | Ratified as prototype defaults only; any threshold change = domain-pack content + methodological review by this department (WU2 records the rule). |
| B-02 | Conservative task-aware sufficiency: representative strategy `final_or_latest`; 2 pairwise / 3 direction / 5 adequate tasks; transparent working assumptions without educational or measurement validation | DECISION_LOG D015; `app/configuration/schemas.py:57-63` | TEMPORARY ENGINEERING DECISION | Ratified as prototype defaults; normative trend claims require validated measurement (WU7). |
| B-03 | Current Gate is authoritative; history cannot reactivate suppressed signals; zero targets valid; strength patterns never imply stable learner trait | DECISION_LOG D016 | FROZEN ARCHITECTURE (frozen product contract) | Binding; WU7 keeps claim bounds. |
| B-04 | Revision-response claims conservative: observed change only, never mastery/learning/causation/transfer; accuracy unavailability never replaced by zero | DECISION_LOG D031 | FROZEN ARCHITECTURE (frozen product contract) | Binding; WU7 generalizes to all evidence classes. |
| B-05 | Backend-owned longitudinal facts; within-task vs cross-task evidence separated (revision group = one independent task; min 2 comparable independent tasks for cross-task assessment); provider status is an execution record; CALF statuses separate from availability; candidate syntax never becomes formal measures automatically; actual duration only for output rate; CALF is research evidence not a score | DECISION_LOG D020-D027; `app/calf/measurement.py:44-52` | FROZEN ARCHITECTURE (frozen product contracts) | Binding; WU7 evidence-class boundaries reuse these. |
| B-06 | `HISTORY_LIMITATION` extends to all longitudinal output ("does not establish language-ability improvement, decline, mastery, or regression") | `app/learner/history.py:15`; ARCH-04 §3 | FROZEN ARCHITECTURE | Binding; WU7 includes it verbatim in longitudinal-evidence bounds. |
| B-07 | Comparability rule `comparability-v0.3.0`: student_id/genre/draft_stage/timed/time_limit/tool_use/prompt equality; draft_stage-only mismatch ⇒ partially_comparable | `app/configuration/schemas.py:29`; `app/learner/history.py:90-110` | TEMPORARY ENGINEERING DECISION (rule version, unvalidated) | Ratified as prototype; comparability-threshold change requires methodological review; `task_type` stays metadata-only until legacy mapping decision (D-22). |
| B-08 | CALF registry: constructs `VALIDATION_PENDING`/`UNAVAILABLE`/`PROTOTYPE`; measurement statuses incl. `RESEARCH_METRIC`, `DESCRIPTIVE_PROXY`, `AUTOMATIC_CANDIDATE`, `MANUAL_ANNOTATION_REQUIRED`, `UNAVAILABLE`; `ACTIVE_RESEARCH` requires formula/unit/min-data/fixtures/references/limitations; eligibility flags default False; `lexical_sophistication` UNAVAILABLE (no authorized frequency resource) | `app/calf/schemas.py`; `app/calf/registry.py:96-214` | FROZEN ARCHITECTURE (product baseline) + TEMPORARY ENGINEERING DECISION (status management) | Binding; this department owns construct-registry governance mechanics per charter; WU7 uses statuses in claim bounds. |
| B-09 | Research export schema `research-export-v0.1`; privacy modes internal/pseudonymized/minimal_anonymous; pseudonym `PNNNNNN` stable per batch; CSV formula-injection guard; manifest SHA-256; interpretation boundaries "prototype research data … not training-ready … human review is expert opinion, not ground truth" | `app/research/schemas.py:277-305`; `app/research/service.py:22-26,37-41,190-194` | FROZEN ARCHITECTURE (product baseline) | Ratified; domain-scoped default (D-19) not yet enforced in code ⇒ integration dependency. |
| B-10 | Dataset split prototype: student-level, seed 20260730, ratios 0.70/0.15/0.15, `floor_with_remainder_to_train`, "infrastructure only … not suitable for model training" | `app/research/schemas.py:263-286`; `app/research/service.py:248-268` | TEMPORARY ENGINEERING DECISION | Ratified as prototype tooling only; leakage constraints (WU10) define what future research partitions must satisfy; splitter is not a research partition authority. |
| B-11 | PII scanner regex/dictionary-based, explicitly "not claimed as complete or reliable"; review workflow CANDIDATE/CONFIRMED/REJECTED/REDACTED | `app/research/scanner.py:1,9-25`; `app/research/schemas.py` | TEMPORARY ENGINEERING DECISION (documented limitation) | Ratified with limitation; WU9 audit-sampling evidence requirements reference PII review. |
| B-12 | Diagnosis limitation wording: "transparent prototype rules…", "teacher review is required"; raw candidates require gate before feedback | `app/calibration/service.py:117`; `app/diagnosis/heuristic.py`; `app/diagnosis/nlp_heuristic.py` | FROZEN ARCHITECTURE (wording contracts) | Binding; WU7 claim policy reuses the wording contract. |

## 4. Corpus Readiness decisions (preparation phase)

| ID | Decision / rule | Evidence | Class | Disposition |
| --- | --- | --- | --- | --- |
| C-01 | License status `PARTIALLY_DOCUMENTED` (published book ISBN 978-7-5600-8015-4; copyright page; no explicit corpus-use license in manual); local preparation/analysis/descriptive reporting permitted; external distribution or learner-facing use REQUIRES_REVIEW | `docs/corpus-readiness/sweccl2/corpus_version.json`; RD-11:43-48; L2-01 | DEPARTMENT POLICY (canonicalized in WU3) | WU3 creates the full authorization-state model with per-state evidence. |
| C-02 | Quality findings: WARG2081 RAW/LEMMA all-NUL (high); extremely short text; variant-identical bytes; non-ASCII learner content preserved; SECCL transcriber notes flagged; candidate exclusions only (draft); final exclusion = Researcher review | RD-06; RD-11 | RESEARCH DECISION REQUIRED (final exclusion policy) | Stage-5 treats WARG2081 as unavailable (no substitution), consistent with candidate status; final exclusion stays open. |
| C-03 | Duplicates: 348 scope-level groups (raw 127/lemma 117/tagged 104), 240 unique documents touched; "must be reconciled before evaluation use"; no text deleted | RD-06; RD-08; RD-11:24 | RESEARCH DECISION REQUIRED (final handling) + TEMPORARY ENGINEERING DECISION (current deterministic fold) | WU5 evaluates the Stage-5 fold and ratifies per-purpose policy. |
| C-04 | Reference-group candidates: 42 (33 READY_FOR_VALIDATION, 7 PROMISING, 2 TOO_SPARSE ARG13/ARG19); conservative min-N 30 preparation criterion; "final policy is a Researcher decision" | RD-08 | RESEARCH DECISION REQUIRED (final policy) | WU6 reviews the Stage-5 approval of 75 groups and issues eligibility criteria. |
| C-05 | Partitioning constraints: never split duplicate-group members across dev/eval; never split the same prompt across dev/eval without prompt-matching design; protect the scored expository block as one unit; partitions reproducible from document_id + grouping keys and versioned; no final partitions created | RD-10:37-42 | DEPARTMENT POLICY (canonicalized in WU10) | WU10 formalizes as the evaluation-leakage policy. |
| C-06 | No learner IDs in WECCL: same-learner isolation cannot be guaranteed; duplicate detection is the only proxy | RD-10:22; RD-11:28 | DEPARTMENT POLICY (acknowledged limitation) | WU10 carries the unknown-learner-ID constraint. |
| C-07 | CLAWS4 legacy annotation historical; no CLAWS4↔spaCy comparison without an explicit mapping contract; mapping vs re-tagging = decision with Research Evaluation | RD-11:36; L2-02 | DEFERRED (feature-contract decision) | Integration dependency for Corpus & NLP + this department. |

## 5. Corpus Stage-5 decisions (proposed by Corpus & NLP, now under research governance)

Stage 5 was implemented by the Corpus & NLP department and its four research-governance
decisions (score linkage, duplicate policy, evaluation protection, min-N + fallback)
received a methodology review (`L2 evidence/methodology_review.md`) with outcome
`APPROVED_WITH_CONDITIONS` (both documentation conditions already applied to L2-03/L2-04).
The independent final review (`L2 evidence/independent_review_stage5.md`) concluded
`READY FOR STAGE 6` with 5 LOW findings (L1-L5, all Corpus-department documentation
follow-ups; none blocking). This foundation treats the Stage-5 *facts* as evidence and
the Stage-5 *choices* as proposals that must be explicitly ratified, revised, or
deferred by research governance — not blindly re-ratified.

| ID | Decision / rule | Evidence | Class | Disposition |
| --- | --- | --- | --- | --- |
| D-01 | Resource registration: package `sweccl2-weccl20-v0.1.0`, manifest hash `0d8940ff…59eb9`, 4,950 logical texts (raw 4,949 usable), immutable descriptor, verified load/failure paths | L2-01; L2-09 | FROZEN ARCHITECTURE-compliant implementation (Corpus-owned; retained) | Evidence for all downstream policies; registration itself is Corpus & NLP scope. |
| D-02 | FeatureSetVersion `corpus-features-v0.1.0`: 14 features, pinned spaCy `en_core_web_sm` 3.8.0 on RAW, single implementation for corpus and Student-compatible text | L2-02; L2-05 | TEMPORARY ENGINEERING DECISION (feature-set scope D8 open) | Ratified as the v0.1 engineering reference contract; scope of the feature set remains RESEARCH DECISION REQUIRED (D8). |
| D-03 | CLAWS4 decision `HYBRID-NONE-FOR-V0.1`: historical CLAWS4 preserved; v0.1 uses spaCy on RAW on both sides; no cross-tag comparison without mapping contract | L2-02 | TEMPORARY ENGINEERING DECISION | Deferred mapping (C-07); ratified for v0.1 comparability. |
| D-04 | Duplicate policy `effective_sample_excludes_non_canonical_duplicate_members`: canonical = lexicographically smallest document_id; document-level fold via `Path(member).stem` + last-wins (240 affected docs, 120 groups); effective membership for reference samples; physical counts and raw records untouched; never delete | L2-03:26-35; L2-10:49-51; `evidence/methodology_review.md` D2 | TEMPORARY ENGINEERING DECISION | WU5 reviews per purpose (descriptive statistics / reference distributions / evaluation / future model development) and ratifies or flags dependencies. |
| D-05 | Score linkage: exp.xls/exp.sav 270×8 identical columns; IDs WEXP#### unique; 270/270 set equality with EXP01 manifest; 0 missing/ambiguous; scores never enter distributions or learner-facing code | L2-03:9-24; `evidence/independent_review_stage5.md` §6 | DEPARTMENT POLICY (established evidence fact) | Ratified: linkage established for evaluation readiness only. |
| D-06 | Evaluation protection: 270 scored expository texts = protected block; no development use without Research Evaluation approval; duplicate-group members never split across dev/eval; no final partitions created | L2-03:40-41; L2-10:72-75 | DEPARTMENT POLICY (canonicalized in WU4) | WU4 issues the full protection policy incl. circularity prevention. |
| D-07 | min-N = 30 effective documents after duplicate policy; explicitly "NOT a normative/scientific sufficiency claim and remains reviewable by Research Evaluation"; feature-specific missingness flagged per distribution | L2-04:11-16 | TEMPORARY ENGINEERING DECISION | WU6 determines temporary-heuristic vs policy status with reasoning. |
| D-08 | 75 approved groups = 25 prompt-only + 35 prompt×timed + 2 genre + 2 timed + 2 major_type + 4 grade + 5 entry_year; ARG13/ARG19 standalone unavailable (indexed, not approved); any group with effective N < 30 unavailable | L2-04:18,24,29-30 | TEMPORARY ENGINEERING DECISION | WU6 issues eligible/limited/unavailable/requires-review criteria. |
| D-09 | Fallback hierarchy: prompt+timed → prompt → genre+timed → genre → UNAVAILABLE; genre derived from prompt prefix; requested/resolved group + fallback disclosure in every result; silent broadening impossible by construction | L2-04:34-37; L2-10:44-47 | TEMPORARY ENGINEERING DECISION | WU6 ratifies with disclosure contract (already satisfies I4). |
| D-10 | Reference distributions `reference-distributions-v0.1.0`: 1,050 records (75×14), availability=available, 100 validity-flag records (missing values, never imputed), full 7-field provenance per record, deterministic byte-identical rebuild (SHA-256 `900ee352…ce73d`) | L2-06; L2-08; L2-09 | TEMPORARY ENGINEERING DECISION (implementation) | Retained as v0.1 reference evidence; WU8 requires DistributionVersion + provenance for admissibility. |
| D-11 | Query boundary: `learner_exposure="research_only"` on every result; no raw corpus text; no unrestricted examples; license-restricted operations out of boundary | L2-07 | DEPARTMENT POLICY (enforcement point; D-08 implementation) | WU3/WU8 keep exposure rules; WU11 validates the artifacts, not the code. |
| D-12 | Honest unavailability: WARG2081 all 14 features unavailable with reason, no variant substitution; WARG0228 t_unit_proxy unavailable (no finite clause head) | L2-05; L2-09 | DEPARTMENT POLICY (I4 implementation) | Ratified; WU8 includes missingness in admissibility. |
| D-13 | Methodology review `APPROVED_WITH_CONDITIONS` (2 doc-wording conditions, applied) + independent review `READY FOR STAGE 6` (5 LOW findings L1-L5) | `evidence/methodology_review.md`; `evidence/independent_review_stage5.md` | Evidence record | L1-L5 are Corpus-department documentation follow-ups ⇒ integration dependency; no action by this department on Corpus files. |
| D-14 | Reproducibility: data artifacts byte-identical on rerun; version manifests carry build timestamps | L2-08; L2-09 | TEMPORARY ENGINEERING DECISION | Retained; WU8 provenance requirements build on it. |

## 6. Decisions embedded in tests

| ID | Decision / rule | Evidence | Class | Disposition |
| --- | --- | --- | --- | --- |
| E-01 | `tests/corpus/**` (36 tests) encode resource hash, feature contract, duplicate fold, min-N, fallback, unavailable states, determinism | L2-09 table; `tests/corpus/` | FROZEN (Corpus-owned tests; not modified) | Evidence for WU6/WU8; governance validators must agree with these contracts. |
| E-02 | `tests/test_research_v082.py`, `tests/test_calf_v08.py` encode export schema/interpretation boundaries and CALF statuses | `tests/` | FROZEN (existing suite) | Regression authority; WU11 additions must not conflict. |
| E-03 | Full non-live core suite 1237 passed / 8 skipped / 0 failed (v0.9.7-D closure) | RUN_VERIFICATION_V0.9.7_D.md | FROZEN (regression authority) | WU11 runs the full core and the new validator tests; must stay green. |

## 7. Special-attention cross-cut (goal section 5)

| Item | Current status | Owner class | Resolved by |
| --- | --- | --- | --- |
| min-N = 30 | Explicit policy with explicit "not normative" caveat; reviewable by Research Evaluation | TEMPORARY ENGINEERING DECISION → WU6 | 06_REFERENCE_GROUP_ELIGIBILITY_POLICY.md |
| Duplicate collapsing | Deterministic representative selection (lexicographically smallest); effective vs physical N distinguished; raw records untouched | TEMPORARY ENGINEERING DECISION → WU5 | 05_DUPLICATE_POLICY.md |
| Reference-group eligibility | 75 approved groups; ARG13/ARG19 unavailable; effective-N floor | TEMPORARY ENGINEERING DECISION → WU6 | 06_REFERENCE_GROUP_ELIGIBILITY_POLICY.md |
| Fallback hierarchy | prompt+timed → prompt → genre+timed → genre → UNAVAILABLE; disclosure required | TEMPORARY ENGINEERING DECISION → ratify WU6 | 06_REFERENCE_GROUP_ELIGIBILITY_POLICY.md |
| 270 scored expository protection | Protected block; no development use without approval; never split duplicates; no final partitions | DEPARTMENT POLICY → WU4 | 04_EVALUATION_PROTECTION_POLICY.md |
| License restrictions | PARTIALLY_DOCUMENTED; external use REQUIRES_REVIEW | DEPARTMENT POLICY → WU3 | 03_CORPUS_USE_AND_LICENSE_POLICY.md |
| Evaluation holdout rules | 511 holdout candidates (270+240+1); constraints from readiness phase | DEPARTMENT POLICY → WU10 | 10_EVALUATION_LEAKAGE_POLICY.md |
| Feature availability | Explicit unavailable states (I4); WARG2081/WARG0228; missingness flags; same-feature-contract rule | FROZEN ARCHITECTURE + DEPARTMENT POLICY → WU8 | 08_STAGE6_EVIDENCE_ADMISSIBILITY.md |
| Learner-facing exposure | Disabled by default (D-08); all query results research_only | FROZEN ARCHITECTURE + RESEARCH DECISION REQUIRED (any opt-in) | 03 + 07_MEASUREMENT_CLAIM_POLICY.md |

## 8. Inventory summary

Counted rows by class (A + B + C + D + E above):

| Class | Count |
| --- | --- |
| FROZEN ARCHITECTURE (binding, incl. frozen product contracts; rows A-01..A-24, B-03..B-09/B-12, D-01, E-01..E-03) | 35 |
| DEPARTMENT POLICY (existing constraints canonicalized in this foundation; C-01/C-05/C-06, D-05/D-06/D-11/D-12) | 7 |
| TEMPORARY ENGINEERING DECISION (requires ratification/revision in WU2-WU10; B-01/B-02/B-07/B-10/B-11, D-02/D-03/D-04/D-07/D-08/D-09/D-10/D-14) | 13 |
| RESEARCH DECISION REQUIRED (rows whose primary class is open; A-25, C-02/C-03/C-04) | 4 |
| DEFERRED (C-07) | 1 |
| Evidence record (D-13) | 1 |

Two additional rows carry a mixed class with a RESEARCH DECISION REQUIRED component:
A-09 (any learner-facing corpus opt-in) and A-10 (epistemic-status persistence form).

Carried-open Researcher decisions (not resolved by this goal): corpus authorization (D1),
licensing model (D3), band method + normative min-N justification (D4), task taxonomy (D5),
proficiency-annotated metadata use (D6), feature-set scope (D8), embeddings (D9), comparison
persistence (D10), frequency-resource authorization (D11), UI exposure (D12), genre taxonomy
authority, validity-evidence storage, audit-sampling rate/criteria/reviewer pool, final
corpus exclusion policy, final duplicate handling, CLAWS4 mapping vs re-tagging, epistemic
status persistence form, cross-domain exports, learner multi-domain profile views.

## 9. Traceability guarantee

Every count and number quoted in this inventory is directly traceable to the cited
evidence locations; where an independent review corrected a number (e.g., the
`reference_distributions.jsonl` hash), this inventory uses the corrected value and cites
the correction record (`evidence/independent_review_stage5.md`, coordinator closing note).
No Stage-5 fact was silently modified; no Corpus artifact was changed.
