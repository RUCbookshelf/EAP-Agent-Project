"""Worker B probe: fresh / existing / idempotent migration paths + persistence.

Read-only against product code; writes ONLY to the temp DB file and the
probe log inside this evidence directory.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

WORKTREE = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(WORKTREE))

from app.database import Database
from app.database import migrations as mig_mod
from app.database import upgrade
from app.infrastructure.sqlite.repositories.review import SQLiteReviewRepository
from app.infrastructure.sqlite.repositories.wave2 import (
    LearningItem,
    SQLiteWave2Repository,
)
from app.review.models import (
    Rating,
    ReviewEvent,
    PracticeActivity,
    PracticeActivityStatus,
    SchedulerStateSnapshot,
    SchedulingResult,
)
from app.review.scheduler import FSRSSchedulerAdapter
from app.version import PLATFORM_DATABASE_MIGRATION_VERSION

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "probe_out")
OUT.mkdir(parents=True, exist_ok=True)
TMP = OUT / "tmp"
TMP.mkdir(parents=True, exist_ok=True)
for leftover in TMP.glob("*.db"):
    leftover.unlink()


def log(msg: str) -> None:
    print(msg)
    with open(OUT / "probe_results.txt", "a", encoding="utf-8") as fh:
        fh.write(msg + "\n")


def table_names(con: sqlite3.Connection) -> set[str]:
    rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {r[0] for r in rows}


def main() -> None:
    log(f"== Probe start: LATEST={mig_mod.LATEST_MIGRATION_VERSION} "
        f"version.py={PLATFORM_DATABASE_MIGRATION_VERSION}")
    results = {"fresh": None, "existing": None, "idempotent": None,
               "close_reopen": None, "single_file": None}

    # --- 1. Fresh path -----------------------------------------------------
    fresh_path = TMP / "fresh.db"
    con = sqlite3.connect(fresh_path)
    con.row_factory = sqlite3.Row
    v = upgrade(con)
    tables = table_names(con)
    new_tables = {"practice_activities", "review_events",
                  "learning_item_scheduler_states"}
    ok_fresh = (
        v == 15
        and new_tables <= tables
        and {"learning_items", "writing_tasks"} <= tables
        and con.execute("PRAGMA user_version").fetchone()[0] == 15
    )
    versions = {r["version"] for r in
                con.execute("SELECT version FROM schema_migrations")}
    ok_fresh = ok_fresh and versions == set(range(1, 16))
    con.close()
    log(f"1. FRESH path: user_version={v}, versions={sorted(versions)} -> {ok_fresh}")
    results["fresh"] = ok_fresh

    # --- 2. Existing path: authentic migration-14 DB with Wave-2 data ------
    existing_path = TMP / "existing.db"
    con = sqlite3.connect(existing_path)
    con.row_factory = sqlite3.Row
    # Authentic 14-only DB: run the real upgrade with latest capped at 14.
    original_latest = mig_mod.LATEST_MIGRATION_VERSION
    mig_mod.LATEST_MIGRATION_VERSION = 14
    v14 = upgrade(con)
    assert v14 == 14, v14
    assert "practice_activities" not in table_names(con)
    mig_mod.LATEST_MIGRATION_VERSION = original_latest
    # Insert Wave-2 data through the real Wave-2 repository.
    db14 = Database(existing_path)
    w2 = SQLiteWave2Repository(db14._connection_manager)
    w2.save_learning_item(
        LearningItem(learning_item_id="LI000001", student_id="S1",
                     category="grammar")
    )
    w2.save_learning_item(
        LearningItem(learning_item_id="LI000002", student_id="S1",
                     category="vocabulary")
    )
    con = sqlite3.connect(existing_path)
    con.row_factory = sqlite3.Row
    rows_before = con.execute(
        "SELECT learning_item_id, student_id, category FROM learning_items"
        " ORDER BY learning_item_id").fetchall()
    con.close()
    # Now upgrade to 15 through the normal path (fresh Database connection).
    con = sqlite3.connect(existing_path)
    con.row_factory = sqlite3.Row
    v15 = upgrade(con)
    rows_after = con.execute(
        "SELECT learning_item_id, student_id, category FROM learning_items"
        " ORDER BY learning_item_id").fetchall()
    con.close()
    ok_existing = (
        v15 == 15
        and [tuple(r) for r in rows_after] == [tuple(r) for r in rows_before]
        and {r["learning_item_id"] for r in rows_after} == {
            "LI000001", "LI000002"}
        and table_names(sqlite3.connect(existing_path))
        >= {"practice_activities", "review_events",
            "learning_item_scheduler_states"}
    )
    log(f"2. EXISTING path (14 with data -> 15): v={v15}, "
        f"rows_before={[tuple(r) for r in rows_before]}, "
        f"rows_after={[tuple(r) for r in rows_after]} -> {ok_existing}")
    results["existing"] = ok_existing

    # --- 3. Idempotent re-run ----------------------------------------------
    con = sqlite3.connect(existing_path)
    con.row_factory = sqlite3.Row
    tables_first = table_names(con)
    versions_first = {r["version"] for r in
                      con.execute("SELECT version FROM schema_migrations")}
    v_again = upgrade(con)
    tables_again = table_names(con)
    versions_again = {r["version"] for r in
                      con.execute("SELECT version FROM schema_migrations")}
    con.close()
    ok_idem = v_again == 15 and tables_first == tables_again and \
        versions_first == versions_again
    log(f"3. IDEMPOTENT re-run: v={v_again}, tables_equal="
        f"{tables_first == tables_again}, versions_equal="
        f"{versions_first == versions_again} -> {ok_idem}")
    results["idempotent"] = ok_idem

    # --- 4. Close/reopen persistence with stable LearningItem identity -----
    path = TMP / "reopen.db"
    first = Database(path)
    first.initialize()
    assert first._system_repository.migration_version() == 15
    w2 = SQLiteWave2Repository(first._connection_manager)
    w2.save_learning_item(
        LearningItem(learning_item_id="LI000007", student_id="S1",
                     category="grammar"))
    repo = first._review_repository
    t0 = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
    activity = repo.save_practice_activity(PracticeActivity(
        activity_id="PA-PENDING", student_id="S1",
        learning_item_id="LI000007", activity_type="blank_fill",
        status=PracticeActivityStatus.COMPLETED, occurred_at=t0))
    identity = FSRSSchedulerAdapter().identity()
    state_row = {
        "learning_item_id": "LI000007",
        "student_id": "S1",
        "identity": identity.model_dump(mode="json"),
        "state": SchedulerStateSnapshot(
            card_id=7, state="review", stability=2.3065, due=t0
        ).model_dump(mode="json"),
        "rating_rule_version": "rating-rule-v1.0.0",
        "updated_at": "2026-01-01T08:00:00+00:00",
        "last_review_event_id": "RE-PENDING",
    }
    event = repo.record_review_event(ReviewEvent(
        review_event_id="RE-PENDING", student_id="S1",
        learning_item_id="LI000007", practice_activity_id=activity.activity_id,
        reviewed_at=t0, system_provisional_rating=Rating.GOOD,
        learner_self_rating=Rating.HARD, final_scheduler_rating=Rating.HARD,
        rating_rule_version="rating-rule-v1.0.0",
        scheduler_implementation="py-fsrs", scheduler_version="6.3.2",
        state_before=SchedulerStateSnapshot(card_id=7, due=t0),
        state_after=SchedulerStateSnapshot(
            card_id=7, state="learning", step=1, due=t0),
        scheduling_result=SchedulingResult(next_due=t0),
    ), state_row)
    li_before = first._wave2_repository.get_learning_item("LI000007")
    event_id = event.review_event_id
    activity_id = activity.activity_id
    # Drop every reference -> close; reopen the same file.
    del repo, first, w2
    second = Database(path)
    second.initialize()
    repo2 = second._review_repository
    events = repo2.list_review_events("LI000007")
    state = repo2.get_scheduler_state("LI000007")
    act = repo2.get_practice_activity(activity_id)
    li_after = second._wave2_repository.get_learning_item("LI000007")
    ok_reopen = (
        len(events) == 1
        and events[0].review_event_id == event_id
        and state is not None
        and state.state.state == "review"
        and state.last_review_event_id == event_id
        and act is not None
        and act.activity_id == activity_id
        and li_after is not None
        and li_after.learning_item_id == "LI000007"
        and li_after.model_dump() == li_before.model_dump()
    )
    log(f"4. CLOSE/REOPEN: event_id={event_id}, activity_id={activity_id}, "
        f"events={len(events)}, state_state="
        f"{(state.state.state if state else None)}, li_identity_stable="
        f"{li_before.learning_item_id == li_after.learning_item_id} "
        f"-> {ok_reopen}")
    results["close_reopen"] = ok_reopen

    # --- 5. Single database file, no second persistence authority ----------
    before = {p.name for p in TMP.glob("*.db")}
    third = Database(path)
    third.initialize()
    _ = third._review_repository.list_review_events("LI000007")
    after = {p.name for p in TMP.glob("*.db")}
    db_files = sorted(before | after)
    # Exactly three named DB files were created by this probe; opening and
    # re-initializing an existing Database must not create another file.
    ok_single = (
        before == after
        and len(after) == 3
        and after == {"fresh.db", "existing.db", "reopen.db"}
    )
    # No ATTACH databases; SQLite engine = sqlite3 only.
    con = sqlite3.connect(path)
    attached = con.execute("PRAGMA database_list").fetchall()
    con.close()
    ok_single = ok_single and len(attached) == 1
    log(f"5. SINGLE FILE: db_files={db_files}, before==after={before == after}, "
        f"attached_dbs={len(attached)} -> {ok_single}")
    results["single_file"] = ok_single

    log(f"== RESULT: {results}")
    if not all(results.values()):
        log("== PROBE FAILED ==")
        sys.exit(1)
    log("== PROBE OK ==")


if __name__ == "__main__":
    main()
