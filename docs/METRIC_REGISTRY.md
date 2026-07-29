# Metric Registry v0.4

`MetricDefinition` describes identity, version, unit, value type, parameters and limitations. `MetricResult` binds a value/status to Analyzer/resource versions, evidence and a human-verification status. `MetricRegistry` permits multiple versions of one metric and rejects duplicate registrations.

Compatibility metrics remain word/sentence/paragraph counts, average sentence length, unique surface words, TTR, connective count and repeated content words. v0.4 adds prototype lexical density, MATTR, finite-verb/subordinate/coordination candidate counts, mean dependency-tree depth and mean noun-phrase length.

Algorithm changes require a new `metric_version`. Reanalysis appends MetricResults under a new AnalysisRun. `automatic_unverified` is the default; later registries support `automatically_cross_checked`, `human_reviewed`, `human_confirmed`, `rejected` and `not_applicable`. No registry entry represents a CALF total, proficiency score or CEFR level.
