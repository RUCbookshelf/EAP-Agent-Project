# v0.3 comparability rules

Rule version: `comparability-v0.3.0`.

## Necessary conditions

- same pseudonymous student;
- both texts nonblank;
- both metric records available.

Different students are `not_comparable`; missing text/metrics is `insufficient_information`.

## Important conditions

- Genre mismatch is `not_comparable` for the primary cohort.
- Differences in timed status, tool use, draft stage or recorded time limit produce `partially_comparable`.

## Limit conditions

- Prompt token Jaccard overlap below 0.25 records a topic/task-family limitation.
- Word-count difference ratio above 0.50 records a length limitation.
- Analysis-version mismatch records a compatibility limitation.
- Submission intervals below 1 hour or above 730 days record context limitations.

Limit conditions reduce a record to `partially_comparable`; it remains in history/background but is excluded from default primary trends. `comparable_only=false` can expose a sensitivity view, which remains lower-confidence context. Every result lists matched fields, mismatches, reasons, confidence and rule version.

These thresholds are working assumptions, not validated task-equivalence criteria.
