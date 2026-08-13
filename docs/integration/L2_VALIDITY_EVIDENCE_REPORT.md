# L2-VALIDITY-EVIDENCE — V1 + V3 Evidence-Generation Report

**Goal:** `L2-VALIDITY-EVIDENCE` — execute V1 content review; prepare V3
coverage census methodology. Evidence generation only; **no validity claim; no
ratification; no Domain Pack v1 implementation; no product code changes.**
**Date:** 2026-08-09
**Owner:** L2 Writing Domain
**Starting SHA:** `09264abbd93cdc6b62b83cefd94b3b640319ac9b`
**Branch / Worktree:** `dept/l2-writing` / `A:\EAP Agent Project\worktrees\l2-writing`

## 1. Preflight (verified)

* Git root = authorized worktree; branch = `dept/l2-writing`; HEAD = promoted
  baseline `09264ab` (matches Goal Packet `promoted_baseline`); worktree list
  matches `WORKTREE_REGISTRY.md` (L2 canonical at `09264ab`).
* Pre-existing untracked files preserved untouched: `docs/domain/` records,
  `docs/integration/` records (three), `handoff.json`.
* Program artifacts read: `WORKSTREAM_REGISTRY.json`, `PROGRAM_STATUS.md`,
  `DEPENDENCY_GRAPH.md`, `PROMOTION_HISTORY.md`, `WORKTREE_REGISTRY.md`, dispatch
  record, context bundle, `schemas/handoff.schema.json`.
* Taxonomy contract read in full; validity-evidence package read in full;
  D-22 mapping proposal + manifest, D-L2-02/09/10 records, discourse-organization
  spike, measurement-claim policy, `06_L2_WRITING_DOMAIN.md` read as anchors.

## 2. Deliverables delivered

| # | Deliverable | Artifact |
| --- | --- | --- |
| 1 | V1 content review execution: protocol + review records (AX-1..AX-7), findings register, surfaced-ambiguities register (A-1..A-8), honest-state declaration | `docs/domain/L2_VALIDITY_V1_CONTENT_REVIEW.md` |
| 2 | V3 coverage census methodology: data-collection plan (S1/S2), instruments (census protocol C1-C9; feature checklist F01-F17), DP-4 snapshot dependency recorded as NOT authorized / execution NOT_RUN | `docs/domain/L2_VALIDITY_V3_COVERAGE_CENSUS_METHODOLOGY.md` |
| 3 | This report | `docs/integration/L2_VALIDITY_EVIDENCE_REPORT.md` |

## 3. Key findings

* **V1 executed as evidence generation.** All five types + two states reviewed
  against contract §1/§2/§3/§4/§7 with evidence-anchored determinations: 6/10
  type pairs CLEAR, 2/10 PARTIAL, 2/10 AMBIGUOUS; exhaustiveness and the
  no-silent-guess guarantee are explicit (§2.5, §6, §7). Eight contract
  ambiguities surfaced (A-1..A-8) — notably: discussion/opinion boundary with
  "give your own opinion" prompts (A-1); unoperationalized "comparable strength"
  conflict-vs-chain boundary (A-3); `problem_solution` silently outranking a full
  `argumentative` match (A-4); circular `general_eap` condition (c) (A-5);
  compound-prompt unit rule (A-6); effects-only prompts (A-7); dictionary-
  dependent "mandated" detection (A-8). None resolved by this Goal.
* **Signed expert disposition remains outstanding (G1 open).** The V1 review
  records are a first machine-executed reviewer pass; adjudication and signed
  human panel disposition (Research Evaluation + L2) remain pending and are
  recorded in `dependencies_remaining`. No validity claim is made anywhere.
* **V3 execution is blocked on DP-4.** The governed snapshot of the real legacy
  `essays` table is not authorized (DP-4; Research Evaluation + PROGRAM name the
  snapshot procedure). Methodology and instruments are ready; all census numbers
  remain `NR`; no counts were fabricated or estimated. Raw SWECCL is not a
  substitute (corpus genres != product legacy genres).
* **`discourse_organization` remains excluded** (UD-02 DEFER) throughout; the V1
  review confirms it is absent from the five types and the two states.

## 4. Verification

| Check | Result |
| --- | --- |
| Preflight identity (root/branch/HEAD/worktree) | PASS |
| V1 review records created under `docs/domain/` with protocol, determinations, findings, ambiguity register, honest-state declaration | PASS |
| V3 methodology created with data-collection plan + both instruments (census protocol, feature checklist) | PASS |
| DP-4 dependency explicitly recorded: snapshot NOT authorized; execution status NOT_RUN | PASS |
| No validity claim / no ratification wording anywhere in deliverables | PASS |
| `discourse_organization` excluded; no Domain Pack v1 implementation; no product code (`app/`, `locales/`, `tests/`, `data/`, `run.bat` untouched) | PASS |
| Pre-existing untracked files preserved; no push/PR; raw SWECCL untouched | PASS |
| Handoff JSON valid against `schemas/handoff.schema.json` (required fields; parses) | PASS |

## 5. Dependencies

Unlocked (review lane): V1 review records + V3 methodology now exist as
reviewable evidence for Research Evaluation + L2 (the "taxonomy validity evidence"
review lane advances; execution of the studies remains gated).

Remaining (tracked by PROGRAM; outside this Goal):

* V1 signed panel disposition / adjudication (Research Evaluation + L2) — G1
  acceptance item.
* Contract ambiguity dispositions A-1..A-8 (contract owner + Research Evaluation;
  needed before V2/V4 design can close).
* Governed legacy-essays snapshot authorization (DP-4) — V3 execution blocker.
* V2/V4 execution (separately gated; V2 additionally needs trigger dictionaries
  or a rule-application protocol).
* D-22 mapping approval (Research Evaluation + L2).
* Domain Pack v1 implementation authorization (excludes `discourse_organization`).

## 6. Boundaries honored

Docs-only changes inside the L2 worktree; no approval issued; no product behavior;
no comparability change; no push/PR; nothing written outside the authorized
worktree; raw SWECCL untouched; pre-existing untracked files preserved.

*Report produced by the L2 execution agent under Goal L2-VALIDITY-EVIDENCE,
2026-08-09. Evidence generation only; no validity claim; no ratification.*
