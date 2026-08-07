# 05 — Academic Writing Domain

## 1. Positioning

Domain A — Academic Writing Agent: undergraduate students completing academic and research writing. Designed, not implemented; layered on the existing verified loop (submission → analysis → calibration gate → evidence-based Feedback → Revision → Practice → Journey). The tutor must guide rather than fabricate: it never invents references, source contents, evidence, citations, research data, or findings.

## 2. MVP vs long-term

- **Academic MVP:** research-topic/question development; source intake (manual bibliographic entry and/or uploaded source text); evidence notes bound to exact source locations; outline as ordered planned sections; section drafting; source-use and claim-evidence Feedback; citation checking against learner-provided sources; section-level Feedback and Revision; whole-paper scaffold and read-time structure view (persisted-structure facts only).
- **Long-term (explicitly out of MVP):** whole-paper coherence analysis; discipline-aware discourse models; argument mining/auto claim detection; multi-paper portfolios; external (web/DOI) citation verification; automatic bibliography generation; any proficiency/mastery/learning-gain construct.

## 3. Conceptual model (Goal section 10 candidates, evaluated)

| Candidate | Verdict | Reason |
| --- | --- | --- |
| ResearchProject | Keep | lean learner-owned container; one paper per project in MVP (multi-paper = `Researcher decision required`) |
| ResearchQuestion | Keep | versioned; claims trace to the question; question formulation is itself a feedback target |
| Source | Keep | anchor of source/evidence/citation provenance; metadata + optional uploaded text + SHA-256 + version |
| SourceNote | Reject | a note without source location is not evidence; covered by `learner_note` fields |
| EvidenceUnit | Keep | source-located, learner-authored evidence (kind: direct_quote | learner_paraphrase; exact location; source version; verification status) |
| Claim | Keep | learner-declared; support state `supported | partially_supported | unsupported | undetermined`; never inferred |
| OutlineNode | Reject | an outline is an ordered list of PaperSection records in `planned` status |
| PaperSection | Keep | ordered, hierarchical, `planned/drafted/reviewed` status; passage-span anchor |
| CitationLink | Keep | passage span <-> Source; local verification status; the only place verification outcomes are stored |
| DraftRevision | Reject | duplicates existing `revision_groups`/`revision_snapshots` semantics |

## 4. Four independent provenance chains (never merged)

1. **Source provenance:** origin `learner_entered | imported_file`; system never generates source records from memory.
2. **Evidence provenance:** kind, exact source location, source version, verification status; quotes verbatim from the learner's own source text; paraphrases explicitly learner-authored.
3. **Citation provenance:** created by explicit learner action or local string verification; always `verified | unverified | verification_unavailable`.
4. **Claim–evidence relationship:** link type (`supports | contradicts | contextualizes | related`) + support state; a claim without linked evidence is `unsupported`.

## 5. Academic Evidence Architecture (Goal section 20)

- **Minimum viable model (relational):** Source → EvidenceUnit → Claim ↔ PaperSection ↔ CitationLink; five core tables + link tables in the existing SQLite DB via a future additive migration. No graph store.
- **Provenance rules:** append-only verification outcomes (following the `history_evidence_registry` precedent); every record stores origin, verification status/version, creator, timestamps; edits create new versions, never overwrite verified records.
- **Citation verification boundary:** local and deterministic only — in-text marker/source use must match a learner-provided source text and a reference-list entry; no web lookup, DOI resolution, or external citation databases; no source text → `verification_unavailable`, never `verified`.
- **Source integrity boundary:** source text hashed and versioned; EvidenceUnit locations reference a specific source version; content never rewritten by the LLM; learners may mark a source unavailable (downgrades to `verification_unavailable`).
- **Relation to Feedback:** existing evidence-validation rules extend by reference — Feedback priorities may bind to EvidenceUnit/CitationLink IDs in addition to essay spans; quotes about source use verified against the essay text or the learner's source text; internal diagnostic evidence and learner research evidence remain two separate evidence kinds (never merged).
- **Graph verdict:** conceptually useful only as a read-time projection (claim → evidence → source navigation, unverified-citation views); relational persistence remains the initial implementation. No graph infrastructure.

## 6. Integrity guardrails (non-negotiable)

- Every Academic artifact carries an explicit origin and verification state; `unverified`/`verification_unavailable` are first-class honest states, never silently repaired.
- LLM output is guidance only; the system never auto-inserts citations or source-derived sentences into a draft without an explicit learner action.
- Academic integrity is enforced at the service/validation layer (like the existing FeedbackValidator), not at the UI or prompt level alone.
- A source-verification pre-gate is a precondition for any Domain A implementation that references sources — not an option (Council A risk 3; D-03).

## 7. Relationship to the current cycle

Writing = section drafts inside a paper (additive `paper_id`/`section_id`/`section_position`/`section_kind` on submissions); Feedback = same pipeline with academic evidence IDs; Revision = same groups/snapshots over section drafts; Practice = same target provenance (Academic exercise kinds deferred); Journey = same read-time projection with unchanged event types (D-11); paper-level aggregation deferred.

## 8. Open decisions (explicit, unresolved)

- Paper vs multi-paper project; Journey representation of section-level cycles; claim creation mode (learner-declared only vs `system_derived_candidate` with confirmation) — `Researcher decision required`
- Academic practice target kinds; external citation verification long-term; exportability of Academic learner data; question-versioning depth; whole-paper feedback surface timing — `Researcher decision required` / `Unclear`
- Academic task schema details (genres, citation styles, source-set lifecycle); locale policy — `NR`
- Plagiarism detection — `NA` for this Goal (separate product/instrument decision)

## 9. Amendments (Round 4 red team)

- **Citation verification record (D-32):** the evidence model includes a versioned verification-rule manifest and an append-only verification record per CitationLink (rule id/version, source revision hash, matched spans, run time, result). `verified` without such a record is impossible by construction; `verification_unavailable` is frozen when no source text exists.
- **Academic Journey honest state (D-37/RT-20):** the Academic workspace carries an explicit honest state — "academic journey unavailable in MVP" — since the frozen Journey event vocabulary has no Academic event types in MVP; paper-anchored journey design stays in the open-decision log.