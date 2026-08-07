# 16 — Architecture Red Team Review

**Reviewer:** Independent Architecture Red-Team Reviewer (fresh `deepseek/deepseek-v4-flash`; did NOT participate in Rounds 1–3)
**Date:** 2026-08-07
**Session provenance (noncanonical):** Round 4 was delivered by a fresh independent reviewer; the working note lived at `.agent-workflow/writing-intelligence-platform-architecture/handoffs/round4-red-team.md`. The findings and resolutions below are canonical and self-contained in this document.
**Verdict received:** NOT SAFE TO FREEZE AS-IS — 1 BLOCKING + 6 HIGH + 9 MEDIUM + 5 LOW + 4 REJECTED (25 findings).
**Chair resolution:** All BLOCKING and HIGH findings resolved in the synthesis (decisions D-21..D-27); all MEDIUM resolved (D-28..D-36); LOW findings given dispositions (D-37). Final status after resolution: **architecture ready for departmental development.**

## Summary table

| ID | Category | Severity | Finding | Resolution |
| --- | --- | --- | --- | --- |
| RT-02 | Provenance | BLOCKING | Domain-attribution authority undefined/contradictory | D-21: server-derived attribution, client advisory, provenance + contract test |
| RT-01 | Migration traps | HIGH | task_type would silently change legacy comparability | D-22: metadata-only until mapping decision; legacy_unclassified; behavior-diff test |
| RT-03 | Hidden coupling | HIGH | domain-equality blanket unspecified on 33 tables | D-23: submission-ancestry resolver + table map + isolation tests |
| RT-04 | Premature abstractions | HIGH | S-CIC with zero consumers/corpora | D-24: downgrade to boundary contract; machinery gated |
| RT-05 | Duplicated systems | HIGH | S-CIC overlaps CALF band machinery | D-25: CALF owns measurement/eligibility; corpus content via resource_requirement |
| RT-06 | Parallel-dev conflicts | HIGH | registry content in shared Python modules | D-26: per-domain `domain_packs` data layout; mechanism-only code |
| RT-07 | Maintenance | HIGH | 12 sync-conflict duplicate files unaddressed | D-27: Horizon 1 inventory + manifest + quarantine + drift check |
| RT-09 | Hidden coupling | MEDIUM | language semantics undefined | D-28: submission language; distinct from locale/L1; drop if no consumer |
| RT-10 | Maintenance | MEDIUM | single-sourcing could merge evidence streams | D-29: identity-only scope; artifact streams independent |
| RT-11 | Evaluation | MEDIUM | no gate for "zero behavior change" | D-30: Horizon 1 acceptance gate (core green, additive-only contract diff, 600/600, golden-submission diff, migration 13) |
| RT-12 | Evaluation | MEDIUM | isolation tests unspecified | D-31: five frozen invariants, each a named contract test |
| RT-13 | Provenance | MEDIUM | citation verified lacks verification record | D-32: verification-rule manifest + append-only per-link record |
| RT-14 | Ownership | MEDIUM | calibration machinery vs thresholds | D-33: machinery shared; threshold content in domain packs + methodological review |
| RT-16 | Over-engineering | MEDIUM | governance weight vs repo scale | D-34: office convenes only contract gates + migration coordination; ADR only for shared contracts; concrete drift triggers |
| RT-25 | Premature abstractions | MEDIUM | parametrize 1237-test core by domain | D-35: core stays single-domain; seam contracts parametrized when Domain A exists |
| RT-26 | Migration traps | MEDIUM | deferred CHECK leaves exports open | D-36: CHECK+DEFAULT in migration 14; export-time validation until then |
| RT-15 | Ownership | LOW | corpus triple ownership | D-37: charter ownership statements |
| RT-17 | Over-engineering | LOW | dimension envelope mixes axes | D-37: availability + learner_exposure split |
| RT-18 | Parallel-dev | LOW | Horizon 2 lacks gate annotations | D-37: blocked-until markers in deliverable 12 |
| RT-19 | Maintenance | LOW | contract regeneration step missing | D-37/D-30: named Horizon 1 step |
| RT-20 | Missing concepts | LOW | Academic MVP Journey gap | D-37: honest "academic journey unavailable in MVP" state |
| RT-21 | — | REJECTED | duplicate health endpoint | not reproducible at HEAD |
| RT-22 | — | REJECTED | UI imports backend schemas | not reproducible at HEAD |
| RT-23 | — | REJECTED | DomainDescriptor = workflow engine | unsupported by candidate text |
| RT-24 | — | REJECTED | per-domain suite duplication | candidate already rejects it |

## Frozen-contract assessment (red team)

- Would break contracts if implemented as written: RT-01 (longitudinal event evidence, Journey cycles, insufficient-evidence states), RT-02 (learner isolation, learner-owned submissions, persistent records, research-validity boundaries), RT-09 (bilingual Student UI), RT-11 (all contracts via un-gated consolidation). All four resolved above (D-22, D-21, D-28, D-30).
- Correctly preserved (verified): epistemic-status boundary; practice provenance + activity-only completion; revision linkage/comparability; L2 feedback schema and journey event vocabulary untouched; corpus invariants strengthen the research-validity boundary.

## Accepted risks (explicit)

- Governance process weight accepted with bounds (D-34).
- Corpus machinery deferred until authorized corpus + consumer + licensing (D-24) — accepted cost: no corpus-grounded diagnosis until then.
- Sync-conflict file removal requires user approval; quarantine documented until then (D-27).
- Legacy genre → task_type reconciliation remains `NR` until a Researcher decision; task_type stays metadata-only (D-22).