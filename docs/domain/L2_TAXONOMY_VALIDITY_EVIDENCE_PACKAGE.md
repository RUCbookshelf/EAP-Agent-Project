# L2 Task-Type Taxonomy — Validity-Evidence Package (PROPOSAL)

**Package id:** `L2-TAXONOMY-VALIDITY-EVIDENCE-PACKAGE-001`
**Goal:** `L2-EVIDENCE-PREP`
**Date:** 2026-08-09
**Owner:** L2 Writing Domain
**Baseline:** `5aafe2728d7135212bd675a6975b44bcf99ee099`
**Branch / Worktree:** `dept/l2-writing` / `A:\EAP Agent Project\worktrees\l2-writing`
**Status:** EVIDENCE PACKAGE — **PROPOSAL ONLY**. This package does NOT approve the
taxonomy's validity and produces no validity claim. Research Evaluation + L2 review
the package; PROGRAM tracks the decision (D-22 lane). `discourse_organization`
remains excluded (UD-02 DEFER).
**Contract anchor:** `docs/domain/L2_TASK_TYPE_TAXONOMY_CONTRACT.md` Section 10
("Validity evidence for the taxonomy: required before ANY measurement use; none is
claimed or produced here").

---

## 1. Claim scope — what the taxonomy asks evidence to support

The taxonomy is **task-routing / task-semantics metadata ONLY** (contract Section 0):

* It labels tasks with a typed, versioned, deterministic semantic label.
* It is explicitly NOT a proficiency, mastery, ability, learning-gain, or
  measurement taxonomy; it assigns no level, score, quality, or ability.
* It participates in NO comparability predicate until the legacy-mapping decision
  (D-22) resolves, and any future comparability change requires the D-22
  behavior-diff test.

Consequence for the validation standard: the evidence program proposed here targets
**content coverage + classification reliability + honest unavailability** for
routing labels. It is deliberately NOT a psychometric validation program; no
measurement use is proposed, and Section 10's requirement (validity evidence before
ANY measurement use) remains unsatisfied and untouched by this package.

## 2. Inventory of existing validity evidence

### 2.1 Definitional / documentary evidence — EXISTS

| # | Evidence item | Location | What it supports | Limitation |
| --- | --- | --- | --- | --- |
| D1 | Five-type enumeration + routing semantics + two explicit states | Contract §1 | Type definitions; `legacy_unclassified` / `unclassified` semantics | Definitional only; no empirical backing |
| D2 | Opinion-vs-argumentative discriminator (mandated-structure table) | Contract §3 | Operational boundary between two adjacent types | Definitional; boundary rate unmeasured |
| D3 | Precedence chain for ambiguous prompts | Contract §4 | Ambiguity handling; `ambiguous_precedence_conflict` outcome | Definitional; conflict rate unmeasured |
| D4 | `general_eap` affirmative conditions (a/b/c) | Contract §7 | Fallback scope; never a garbage bucket | Definitional |
| D5 | Deterministic procedure + normalization discipline | Contract §2.1–2.2 | Procedural determinism spec (same discipline as frozen corpus features) | No implementation exists (Domain Pack v1 blocked) |
| D6 | Non-claims + boundaries checklist | Contract §0, §9 | Claim-scope definition | Negative evidence only |
| D7 | Enumeration decision provenance (UD-01) | `program-control/USER_DECISION_BRIEF.json` | Decision basis for the five types | A governance decision, not evidence |
| D8 | Evaluation-separation governance (ADR-07) | `program-control/qualified-adrs/ADR-07-evaluation-taxonomy.json` | Versioned taxonomy; no mastery semantics | Governance, not validity |
| D9 | Registry/versioning/comparability governance (D-04, D-22, D-26, D-29) | `docs/architecture/writing-intelligence-platform/14_ARCHITECTURE_DECISIONS.md` | Mechanism, version streams, comparability freeze | Governance, not validity |
| D10 | Canonical label pairs en/zh_CN + non-hierarchical display order | `docs/domain/D-L2-09_ZHCN_LABELS_DECISION.md` | Label consistency | Editorial |
| D11 | Discourse-organization feasibility spike (negative evidence) | `docs/integration/L2_DISCOURSE_ORGANIZATION_FEASIBILITY_SPIKE.md` | Confirms organization is NOT a v1 task-type/measurement item | Not a task-type validation |

### 2.2 Mechanism / verification evidence — EXISTS (but is NOT validity evidence for the taxonomy)

| # | Item | Location | What it actually supports |
| --- | --- | --- | --- |
| M1 | `TaskTypeRegistry` mechanism + `legacy_unclassified` sentinel | `app/shared/task_type_registry.py` | Mechanism readiness; sentinel availability |
| M2 | Domain-pack loader + namespace tests | `tests/shared/test_domain_packs.py` | Pack content loads under its namespace; H1 lists are empty |
| M3 | Locale parity tests (600/600; key-parity) | `tests/test_design_tokens_v094a.py`, `tests/test_v097d_design_system.py`, `tests/test_v095c_feature_extraction.py` | Label-parity machinery only |
| M4 | D-22 comparability freeze + D-30 zero-change gate | `14_ARCHITECTURE_DECISIONS.md` | Behavior-safety guarantees, not taxonomy validity |
| M5 | Persistence design (write-time provenance) | `docs/domain/D-L2-02_TASK_TYPE_PERSISTENCE_DECISION.md` | Where provenance would live; no evidence content |

### 2.3 Adjacent evidence — EXISTS but does NOT validate the five types

| # | Item | Location | Why it is NOT task-type validity evidence |
| --- | --- | --- | --- |
| A1 | Corpus annotation-quality checks (token-ratio stats, corrupt-variant counts, 4950 docs) | `docs/corpus-readiness/sweccl2/data/legacy_annotation_quality.json` | Corpus data-quality checks on SWECCL; no relation to the five task types |
| A2 | CALF measurement/band discipline | `docs/CALF_MEASUREMENT.md`, `docs/CALF_CONSTRUCT_REGISTRY.md` | Measurement discipline for dimension metrics; taxonomy is explicitly not measurement |
| A3 | Corpus feature contract (14 frozen features) | `docs/corpus-intelligence/l2/02_FEATURE_CONTRACT.md` | Features, not task types; organization deferred |
| A4 | Genre vocabulary inventory (3 options × 2 locales) | `locales/en.json`, `locales/zh_CN.json`, `app/ui/features/student/writing.py:233-236` | Legacy genre surface; feeds the D-22 mapping, not validity |

### 2.4 Empirical validity evidence — NONE

Standard validity classes, status per class (honest `NR` where not measured):

| Validity class | Status | Notes |
| --- | --- | --- |
| Content validity (expert review of definitions, trigger classes, precedence, coverage frame) | **NR** — no expert panel review exists | No signed disposition from any reviewer on mutual exclusivity / joint exhaustiveness |
| Classification reliability (inter-rater; human-vs-rule agreement) | **NR** — no rater study exists | No kappa/percent-agreement data of any kind |
| Coverage / representativeness (task-prompt universe vs the five types) | **NR** — no census exists | Real legacy prompt distribution unknown; no governed DB snapshot in the worktree |
| Boundary / ambiguity statistics (unclassified rate; reason-code distribution) | **NR** — not measured | Ambiguous-prompt rate and `ambiguous_precedence_conflict` rate unknown |
| Deterministic-procedure verification (rule implementation matches spec) | **NR** — no implementation exists | Domain Pack v1 (trigger dictionaries + procedure) is blocked |
| Construct / criterion-related evidence | **N/A** — out of scope by design | Taxonomy makes no measurement claim; criterion validation is a future, separately authorized program (contract §10, D-07) |
| Consequential evidence | **N/A** — out of scope by design | No measurement use; non-claims documented in contract §0/§9 |

## 3. Gap analysis

* **G1 — Content validity evidence absent.** Definitions and trigger classes exist
  (D1–D4) but no expert review recorded mutual exclusivity, joint exhaustiveness,
  or coverage of the intended task universe. Nothing can claim the five types
  "cover" L2 writing tasks.
* **G2 — Reliability evidence absent.** No inter-rater study; no human-vs-rule
  agreement; no adjudication protocol. Determinism of the *procedure* (by
  construction) is not the same as agreement between rule-appliers or with the
  rule spec.
* **G3 — Coverage unknown.** No census of real legacy prompts/genres; no governed
  snapshot available in the worktree. `legacy_unclassified` rate is unmeasured.
* **G4 — Boundary behavior unmeasured.** Opinion-vs-argumentative and precedence
  conflicts have definitions but no empirical ambiguity rate; the "no silent
  guess" guarantee (contract §4) is untested on real prompts.
* **G5 — No implementation to verify.** Trigger dictionaries and the deterministic
  procedure are Domain Pack v1 content; until authorized, the spec cannot be
  executed or tested.
* **G6 — Validation governance undefined.** No record names the evidence standard,
  sign-off owner, or re-validation trigger for taxonomy changes (bump rules exist
  in contract §7.2 but not an evidence re-check rule).

## 4. Proposed bounded validation plan (for Research/Program review)

**Purpose:** produce evidence sufficient for the taxonomy's stated use —
deterministic routing labels with honest unavailability. **Explicitly not** a
psychometric validation; measurement use remains blocked (contract §10, D-07).

### 4.1 Sources (bounded)

* S1 — **Governed snapshot of the real legacy `essays` table** (product DB) for
  census + D-22 behavior-diff snapshot. Requires an authorized snapshot procedure
  (named by Research Evaluation + PROGRAM; NOT raw SWECCL — corpus counts are not
  transferable to product legacy rows).
* S2 — **License-clean public/owned EAP task-prompt collections** (for coverage
  breadth outside the product DB).
* S3 — **Expert reviewers**: Research Evaluation + L2, optionally one external
  L2-writing/ESL-writing researcher.

### 4.2 Studies (fixed scope, one run each unless a new Goal re-runs)

| Study | Design | Criteria / acceptance (proposed) |
| --- | --- | --- |
| V1 Content review | Panel review of contract §1/§3/§4/§7 definitions, trigger classes, precedence, non-claims; one round + adjudication | Every type rated: definition clear; pairwise mutually exclusive; jointly exhaustive for the intended task universe; disagreements documented with resolution; signed disposition |
| V2 Classification agreement | N = 100–200 prompts (≈50% from S1 sample, ≈50% from S2); two raters apply the documented rules; one adjudication round; deterministic classifier output (once implementable, G5) compared vs human rule-applications | Proposal targets: Cohen's kappa ≥ 0.80 and ≥ 90% raw agreement on the adjudicated set; unclassified rate and reason-code distribution reported per type; `NR` for anything unmeasured |
| V3 Coverage census | Full genre-value census of S1 + prompt-pattern audit; per-type counts; `legacy_unclassified` / `unclassified` counts with reason codes; uncovered patterns listed | 100% of distinct genre values dispositioned (mapped rule, no-map rule, or explicit review item); feeds D-22 manifest coverage |
| V4 Ambiguity adversarial set | Hand-built boundary set: opinion-vs-argumentative discriminator cases; precedence conflicts; near-`general_eap` cases | Classifier must return `unclassified` + reason code (never a silent guess) for conflict cases; deterministic re-run bit-identical under same rules+version |

### 4.3 Reliability expectations (explicit, modest)

* **Procedural determinism:** same input + same rule version → identical output
  (verified in V4; by construction, once implemented).
* **Human-rule agreement:** kappa ≥ 0.80 target (proposal; Researcher may adjust
  before the study runs). Agreement is about *applying the rules*, not about
  external truth.
* **No psychometric reliability indices** (alpha/IRT/SE) are proposed or claimed —
  out of scope because there is no measurement use.
* Every number in the final summary is reported with sample size, version, and
  evidence ids; missing items are `NR`, never fabricated.

### 4.4 Non-goals (boundaries)

* No learner data, no proficiency/difficulty claims, no item banking, no criterion
  validation, no measurement unblocking.
* Results do NOT retroactively validate legacy rows (write-time provenance per
  D-L2-02).
* No product behavior change results from this plan; approval of the plan is not
  approval of taxonomy validity or of Domain Pack v1.

## 5. Governance and boundedness

* Cost bound: four fixed studies, one adjudication round, one summary record;
  re-runs require a new Goal.
* Sign-off: Research Evaluation + L2 review the package and the study results;
  PROGRAM tracks the decision; this package requests review, it does not decide.
* Versioning: validation artifacts versioned and SHA-256-pinned per the
  configuration-version machinery; taxonomy changes (contract §7.2) trigger a
  documented evidence re-check as part of the bump rule (G6 closure).
* Relationship to D-22: V3 output (genre census + dispositions) is a required
  input to the D-22 mapping manifest coverage; the mapping decision is separate
  and remains with Research Evaluation + L2.

## 6. Evidence references

* `docs/domain/L2_TASK_TYPE_TAXONOMY_CONTRACT.md` — §0, §1, §2, §3, §4, §6, §7, §9, §10.
* `docs/domain/D-L2-02_TASK_TYPE_PERSISTENCE_DECISION.md` — write-time provenance.
* `docs/domain/D-L2-09_ZHCN_LABELS_DECISION.md` — label pairs.
* `docs/architecture/writing-intelligence-platform/06_L2_WRITING_DOMAIN.md` — §3.1, §4, §6, §7.
* `docs/architecture/writing-intelligence-platform/14_ARCHITECTURE_DECISIONS.md` — D-04, D-07, D-22, D-26, D-29, D-30.
* `docs/integration/L2_DISCOURSE_ORGANIZATION_FEASIBILITY_SPIKE.md` — UD-02 DEFER evidence.
* `docs/departments/research-evaluation-governance/foundation/07_MEASUREMENT_CLAIM_POLICY.md` — claim classes.
* `app/shared/task_type_registry.py`, `tests/shared/test_domain_packs.py`, `locales/en.json`, `locales/zh_CN.json`, `app/ui/features/student/writing.py`.
* `program-control/USER_DECISION_BRIEF.json` — UD-01/UD-02 resolutions.
* `docs/corpus-readiness/sweccl2/data/legacy_annotation_quality.json` — adjacent corpus QA (not validity).

## 7. Honest-state declaration

No validity evidence currently exists for the five-type taxonomy beyond definitional
and governance records. This package inventories that state, names the gaps, and
proposes a bounded plan. It does NOT approve the taxonomy's validity, does NOT
change product behavior, does NOT implement Domain Pack v1, and does NOT unblock
any measurement use.

*Produced by the L2 execution agent under Goal L2-EVIDENCE-PREP, 2026-08-09.
Proposal only; no approval implied.*
