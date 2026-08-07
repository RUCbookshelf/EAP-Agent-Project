# 06 — Reference Distributions

## Artifacts

- `data/reference_distributions.jsonl` - 1,050 records
  (75 approved groups x 14 features).
- `data/distribution_version.json` - version
  `reference-distributions-v0.1.0`, algorithm
  `distribution-algorithm-v0.1.0`.
- Per-document feature snapshots (outside git):
  `A:\[Linguistics Data] Corpus\SWECCL 2.0\PREPARED\corpus-intelligence\feature_snapshots.csv`
  (69,300 rows).

## Statistics per record

n_effective, n_missing, n_raw, mean, median, std (ddof=1), IQR, quantiles
(5/25/50/75/95, numpy linear interpolation), min, max, availability,
validity_flags, duplicate_policy.

## Availability

1050/1050 records availability=available. 100 records carry validity flags,
all of type "missing values: N of M" (feature-level missingness, e.g.,
t_unit_proxy unavailable for fragment texts); none triggered
unavailable/limited at group level.

## Provenance per record

reference_group_id, feature_id, feature_set_version, reference_group_version,
distribution_version, corpus_package_id, manifest_hash - every record is
fully traceable to the corpus package and feature/group versions.

## Validity checks applied

- min-N: effective N >= 30 required for availability.
- missingness: recorded per record; missing values never imputed.
- degenerate distributions: zero-variance / zero-IQR flags.
- duplicate sensitivity: duplicate policy applied before statistics.
- prompt imbalance, length effects, timed/untimed differences: documented as
  group-level limitations in 04/11 rather than normalized away.
