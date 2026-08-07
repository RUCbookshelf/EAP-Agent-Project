# 06 — Application Services

**Goal:** Academic Writing Domain Foundation (Wave-1)
**Baseline:** b171cce | **Branch:** dept/academic-foundation
**Date:** 2026-08-07 | **Status:** WU7 GREEN

## 1. Purpose

`app/academic/services.py` implements the minimal use cases proving the domain is coherent (goal section 19). Framework-neutral (no FastAPI/Streamlit/LLM); deterministic; application/domain services, not UI workflows; no generalized "AI writing" behavior.

## 2. Use cases

| Use case | Method | Write-time guarantees |
| --- | --- | --- |
| create research project | create_research_project(title, research_scope?) | auto `rp-` id or explicit |
| add research question | add_research_question(project_id, question_text) | project must exist |
| register source | register_source(project_id, title, origin, ...) | project must exist; text hashed (sha256) |
| capture evidence unit | capture_evidence_unit(project_id, source_id, kind, locator, content, ...) | source must exist in project; source_version pinned to current |
| create claim | create_claim(project_id, claim_text, support_state="unsupported", rq_ids?, section_ids?) | project/rq/section membership validated |
| link evidence to claim | link_evidence_to_claim(claim_id, evidence_id, link_type) | same project; dedupe no-op; support_state stays learner-declared (never inferred) |
| create paper section | create_paper_section(project_id, section_title, order, parent?, rq_ids?) | parent/rq membership validated; nesting allowed |
| attach claim to section | attach_claim_to_section(claim_id, section_id) | same project; dedupe no-op |
| create citation link | create_citation_link(project_id, claim_id, source_id, evidence_id?, passage_span?) | claim/source membership validated; evidence must match citation source; ALWAYS unverified |
| validate project integrity | validate_project_integrity(project_id) | delegates to IntegrityService over the snapshot |
| project graph | project_graph(project_id) | snapshot bridge to ProvenanceGraph |

## 3. Design rules

- IDs: auto-generated `uuid4().hex[:12]` with entity prefixes when not supplied; explicit ids validated by entity patterns.
- Cross-project references are rejected at write time (no leakage); deliberately invalid rows can only exist via direct repository writes and are detected by the integrity service.
- Support state is never inferred: linking evidence does not change `support_state`; an unsupported claim is an honest state, not an error.
- Citations are created `unverified`; only the citation verification service (WU8) can change verification status.

## 4. Evidence

- `app/academic/services.py`; `tests/academic/test_services.py`
- Frozen references: goal section 19; 05:7 (section workflow deferred to integration)