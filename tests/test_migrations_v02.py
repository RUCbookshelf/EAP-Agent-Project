from __future__ import annotations

import sqlite3

from app.database import Database, LATEST_MIGRATION_VERSION


def test_empty_database_upgrades_and_is_idempotent(tmp_path):
    repository = Database(tmp_path / "empty.db")
    repository.initialize()
    assert repository.migration_version() == LATEST_MIGRATION_VERSION
    before = repository.counts()
    repository.initialize()
    assert repository.migration_version() == LATEST_MIGRATION_VERSION
    assert repository.counts() == before


def test_legacy_database_upgrades_without_losing_history(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as connection:
        connection.executescript("""
        CREATE TABLE students(student_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, is_synthetic INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE essays(essay_id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT NOT NULL REFERENCES students(student_id), writing_prompt TEXT NOT NULL, genre TEXT NOT NULL, draft_stage TEXT NOT NULL, timed INTEGER NOT NULL, tool_use TEXT NOT NULL, essay_text TEXT NOT NULL, submitted_at TEXT NOT NULL);
        INSERT INTO students VALUES('LEGACY','2026-01-01T00:00:00+00:00',0);
        INSERT INTO essays(student_id,writing_prompt,genre,draft_stage,timed,tool_use,essay_text,submitted_at) VALUES('LEGACY','Prompt','argumentative essay','first draft',0,'none','Legacy essay.','2026-01-01T00:00:00+00:00');
        """)
    repository = Database(path)
    repository.initialize()
    assert repository.migration_version() == LATEST_MIGRATION_VERSION
    assert repository.get_student("LEGACY")["submission_count"] == 1
    assert repository.get_submission_bundle(1)["essay_text"] == "Legacy essay."
