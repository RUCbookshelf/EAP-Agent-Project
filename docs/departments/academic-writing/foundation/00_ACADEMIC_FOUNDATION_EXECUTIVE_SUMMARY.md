# 00 — Academic Foundation Executive Summary

**Goal:** Academic Writing Domain Foundation (Wave-1)
**Branch:** dept/academic-foundation | **Baseline:** b171cce | **Date:** 2026-08-07
**Decision:** ACADEMIC WRITING DOMAIN FOUNDATION DEPARTMENT GREEN - READY FOR INTEGRATION

## 1. What was built

The first implementation-ready Academic Writing domain foundation: seven frozen entities (ResearchProject, ResearchQuestion, Source, EvidenceUnit, Claim, PaperSection, CitationLink), four independent provenance chains, deterministic local citation verification with D-32 append-only records, seven integrity guardrails, domain-local vocabulary boundary, eight repository protocols with in-memory adapters, thirteen application use cases, and a full synthetic fixture matrix — all under `app/academic/` with 322 focused tests. Cross-domain integration stays deferred to Architecture & Integration, exactly as the goal requires.

## 2. Work units

| WU | Title | Gate |
| --- | --- | --- |
| WU1 | Current-State & Domain Gap Map | GREEN (greenfield confirmed) |
| WU2 | Domain Entity Contracts | GREEN |
| WU3 | Provenance Graph | GREEN |
| WU4 | Academic Integrity Guardrails | GREEN |
| WU5 | Evidence/Epistemic Status Compatibility | GREEN |
| WU6 | Repository Protocols | GREEN |
| WU7 | Application Services | GREEN |
| WU8 | Citation Verification Boundary | GREEN |
| WU9 | Domain Fixtures & Tests | GREEN |
| WU10 | Integration Boundary Spec + Closure | GREEN |

## 3. DEPARTMENT GREEN criteria

| Criterion | Result |
| --- | --- |
| All seven core entities exist | PASS (entities.py; 8 model types incl. link + record) |
| Domain ownership explicit | PASS (app/academic/; charter-aligned) |
| L2 diagnostic evidence not reused | PASS (gap map; zero L2 imports; fixture contamination test) |
| Provenance relationships represented | PASS (four chains; ProvenanceGraph) |
| Claim/evidence distinction enforceable | PASS (typed links + support state; never inferred) |
| Citation links deterministic | PASS (CIT-RULE-01..05; D-32 records; ACAD-INV-02) |
| Invalid states detected | PASS (ACAD-RULE-01..07) |
| Repository boundaries exist | PASS (8 protocols + in-memory adapters) |
| Core application services work | PASS (13 use cases; end-to-end flow) |
| Synthetic domain tests pass | PASS (322 focused; 366 with regression smoke) |
| No production L2 behavior changes | PASS (zero L2 edits; diff confined to additive paths) |
| No shared contract silently invented | PASS (vocabulary mirrors marked; WU5) |
| Cross-department dependencies explicit | PASS (09_CROSS_DEPARTMENT_DEPENDENCIES.md) |
| Integration handoff complete | PASS (10_INTEGRATION_HANDOFF.md; goal section 31 items) |

## 4. Verification

- Focused Academic suite: 322 passed / 0 failed
- Regression smoke (architecture + database + corpus baseline): 44 passed / 0 failed (366 total; after installing the pinned spaCy model)
- Independent DeepSeek reviews at every design gate (WU2/3/4+5/7+8/10): all APPROVE_WITH_FINDINGS; every finding dispositioned
- No migration (13 authority); no API/UI wiring; no push/PR; user-owned files untouched

## 5. Open decisions (carried forward, never resolved here)

Paper vs multi-paper; claim creation mode; question-versioning depth; citation policy; academic task schema; locale policy; academic practice kinds; external citation verification; epistemic persistence form; plagiarism detection (NA). Statuses per 15_OPEN_QUESTIONS_AND_DEFERRED_DECISIONS.md.

## 6. Next step (integration, NOT this Goal)

Architecture & Integration milestone gate after Shared Core H1: discriminator + migration 14, domain packs layout, vocabulary adoption, SQLite adapters, API routing, then Frontend surfaces. See 10_INTEGRATION_HANDOFF.md.