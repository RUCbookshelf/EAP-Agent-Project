# 05 — Duplicate Policy

**Department:** Research Evaluation & Data Governance
**Policy id:** `duplicate-handling-policy-v0.1.0`
**Ratification:** RD-POL-005 (2026-08-07)
**Status:** RATIFIED (per-purpose; Stage-5 duplicate strategy reviewed and ratified with conditions)
**Supersedes:** none (first canonical version)

## 1. Purpose

This policy reviews the Stage-5 duplicate strategy
(`effective_sample_excludes_non_canonical_duplicate_members`, canonical =
lexicographically smallest document_id; L2-03:26-35; L2-10:49-51) and decides, per
purpose, how duplicates are handled. One policy need not serve all purposes, and it
does not.

## 2. Verified facts (evidence base)

| Fact | Value | Evidence |
| --- | --- | --- |
| Scope-level duplicate groups | 348 (raw 127 / lemma 117 / tagged 104), all groups of size 2, 696 member records | `data/duplicate_report.csv` (RD-06); methodology review D2 |
| Document-level fold | `Path(member).stem` normalization + deterministic last-wins; every document maps to at most one document-level group | methodology review D2 condition 1; L2-03:26-29 |
| Affected documents | 240 unique physical documents | L2-03; L2-10:80; RD-06 |
| Folded groups | 120 groups × 2 documents; 120 canonical + 120 non-canonical | methodology review D2 |
| Canonical rule | lexicographically smallest document_id per group | L2-03:29; independent review §5 |
| Reference membership | canonical members only; 0 non-canonical leakage; per-group rows == n_effective | independent review §5; `reference_group_membership.csv` (33,543 rows) |
| Physical preservation | all 4,950 documents remain in `corpus_manifest.csv`; nothing deleted | RD-06; L2-03:31-33 |
| Overlap with scored block | 0 (duplicate-group members ∩ EXP01 scored docs = ∅) | methodology review D3 |
| Evaluation holdout rows | 240 `duplicate-group member` rows in `holdout_candidates.csv`, all CANDIDATE | RD-10; independent review §7 |
| Methodology review | D2 APPROVED_WITH_CONDITIONS (condition 1 = document-level fold wording; applied in L2-03) | `evidence/methodology_review.md` |

## 3. Definitions (canonical)

- **Physical N** — the count of source documents as stored (4,950 logical texts in the
  manifest, including all duplicate members and the corrupt WARG2081). Never reduced;
  source records are never deleted.
- **Logical N** — the count of distinct text content after duplicate detection:
  4,830 (= 4,950 − 120 duplicate copies in folded groups). Identity here is defined by
  the scope-level duplicate evidence folded deterministically at document level; it is
  a data-hygiene count, not a semantic-uniqueness claim.
- **Effective N** — the count used for reference statistics: canonical
  (representative) members only, after excluding non-canonical duplicate members.
  Per group, `n_effective` equals the group's membership rows and is `<= n_raw`.
- **Duplicate-group identity** — the deterministic document-level group a document
  belongs to (folded from scope-level evidence; at most one group per document);
  stable across versions of the fold rule.
- **Representative selection** — the deterministic rule choosing the canonical member
  (lexicographically smallest document_id). Arbitrary but auditable and reproducible;
  it is not a content-quality or recency claim.
- **Evaluation isolation** — the constraint that duplicate-group members are never
  split across development/evaluation boundaries (RD-10:37-42; L2-10:72-75); enforced
  by holdout candidacy (240 rows) and by 10_EVALUATION_LEAKAGE_POLICY.md.

## 4. Per-purpose decisions

### 4.1 Descriptive corpus statistics — RATIFIED (unchanged behavior)

Physical counts include all documents; duplicates are reported as a documented quality
fact (348 groups / 240 documents), never silently removed. No collapsing in descriptive
counts. Evidence: RD-06; L2-03:31-33.

### 4.2 Reference distributions — RATIFIED (effective membership)

Reference distributions use effective membership (canonical members only) so that
near-identical texts do not double-count in distributional statistics. This is a
versioned Research decision (RD-POL-005) with the following conditions:

1. Non-canonical members remain in physical records and manifests (never deleted).
2. Every distribution record carries the duplicate policy id (L2-06 provenance).
3. The representative rule is deterministic and documented; any future change of the
   rule is a major policy amendment with methodological review (02 §2/§5).
4. Missingness and duplicate sensitivity are reported per distribution (L2-06 validity
   checks), not normalized away.

### 4.3 Evaluation — RATIFIED (isolation, no splits)

Duplicate-group members are never split across dev/eval; the 240 members are protected
holdout candidates; any partition must be reproducible and versioned (WU10). This
ratifies RD-10:37-42 and L2-10:72-75.

### 4.4 Future model development — NOT SETTLED (separate decision required)

The Stage-5 duplicate policy does **not** automatically extend to model development.
When a training/evaluation design exists, a separate Researcher decision must define
duplicate handling for that purpose (e.g., whether non-canonical members may be used in
training, what leakage controls apply). This is recorded as an integration dependency
for Architecture & Integration and as an open Researcher decision; nothing here
authorizes training use.

## 5. Research decision (ratification record)

- **Decision:** ratify `effective_sample_excludes_non_canonical_duplicate_members` for
  purposes 4.1-4.3 as the versioned duplicate-handling policy of this department.
- **Rationale:** deterministic, auditable, reproducible; preserves physical records;
  prevents double counting in reference statistics; prevents leakage in evaluation;
  explicitly does not extend to model development without a further decision.
- **Alternatives rejected:** random representative selection (non-deterministic);
  deletion of non-canonical members (destructive, prohibited); per-group manual
  selection (not reproducible); content-similarity deduplication at v0.1 (no validated
  similarity contract).
- **Conditions:** representative-rule changes require methodological review; model
  development requires a separate decision; corpus implementation is unchanged.

## 6. Integration posture

No Corpus implementation or data artifact is modified by this policy. If a future
decision changes duplicate handling, it must be routed through Architecture & Integration
when it touches the query boundary, membership artifacts, or partitions (ARCH-13 §1);
never silently in Corpus feature code.

## 7. Machine artifact

`policies/duplicate_policy.json` mirrors section 4 and validates against
`policies/policy_schema.json` (WU11).