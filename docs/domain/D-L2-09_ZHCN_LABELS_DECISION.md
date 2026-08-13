# D-L2-09 Decision Record — zh_CN naming/ordering for the five taxonomy labels

**Decision id:** `D-L2-09`
**Goal:** L2-PREREQ-REMAINING
**Date:** 2026-08-09
**Status:** RESOLVED (proposal + ordering documented; final copy lands with Domain Pack v1 locale keys)
**Owner:** L2 Writing Domain
**Baseline:** `5aafe2728d7135212bd675a6975b44bcf99ee099`
**Branch:** `dept/l2-writing`
**Prior status:** open — "zh_CN naming/ordering (parity contract applies)"
(`06_L2_WRITING_DOMAIN.md` section 7)

---

## 1. Decision

1. **Naming scheme:** each of the five types carries one canonical label pair
   (en from the taxonomy contract, zh_CN proposed below), stored as locale keys
   with the `task_type_` prefix. The zh_CN labels follow the existing Student
   UI style (compare `genre_argumentative` = 议论文 in `locales/zh_CN.json`)
   and are **parity translations**: same meaning as en, no added ordering,
   difficulty, or measurement implication.
2. **Ordering:** the fixed canonical display order is the taxonomy contract's
   Section 1 table order — `opinion` → `argumentative` → `discussion` →
   `problem_solution` → `general_eap` — used identically in en and zh_CN
   pickers and lists. This order is an **editorial, non-hierarchical** order.
3. **Prohibited ordering:** the classification precedence chain (Constraint 3:
   `problem_solution` → `argumentative` → `discussion` → `opinion` →
   `general_eap`) is a rule for ambiguous-prompt assignment and MUST NOT be
   used as a display order; no difficulty ordering exists anywhere in the
   taxonomy (contract section 0).

## 2. Proposed label pairs

| task_type id | en (contract §1) | zh_CN (proposal) | semantics note |
| --- | --- | --- | --- |
| `opinion` | Opinion Essay | 观点类作文 | personal viewpoint without evidence/counterargument mandate |
| `argumentative` | Argumentative Essay | 议论文 | position + evidence-based argumentation (matches existing `genre_argumentative`) |
| `discussion` | Discussion Essay | 讨论类作文 | balanced multi-perspective, no mandated stance |
| `problem_solution` | Problem-Solution Essay | 问题解决类作文 | named problem + cause/solution content |
| `general_eap` | General EAP | 通用学术写作 | affirmative generic EAP type (contract §7), never a garbage bucket |

Rationale for the zh_CN forms:

- `议论文` for `argumentative` reuses the translation already verified in the
  bilingual Student UI (`genre_argumentative`), keeping learner-facing
  vocabulary consistent.
- `观点类作文` for `opinion` keeps the opinion/argumentative distinction visible
  in Chinese (viewpoint-only vs argument-with-evidence), matching Constraint 2.
- `讨论类作文` and `问题解决类作文` name the task's required structure rather
  than a learner trait; `通用学术写作` describes the affirmative generic EAP
  type without implying "other"/"unclassified".

These strings are a bounded proposal for the Domain Pack v1 content decision;
exact copy is finalized by L2 with UX parity review at implementation time.
Alternative candidates considered: `论证型议论文` (argumentative), `双边讨论类`
(discussion), `问题—解决类` (problem_solution); the primary forms above are
recommended for brevity and consistency.

## 3. Ordering rationale

- The contract's Section 1 table order is already the published canonical order
  of the five types; reusing it as display order keeps docs, pack content, and
  UI in one sequence and is stable across taxonomy patch releases (Constraint
  7.2 bump rules).
- The order is explicitly non-hierarchical: `opinion` is not "lower" than
  `argumentative` (contract section 3), and no label, position, or sort key may
  imply proficiency, difficulty, or validity. UI pickers render the fixed
  canonical order; sorting by inferred difficulty is prohibited.

## 4. UI implications (documented; NO UI change in this Goal)

1. **Locale keys:** implementation adds `task_type_opinion`,
   `task_type_argumentative`, `task_type_discussion`,
   `task_type_problem_solution`, `task_type_general_eap` to BOTH
   `locales/en.json` and `locales/zh_CN.json` in one change. The parity
   contract is enforced by existing tests — `tests/test_design_tokens_v094a.py`
   (`test_key_parity`), `tests/test_v097d_design_system.py` (600/600 key
   parity), `tests/test_v095c_feature_extraction.py`
   (`test_feature_locale_keys_resolve_and_parity_holds`) — so the key set must
   stay equal and the count moves 600/600 → 605/605 at implementation time.
2. **Pack content:** per `06_L2_WRITING_DOMAIN.md` section 4, locale keys are
   Domain Pack v1 content; the pack registers the five types with display names
   (D-L2-01 resolved via the taxonomy contract), and the UI renders labels from
   the registry/pack via `t()` — the exact label-resolution mechanism is a
   Domain Pack v1 + UX contract decision, not made here.
3. **Non-claims surface:** labels must never be rendered as proficiency,
   difficulty, or validity statements; `unclassified` / `legacy_unclassified`
   states are honest non-type states and are never presented as a sixth type
   (contract §6.4; D-L2-10).
4. No design-system change: labels ride the frozen v0.9.7-D tokens and the
   bilingual `t()` machinery.

## 5. Non-claims and boundaries

- This record proposes naming and ordering only. It does NOT create locale
  files, does NOT register pack content, does NOT implement Domain Pack v1,
  does NOT change the UI, and does NOT claim validity evidence for the
  taxonomy (contract section 10: validity evidence remains a Researcher item).
- The taxonomy's explicit non-claims (contract section 0) bind all label
  wording: no ordering of learners/tasks/types by proficiency.

## 6. Evidence references

- `docs/domain/L2_TASK_TYPE_TAXONOMY_CONTRACT.md` — Section 1 table,
  Constraint 2 (opinion vs argumentative), Constraint 3 (precedence —
  display-prohibited), section 7 (`general_eap`), section 10 (open items).
- `locales/en.json`, `locales/zh_CN.json` — existing genre keys and style
  (`genre_argumentative` = 议论文).
- `tests/test_design_tokens_v094a.py`, `tests/test_v097d_design_system.py`,
  `tests/test_v095c_feature_extraction.py` — locale parity contract tests.
- `app/ui/locale.py` — `t()` / `load_locale` machinery.

*Decision record produced by the L2 execution agent under Goal
L2-PREREQ-REMAINING, 2026-08-09. Bounded record; no implementation.*
