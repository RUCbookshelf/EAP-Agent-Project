"""v0.9.7-B WU6 browser harness (extends the WU5 harness).

Points the isolated database and logs at this WU6 run directory, seeds the
WU6 synthetic learners (four main matrix learners plus evaluation-
unavailable, no-priority, and legacy learners), and reports the
learner-scoped practice counts, full Journey payloads, and whole-database
row counts used by the final product matrix and the Journey write checks.
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import sys

import requests

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
BASE_HARNESS_DIR = PROJECT_ROOT / "verification/v0.9.4-a/v0.9.4-a-20260801-r1"
WU5_DIR = PROJECT_ROOT / "verification/v0.9.7-b/v0.9.7-b-wu5-20260805-r1"
sys.path.insert(0, str(BASE_HARNESS_DIR))
sys.path.insert(0, str(WU5_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.locale import t  # noqa: E402

import w5_harness as _w5  # noqa: E402
from w5_harness import *  # noqa: E402,F403

# The star import above shadows THIS module's path constants with the WU5
# values, so the run-directory state is re-derived and re-pointed AFTER it:
# the shared v0.9.4-A harness state must target this WU6 run directory.
HERE = pathlib.Path(__file__).resolve().parent
_w5._base.RUN_DIR = HERE
_w5._base.ISOLATED_DB = HERE / "isolated" / "writing_feedback_v097b_wu6.db"
_w5._base.LOG_DIR = HERE / "logs"
_w5.RUN_DIR = HERE
_w5.ISOLATED_DB = _w5._base.ISOLATED_DB
_w5.LOG_DIR = HERE / "logs"

RUN_DIR = _w5.RUN_DIR
ISOLATED_DB = _w5.ISOLATED_DB
LOG_DIR = _w5.LOG_DIR
BASE = _w5._base.BASE

MAIN_STUDENTS = ("V097B-W6-ED", "V097B-W6-ZD", "V097B-W6-EM", "V097B-W6-ZM")
FOCUS_STUDENTS = ("V097B-W6-EU", "V097B-W6-ZU", "V097B-W6-NP", "V097B-W6-NZ",
                  "V097B-W6-LE", "V097B-W6-LZ")
ALL_STUDENTS = MAIN_STUDENTS + FOCUS_STUDENTS


def prepare_isolated_db() -> pathlib.Path:
    path = _w5._base.prepare_isolated_db()
    with sqlite3.connect(path) as con:
        for student_id in ALL_STUDENTS:
            con.execute(
                "INSERT OR IGNORE INTO students (student_id, created_at, is_synthetic) "
                "VALUES (?, '2026-08-05T00:00:00+00:00', 1)",
                (student_id,),
            )
        con.commit()
    return path


def journey_payload(student_id: str) -> dict:
    response = requests.get(
        f"{_w5._base.BASE}/api/v1/students/{student_id}/journey", timeout=30)
    assert response.status_code == 200, response.text
    return response.json()


def journey_event_keys(student_id: str) -> list[tuple[str, str]]:
    return [(e["event_type"], e["source_record_id"])
            for e in journey_payload(student_id)["events"]]


def whole_db_counts() -> dict[str, int]:
    with sqlite3.connect(ISOLATED_DB) as con:
        tables = [
            row[0] for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        ]
        return {table: int(con.execute(
            f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]) for table in tables}


def delete_evaluations_for_student(student_id: str) -> None:
    with sqlite3.connect(ISOLATED_DB) as con:
        con.execute(
            "DELETE FROM practice_evaluations WHERE attempt_id IN "
            "(SELECT attempt_id FROM exercise_attempts WHERE student_id=?)",
            (student_id,),
        )
        con.commit()


def delete_attempts_for_student(student_id: str) -> None:
    with sqlite3.connect(ISOLATED_DB) as con:
        con.execute(
            "DELETE FROM exercise_attempts WHERE student_id=?", (student_id,))
        con.commit()
