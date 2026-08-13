# L2-D22-CENSUS-AND-V1 — Execution Report

**Goal:** `L2-D22-CENSUS-AND-V1` — D-22 governed-snapshot census (DP-4) + D-22
manifest qualification + V1 ambiguity adjudication (A-1..A-8)
**Owner:** L2 Writing Domain
**Date:** 2026-08-09
**Baseline / Branch / Worktree:** `09264abbd93cdc6b62b83cefd94b3b640319ac9b` /
`dept/l2-writing` / `A:\EAP Agent Project\worktrees\l2-writing`
**Status:** DEPARTMENT COMPLETE (not integration GREEN; not promoted)

---

## 1. Preflight

- Worktree root, branch (`dept/l2-writing`), and HEAD (`09264ab`) verified
  against the Goal Packet and `WORKSTREAM_REGISTRY.json`; all match.
- Pre-existing untracked files preserved untouched: `docs/domain/*`,
  `docs/integration/*.md`, `handoff.json`.
- Program-control artifacts read: `WORKSTREAM_REGISTRY.json`,
  `PROGRAM_STATUS.md`, `DEPENDENCY_GRAPH.md`, `PROMOTION_HISTORY.md`,
  `WORKTREE_REGISTRY.md`.
- Governing decision records read: `RD-D22-approved.json`,
  `RD-D22-DP4-authorized.json`, `L2-VALIDITY-scoped-disposition.json`;
  D-22 proposal + manifest proposal; V1 content review (A-1..A-8);
  taxonomy contract; D-L2-02 / D-L2-09 / D-L2-10.

## 2. (A) DP-4 census — governed snapshot of the legacy `essays` table

Read-only census over the product database
(`A:\EAP Agent Project\writing-feedback-mvp\data\writing_feedback.db`,
SQLite `mode=ro`; integrity check `ok`; no WAL; no writes; DB SHA-256
`20c609ee...b1d0c` pinned in the record; schema_migrations max version 13).
Methodology: V3 census protocol C1-C9
(`docs/domain/L2_VALIDITY_V3_COVERAGE_CENSUS_METHODOLOGY.md`) — DP-4 now
authorized, so the prepared instruments executed unchanged.

### 2.1 Snapshot guarantees

- Snapshot contains counts, genre values (task metadata), schema headers,
  provenance, and QA records only. NO essay text, NO prompt text, NO learner
  identity values (`essay_text`, `writing_prompt`, `tool_use` excluded).
- No mappings outside M0-M4 were created; nothing was written to the product
  DB; no raw SWECCL access; no product mutation.

### 2.2 Results

| Metric | Value |
| --- | --- |
| Total legacy rows | 29 |
| Distinct raw genre values | 2 (`argumentative essay` x26, `议论文` x3) |
| Distinct normalized values | 2 |
| M1 (`argumentative essay` -> `argumentative`) | 26 rows |
| M1-zh (`议论文` -> `argumentative`) | 3 rows |
| M2 / M2-zh / M3 / M3-zh / M4 / M0 | 0 rows each (no such values in snapshot) |
| Resulting task type distribution | `argumentative` 29 (100%); `legacy_unclassified` 0 |
| Typed rate | 1.0 |
| `legacy_unclassified` rate | 0.0 |
| Mapping conflicts | 0 |
| Distinct-value coverage | 100% (2/2 dispositioned; M0 default governs any future unmatched value) |
| QA (second disposition pass) | identical; duplicate-rule detection PASS |

### 2.3 Legacy-source distribution

| Dimension | Distribution |
| --- | --- |
| By genre option | `option_argumentative_en` 26; `option_argumentative_zh` 3 |
| By locale hint | en 26; zh_CN 3 |
| Independent vs revision | independent 12; revision 17 |
| By revision stage | first_draft 11; revised_draft 11; final_draft 5; independent_submission 2 |
| By draft stage | "first draft" 11; "revised draft" 11; "final draft" 5; "independent submission" 1; "终稿" 1 |
| By student class | real 27; synthetic_demo 2 |

### 2.4 Edge cases requiring review

None in the current governed snapshot: no empty/whitespace-only values, no
values without a rule, no near-miss variants, no mixed-script values, no long
values, no digit-containing values. The governed snapshot is a point-in-time
pin; a re-run is required if the product DB changes (recorded in the census
artifact and the manifest open items).

### 2.5 NR items (honest unavailability)

Prompt-pattern audit (V3 instrument 2, F01-F17) is `NR` for the governed
snapshot: prompt text is excluded from the snapshot by the packet's
no-essay-text rule; the pattern audit remains a separate V3/V4 execution item.
V2 agreement-sample and V4 adversarial-set execution are likewise `NR` (not
part of this Goal).

Artifact: `docs/domain/census/L2_DP4_LEGACY_ESSAYS_CENSUS_v1.0.0.json`
(script: `docs/domain/census/dp4_census.py`).

## 3. (B) D-22 manifest qualification

The approved explicit-only mapping manifest v1 is persisted as
`docs/domain/D-22_legacy_genre_mapping_manifest.v1.0.0.qualified.json`:

- status `QUALIFIED` under RD-D22 (APPROVED) and RD-D22-DP4 (AUTHORIZED);
- rule version `v1.0.0`; taxonomy version `l2-task-type-taxonomy-v1.0.0`;
- rules M0-M4 unchanged from the proposal (no rule edits during qualification);
- precedence rules, provenance, non-claims, and the rollback note recorded
  (versioned data; configuration-version deactivation; append-only rows;
  comparability freeze until behavior-diff + D-30);
- census summary embedded (29 rows; 2 distinct values; 100% coverage).

No Domain Pack v1 content; no product behavior change; the write-time
application of the manifest remains a separately authorized implementation
Goal (D-L2-02).

## 4. (C) V1 adjudication A-1..A-8

Full per-item determinations with contract evidence and condition checks are in
`docs/domain/L2_VALIDITY_V1_ADJUDICATION.md`; machine-readable record in
`docs/domain/L2_VALIDITY_V1_DISPOSITION.json`.

| Item | Determination | Outcome |
| --- | --- | --- |
| A-1 | RESOLVED-CLARIFICATION | viewpoint-only request is not a mandated final stance; balanced treatment + own opinion (no evidence mandate) -> `discussion` by chain |
| A-2 | RESOLVED-CLARIFICATION | precedence rationale documented (subsumption, not difficulty); no outcome change |
| A-3 | RESOLVED-SCOPING | conflict rule + outcome state are contract-complete; conflict-pair enumeration is Domain Pack v1 content (G5), not authored here |
| A-4 | RESOLVED-CLARIFICATION | §3 governs only opinion/argumentative; §4 chain governs co-matches; rationale documented; outcome unchanged |
| A-5 | RESOLVED-CLARIFICATION | (c) is a version-binding hook satisfied iff (a)+(b); adds no criterion |
| A-6 | RESOLVED-CLARIFICATION | unit = registered task definition; compound definitions classify whole via chain; conflict rule for comparable-strength full matches |
| A-7 | RESOLVED-CLARIFICATION | closed trigger class: effects-only prompts never route to `problem_solution`; extension would require RE-approved major amendment |
| A-8 | RESOLVED-SCOPING | semantic definition complete at contract level; machine dictionaries are Domain Pack v1 content (G5) |

All eight items resolve under the Researcher-authorized scoped conditions: no
new task construct, no new measurement construct, no material taxonomy change,
no unsupported inferential claims, five-type compatible. Therefore the
disposition is persisted:

> **OPERATIONAL_CONTENT_VALIDITY: ADEQUATE_FOR_V1_ROUTING_AND_CLASSIFICATION**

Scoping is verbatim-policy: content-level adequacy for operational task-routing
and classification semantics; NOT a psychometric validity claim; no
proficiency/mastery/ability/learning-gain/measurement meaning; execution
remains gated on Domain Pack v1 trigger content (G5) and the D-22 write-time
lane; no comparability participation.

`researcher_decision_required = false`. Research Evaluation retains the right
to object to any item; the signed expert-panel disposition (G1) and V2/V4
studies remain outstanding dependencies (unchanged).

## 5. Verification performed

1. Census script executed over the read-only DB; second disposition re-pass
   identical; duplicate-rule detection clean; 100% distinct-value coverage.
2. All produced JSON artifacts parse as valid JSON (census, qualified
   manifest, disposition; handoff validated against
   `program-control/schemas/handoff.schema.json`).
3. Product DB verified unchanged after the run (same SHA-256).
4. Git status re-checked: only new files added under the L2 worktree;
   pre-existing untracked files untouched; no commits, no push, no PR.

## 6. Honest-state declarations

- Department scope complete; NOT integration GREEN; `promotion_eligible =
  false`; `integration_required = true`.
- No product code, no registry, no locale, no API, no UI change; no Domain
  Pack v1 implementation; no contract file amended; no raw SWECCL access.
- The census is a point-in-time pin of the current product DB (29 rows); it
  does not estimate distributions for any other database state.

*Produced by the L2 execution agent under Goal L2-D22-CENSUS-AND-V1, 2026-08-09.*
