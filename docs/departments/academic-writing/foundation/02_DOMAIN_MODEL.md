# 02 — Academic Writing Domain Model

**Goal:** Academic Writing Domain Foundation (Wave-1)
**Baseline:** b171cce | **Branch:** dept/academic-foundation
**Date:** 2026-08-07 | **Status:** WU2 GREEN (entity contracts implemented and tested)

## 1. Purpose

The seven frozen Domain A entities plus the D-32 verification record, implemented as self-contained Pydantic v2 models in `app/academic/entities.py` (zero imports from existing L2 modules). The module is the single source of truth for entity shapes used by provenance, integrity, repository, service, and citation work units.

## 2. Design conventions

- Pydantic v2 `BaseModel` with `ConfigDict(extra="forbid", frozen=True)` on every model — schema discipline (charter) and immutability (edits create new versions; never overwrite).
- Stable string IDs with per-type prefixes and pattern `^<prefix>-[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`; prefix namespaces never collide with L2 ID families (`PRIO-`, `LPS######`, `HE######`, `AR/MT/DC/...`).
- Domain-local Literal statuses exactly as frozen by the architecture (05_ACADEMIC_WRITING_DOMAIN.md); no invented closed taxonomies where the architecture leaves content open (`source_type`, `section_kind` are free text; `NR` taxonomy decisions preserved).
- Timestamps via `utc_now()`; `created_at`/`updated_at` on every mutable entity; `run_time` always explicit on verification records.
- Shared-vocabulary alignment (WU5): `epistemic_status` uses the frozen four-layer values; Academic verification states use the frozen 05:4.3 vocabulary (`verified | unverified | verification_unavailable`) — distinct from the registry-layer 8-value evidence-status vocabulary (alignment belongs to Shared Core registries, not entity fields).

## 3. Entities

### 3.1 ResearchProject (`rp-`)
| Field | Type | Notes |
| --- | --- | --- |
| project_id | str | pattern `rp-...` |
| title | str | 1-200, stripped, non-blank |
| research_scope | str \| None | <= 2000 |
| status | ProjectStatus | `active` (default) \| `archived` |
| created_at / updated_at | datetime | utc_now defaults |

### 3.2 ResearchQuestion (`rq-`)
question_id, project_id (`rp-`), question_text (1-1000), version int >= 1 (default 1; question-versioning depth = Researcher decision required), created_at, updated_at. Relates to EvidenceUnits, Claims, and PaperSections via list fields (many-to-many; no implication that every section maps to exactly one RQ).

### 3.3 Source (`src-`)
| Field | Type | Notes |
| --- | --- | --- |
| source_id / project_id | str | `src-` / `rp-` |
| title | str | 1-500 |
| authors, publication | str \| None | free text |
| year | int \| None | 1000-2100; absent = no metadata invented |
| doi | str \| None | never assumed |
| source_type | str \| None | free text (taxonomy NR) |
| origin | SourceOrigin | `learner_entered` \| `imported_file` (source provenance) |
| availability | SourceAvailability | `active` (default) \| `unavailable` \| `removed` (removed = deletion; guardrail target) |
| file_name / file_hash | str \| None | file identity; hash must be 64-hex |
| source_text / source_text_hash | str \| None | optional uploaded text; hash = sha256(text) enforced by model validator; text absent => hash None |
| version | int | >= 1; `new_version(**updates)` returns a new Source with version+1 and refreshed updated_at |

Source provenance chain: origin + file identity + text hash + version + availability. No external metadata fetch (non-goal).

### 3.4 EvidenceUnit (`ev-`)
| Field | Type | Notes |
| --- | --- | --- |
| evidence_id / project_id / source_id | str | `ev-` / `rp-` / `src-` |
| source_version | int | >= 1; evidence locations pin a specific source version |
| kind | EvidenceKind | `direct_quote` \| `learner_paraphrase` |
| locator | str | exact location (1-500) |
| content | str | captured content (1-20000) |
| verification_status | EvidenceVerificationStatus | `unverified` (default) \| `verified` \| `verification_unavailable` |
| epistemic_status | EpistemicStatus | `observed_descriptive` (default); shared vocabulary (WU5) |
| learner_note / model_interpretation | str \| None | notes/interpretation separation (goal section 11); model output is never evidence content |
| rq_ids | list[str] | many-to-many to ResearchQuestion |

Evidence provenance chain: kind + exact location + source version + verification status; quotes are the learner's own source text, paraphrases explicitly learner-authored.

### 3.5 ClaimEvidenceLink + Claim (`cl-`)
- **ClaimEvidenceLink**: evidence_id (`ev-`), link_type (`supports | contradicts | contextualizes | related` — frozen 05:4.4), created_at. Typed claim-evidence relationship.
- **Claim**: claim_id, project_id, claim_text (1-5000), support_state (`supported | partially_supported | unsupported | undetermined`, default `unsupported`; never inferred), rq_ids, section_ids, evidence_links (list[ClaimEvidenceLink]).
- Entity invariant (model_validator): no evidence links => support_state must be `unsupported` or `undetermined`; `supported` requires at least one `supports` link; `partially_supported` requires at least one link.
- Claim-evidence provenance chain: typed links + aggregate support state; a claim without links is `unsupported` by construction.

### 3.6 PaperSection (`sec-`)
section_id, project_id, section_title (1-500), section_kind (free text, <= 100), order (>= 0), parent_section_id (`sec-` | None; nesting), status (`planned | drafted | reviewed`, default `planned`), passage_span (| None, <= 500, manuscript anchor), rq_ids. Logical manuscript structure only — no rich-text editor, no frontend binding (non-goals).

### 3.7 CitationLink (`cit-`)
citation_id, project_id, claim_id (`cl-`), source_id (`src-`), evidence_id (`ev-` | None), passage_span (| None), verification_status (`unverified` default | `verified` | `verification_unavailable`). The only place citation verification outcomes are stored (05:4.3). `verified` is impossible without an append-only record by construction at the repository/service layer (named invariant ACAD-INV-02, enforced in WU8).

### 3.8 CitationVerificationRecord (`vr-`) — D-32 append-only record
record_id, citation_id (`cit-`), rule_id, rule_version (non-blank, <= 100), source_revision_hash (64-hex | None), matched_spans (list[str]), run_time (explicit), result (`verified | unverified | verification_unavailable` — unified vocabulary, no `not_verified` drift), created_by (`system | learner`, default `system`), created_at.
Entity invariants: `verified` requires source_revision_hash; `verification_unavailable` requires hash None. The versioned verification-rule manifest ships in WU8 (rule_id/rule_version resolve against it — contract test).

## 4. Validation discipline

- `extra="forbid"` on all models (parameterized test).
- `frozen=True`; attribute assignment raises ValidationError; `model_copy(update=...)` produces new versions.
- Per-prefix ID validators on every ID-bearing field and list item; duplicate IDs rejected.
- Required text fields stripped and rejected when blank; length bounds enforced.
- Source text/hash consistency; file_hash format; year bounds.
- Non-str inputs raise ValueError (pydantic-convertible) — no raw AttributeError/TypeError leaks.
- Cross-entity invariants are NOT entity validators (see section 6): they live in the integrity service and repositories as named invariants (WU4/WU6).

## 5. Serialization

`model_dump_json()` / `model_validate_json()` round-trip tested for every entity; datetime fields serialize to ISO-8601; lists default to fresh `[]` instances.

## 6. Invariant ownership map

| Invariant | Layer | Work unit |
| --- | --- | --- |
| Claim support-state / link consistency | entity (model_validator) | WU2 |
| Record verified/unavailable hash rules | entity | WU2 |
| ACAD-INV-02: CitationLink verified => >=1 CitationVerificationRecord(result=verified) for same citation_id | repository + citation service | WU6/WU8 |
| Cross-project membership of references | integrity service | WU4 |
| Deleted source still referenced | integrity service | WU4 |
| EvidenceUnit source_version exists on referenced Source | integrity service | WU4 |
| Citation link references unrelated evidence | integrity service | WU4 |

## 7. Review status

Independent DeepSeek review: APPROVE_WITH_FINDINGS (8 findings). All dispositioned: F1/F3/F4/F5/F8 fixed; F6 retained (goal section 11 interpretation separation); F7 partially fixed (created_by added; manifest in WU8); F2 deferred as ACAD-INV-02. Focused suite: 85 passed / 0 failed.

## 8. Evidence

- `app/academic/entities.py`
- `tests/academic/test_entities.py`
- `.agent-workflow/academic-writing-foundation/evidence/wu2-review.md` (noncanonical runtime)
- Frozen references: 05_ACADEMIC_WRITING_DOMAIN.md sections 3-6; 14_ARCHITECTURE_DECISIONS.md D-32