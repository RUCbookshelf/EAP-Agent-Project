from __future__ import annotations

import sqlite3

import pytest

from app.database import Database
from app.models import EssaySubmission


def sample(student_id="R001"):
    return EssaySubmission(
        student_id=student_id, writing_prompt="A prompt", genre="argumentative essay",
        draft_stage="first draft", timed=False, tool_use="none",
        essay_text="A complete sentence provides enough text.",
    )


def test_repository_save_read_restart_and_isolation(tmp_path):
    first = Database(tmp_path / "first.db")
    second = Database(tmp_path / "second.db")
    first.initialize(); second.initialize()
    essay_id = first.save_essay(sample())
    assert Database(tmp_path / "first.db").get_submission_bundle(essay_id)["student_id"] == "R001"
    assert second.get_student("R001") is None


def test_transaction_failure_rolls_back(tmp_path):
    repository = Database(tmp_path / "rollback.db")
    repository.initialize()
    with pytest.raises(RuntimeError):
        with repository.transaction() as connection:
            connection.execute(
                "INSERT INTO students(student_id, created_at, is_synthetic) VALUES ('ROLLBACK', CURRENT_TIMESTAMP, 0)"
            )
            raise RuntimeError("force rollback")
    assert repository.get_student("ROLLBACK") is None


def test_connections_close_after_context(tmp_path):
    repository = Database(tmp_path / "closed.db")
    repository.initialize()
    connection = repository.connect()
    with connection:
        connection.execute("SELECT 1")
    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")
