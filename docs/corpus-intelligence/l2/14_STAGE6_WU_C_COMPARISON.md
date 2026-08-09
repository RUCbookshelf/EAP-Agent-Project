# 14 - Stage 6 WU-C: Observed-Descriptive Comparison Math

## Purpose

WU-C computes within-group comparison statistics for one student feature
snapshot against an approved reference-group distribution, as
observed-descriptive evidence only (D-07). No normative labels exist in the
result objects - structurally (verified by tests).

## Module

`app/corpus/comparison.py`

- `estimated_percentile(value, dist)` - piecewise-linear interpolation over
  the recorded minimum, maximum, and quantiles (5/25/50/75/95), value clamped
  to [min, max]. Documented approximation, not an exact rank; the method is
  disclosed on every result (`percentile_method`).
- `z_distance(value, dist)` - `(value - mean) / std`; None (with limitation)
  when mean/std are missing or std is zero (degenerate distribution).
- `ComparisonEngine.compare(snapshot, match, feature_ids=None)` - one
  snapshot against one matched group, through the Stage-5 query boundary;
  returns `SnapshotComparisonResult` with per-feature
  `FeatureComparisonResult` objects and available/unavailable counts.

## Same-FeatureSetVersion enforcement

Comparison fails closed (`CorpusInvalidRequestError`) unless snapshot,
distribution, and required versions are all `corpus-features-v0.1.0`
(Stage-6 I3: no cross-version comparisons).

## Explicit unavailable states (never imputed)

- Student feature `analysis_status="unavailable"` -> unavailable result;
- distribution missing or not `available` -> unavailable result with the
  boundary reason;
- degenerate distribution -> `z_distance=None` with validity flags carried
  into `distance_limitations`.

## No normative interpretation

- Result objects carry no label/proficiency/mastery/learning-gain/rank/band
  fields (structural, verified by test).
- `evidence_class="observed_descriptive"` on every comparison.
- No LLM computation (I5); deterministic local math only.

## Versions and provenance

| Field | Value |
| --- | --- |
| artifact_version | `feature-comparison-v0.1.0` |
| processing_version | `comparison-engine-v0.1.0` |
| algorithm_version | `comparison-algorithm-v0.1.0` |
| learner_exposure | `research_only` |

Every result records corpus package id, manifest hash, resolved reference
group id, reference group version, distribution version, feature set
version, and effective N.
