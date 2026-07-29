# Metric Trajectories v0.7

Metrics are grouped by Task Cluster, metric ID, metric version and analyzer version. Each point retains submission ID, AnalysisRun ID, timestamp, value and Metric Confidence. Non-available or ineligible points remain auditable and are not silently connected.

One point is insufficient. Two points report `pairwise_difference` and `relative_change` but direction remains `insufficient_data`. Three or four compatible points may report a provisional increasing, decreasing, stable or variable signal. Five or more may report an adequate descriptive trend. Slope and coefficient-of-variation rules are transparent prototype calculations.

No direction is interpreted as writing quality, ability growth, learning, regression, statistical significance, reliability, or validity. Cross-version normalization is not implemented.
