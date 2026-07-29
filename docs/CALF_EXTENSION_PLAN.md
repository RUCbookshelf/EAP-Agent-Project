# CALF extension plan after v0.6

v0.6 does not implement a complete CALF system. Future work can add replaceable `MetricCalculator` implementations
and register `MetricDefinition`, `AlgorithmVersion`, `ResourceVersion` and versioned `MetricResult` outputs under an
AnalysisRun. Candidate families include syntactic complexity, lexical diversity, lexical sophistication, lexical
density, human-confirmed accuracy candidates, product fluency and separately sourced process fluency.

Each future result must preserve unit, parameters, Analyzer/Algorithm/resource versions, evidence, limitations and one
of: `automatic_unverified`, `automatically_cross_checked`, `human_reviewed`, `human_confirmed`, `rejected`, or
`not_applicable`. Adding a family should require an implementation, registry entry and tests—not changes to the core
FastAPI or Streamlit submission workflow.

No single CALF total, proficiency score or CEFR field is planned. Accuracy and process measures require new authorized
evidence and human research decisions before v0.7 begins.
