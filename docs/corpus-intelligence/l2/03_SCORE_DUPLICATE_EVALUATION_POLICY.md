# 03 — Score Linkage, Duplicate Policy, Evaluation Protection

## Score linkage result (WU3.1)

TOOLS/exp.xls and TOOLS/exp.sav were inspected with local readers (xlrd,
pyreadstat):

| Check | Result |
| --- | --- |
| exp.xls rows | 270 (+ header), sheet "scores", 8 columns |
| exp.sav rows | 270, identical 8 columns |
| Linkage key | ID = WEXP#### (exact match to corpus document IDs) |
| Coverage | 270/270 (set equality with manifest EXP01 documents) |
| Ambiguity | none (270 unique IDs, 0 duplicates) |
| Missingness | 0 (all score fields populated) |
| Score fields | Rater_A, Rater_B, Rater_C (100-scale); Language, Content, Organization; Average_score |

One reading artifact: xlrd reports an OLE2 inconsistency warning for exp.xls
(SSCS size 0); the file reads correctly and the warning does not affect
content.

Status: score linkage ESTABLISHED for evaluation readiness. Scores are NOT
incorporated into any learner-facing Corpus Intelligence; the 270 expository
texts remain a protected evaluation block.

## Duplicate policy (WU3.2)

- Duplicate provenance: `data/duplicate_report.csv` (preparation phase) provides duplicate evidence per scope (raw text / raw bytes / lemma bytes / tagged bytes). At document level, evidence is folded deterministically: a document appears in a duplicate group if it appears in any scope, and each document maps to exactly one document-level group (last-wins deterministic fold on member stems normalized via Path(member).stem; 240 affected documents, 120 folded groups).
- Canonical representative per group: lexicographically smallest document_id.
- Reference distribution samples use EFFECTIVE membership (canonical members
  only). Non-canonical members are excluded from effective N but never
  deleted and remain in physical counts.
- Descriptive corpus counts (reported in readiness docs) keep all documents.
- Duplicate policy identifier:
  `effective_sample_excludes_non_canonical_duplicate_members`, recorded in
  every distribution record.

## Evaluation protection (WU3.3)

- 270 scored expository texts: protected block; no use as development
  material without Research Evaluation approval.
- Duplicate-group members: never split across dev/eval.
- No irreversible final train/dev/test partition is created by Stage 5.

## Approval status

Policies above are proposed by the Corpus & NLP department and require the
explicit Research/Methodology review recorded in `evidence/` (see
methodology approval note) before WU4 distributions are treated as final
policy.
