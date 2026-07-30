# Diagnostic Calibration v0.6.1

## v0.7.1 reliability use

Calibration and gates are unchanged. Zero selected priorities and zero targeted practices are valid and now produce explicit UI empty-state codes. Positive findings remain independently validated: explanations may describe the quoted observable feature but prohibited ability/proficiency inferences are locally replaced without reactivating a diagnosis or discarding other valid feedback.

## v0.7 longitudinal use

Calibration v0.6.1 remains authoritative for the current essay. Learner Model v0.7 may summarize prior selected diagnoses within a compatible Task Cluster, but it cannot re-enable a current monitored or suppressed signal. Current learning targets require current `selected_priority` plus `evidence_relevance_status=verified`; zero targets is valid. The calibration version is recorded on every trajectory.

v0.6.1 inserts a deterministic calibration layer between NLP analysis and formative feedback. It does not score proficiency and does not implement CALF.

## Processing contract

`MetricResult -> Metric Confidence -> raw signal -> Diagnostic Gate -> Evidence Relevance -> Priority Score -> selected priority -> feedback`

A metric may be saved without becoming a diagnosis. A diagnosis candidate may be monitored or suppressed without reaching the student. All raw and excluded signals remain available in the append-only research audit.

## Metric confidence

Metric confidence is separate from diagnosis confidence and may be `high`, `medium`, `low`, `insufficient`, or `not_applicable`. The local evaluator considers data completeness, token length, Analyzer fallback, NLP model status, Analyzer/model/resource versions, metric parameters, parser or dictionary dependence, minimum-data rules, and cross-version comparability. Metric magnitude alone never determines confidence.

## Gate states

- `raw_signal`: candidate emitted by the heuristic Diagnoser.
- `monitored_signal`: retained for research observation but excluded from student feedback.
- `eligible_diagnosis`: passed the gate and awaits ranking.
- `selected_priority`: evidence-verified candidate selected for feedback.
- `suppressed`: excluded by the gate or priority selection.
- `insufficient_evidence`: no relevant, specific evidence supports feedback.

The gate and ranking versions are `diagnostic-gate-v0.6.1` and `diagnostic-priority-v0.6.1`.

## Conservative defaults

| Parameter | Default |
|---|---:|
| Maximum selected priorities | 2 |
| Priority threshold | 0.52 |
| Repetition minimum count | 4 |
| Repetition minimum density | 0.025 |
| Require local cluster at low count | true |
| Prompt-keyword penalty | 1.0 |
| Necessary-term penalty | 0.7 |
| Connective specific-location requirement | true |
| Exercises for high / medium / low confidence | 3 / 2 / 1 |
| Exercises for monitored signals | 0 |

These are prototype defaults, not educational or measurement-validated thresholds.

## Repetition and connectives

Distributed repetition with only three occurrences and no local cluster remains monitored. Prompt keywords and conservative `necessary_task_term` candidates are down-weighted. A lexical priority needs a local cluster or sufficient non-topic frequency and density, plus relevant evidence.

The connective resource distinguishes discourse connectives, ordinary coordination, subordination, and paragraph-organization expressions. Detection only demonstrates dictionary matches. A connective priority requires a specific verified sentence relation or paragraph boundary; absence from the dictionary is not treated as lack of cohesion.

## Strengths and descriptive signals

Word count, analysis sufficiency, long sentences, MATTR, connective counts, and parser candidates are descriptive signals, not strengths. A positive finding requires an exact, relevant text span and describes only an observable feature. If the local rules cannot identify one, LocalDemo uses a neutral observation.

## Priority score

The transparent score records evidence strength, metric confidence, diagnosis confidence, local concentration, magnitude, actionability, pedagogical value, history relevance, verified location, redundancy, prompt-term, necessary-term, and low-confidence components. It is a selection aid, never a writing or ability score.

## Audit access

Researchers can use the Streamlit **Diagnostic audit** page or `GET /api/v1/submissions/{submission_id}/diagnostic-audit`. Students see only verified positive findings, at most two selected priorities, matching exercises, and concise limitations.
