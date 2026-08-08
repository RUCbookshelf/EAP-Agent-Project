# 03 — Academic Provenance Model

**Goal:** Academic Writing Domain Foundation (Wave-1)
**Baseline:** b171cce | **Branch:** dept/academic-foundation
**Date:** 2026-08-07 | **Status:** WU3 GREEN

## 1. Purpose

`app/academic/provenance.py` implements the read-time provenance projection over Domain A entities (frozen 05:5 graph verdict: conceptually useful only as a read-time projection; relational persistence remains the future implementation). It makes the four independent provenance chains traversable without forcing a single linear hierarchy and without any graph infrastructure.

## 2. The four provenance chains (never merged)

| Chain | Backing fields | Traversal |
| --- | --- | --- |
| Source provenance | Source.origin, availability, file_hash, source_text_hash, version, created_at/updated_at | sources_for_evidence / citations_for_source / sources_for_claim |
| Evidence provenance | EvidenceUnit.kind, locator, source_id + source_version, verification_status, epistemic_status, learner_note vs model_interpretation separation | evidence_for_claim / sources_for_evidence / orphan_evidence |
| Claim–evidence relationship | ClaimEvidenceLink.link_type + Claim.support_state | links_for_claim / evidence_for_claim / claims_for_evidence |
| Citation provenance | CitationLink (passage_span <-> source) + append-only CitationVerificationRecord | citations_for_claim / citations_for_source / records_for_citation / broken_citation_links |

A future reviewer can answer: where did this source come from (Source provenance); which exact evidence supports this claim (evidence_for_claim + links_for_claim); which claim is expressed in this section (claims_for_section); which citation supports which textual assertion (citations_for_claim + records_for_citation).

## 3. Query API (deterministic, id-sorted)

| Query | Semantics |
| --- | --- |
| evidence_for_claim(claim_id) | distinct EvidenceUnits linked by the claim (deduplicated), sorted by evidence_id |
| links_for_claim(claim_id) | typed ClaimEvidenceLinks sorted by (evidence_id, link_type) |
| claims_for_evidence(evidence_id) | claims whose evidence_links reference it, sorted by claim_id |
| claims_for_rq(rq_id) | claims containing rq_id, sorted by claim_id |
| sources_for_claim(claim_id) | distinct sources reachable via links -> evidence -> source_id, sorted |
| citations_for_claim(claim_id) | citations of the claim, sorted by citation_id |
| unsupported_claims(project_id) | claims with support_state == "unsupported" (undetermined excluded - frozen honest states stay distinct) |
| orphan_evidence(project_id) | evidence units not referenced by any claim link |
| broken_citation_links(project_id) | citations whose claim/source/evidence is missing OR belongs to a different project |
| claims_for_section(section_id) | claims attached to the section (M2M; a section may carry multiple claims, a claim may span sections) |
| sources_for_evidence(evidence_id) | the single source behind an evidence unit |
| citations_for_source(source_id) | citations referencing the source |
| records_for_citation(citation_id) | append-only verification records sorted by (run_time, record_id) |

Conventions: unknown ids return [] (query-friendly, never raises); results sorted deterministically by entity id; constructor indexes built once (duplicates: last-wins per id, documented); wrong constructor input types raise TypeError.

## 4. Design notes

- No single linear hierarchy: ResearchProject -> ResearchQuestion -> EvidenceUnit -> Claim -> PaperSection -> CitationLink is a traversal capability, not a tree; sections and RQs relate many-to-many.
- Cross-project references are detected by broken_citation_links (claim/source/evidence in a different project counts as broken).
- The graph is read-only: it is constructed from a snapshot of validated entities. Writes flow through application services (WU7) and repository protocols (WU6).
- Evidence/claim separation holds: evidence is source-located content; claims are learner-declared statements with typed links; the same-word traps are confined to the Domain A module (03:6).

## 5. Relationship to other work units

- WU4 (integrity guardrails) consumes the graph to detect invalid states (e.g., removed source still referenced; evidence-source mismatch in citations).
- WU8 (citation verification) consumes records_for_citation and broken_citation_links for deterministic verification and D-32 auditability.
- Future persistence handoff: the graph becomes a read projection over relational tables (future additive migration); no graph store.

## 6. Review status

Independent DeepSeek review: APPROVE_WITH_FINDINGS (2 low findings, both fixed): evidence_for_claim deduplicated + links_for_claim added (link-type access); constructor type checks raise TypeError instead of AttributeError. Focused suite: 138 passed / 0 failed (53 provenance tests).

## 7. Evidence

- `app/academic/provenance.py`
- `tests/academic/test_provenance.py`
- `.agent-workflow/academic-writing-foundation/evidence/wu3-review.md` (noncanonical runtime)
- Frozen references: 05_ACADEMIC_WRITING_DOMAIN.md sections 4-5; goal section 15