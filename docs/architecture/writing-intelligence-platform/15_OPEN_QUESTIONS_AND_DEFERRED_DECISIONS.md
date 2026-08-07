# 15 — Open Questions and Deferred Decisions

All items below are explicitly unresolved. Statuses: `Researcher decision required` / `NR` (no information) / `Unclear` / `NA` (not applicable in this Goal). Nothing here may be silently resolved by an implementation Goal; each requires the named decision owner.

## A. L2 Writing Domain

| ID | Question | Status |
| --- | --- | --- |
| D-L2-01 | Exact v1 task-type enumeration and labels (opinion/argumentative/discussion/problem-solution/general-EAP boundary) | Researcher decision required; general/EAP scope Unclear |
| D-L2-02 | `task_type` persisted column vs derived value (recommendation: additive typed field; metadata-only until D-22 conditions) | NR |
| D-L2-03 | Dimension-envelope membership incl. discourse_organization feasibility | Researcher decision required; deterministic-evidence feasibility Unclear (spike needed) |
| D-L2-04 | Corpus-profile contents and authorization source | NR (no authorized resource exists) |
| D-L2-05 | New practice target codes / exercise types | Researcher decision required |
| D-L2-06 | Organization-feature resource reuse | Unclear |
| D-L2-07 | Academic sharing of TaskTypeRegistry (resolved: namespace-scoped, D-04) | Resolved |
| D-L2-08 | Domain Pack shipping form (recommendation: configuration version + resources) | NR |
| D-L2-09 | zh_CN naming/ordering for new labels (parity contract applies) | Unclear |
| D-L2-10 | Typed task-type picker in Student UI | Unclear; deferred beyond this Goal |

## B. Academic Writing Domain

| Question | Status |
| --- | --- |
| Paper vs multi-paper project; multi-paper portfolios | Researcher decision required |
| Journey representation of section-level cycles; paper-anchored aggregation | NR until product-shape/domain decisions; MVP honest state frozen (D-37/RT-20) |
| Claim creation mode (learner-declared only vs `system_derived_candidate` + confirmation) | Researcher decision required |
| Academic practice target kinds | Unclear; no user-research evidence |
| External citation verification (web/DOI) long-term | Researcher decision required; out of MVP |
| Exportability of Academic learner data | Policy decision |
| Feedback granularity (section-only vs paper-level structure priorities) | NR |
| Question-versioning depth | Researcher decision required |
| Plagiarism detection | NA for this Goal |
| Academic task schema (genres, citation styles, source-set lifecycle) | NR |
| Academic locale policy | NR |

## C. Corpus & NLP

| ID | Question | Status |
| --- | --- | --- |
| D1 | Which corpora are authorized and for which populations | Researcher decision required |
| D2 | Whether authentic corpus excerpts may ever be shown to learners | Researcher decision required; default: no display |
| D3 | Licensing/permission model per corpus | Researcher decision required (NA until a corpus is selected) |
| D4 | Band method (quantile vs SD) and minimum reference-group N | Researcher decision required |
| D5 | Controlled task taxonomy for L2 vs Academic profiles | Researcher decision required |
| D6 | Proficiency-annotated corpus metadata usage (I1 applies regardless) | Researcher decision required |
| D7 | L1-matched reference groups | NR |
| D8 | v0.1 feature-set scope | NR |
| D9 | Embedding-based example retrieval | NR (YAGNI) |
| D10 | Corpus comparison persistence location | Unclear (recommendation: append-only `student_corpus_comparisons` + manifest/distribution tables) |
| D11 | Frequency-resource authorization from corpus data (lexical_sophistication) | Researcher decision required (circularity risk per G) |
| D12 | UI exposure of corpus grounding | Unclear (recommendation: Research first) |

## D. Shared Platform & Governance

| Question | Status |
| --- | --- |
| Learner multi-domain policy (one learner, both domains) | Deferred (D-15 sets evidence isolation regardless) |
| Epistemic-status persistence (additive typed field vs compute-at-boundary) | Researcher decision required (interim: compute-at-boundary) |
| Genre taxonomy authority; legacy genre reconciliation | Researcher decision required / NR (legacy mapping never inferred) |
| Descriptive-trend thresholds (min observations/window) | Unclear / Researcher decision required |
| Reference-group policy | NA today; Researcher decision required before that capability |
| Citation policy (never / source-grounded-only / disabled-by-default) | Researcher decision required; default: never by default |
| Feedback audit sampling design (rate, criteria, reviewer pool) | Unclear / Researcher decision required |
| Validity-evidence storage (research DB vs documents) | Unclear / Researcher decision required |
| Practice completion semantics drift | Researcher decision required; recommendation: keep activity-only |
| Configuration model (single payload with domain sections vs families) | Open (recommendation: single payload, D-17) |
| Migration-14 rollback policy extension | Open (recommendation: keep one-step non-destructive) |
| Domain-selector persistence per learner | NR |
| Academic source model (upload vs reference-only) | NR |
| URL-addressable page states | Unclear |
| Profile implementation form (snapshot JSON extension vs new table) | Decision pending with Domain A work (recommendation: extension) |
| Version single-sourcing authority module | Open (with Horizon 1 work) |
| `.agent-workflow/` ignore policy | Operational follow-up for Architecture & Integration; no `.gitignore` change was made in the freeze-baseline Goal (runtime planning state currently unignored) |

## E. Explicit non-goals carried forward (never to be silently reopened)

Proficiency/mastery/learning-gain reporting; outcome attribution; auto-citation generation without grounding verifier; graph persistence; repo split; microservices; corpus ingestion/search infrastructure; per-domain design tokens; auth/SSO; collaborative editing.