# CORPUS Licensing and Permitted-Use Review (UD-04)

**Goal:** `CORPUS-LICENSING-REVIEW` — Corpus Stage-6 Licensing and Permitted-Use Review (UD-04)
**Owner:** CORPUS (Corpus & NLP)
**Worktree:** `A:\EAP Agent Project\worktrees\corpus` (branch `dept/corpus`)
**Baseline:** `5aafe2728d7135212bd675a6975b44bcf99ee099` (promoted master)
**Date:** 2026-08-09
**Verdict:** GREEN (review complete; 12/12 categories classified; fail-closed where unresolved; no blocking findings)
**Decision flags:** `user_decision_required = true` (UD-04 authorization for scoped Stage-6 artifact use), `researcher_decision_required = false`

---

## 1. Purpose and boundary

This is a bounded licensing review. It does NOT implement Corpus Stage 6, does NOT
modify product code, and does NOT access raw corpus content beyond read-only
inspection of licensing metadata/documentation in the raw tree. It produces a
documented permitted-use matrix over the 12 required use categories, classifies
every category as one of three artifact classes, and states `PERMITTED` /
`CONDITIONAL` / `FAIL-CLOSED` with the documented basis.

This review does NOT assert an unrestricted open license for SWECCL 2.0 and does
NOT authorize redistribution of raw or derived corpus material. Categories that
cannot be resolved from documentation are fail-closed by design.

## 2. Governing evidence inventory

All paths relative to the worktree root unless noted. Every citation was
re-verified from disk during this run.

| # | Evidence | What it establishes | Verification |
| --- | --- | --- | --- |
| E1 | `docs/corpus-readiness/sweccl2/11_LIMITATIONS_AND_OPEN_ISSUES.md:43-48` | License status `PARTIALLY_DOCUMENTED`; corpus ships as published book (ISBN 978-7-5600-8015-4) with copyright page but no explicit corpus-use license in the manual; "Local preparation, analysis, and descriptive reporting are permitted; external distribution or learner-facing use REQUIRES_REVIEW." | line refs re-checked (43 heading, 45 status, 48 permission clause) |
| E2 | `docs/corpus-readiness/sweccl2/corpus_version.json` | Registered package `sweccl2-weccl20-v0.1.0`, manifest hash `0d8940ff...59eb9`, `license_status: "PARTIALLY_DOCUMENTED; external use REQUIRES_REVIEW"` | read verbatim |
| E3 | `docs/departments/research-evaluation-governance/foundation/03_CORPUS_USE_AND_LICENSE_POLICY.md` | RATIFIED policy `corpus-use-policy-v0.1.0` (RD-POL-003, 2026-08-07): authorization-state model `ALLOWED` / `REQUIRES_REVIEW` / `PROHIBITED` / `UNKNOWN`; operation x state matrix; review path; non-negotiable constraints | read verbatim |
| E4 | `docs/departments/research-evaluation-governance/foundation/policies/corpus_use_policy.json` | Machine artifact with statements CU-01..CU-12 (class + evidence per statement) | read verbatim |
| E5 | `docs/corpus-readiness/sweccl2/00_L2_CORPUS_READINESS_EXECUTIVE_SUMMARY.md` | RD-00 key constraints: raw corpus untouched; no raw texts in reports; no commits of raw corpus content or derived texts | read verbatim |
| E6 | `docs/corpus-readiness/sweccl2/12_L2_CORPUS_IMPLEMENTATION_HANDOFF.md` | Licensing/privacy constraints: PARTIALLY_DOCUMENTED; sensitive research data; no external uploads; no PII propagation; no raw corpus content in git | read verbatim |
| E7 | `docs/corpus-intelligence/l2/01_CORPUS_RESOURCE_REGISTRATION.md` | Registered resource identity + license_status field; hash-verified load | read verbatim |
| E8 | `docs/corpus-intelligence/l2/04_REFERENCE_GROUP_POLICY.md` | ReferenceGroupVersion `reference-groups-v0.1.0`; min-N=30; fallback hierarchy; duplicate policy | read verbatim |
| E9 | `docs/corpus-intelligence/l2/06_REFERENCE_DISTRIBUTIONS.md` | `reference-distributions-v0.1.0`; 1,050 records; statistics only; full provenance per record; missingness never imputed | read verbatim |
| E10 | `docs/corpus-intelligence/l2/07_CORPUS_INTELLIGENCE_QUERY_BOUNDARY.md` | Query boundary: every result `learner_exposure="research_only"`; no raw corpus text; no unrestricted examples; license-restricted operations out of boundary | read verbatim |
| E11 | `docs/corpus-intelligence/l2/09_STAGE5_VERIFICATION.md` | 36/36 focused tests; query smoke; byte-identical reproducibility (SHA-256 `900ee352...`); Stage 5/6 boundary check | read verbatim |
| E12 | `docs/corpus-intelligence/l2/10_STAGE6_IMPLEMENTATION_HANDOFF.md` | Stage 6 Work Units A-E; all consume governed/versioned artifacts; MUST NOT emit proficiency/mastery/learning-gain vocabulary, expose learner-facing corpus content (D-08), or use LLM for corpus statistics (I5) | read verbatim |
| E13 | `docs/departments/research-evaluation-governance/foundation/01_DECISION_INVENTORY.md` | C-01 (license canonicalized), A-09 (D-08 learner exposure), A-12 (D-24 gated scope), A-24 (corpus-grounded diagnosis gated), A-25 (D1/D3/D12 open) | read verbatim |
| E14 | `docs/architecture/writing-intelligence-platform/14_ARCHITECTURE_DECISIONS.md:77-84` | D-08: learner-facing corpus citations disabled by default; any learner-facing corpus excerpt requires Researcher decision + display policy + licensing/anonymization gate | line refs re-checked (L77/L80/L83) |
| E15 | `docs/architecture/writing-intelligence-platform/07_CORPUS_NLP_ARCHITECTURE.md:28` | I2: corpus is read-only reference data; learner text never written into corpus | line ref re-checked |
| E16 | `A:\EAP Agent Project\program-control\qualified-adrs\ADR-06-corpus-intelligence.json` | QUALIFIED (2026-08-09): raw SWECCL paths/handles rejected by generic runtime/retrieval/Skill/MCP pathways; only governed/versioned artifacts and approved query contracts cross the CORPUS boundary; enforcement testable; does NOT authorize Stage 6 | read verbatim |
| E17 | `A:\EAP Agent Project\program-control\WORKSTREAM_REGISTRY.json` (`external_corpus`) | Raw SWECCL: `CORPUS_ONLY` default; other departments consume versioned artifacts/query boundaries/shared contracts/governed evidence; GOV direct access only via separately authorized audit Goal | read verbatim |
| E18 | `A:\EAP Agent Project\program-control\USER_DECISION_BRIEF.md` / `.json` (UD-04) | UD-04 ACTIVE (open Researcher/authorization decision); options and tradeoffs; POLICY: PROGRAM never infers approval; lanes fail closed | read verbatim |
| E19 | Raw tree read-only inspection: `A:\[Linguistics Data] Corpus\SWECCL 2.0\SWECCL2.0_语料库概况报告.md` | Transcription of the 82-page manual (Pdg2Pic scan, no text layer): publisher FLTRP, 2008-12, ISBN 978-7-5600-8015-4, copyright page recorded (PDF p.4), stated purpose is to serve English teachers, teaching researchers, and graduate students (PDF p.11) — a purpose statement, not a license grant. No license/permission text is documented anywhere in the manual transcription. | read verbatim |
| E20 | Raw tree read-only inspection: directory listing of `A:\[Linguistics Data] Corpus\SWECCL 2.0` | Top level contains only `PREPARED/`, `SECCL20/`, `TOOLS/`, `WECCL20/`, `autorun.exe`, `autorun.inf` (DVD auto-run stub), `fltrp.avi`, and the 概况报告. No README, license, EULA, or permission file is present. Recursive scan for readme/license/说明/版权/手册/manual filenames found no such file (only corpus data files and the 概况报告). | directory listing + filtered recursive scan |
| E21 | `docs/corpus-intelligence/l2/02_FEATURE_CONTRACT.md`, `05_FEATURE_IMPLEMENTATION.md`, `08_REPRODUCIBILITY.md` | Feature contract `corpus-features-v0.1.0` (14 features); snapshots outside git under `PREPARED/corpus-intelligence/`; reproducibility requirements | referenced via E9/E11/E12 |

## 3. Artifact-class definitions

Every use category is classified by what the artifact can reconstruct, not by
where it lives.

| Class | Definition | Reconstructive? |
| --- | --- | --- |
| `RAW SOURCE` | The corpus files themselves (RAW/LEMMA/TAGGED texts, SECCL transcripts/audio, TOOLS), byte-level copies, or text-level copies. Content is original learner/transcriber text. | Yes — the original text itself |
| `NON-RECONSTRUCTIVE AGGREGATE ARTIFACT` | Statistics, distributions, numeric per-document feature snapshots, manifests, inventory/descriptor records. Contains no sentences or excerpts; original wording cannot be recovered from the artifact. | No |
| `TEXTUAL/RECONSTRUCTIVE DERIVATIVE` | Excerpts, quotations, examples, paraphrases, near-verbatim reproductions, derived text files, or any artifact from which original wording (or substantial portions) can be recovered. | Yes |

The three classes are mutually exclusive for a given artifact. Where a category
can hold artifacts of different classes (e.g., reproducibility artifacts), the
category is split and each split is classified separately.

## 4. Permitted-use matrix (12 categories)

Legend: disposition and basis apply to the documented scope of the category as
consumed by this platform. `FAIL-CLOSED` means the operation is not authorized
by any documentation reviewed here and must not proceed.

| # | Use category | Artifact class | Disposition | Documented basis | Conditions / notes |
| --- | --- | --- | --- | --- | --- |
| 1 | Local research processing | RAW SOURCE (consumed for analysis) | **PERMITTED** | E1 (RD-11:43-48: "Local preparation, analysis, and descriptive reporting are permitted"); CU-01 (`ALLOWED`: local deterministic analysis over prepared corpus texts); Stage 5 ran fully locally (E11) | Read-only (E15/I2); CORPUS-owned scope only (E17); no raw text committed to git or reports (E5/E6); package hash-verified (E2/E7) |
| 2 | Internal product-development processing | RAW SOURCE (internal pipeline) | **PERMITTED** | CU-03 (`ALLOWED`: research/development use inside the platform with `research_only` exposure); E14/D-08; E10/L2-07 (every query result carries `learner_exposure="research_only"`) | Internal only; learner-facing exposure disabled by default (E14); no unrestricted examples (E10) |
| 3 | Persistent derived statistics | NON-RECONSTRUCTIVE AGGREGATE ARTIFACT | **PERMITTED** | CU-02 (`ALLOWED`: aggregate internal statistics, descriptive reference distributions, internal research reporting, no raw text); E9 (statistics-only records, provenance per record) | Statistics only, no raw text; missingness never imputed; per-document snapshots stay outside git (E21/E5); versioned with manifest hash (E9) |
| 4 | Reference-group distributions | NON-RECONSTRUCTIVE AGGREGATE ARTIFACT | **PERMITTED** | CU-02; E8 (min-N=30 effective, duplicate policy applied, fallback hierarchy with disclosure); E13 A-12/D-24 (distributions gated on authorized corpus + licensing — the licensing condition is satisfied for this internal scope per CU-02) | min-N=30; requested/resolved group always disclosed; descriptive evidence only — no normative labels, no proficiency/mastery/learning-gain interpretation (E12; E13 A-01/A-08) |
| 5 | Feature-level aggregates | NON-RECONSTRUCTIVE AGGREGATE ARTIFACT | **PERMITTED** | CU-01; E21 (feature contract `corpus-features-v0.1.0`, 14 features, single implementation for corpus and student-compatible text); E12 (same FeatureSetVersion required both sides) | Same feature contract on both sides (I3); explicit unavailable states (I4); features needing unauthorized resources remain unavailable (lexical_sophistication `UNAVAILABLE` — D11 open) |
| 6 | Example / text excerpts (including any example index) | TEXTUAL/RECONSTRUCTIVE DERIVATIVE | **FAIL-CLOSED** | CU-10 (`PROHIBITED` at `PARTIALLY_DOCUMENTED` status: unrestricted corpus-example exposure through the query boundary); CU-05 + E14/D-08 (learner-facing corpus examples `REQUIRES_REVIEW` with display policy + licensing/anonymization gate); E1 (learner-facing use REQUIRES_REVIEW); E10 (no unrestricted examples exposed) | No license text or vendor grant found (E19/E20) that would support example display; stays fail-closed even internally as an index/retrieval surface (ADR-06, E16) |
| 7 | Reproducibility artifacts | Split: numeric/manifest layer = NON-RECONSTRUCTIVE AGGREGATE ARTIFACT; any textual reproduction = TEXTUAL/RECONSTRUCTIVE DERIVATIVE | **CONDITIONAL** | PERMITTED for the aggregate layer: CU-01/CU-02; E11 (byte-identical reproducible rebuild, SHA-256 `900ee352...`); E21 (snapshots outside git). FAIL-CLOSED for any raw/derived-text reproduction: CU-09 (`PROHIBITED` structural: raw corpus text in repository or reports); E5/E6 (no raw corpus content in git; derived texts stay outside the repository) | Reproducible numeric artifacts (manifests, inventories, distributions, numeric snapshots) permitted with provenance; any artifact that reproduces wording is fail-closed |
| 8 | Collaborator access | Depends on payload: governed artifacts = NON-RECONSTRUCTIVE AGGREGATE ARTIFACT; raw source = RAW SOURCE | **CONDITIONAL** | Internal departments: PERMITTED for governed/versioned artifacts, query boundaries, and shared contracts only (E17 `external_corpus`: `CORPUS_ONLY` default, other departments consume versioned artifacts; CU-03 internal research/development); GOV direct raw access only via a separately authorized audit Goal (E17). External/third-party collaborators: FAIL-CLOSED (CU-04/CU-08 `REQUIRES_REVIEW` unresolved) | Never share raw paths/handles with other departments (E16/E17); every artifact crossing the CORPUS boundary is governed/versioned and carries research_only exposure (E10) |
| 9 | Product/runtime exposure | Split: statistics via query boundary = NON-RECONSTRUCTIVE AGGREGATE ARTIFACT; any text/example exposure = TEXTUAL/RECONSTRUCTIVE DERIVATIVE | **CONDITIONAL** | Statistics-only exposure PERMITTED: CU-03; E10 (boundary returns distributions only, every result research_only). Any corpus text/example exposure FAIL-CLOSED: CU-05/CU-10; E14/D-08 (disabled by default); D-12 UI exposure remains open (E13 A-25) | Raw SWECCL must never be reachable through generic runtime, retrieval, Skills, MCP, UX, L2, ACAD, or LEARNER pathways (E16 ADR-06 constraints; raw_corpus_rule); only approved `corpus_query` contracts and governed artifacts may cross the CORPUS boundary |
| 10 | Export | Split: internal aggregate reporting = NON-RECONSTRUCTIVE AGGREGATE ARTIFACT; text export = TEXTUAL/RECONSTRUCTIVE DERIVATIVE | **CONDITIONAL** | Internal descriptive reporting of aggregate statistics PERMITTED: CU-02. External export of corpus text or unrestricted excerpts FAIL-CLOSED: CU-06 (`REQUIRES_REVIEW`: external API upload, no external uploads by default); CU-08 (`REQUIRES_REVIEW`: public release); CU-09 (no raw text in reports) | Any export beyond internal descriptive reporting requires a named review recording a legal basis (policy review path, 03_CORPUS_USE_AND_LICENSE_POLICY section 4); none exists today |
| 11 | External redistribution | TEXTUAL/RECONSTRUCTIVE DERIVATIVE | **FAIL-CLOSED** | CU-04 (`REQUIRES_REVIEW`: external redistribution of corpus texts or derived raw text); CU-08 (public release `REQUIRES_REVIEW`); CU-12 (`UNKNOWN`: commercial exploitation, sub-licensing, derivative corpus publication); E1 (external distribution REQUIRES_REVIEW); E19/E20 (no license text, vendor statement, or owner grant located) | This review explicitly does NOT authorize redistribution and does NOT assert an open license. No review of this category can succeed on current documentation; requires owner grant/license text or a named legal review (policy review path) |
| 12 | Raw corpus access | RAW SOURCE | **CONDITIONAL** | CORPUS-owned only, read-only by default, within explicitly authorized Goal scope (E17; identity packet read boundary); GOV direct access only via a separately authorized audit Goal (E17); every other department never — governed artifacts instead (E16/E17) | Any access outside the CORPUS-owned, read-only, Goal-scoped boundary is FAIL-CLOSED; no mutation (E15/I2); no raw path/handle through generic runtime/retrieval/Skills/MCP (E16) |

## 5. Summary by artifact class

| Class | Categories that may proceed (PERMITTED / CONDITIONAL within documented scope) | Categories fail-closed |
| --- | --- | --- |
| RAW SOURCE | 1, 2 (internal, read-only, CORPUS-owned); 12 (CORPUS-owned read-only, Goal-scoped) | 8 (external collaborators), 11 |
| NON-RECONSTRUCTIVE AGGREGATE ARTIFACT | 3, 4, 5 (PERMITTED); 7 aggregate layer, 9 statistics-only, 10 internal reporting (CONDITIONAL) | none — aggregate artifacts without text are the permitted core of Stage 5/6 |
| TEXTUAL/RECONSTRUCTIVE DERIVATIVE | none | 6 (examples/excerpts), 7 textual layer, 9 text exposure, 10 text export, 11 (external redistribution) |

## 6. UD-04 recommendation and Stage-6 unlock

### 6.1 What the documented review confirms

The RATIFIED policy (E3/E4) marks, with documented evidence:

- CU-01: local deterministic analysis over prepared corpus texts — `ALLOWED`;
- CU-02: aggregate internal statistics and descriptive internal research reporting — `ALLOWED`;
- CU-03: research and development use inside the platform with `research_only` exposure — `ALLOWED`.

Corpus Stage 6, as scoped in E12 (WU-A student FeatureSnapshot harness, WU-B
reference-group matching, WU-C comparison math as observed-descriptive evidence,
WU-D diagnostic gating design, WU-E protected-block evaluation design), consumes
only governed/versioned artifacts (E9/E10/E12): distributions, group memberships,
the feature contract, and numeric snapshots. Stage 6 is explicitly prohibited
from learner-facing corpus content (E14/D-08), from proficiency/mastery/
learning-gain vocabulary, and from LLM-computed corpus statistics (E12).

**Conclusion: governed/versioned Stage-6 artifact use is confirmed permitted for
the internal research-pipeline scope** (categories 1-5, and category 7 aggregate
layer): local deterministic processing, internal development, persistent
statistics, reference-group distributions, and feature-level aggregates, all with
`research_only` exposure and no raw text in outputs.

### 6.2 Recommendation

Resolve UD-04 **for that specific scope** (USER_DECISION_BRIEF option 1, scoped):
authorize governed/versioned artifact usage under this documented licensing
review for the internal research pipeline with `research_only` exposure. This
unlocks the corresponding **Stage-6 preparation Goal** (WU-A/B/C/E research-only
work) for assignment by Program Control.

The resolution must explicitly exclude, and leave fail-closed:

- learner-facing display or exposure of any corpus content (categories 6, 9-text,
  10-text) — requires the D-08 display policy and licensing/anonymization gate
  (E14) plus the D3 licensing-model determination;
- WU-D learner-facing diagnostic-gating output — same gates;
- external redistribution, export of text, model training, public release
  (categories 10-11; CU-04/CU-06/CU-07/CU-08/CU-12) — require a recorded owner
  grant/license text or a named legal review;
- any raw-source access outside CORPUS-owned read-only Goal scope (category 12).

If Program Control or the user declines the scoped authorization, the alternative
per UD-04 is to keep Stage 6 fully blocked and prepare public/owned corpora
(e.g., openly licensed learner corpora such as EFCAMDAT, ICLE-derivative or other
CC-licensed learner corpora, or owned student data with explicit consent
frameworks) as the evidence base for reference-group/distribution work.

### 6.3 Stage-6 status after this review

- **Stage 6 remains gated** until UD-04 is resolved by the user. This review is
  the documented-basis prerequisite; it does not itself authorize implementation.
- The unlock recommendation covers only the scoped research-only preparation
  WUs (A/B/C/E). WU-D (diagnostic gating with Feedback & Learner Intelligence)
  and any learner-facing scope stay blocked on D-08/D-12/D3 gates.
- Raw SWECCL remains CORPUS-owned; no raw-source access through generic runtime,
  retrieval, Skills, MCP, UX, L2, ACAD, or LEARNER pathways (E16).

## 7. Decision packet

Machine-readable decision packet for Program Control:
`docs/corpus-licensing/CORPUS-LICENSING-REVIEW.decision.json`

- `user_decision_required = true` — UD-04 authorization is the user's decision;
  PROGRAM policy never infers approval (E18).
- `researcher_decision_required = false` for the scoped unlock (the policy basis
  CU-01..CU-12 is already ratified under RD-POL-003); the D3 licensing model and
  any external-use grant remain separate Researcher/legal decisions recorded as
  dependencies remaining.

## 8. Fail-closed register (must not proceed without new authority)

1. Example/text excerpts and any example index (category 6).
2. Unrestricted corpus-example exposure through any query boundary (CU-10).
3. Learner-facing display of corpus content (CU-05, D-08) — includes WU-D output.
4. Textual reproducibility artifacts / derived texts in git or reports (CU-09).
5. External API upload of corpus texts (CU-06).
6. External redistribution, public release, model training, sub-licensing,
   derivative corpus publication (CU-04/CU-07/CU-08/CU-12).
7. Raw-source access outside CORPUS-owned read-only Goal scope (I2, E17).
8. Raw SWECCL path/handle injection through generic runtime/retrieval/Skill/MCP
   plumbing (ADR-06).

## 9. Verification performed

| Check | Result | Evidence |
| --- | --- | --- |
| Git preflight (root/branch/HEAD/worktree) | PASS | `A:/EAP Agent Project/worktrees/corpus`; branch `dept/corpus`; HEAD `5aafe2728d7135212bd675a6975b44bcf99ee099` = assigned baseline; pre-existing dirty/untracked files preserved untouched (path-portability work) |
| Governed policy artifacts read (E3/E4/E13/E14/E15) | PASS | read verbatim; policy `corpus-use-policy-v0.1.0` RATIFIED; CU-01..CU-12 recorded |
| ADR-06 + UD-04 brief read (E16/E18) | PASS | ADR-06 QUALIFIED; UD-04 ACTIVE; no inferred approval |
| Raw tree read-only inspection (E19/E20) | PASS | no license/README/EULA file; manual transcription documents copyright page + purpose only; no license grant text |
| Stage-5/Stage-6 evidence chain read (E7-E12, E21) | PASS | Stage 5 implemented with 36/36 tests; Stage 6 scope consumes governed artifacts only |
| 12-category matrix complete, classified, dispositioned | PASS | section 4; every category has artifact class + disposition + basis; unresolvable categories fail-closed |
| Write boundary respected | PASS | only new files under `docs/corpus-licensing/`; no existing file modified; no commit/push/PR |

## 10. Artifacts

- This report: `docs/corpus-licensing/CORPUS-LICENSING-REVIEW.md`
- Decision packet: `docs/corpus-licensing/CORPUS-LICENSING-REVIEW.decision.json`
- Machine handoff: `docs/corpus-licensing/handoff.json`

## 11. Notes and uncertainty

- This review is a documentation review, not a legal opinion. `PARTIALLY_DOCUMENTED`
  means no license text, vendor statement, or owner grant has been located; the
  manual transcription (E19) is based on a scanned PDF with no text layer and
  states figures were visually double-checked, but the original book remains the
  authority for any legal reading.
- If the owner later locates a license text or grant (e.g., FLTRP permission,
  or a written research-use authorization), categories 6/9-text/10-text/11 must be
  re-reviewed against that text before any status change.
- The categories marked CONDITIONAL are permitted only within the conditions
  stated; each condition is enforced by existing architecture contracts (I2/I3/I4,
  D-08, ADR-06) and the query boundary (E10).
