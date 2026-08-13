# L2-EVIDENCE-PREP — Bounded Evidence/Proposal Report

**Goal:** `L2-EVIDENCE-PREP` — taxonomy validity-evidence preparation + D-22
legacy-genre mapping manifest PROPOSAL (evidence/proposal-only; no approval).
**Date:** 2026-08-09
**Owner:** L2 Writing Domain
**Starting SHA:** `5aafe2728d7135212bd675a6975b44bcf99ee099`
**Branch / Worktree:** `dept/l2-writing` / `A:\EAP Agent Project\worktrees\l2-writing`
**Verdict:** GREEN (deliverables complete; proposals only; no product change;
no researcher-labelled items resolved — review items explicitly deferred)

## 1. Preflight (verified)

* Git root = authorized worktree; branch = `dept/l2-writing`; HEAD = promoted
  baseline `5aafe27`; worktree list matches `WORKTREE_REGISTRY.md`.
* Pre-existing untracked files (`docs/domain/` records, three `docs/integration/`
  records, `handoff.json`) preserved untouched.
* Program artifacts read: `WORKSTREAM_REGISTRY.json`, `PROGRAM_STATUS.md`,
  `DEPENDENCY_GRAPH.md`, `PROMOTION_HISTORY.md`, `WORKTREE_REGISTRY.md`,
  dispatch record, context bundle, `USER_DECISION_BRIEF.json`,
  `schemas/handoff.schema.json`.
* Taxonomy contract (Section 10), D-L2-02/09/10 decision records, and the
  discourse-organization feasibility spike read in full.

## 2. Deliverables delivered

| # | Deliverable | Artifact |
| --- | --- | --- |
| 1 | Taxonomy validity-evidence package (inventory of existing evidence, gaps, proposed bounded validation plan per contract §10) | `docs/domain/L2_TAXONOMY_VALIDITY_EVIDENCE_PACKAGE.md` |
| 2 | D-22 legacy-genre mapping manifest PROPOSAL + impact analysis (explicit-only mapping table M0–M4, precedence/ambiguity rules, affected contracts, rollback, decision points) | `docs/domain/D-22_LEGACY_GENRE_MAPPING_PROPOSAL.md` |
| 3 | Machine-readable draft manifest (proposal) | `docs/domain/D-22_legacy_genre_mapping_manifest.proposal.json` |
| 4 | This report | `docs/integration/L2_EVIDENCE_PREP_REPORT.md` |

## 3. Key findings

* **No empirical validity evidence exists for the five-type taxonomy.** Only
  definitional (contract §1/§3/§4/§7) and governance (UD-01, ADR-07, D-04/D-22/
  D-26/D-29, D-L2-09) records exist; a repository-wide search for validity,
  rater, kappa, expert-review, and psychometric evidence found only explicit
  "none is claimed" statements (contract §10; D-L2-09 §5; L2-PREREQ-REMAINING
  report). The package inventories this state and proposes four bounded studies
  (V1 content review, V2 classification agreement, V3 coverage census, V4
  ambiguity adversarial set) with explicit reliability targets (procedural
  determinism; kappa ≥ 0.80 proposal) and explicit non-goals (no psychometric
  program; no measurement unblocking).
* **Legacy genre vocabulary is known from product sources but the real-DB
  distribution is not.** The only registration surface is the Student Writing
  selectbox (3 options × en/zh_CN localized display strings; locale keys stable
  since v0.8.1). Because `genre` is free text and the selectbox stores localized
  strings, the manifest uses explicit per-locale exact-value rules (M1–M4) plus a
  default sentinel rule (M0). A governed snapshot of the real legacy `essays`
  table is a named prerequisite (census + D-22 behavior-diff); no snapshot exists
  in the worktree and raw SWECCL was not accessed.
* **Mapping proposal is explicit-only and behavior-neutral.** No substring/
  similarity inference (contract §5.1); `expository`/`narrative` → sentinel with
  documented rules; `general_eap` never assigned from genre; row-level overrides
  deferred (DP-2). Approval would unblock only the D-22 data-governance lane —
  not Domain Pack v1, not comparability (behavior-diff gate stays).
* **Four decision points deferred to Research Evaluation + L2** (DP-1 expository
  disposition; DP-2 row-level path; DP-3 validation targets; DP-4 snapshot
  authorization). They are surfaced via the proposal documents for PROGRAM
  tracking; this Goal does not resolve them and does not block on a Researcher
  answer (`researcher_decision_required=false` per dispatch semantics).

## 4. Verification

| Check | Result |
| --- | --- |
| Preflight identity (root/branch/HEAD/worktree) | PASS |
| Validity-evidence package created under `docs/domain/` | PASS (154 lines; §10-anchored) |
| D-22 mapping proposal created under `docs/domain/` | PASS (explicit table M0–M4; precedence; contracts; rollback) |
| Machine-readable draft manifest valid JSON | PASS (parsed with PowerShell `ConvertFrom-Json`) |
| Integration report created under `docs/integration/` | PASS (this file) |
| No product/behavior change (no `app/`, `locales/`, `tests/`, `data/` edits; docs only) | PASS |
| No approval of taxonomy validity or D-22 mapping issued | PASS (documents state PROPOSAL ONLY) |
| `discourse_organization` excluded; raw SWECCL untouched | PASS |
| Handoff JSON valid against `schemas/handoff.schema.json` | PASS |

## 5. Dependencies

Unlocked (proposal lanes ready for review): taxonomy validity-evidence package +
D-22 mapping proposal now exist as reviewable artifacts; the L2 prerequisite
"legacy-genre mapping manifest (Research Evaluation + L2)" and "taxonomy validity
evidence" items are unblocked for the review step only.

Remaining (tracked by PROGRAM; outside this Goal):

* D-22 mapping decision approval (Research Evaluation + L2 data-governance).
* Taxonomy validity approval + validation study execution (V1–V4) under a future
  Goal.
* Governed snapshot authorization for the real legacy `essays` table (DP-4).
* Domain Pack v1 implementation authorization (separately gated; excludes
  `discourse_organization`).

## 6. Boundaries honored

Proposals only; no approval; no Domain Pack v1 implementation; no product code;
no UI/locale/registry/migration change; no comparability change; no push/PR;
nothing written outside the L2 worktree; raw SWECCL untouched; pre-existing
untracked files preserved.

*Report produced by the L2 execution agent under Goal L2-EVIDENCE-PREP,
2026-08-09.*
