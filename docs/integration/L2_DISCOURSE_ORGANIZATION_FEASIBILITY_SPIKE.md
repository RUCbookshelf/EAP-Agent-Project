# L2 Discourse-Organization Dimension Feasibility Spike

**Spike id:** `L2-DISCOURSE-ORGANIZATION-FEASIBILITY-SPIKE-001`  
**Goal:** L2-DOMAIN-TAXONOMY-CONTRACT (UD-02 / D-L2-03)  
**Date:** 2026-08-09  
**Owner:** L2 Writing Domain  
**Baseline:** `5aafe2728d7135212bd675a6975b44bcf99ee099`  
**Branch:** `dept/l2-writing`  
**Status:** SPIKE COMPLETE - **RECOMMENDATION: DEFER**  
**Spike only:** this document is NOT a Researcher sign-off and does NOT persist
the dimension as validated measurement. The UD-02 resolution remains with the
Researcher / Program Control.

---

## 1. Scope and method

The spike is a bounded, read-only investigation of the `discourse_organization`
candidate feedback dimension: construct definition, observable indicators,
analyzer/feature feasibility, scoring/classification semantics, reliability
expectations, evidence provenance, failure/unavailable behavior, and separation
from unsupported proficiency/learning-outcome claims.

Method: inspection of the current analysis pipeline
(`app/analysis/spacy_analyzer.py`, `app/analysis/connective_features.py`,
`app/analysis/lexical_features.py`, `app/analysis/coordinator.py`), the corpus
feature contract (`docs/corpus-intelligence/l2/02_FEATURE_CONTRACT.md`), the
feedback-dimension registry (`app/shared/feedback_dimension_registry.py`), the
architecture baseline (`docs/architecture/writing-intelligence-platform/06_L2_WRITING_DOMAIN.md`,
`14_ARCHITECTURE_DECISIONS.md`, `15_OPEN_QUESTIONS_AND_DEFERRED_DECISIONS.md`),
and the governance measurement-claim policy
(`docs/departments/research-evaluation-governance/foundation/07_MEASUREMENT_CLAIM_POLICY.md`).

Constraints honored: no raw SWECCL access, no Corpus Stage 6 (UD-04 open), no
product code changes, no new analyzers/features implemented, no domain pack
content created.

## 2. Construct definition

Proposed construct (as a feedback dimension): **discourse organization** = the
global structure of a written text - introduction/body/conclusion macro-structure,
paragraph role (topic sentence, supporting elaboration, concluding function),
argument or move progression, and the coherent sequencing of ideas across
paragraphs.

The construct is pedagogically meaningful in L2 writing research, but it must be
kept distinct from **local cohesion** (connective devices, referential ties),
which is already covered by the available `cohesion` dimension
(`app/shared/feedback_dimension_registry.py`). The dimension under spike is the
*organizational* layer, not the cohesive layer.

## 3. Observable indicators - candidate inventory

| candidate indicator | deterministic implementation exists today? | evidence location |
| --- | --- | --- |
| paragraph count / paragraph spans | YES (blank-line heuristic only; counts and spans, no roles) | `app/analysis/spacy_analyzer.py` `_paragraph_spans`; `app/analysis/lexical_features.py` paragraph spans |
| connective placement (sentence_id, paragraph_id, function category) | YES | `app/analysis/connective_features.py` (per-item offsets, category, paragraph/sentence ids) |
| repetition distribution across paragraphs | YES | `app/analysis/lexical_features.py` (paragraph_distribution, necessary_term) |
| sentence / T-unit / clause structure | YES | `app/analysis/spacy_analyzer.py`, `syntactic_features.py` |
| topic-sentence identification | NO | none in pipeline or feature contract |
| paragraph-role classification (intro/body/conclusion) | NO | none |
| macro-structure detection (introduction-body-conclusion) | NO | none |
| argument/move progression (claim -> evidence -> counterargument) | NO | none |
| thesis-statement identification | NO | none |

Every existing indicator above is a **cohesion or local-surface indicator**. No
indicator of global organizational structure exists anywhere in the current
pipeline.

## 4. Analyzer / feature feasibility

What exists (deterministic and versioned):

- `ConnectiveFeatureExtractor` over the pinned `connectives_v0_6_1.json` resource
  with resource SHA-256, word-boundary matching, per-item offsets, sentence and
  paragraph ids, function/expression classes (`app/analysis/connective_features.py`).
- Paragraph spans via a blank-line heuristic (`spacy_analyzer.py`), used for
  paragraph-relative placement only.
- Lexical repetition with paragraph distribution (`lexical_features.py`).
- Corpus feature set `corpus-features-v0.1.0` (14 features): text length,
  sentence length, T-unit proxy, connective density, POS shares
  (`docs/corpus-intelligence/l2/02_FEATURE_CONTRACT.md`). **None** of the 14
  features measures organization.

What does not exist:

- No topic-sentence, paragraph-role, macro-structure, or progression analyzer.
- The feature contract explicitly defers: "Lexical cohesion/discourse
  organization - requires D-L2-03 feasibility" (`02_FEATURE_CONTRACT.md`,
  Deferred features). D-L2-03 is this spike; until it resolves, no organization
  feature may enter the contract.
- D-L2-06 (organization-feature resource reuse) remains `Unclear`: no existing
  resource covers organization; the connectives resource is cohesion-only.
- No corpus reference data exists for organization (Stage 6 blocked by UD-04;
  no authorized corpus; `10_STAGE6_IMPLEMENTATION_HANDOFF.md`).

Conclusion: global organization indicators are **not implementable
deterministically from the current pipeline** without (a) new versioned feature
definitions and analyzers, (b) a feature-contract update, and (c) validation
basis. All three are out of scope for a spike and absent today.

## 5. Scoring / classification semantics

- No scoring semantics exist for organization. The feedback-dimension registry
  (`app/shared/feedback_dimension_registry.py`) contains **no**
  `discourse_organization` entry at all; the envelope in `06_L2_WRITING_DOMAIN.md`
  lists it only as a candidate.
- Any organization "score", band, or percentile is a measurement claim and
  requires the validated-measurement gate (D-07; `07_MEASUREMENT_CLAIM_POLICY.md`
  section 2.2). Band/percentile semantics are additionally blocked by the absence
  of an authorized corpus and reference groups (D-07; D-24; UD-04).
- Organization feedback in the diagnostic layer (a gated inference) would require
  deterministic signals, a calibration-gate entry (current gate
  `diagnostic-calibration-v0.6.1` has no organization signals), and evidence ids.
  None exist.

## 6. Reliability expectations

- No annotation basis, no reference groups, no effective-N eligibility, and no
  distribution artifacts exist for organization (D-07; reference-group policy;
  Stage 6 blocked). Reliability cannot be estimated, let alone established, at
  this time.
- The platform's reliability discipline for released artifacts (pinned models,
  versioned resources, deterministic extraction) exists as a *pattern* but has no
  organization artifact to apply it to.

## 7. Evidence provenance

- The local cohesion indicators that DO exist carry strong provenance: resource
  version + resource hash, per-item character offsets, sentence/paragraph ids,
  feature-set version (`connectives_v0_6_1`; `corpus-features-v0.1.0`; pinned
  spaCy 3.8.14 / en_core_web_sm 3.8.0, same extractor both sides - `02_FEATURE_CONTRACT.md`).
- However, provenance of an indicator does not validate a construct. There is no
  organization indicator, therefore no organization evidence provenance exists.
  Any future organization feature would need the same provenance discipline plus
  construct-validation evidence (annotations or an authorized reference).

## 8. Failure / unavailable behavior

- The machinery for honest unavailability exists and is frozen: dimension
  availability states (`available | insufficient_evidence | not_applicable`) and
  learner-exposure axis (`student | research_only`) in
  `app/shared/feedback_dimension_registry.py`; evaluation-unavailable and
  insufficient-evidence states in the L2 loop (`06_L2_WRITING_DOMAIN.md` section 2);
  explicit analyzer fallback with recorded reason (`app/analysis/coordinator.py`).
- If the dimension remains a candidate, the correct persisted state is
  `insufficient_evidence` / research-only (no student exposure), never replaced by
  zero or by inference (`07_MEASUREMENT_CLAIM_POLICY.md` section 2.4). No product
  change is required to hold this state; it is the current default.

## 9. Separation from proficiency / learning-outcome claims

Per `07_MEASUREMENT_CLAIM_POLICY.md`:

| statement class | permitted example | prohibited example |
| --- | --- | --- |
| observed feature | "connective density is 39.0 per 1000 tokens (feature_set_version; evidence id)." | "The learner is a good writer." |
| diagnostic inference | "Signal X passed Diagnostic Gate vX with verified evidence." | "The learner is a disorganized writer." (trait attribution) |
| feedback recommendation | "Revise the local repetition at sentence 3 (evidence ids)." | "This feedback shows your writing level." |
| learning outcome | nothing, until a validated measurement model exists | organization "level", "score", "mastery", "gain" applied to a learner |

An organization "quality" judgment ("well-organized", "weak organization") aimed
at a learner is a prohibited trait/quality claim absent validated measurement
(policy 2.1/2.3; HISTORY_LIMITATION applies to all longitudinal output). The
absence of an organization dimension means no new claim surface is created; the
four epistemic layers (D-09) and the ADR-07 practice/formative/research/protected
separation are preserved untouched.

## 10. Feasibility assessment

| spike criterion | verdict | basis |
| --- | --- | --- |
| construct definition | NOT defensible as measurement | pedagogically meaningful, but no measurement semantics defined; cohesion layer already covered by `cohesion` dimension |
| observable indicators | NOT defensible | only cohesion/local-surface indicators exist; organization indicators absent (Section 3) |
| analyzer/feature feasibility | NOT defensible for v1 | no organization analyzer or feature; feature contract defers it; D-L2-06 Unclear (Section 4) |
| scoring/classification semantics | NOT defensible | none exist; any score blocked by D-07 validated-measurement gate and corpus absence (Section 5) |
| reliability expectations | NOT defensible | no annotation or reference basis; Stage 6 blocked (Section 6) |
| evidence provenance | NOT defensible | provenance discipline exists, but no organization artifact carries it (Section 7) |
| failure/unavailable behavior | OK (non-blocking) | `insufficient_evidence` / research-only states exist and are the current default (Section 8) |
| separation from proficiency claims | OK (non-blocking) | measurement-claim policy governs statement classes (Section 9) |

## 11. Conclusion and recommendation

**Recommendation: DEFER the `discourse_organization` dimension.**

Evidence summary: the dimension is not defensible as deterministic measurement at
this time. The only existing deterministic indicators are cohesion indicators that
already belong to the available `cohesion` dimension; no organizational-structure
indicator, feature, analyzer, scoring semantics, reliability basis, or authorized
reference data exists, and the validated-measurement gate (D-07) plus the open
UD-04 corpus authorization block the prerequisites a defensible version would
need.

Consequences (all bounded):

- The dimension is NOT added to the v1 available envelope and is NOT persisted as
  validated measurement anywhere.
- Its state remains candidate / `insufficient_evidence`, research-only, consistent
  with `06_L2_WRITING_DOMAIN.md` and the dimension registry default.
- UD-02 option 3 (defer the dimension to a later pack) is the evidence-supported
  resolution for the Researcher / Program Control to confirm.
- Per the dispatch packet semantics, the spike concludes NOT defensible, so no
  Researcher decision packet is requested at this stage:
  `researcher_decision_required=false`.

Named preconditions for a future re-spike (Domain Pack v2 or later):

1. deterministic indicator definitions for organization (topic sentence,
   paragraph role, macro-structure) with a versioned feature contract;
2. construct-validation basis: validated annotations or an authorized reference
   corpus (Stage 6 licensing per UD-04, reference-group policy);
3. calibration-gate signals with thresholds and evidence ids (methodological
   review required for threshold content, D-33);
4. reliability study (min-N, consistency) before any learner-facing exposure;
5. Researcher sign-off on the evidence requirements.

Meanwhile, the `cohesion` dimension remains the available home for
connective/paragraph-level cohesion evidence; no learner-facing organization
claims are made.

## 12. Evidence references

- `docs/architecture/writing-intelligence-platform/06_L2_WRITING_DOMAIN.md` -
  gap 3 (discourse/organization evidence absent), envelope table, open decision
  D-L2-03 / D-L2-06.
- `docs/architecture/writing-intelligence-platform/15_OPEN_QUESTIONS_AND_DEFERRED_DECISIONS.md` -
  D-L2-03 status (`Researcher decision required`; feasibility `Unclear`).
- `docs/corpus-intelligence/l2/02_FEATURE_CONTRACT.md` - 14 frozen features, none
  organizational; deferred "Lexical cohesion/discourse organization".
- `app/shared/feedback_dimension_registry.py` - availability/learner-exposure
  axes; no `discourse_organization` entry; cohesion/lexical/sentence entries.
- `app/analysis/connective_features.py` - connective resource, hashes, offsets,
  paragraph/sentence ids.
- `app/analysis/spacy_analyzer.py` - sentence/paragraph spans, metrics.
- `app/analysis/lexical_features.py` - repetition paragraph distribution.
- `app/analysis/coordinator.py` - explicit fallback/unavailable behavior.
- `docs/departments/research-evaluation-governance/foundation/07_MEASUREMENT_CLAIM_POLICY.md`
  - permitted/prohibited statement classes; banned tokens.
- `docs/architecture/writing-intelligence-platform/14_ARCHITECTURE_DECISIONS.md` -
  D-07 (descriptive reference evidence; validated-measurement gate), D-09
  (epistemic layers), D-22, D-33 (threshold content governance).
- `program-control/USER_DECISION_BRIEF.json` - UD-02 (feasibility spike then
  Research sign-off), UD-04 (Stage-6 authorization open).
- `docs/integration/L2_PREREQUISITE_RESOLUTION.md` - prior D-L2-03 analysis
  (status `Unclear`, spike needed).

## 13. Honest-state declaration

This spike is a bounded evidence record, not a Researcher sign-off. UD-02 remains
an open Researcher decision; the recommendation above (DEFER, option 3) is
evidence-bounded and fully reversible. Nothing in this document adds a validated
measurement, changes product behavior, or unblocks Domain Pack v1 implementation.

*Produced by the L2 execution agent under Goal L2-DOMAIN-TAXONOMY-CONTRACT,
2026-08-09. Spike only; no dimension persisted as validated measurement.*
