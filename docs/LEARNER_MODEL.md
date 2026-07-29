# Learner Model 2.0 v0.7

## Purpose and boundary

The learner model is an immutable, task-aware record of observed text signals. It is designed for formative feedback research and audit. It does not estimate language ability, mastery, learning, causal improvement, CEFR, CALF, or a score.

## Snapshot v2

Each `learner-profile-v0.7.0` snapshot records generation time, source submissions, representative submissions, excluded submissions and reasons, Task Clusters, Data Sufficiency, version-separated Metric and Diagnostic Trajectories, current learning targets, strength patterns, History Evidence, active configuration, input analysis versions, algorithm versions, confidence and limitations. New snapshots are append-only `LPS######`; old `LP######` snapshots remain readable.

## Current learning targets

A target is admitted only when the current Diagnostic Gate selected the category and current evidence relevance is `verified`. History may qualify that current target, but cannot create or reactivate it. At most two targets are returned and zero is valid. A recently reduced historical signal is not a current target unless the current Gate selects it again.

## Strength patterns

Only verified, quotable textual strengths can contribute. One observation is `observed_once`, two are `recurring_strength`, and three or more are `stable_strength_signal`. These labels remain text-feature observations rather than learner traits.

## Data sufficiency

- 0–1 representative task: `insufficient`.
- 2: `limited`; pairwise description only.
- 3–4: `provisional`.
- 5+: `adequate_for_descriptive_trend`.

The model also records time span, metadata gaps, revision duplicates, input-quality exclusions, analyzer compatibility, metric-version compatibility and valid metric counts. Thresholds are unvalidated prototype defaults.
