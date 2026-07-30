# Metric Registry v0.8

The CALF registry supplements the compatibility registry with 4 constructs, 22 measurement specifications, and 14 analysis units. New current lexical definitions are MTLD 0.8.0 and HD-D 0.8.0; output rate 0.8.0 is a descriptive proxy. Semantic measurement status and automation level are independent of observed availability/confidence. Activation is rejected without formula, unit, minimum data, fixtures, references, and limitations.

The registry retains old definitions while `latest_list()` selects current versions for new AnalysisRuns. Lexical versions are word count 2.0.0, unique word count 2.0.0, TTR 2.0.0, MATTR 0.6.1, lexical density 0.6.1, repetition density 0.6.1, repeated-content evidence 3.0.0, and connective count 2.1.0. Old/new versions are separate longitudinal series and are never bridged silently.

Current syntax candidates are finite verbs 0.6.1, clause-like dependencies 0.6.1, coordinator tokens 0.6.1, conjunct dependencies 0.6.1, and coordinated-structure candidates 0.6.1. Older aggregate names remain readable only for historical audit.

`MetricResult.measurement_metadata` stores sufficient numerator, denominator, token, type, window, POS, parameter, and resource details for the applicable metric to be independently checked. `confidence` describes measurement trust, while Diagnosis Confidence describes the later teaching inference; the two must not be merged.

`MetricDefinition` describes identity, version, unit, value type, parameters and limitations. `MetricResult` binds a value/status to Analyzer/resource versions, evidence and a human-verification status. `MetricRegistry` permits multiple versions of one metric and rejects duplicate registrations.

Compatibility metrics remain word/sentence/paragraph counts, average sentence length, unique surface words, TTR, connective count and repeated content words. v0.4 adds prototype lexical density, MATTR, finite-verb/subordinate/coordination candidate counts, mean dependency-tree depth and mean noun-phrase length.

Algorithm changes require a new `metric_version`. Reanalysis appends MetricResults under a new AnalysisRun. `automatic_unverified` is the default; later registries support `automatically_cross_checked`, `human_reviewed`, `human_confirmed`, `rejected` and `not_applicable`. No registry entry represents a CALF total, proficiency score or CEFR level.
