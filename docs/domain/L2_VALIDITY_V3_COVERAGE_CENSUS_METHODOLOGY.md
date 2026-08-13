# V3 Coverage Census — Methodology and Instruments (prepared; execution NOT authorized)

**Methodology id:** `L2-VALIDITY-V3-COVERAGE-CENSUS-METHODOLOGY-001`
**Goal:** `L2-VALIDITY-EVIDENCE` (V3 of the bounded validation plan in
`docs/domain/L2_TAXONOMY_VALIDITY_EVIDENCE_PACKAGE.md` §4.2)
**Date:** 2026-08-09
**Owner:** L2 Writing Domain
**Baseline:** `09264abbd93cdc6b62b83cefd94b3b640319ac9b`
**Branch / Worktree:** `dept/l2-writing` / `A:\EAP Agent Project\worktrees\l2-writing`
**Status:** METHODOLOGY PREPARED — **EXECUTION NOT_RUN**. This document prepares
the V3 coverage census (data-collection plan + instruments: census protocol and
feature checklist) and records the named execution dependency: a governed
snapshot of the real legacy `essays` table (decision point **DP-4**) is **NOT
authorized**, so no census numbers are produced or estimated here. No validity
claim is made; nothing is ratified.

---

## 1. Purpose and claim scope

V3 addresses gap **G3** (coverage unknown) of the validity-evidence package: the
real legacy prompt/genre universe has never been censused, and the
`legacy_unclassified` / `unclassified` rates are unmeasured. The census produces
coverage/representativeness evidence for the taxonomy's stated use — deterministic
**routing labels with honest unavailability** (package §1). It is deliberately not
a psychometric study (package §2.4, §4.3); its output feeds three consumers:

1. **D-22 manifest coverage:** 100% of distinct genre values dispositioned
   (mapped rule, no-map rule, or explicit review item) per the mapping proposal's
   M0–M4 rules (contract §5; D-22 proposal §2–§3).
2. **V2 sampling frame:** the census defines the stratum frame from which the
   classification-agreement sample is drawn (package §4.2 V2, ≈50% S1).
3. **V4 ambiguity set:** census-observed prompt patterns seed the adversarial
   boundary set (package §4.2 V4; this methodology's checklist items map to
   surfaced contract ambiguities A-1..A-8 from the V1 review records).

**Non-claims (unchanged):** the census assigns no level, score, quality, or
ability; it does not validate the taxonomy; it does not retroactively validate
legacy rows (D-L2-02 write-time provenance); it does not change product behavior;
it never accesses raw SWECCL (corpus genres are not product legacy genres);
`discourse_organization` remains excluded (UD-02 DEFER).

## 2. Execution dependency — recorded (blocking, not yet authorized)

| Field | Value |
| --- | --- |
| Dependency | Governed snapshot of the real legacy `essays` table (product DB) with a documented snapshot procedure |
| Decision point | **DP-4 — snapshot authorization** (D-22 proposal §7; researcher-decision record `RD-D22-legacy-genre-mapping.json`) |
| Owner of the authorization | Research Evaluation + PROGRAM name the snapshot procedure; Research Evaluation + L2 own the decision |
| Current status | **NOT AUTHORIZED — census execution blocked** |
| Evidence | `D-22_LEGACY_GENRE_MAPPING_PROPOSAL.md` §2, §7 (DP-4); `program-control/researcher-decisions/RD-D22-legacy-genre-mapping.json`; `program-control/handoff-digests/L2-EVIDENCE-PREP__*.digest.json` (dependencies_remaining) |
| Consequence | No S1 rows, no genre-value counts, no per-type counts, no `legacy_unclassified` rate, no coverage statistics are produced or estimated by this Goal. All V3 numeric outputs remain `NR` until the snapshot exists and this methodology is re-executed under a new Goal |
| Substitute sources | None. Raw SWECCL is NOT a substitute (corpus genres ≠ product legacy genres; contract §1; package §4.1 S1 note) |

The instruments below are ready to execute unchanged once DP-4 resolves and a
new Goal authorizes the census run.

## 3. Data-collection plan

### 3.1 Sources

| Source | Content | Status | Handling |
| --- | --- | --- | --- |
| S1 | Governed snapshot of the real legacy `essays` table (product DB): rows, free-text `genre`, stored prompt/task metadata as available | NOT authorized (DP-4) | Extract via the named snapshot procedure; integrity-pin the extract (row count + SHA-256); treat as immutable governed artifact; never write back |
| S2 | License-clean public/owned EAP task-prompt collections (coverage breadth outside the product DB) | Not yet selected | Selection requires per-source license review; fail-closed on unclear license; record selection + version per source |
| Excluded | Raw SWECCL; learner output/behavior/history; any corpus distribution as legacy-genre evidence | permanently | contract §1; package §4.1 |

### 3.2 Variables collected per S1 row

| Field | Definition |
| --- | --- |
| row id | governed snapshot row identifier (opaque; no learner identity) |
| genre_raw | free-text `genre` exactly as stored |
| genre_normalized | casefold + whitespace/punctuation normalization (contract §2.2 discipline) |
| locale_hint | declared locale/display-string provenance where determinable (en / zh_CN / unknown) |
| prompt_text | stored prompt/task definition where present (for the pattern audit only) |
| genre_disposition | `mapped_rule` (rule id) / `no_map_rule` (reason code) / `review_item` — per D-22 M0–M4 + DP-2 posture |
| pattern_features | feature-checklist flags from the prompt-pattern audit (instrument 2) |
| audit_note | explicit reviewer note; never a silent guess |

### 3.3 Census outputs (defined; not computed)

1. Distinct normalized genre-value table with disposition per value and reason
   code (coverage = 100% of distinct values dispositioned).
2. Per-type and per-state counts and rates (five types + `legacy_unclassified` +
   `unclassified` with reason codes) — computed by applying approved mapping
   rules to S1 and pattern evidence to S2; classification of new prompts remains
   gated on Domain Pack trigger dictionaries (G5), so S2 pattern counts are
   feature-presence statistics, not final labels.
3. Uncovered-pattern list: prompts/features with no governing rule — expected to
   include the V1 ambiguity families (A-1..A-8).
4. Machine-readable census record (JSON), versioned and SHA-256-pinned per the
   configuration-version machinery, with sample sizes, versions, and evidence ids
   in every reported number; anything unmeasured reported as `NR`.

### 3.4 Sampling and QA rules

* S1 census is full-population over the snapshot (no sampling for the genre
  census); the prompt-pattern audit samples with a documented stratum frame
  (strata = distinct genre values, min 5 prompts per stratum, capped at a
  documented bound).
* QA: independent second disposition pass on 100% of distinct genre values;
  reason-code completeness check; duplicate-rule detection (D-22 proposal §4.2);
  recorded discrepancies resolved by explicit review item — never by coin flip.

## 4. Instrument 1 — Census protocol (steps)

| Step | Action | Gate / evidence |
| --- | --- | --- |
| C1 | Verify DP-4 authorization record and named snapshot procedure exist | snapshot authorization + procedure id; else STOP (blocked) |
| C2 | Obtain governed snapshot; record extract method, row count, SHA-256 | snapshot integrity record |
| C3 | Normalize genre values (contract §2.2 discipline); enumerate distinct values | distinct-value table |
| C4 | Apply D-22 mapping rules M0–M4 to each distinct value; assign disposition + reason code | disposition table; 100% coverage check |
| C5 | Draw prompt-pattern audit sample per stratum frame; apply feature checklist | sample manifest (ids, sizes) |
| C6 | Compute census outputs §3.3 with per-number provenance (source, version, n) | census record (JSON) |
| C7 | QA pass: second disposition, reason-code completeness, duplicate-rule check | QA record; discrepancies as review items |
| C8 | Version + pin census record; publish under `docs/domain/` or the named governed location | version + SHA-256 |
| C9 | Produce V3 summary with honest `NR` for anything unmeasured; no validity claim | V3 summary record |

## 5. Instrument 2 — Feature checklist (prompt-pattern audit)

Feature items are derived from contract trigger classes (§2.3, §3, §4, §7) and
the V1 ambiguity register. Each item is recorded `present | absent | unclear`
with prompt evidence; `unclear` is never promoted to a guess. Checklist version
`v1.0.0-draft` — final version rides the taxonomy version at execution time.

| Feature id | Feature | Definition (evidence) | Contract anchor |
| --- | --- | --- | --- |
| F01 | viewpoint_request | explicit request for the writer's personal viewpoint/preference | §1 `opinion`; §3 |
| F02 | agree_disagree_request | agree/disagree framing | §2.3 `opinion` trigger class |
| F03 | stance_mandate | take/defend a position mandated | §1 `argumentative`; §2.3 |
| F04 | evidence_mandate | reasons/evidence explicitly required | §3 discriminator |
| F05 | counterargument_mandate | counterargument/refutation (or position-vs-alternatives) required | §3 discriminator |
| F06 | balanced_multi_perspective | both sides / advantages AND disadvantages / compare views | §2.3 `discussion` |
| F07 | final_stance_mandate | a final stance is mandated (boundary vs F01 — ambiguity A-1) | §2.3 `discussion`; A-1 |
| F08 | named_problem | a problem is named in the prompt | §2.3 `problem_solution` |
| F09 | solution_requirement | solution content explicitly required | §2.3 `problem_solution` |
| F10 | cause_requirement | cause content explicitly required | §2.3 `problem_solution` |
| F11 | effects_only | effects (not cause/solution) content required — ambiguity A-7 | §2.3; A-7 |
| F12 | eap_register_evidence | academic-register evidence in the task definition | §7(a) |
| F13 | instructional_context | EAP instructional context evidenced | §7(a) |
| F14 | compound_prompt | multiple independent task requests in one task definition — ambiguity A-6 | §2.1; A-6 |
| F15 | missing_prompt | no prompt/task definition available at registration | §6.1 |
| F16 | conflict_evidence | two fully-matched trigger classes present — ambiguity A-3 | §4; A-3 |
| F17 | no_type_trigger | no specific-type feature present (candidate `general_eap`/`unclassified`) | §7(b) |

Every checklist row in a census record carries the prompt evidence location;
items F11, F14, F16 feed the V4 adversarial set; F15/F16 feed reason-code
statistics (F-11 recommendation: close the reason-code vocabulary before V2).

## 6. Governance and bounds

* One run per authorization; re-runs require a new Goal (package §5).
* Outputs versioned and SHA-256-pinned; taxonomy changes trigger a documented
  evidence re-check (package §5; G6 remains open — see V1 review F-7).
* V3 output is a required input to the D-22 mapping manifest coverage; the
  mapping decision itself remains with Research Evaluation + L2.
* No product code, no registry/locale/UI/API change, no raw SWECCL access, no
  learner data, no validity claim, no ratification.

## 7. Evidence references

* `docs/domain/L2_TAXONOMY_VALIDITY_EVIDENCE_PACKAGE.md` — §2.4 (coverage row), §3 (G3), §4.1 (S1/S2), §4.2 (V3), §4.3, §5.
* `docs/domain/L2_TASK_TYPE_TAXONOMY_CONTRACT.md` — §1, §2.2, §2.3, §3, §4, §5, §6, §7.
* `docs/domain/L2_VALIDITY_V1_CONTENT_REVIEW.md` — ambiguities A-1..A-8; findings F-3, F-11.
* `docs/domain/D-22_LEGACY_GENRE_MAPPING_PROPOSAL.md` — §2 (inventory), §3 (M0–M4), §4 (precedence), §7 (DP-4).
* `program-control/researcher-decisions/RD-D22-legacy-genre-mapping.json` — DP-4 recommendation.
* `docs/departments/research-evaluation-governance/foundation/07_MEASUREMENT_CLAIM_POLICY.md` — statement classes.

*Produced by the L2 execution agent under Goal L2-VALIDITY-EVIDENCE, 2026-08-09.
Methodology and instruments prepared; execution blocked on DP-4 snapshot
authorization; no census numbers produced; no validity claim; no ratification.*
