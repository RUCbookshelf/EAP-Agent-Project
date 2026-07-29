# Versioned configuration management v0.6.1

Migration 7 preserves the existing `config-v0.6.1` and activates its child `config-v0.6.2`, because the requested name was already occupied. The child adds diagnostic calibration parameters: maximum priorities 2, score threshold 0.52, repetition count/density 4/0.025, local-cluster requirement, prompt/necessary-term penalties 1.0/0.7, specific connective-location requirement, exercise maxima 3/2/1, and no monitored-signal exercises.

These are prototype defaults. They have not been calibrated against literature, teacher judgements, educational outcomes, fairness evidence, or measurement-validity studies. Rollback reactivates `config-v0.6.1` without deleting the child or recomputing historical runs.

Sensitive values remain exclusively in `.env` or the operating-system environment. The configuration schema is a
Pydantic allowlist of non-sensitive research parameters; extra fields are rejected and are not echoed into storage.

Creating an edit produces a new `draft` with a required change note, parent version and deterministic SHA-256 content
hash. Validation checks Analyzer/fallback registration and availability, Prompt existence, required Metrics and
Algorithm compatibility. Only `passed` versions can activate. SQLite enforces one active version. Activation marks the
previous version inactive and immediately applies the selected Analyzer parameters and LLM temperature/token limit to
subsequent runs.

Rollback starts from the active version and reactivates its parent. Neither version nor any prior AnalysisRun is
deleted or automatically recomputed. Create, validate, activate and rollback actions record actor, reason, time and
safe details. This local admin interface has no production authentication and must not be publicly deployed.
