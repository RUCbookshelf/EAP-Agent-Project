# History Evidence Registry v0.7

`history_evidence_registry` is the append-only provenance layer between learner-model calculations and longitudinal feedback. Every `HE######` record stores evidence type, source submission IDs, AnalysisRun IDs, diagnosis IDs, metric IDs, source snapshot, Task Cluster, concise evidence text, optional character offsets, evidence status, version compatibility, confidence, limitations and registry version.

Only evidence relevant to current Gate-selected targets is screened into `feedback-prompt-v0.7.0`, with a default maximum of five records. The prompt cannot use an unknown ID. Suppressed diagnostics, unrelated metrics and whole unscreened histories do not enter the model context.

Traceability establishes provenance, not correctness, educational validity, learning, or causality. Rebuilding a profile appends a snapshot and new registry rows; it never mutates earlier evidence.
