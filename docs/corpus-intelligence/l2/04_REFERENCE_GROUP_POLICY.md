# 04 — Reference Group Policy

## ReferenceGroupVersion

`reference-groups-v0.1.0` (machine artifact: `data/reference_group_version.json`).
Groups derive from the preparation-phase candidate set (42 candidates) plus
prompt x timed combinations validated against actual metadata.

## Minimum-N policy

- min-N = 30 effective documents (after duplicate policy).
- Rationale: conservative descriptive stability for percentile-based
  reference statistics at the scale of this corpus; exploratory minimum
  carried into an explicit policy. This is NOT a normative/scientific
  sufficiency claim and remains reviewable by Research Evaluation.
- Feature-specific concern: all v0.1 features share min-N=30; features with
  higher missingness are additionally flagged per distribution.
- ARG13 (n_raw=14) and ARG19 (n_raw=18) remain unavailable as standalone
  distributions; their documents still participate in broader groups
  (genre, prompt+timed where applicable).

## Approved groups

75 groups = 25 approved prompt-only + 35 approved prompt x timed + 2 genre + 2 timed + 2 major type + 4 grade + 5 entry year. (ARG13/ARG19 prompt-only groups exist but are unavailable as standalone distributions, so the approved prompt-only count is 25, not 27; 35 prompt x timed combinations meet min-N.)
Machine artifact: `data/reference_group_membership.csv`.

## Unavailable groups

- ARG13, ARG19 standalone distributions (too sparse).
- Any group whose effective N falls below 30 after duplicate policy
  (e.g., prompt x timed combinations not listed above).
- Unknown/unsupported group ids raise CorpusInvalidRequestError.

## Fallback policy (deterministic, disclosed)

Hierarchy: prompt+timed -> prompt -> genre+timed -> genre -> UNAVAILABLE.
Genre is derived from the prompt prefix when not supplied (ARG -> argumentative,
EXP -> expository). Every query result reports the requested group and the
actually resolved group; silent broadening is impossible by construction.

## Duplicate policy application

All group memberships and distributions apply the effective-sample duplicate
policy from 03.
