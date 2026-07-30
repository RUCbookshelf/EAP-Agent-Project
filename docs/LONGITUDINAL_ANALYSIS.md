# v0.7 task-aware longitudinal analysis

## v0.8 CALF research series

CALF series do not alter v0.7 learner snapshots. Eligible observations are grouped by metric version, analysis-unit version, Analyzer compatibility, genre, timed/untimed condition, time limit, and tool use. Incompatible, candidate, unavailable, or insufficient observations are listed with exclusion reasons; no bridging, improvement, ability, or causal claim is made.

## v0.7.1 deterministic status and wording

The backend owns the status, scope, comparable independent-task count, minimum, revision-group count, draft count, evidence IDs and limitations. No-history and non-comparable states clear evidence IDs and use an explicit unavailable explanation. Two comparable tasks permit only a pairwise descriptive comparison; three/four permit a provisional pattern; five or more permit a descriptive trend. A model comment that does not match the structured status is replaced locally while valid current-feedback sections are retained.

v0.7 supersedes the default v0.3 calculation with Task Cluster scoped Snapshot v2 while retaining v0.3 fields for readers. Revision groups contribute one representative draft by default. Metric values are segmented by metric and analyzer version; two observations are only pairwise, three or four are provisional, and five or more may be labelled an adequate descriptive trend.

Diagnostic trajectories use selected priorities as primary evidence, eligible diagnoses as auxiliary evidence, and monitored/suppressed signals as research-only evidence. A current target always requires a current verified selected priority. “Recently reduced” cannot be used as a current target by itself. See `LEARNER_MODEL.md`, `METRIC_TRAJECTORIES.md`, and `DIAGNOSTIC_TRAJECTORIES.md`.

## Retained v0.3 contract

## v0.5 revision-group policy

Within-task drafts are not treated as independent long-term observations. Each Revision Group contributes its
`final_draft`, or otherwise the latest sequence member, to default learner-profile trends. Excluded drafts retain an
explicit reason in the Snapshot. Draft-to-draft changes remain available through revision analysis. This selection
does not establish learning, proficiency growth or causal impact.

v0.6 dashboard responses expose every included/excluded point, reason, Analyzer/Metric/configuration version,
direction, variability, confidence and limitations. Points with incompatible version triples are returned in separate
segments and the UI never silently connects them.

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
