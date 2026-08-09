# 13 - Stage 6 WU-B: TaskSignature Reference-Group Matching

## Purpose

WU-B maps a research submission's task properties to an approved reference
group through the Stage-5 deterministic fallback hierarchy (prompt+timed ->
prompt -> genre+timed -> genre -> UNAVAILABLE) with explicit unmatched
states and full disclosure of requested vs resolved group.

## Module

`app/corpus/tasksignature.py`

- `TaskSignature(prompt_id, timed_status, genre)` - validated semantic task
  values only:
  - `prompt_id`: `ARG##` / `EXP##` (or None);
  - `timed_status`: `timed` / `untimed` (or None);
  - `genre`: `argumentative` / `expository` (or None).
  - Genre may be derived from the prompt prefix (ARG -> argumentative,
    EXP -> expository) and the derivation is disclosed in the result.
- `ReferenceGroupMatcher.match(signature) -> TaskMatchResult`
  - exact match: requested group resolved, `fallback_disclosure=None`;
  - fallback match: resolved group disclosed with the requested candidate
    recorded as the fallback disclosure - silent broadening is impossible;
  - explicit unmatched states (`matched=False` + reason):
    - incomplete signature (neither prompt nor genre);
    - no reference group available (all candidates below min-N or absent).

## Same-FeatureSetVersion enforcement

Every `TaskMatchResult` carries the required `feature_set_version`
(`corpus-features-v0.1.0`); WU-C refuses any comparison whose snapshot or
distribution version differs from it.

## Versions and provenance

| Field | Value |
| --- | --- |
| artifact_version | `task-match-result-v0.1.0` |
| processing_version | `task-matcher-v0.1.0` |
| reference_group_version | `reference-groups-v0.1.0` |
| corpus_package_id | `sweccl2-weccl20-v0.1.0` |
| learner_exposure | `research_only` |

The result also records the corpus package manifest hash from the Stage-5
boundary and the requested task dictionary (including derived genre).

## Safety

- No raw corpus path or handle can enter the matcher: inputs are semantic
  task values only.
- Unmatched states are explicit and machine-checkable; no silent widening.
