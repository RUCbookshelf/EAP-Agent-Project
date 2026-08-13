# D-L2-10 Decision Record — typed task-type picker in the Student UI (scope/placement)

**Decision id:** `D-L2-10`
**Goal:** L2-PREREQ-REMAINING
**Date:** 2026-08-09
**Status:** RESOLVED (scope/placement decision; **NO UI implementation**)
**Owner:** L2 Writing Domain
**Baseline:** `5aafe2728d7135212bd675a6975b44bcf99ee099`
**Branch:** `dept/l2-writing`
**Prior status:** `Unclear` — "typed task-type picker in the UI (deferred beyond this Goal)"
(`06_L2_WRITING_DOMAIN.md` section 7)

---

## 1. Decision

A typed task-type picker is **deferred**: it is not implemented in this Goal
and not part of Domain Pack v1 content authoring. When a future, separately
authorized implementation Goal builds it, its scope and placement are fixed as
follows:

1. **Placement — Student Writing page only, independent tasks only.** The
   picker appears in the task-metadata section of the Student Writing page
   (`app/ui/features/student/writing.py`, alongside the existing `genre`
   selectbox) for **new independent tasks** (first drafts). It declares the
   task type as task metadata at registration.
2. **Linked revisions inherit; no re-picker.** A linked revision
   (`revision_of_submission_id` set) inherits the source submission's
   `task_type`; the picker is not offered for revisions. Practice and Revision
   surfaces never host a picker — practice targets already resolve their task
   context from the source submission (`app/practice/task_context.py`).
3. **Declared, then server-validated.** The picker provides **declared task
   metadata**; the deterministic classifier validates the declaration at
   task-registration time (contract Constraint 1.1). Client declaration never
   overrides server-side classification; the mismatch outcome (explicit
   `unclassified` with reason code vs rejection) is Domain Pack v1 content —
   not resolved here (mirrors the D-36 domain/language advisory posture in
   `docs/departments/shared-platform-core/h1/02_DOMAIN_LANGUAGE_CONTRACT.md`).
4. **Honest states, never types.** `legacy_unclassified` and `unclassified`
   are NOT selectable options. Records without a typed value render an honest
   "unclassified" state, never a guessed type (contract §6.4).
5. **Fixed non-hierarchical order.** The picker lists the five types in the
   canonical display order fixed by D-L2-09, identical in en and zh_CN; no
   difficulty/proficiency ordering.
6. **`genre` remains.** The free-text `genre` selectbox/field stays for
   backward compatibility; the picker is additive.

## 2. Scope boundary (this Goal)

- NO UI implementation, NO API change, NO locale change, NO registry
  registration, NO product behavior change.
- The picker's prerequisites are: (a) Domain Pack v1 registry content
  (five types + locale keys per D-L2-09) authorized; (b) the Cross-Department
  Contract Gate for registry/domain-pack content (UX owns the surface, L2 owns
  task semantics/labels, CORE owns the registry mechanism); (c) locale parity
  tests extended to the new keys; (d) frozen v0.9.7-D design system preserved
  (no token/CSS change).

## 3. Placement rationale

- The task-metadata section of the Writing page is the only surface where a
  task is first defined; revision and practice flows already derive their task
  context from the source submission, so a picker there would be redundant or
  contradictory (a revision cannot change the task type).
- Keeping the picker additive to `genre` preserves all legacy behavior
  (compatibility rule, `06_L2_WRITING_DOMAIN.md` section 4) and lets
  `task_type` remain optional metadata (D-22).
- Honest unclassified rendering (item 4) is required by the taxonomy contract
  and by the measurement-claim policy's prohibition on guessed classification
  (contract §5, §6).

## 4. Non-claims and boundaries

- No picker exists today: `task_type` appears only in the registry mechanism
  (`app/shared/task_type_registry.py`), the empty pack manifest
  (`app/configuration/domain_packs/l2/v0.1.0/manifest.json`), and the domain
  enum — no persistence column, no API field, no UI surface (verified 2026-08-09).
- This record does not implement Domain Pack v1, does not change the Student
  UI, does not alter the frozen design system, and does not add measurement or
  evaluation semantics.

## 5. Evidence references

- `docs/domain/L2_TASK_TYPE_TAXONOMY_CONTRACT.md` — Constraints 1.1, 5.5, 6.4;
  section 9 (typed pickers out of scope).
- `docs/architecture/writing-intelligence-platform/09_FRONTEND_WORKFLOW_ARCHITECTURE.md` —
  frozen Student design system; shared vs domain-specific surface rule.
- `docs/architecture/writing-intelligence-platform/06_L2_WRITING_DOMAIN.md` —
  sections 4, 7 (D-L2-10 deferred).
- `app/ui/features/student/writing.py` — current task-metadata section (genre
  selectbox location).
- `app/practice/task_context.py` — source-submission task context for practice.
- `docs/departments/shared-platform-core/h1/02_DOMAIN_LANGUAGE_CONTRACT.md` —
  advisory-field posture (D-36 pattern).

*Decision record produced by the L2 execution agent under Goal
L2-PREREQ-REMAINING, 2026-08-09. Bounded record; no implementation.*
