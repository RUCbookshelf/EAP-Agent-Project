# Database migrations

v0.2 uses a minimal native SQLite migration runner because the existing repository is small and sqlite3-based. This is a deliberate local prototype choice, not an Alembic or PostgreSQL implementation.

- Current version: 2.
- Authority: `PRAGMA user_version` plus `schema_migrations` audit rows.
- Migration 1 preserves/normalizes the v0.1.1 schema and adds missing legacy columns.
- Migration 2 adds the migration ledger and the student/submission lookup index.

The runner applies versions in order inside transactions, never drops the database, and is repeatable. Tests prove empty initialization, legacy-row preservation, idempotence and separate test databases. `run.bat` executes `python -m scripts.migrate_database` before either service starts.

Back up research data before future migrations. PostgreSQL requires a separate adapter and migration strategy and is not currently implemented.
