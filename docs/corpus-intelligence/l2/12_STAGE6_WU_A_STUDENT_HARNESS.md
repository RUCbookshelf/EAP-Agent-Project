# 12 - Stage 6 WU-A: Student FeatureSnapshot Harness

## Purpose

WU-A provides the research harness that runs the SAME v0.1 feature extractor
(`app/corpus/features.py::extract_features`) over student submissions and
returns a governed, versioned, numeric-only `StudentFeatureSnapshot` with
explicit eligibility checks - ready for WU-B matching and WU-C comparison
without touching corpus files or preparation CSVs.

## Module

`app/corpus/student.py`

- `extract_student_features(text, submission_id=None, feature_ids=None)`
  - rejects input whose first line starts with `<STU` (corpus header format;
    the corpus batch adapter strips that header from corpus texts, and the
    student side must not contain it) - fail closed;
  - rejects path-shaped `submission_id` values (path separators / drive
    letters) - no raw path/handle injection into the harness (ADR-06);
  - returns a `StudentFeatureSnapshot` that structurally retains NO raw
    text (`text_retained=False`; artifact class NON-RECONSTRUCTIVE
    AGGREGATE ARTIFACT).
- `recheck_eligibility(snapshot, required_feature_set_version)` - re-runs
  the machine-checkable version/no-text checks at any later point.
- `EligibilityCheck` - one check with id/description/result (`pass` /
  `warning` / `fail`) and detail.

## Versions and provenance

| Field | Value |
| --- | --- |
| artifact_version | `student-feature-snapshot-v0.1.0` |
| processing_version | `student-harness-v0.1.0` |
| feature_set_version | `corpus-features-v0.1.0` |
| extractor | spaCy `en_core_web_sm` 3.8.0 |
| learner_exposure | `research_only` |

Every snapshot exposes `provenance` with those fields.

## Eligibility checks

- `feature_set_version` - all snapshots must carry the registered
  `corpus-features-v0.1.0`; mismatch is a `fail`.
- `corpus_header_absent` - corpus-header input is rejected before
  extraction.
- `minimum_evidence` - empty input produces a `warning` (extraction still
  returns zero/unavailable values per the Stage-5 contract).
- `feature_availability` - features with `analysis_status="unavailable"`
  (e.g. `t_unit_proxy` on fragments) are listed as a `warning`; WU-C reports
  them as explicit unavailable comparisons, never imputed.

## Licensing / disclosure

- NON-RECONSTRUCTIVE AGGREGATE ARTIFACT: only numbers and statuses are
  retained; raw submission text is never stored, logged, or attached.
- `learner_exposure="research_only"` on every snapshot; no production or
  learner-facing path exists in this module.
- No proficiency/mastery/learning-gain vocabulary; no LLM computation.
