# 04 — Academic Integrity Rules

**Goal:** Academic Writing Domain Foundation (Wave-1)
**Baseline:** b171cce | **Branch:** dept/academic-foundation
**Date:** 2026-08-07 | **Status:** WU4 GREEN + WU5 GREEN

## 1. Purpose

Deterministic integrity guardrails for the Academic domain (`app/academic/integrity.py`) and the domain-local vocabulary boundary (`app/academic/vocabulary.py`). Integrity is enforced at the service/validation layer (frozen 05:6), never at the UI or prompt level; honest states are first-class and never silently repaired; no LLM judgment; no automated plagiarism detection (NA).

## 2. Rule registry (versioned)

`INTEGRITY_RULES_VERSION = "academic-integrity-rules-v0.1.0"`

| Rule | Contract | Entity | Violation example |
| --- | --- | --- | --- |
| ACAD-RULE-01 | Claim marked supported/partially_supported has zero supporting evidence links | claim | support_state=supported but evidence_links empty (defense-in-depth; entity validators normally prevent) |
| ACAD-RULE-02 | EvidenceUnit references a missing or cross-project Source | evidence_unit | source_id not found; source belongs to another project |
| ACAD-RULE-03 | CitationLink references a missing or cross-project Source | citation_link | source_id not found; source belongs to another project |
| ACAD-RULE-04 | CitationLink references an unrelated EvidenceUnit | citation_link | evidence missing, cross-project, or evidence source != citation source |
| ACAD-RULE-05 | Removed Source is still referenced by EvidenceUnit or CitationLink | source | availability=removed but evidence/citation still points at it |
| ACAD-RULE-06 | Cross-project reference in rq/section/parent-section/claim/evidence linkage, or claim link to a missing evidence unit | referencing entity | rq/section/evidence/parent/claim target in another project or missing |
| ACAD-RULE-07 | CitationLink marked verified without an append-only verification record with result=verified (ACAD-INV-02, D-32) | citation_link | verification_status=verified but no verified record exists |

Determinism guarantees: violations sorted by (rule_id, entity_id); at most one violation per (rule_id, entity_type, entity_id) with all offending references summarized in detail; same snapshot => same result.

## 3. Coverage mapping (goal section 16)

| Goal example | Rule |
| --- | --- |
| Claim marked supported but has zero supporting EvidenceUnits | ACAD-RULE-01 |
| EvidenceUnit references missing Source | ACAD-RULE-02 |
| CitationLink references missing Source | ACAD-RULE-03 |
| CitationLink references unrelated EvidenceUnit | ACAD-RULE-04 |
| deleted Source still referenced | ACAD-RULE-05 |
| cross-project evidence leakage | ACAD-RULE-02/03/04/06 |
| verified citation without record (D-32) | ACAD-RULE-07 |

## 4. Vocabulary boundary (WU5)

- `EvidenceStatus` = the frozen 8-value shared vocabulary (`verified | candidate | insufficient | suppressed | not_applicable | unavailable | legacy | unresolved`) — domain-local mirror ONLY; ownership stays with Shared Platform & Core; no competing global contract (goal section 17).
- `EpistemicStatus` is re-exported from `entities.py` (single canonical definition; the four frozen layers observed_descriptive / gated_inference / recommendation / outcome_claim).
- `epistemic_downgrade_allowed(current, target)`: same-layer or downgrade True; upgrade never (frozen 04:2 downgrade-only display invariant).
- `academic_verification_to_shared`: provisional integration adapter (verified->verified; unverified->candidate; verification_unavailable->unavailable); unknown values raise ValueError (closed vocabulary, no silent mapping). Final mapping is confirmed at integration time.
- Epistemic<->evidence cross-axis mapping is intentionally absent (documented guard); persistence form of epistemic status remains `Researcher decision required` (compute-at-boundary interim).
- Integration-point constants (`SHARED_CORE_EVIDENCE_STATUS`, `SHARED_CORE_EPISTEMIC_STATUS`, `EPISTEMIC_STATUS_PERSISTENCE`) are consumed by the WU10 handoff.

## 5. Review status

Independent DeepSeek review (WU4+WU5): APPROVE_WITH_FINDINGS (2 low findings, both fixed): claim link to missing evidence now flagged (R06); R06 detail summarizes all offending references. Focused suite: 203 passed / 0 failed.

## 6. Evidence

- `app/academic/integrity.py`, `app/academic/vocabulary.py`
- `tests/academic/test_integrity.py`, `tests/academic/test_vocabulary.py`
- `.agent-workflow/academic-writing-foundation/evidence/wu4-wu5-review.md` (noncanonical runtime)
- Frozen references: 05:5-6; 02:4; 04:2; D-32; 03:6