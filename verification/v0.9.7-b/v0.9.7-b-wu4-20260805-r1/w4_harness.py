"""v0.9.7-B WU4 browser harness (extends the stable v0.9.4-A harness).

Points the isolated database and logs at this run directory, seeds the four
synthetic WU4 learners, and reports the practice-table counts used by the
focused task-and-attempt matrix.
"""
from __future__ import annotations

import pathlib
import sqlite3
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
BASE_HARNESS_DIR = PROJECT_ROOT / "verification/v0.9.4-a/v0.9.4-a-20260801-r1"
sys.path.insert(0, str(BASE_HARNESS_DIR))

sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.locale import t  # noqa: E402

import v094a_harness as _base  # noqa: E402
from v094a_harness import *  # noqa: E402,F403

_base.RUN_DIR = HERE
_base.ISOLATED_DB = HERE / "isolated" / "writing_feedback_v097b_wu4.db"
_base.LOG_DIR = HERE / "logs"

RUN_DIR = _base.RUN_DIR
ISOLATED_DB = _base.ISOLATED_DB
LOG_DIR = _base.LOG_DIR

STUDENTS = ("V097B-W1", "V097B-W2", "V097B-W3", "V097B-W4")


def prepare_isolated_db() -> pathlib.Path:
    path = _base.prepare_isolated_db()
    with sqlite3.connect(path) as con:
        for student_id in STUDENTS:
            con.execute(
                "INSERT OR IGNORE INTO students (student_id, created_at, is_synthetic) "
                "VALUES (?, '2026-08-05T00:00:00+00:00', 1)",
                (student_id,),
            )
        con.commit()
    return path


def close_sidebar(page) -> None:
    """Close Streamlit 1.60's unlabeled mobile sidebar control reliably."""
    if page.viewport_size and page.viewport_size["width"] >= 700:
        return
    _base.close_sidebar(page)
    sidebar = page.locator('[data-testid="stSidebar"]')
    if sidebar.count() == 0 or sidebar.first.get_attribute("aria-expanded") != "true":
        return
    control = sidebar.locator('[data-testid="stBaseButton-headerNoPadding"]').first
    if control.count() and "keyboard_double_arrow_left" in control.inner_text():
        control.click(timeout=4_000)
        page.wait_for_timeout(500)
    if sidebar.first.get_attribute("aria-expanded") == "true":
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
    if sidebar.first.get_attribute("aria-expanded") == "true":
        raise RuntimeError("Mobile sidebar remained open after the WU4 close helper")


def open_sidebar(page) -> None:
    """Open the mobile sidebar, including the Streamlit 1.60 header expand."""
    if page.viewport_size and page.viewport_size["width"] >= 700:
        return
    sidebar = page.locator('[data-testid="stSidebar"]')
    if sidebar.count() and sidebar.first.get_attribute("aria-expanded") == "true":
        return
    _base.open_sidebar(page)
    if sidebar.count() and sidebar.first.get_attribute("aria-expanded") == "true":
        return
    expand = page.locator(
        '[data-testid="stHeader"] button:has-text("keyboard_double_arrow_right")'
    )
    if expand.count():
        expand.first.click(timeout=4_000)
        page.wait_for_timeout(900)
    if sidebar.count() and sidebar.first.get_attribute("aria-expanded") != "true":
        raise RuntimeError("Mobile sidebar failed to open via the WU4 helper")


def click_label(page, label: str, timeout: int = 12_000) -> None:
    open_sidebar(page)
    loc = page.locator(f"label:has-text('{label}')").last
    loc.wait_for(state="visible", timeout=timeout)
    loc.click(timeout=timeout)


def select_page(page, label: str, expected_h2: str, *, attempts: int = 3) -> bool:
    for _ in range(attempts):
        click_label(page, label)
        wait_stable(page, timeout=15)
        close_sidebar(page)
        if any(expected_h2 in h for h in current_h2(page)):
            return True
    return False


def open_page(page, title_key: str, lang: str) -> None:
    assert select_page(page, t(title_key, lang), t(title_key, lang))
    close_sidebar(page)


def learner_counts(student_id: str) -> dict[str, int]:
    with sqlite3.connect(ISOLATED_DB) as con:
        return {
            "essays": int(con.execute(
                "SELECT COUNT(*) FROM essays WHERE student_id=?", (student_id,)
            ).fetchone()[0]),
            "practice_targets": int(con.execute(
                "SELECT COUNT(*) FROM practice_targets WHERE student_id=?",
                (student_id,),
            ).fetchone()[0]),
            "exercise_instances": int(con.execute(
                "SELECT COUNT(*) FROM exercise_instances WHERE student_id=?",
                (student_id,),
            ).fetchone()[0]),
            "exercise_attempts": int(con.execute(
                "SELECT COUNT(*) FROM exercise_attempts WHERE student_id=?",
                (student_id,),
            ).fetchone()[0]),
            "practice_evaluations": int(con.execute(
                """SELECT COUNT(*) FROM practice_evaluations pe
                JOIN exercise_attempts ea ON ea.attempt_id = pe.attempt_id
                WHERE ea.student_id=?""",
                (student_id,),
            ).fetchone()[0]),
        }
