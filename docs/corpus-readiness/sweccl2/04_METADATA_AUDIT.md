# 04 — Metadata Audit

## WECCL 2.0 (canonical manifest: `data/corpus_manifest.csv`)

All 4,950 logical texts have parsed headers (metadata coverage 100% on every
dimension; see `data/metadata_coverage.csv`).

### Normalized vocabulary (used in this package)

| Dimension | Values |
| --- | --- |
| domain | l2_writing |
| corpus | weccl_2_0 |
| genre | argumentative / expository |
| prompt_id | ARG01-ARG26, EXP01 |
| major_type | english_major / non_english_major |
| entry_year | 2003-2007 |
| grade | 1-4 |
| timed_status | timed / untimed |

### Documented-vs-physical counts (all MATCH)

| Dimension | Value | N |
| --- | --- | --- |
| genre | argumentative / expository | 4,680 / 270 |
| major_type | english / non-english | 4,359 / 591 |
| entry_year | 2003/2004/2005/2006/2007 | 68/307/1,672/2,450/453 |
| grade | 1/2/3/4 | 1,549/2,172/1,108/121 |
| timed_status | timed / untimed | 2,499 / 2,451 |
| prompt | ARG01..ARG26, EXP01 | matches manual per-prompt counts (e.g., ARG17 656, ARG23 391, EXP01 270) |

One document (WARG2081) has corrupt RAW/LEMMA variants; its metadata was parsed
from the intact TAGGED header (`metadata_source = tagged`). Filename prefix
agrees with header genre for all 4,950 documents (0 conflicts).

## SECCL 2.0 transcripts (`data/seccl_manifest.csv`)

- 2,852 transcripts, all eight documented header tags parsed (SPOKEN, TEM4,
  GRADE, YEAR, GROUP, TASKTYPE, SEX, RANK): 2,852/2,852 `parsed`.
- Task folders: TASK1/TASK2/TASK3/TASK123 = 713 each; years 2003-2006;
  6 groups per year; transcript IDs encode year-group-slot-role (e.g.,
  03-130-15B).
- Exam tag: TEM4 for all 2,852 (TEM8 component absent in this physical copy).

## Reliability statements

- Reliable: all six WECCL dimensions (header tags consistent with the manual's
  own tables), filename-to-genre mapping, SECCL header tags and folder
  structure.
- Unreliable/absent: no learner identity beyond document IDs (no cross-text
  learner linkage); no scores in headers (scores exist only for the 270
  expository texts via TOOLS/exp.sav + exp.xls); TEM8 metadata unavailable.
