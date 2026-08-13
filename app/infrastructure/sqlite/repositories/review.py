"""SQLite repository for the shared Review / Scheduling Foundation.

Owns the migration-15 table families (one SQLite database, one composition
root):

- ``practice_activities``: shared PracticeActivity persistence.
- ``review_events``: durable review events with separate rating channels.
- ``learning_item_scheduler_states``: ONE durable FSRS memory-scheduling
  state per LearningItem (outside LearningItem v1, which keeps its no-FSRS
  contract).

SQL, connections, migrations, and transactions stay in this infrastructure
module; services depend on the review repository protocol.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.infrastructure.sqlite import SQLiteConnectionManager
from app.review.models import (
    Rating,
    ReviewEvent,
    PracticeActivity,
    PracticeActivityStatus,
    SchedulerIdentity,
    SchedulerStateRecord,
    SchedulerStateSnapshot,
    SchedulingResult,
)
from app.review.protocols import ReviewRepositoryConflictError


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rating_text(value: Any) -> str | None:
    if value is None:
        return None
    return Rating(value).value if isinstance(value, Rating) else str(value)


def _rating_from_text(value: Any) -> Rating | None:
    if value is None:
        return None
    return Rating(str(value))


def _duplicate_primary_key(exc: sqlite3.IntegrityError) -> bool:
    """True when the IntegrityError is a PRIMARY KEY / UNIQUE conflict."""
    code = getattr(exc, "sqlite_errorcode", None)
    if code in (1555, 2067):  # SQLITE_CONSTRAINT_PRIMARYKEY / _UNIQUE
        return True
    return "UNIQUE constraint failed" in str(exc)


class SQLiteReviewRepository:
    """Additive repository over the migration-15 table families."""

    def __init__(self, connection_manager: SQLiteConnectionManager):
        self._connection_manager = connection_manager

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _next_suffix_id(
        connection, table: str, column: str, prefix: str
    ) -> str:
        row = connection.execute(
            f"SELECT MAX(CAST(SUBSTR({column}, {len(prefix) + 1}) AS INTEGER))"
            f" FROM {table}"
        ).fetchone()
        next_number = int(row[0] or 0) + 1
        return f"{prefix}{next_number:06d}"

    # ------------------------------------------------------------------
    # practice_activities
    # ------------------------------------------------------------------

    def save_practice_activity(
        self, activity: PracticeActivity
    ) -> PracticeActivity:
        with self._connection_manager.transaction() as connection:
            activity_id = activity.activity_id
            if (
                activity_id is None
                or activity_id == "PA-PENDING"
                or not str(activity_id).startswith("PA")
            ):
                activity_id = self._next_suffix_id(
                    connection, "practice_activities", "activity_id", "PA"
                )
            existing = connection.execute(
                "SELECT 1 FROM practice_activities WHERE activity_id=?",
                (activity_id,),
            ).fetchone()
            if existing is not None:
                raise ReviewRepositoryConflictError(
                    "practice_activity_already_exists",
                    f"Practice activity {activity_id!r} already exists; "
                    "durable evidence is append-only and will not be "
                    "replaced.",
                )
            try:
                connection.execute(
                    """INSERT INTO practice_activities(
                        activity_id, student_id, learning_item_id,
                        activity_type, source, status, occurred_at,
                        completed_at, created_at, provenance_json,
                        evaluator, evaluation_id, evaluator_version,
                        evidence_kind, authentic_evidence_status,
                        limitations_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        activity_id,
                        activity.student_id,
                        activity.learning_item_id,
                        activity.activity_type,
                        activity.source,
                        activity.status.value,
                        activity.occurred_at.isoformat(),
                        (
                            activity.completed_at.isoformat()
                            if activity.completed_at is not None
                            else None
                        ),
                        activity.created_at.isoformat(),
                        json.dumps(activity.provenance, sort_keys=True),
                        activity.evaluator,
                        activity.evaluation_id,
                        activity.evaluator_version,
                        activity.evidence_kind,
                        activity.authentic_evidence_status,
                        json.dumps(activity.limitations, sort_keys=True),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                if _duplicate_primary_key(exc):
                    raise ReviewRepositoryConflictError(
                        "practice_activity_already_exists",
                        f"Practice activity {activity_id!r} already exists; "
                        "durable evidence is append-only and will not be "
                        "replaced.",
                    ) from exc
                raise
        return activity.model_copy(update={"activity_id": activity_id})

    def get_practice_activity(
        self, activity_id: str
    ) -> PracticeActivity | None:
        with self._connection_manager.connect() as connection:
            row = connection.execute(
                "SELECT * FROM practice_activities WHERE activity_id=?",
                (activity_id,),
            ).fetchone()
        return _practice_activity_from_row(row) if row else None

    def list_practice_activities(
        self, learning_item_id: str
    ) -> list[PracticeActivity]:
        with self._connection_manager.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM practice_activities WHERE learning_item_id=?"
                " ORDER BY occurred_at, activity_id",
                (learning_item_id,),
            ).fetchall()
        return [_practice_activity_from_row(row) for row in rows]

    # ------------------------------------------------------------------
    # review_events + scheduler states (atomic)
    # ------------------------------------------------------------------

    def record_review_event(
        self, event: ReviewEvent, state_row: dict[str, object]
    ) -> ReviewEvent:
        """Insert the review event and upsert the scheduler state atomically."""
        with self._connection_manager.transaction() as connection:
            review_event_id = event.review_event_id
            if (
                review_event_id is None
                or review_event_id == "RE-PENDING"
                or not str(review_event_id).startswith("RE")
            ):
                review_event_id = self._next_suffix_id(
                    connection, "review_events", "review_event_id", "RE"
                )
            existing = connection.execute(
                "SELECT 1 FROM review_events WHERE review_event_id=?",
                (review_event_id,),
            ).fetchone()
            if existing is not None:
                raise ReviewRepositoryConflictError(
                    "review_event_already_exists",
                    f"Review event {review_event_id!r} already exists; "
                    "durable evidence is append-only and will not be "
                    "replaced.",
                )
            try:
                connection.execute(
                    """INSERT INTO review_events(
                        review_event_id, student_id, learning_item_id,
                        practice_activity_id, reviewed_at,
                        system_provisional_rating, learner_self_rating,
                        final_scheduler_rating, rating_rule_version,
                        scheduler_implementation, scheduler_version,
                        scheduler_parameters_json, state_before_json,
                        state_after_json, scheduling_result_json,
                        authentic_evidence_status, provenance_json,
                        limitations_json, recorded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        review_event_id,
                        event.student_id,
                        event.learning_item_id,
                        event.practice_activity_id,
                        event.reviewed_at.isoformat(),
                        event.system_provisional_rating.value,
                        _rating_text(event.learner_self_rating),
                        event.final_scheduler_rating.value,
                        event.rating_rule_version,
                        event.scheduler_implementation,
                        event.scheduler_version,
                        json.dumps(event.scheduler_parameters, sort_keys=True),
                        json.dumps(
                            event.state_before.model_dump(mode="json"),
                            sort_keys=True,
                        ),
                        json.dumps(
                            event.state_after.model_dump(mode="json"),
                            sort_keys=True,
                        ),
                        json.dumps(
                            event.scheduling_result.model_dump(mode="json"),
                            sort_keys=True,
                        ),
                        event.authentic_evidence_status,
                        json.dumps(event.provenance, sort_keys=True),
                        json.dumps(event.limitations, sort_keys=True),
                        event.recorded_at.isoformat(),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                if _duplicate_primary_key(exc):
                    raise ReviewRepositoryConflictError(
                        "review_event_already_exists",
                        f"Review event {review_event_id!r} already exists; "
                        "durable evidence is append-only and will not be "
                        "replaced.",
                    ) from exc
                raise
            identity = SchedulerIdentity.model_validate(state_row["identity"])
            state = SchedulerStateSnapshot.model_validate(state_row["state"])
            connection.execute(
                """INSERT OR REPLACE INTO learning_item_scheduler_states(
                    learning_item_id, student_id, scheduler_implementation,
                    scheduler_version, scheduler_parameters_json,
                    state_json, rating_rule_version, updated_at,
                    last_review_event_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(state_row["learning_item_id"]),
                    str(state_row["student_id"]),
                    identity.implementation,
                    identity.library_version,
                    json.dumps(identity.parameters, sort_keys=True),
                    json.dumps(state.model_dump(mode="json"), sort_keys=True),
                    str(state_row["rating_rule_version"]),
                    str(state_row["updated_at"]),
                    review_event_id,
                ),
            )
            row = connection.execute(
                "SELECT * FROM review_events WHERE review_event_id=?",
                (review_event_id,),
            ).fetchone()
        return _review_event_from_row(row)  # type: ignore[arg-type]

    def get_review_event(self, review_event_id: str) -> ReviewEvent | None:
        with self._connection_manager.connect() as connection:
            row = connection.execute(
                "SELECT * FROM review_events WHERE review_event_id=?",
                (review_event_id,),
            ).fetchone()
        return _review_event_from_row(row) if row else None

    def list_review_events(
        self, learning_item_id: str
    ) -> list[ReviewEvent]:
        with self._connection_manager.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM review_events WHERE learning_item_id=?"
                " ORDER BY reviewed_at, review_event_id",
                (learning_item_id,),
            ).fetchall()
        return [_review_event_from_row(row) for row in rows]

    # ------------------------------------------------------------------
    # scheduler states
    # ------------------------------------------------------------------

    def get_scheduler_state(
        self, learning_item_id: str
    ) -> SchedulerStateRecord | None:
        with self._connection_manager.connect() as connection:
            row = connection.execute(
                "SELECT * FROM learning_item_scheduler_states"
                " WHERE learning_item_id=?",
                (learning_item_id,),
            ).fetchone()
        return _scheduler_state_from_row(row) if row else None


class SQLiteReviewEvidenceLookup:
    """Shared, learner-scoped lookup over the review-family tables.

    Resolves ownership and returns the durable shared record for
    practice-activity (``PA*``) and review-event (``RE*``) source ids.
    Unknown, empty, or non-review ids fail closed with ``None``; a record
    is returned only to its owner. The adapter is mechanical shared
    persistence: it does not apply acknowledgement wording, consent
    policy, admission, or Journey semantics. Downstream consumers (for
    example the LEARNER acknowledgement evidence port) own those rules.
    """

    def __init__(self, connection_manager: SQLiteConnectionManager):
        self._connection_manager = connection_manager

    def owner_of(self, source_id: str) -> str | None:
        if not isinstance(source_id, str) or not source_id:
            return None
        with self._connection_manager.connect() as connection:
            if source_id.startswith("PA"):
                row = connection.execute(
                    "SELECT student_id FROM practice_activities"
                    " WHERE activity_id=?",
                    (source_id,),
                ).fetchone()
            elif source_id.startswith("RE"):
                row = connection.execute(
                    "SELECT student_id FROM review_events"
                    " WHERE review_event_id=?",
                    (source_id,),
                ).fetchone()
            else:
                return None
        return row["student_id"] if row else None

    def get_record(self, learner_id: str, source_id: str) -> Any | None:
        owner = self.owner_of(source_id)
        if owner is None or owner != learner_id:
            return None
        with self._connection_manager.connect() as connection:
            if source_id.startswith("PA"):
                row = connection.execute(
                    "SELECT * FROM practice_activities WHERE activity_id=?",
                    (source_id,),
                ).fetchone()
                return _practice_activity_from_row(row) if row else None
            if source_id.startswith("RE"):
                row = connection.execute(
                    "SELECT * FROM review_events WHERE review_event_id=?",
                    (source_id,),
                ).fetchone()
                return _review_event_from_row(row) if row else None
        return None


# ---------------------------------------------------------------------------
# row mappers
# ---------------------------------------------------------------------------


def _practice_activity_from_row(row) -> PracticeActivity:
    return PracticeActivity(
        activity_id=row["activity_id"],
        student_id=row["student_id"],
        learning_item_id=row["learning_item_id"],
        activity_type=row["activity_type"],
        source=row["source"],
        status=PracticeActivityStatus(row["status"]),
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        completed_at=(
            datetime.fromisoformat(row["completed_at"])
            if row["completed_at"] is not None
            else None
        ),
        created_at=datetime.fromisoformat(row["created_at"]),
        evaluator=row["evaluator"],
        evaluation_id=row["evaluation_id"],
        evaluator_version=row["evaluator_version"],
        provenance=json.loads(row["provenance_json"]),
        evidence_kind=row["evidence_kind"],
        authentic_evidence_status=row["authentic_evidence_status"],
        limitations=json.loads(row["limitations_json"]),
    )


def _review_event_from_row(row) -> ReviewEvent:
    return ReviewEvent(
        review_event_id=row["review_event_id"],
        student_id=row["student_id"],
        learning_item_id=row["learning_item_id"],
        practice_activity_id=row["practice_activity_id"],
        reviewed_at=datetime.fromisoformat(row["reviewed_at"]),
        system_provisional_rating=Rating(row["system_provisional_rating"]),
        learner_self_rating=_rating_from_text(row["learner_self_rating"]),
        final_scheduler_rating=Rating(row["final_scheduler_rating"]),
        rating_rule_version=row["rating_rule_version"],
        scheduler_implementation=row["scheduler_implementation"],
        scheduler_version=row["scheduler_version"],
        scheduler_parameters=json.loads(row["scheduler_parameters_json"]),
        state_before=SchedulerStateSnapshot.model_validate(
            json.loads(row["state_before_json"])
        ),
        state_after=SchedulerStateSnapshot.model_validate(
            json.loads(row["state_after_json"])
        ),
        scheduling_result=SchedulingResult.model_validate(
            json.loads(row["scheduling_result_json"])
        ),
        authentic_evidence_status=row["authentic_evidence_status"],
        provenance=json.loads(row["provenance_json"]),
        limitations=json.loads(row["limitations_json"]),
        recorded_at=datetime.fromisoformat(row["recorded_at"]),
    )


def _scheduler_state_from_row(row) -> SchedulerStateRecord:
    return SchedulerStateRecord(
        learning_item_id=row["learning_item_id"],
        student_id=row["student_id"],
        identity=SchedulerIdentity(
            implementation=row["scheduler_implementation"],
            library_version=row["scheduler_version"],
            algorithm="FSRS",
            parameters=json.loads(row["scheduler_parameters_json"]),
        ),
        state=SchedulerStateSnapshot.model_validate(
            json.loads(row["state_json"])
        ),
        rating_rule_version=row["rating_rule_version"],
        updated_at=row["updated_at"],
        last_review_event_id=row["last_review_event_id"],
    )


__all__ = ["SQLiteReviewEvidenceLookup", "SQLiteReviewRepository"]
