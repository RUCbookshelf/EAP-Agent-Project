# Project development rules

These rules apply to every future change in this repository.

## Required reading before development

Read, in order: `AGENTS.md`, `docs/development/MASTER_ROADMAP.md`, `docs/development/DECISION_LOG.md`, the current version SPEC, and the previous version's `RUN_VERIFICATION` report.

## Architecture boundaries

- Core business code must not depend on Streamlit, browser session state, UI components, local ports, or a particular frontend.
- Streamlit is only an HTTP API client and local researcher interface.
- API routes validate and translate requests; application services own workflows.
- Core services depend on Repository protocols, never directly on `sqlite3.connect`.
- SQLite SQL, connections, migrations, and transaction handling stay in infrastructure/repository modules.
- Existing Prompt construction, Pydantic response validation, diagnosis/history evidence IDs, quote validation, retry, and fallback safeguards must remain in the submission path.

## Runtime synchronization

Update `run.bat` whenever Python requirements, dependency files, FastAPI or Streamlit entry points, environment variables, migration commands, project paths, Prompt/config locations, or ports change.

## Version gates

Every version must run all tests, verify FastAPI, Streamlit, `run.bat`, and migrations, update documentation, produce an independent acceptance report, and create an independent Git commit.

All longitudinal outputs are prototype observations, not proficiency, CEFR, validated growth, rankings, or high-risk instructional decisions. API keys may only come from `.env` or process environment and may never enter code, tests, logs, databases, documentation, or Git.

After v0.3 is complete, stop. Do not implement v0.4, dashboards, exercise-transfer loops, configuration administration, WeChat clients, or cloud deployment without human review.
