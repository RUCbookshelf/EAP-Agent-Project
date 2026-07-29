# Visualization v0.6

The Student progress page requests `/api/v1/students/{student_id}/dashboard`; Streamlit does not recalculate metrics,
comparability or trajectories. The response contains a complete submission timeline, included/excluded state and
reason, Revision Group representative flag, AnalysisRun, Analyzer and configuration versions.

Metric points include submission/date/value, inclusion, exclusion reason, Metric/Analyzer/configuration versions and
limitations. The API groups included points by that version triple. Streamlit renders each group as an independent
line chart, so incompatible implementations are never silently connected. Missing or non-numeric values remain
visible in the point list but are not fabricated into a line.

Issue trajectories, confidence and supporting submissions come from structured local services. Labels describe
prototype signal patterns—not proficiency, ability growth, CEFR, CALF totals or class rank.
