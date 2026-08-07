# 06 — Data Quality and Duplicates

Data: `data/quality_issues.csv`, `data/duplicate_report.csv`,
`data/corpus_exclusions_draft.csv`, `data/quality_summary.json`.

## Quality findings (90 total)

| Issue type | Severity | N |
| --- | --- | --- |
| all_nul_bytes (WARG2081 RAW + LEMMA) | high | 2 |
| extremely_short_text (WARG2081, 1 token) | candidate | 1 |
| variant_identical_bytes (WARG3437 LEMMA==RAW) | candidate | 1 |
| non_ascii_learner_content (37 RAW + 37 LEMMA) | info | 74 |
| chinese_annotator_note_in_transcript (SECCL) | info | 12 |

Notes: non-ASCII WECCL content is learner-typed (Chinese chars, fullwidth
punctuation, ideographic spaces) and is preserved as-is. SECCL transcripts
contain Chinese transcriber annotations (e.g., "未录完", "以下AB全反") embedded
in the text; these are annotator notes, not learner speech.

## Duplicates (348 groups)

| Scope | Kind | Groups |
| --- | --- | --- |
| weccl_raw | exact_byte_duplicate | 12 (24 files, identical headers) |
| weccl_raw | exact_duplicate_text (normalized) | 115 (230 files, identical headers) |
| weccl_lemma | exact_byte_duplicate | 117 |
| weccl_tagged | exact_byte_duplicate | 104 |

240 unique documents are touched by duplicate groups. LEMMA/TAGGED byte
duplicates exceed RAW because lemmatization/tagging collapses surface
variation in near-identical texts - a strong near-duplicate signal.

Classification: physical duplicates (same bytes) and logical duplicates
(same normalized text) with identical metadata headers; treated as possible
repeated learner submissions / data-entry duplication. No text is deleted;
all remain CANDIDATE review items and must be handled in partitioning
(see 10).

## Length profile (RAW, header excluded)

Median 242 tokens, mean 252.1, p1 99, p5 126, p95 407, max 1,076, min 1
(WARG2081 corrupt).

## Candidate exclusions (draft only)

- WECCL20/RAW/WARG2081.txt (all-NUL)
- WECCL20/LEMMA/WARG2081.txt (all-NUL)

Exclusion status remains candidate; final exclusion decisions belong to the
next Goal with Researcher review.
