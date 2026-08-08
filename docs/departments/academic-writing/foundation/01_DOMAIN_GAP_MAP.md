# 01 — Academic Writing Domain Gap Map

**Goal:** Academic Writing Domain Foundation (Wave-1)
**Baseline:** b171cce (corrected common Wave-1 baseline; Corpus Stage 5 included)
**Branch:** dept/academic-foundation
**Date:** 2026-08-07
**Status:** WU1 GREEN — ownership boundaries are clear

## 1. Executive conclusion

Academic Writing (Domain A) is **greenfield** at baseline b171cce:

- All seven frozen entity names (ResearchProject, ResearchQuestion, Source, EvidenceUnit, Claim, PaperSection, CitationLink) have **zero hits** in `app/`, `tests/`, and `scripts/` implementation code.
- **Zero Academic database tables** exist (frozen baseline: 33 unique tables, migration 13). No migration 14.
- **Zero Academic UI stubs, pages, or workspace features** exist.
- The words `academic`, `citation`, and `paper` have zero hits in implementation code, tests, scripts, data, locales, and prompts.
- **No REUSE or EXTEND candidate exists** for any Academic entity. Every same-word candidate belongs to another domain and must not be appropriated.

## 2. Method and verification

1. Mechanical inventory (engineering executor, mimo-v2.5): full scan of `app/`, `tests/`, `scripts/`, `data/`, `docs/` for candidate names (`academic`, `evidence`, `citation`, `source`, `research`, `document`, `project`, `claim`, `paper`, `resource`, `note`, `corpus`) plus exact Academic entity names, DB DDL, and UI features. Evidence: `.agent-workflow/academic-writing-foundation/evidence/wu1-inventory.md` (271 lines, exact path:line citations).
2. Orchestrator parent verification: independent spot-checks reproduced the zero-hit claims and representative citations (e.g., `app/calibration/evidence.py:9`, `app/corpus/resource.py:58`, `app/research/service.py:76`, `app/database/migrations.py:405`, `app/practice/mapping.py:217`); `git status --short` showed no tracked modifications.
3. Fresh independent review (deepseek-v4-flash): classification consistent with frozen contracts; supplementary locales/prompts/data scan found no conflicts; greenfield conclusion confirmed; no REUSE/EXTEND candidates. Evidence: `.agent-workflow/academic-writing-foundation/evidence/wu1-review.md`.

## 3. Classification results

Legend: REUSE = use as-is; EXTEND = extend; ISOLATE = keep separate (other department); DEPRECATE LATER = keep but plan removal; DO NOT REUSE = different semantics, must not be borrowed.

### 3.1 The seven Domain A entities — DO NOT REUSE (greenfield)

| Entity | Evidence | Verdict |
| --- | --- | --- |
| ResearchProject | zero hits in code/tests/scripts; only frozen architecture docs (05_ACADEMIC_WRITING_DOMAIN.md) | DO NOT REUSE — implement fresh under `app/academic/` |
| ResearchQuestion | zero hits | DO NOT REUSE — implement fresh |
| Source | zero hits as entity; existing `source*` identifiers are L2 submission/practice/revision/CALF meanings | DO NOT REUSE — implement fresh |
| EvidenceUnit | zero hits; existing `evidence*` identifiers are L2 diagnostic/CALF/Research Evaluation meanings | DO NOT REUSE — implement fresh |
| Claim | zero hits as entity; existing `claim*` identifiers are L2 disclaimers/validators | DO NOT REUSE — implement fresh |
| PaperSection | zero hits | DO NOT REUSE — implement fresh |
| CitationLink | zero hits; `citation` zero-hit app-wide | DO NOT REUSE — implement fresh |

### 3.2 Same-word candidates — DO NOT REUSE (L2/Feedback & Learner Intelligence)

| Candidate | Representative locations | Actual identity | Verdict |
| --- | --- | --- | --- |
| `evidence` (500+ hits) | `app/analysis/schemas.py:97` (MetricResult.evidence); `app/calibration/evidence.py:9-51` (EvidenceRelevanceValidator, evidence-relevance-v0.6.1); `app/database/migrations.py:405` (history_evidence_registry); `app/database/migrations.py:683` (transfer_evidence_candidates); `app/core/longitudinal_models.py:236-253` (HistoryEvidenceRecord); `app/calibration/service.py:52-193`; `app/ui/components.py:375` (evidence_quote) | L2 internal diagnostic evidence, longitudinal learner evidence, feedback quotes | DO NOT REUSE |
| `source` | `app/practice/mapping.py:217` (source submission bundle); `app/practice/target_creation.py:117` (source_diagnosis_id); `app/infrastructure/sqlite/repositories/revision.py:46,76`; `app/calf/schemas.py:55` (TimingSource); `app/ui/features/student/writing.py:213` (revision_source_preset) | L2 submission ancestry, practice provenance, CALF timing classification | DO NOT REUSE |
| `claim` | `app/feedback/validation.py:166` (deterministic-development-claim guard); `app/practice/service.py:17`; `app/services/learner_model.py:114,323`; `app/services/calf.py:165`; `app/journey/service.py:8` | L2 research-validity disclaimers and feedback validation guards | DO NOT REUSE |
| `resource` | `app/analysis/schemas.py:35` (ResourceVersion); `app/analysis/connective_features.py:10` (RESOURCE_PATH); `app/errors.py:23` (RESOURCE_NOT_FOUND category) | NLP resource versioning, analyzer resources, generic error category | DO NOT REUSE |
| `note` | `app/configuration/schemas.py:124` (change_note); `app/models/schemas.py:249` (uncertainty_note); `app/api/routers/admin.py:42` (security_note) | L2 configuration/feedback/admin notes (SourceNote was explicitly rejected by frozen design; learner notes stay field-level) | DO NOT REUSE |
| `project` | `app/journey/service.py:132-157` (projection_reader); `app/journey/cycles.py:5` (projection) | Journey read-time projection mechanics | DO NOT REUSE |

### 3.3 Parallel-department content — ISOLATE

| Candidate | Representative locations | Owner | Verdict |
| --- | --- | --- | --- |
| `research` | `app/research/` module, `app/research/service.py:76` (ResearchDataService), `app/api/routers/research.py`, `app/ui/ports/research.py:42`, `app/ui/features/research/evidence.py:18`, `app/infrastructure/sqlite/repositories/research.py` | Research Evaluation & Data Governance | ISOLATE — never imported by `app/academic/` |
| `corpus` | `app/corpus/` (resource.py:58 CorpusResourceDescriptor, intelligence.py:42, features.py:25, groups.py:15, distributions.py), `tests/corpus/`, `docs/corpus-intelligence/l2/` | Corpus & NLP Intelligence (parallel department; now in baseline) | ISOLATE — never imported by `app/academic/` |
| `document` | `app/corpus/groups.py:42-93` (document_id) | Corpus & NLP | ISOLATE — naming caution: `document` is a near-synonym for manuscript/PaperSection; Academic must not reuse this identifier semantics |

### 3.4 DEPRECATE LATER / REUSE / EXTEND

- **None identified.** No existing structure is an Academic-adjacent prototype worth deprecating or extending. Academic starts clean under `app/academic/`.

## 4. Same-word trap registry (never treat as shared referents)

| Word | L2 / platform referent | Academic referent (Domain A) |
| --- | --- | --- |
| evidence | diagnostic evidence, learner evidence families, feedback quotes | source-located research EvidenceUnit (kind direct_quote / learner_paraphrase) |
| claim | research-validity disclaimer, validator guard | learner-declared argumentative claim with support state |
| source | submission ancestry, practice provenance, timing source | bibliographic/research Source with four-chain provenance |
| paper | (none in code) | PaperSection container / manuscript |
| document | corpus document identifier | (avoid; use PaperSection vocabulary) |
| project | Journey projection | ResearchProject container |
| revision | L2 revision groups/snapshots | (Academic section drafting reuses shared loop mechanics later; no entity duplication) |
| practice | L2 practice targets/provenance (PRIO-...) | deferred Academic exercise kinds (Researcher decision required) |

Frozen rule (03_SHARED_CORE_AND_DOMAIN_BOUNDARIES.md section 6): L2 internal diagnostic evidence and Academic research evidence never share a table or schema; Academic evidence is referenced by ID only (D-06).

## 5. Ownership boundaries for this Goal

- `app/academic/` (new, additive): seven entities, provenance graph, integrity guardrails, evidence/epistemic-status domain-local adapters, repository protocols + in-memory adapters, application services, citation verification boundary.
- `tests/academic/` (new): fixtures and tests. No modification of existing L2 modules.
- `docs/departments/academic-writing/foundation/` (new): canonical deliverables 00-10.
- Explicitly untouched: `app/api` (no endpoints), `app/ui` (no UI), `app/database`/migrations (no migration 14), `app/research`, `app/corpus`, all L2 services.

## 6. Open decisions carried forward (not resolved here)

| Decision | Status |
| --- | --- |
| Paper vs multi-paper project (one paper per project in MVP) | Researcher decision required |
| Claim creation mode (learner-declared only vs system_derived_candidate + confirmation) | Researcher decision required |
| Question-versioning depth | Researcher decision required |
| Citation policy (never / source-grounded-only / disabled-by-default) | Researcher decision required; default: never by default |
| Academic task schema (genres, citation styles, source-set lifecycle) | NR |
| Academic locale policy | NR |
| Academic practice target kinds | Unclear |
| External citation verification (web/DOI) long-term | Researcher decision required; out of MVP |
| Plagiarism detection | NA for this Goal |

## 7. Evidence references

- `.agent-workflow/academic-writing-foundation/evidence/wu1-inventory.md` (noncanonical runtime evidence)
- `.agent-workflow/academic-writing-foundation/evidence/wu1-review.md` (noncanonical runtime evidence)
- `docs/architecture/writing-intelligence-platform/05_ACADEMIC_WRITING_DOMAIN.md`
- `docs/architecture/writing-intelligence-platform/03_SHARED_CORE_AND_DOMAIN_BOUNDARIES.md`
- `docs/architecture/writing-intelligence-platform/10_DEPARTMENT_CHARTERS.md`
- `docs/architecture/writing-intelligence-platform/01_CURRENT_STATE_MAP.md`

## 8. Gate decision

WU1 GREEN — ownership boundaries are clear: Academic Writing is greenfield; all same-word structures belong to other domains (ISOLATE/DO NOT REUSE); no REUSE/EXTEND/DEPRECATE LATER candidates; L2 diagnostic evidence is not reused. Proceed to WU2 (Domain Entity Contracts).