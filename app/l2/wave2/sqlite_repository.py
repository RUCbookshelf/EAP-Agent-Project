"""Self-contained TEST-ONLY SQLite implementation of RevisionLoopRepository.

Goal PDW2-C-L2-REVISION-SCAFFOLD: the L2 branch must not import CORE-branch
persistence (``app.infrastructure.sqlite.repositories.wave2`` or migration-14
DDL; those land at integration). This module owns its own tables
(``wave2_l2_*``), created inside a TEST-ONLY database passed by the caller
(for example a pytest tmp_path database). It is never wired into the
composition root and must never serve as the shared persistence layer.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from app.l2.wave2.models import (
    LearningItem,
    LearningItemStatus,
    PriorityRevisionPlan,
    RevisionObservation,
    ScaffoldEvent,
    SubmissionVersion,
    WritingTask,
)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS wave2_l2_writing_tasks (
    task_id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS wave2_l2_submission_versions (
    task_id TEXT NOT NULL,
    submission_id INTEGER NOT NULL,
    version_number INTEGER NOT NULL,
    record_json TEXT NOT NULL,
    PRIMARY KEY (task_id, submission_id)
);
CREATE TABLE IF NOT EXISTS wave2_l2_revision_observations (
    observation_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    record_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS wave2_l2_priority_plans (
    plan_id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL,
    record_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS wave2_l2_scaffold_events (
    scaffold_event_id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL,
    learning_item_id TEXT,
    record_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS wave2_l2_learning_items (
    learning_item_id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL,
    status TEXT NOT NULL,
    record_json TEXT NOT NULL
);
"""


class SqliteRevisionLoopRepository:
    """SQLite implementation creating its own tables (TEST-ONLY databases)."""

    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        self._connection = sqlite3.connect(str(self._path))
        self._connection.row_factory = sqlite3.Row
        self._counters: dict[str, int] = {}
        self._create_schema()

    def _next_id(self, prefix: str) -> str:
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return f"{prefix}{self._counters[prefix]:06d}"

    def _create_schema(self) -> None:
        self._connection.executescript(_SCHEMA)
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "SqliteRevisionLoopRepository":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def save_writing_task(self, task: WritingTask) -> WritingTask:
        if task.task_id == "WT-PENDING" or not task.task_id.startswith("WT"):
            task = task.model_copy(update={"task_id": self._next_id("WT")})
        self._connection.execute(
            "INSERT OR REPLACE INTO wave2_l2_writing_tasks (task_id, record_json)"
            " VALUES (?, ?)",
            (task.task_id, task.model_dump_json()),
        )
        self._connection.commit()
        return task

    def get_writing_task(self, task_id: str) -> WritingTask | None:
        row = self._connection.execute(
            "SELECT record_json FROM wave2_l2_writing_tasks WHERE task_id=?",
            (task_id,),
        ).fetchone()
        return WritingTask.model_validate_json(row["record_json"]) if row else None

    def list_writing_tasks(self, student_id: str) -> list[WritingTask]:
        rows = self._connection.execute(
            "SELECT record_json FROM wave2_l2_writing_tasks"
        ).fetchall()
        return [
            task for task in (
                WritingTask.model_validate_json(row["record_json"]) for row in rows
            )
            if task.student_id == student_id
        ]

    def save_submission_version(
        self, version: SubmissionVersion,
    ) -> SubmissionVersion:
        self._connection.execute(
            "INSERT OR REPLACE INTO wave2_l2_submission_versions "
            "(task_id, submission_id, version_number, record_json) VALUES (?, ?, ?, ?)",
            (
                version.task_id, version.submission_id,
                version.version_number, version.model_dump_json(),
            ),
        )
        self._connection.commit()
        return version

    def get_submission_version(
        self, task_id: str, submission_id: int,
    ) -> SubmissionVersion | None:
        row = self._connection.execute(
            "SELECT record_json FROM wave2_l2_submission_versions"
            " WHERE task_id=? AND submission_id=?",
            (task_id, submission_id),
        ).fetchone()
        return SubmissionVersion.model_validate_json(row["record_json"]) if row else None

    def list_submission_versions(self, task_id: str) -> list[SubmissionVersion]:
        rows = self._connection.execute(
            "SELECT record_json FROM wave2_l2_submission_versions WHERE task_id=?"
            " ORDER BY version_number",
            (task_id,),
        ).fetchall()
        return [
           SubmissionVersion.model_validate_json(row["record_json"]) for row in rows
        ]

    def find_task_id_for_submission(self, submission_id: int) -> str | None:
        row = self._connection.execute(
            "SELECT task_id FROM wave2_l2_submission_versions WHERE submission_id=?",
            (submission_id,),
        ).fetchone()
        return row["task_id"] if row else None

    def save_revision_observation(self, observation: RevisionObservation) -> None:
        self._connection.execute(
            "INSERT OR REPLACE INTO wave2_l2_revision_observations "
            "(observation_id, task_id, record_json) VALUES (?, ?, ?)",
            (observation.observation_id, observation.task_id, observation.model_dump_json()),
        )
        self._connection.commit()

    def list_revision_observations(self, task_id: str) -> list[RevisionObservation]:
        rows = self._connection.execute(
            "SELECT record_json FROM wave2_l2_revision_observations WHERE task_id=?",
            (task_id,),
        ).fetchall()
        return [
            RevisionObservation.model_validate_json(row["record_json"]) for row in rows
        ]

    def save_priority_plan(self, plan: PriorityRevisionPlan) -> None:
        if plan.plan_id == "PP-PENDING" or not plan.plan_id.startswith("PP"):
            plan = plan.model_copy(update={"plan_id": self._next_id("PP")})
        self._connection.execute(
            "INSERT OR REPLACE INTO wave2_l2_priority_plans "
            "(plan_id, learner_id, record_json) VALUES (?, ?, ?)",
            (plan.plan_id, plan.learner_id, plan.model_dump_json()),
        )
        self._connection.commit()

    def get_priority_plan(self, plan_id: str) -> PriorityRevisionPlan | None:
        row = self._connection.execute(
            "SELECT record_json FROM wave2_l2_priority_plans WHERE plan_id=?",
            (plan_id,),
        ).fetchone()
        return PriorityRevisionPlan.model_validate_json(row["record_json"]) if row else None

    def list_priority_plans(self, learner_id: str) -> list[PriorityRevisionPlan]:
        rows = self._connection.execute(
            "SELECT record_json FROM wave2_l2_priority_plans WHERE learner_id=?",
            (learner_id,),
        ).fetchall()
        return [
            PriorityRevisionPlan.model_validate_json(row["record_json"]) for row in rows
        ]

    def save_scaffold_event(self, event: ScaffoldEvent) -> None:
        if event.scaffold_event_id == "SE-PENDING" or not event.scaffold_event_id.startswith("SE"):
            event = event.model_copy(
                update={"scaffold_event_id": self._next_id("SE")},
            )
        self._connection.execute(
            "INSERT OR REPLACE INTO wave2_l2_scaffold_events "
            "(scaffold_event_id, learner_id, learning_item_id, record_json)"
            " VALUES (?, ?, ?, ?)",
            (
                event.scaffold_event_id, event.learner_id,
                event.learning_item_id, event.model_dump_json(),
            ),
        )
        self._connection.commit()

    def list_scaffold_events(
        self, learner_id: str, learning_item_id: str | None = None,
    ) -> list[ScaffoldEvent]:
        if learning_item_id is None:
            rows = self._connection.execute(
                "SELECT record_json FROM wave2_l2_scaffold_events"
                " WHERE learner_id=?",
                (learner_id,),
            ).fetchall()
        else:
            rows = self._connection.execute(
                "SELECT record_json FROM wave2_l2_scaffold_events"
                " WHERE learner_id=? AND learning_item_id=?",
                (learner_id, learning_item_id),
            ).fetchall()
        events = [
            ScaffoldEvent.model_validate_json(row["record_json"]) for row in rows
        ]
        return sorted(events, key=lambda event: event.requested_at)

    def save_learning_item(self, item: LearningItem) -> LearningItem:
        if item.learning_item_id == "LI-PENDING" or not item.learning_item_id.startswith("LI"):
            item = item.model_copy(update={"learning_item_id": self._next_id("LI")})
        self._connection.execute(
            "INSERT OR REPLACE INTO wave2_l2_learning_items "
            "(learning_item_id, student_id, status, record_json) VALUES (?, ?, ?, ?)",
            (
                item.learning_item_id, item.student_id,
                item.status, item.model_dump_json(),
            ),
        )
        self._connection.commit()
        return item

    def get_learning_item(self, learning_item_id: str) -> LearningItem | None:
        row = self._connection.execute(
            "SELECT record_json FROM wave2_l2_learning_items"
            " WHERE learning_item_id=?",
            (learning_item_id,),
        ).fetchone()
        return LearningItem.model_validate_json(row["record_json"]) if row else None

    def list_learning_items(
        self, student_id: str, status: LearningItemStatus | None = None,
    ) -> list[LearningItem]:
        if status is None:
            rows = self._connection.execute(
                "SELECT record_json FROM wave2_l2_learning_items WHERE student_id=?"
                "",
                (student_id,),
            ).fetchall()
        else:
            rows = self._connection.execute(
                "SELECT record_json FROM wave2_l2_learning_items"
                " WHERE student_id=? AND status=?",
                (student_id, status),
            ).fetchall()
        items = [
            LearningItem.model_validate_json(row["record_json"]) for row in rows
        ]
        return sorted(items, key=lambda item: item.updated_at)

    def update_learning_item_status(
        self, learning_item_id: str, status: LearningItemStatus,
        updated_at: datetime,
    ) -> LearningItem | None:
        row = self._connection.execute(
            "SELECT record_json FROM wave2_l2_learning_items"
            " WHERE learning_item_id=?",
            (learning_item_id,),
        ).fetchone()
        if row is None:
            return None
        item = LearningItem.model_validate_json(row["record_json"])
        updated = item.model_copy(update={"status": status, "updated_at": updated_at})
        self._connection.execute(
            "UPDATE wave2_l2_learning_items SET status=?, record_json=?"
            " WHERE learning_item_id=?",
            (status, updated.model_dump_json(), learning_item_id),
        )
        self._connection.commit()
        return updated


__all__ = ["SqliteRevisionLoopRepository"]
