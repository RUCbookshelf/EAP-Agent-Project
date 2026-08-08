# 05 — Citation Verification Boundary

**Goal:** Academic Writing Domain Foundation (Wave-1)
**Baseline:** b171cce | **Branch:** dept/academic-foundation
**Date:** 2026-08-07 | **Status:** WU8 GREEN

## 1. Boundary statement

Local and deterministic only. Citation verification never uses the web, DOI resolution, external citation databases, or any external API. It never fabricates citation metadata and never asserts semantic support equivalence: a `verified` result means deterministic reference-resolution and text-matching checks passed (frozen 05:8, D-32, goal section 20).

## 2. Versioned rule manifest

`VERIFICATION_RULES_VERSION = "academic-citation-verification-v0.1.0"`

| Rule | Check |
| --- | --- |
| CIT-RULE-01 | Citation target references resolve in the project graph (claim, source, optional evidence; same project) |
| CIT-RULE-02 | Source identity exists, belongs to the citation's project, and is active |
| CIT-RULE-03 | Evidence link exists and evidence source matches citation source |
| CIT-RULE-04 | Bibliographic identifier consistency: DOI format-valid when supplied (no lookup) |
| CIT-RULE-05 | Direct-quote evidence content deterministically matches the source text (normalized-whitespace substring) |

## 3. Verification states (frozen 05:4.3)

- `verified` — all applicable rules passed; requires an append-only `CitationVerificationRecord(result="verified")` (ACAD-INV-02, D-32); impossible to set through any path other than `CitationVerificationService.verify_citation`.
- `unverified` — checks ran and at least one failed (quote miss, unrelated evidence, invalid DOI, missing reference, cross-project reference).
- `verification_unavailable` — no source, blank source text, or source not active; hash is None; this state is frozen and never upgraded silently.

## 4. D-32 verification record

`CitationVerificationRecord` (append-only, frozen): record_id (`vr-`), citation_id, rule_id = manifest version, rule_version, source_revision_hash (present iff verified), matched_spans (locators of matched quotes), run_time (explicit), result, created_by (`system` for the local verifier). Records are appended only (protocol has no update/delete); history is sorted by (run_time, record_id).

## 5. Boundary guarantees

- `verified` without a record is impossible by construction (service is the only writer; tampering is detected by ACAD-RULE-07).
- No source text => `verification_unavailable`, never `verified`.
- No semantic support claim: verification never claims the source "supports" the claim text; it checks reference existence and deterministic text match.
- Verification is a per-citation audit trail: every run appends a record, including failed and unavailable runs.

## 6. Evidence

- `app/academic/citation.py`; `tests/academic/test_citation.py`
- `.agent-workflow/academic-writing-foundation/evidence/wu7-wu8-review.md` (noncanonical runtime)
- Frozen references: 05:5/8; D-32; goal section 20