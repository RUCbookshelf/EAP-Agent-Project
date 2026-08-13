# V1 Content Review — Review Records (evidence generation, not ratification)

**Review id:** `L2-VALIDITY-V1-CONTENT-REVIEW-001`
**Goal:** `L2-VALIDITY-EVIDENCE` (V1 of the bounded validation plan in
`docs/domain/L2_TAXONOMY_VALIDITY_EVIDENCE_PACKAGE.md` §4.2)
**Date:** 2026-08-09
**Owner:** L2 Writing Domain
**Baseline:** `09264abbd93cdc6b62b83cefd94b3b640319ac9b`
**Branch / Worktree:** `dept/l2-writing` / `A:\EAP Agent Project\worktrees\l2-writing`
**Review target:** `docs/domain/L2_TASK_TYPE_TAXONOMY_CONTRACT.md` (contract id
`l2-task-type-taxonomy-contract-v1.0.0`; taxonomy `l2-task-type-taxonomy-v1.0.0`)
**Status:** REVIEW RECORDS — EVIDENCE GENERATION ONLY. This document executes the
V1 content-review protocol as a first machine-executed reviewer pass and records
findings and surfaced contract ambiguities. It does **NOT** claim validity, does
**NOT** ratify the taxonomy, and does **NOT** substitute for the signed expert
panel disposition that the validation package (G1) still requires.

---

## 1. Scope and review purpose

Per the validity-evidence package §4.2, V1 is the content review: definitions,
trigger classes, precedence, and non-claims of the taxonomy contract, with every
type rated for definitional clarity, pairwise mutual exclusivity, and joint
exhaustiveness over the intended task universe, with disagreements documented and
a signed disposition. This Goal executes the review (evidence generation) only;
adjudication and signed disposition remain with the human panel (Research
Evaluation + L2, optionally one external L2/ESL-writing researcher).

**Claim scope of the taxonomy (contract §0):** task-routing / task-semantics
metadata only; NOT a proficiency, mastery, ability, learning-gain, or measurement
taxonomy; no comparability participation until the D-22 legacy-mapping decision;
`discourse_organization` remains excluded (UD-02 DEFER; spike record D11 in the
package). The review therefore evaluates **routing-label content adequacy** —
clarity, exclusivity, exhaustiveness, determinism-of-spec — not psychometric
validity.

## 2. Review protocol (executed)

1. **Scope pin:** review items are bound to contract §0, §1, §2, §3, §4, §5, §6,
   §7, §8, §9 and the package's V1 study definition. No item may invent new
   taxonomy semantics.
2. **Evidence discipline:** every determination cites the contract section that
   governs it. Where a determination depends on Domain Pack v1 trigger
   dictionaries (blocked, G5), that dependency is recorded explicitly; the review
   rates the *spec*, never an implementation.
3. **Determination scale:** `CLEAR` (unambiguous at contract level, decidable
   given the trigger dictionaries); `PARTIAL` (semantics clear but a named
   operational decision is deferred or under-documented); `AMBIGUOUS` (two or
   more readings yield different outcomes with no governing rule);
   `GAP` (a real case has no rule); `N_A` (not applicable at contract level).
4. **Review axes:** AX-1 definitional clarity per type/state (§1, §2.3);
   AX-2 deterministic criteria (§2); AX-3 opinion-vs-argumentative discriminator
   (§3); AX-4 precedence chain (§4); AX-5 pairwise mutual exclusivity (10 pairs);
   AX-6 joint exhaustiveness and honest unavailability (§2.5, §6, §7);
   AX-7 non-claims, exclusions, and change-coupling (§0, §8, §9).
5. **Record:** each item records determination, evidence, and reviewer note.
   Ambiguities are surfaced in the register (§11) with proposed resolution
   owners; they are **not resolved** by this run (no silent resolution of
   Researcher or contract-owner decisions).
6. **Reviewer identity (honest-state):** first reviewer = L2 execution agent
   (machine-executed, deterministic, single-pass). Human panel review,
   disagreement adjudication, and signed disposition: **PENDING** — recorded as
   the V1 completion dependency. Nothing here is a signed expert disposition.

## 3. AX-1 — Definitional clarity per type and state

| Item | Target | Contract evidence | Determination | Reviewer note |
| --- | --- | --- | --- | --- |
| T1 | `opinion` | §1; §2.3 | CLEAR | Routing meaning (personal viewpoint/preference; no mandated evidence or counterargument structure) and trigger class (explicit personal-viewpoint/preference/agree-disagree request WITHOUT evidence/counterargument mandate) are explicit and mutually consistent. |
| T2 | `argumentative` | §1; §2.3; §3 | CLEAR | Stance mandate PLUS evidence/argument/counterargument mandate is explicit; §3 gives the operational decision rule (stance + evidence mandate wins). |
| T3 | `discussion` | §1; §2.3 | PARTIAL | Balanced multi-perspective requirement without mandated final stance is explicit; boundary against `opinion` when a prompt also requests the writer's own view is ungoverned (ambiguity A-1). |
| T4 | `problem_solution` | §1; §2.3 | PARTIAL | Named problem + explicit solution/cause requirement is explicit; the scope of "cause/solution" versus effects-only prompts is ungoverned (ambiguity A-7). |
| T5 | `general_eap` | §1; §7 | PARTIAL | Affirmative conditions (a)/(b) are explicit; condition (c) is circular at contract level (ambiguity A-5). |
| S1 | `legacy_unclassified` | §1; §5.2 | CLEAR | Historical-only sentinel; never inferred; explicit-only mapping path; D-22 manifest rules M0–M4 in the mapping proposal supply the disposition vocabulary. |
| S2 | `unclassified` | §1; §4; §6 | PARTIAL | Meaning explicit (missing prompt, ambiguous conflict, insufficient evidence); the reason-code vocabulary is named in prose but not enumerated as a closed list (finding F-11). |

## 4. AX-2 — Deterministic classification criteria (§2)

| Item | Contract evidence | Determination | Reviewer note |
| --- | --- | --- | --- |
| D1 Input source (task definition only; never learner output) | §2.1 | CLEAR | Classification of tasks, not people; consistent with §0 non-claims. |
| D2 Closed, versioned, rule-based procedure; no LLM/probabilistic scoring | §2.2 | CLEAR | Spec-level; same normalization discipline as the frozen corpus features. |
| D3 Trigger classes fixed; concrete dictionaries are Domain Pack v1 content | §2.3 | PARTIAL | Correct scoping per G5; consequence: the criteria are not executable today and "mandate" detection is dictionary-dependent (ambiguity A-8). |
| D4 Rule versioning and provenance | §2.4; §8.1–8.4 | CLEAR | Every typed record carries taxonomy version; consumers fail closed on unknown versions. |
| D5 Exhaustiveness (exactly one outcome; no implicit don't-know into `general_eap`) | §2.5; §7(b); §6.2 | CLEAR | Five types + two states; explicit no-coercion rules. Compound prompts are an ungoverned unit-of-classification case (ambiguity A-6). |

## 5. AX-3 — Opinion-vs-argumentative discriminator (§3)

| Item | Contract evidence | Determination | Reviewer note |
| --- | --- | --- | --- |
| O1 Discriminator basis (mandated structure, not stance words) | §3 table | CLEAR | The two rows are explicit: evidence/reasons mandate and counterargument/refutation (or position-vs-alternatives) mandate separate `argumentative` from `opinion`. |
| O2 Decision rule (evidence mandate wins over the word "opinion") | §3 "Decision rule" | CLEAR | "What is your opinion… support it with reasons" → `argumentative`; viewpoint without evidence mandate → `opinion`. |
| O3 Neither stance nor evidence mandated → neither type | §3 | CLEAR | Non-`opinion`/non-`argumentative` prompts fall elsewhere in the chain (e.g., `discussion`) or to `general_eap`/`unclassified`. |
| O4 No developmental ordering | §3 last paragraph; §0 | CLEAR | Semantic, not developmental; no difficulty ordering anywhere. |
| O5 Operational detectability of "mandated" | §3 vs §2.2 | PARTIAL | Semantic rule is clear; machine detection depends on trigger dictionaries (G5; ambiguity A-8). |

## 6. AX-4 — Precedence chain (§4)

| Item | Contract evidence | Determination | Reviewer note |
| --- | --- | --- | --- |
| P1 Strict priority chain (problem_solution > argumentative > discussion > opinion > general_eap) | §4 | CLEAR | Total order is explicit; each type has a distinct position. |
| P2 Highest-priority fully-matched type wins | §4 application rule 1 | PARTIAL | Clear as written; interacts with the conflict rule (A-3): the contract does not say when a co-match is "comparable strength" (conflict) versus chain-resolvable. |
| P3 `ambiguous_precedence_conflict` outcome | §4 application rule 2 | PARTIAL | The rule and the example (argumentative stance+evidence AND balanced discussion requirement) are explicit; the example pair is itself chain-orderable (argumentative > discussion), so the boundary between conflict and silent chain resolution is not operationalized (A-3). |
| P4 `general_eap` never selected when any specific trigger matched | §4 application rule 3; §7(b) | CLEAR | Consistent across sections. |
| P5 `unclassified` never promoted automatically | §4 application rule 4; §6.2–6.3 | CLEAR | Consistent. |
| P6 No-silent-guess rationale | §4 rationale | CLEAR | Routing semantics differ; documented. Operability depends on P3 (A-3). |

## 7. AX-5 — Pairwise mutual exclusivity (10 pairs)

Pairwise exclusivity is judged on the documented definitions plus the precedence
chain as the tie-breaker, and separately on whether a *governing rule* exists for
the boundary case (that is what a content reviewer evaluates).

| Pair | Determination | Evidence | Note / ambiguity |
| --- | --- | --- | --- |
| opinion ↔ argumentative | CLEAR | §3 | Explicit mandated-structure discriminator; only operational dependency is A-8. |
| opinion ↔ discussion | AMBIGUOUS | §2.3; §3 | A prompt requiring balanced treatment AND the writer's own view ("give your own opinion") without an evidence mandate: discussion requires "WITHOUT a mandated final stance", but "give your own opinion" is not defined as a mandated final stance vs a viewpoint-only request (A-1). |
| opinion ↔ problem_solution | CLEAR | §4 | Co-matches resolve to `problem_solution` by chain position; core trigger classes are disjoint (viewpoint-only vs named problem + cause/solution). |
| opinion ↔ general_eap | CLEAR | §7(b) | `general_eap` requires no specific trigger matched. |
| argumentative ↔ discussion | AMBIGUOUS | §4 | The contract's own conflict example; "comparable strength" is not operationalized, and this pair is simultaneously chain-orderable (A-3). |
| argumentative ↔ problem_solution | PARTIAL | §4 | Chain resolves to `problem_solution`; the rationale for content-anchoring over the rhetorical mandate for this pair is not documented, and reading §3 alone would suggest `argumentative` (A-4). |
| argumentative ↔ general_eap | CLEAR | §7(b) | No specific trigger matched is a condition of `general_eap`. |
| discussion ↔ problem_solution | PARTIAL | §4 | Chain resolves ("discuss causes/solutions considering multiple perspectives" → `problem_solution`); rationale under-documented; same A-3 question family. |
| discussion ↔ general_eap | CLEAR | §7(b) | No specific trigger matched is a condition of `general_eap`. |
| problem_solution ↔ general_eap | CLEAR | §7(b) | No specific trigger matched is a condition of `general_eap`. |

**Pairwise summary:** 6/10 pairs CLEAR; 2/10 PARTIAL; 2/10 AMBIGUOUS. The
ambiguous pairs both involve the unoperationalized conflict-vs-chain boundary
(A-3) and the discussion stance boundary (A-1). No pair is mutually exclusive by
construction alone; exclusivity is achieved through the chain plus the conflict
rule, which is the documented design (contract §4).

## 8. AX-6 — Joint exhaustiveness and honest unavailability (§2.5, §6, §7)

| Item | Contract evidence | Determination | Reviewer note |
| --- | --- | --- | --- |
| E1 Exactly-one outcome: five types + `legacy_unclassified` (historical only) + `unclassified` (with reason code) | §2.5 | CLEAR | Complete outcome set stated; no residual bucket. |
| E2 No implicit don't-know collapse into `general_eap` | §2.5; §6.2; §7 | CLEAR | Triple redundancy across sections — consistent. |
| E3 `legacy_unclassified` never inferred; explicit-only mapping | §5 | CLEAR | D-22 proposal M0–M4 operationalize. |
| E4 `unclassified` carries no typed semantics; no silent reclassification | §6.3–6.5 | CLEAR | Consistent with D-L2-02 write-time provenance. |
| E5 Coverage of the intended task universe (routing frame) | §1; §6 | PARTIAL | Definitionally complete over the *stated* frame; empirical coverage is exactly what V3 (census) must measure — unknown today (G3). |
| E6 Compound/multi-part prompts | §2.1 | AMBIGUOUS | "The task definition" is the unit, but a definition containing multiple independent task requests has no unit rule (A-6). |
| E7 Effects-only prompts ("What are the causes and effects of X?") | §2.3 | AMBIGUOUS | `problem_solution` trigger class names "cause/solution" only; an effects-only requirement either extends the class (reading 1 → `problem_solution`) or does not (reading 2 → `general_eap` if EAP-affirmative) (A-7). |

## 9. AX-7 — Non-claims, exclusions, and change-coupling (§0, §8, §9)

| Item | Contract evidence | Determination | Reviewer note |
| --- | --- | --- | --- |
| N1 Non-claims checklist (7 boxes) | §0; §9 | CLEAR | Consistent with the measurement-claim policy (`docs/departments/research-evaluation-governance/foundation/07_MEASUREMENT_CLAIM_POLICY.md`); no claim surface created. |
| N2 `discourse_organization` excluded | §1; §9; package D11 | CLEAR | Not present in the five types or the two states; exclusion honored (UD-02 DEFER). |
| N3 Versioning: SemVer bump rules | §8.1–8.2 | CLEAR | Add type = minor; criteria/trigger/precedence change = major; wording = patch. |
| N4 Evidence re-check on taxonomy change (G6) | §8 vs package G6 | GAP | Bump rules exist but no evidence re-check rule is tied to a taxonomy change; G6 remains open (finding F-7). |
| N5 Single active version; rollback via configuration-version machinery | §8.3 | CLEAR | Mechanism-level; unchanged by this Goal. |

## 10. Findings register

| # | Finding | Severity | Evidence | Status / owner |
| --- | --- | --- | --- | --- |
| F-1 | All five types have explicit routing semantics; none is a residual bucket; `general_eap` is affirmative | info | §1; §7 | recorded |
| F-2 | Opinion-vs-argumentative distinction is the most fully specified boundary (§3) | info | §3 | recorded |
| F-3 | Exactly-one-outcome exhaustiveness with two honest states is explicit | info | §2.5; §6 | recorded |
| F-4 | No-silent-guess guarantee is consistent in intent across §4/§6/§7 | info | §4; §6; §7 | recorded; operability depends on A-3 |
| F-5 | `discourse_organization` exclusion honored in the reviewed contract | info | §1; §9; package D11 | recorded |
| F-6 | Non-claims consistent with measurement-claim policy; no claim surface | info | §0; §9; policy 07 | recorded |
| F-7 | G6 open: no evidence re-check rule tied to taxonomy bumps | non-blocking | §8; package G6 | contract owner + Research Evaluation (outside this Goal) |
| F-8 | `legacy_unclassified` vs `unclassified` semantics are distinct and explicit | info | §1; §5; §6 | recorded |
| F-9 | Determinism is spec-level; no implementation exists (G5) | info | §2.2; package G5 | Domain Pack v1 (separately gated) |
| F-10 | V1 evidence state changed: review records now exist (G1 partially served); signed human panel disposition still outstanding | info | this document | Research Evaluation + L2 adjudication; remains in dependencies_remaining |
| F-11 | `unclassified` reason-code vocabulary is named in prose (missing prompt, ambiguous conflict, insufficient evidence) but not enumerated as a closed machine-readable list | non-blocking | §1; §4; §6.1 | record with V3/V4 instruments; contract-owner clarification recommended before V2 execution |

## 11. Surfaced contract ambiguities (register — NOT resolved here)

Each entry names the ambiguity, the two readings, the consequence, and the
proposed resolution owner. Resolution is a contract-owner / Researcher decision
and is explicitly outside this Goal.

| # | Ambiguity | Readings and consequence | Proposed resolution owner |
| --- | --- | --- | --- |
| A-1 | `discussion` vs `opinion` boundary when a prompt requires balanced treatment AND asks for the writer's own view without an evidence mandate ("Discuss both views and give your own opinion.") | Reading 1: "give your own opinion" = viewpoint-only request → `opinion` as the full match (discussion's "no mandated final stance" is violated). Reading 2: "give your own opinion" is not an argumentative stance mandate, so the prompt still fully matches `discussion` → `discussion` by chain. Reading 3: both fully match → conflict/`unclassified`. No governing rule distinguishes "mandated final stance" from "viewpoint requested". | Contract owner (L2) + Research Evaluation; recommend explicit rule + V2/V4 boundary set |
| A-2 | Precedence rationale for `discussion` > `opinion` and silent chain resolution for their co-match | The chain silently resolves opinion+discussion co-matches; the "comparable strength" conflict notion (§4) suggests some co-matches must conflict. Basis for the ordering and for which co-matches conflict is undocumented. | Contract owner (L2); document rationale in a patch-level contract note or major-version rule change |
| A-3 | "Comparable strength" is not operationalized; conflict-vs-chain boundary undefined | The §4 example pair (argumentative + discussion) is chain-orderable (argumentative > discussion), so the chain alone cannot decide when a co-match is a conflict. A classifier needs a deterministic rule (e.g., an enumerated conflict-pair table) before V2/V4 can run without researcher judgment at classification time. | Contract owner (L2) + Research Evaluation; recommend explicit conflict-pair table as part of trigger-dictionary content (Domain Pack v1) |
| A-4 | `problem_solution` silently outranks a full `argumentative` match ("Take a position on the causes of X and support it with reasons and counterarguments.") | Chain: `problem_solution`. §3 decision rule read alone: `argumentative` (stance + evidence mandate). Cross-section consistency question; consequence for routing semantics is material (practice-target eligibility differs). | Contract owner (L2); confirm intended semantics and record rationale |
| A-5 | `general_eap` condition (c) is circular at contract level | (c) "the general_eap definition of the current taxonomy version is satisfied" restates (a)+(b) unless it refers to Domain Pack trigger content (blocked, G5). Currently vacuous; a task satisfying (a)+(b) satisfies (c) by definition. | Contract owner (L2); clarify whether (c) is a Domain Pack v1 content hook |
| A-6 | Compound/multi-part prompts have no unit-of-classification rule | "Task definition" (§2.1) may contain several independent task requests; readings: one label via chain (silent), or `unclassified` (multi-task), or per-prompt units. Consequence: determinism gap for a real prompt class. | Contract owner (L2); recommend explicit unit rule; add to V3 feature checklist + V4 set |
| A-7 | Effects-only prompts ("What are the causes and effects of X?") are not governed | `problem_solution` trigger class covers "cause/solution" only. Reading 1: effects ⊂ problem content → `problem_solution`. Reading 2: no match → `general_eap` (if EAP-affirmative). Different routing outcomes from the same prompt. | Contract owner (L2) + Research Evaluation; confirm class scope; add effects-only to V3 checklist |
| A-8 | "Mandated" (evidence/argument/counterargument) is semantically defined but not machine-operationally defined | Detection depends on Domain Pack v1 trigger dictionaries (G5); contract-level examples are imperative/interrogative, but no rule governs mandate detection beyond the dictionaries. Not an implementation claim; a spec-completeness item. | Domain Pack v1 content owner (L2), under the implementation authorization lane |

**Ambiguity summary:** 8 ambiguities surfaced; 0 resolved by this run. All are
recorded for contract-owner / Research Evaluation disposition and for direct use
in V2 (agreement set construction) and V4 (adversarial boundary set) study design.

## 12. V1 status and honest-state declaration

* V1 review protocol executed; review records produced for AX-1..AX-7 with
  evidence-anchored determinations.
* **No validity claim is made.** **No ratification is issued.** The signed expert
  panel disposition (adjudication + signature, package §4.2 V1 acceptance) is
  **PENDING** and is recorded in `dependencies_remaining`.
* G1 status: review *records* now exist (previously none); G1 as an acceptance
  item (signed panel disposition on mutual exclusivity / joint exhaustiveness /
  coverage frame) remains **open**.
* The ambiguities register is an input to V2/V4 design and to the D-22 lane; it
  does not block anything and does not change product behavior.
* No Domain Pack v1 implementation; no product code changes; raw SWECCL untouched;
  `discourse_organization` remains excluded.

## 13. Evidence references

* `docs/domain/L2_TASK_TYPE_TAXONOMY_CONTRACT.md` — §0, §1, §2, §3, §4, §5, §6, §7, §8, §9.
* `docs/domain/L2_TAXONOMY_VALIDITY_EVIDENCE_PACKAGE.md` — §2.4, §3 (G1, G3, G5, G6), §4.2 (V1), §4.4.
* `docs/domain/D-22_LEGACY_GENRE_MAPPING_PROPOSAL.md` — M0–M4 rules; DP-1..DP-4.
* `docs/architecture/writing-intelligence-platform/06_L2_WRITING_DOMAIN.md` — §3.1, §4, §6.
* `docs/departments/research-evaluation-governance/foundation/07_MEASUREMENT_CLAIM_POLICY.md` — statement classes.
* `docs/integration/L2_DISCOURSE_ORGANIZATION_FEASIBILITY_SPIKE.md` — UD-02 DEFER evidence.
* `program-control/USER_DECISION_BRIEF.json` — UD-01/UD-02.

*Produced by the L2 execution agent under Goal L2-VALIDITY-EVIDENCE, 2026-08-09.
Review records only; evidence generation; no validity claim; no ratification.*
