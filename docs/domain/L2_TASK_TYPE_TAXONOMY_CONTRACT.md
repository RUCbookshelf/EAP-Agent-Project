# L2 Task-Type Taxonomy Contract

**Contract id:** `l2-task-type-taxonomy-contract-v1.0.0`  
**Taxonomy version:** `l2-task-type-taxonomy-v1.0.0`  
**Status:** PERSISTED (UD-01 approved; 2026-08-09)  
**Owner:** L2 Writing Domain  
**Decision provenance:** `USER_DECISION_BRIEF.json` UD-01 option 1 (recommended); `docs/integration/L2_PREREQUISITE_RESOLUTION.md`; `program-control/qualified-adrs/ADR-07-evaluation-taxonomy.json`; architecture decisions D-04, D-22, D-26, D-29.  
**Baseline:** `5aafe2728d7135212bd675a6975b44bcf99ee099`  
**Branch:** `dept/l2-writing`  
**Worktree:** `A:\EAP Agent Project\worktrees\l2-writing`

---

## 0. Purpose and scope

This contract persists the UD-01-approved five-type operational taxonomy for L2
writing tasks and fixes its operational semantics. The taxonomy is **task-routing
and task-semantics metadata ONLY**. It exists so that tasks can carry a typed,
versioned, deterministic semantic label that downstream L2 behavior (task routing,
task-type expectations, practice target eligibility) may reference.

**Explicit non-claim (verbatim policy):** this taxonomy is NOT a validated
proficiency, mastery, ability, learning-gain, or measurement taxonomy. It assigns
no level, score, quality, or ability to any learner, and it confers no validity
evidence on any dimension, diagnosis, or outcome. It must never be used to order
learners, tasks, or types by proficiency, and no type label implies learner
performance. The measurement-claim policy
(`docs/departments/research-evaluation-governance/foundation/07_MEASUREMENT_CLAIM_POLICY.md`)
and the practice/formative/research/protected evaluation separation of ADR-07
apply to everything downstream of this contract.

This contract resolves the enumeration portion of D-L2-01 only. It does **not**
implement Domain Pack v1 content, does not change product code, does not alter the
registry mechanisms, and does not resolve D-L2-02 (persisted vs derived), D-L2-09
(zh_CN labels), or D-L2-10 (UI picker), which remain open.

## 1. Taxonomy identity and enumeration

Namespace: `l2` (namespace-scoped `TaskTypeRegistry`, D-04). Values are
`snake_case` task-type ids. All five types are first-class; none is a residual or
"other" bucket (the fallback semantics of `general_eap` are fixed in Section 7).

| task_type id | display name | task semantics (routing meaning) |
| --- | --- | --- |
| `opinion` | Opinion Essay | Task asks for the writer's personal viewpoint/preference; no mandated evidence or counterargument structure. |
| `argumentative` | Argumentative Essay | Task mandates a position plus evidence-based argumentation (reasons/evidence and/or counterargument). |
| `discussion` | Discussion Essay | Task requires balanced examination of two or more perspectives; no mandated final stance. |
| `problem_solution` | Problem-Solution Essay | Task names a problem and requires cause/solution content. |
| `general_eap` | General EAP | Task is affirmatively an EAP writing task that matches no specific type under the current criteria. |

Two additional **states** exist beside the five types. They are not task types:

| state | meaning |
| --- | --- |
| `legacy_unclassified` | Historical rows whose genre/task evidence is insufficient for explicit mapping (D-22 sentinel). Never inferred. |
| `unclassified` | A task whose classification could not be deterministically established (missing prompt, ambiguous conflict, or insufficient evidence) at registration time. Never inferred. |

Per D-22, `task_type` is **metadata-only**: it participates in **no**
comparability predicate until the legacy-mapping decision is resolved, and any
future comparability change requires a behavior-diff test over a snapshot of the
real legacy database. Per `docs/architecture/writing-intelligence-platform/06_L2_WRITING_DOMAIN.md`
section 4, `genre` remains free text for backward compatibility; `task_type`
becomes the comparability/clustering key only under a new rule version, with old
snapshots untouched.

## 2. Constraint 1 - Deterministic classification criteria

1. **Input source:** classification operates on the **task definition** (the
   writing prompt and declared task metadata) at task-registration / task-metadata
   time. It NEVER operates on learner output, learner behavior, or learner history.
   The taxonomy classifies tasks, not people.
2. **Deterministic procedure:** classification is a closed, versioned, rule-based
   decision procedure. Rules are string-matching criteria over a normalized prompt:
   casefold, whitespace/punctuation normalization, word-boundary matching (the same
   normalization discipline as the frozen corpus features). No model output, no
   LLM judgment, no probabilistic scoring is permitted at classification time.
3. **Criteria classes per type:** the contract fixes the *classes* of triggers;
   the concrete trigger dictionaries are Domain Pack v1 content under this
   contract. Each type's trigger class:

   | type | trigger class (task-semantics evidence) |
   | --- | --- |
   | `opinion` | explicit personal-viewpoint/preference/agree-disagree request WITHOUT an evidence or counterargument mandate |
   | `argumentative` | stance mandate (take/defend a position) PLUS evidence/argument/counterargument mandate |
   | `discussion` | balanced multi-perspective requirement (both sides, advantages AND disadvantages, compare views) WITHOUT a mandated final stance |
   | `problem_solution` | named problem plus explicit solution/cause requirement |
   | `general_eap` | generic academic-writing instruction with no specific-type trigger (conditions in Section 7) |

4. **Rule versioning:** every trigger set and the decision procedure carry the
   taxonomy version; a classification records the rule version that produced it
   (provenance, Section 8).
5. **Exhaustiveness:** every prompt falls into exactly one outcome: one of the
   five types, `legacy_unclassified` (historical only), or `unclassified` (with a
   reason code). There is no implicit "don't know" collapse into `general_eap`.

## 3. Constraint 2 - Explicit opinion-vs-argumentative distinction

The two types are distinguished by the **task's mandated structure**, not by the
presence of stance words:

| discriminator | `opinion` | `argumentative` |
| --- | --- | --- |
| personal viewpoint requested | required | required (as the position) |
| evidence/reasons mandated by prompt | no | yes |
| counterargument/refutation mandated | no | yes (or position-vs-alternatives) |
| persuasive goal (convince reader) | not mandated | mandated |
| example | "What is your opinion on studying abroad?" | "Take a position on studying abroad and support it with reasons and counterarguments." |

Decision rule: if the prompt contains an **evidence/argument/counterargument
mandate**, the task is `argumentative` even when the word "opinion" appears
(stance + evidence mandate wins). If the prompt requests a viewpoint with no
evidence mandate, the task is `opinion`. A prompt that mandates neither stance nor
evidence is neither of these types.

The distinction is semantic, not developmental: `opinion` is not "lower" than
`argumentative`. No difficulty ordering exists anywhere in this taxonomy (Section 0).

## 4. Constraint 3 - Precedence for ambiguous prompts

When triggers from multiple types co-occur, assignment follows a strict priority
chain (highest first):

1. `problem_solution` - most content-anchored (named problem + solution/cause).
2. `argumentative` - strongest rhetorical mandate (stance + evidence).
3. `discussion` - balanced multi-perspective requirement.
4. `opinion` - viewpoint-only requirement.
5. `general_eap` - only when no type 1-4 trigger matched (Section 7).

Application rules:

- A prompt is assigned the highest-priority type whose trigger class is fully
  matched.
- If a prompt **fully** matches two trigger classes of comparable strength (e.g.,
  an argumentative stance+evidence mandate AND a balanced discussion requirement),
  the outcome is `unclassified` with reason code `ambiguous_precedence_conflict`.
  Example: "Discuss both views and take a position, arguing with evidence." - no
  silent choice is made; the task is surfaced for an explicit decision before it
  may carry typed semantics.
- `general_eap` is never selected when any specific trigger matched.
- `unclassified` is never promoted to `general_eap` or to any type automatically.

Rationale: routing semantics differ materially between types; a silent guess would
change downstream task-type expectations and practice-target eligibility without
evidence.

## 5. Constraint 4 - Legacy task/genre mapping without silent inference

Legacy rows carry arbitrary free-text `genre` and no `task_type` (D-22;
`06_L2_WRITING_DOMAIN.md` section 6; `app/services/learner_model.py` `_cluster_key`
substring inference that must not survive).

1. **Explicit-only mapping:** a legacy `genre` maps to a `task_type` ONLY through
   an approved, versioned mapping manifest that records per-row or per-genre rule
   id, rationale, and evidence. No mapping is inferred from string similarity,
   substring matches, or taxonomy definitions.
2. **Insufficient evidence:** genres without a documented, approved mapping rule
   (including `expository` and `narrative`) stay `Unclear` / `legacy_unclassified` -
   never guessed (`06_L2_WRITING_DOMAIN.md` section 6).
3. **Governance:** the mapping manifest and its approval are a data-governance
   decision owned by Research Evaluation + L2 (same document). PROGRAM does not
   infer this approval.
4. **Comparability freeze:** `task_type` participates in NO comparability
   predicate until the legacy-mapping decision is resolved (D-22). A future
   comparability change requires a behavior-diff test over a snapshot of the real
   legacy database, plus the frozen-contract review path (D-22, D-30).
5. **Provenance:** every legacy row that later gains a typed value records the
   mapping manifest version, rule id, and approval reference at write time.

## 6. Constraint 5 - Unknown/unclassified handling

1. **States are first-class.** `legacy_unclassified` (historical, evidence
   insufficient) and `unclassified` (new task: missing prompt, ambiguous conflict,
   or insufficient evidence) are explicit, persisted outcomes with a reason code
   and the classification rule version.
2. **No coercion:** unclassified tasks are never folded into `general_eap`, never
   assigned a default type, and never silently reclassified on later reads.
3. **No typed semantics:** unclassified tasks carry no task-type routing,
   expectations, or practice-target eligibility. They behave as untyped metadata
   (which is the D-22 default: metadata-only, no comparability participation).
4. **Display:** UI/API surfaces may show an explicit "unclassified" honest state
   but must not present a guessed type. Typed pickers are out of scope (D-L2-10).
5. **Escalation:** a task may be reclassified later ONLY by an explicit decision
   recorded with provenance (human/Researcher decision or a new approved mapping
   rule), never by inference.

## 7. Constraint 6 - `general_eap` fallback semantics

`general_eap` is a designated type with **affirmative** conditions, not a garbage
bucket:

- (a) the task is affirmatively an EAP writing task (instructional context and
  academic-register evidence in the task definition); AND
- (b) no specific-type trigger (problem_solution, argumentative, discussion,
  opinion) matched under the priority chain; AND
- (c) the general_eap definition of the current taxonomy version is satisfied.

Routing semantics: tasks typed `general_eap` receive generic EAP task-type
expectations only (Domain Pack content), and no type-specific moves or practice
targets.

Explicitly: `general_eap` confers no validity or measurement meaning; it is a
routing label. Tasks that fail (a), (b), or (c) go to `unclassified` - never to
`general_eap` by default. This fixes the previously open "general/EAP scope"
boundary of D-L2-01.

## 8. Constraint 7 - Taxonomy versioning and migration/compatibility

1. **Versioning:** the taxonomy follows SemVer (`vX.Y.Z`), version
   `l2-task-type-taxonomy-v1.0.0` at this contract. Published versions are
   immutable and SHA-256 pinned (consistent with the configuration-version
   machinery; `05_DOMAIN_PACK_BOUNDARY.md`, `06_L2_WRITING_DOMAIN.md` section 4).
2. **Bump rules:** adding a task type = minor; changing classification criteria,
   trigger classes, or precedence = major; definitional wording only = patch.
   Classification rules are versioned with the taxonomy, never silently edited.
3. **Single active version:** one taxonomy version is active at a time; activation
   and rollback ride the existing configuration-version machinery.
4. **Write-time record:** every typed task records its `task_type` AND the
   `taxonomy_version` at write time. Records are append-only; old snapshots are
   never rewritten (06 section 4).
5. **Migration:** reclassification of existing records happens ONLY through a
   versioned migration rule with documented rationale and the required
   governance/Researcher approval. No silent re-tagging on read or write.
6. **Compatibility:** consumers of `task_type` must read and honor the recorded
   `taxonomy_version`. A consumer that does not know the recorded version fails
   closed (treats the value as untyped metadata) rather than applying wrong
   semantics.
7. **Registry content:** Domain Pack v1 (when authorized) registers the five
   types plus `legacy_unclassified` under the `l2` namespace via the existing
   `TaskTypeRegistry` mechanism (`app/shared/task_type_registry.py`); this
   contract is the content authority that unblocks that registration.
   Registry-content tests per namespace apply (D-26; `tests/shared/test_domain_packs.py`).

## 9. Boundaries and non-claims (checklist)

- [x] NOT a proficiency/mastery/ability/learning-gain/measurement taxonomy.
- [x] No learner classification, ordering, or trait attribution.
- [x] No comparability participation until the legacy-mapping decision (D-22).
- [x] No practice/feedback/measurement semantics introduced by this contract.
- [x] No Domain Pack v1 implementation; no product code changes.
- [x] `genre` free text and all legacy rows remain untouched.
- [x] ADR-07 practice/formative-diagnostic/research/protected-evaluation
      separation is preserved; nothing here adds a measurement layer.
- [x] Task-type expectations (moves, paragraphing, diagnosis mapping, practice
      target codes, locale keys) are Domain Pack v1 CONTENT decisions, blocked
      until the remaining L2 prerequisites resolve - not part of this contract.

## 10. Still open (not resolved by this contract)

- D-L2-02 `task_type` persisted column vs derived value (`NR`).
- D-L2-09 zh_CN naming/ordering for the five labels (parity contract applies).
- D-L2-10 typed task-type picker in the Student UI (deferred).
- Validity evidence for the taxonomy: required before ANY measurement use; none is
  claimed or produced here.

## 11. Evidence references

- `program-control/USER_DECISION_BRIEF.json` - UD-01 (five-type enumeration,
  recommended option).
- `program-control/qualified-adrs/ADR-07-evaluation-taxonomy.json` - versioned
  taxonomy; no mastery semantics.
- `docs/architecture/writing-intelligence-platform/14_ARCHITECTURE_DECISIONS.md` -
  D-04 (namespace-scoped TaskTypeRegistry), D-22 (metadata-only; legacy
  sentinel; behavior-diff test), D-26 (registry content layout), D-29 (version
  single-sourcing scope).
- `docs/architecture/writing-intelligence-platform/06_L2_WRITING_DOMAIN.md` -
  enumeration, genre backward compatibility, legacy-genre reconciliation
  (sections 3, 4, 6).
- `docs/departments/shared-platform-core/h1/03_VERSIONING_CONTRACT.md` -
  independent subsystem version streams.
- `docs/departments/shared-platform-core/h1/05_DOMAIN_PACK_BOUNDARY.md` -
  pack layout, manifest fields, blocked content.
- `docs/departments/research-evaluation-governance/foundation/07_MEASUREMENT_CLAIM_POLICY.md`
  - permitted/prohibited statement classes.
- `app/shared/task_type_registry.py` - registry mechanism and `legacy_unclassified`
  sentinel.
- `app/configuration/domain_packs/l2/v0.1.0/manifest.json` - H1 pack with blocked
  content lists.

*Persisted by the L2 execution agent under Goal L2-DOMAIN-TAXONOMY-CONTRACT,
2026-08-09. Contract work only; no Domain Pack v1 implementation.*
