# L2 Domain Pack v1 Content Record (G5 trigger dictionaries + conflict-pair table)

**Content id:** `l2-domain-pack-v1-content-001`
**Goal:** `L2-DOMAIN-PACK-V1`
**Date:** 2026-08-09
**Owner:** L2 Writing Domain
**Authorization:** `program-control/researcher-decisions/DOMAIN-PACK-V1-conditional-auth.json`
(CONDITIONALLY AUTHORIZED, 2026-08-09; conditions satisfied: D-22 qualified,
DP-4 census acceptable, V1 adjudication resolved, D-L2-02/09/10 records)
**Baseline:** `09264abbd93cdc6b62b83cefd94b3b640319ac9b`
**Pack content location:** `app/configuration/domain_packs/l2/v1.0.0/`

---

## 1. What ships in this record

Domain Pack v1 content is versioned JSON data under the `l2/v1.0.0` pack
namespace (D-26 layout), consumed by two deterministic L2 services:

| Pack file | Content | Consumer |
| --- | --- | --- |
| `manifest.json` | Pack identity, five `supported_task_types`, availability, content status | `app/configuration/domain_packs_loader.py` |
| `task_types.json` | Five-type definitions, en/zh_CN label pairs (D-L2-09), canonical display order | registry content parity + locale parity tests |
| `trigger_dictionaries.json` | G5 trigger dictionaries (per-type groups, en + zh_CN) and composition rules | `app/services/task_type_classifier.py` |
| `conflict_pairs.json` | G5 conflict-pair table (comparable-strength conflicts) | `app/services/task_type_classifier.py` |
| `legacy_genre_mapping.json` | Qualified D-22 manifest v1.0.0 (embedded, provenance-preserving) | `app/services/legacy_genre_mapping.py` |

Runtime registration: `app/shared/task_type_registry.py::default_task_type_registry`
registers the five types plus the `legacy_unclassified` sentinel under the
`l2` namespace (taxonomy contract §8.7; D-04/D-26).

## 2. G5 trigger dictionaries - content decisions

### 2.1 Matching semantics

- Normalization: NFC + casefold + strip + Unicode-whitespace collapse; no
  punctuation stripping (taxonomy contract Constraint 1.2 discipline; same as
  the frozen corpus features and the D-22 census).
- English phrases: word-boundary phrase matching (e.g. `opinion` never matches
  inside `opinions`); phrase-internal whitespace matches any whitespace run.
- zh_CN phrases: substring matching; content validation enforces
  multi-character phrases only (length >= 2) because Chinese has no word
  boundaries.
- Locale-agnostic matching: both dictionaries are matched against the same
  normalized prompt; a mixed-script prompt matches both.
- No model output, no LLM judgment, no probabilistic scoring at classification
  time (Constraint 1.2; A-8: machine detection is dictionary-based G5 content).

### 2.2 Per-type composition rules (full-match predicates)

| type | full match |
| --- | --- |
| `problem_solution` | `cause_or_solution_mandate` present AND (`problem_naming` present OR `topic_referencing` present) |
| `argumentative` | (`stance_mandate` present OR `opinion.viewpoint_request` present) AND `evidence_mandate` present |
| `discussion` | `balanced_multiperspective` present |
| `opinion` | `viewpoint_request` present AND `argumentative.evidence_mandate` absent |
| `general_eap` | `eap_affirmative` present AND no specific-type full match (§7 (a)+(b); (c) is the version-binding hook, A-5) |

The `argumentative` stance component reuses the `opinion.viewpoint_request`
group because the contract (§3) treats a viewpoint request as the position
when an evidence mandate is present ("stance + evidence mandate wins").

### 2.3 G5 content decisions recorded (with rationale)

1. **Type-name genre labels are not request triggers.** `"opinion essay"` or
   `"argumentative essay"` inside a prompt is free-text genre vocabulary, not
   a viewpoint/stance/evidence request. A prompt that names a type without
   the request phrases classifies per the request dictionaries (e.g.
   `"Write an argumentative essay about X."` -> `general_eap` when
   EAP-affirmative). A-8 assigns machine detection of "mandated" to G5
   content; this is the v1 reading. The D-22 manifest separately governs
   DECLARED genre metadata for legacy rows (explicit-only).
2. **Effects do not extend `problem_solution` (A-7 closed class).**
   `"What are the effects of X?"` never matches (effects are not
   cause/solution content); it falls to `general_eap` if EAP-affirmative,
   else `unclassified`. `"What are the causes and effects of X?"` matches
   because cause content is present; the class is not extended.
3. **Cause/solution constructions name their complement as the problem.**
   `topic_referencing` phrases (e.g. `"causes of"`, `"how to solve"`,
   `"solutions to"`) satisfy the problem-naming component, per A-4's example
   (`"Take a position on the causes of X..."` -> `problem_solution`).
   Documented approximation: `"causes of success"`-type prompts classify
   `problem_solution` although the complement is not a canonical problem;
   accepted and recorded, never inferred beyond the dictionary.
4. **`"reasons for"` is excluded from cause triggers.** It overlaps the
   argumentative evidence vocabulary (`"give reasons for your opinion"`);
   cause-questions are served by the `"causes of"` family. Documented
   conservative boundary; such prompts fall through the chain.
5. **EAP-affirmative vocabulary is academic-register, not generic writing.**
   `essay/paragraph/composition/academic/assignment/paper/...` (en) and
   `文章/作文/论文/短文/段落/学术/写作/...` (zh_CN). `"Write a story about
   your holiday."` is NOT EAP-affirmative -> `unclassified` (`not_eap`).
6. **Declared task metadata validation (D-L2-10 posture).** A declared
   `task_type` that is not one of the five ids is REJECTED
   (`TaskTypeClassificationError`); a valid declared id that disagrees with
   the prompt-derived typed outcome yields `unclassified` with reason code
   `declared_type_mismatch` (no coercion, Constraint 6). When the
   prompt-derived outcome is already `unclassified`, the honest reason is
   preserved and the declaration is recorded in provenance. The picker
   consumer is deferred (D-L2-10); this path is dormant until it ships.

## 3. G5 conflict-pair table - content decisions

- v1 enumerates exactly ONE comparable-strength conflict pair:
  `(argumentative, discussion)` - the canonical contract example (A-3).
- A prompt whose fully-matched type set contains any enumerated pair is
  `unclassified` with reason code `ambiguous_precedence_conflict`; no silent
  choice is made (Constraint 3 application rule 2).
- All other pairs resolve by the chain `problem_solution` >
  `argumentative` > `discussion` > `opinion` > `general_eap`:
  - `discussion` + `opinion` is chain-resolved, not a conflict (A-1/A-2:
    balanced-treatment subsumes the viewpoint request);
  - `problem_solution` + `argumentative` is chain-resolved (A-4:
    content-anchoring outranks the rhetorical mandate).

## 4. D-L2-09 zh_CN labels and canonical display order

Canonical display order (contract §1 table order; editorial, non-hierarchical;
the classification precedence chain must never be used as display order):

| order | task_type id | en (locale key) | zh_CN (locale key) |
| --- | --- | --- | --- |
| 1 | `opinion` | Opinion Essay | 观点类作文 |
| 2 | `argumentative` | Argumentative Essay | 议论文 |
| 3 | `discussion` | Discussion Essay | 讨论类作文 |
| 4 | `problem_solution` | Problem-Solution Essay | 问题解决类作文 |
| 5 | `general_eap` | General EAP | 通用学术写作 |

Locale keys `task_type_*` are added to BOTH `locales/en.json` and
`locales/zh_CN.json` in one change (parity count 600/600 -> 605/605,
D-L2-09 §4.1); labels are parity translations with no ordering, difficulty,
or measurement implication.

## 5. Legacy mapping (D-22 manifest, explicit-only)

The qualified manifest (`l2-legacy-genre-mapping-v1.0.0`, QUALIFIED
2026-08-09) is embedded in the pack with full provenance (approvals RD-D22 /
DP-4, rule version, census summary, non-claims). `map_legacy_genre` applies
exact normalized-value matching only:

- `argumentative essay` / `议论文` -> `argumentative` (M1 / M1-zh);
- `expository essay` / `说明文`, `narrative essay` / `记叙文` ->
  `legacy_unclassified` (`no_mapping_rule`) - explicitly NOT mapped;
- empty/missing -> `legacy_unclassified` (`missing_genre`, M4);
- anything else -> `legacy_unclassified` (`no_mapping_rule`, M0 default).

No substring, similarity, or taxonomy-definition inference; `general_eap` is
never assigned from genre alone; every outcome records manifest id, rule id,
reason code, and approval references for write-time provenance (D-L2-02).

## 6. What this content is NOT

- NOT a proficiency/mastery/ability/learning-gain/measurement taxonomy
  (contract §0; measurement-claim policy).
- NOT a comparability predicate: `task_type` participates in no comparability
  predicate here; the D-22 behavior-diff gate (over the DP-4 census snapshot)
  and the D-30 zero-change gate are the rollback boundary before any future
  comparability change.
- NOT a schema migration: D-L2-02 additive columns are a separate CORE-owned
  lane (design note: `docs/domain/D-L2-02_MIGRATION_14_DESIGN_NOTE.md`).
- NOT a UI picker (D-L2-10 deferred) and NOT a discourse_organization
  dimension (EXCLUDED, CANDIDATE/INSUFFICIENT_EVIDENCE, UD-02 DEFER).

*Produced by the L2 execution agent under Goal L2-DOMAIN-PACK-V1, 2026-08-09.
Content decision record; pack content is the machine authority, this record
is the rationale.*
