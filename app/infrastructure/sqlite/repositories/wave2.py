"""Additive Wave-2 persistence repository (Goal PDW2-A-CORE-PERSISTENCE).

``SQLiteWave2Repository`` owns the migration-14 table families:

- writing_tasks: task/context metadata for the L2 revision loop.
- submission_revisions: revision relationship records (ancestry,
  timestamps, task-context/analysis/feedback links) layered over the
  existing revision_groups/revision_snapshots contract.
- learning_observations: longitudinal learner observations.
- learning_items: learner-owned items with feedback and revision history.

This repository is additive and standalone: it is NOT composed into
``app.database.repository.Database`` by this Goal (that wiring is deferred to
the Wave-2 assembly follow-up); it is constructed with a
``SQLiteConnectionManager`` and remains directly usable by later department
Goals (LEARNER PDW2-B, L2 PDW2-C).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.infrastructure.sqlite import SQLiteConnectionManager


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class WritingTask:
    """Task/context metadata row (writing_tasks)."""

    task_id: str | None = None
    student_id: str = ""
    writing_prompt: str = ""
    genre: str = "argumentative essay"
    task_type: str = "independent_writing"
    modality: str = "written"
    reference_group_id: str | None = None
    created_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)


@dataclass
class SubmissionRevisionLink:
    """Revision relationship record (submission_revisions)."""

    revision_link_id: str | None = None
    revision_group_id: str = ""
    source_submission_id: int = 0
    target_submission_id: int = 0
    ancestry: list[int] = field(default_factory=list)
    task_id: str | None = None
    analysis_run_id: str | None = None
    feedback_record_id: int | None = None
    revision_sequence: int = 1
    created_at: str | None = None
    limitations: list[str] = field(default_factory=list)


@dataclass
class LearningObservation:
    """Longitudinal learner observation (learning_observations)."""

    observation_id: str | None = None
    student_id: str = ""
    observation_type: str = "difficulty"
    evidence_refs: list[Any] = field(default_factory=list)
    task_id: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    occurrence_count: int = 1
    first_observed_at: str | None = None
    last_observed_at: str | None = None
    recency: str = "unknown"
    revision_response: dict[str, Any] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    created_at: str | None = None


@dataclass
class LearningItem:
    """Learner-owned item (learning_items)."""

    learning_item_id: str | None = None
    student_id: str = ""
    originating_evidence: dict[str, Any] = field(default_factory=dict)
    feedback_reference: str | None = None
    revision_history: list[Any] = field(default_factory=list)
    task_id: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    status: str = "proposed"
    created_at: str | None = None
    updated_at: str | None = None


class SQLiteWave2Repository:
    """Additive repository over the Wave-2 migration-14 table families."""

    def __init__(self, connection_manager: SQLiteConnectionManager):
        self._connection_manager = connection_manager

    # ------------------------------------------------------------------
    # writing_tasks
    # ------------------------------------------------------------------

    def save_writing_task(self, task: WritingTask) -> WritingTask:
        now = task.created_at or _utc_now()
        with self._connection_manager.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO writing_tasks(
                    student_id, writing_prompt, genre, task_type, modality,
                    reference_group_id, created_at, metadata_json,
                    limitations_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (task.student_id, task.writing_prompt, task.genre,
                 task.task_type, task.modality, task.reference_group_id, now,
                 json.dumps(task.metadata), json.dumps(task.limitations)),
            )
            task_id = f"WT{int(cursor.lastrowid):06d}"
            connection.execute(
                "UPDATE writing_tasks SET task_id=? WHERE rowid=?",
                (task_id, int(cursor.lastrowid)),
            )
        return WritingTask(
            task_id=task_id,
            student_id=task.student_id,
            writing_prompt=task.writing_prompt,
            genre=task.genre,
            task_type=task.task_type,
            modality=task.modality,
            reference_group_id=task.reference_group_id,
            created_at=now,
            metadata=task.metadata,
            limitations=task.limitations,
        )

    def get_writing_task(self, task_id: str) -> WritingTask | None:
        with self._connection_manager.connect() as connection:
            row = connection.execute(
                "SELECT * FROM writing_tasks WHERE task_id=?", (task_id,)
            ).fetchone()
        return _writing_task_from_row(row) if row else None

    def list_writing_tasks(self, student_id: str) -> list[WritingTask]:
        with self._connection_manager.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM writing_tasks WHERE student_id=?"
                " ORDER BY created_at, task_id",
                (student_id,),
            ).fetchall()
        return [_writing_task_from_row(row) for row in rows]

    # ------------------------------------------------------------------
    # submission_revisions
    # ------------------------------------------------------------------

    def save_submission_revision(
        self, link: SubmissionRevisionLink
    ) -> SubmissionRevisionLink:
        now = link.created_at or _utc_now()
        with self._connection_manager.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO submission_revisions(
                    revision_group_id, source_submission_id,
                    target_submission_id, ancestry_json, task_id,
                    analysis_run_id, feedback_record_id, revision_sequence,
                    created_at, limitations_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (link.revision_group_id, link.source_submission_id,
                 link.target_submission_id, json.dumps(link.ancestry),
                 link.task_id, link.analysis_run_id, link.feedback_record_id,
                 link.revision_sequence, now, json.dumps(link.limitations)),
            )
            revision_link_id = f"SR{int(cursor.lastrowid):06d}"
            connection.execute(
                "UPDATE submission_revisions SET revision_link_id=? WHERE rowid=?",
                (revision_link_id, int(cursor.lastrowid)),
            )
        return SubmissionRevisionLink(
            revision_link_id=revision_link_id,
            revision_group_id=link.revision_group_id,
            source_submission_id=link.source_submission_id,
            target_submission_id=link.target_submission_id,
            ancestry=link.ancestry,
            task_id=link.task_id,
            analysis_run_id=link.analysis_run_id,
            feedback_record_id=link.feedback_record_id,
            revision_sequence=link.revision_sequence,
            created_at=now,
            limitations=link.limitations,
        )

    def get_submission_revision(
        self, revision_link_id: str
    ) -> SubmissionRevisionLink | None:
        with self._connection_manager.connect() as connection:
            row = connection.execute(
                "SELECT * FROM submission_revisions WHERE revision_link_id=?",
                (revision_link_id,),
            ).fetchone()
        return _submission_revision_from_row(row) if row else None

    def list_submission_revisions(
        self, revision_group_id: str
    ) -> list[SubmissionRevisionLink]:
        with self._connection_manager.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM submission_revisions WHERE revision_group_id=?"
                " ORDER BY revision_sequence, revision_link_id",
                (revision_group_id,),
            ).fetchall()
        return [_submission_revision_from_row(row) for row in rows]

    def list_submission_revisions_for_submission(
        self, target_submission_id: int
    ) -> list[SubmissionRevisionLink]:
        with self._connection_manager.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM submission_revisions WHERE target_submission_id=?"
                " ORDER BY created_at, revision_link_id",
                (target_submission_id,),
            ).fetchall()
        return [_submission_revision_from_row(row) for row in rows]

    # ------------------------------------------------------------------
    # learning_observations
    # ------------------------------------------------------------------

    def save_learning_observation(
        self, observation: LearningObservation
    ) -> LearningObservation:
        created_at = observation.created_at or _utc_now()
        first_observed_at = observation.first_observed_at or created_at
        last_observed_at = observation.last_observed_at or created_at
        with self._connection_manager.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO learning_observations(
                    student_id, observation_type, evidence_refs_json, task_id,
                    context_json, occurrence_count, first_observed_at,
                    last_observed_at, recency, revision_response_json,
                    limitations_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (observation.student_id, observation.observation_type,
                 json.dumps(observation.evidence_refs), observation.task_id,
                 json.dumps(observation.context), observation.occurrence_count,
                 first_observed_at, last_observed_at, observation.recency,
                 json.dumps(observation.revision_response),
                 json.dumps(observation.limitations), created_at),
            )
            observation_id = f"LO{int(cursor.lastrowid):06d}"
            connection.execute(
                "UPDATE learning_observations SET observation_id=? WHERE rowid=?",
                (observation_id, int(cursor.lastrowid)),
            )
        return LearningObservation(
            observation_id=observation_id,
            student_id=observation.student_id,
            observation_type=observation.observation_type,
            evidence_refs=observation.evidence_refs,
            task_id=observation.task_id,
            context=observation.context,
            occurrence_count=observation.occurrence_count,
            first_observed_at=first_observed_at,
            last_observed_at=last_observed_at,
            recency=observation.recency,
            revision_response=observation.revision_response,
            limitations=observation.limitations,
            created_at=created_at,
        )

    def get_learning_observation(
        self, observation_id: str
    ) -> LearningObservation | None:
        with self._connection_manager.connect() as connection:
            row = connection.execute(
                "SELECT * FROM learning_observations WHERE observation_id=?",
                (observation_id,),
            ).fetchone()
        return _learning_observation_from_row(row) if row else None

    def list_learning_observations(
        self, student_id: str, observation_type: str | None = None
    ) -> list[LearningObservation]:
        sql = "SELECT * FROM learning_observations WHERE student_id=?"
        params: list[Any] = [student_id]
        if observation_type is not None:
            sql += " AND observation_type=?"
            params.append(observation_type)
        sql += " ORDER BY last_observed_at, observation_id"
        with self._connection_manager.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [_learning_observation_from_row(row) for row in rows]

    # ------------------------------------------------------------------
    # learning_items
    # ------------------------------------------------------------------

    def save_learning_item(self, item: LearningItem) -> LearningItem:
        created_at = item.created_at or _utc_now()
        updated_at = item.updated_at or created_at
        with self._connection_manager.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO learning_items(
                    student_id, originating_evidence_json, feedback_reference,
                    revision_history_json, task_id, context_json, status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (item.student_id, json.dumps(item.originating_evidence),
                 item.feedback_reference, json.dumps(item.revision_history),
                 item.task_id, json.dumps(item.context), item.status,
                 created_at, updated_at),
            )
            learning_item_id = f"LI{int(cursor.lastrowid):06d}"
            connection.execute(
                "UPDATE learning_items SET learning_item_id=? WHERE rowid=?",
                (learning_item_id, int(cursor.lastrowid)),
            )
        return LearningItem(
            learning_item_id=learning_item_id,
            student_id=item.student_id,
            originating_evidence=item.originating_evidence,
            feedback_reference=item.feedback_reference,
            revision_history=item.revision_history,
            task_id=item.task_id,
            context=item.context,
            status=item.status,
            created_at=created_at,
            updated_at=updated_at,
        )

    def get_learning_item(self, learning_item_id: str) -> LearningItem | None:
        with self._connection_manager.connect() as connection:
            row = connection.execute(
                "SELECT * FROM learning_items WHERE learning_item_id=?",
                (learning_item_id,),
            ).fetchone()
        return _learning_item_from_row(row) if row else None

    def list_learning_items(
        self, student_id: str, status: str | None = None
    ) -> list[LearningItem]:
        sql = "SELECT * FROM learning_items WHERE student_id=?"
        params: list[Any] = [student_id]
        if status is not None:
            sql += " AND status=?"
            params.append(status)
        sql += " ORDER BY updated_at, learning_item_id"
        with self._connection_manager.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [_learning_item_from_row(row) for row in rows]

    def update_learning_item_status(
        self, learning_item_id: str, status: str, updated_at: str
    ) -> LearningItem | None:
        with self._connection_manager.connect() as connection:
            cursor = connection.execute(
                "UPDATE learning_items SET status=?, updated_at=?"
                " WHERE learning_item_id=?",
                (status, updated_at, learning_item_id),
            )
            if cursor.rowcount == 0:
                return None
            row = connection.execute(
                "SELECT * FROM learning_items WHERE learning_item_id=?",
                (learning_item_id,),
            ).fetchone()
        return _learning_item_from_row(row)


def _writing_task_from_row(row) -> WritingTask:
    item = dict(row)
    return WritingTask(
        task_id=item["task_id"],
        student_id=item["student_id"],
        writing_prompt=item["writing_prompt"],
        genre=item["genre"],
        task_type=item["task_type"],
        modality=item["modality"],
        reference_group_id=item["reference_group_id"],
        created_at=item["created_at"],
        metadata=json.loads(item["metadata_json"]),
        limitations=json.loads(item["limitations_json"]),
    )


def _submission_revision_from_row(row) -> SubmissionRevisionLink:
    item = dict(row)
    return SubmissionRevisionLink(
        revision_link_id=item["revision_link_id"],
        revision_group_id=item["revision_group_id"],
        source_submission_id=item["source_submission_id"],
        target_submission_id=item["target_submission_id"],
        ancestry=json.loads(item["ancestry_json"]),
        task_id=item["task_id"],
        analysis_run_id=item["analysis_run_id"],
        feedback_record_id=item["feedback_record_id"],
        revision_sequence=item["revision_sequence"],
        created_at=item["created_at"],
        limitations=json.loads(item["limitations_json"]),
    )


def _learning_observation_from_row(row) -> LearningObservation:
    item = dict(row)
    return LearningObservation(
        observation_id=item["observation_id"],
        student_id=item["student_id"],
        observation_type=item["observation_type"],
        evidence_refs=json.loads(item["evidence_refs_json"]),
        task_id=item["task_id"],
        context=json.loads(item["context_json"]),
        occurrence_count=item["occurrence_count"],
        first_observed_at=item["first_observed_at"],
        last_observed_at=item["last_observed_at"],
        recency=item["recency"],
        revision_response=json.loads(item["revision_response_json"]),
        limitations=json.loads(item["limitations_json"]),
        created_at=item["created_at"],
    )


def _learning_item_from_row(row) -> LearningItem:
    item = dict(row)
    return LearningItem(
        learning_item_id=item["learning_item_id"],
        student_id=item["student_id"],
        originating_evidence=json.loads(item["originating_evidence_json"]),
        feedback_reference=item["feedback_reference"],
        revision_history=json.loads(item["revision_history_json"]),
        task_id=item["task_id"],
        context=json.loads(item["context_json"]),
        status=item["status"],
        created_at=item["created_at"],
        updated_at=item["updated_at"],
    )

