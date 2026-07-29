# Decision log

## D001 — Preserve v0.1.1 as an incremental compatibility layer

- Date: 2026-07-29
- Status: accepted
- Decision: retain Analyzer, Diagnoser, Prompt Builder, Provider Router, and feedback validator; wrap them with new services and Repository protocols rather than rewrite them.
- Reason: protects proven evidence validation and fallback behavior.

## D002 — Use numbered native SQLite migrations for v0.2

- Date: 2026-07-29
- Status: accepted
- Decision: use small, versioned Python migration functions with `PRAGMA user_version` and a migration history table, not SQLAlchemy/Alembic.
- Reason: the existing system is small and sqlite3-based; a native runner is the minimum reliable non-destructive mechanism and keeps dependencies limited. PostgreSQL remains an explicit future adapter seam, not a fake implementation.

## D003 — Keep API routes thin and application services framework-neutral

- Date: 2026-07-29
- Status: accepted
- Decision: FastAPI dependency wiring may construct services, but routes only validate, invoke, and translate results. Services contain no FastAPI or Streamlit imports.

## D004 — Fixed local ports fail clearly

- Date: 2026-07-29
- Status: accepted
- Decision: local FastAPI and Streamlit ports are configured once; startup fails with a clear error when unavailable and never silently selects another port.
