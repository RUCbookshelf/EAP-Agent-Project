# D-22 Legacy-Genre Mapping Manifest — PROPOSAL + Impact Analysis

**Proposal id:** `D-22-LEGACY-GENRE-MAPPING-PROPOSAL-001`
**Goal:** `L2-EVIDENCE-PREP`
**Date:** 2026-08-09
**Owner:** L2 Writing Domain
**Baseline:** `5aafe2728d7135212bd675a6975b44bcf99ee099`
**Branch / Worktree:** `dept/l2-writing` / `A:\EAP Agent Project\worktrees\l2-writing`
**Status:** **PROPOSAL ONLY**. The D-22 legacy-mapping decision is a data-governance
decision owned by Research Evaluation + L2 (same document); PROGRAM does not infer
this approval. This proposal does NOT approve the mapping, does NOT implement
Domain Pack v1, does NOT change product behavior, and does NOT touch
`discourse_organization` (UD-02 DEFER).
**Contract anchors:** `docs/domain/L2_TASK_TYPE_TAXONOMY_CONTRACT.md` Constraints 4
(§5) and 5 (§6); `docs/architecture/writing-intelligence-platform/06_L2_WRITING_DOMAIN.md`
§3.1, §4, §6; architecture decision D-22; decision record D-L2-02.

---

## 1. Scope and boundary

This proposal defines the shape of the approved, versioned mapping manifest that
maps **legacy rows** (free-text `genre`, no `task_type`) to either a `task_type`
or the `legacy_unclassified` sentinel.

* **Explicit-only:** a legacy `genre` maps ONLY through an approved, versioned
  mapping manifest that records per-row or per-genre rule id, rationale, and
  evidence (contract §5.1). No inference from string similarity, substring
  matches, or taxonomy definitions.
* **Metadata-only:** the mapping assigns no proficiency, difficulty, or
  measurement meaning; `task_type` participates in NO comparability predicate
  until the D-22 behavior-diff gate passes (contract §0, §9; D-22).
* **Write-time only:** mapping is applied once at write time with full provenance
  (D-L2-02); reads never re-map; records are append-only.

## 2. Legacy genre vocabulary — inventory (from product sources, verified 2026-08-09)

The `genre` column is free text (`genre TEXT NOT NULL`). The product's only
registration surface is the Student Writing page selectbox
(`app/ui/features/student/writing.py:233-236`) with three options, defined by
locale keys present since v0.8.1 (`git log -S '"genre_narrative"' -- locales/` →
`f43ab28`):

| Locale key | en display string (stored) | zh_CN display string (stored) |
| --- | --- | --- |
| `genre_argumentative` | `argumentative essay` | `议论文` |
| `genre_expository` | `expository essay` | `说明文` |
| `genre_narrative` | `narrative essay` | `记叙文` |

Important: the selectbox stores the **localized display string**, so legacy rows
may contain either the English or the Chinese string for the same option.
Because the column is free text, arbitrary values may also exist in the real
database. The real DB distribution is **UNKNOWN at proposal time**: the worktree
contains no governed database snapshot (`data/` holds only demo JSON), and raw
SWECCL was not accessed and is not a substitute (corpus genres are not product
legacy genres).

**Prerequisite (named, not resolved):** a governed snapshot of the real legacy
`essays` table (product DB) with a documented snapshot procedure is required
before the manifest is finalized (census, coverage check, and the D-22
behavior-diff test all depend on it). Research Evaluation + PROGRAM name the
snapshot authorization.

## 3. Proposed explicit mapping table (rules M0–M4)

Matching key = exact value after the taxonomy's normalization discipline
(casefold + strip + whitespace/punctuation normalization, contract §2.2). No
substring, no similarity, no taxonomy-definition inference (contract §5.1).
Locale-distinct rule entries are explicit.

| Rule id | Normalized value | Locale | Mapping | Reason code | Rationale / evidence |
| --- | --- | --- | --- | --- | --- |
| M1 | `argumentative essay` | en | `argumentative` | (typed) | Product option `genre_argumentative` was the declared task metadata for argumentative writing; mapping records the genre's documented meaning to the same-named taxonomy type (contract §1; `locales/en.json`; `writing.py:233-236`; demo data `data/demo_students.json`) |
| M1-zh | `议论文` | zh_CN | `argumentative` | (typed) | Same option in zh_CN (`locales/zh_CN.json`); matches existing `genre_argumentative` = 议论文 usage |
| M2 | `expository essay` | en | `legacy_unclassified` | `no_mapping_rule` | Explicit no-map decision: contract §5.2 names `expository` as a genre without a documented mapping rule; no five-type definition covers exposition. Open consideration DP-1 (see §7) |
| M2-zh | `说明文` | zh_CN | `legacy_unclassified` | `no_mapping_rule` | Same decision, zh_CN form |
| M3 | `narrative essay` | en | `legacy_unclassified` | `no_mapping_rule` | Contract §5.2 names `narrative` as a genre without a documented mapping rule; no five-type definition covers narration |
| M3-zh | `记叙文` | zh_CN | `legacy_unclassified` | `no_mapping_rule` | Same decision, zh_CN form |
| M4 | (empty / missing) | any | `legacy_unclassified` | `missing_genre` | Defensive explicit rule; schema is NOT NULL but free text may be empty in practice |
| M0 | (any other value) | any | `legacy_unclassified` | `no_mapping_rule` | Default rule: no approved rule exists → sentinel, never guessed (contract §5.2, §6.2) |

Notes on rule M1: the mapping relies on the *declared genre* semantics, not on
re-analysis of legacy prompt text. A legacy row declared as `argumentative essay`
may still have a prompt that would classify differently under the taxonomy; this
is an accepted, documented property of genre-level mapping (the manifest records
this caveat as part of the rule rationale). Rows where the stored prompt
unambiguously matches another type may be handled through a row-level rule if
Research Evaluation requests that path (DP-2, §7).

## 4. Precedence / ambiguity rules for the mapping

1. **Exact-match only.** A value matches a rule iff the normalized value equals
   the rule's normalized value exactly (locale-aware). No substring/similarity.
2. **Disjoint coverage.** The manifest validates that approved rules have disjoint
   normalized values; duplicate coverage is a manifest validation error and the
   manifest version is rejected.
3. **Row-level overrides (if approved).** An explicitly recorded row-level rule
   (R-class, with rationale + evidence + approval reference) takes precedence over
   the genre-level rule for that exact row; otherwise the genre-level rule applies.
   Row-level rules are the ONLY path by which a legacy row may gain a type that
   differs from its genre-level outcome.
4. **No match → sentinel.** Any value without an approved rule → `legacy_unclassified`
   with reason code `no_mapping_rule` (M0). Two applicable rules for one row
   (manifest data error) → `legacy_unclassified` with reason code
   `mapping_rule_conflict`; never a silent choice.
5. **No `general_eap` from genre.** `general_eap` is never assigned from genre
   alone (contract §7(c)); it requires the affirmative conditions, which legacy
   rows cannot be re-verified for without a row-level review.
6. **Write-time only.** Mapping applies at write time with manifest version, rule
   id, and approval reference recorded (D-L2-02; contract §5.5, §8.4). Reads never
   re-map; rows are append-only.

## 5. Affected contracts — impact analysis

| Contract / artifact | Current state | Impact if this proposal is approved | Impact if not approved |
| --- | --- | --- | --- |
| `docs/domain/L2_TASK_TYPE_TAXONOMY_CONTRACT.md` (§5, §6) | Mapping manifest required; sentinel semantics fixed | The approved manifest becomes the named D-22 artifact; sentinel usage governed by M0–M4 | Contract unchanged; `legacy_unclassified` remains the default for all legacy rows |
| `06_L2_WRITING_DOMAIN.md` (§3.1, §4, §6) | Substring inference must not survive; genre stays free text | Typed writes for legacy rows become governed; `genre` untouched | Unchanged |
| `14_ARCHITECTURE_DECISIONS.md` D-22 | Metadata-only; comparability freeze; behavior-diff test required | `task_type` gains approved legacy values; comparability STILL frozen until behavior-diff gate passes | Unchanged |
| D-L2-02 persistence record | Additive columns design; sentinel written only via approved manifest | Manifest is the only sanctioned writer of typed/sentinel values for legacy rows | Unchanged |
| `app/shared/task_type_registry.py` | Mechanism + `legacy_unclassified` sentinel registered | No mechanism change; registry content ships only in the Domain Pack v1 implementation Goal | Unchanged |
| `app/configuration/domain_packs/l2/v0.1.0/manifest.json` | `supported_task_types: []` (NR — blocked by D-L2-01) | No change from this proposal; manifest content is a Domain Pack v1 implementation item | Unchanged |
| `app/services/learner_model.py:332-345` (`_cluster_key`) | Substring purpose inference present (must not survive) | Mapping is metadata-only; the inference itself is removed only in a separately gated implementation Goal with the D-22 behavior-diff test | Unchanged (inference remains, but no comparability change occurs either way) |
| `app/learner/history.py::_classify` | Exact `genre` equality in comparability | Unchanged: `task_type` is not in any comparability predicate under this proposal | Unchanged |
| Locale parity contract (D-L2-09; 600/600 keys) | `genre_*` keys distinct from `task_type_*` keys | No locale change; `task_type_*` keys arrive with the Domain Pack v1 + UX implementation Goal | Unchanged |
| Measurement-claim policy | No claim surface for task types | Mapping is metadata-only; no statement class touched | Unchanged |
| Research data export / research schema | `genre` exported as free text | `task_type` becomes an additive export field only in a later implementation Goal | Unchanged |
| `tests/shared/test_domain_packs.py` | Asserts empty H1 content lists | No test change from this proposal; content updates belong to the implementation Goal | Unchanged |

**Impact summary:** zero product behavior change results from this proposal.
Approval unblocks only the D-22 data-governance lane (the mapping decision itself).
It does NOT unblock Domain Pack v1, does NOT change comparability, does NOT change
any registry, locale, API, or UI surface.

## 6. Rollback

* **Proposal phase:** rejection or edits require no rollback — no artifact is
  applied; this document and the draft manifest remain the record of the proposal.
* **Approved-manifest phase:** the manifest is versioned data (SemVer; immutable
  versions, SHA-256-pinned per the configuration-version machinery, D-26/D-29).
  Deactivation/rollback rides the existing configuration-version machinery:
  stop applying the new version; prior versions remain readable and applicable.
* **Row-level rollback:** rows written under a manifest version are append-only
  and never rewritten; disabling the feature leaves typed values readable as
  untyped metadata (D-L2-02 §5).
* **Comparability rollback boundary:** no comparability participation until the
  D-22 behavior-diff test over a real-legacy-DB snapshot passes (plus the D-30
  zero-change gate); the gate itself is the rollback boundary — if the
  behavior-diff fails, the mapping stays metadata-only with no predicate change.
* No destructive migration and no backfill are proposed anywhere in this document.

## 7. Decision points for Research Evaluation + L2 (NOT resolved here)

* **DP-1 — `expository` disposition.** Recommended: `legacy_unclassified` for v1
  (per contract §5.2's explicit naming of `expository` as unmapped), re-examined
  after the validation studies (V1/V3 in the validity-evidence package) produce
  coverage evidence. Alternative: map `expository essay` to `general_eap` under
  contract §7 conditions — needs an explicit rationale + evidence, and would be a
  separate rule amendment.
* **DP-2 — row-level override path (R-class rules).** Recommended: defer to v2 of
  the manifest; keep M0–M4 closed for v1 so coverage is fully determinable from
  the census.
* **DP-3 — validation targets.** Confirm the kappa ≥ 0.80 / ≥ 90% agreement
  targets and sample sizes proposed in the validity-evidence package before V2
  runs.
* **DP-4 — snapshot authorization.** Name the governed snapshot procedure for the
  real legacy `essays` table (required for census + behavior-diff).

## 8. Evidence references

* `docs/domain/L2_TASK_TYPE_TAXONOMY_CONTRACT.md` — §1, §2.2, §5 (Constraint 4), §6 (Constraint 5), §7, §8.4.
* `docs/architecture/writing-intelligence-platform/06_L2_WRITING_DOMAIN.md` — §3.1, §4, §6, §7.
* `docs/architecture/writing-intelligence-platform/14_ARCHITECTURE_DECISIONS.md` — D-22, D-26, D-29, D-30.
* `docs/domain/D-L2-02_TASK_TYPE_PERSISTENCE_DECISION.md` — §1, §4, §5.
* `app/shared/task_type_registry.py` — `legacy_unclassified` sentinel.
* `app/ui/features/student/writing.py:233-236` — genre selectbox (stores localized strings).
* `locales/en.json`, `locales/zh_CN.json` — `genre_*` keys.
* `app/services/learner_model.py:332-345` — substring inference that must not survive.
* `app/learner/history.py:90-109` — exact-genre comparability predicate (unchanged by this proposal).
* `app/configuration/domain_packs/l2/v0.1.0/manifest.json` — H1 empty pack.
* `tests/shared/test_domain_packs.py` — H1 content assertions.
* Companion artifact: `docs/domain/D-22_legacy_genre_mapping_manifest.proposal.json` (machine-readable draft).

## 9. Honest-state declaration

This is a proposal, not an approval. The mapping table is explicit-only, the
real-DB distribution is unverified until a governed snapshot exists, and no
product behavior, comparability, registry, or measurement semantics change under
this proposal. `discourse_organization` remains excluded.

*Produced by the L2 execution agent under Goal L2-EVIDENCE-PREP, 2026-08-09.
Proposal only; no approval implied.*
