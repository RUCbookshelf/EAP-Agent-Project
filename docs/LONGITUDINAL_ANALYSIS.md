# v0.3 longitudinal analysis

## Personal baseline

The newest submission is the comparison anchor. Only the anchor and earlier records classified `comparable` enter the primary cohort. A baseline requires 3 records. Available baselines report mean, median, minimum and maximum for each metric plus structured diagnosis frequencies; insufficient baselines report no metric summaries. This is a descriptive personal reference, not true language ability.

## Metric trend

For each of the eight v0.1 metrics, observations retain submission ID, date, value, comparability status, inclusion flag and exclusion reason. With fewer than 3 eligible values, direction is `insufficient_data`. Otherwise:

1. ordinary least-squares slope is computed over ordered submission index;
2. first-to-last relative change is compared with ±10%;
3. directions are `increasing`, `decreasing` or `stable`;
4. high variability overrides direction as `fluctuating`.

Descriptive volume metrics and text-length-sensitive metrics carry distinct limitations. Directions never indicate writing quality or ability level.

## Variability

Coefficient of variation uses population standard deviation divided by absolute mean. CV ≤ 0.10 is `low`; 0.10–0.25 is `moderate`; > 0.25 is `high`; fewer than 3 points is `insufficient_data`.

## Confidence

Confidence considers eligible point count, variability, analysis-version consistency and metric limitations. Fewer than 3 points is `insufficient`. Four or more points with low variability and one analysis version may be `medium`; other supported trends are `low`. v0.3 never outputs `high`. This is neither statistical significance nor reliability/validity.

## Issue trajectories

Only structured improvement diagnoses from comparable submissions are used, never LLM prose. `persistent` requires at least 3 occurrences and a current occurrence. `recurring` represents intermittent repeated occurrence. `recently_reduced` requires at least 4 comparable records, at least 2 earlier occurrences and no occurrence in the last 2 records. One absence is insufficient. Diagnosis-version differences reduce confidence.

## Priority candidates

At most 3 candidates combine the current structured diagnosis with persistent or unstable local trajectories. They are candidates for teacher review, not automatic teaching prescriptions.

All parameters are versioned in `app/config/longitudinal.py` as `longitudinal-config-v0.3.0`. Every rule is a prototype heuristic requiring literature review and empirical calibration.
