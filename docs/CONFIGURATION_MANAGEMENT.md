# Versioned configuration management v0.6

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
