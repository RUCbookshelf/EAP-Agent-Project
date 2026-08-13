"""V1 independent probe 2: migration fresh/existing + persistence + provenance.

Uses ONLY product drivers (MIGRATIONS registry, upgrade(), Database facade,
ReviewService, SQLiteWave2Repository) on temp DBs under the V1 evidence dir.
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[6]))

from app.database import Database
from app.database.migrations import MIGRATIONS, upgrade
from app.infrastructure.sqlite.repositories.wave2 import (
    LearningItem,
    SQLiteWave2Repository,
)
from app.review.models import PracticeActivity, Rating
from app.review.scheduler import FSRSSchedulerAdapter
from app.review.service import ReviewService


T0 = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
RESULTS: list[dict] = []


def check(name: str, ok: bool, detail: str) -> None:
    RESULTS.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def tables(connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {r[0] for r in rows}


def upgrade_to(connection: sqlite3.Connection, target: int) -> None:
    for version in range(1, target + 1):
        name, migration = MIGRATIONS[version]
        with connection:
            migration(connection)
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER"
                " PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL"
                " DEFAULT CURRENT_TIMESTAMP)"
            )
            connection.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, name)"
                " VALUES (?, ?)",
                (version, name),
            )
            connection.execute(f"PRAGMA user_version = {version}")


def main() -> None:
    # --- 1. Fresh path: empty DB -> 15. ---
    fresh_path = OUT / "fresh15.db"
    fresh_path.unlink(missing_ok=True)
    connection = sqlite3.connect(fresh_path)
    connection.row_factory = sqlite3.Row
    try:
        version = upgrade(connection)
        table_set = tables(connection)
        ledger = {
            r["version"]
            for r in connection.execute("SELECT version FROM schema_migrations")
        }
        check(
            "fresh DB reaches user_version 15",
            version == 15
            and connection.execute("PRAGMA user_version").fetchone()[0] == 15,
            f"upgrade()={version}",
        )
        check(
            "fresh DB has 3 review tables + Wave-2 tables",
            {
                "practice_activities",
                "review_events",
                "learning_item_scheduler_states",
                "learning_items",
                "writing_tasks",
            }
            <= table_set,
            f"tables={sorted(table_set)}",
        )
        check(
            "ledger covers exactly 1..15",
            ledger == set(range(1, 16)),
            f"ledger={sorted(ledger)}",
        )
    finally:
        connection.close()

    # --- 2. Existing path: genuine migration-14 DB with Wave-2 data -> 15. ---
    existing_path = OUT / "existing14to15.db"
    existing_path.unlink(missing_ok=True)
    connection = sqlite3.connect(existing_path)
    connection.row_factory = sqlite3.Row
    try:
        upgrade_to(connection, 14)
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 14
        assert "review_events" not in tables(connection)
        connection.execute(
            "INSERT INTO students(student_id, created_at, is_synthetic)"
            " VALUES ('S1', '2026-01-01T00:00:00+00:00', 0)"
        )
        connection.execute(
            "INSERT INTO writing_tasks(task_id, student_id, writing_prompt,"
            " writing_context, task_type, created_at)"
            " VALUES ('WT000001', 'S1', 'Parks prompt', 'cet6',"
            " 'argumentative', '2026-01-01T00:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO learning_items(learning_item_id, student_id,"
            " originating_evidence_json, task_id, category, status,"
            " created_at, updated_at)"
            " VALUES ('LI000001', 'S1',"
            " '{\"source\":\"priority_plan\",\"kind\":\"l2\"}',"
            " 'WT000001', 'grammar', 'proposed',"
            " '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')"
        )
        before = dict(
            connection.execute(
                "SELECT * FROM learning_items WHERE learning_item_id='LI000001'"
            ).fetchone()
        )
        assert upgrade(connection) == 15
        after = dict(
            connection.execute(
                "SELECT * FROM learning_items WHERE learning_item_id='LI000001'"
            ).fetchone()
        )
        check(
            "v14-era Wave-2 learning_item row byte-identical after upgrade",
            after == before,
            f"row keys preserved; no_fsrs_note={after.get('no_fsrs_note')!r}",
        )
        wt = dict(
            connection.execute(
                "SELECT * FROM writing_tasks WHERE task_id='WT000001'"
            ).fetchone()
        )
        check(
            "writing_task preserved after upgrade",
            wt["writing_prompt"] == "Parks prompt"
            and wt["writing_context"] == "cet6",
            str(wt),
        )
        check(
            "review tables coexist after upgrade",
            {
                "practice_activities",
                "review_events",
                "learning_item_scheduler_states",
            }
            <= tables(connection),
            "3 review tables present",
        )
        ledger = {
            r["version"]
            for r in connection.execute("SELECT version FROM schema_migrations")
        }
        check("ledger 1..15 after existing upgrade", ledger == set(range(1, 16)), "")
        # Idempotence.
        second = upgrade(connection)
        check(
            "re-upgrade idempotent, data preserved",
            second == 15
            and connection.execute(
                "SELECT 1 FROM learning_items WHERE learning_item_id='LI000001'"
            ).fetchone()
            is not None,
            f"second upgrade()={second}",
        )
    finally:
        connection.close()

    # --- 3. Close/reopen same file + provenance reconstruction + single file. ---
    db_path = OUT / "reopen.db"
    db_path.unlink(missing_ok=True)
    db_a = Database(db_path)
    db_a.initialize()
    wave2 = SQLiteWave2Repository(db_a._connection_manager)
    wave2.save_learning_item(
        LearningItem(
            learning_item_id="LI000002",
            student_id="S1",
            category="grammar",
        )
    )
    service = ReviewService(
        db_a._review_repository,
        FSRSSchedulerAdapter(),
        learning_item_reader=wave2,
    )
    activity = service.record_practice_activity(
        PracticeActivity(
            activity_id="PA-PENDING",
            student_id="S1",
            learning_item_id="LI000002",
            activity_type="blank_fill",
            status="completed",
            occurred_at=T0,
        )
    )
    event = service.record_review(
        student_id="S1",
        learning_item_id="LI000002",
        reviewed_at=T0,
        system_provisional_rating=Rating.GOOD,
        learner_self_rating=Rating.HARD,
        practice_activity_id=activity.activity_id,
    )
    del db_a, wave2, service, activity, event

    db_b = Database(db_path)
    db_b.initialize()  # idempotent re-init on existing 15 DB
    wave2_b = SQLiteWave2Repository(db_b._connection_manager)
    service_b = ReviewService(
        db_b._review_repository,
        FSRSSchedulerAdapter(),
        learning_item_reader=wave2_b,
    )
    events = service_b.list_review_events("LI000002")
    activities = service_b.list_practice_activities("LI000002")
    state, identity = service_b.get_schedule("LI000002")
    check(
        "close/reopen: review event survives on same file",
        len(events) == 1 and events[0].review_event_id.startswith("RE"),
        f"events={[e.review_event_id for e in events]}",
    )
    check(
        "close/reopen: practice activity survives",
        len(activities) == 1 and activities[0].activity_id.startswith("PA"),
        f"activities={[a.activity_id for a in activities]}",
    )
    check(
        "close/reopen: scheduler state survives with identity",
        state is not None and state.state == "learning" and identity is not None,
        f"state={state.model_dump(mode='json') if state else None}, "
        f"identity={identity.library_version if identity else None}",
    )
    item = wave2_b.get_learning_item("LI000002")
    check(
        "LearningItem identity stable after reopen",
        item is not None and item.learning_item_id == "LI000002",
        str(item.learning_item_id if item else None),
    )

    # Provenance: replay the real scheduler on stored state_before + rating.
    ev = events[0]
    adapter = FSRSSchedulerAdapter()
    replayed, _ = adapter.review(
        ev.state_before, ev.final_scheduler_rating, ev.reviewed_at
    )
    check(
        "deterministic reconstruction: replay(state_before, final, reviewed_at) == state_after",
        replayed.model_dump(mode="json")
        == ev.state_after.model_dump(mode="json"),
        (
            f"replayed={replayed.model_dump(mode='json')} "
            f"stored={ev.state_after.model_dump(mode='json')}"
        ),
    )
    check(
        "provenance persisted: rule version + scheduler identity + parameters",
        ev.rating_rule_version == "rating-rule-v1.0.0"
        and ev.scheduler_implementation == "py-fsrs"
        and ev.scheduler_version == "6.3.2"
        and isinstance(ev.scheduler_parameters, dict)
        and ev.scheduler_parameters.get("enable_fuzzing") is False,
        f"rule={ev.rating_rule_version}, impl={ev.scheduler_implementation}, "
        f"ver={ev.scheduler_version}",
    )

    # Single SQLite file: database_list has exactly one attached DB.
    with db_b._connection_manager.connect() as connection:
        listed = connection.execute("PRAGMA database_list").fetchall()
        check(
            "exactly one SQLite file (no ATTACH)",
            len(listed) == 1,
            f"database_list={[r[2] for r in listed]}",
        )

    ok = sum(1 for r in RESULTS if r["ok"])
    print(f"\nSUMMARY {ok}/{len(RESULTS)} passed")
    raise SystemExit(0 if ok == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
