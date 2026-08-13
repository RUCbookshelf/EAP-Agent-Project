# V1 Ambiguity Adjudication - A-1..A-8 (contract-owner determination + disposition)

**Adjudication id:** `L2-VALIDITY-V1-ADJUDICATION-001`
**Goal:** `L2-D22-CENSUS-AND-V1`
**Date:** 2026-08-09
**Owner:** L2 Writing Domain (contract owner), under Researcher-authorized scoped conditions
**Baseline:** `09264abbd93cdc6b62b83cefd94b3b640319ac9b`
**Branch / Worktree:** `dept/l2-writing` / `A:\EAP Agent Project\worktrees\l2-writing`
**Input:** `docs/domain/L2_VALIDITY_V1_CONTENT_REVIEW.md` register items A-1..A-8;
`docs/domain/L2_TASK_TYPE_TAXONOMY_CONTRACT.md` (contract id
`l2-task-type-taxonomy-contract-v1.0.0`, taxonomy `l2-task-type-taxonomy-v1.0.0`)
**Authorization:** `program-control/researcher-decisions/L2-VALIDITY-scoped-disposition.json`
(SCOPED DISPOSITION AUTHORIZED; adjudication authorized for A-1..A-8 when the
scoped conditions hold)

---

## 0. Scope, method, and honest-state declaration

Each item below is adjudicated ONLY against the Researcher-authorized scoped
conditions (RD `L2-VALIDITY`): the determination must (i) clarify the existing
contract; (ii) introduce no new task construct; (iii) introduce no new
measurement construct; (iv) make no unsupported inferential claim; (v) carry a
documented Research Evaluation + L2 agreement rationale; and (vi) remain
compatible with the five-type taxonomy (five types + `legacy_unclassified` +
`unclassified` states, contract §0/§1/§2.5).

Agreement-basis note: the Researcher-authorized scoped disposition delegates
the A-1..A-8 adjudication to this run under the listed conditions; the L2
contract-owner rationale for each item is documented below with contract
evidence. This record is the agreement document; Research Evaluation retains
the right to object to any item, and the signed expert-panel disposition
(validity package G1) remains an outstanding dependency (unchanged, recorded
in `dependencies_remaining`).

Honest-state declarations (all items): no contract file is amended by this
adjudication (the persisted contract v1.0.0 is immutable; §8.3). Interpretive
determinations are recorded here for the next versioned contract revision per
§8.2 (none of the adopted readings alters the type set, the outcome-state set,
the precedence order, or any trigger class as approved, so no major-version
bump is triggered by this disposition; wording clarifications are patch-class).
No psychometric, proficiency, mastery, ability, learning-gain, or measurement
claim is made anywhere in this record. No Domain Pack v1 content is authored;
classification execution remains gated on Domain Pack v1 trigger dictionaries
(G5, unchanged).

Determination scale (same as V1 review): `RESOLVED-CLARIFICATION` (single
contract-coherent reading adopted with documented rationale),
`RESOLVED-SCOPING` (question assigned to its governed location; contract-level
rule/outcome confirmed complete), `RESEARCHER_REQUIRED` (needs a new construct,
material taxonomy change, or RE-confirmed scope decision).

---

## 1. Item determinations

### A-1 - `discussion` vs `opinion` boundary ("Discuss both views and give your own opinion.")

**Determination:** `RESOLVED-CLARIFICATION` -> `discussion` by chain.

**Rule adopted (contract clarification, patch-class):** a viewpoint-only request
("give your own opinion", "what is your view") is the `opinion` trigger class
(§2.3: explicit personal-viewpoint request WITHOUT an evidence or
counterargument mandate). It is NOT a "mandated final stance": the contract's
only stance-mandate concept is the argumentative-class stance mandate
(take/defend a position, §3), which requires the evidence/counterargument
bundle. Therefore "give your own opinion" does not violate `discussion`'s
"WITHOUT a mandated final stance" condition (§2.3). A prompt with balanced
multi-perspective treatment plus a viewpoint-only request fully matches both
`discussion` and `opinion`; §4 application rule 1 assigns the highest-priority
fully-matched type: `discussion` (3) over `opinion` (4). This pair is not a
comparable-strength conflict: the viewpoint request is structurally subordinate
to the balanced-treatment mandate, and the contract's conflict example is the
argumentative+discussion pair (§4). Consequence: "Discuss both views and give
your own opinion." -> `discussion`.

**Conditions check:** clarifies §2.3/§3/§4 interaction; no new task construct
(both types exist); no measurement construct; no inferential claim; five-type
compatible; agreement rationale documented (this record + scoped disposition).

### A-2 - precedence rationale for `discussion` > `opinion` and silent chain resolution of their co-match

**Determination:** `RESOLVED-CLARIFICATION` (rationale documentation; no outcome
change - §4 chain already orders `discussion` above `opinion`).

**Rationale recorded:** `discussion` mandates balanced multi-perspective
coverage (a content obligation spanning both sides of the issue);
`opinion` mandates only the writer's viewpoint. When a prompt mandates both, the
broader content obligation subsumes the viewpoint request; the chain ordering
expresses subsumption, not importance or difficulty (§0: no ordering by
proficiency/difficulty anywhere). Co-match resolution is silent per §4
application rule 1 (chain), which is the documented design; the conflict rule
(application rule 2) is reserved for comparable-strength pairs (see A-3).

### A-3 - "comparable strength" unoperationalized; conflict-vs-chain boundary

**Determination:** `RESOLVED-SCOPING` - the boundary is Domain Pack v1 content;
the contract-level rule and outcome are complete.

**Determination recorded:** the contract defines both mechanisms - the priority
chain (application rule 1) and the conflict rule with its outcome state
(application rule 2: `unclassified`, reason code `ambiguous_precedence_conflict`)
- and names the canonical conflict example (argumentative + discussion, §4).
Which additional pairs are comparable-strength conflicts is operationalized by
an enumerated conflict-pair table, which per the contract's own architecture is
Domain Pack v1 trigger-dictionary content (§0: "the concrete trigger
dictionaries are Domain Pack v1 content under this contract"; validity package
G5), not contract semantics. The V1 review itself recommended exactly this
placement. Contract-level determinism is complete once that content ships; no
contract change is required. This adjudication explicitly does NOT author the
conflict-pair table (that would pre-decide Domain Pack v1 content in a STUDY
Goal); classification execution remains G5-gated (unchanged, F-9).

### A-4 - `problem_solution` vs `argumentative` cross-section consistency

**Determination:** `RESOLVED-CLARIFICATION` - no contradiction; scope pin +
rationale recorded.

**Determination recorded:** §3 (Constraint 2) governs ONLY the
`opinion`/`argumentative` pair ("Explicit opinion-vs-argumentative
distinction"); it is not a general discriminator across all pairs. Multi-type
co-matches are governed by §4 (Constraint 3) chain: `problem_solution` >
`argumentative`. Rationale for content-anchoring: `problem_solution` names the
problem the task requires the writer to address (a content obligation); the
rhetorical mandate (`argumentative`) governs how the content is argued; §4's
ordering is the approved tie-breaker. "Take a position on the causes of X and
support it with reasons and counterarguments." -> `problem_solution` (unchanged
chain outcome). No outcome change; documentation only.

### A-5 - `general_eap` condition (c) circularity

**Determination:** `RESOLVED-CLARIFICATION` - (c) is a version-binding hook, not
a third criterion.

**Determination recorded:** condition (c) names "the general_eap definition of
the current taxonomy version"; at contract level it is satisfied iff (a) and (b)
hold for the current version - it adds no independent criterion. Its operational
content (EAP-register/instructional-context detection) is implemented by Domain
Pack v1 trigger content (§2.3; G5), which is what (c) references. Consequence:
a task satisfying (a)+(b) is `general_eap`; a task failing (a) or (b) is
`unclassified` - never `general_eap` by default (§7). No outcome change.

### A-6 - compound/multi-part prompts: unit of classification

**Determination:** `RESOLVED-CLARIFICATION` - unit rule adopted.

**Rule adopted (contract clarification):** the unit of classification is the
registered task definition - one prompt string plus its declared task metadata
at task-registration time (§2.1; §2.5 "every prompt falls into exactly one
outcome"). A compound/multi-part definition is ONE unit; it is classified
whole, via the §4 chain; multiple full matches of comparable strength within the
unit invoke the conflict rule -> `unclassified`
(`ambiguous_precedence_conflict`). No per-request split labeling; the unit is
fixed at registration and never re-split on read (D-L2-02 write-time
provenance). Determinism gap for the compound-prompt class is closed without a
new construct.

### A-7 - effects-only prompts ("What are the causes and effects of X?")

**Determination:** `RESOLVED-CLARIFICATION` - closed trigger class; no-extension
reading.

**Determination recorded:** the `problem_solution` trigger class is adopted as
closed: "named problem plus explicit solution/cause requirement" (§2.3).
Effects-only prompts do not fully match `problem_solution` under the literal
class (effects are not cause/solution content). They fall to `general_eap` if
EAP-affirmative (§7) or to `unclassified` otherwise. The alternative reading
(extending the class to include effects) is NOT adopted: it would be a
trigger-class change (major-version amendment, §8.2) requiring explicit Research
Evaluation approval - out of scope for this adjudication. Routing consequence
documented: effects-only prompts never route to `problem_solution` under
taxonomy v1.0.0.

### A-8 - "mandated" not machine-operationally defined

**Determination:** `RESOLVED-SCOPING` - semantic definition complete at contract
level; operational dictionaries are Domain Pack v1 content (G5).

**Determination recorded:** at contract level, "mandated" is semantically
defined by the §3 discriminator table (evidence/reasons, counterargument/
refutation or position-vs-alternatives, persuasive goal mandated by the prompt)
and by each type's trigger class (§2.3). Machine detection is dictionary-based
by the contract's explicit design (§2.3: concrete trigger dictionaries are
Domain Pack v1 content), so no contract ambiguity remains at content level;
execution is G5-gated and is not an implementation claim (F-9 unchanged). The
V1-review proposed owner (Domain Pack v1 content owner, L2) is confirmed.

---

## 2. Disposition

All eight items resolve under the Researcher-authorized scoped conditions:

- A-1..A-7: `RESOLVED-CLARIFICATION`; A-3, A-8: `RESOLVED-SCOPING`.
- No item requires a new task construct or a new measurement construct.
- No item materially changes the taxonomy (type set, outcome-state set,
  precedence order, and trigger classes remain as approved; A-7 explicitly
  preserves the closed class rather than extending it).
- No unsupported inferential claims are made.
- Five-type compatibility holds for every item.
- No unresolved RE-L2 disagreement exists at the time of this record; the
  agreement rationale is documented above under the Researcher-authorized
  scoped disposition.

Therefore, per `L2-VALIDITY-scoped-disposition.json`, the persisted disposition
is:

> **OPERATIONAL_CONTENT_VALIDITY: ADEQUATE_FOR_V1_ROUTING_AND_CLASSIFICATION**

Scoping of the claim (verbatim policy):

- Adequacy is **content-level**: the five types, the two honest states, the
  precedence chain, the conflict rule, and the D-22 legacy mapping manifest
  (M0-M4) are adequate for operational task-routing and task-classification
  semantics as used by V1 routing/classification.
- This is NOT a psychometric validity claim and confers NO proficiency,
  mastery, ability, learning-gain, or measurement meaning on the taxonomy, any
  task, or any learner (contract §0; measurement-claim policy).
- Execution of new-task classification remains gated on Domain Pack v1 trigger
  dictionaries (G5) and on the separately authorized Domain Pack v1
  implementation Goal; execution of legacy mapping remains gated on the D-22
  write-time application lane (manifest v1.0.0 qualified; D-L2-02).
- No comparability participation exists or is implied (D-22 comparability
  freeze; behavior-diff gate required before any future change).
- The contract text v1.0.0 is not amended; adopted interpretations are
  recorded for the next versioned contract revision (§8.2; wording-clarification
  class - no adopted reading alters the type set, precedence, or trigger
  classes).
- `researcher_decision_required = false` for this Goal. Research Evaluation
  may still object to any item; the signed expert-panel disposition (G1) and
  the validation studies (V2/V4) remain outstanding dependencies and are
  unchanged by this record.

## 3. Evidence references

- `docs/domain/L2_VALIDITY_V1_CONTENT_REVIEW.md` - register A-1..A-8; findings F-9, F-11.
- `docs/domain/L2_TASK_TYPE_TAXONOMY_CONTRACT.md` - §0, §1, §2.1, §2.3, §2.5, §3, §4, §6, §7, §8.
- `docs/domain/L2_TAXONOMY_VALIDITY_EVIDENCE_PACKAGE.md` - G1, G3, G5, V2/V4.
- `docs/domain/D-22_LEGACY_GENRE_MAPPING_PROPOSAL.md` - M0-M4; DP-1..DP-4.
- `program-control/researcher-decisions/L2-VALIDITY-scoped-disposition.json`.
- `program-control/researcher-decisions/RD-D22-approved.json`, `RD-D22-DP4-authorized.json`.
- `docs/domain/D-22_legacy_genre_mapping_manifest.v1.0.0.qualified.json` (this Goal).

*Produced by the L2 execution agent under Goal L2-D22-CENSUS-AND-V1, 2026-08-09.
Adjudication record; no contract amendment; no validity ratification beyond the
scoped disposition above.*
