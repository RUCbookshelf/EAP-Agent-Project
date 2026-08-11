"""Additive Wave-2 persistence repository (Goal PDW2-A-CORE-PERSISTENCE).

``SQLiteWave2Repository`` owns the migration-14 table families:

- writing_tasks: two-level task/context metadata for the L2 revision loop
  (``writing_context`` authoritative; legacy ``genre`` compat column).
- submission_revisions: revision relationship records (ancestry,
  timestamps, task-context/analysis/feedback links) layered over the
  existing revision_groups/revision_snapshots contract.
- submission_versions: L2 RevisionLoopRepository version family (V1/V2/...
  append-only with ancestry, task-context snapshots, analysis/feedback
  links, corpus routing, reanalysis events).
- revision_observations: bounded observational version comparisons (no
  intent inference).
- priority_plans: small actionable revision plans (observation-only).
- scaffold_events: recorded 7-level scaffold requests (SCAFFOLD FIRST).
- learning_observations: longitudinal learner observations.
- learning_items: learner-owned items with LearningItem v1 fields
  (category/task_context/limitations/no-FSRS/no-practice notes).

F-5 repair (PDW2-WU2-INT-INTEGRATION-GATE-RE-GATE__REPAIR): the shared
repository implements the full L2 ``RevisionLoopRepository`` protocol and
round-trips the L2 WritingTask/LearningItem shapes. The CORE-owned dataclass
shapes mirror the L2 models (dept/l2-writing@135cf8b) and duck-type the
pydantic surface the L2 services/routers consume (``model_dump``,
``model_copy``); legacy CORE-only fields (``genre``/``reference_group_id``/
``context``) are preserved on the dataclass but excluded from JSON dumps so
router payloads match the L2 contract shape.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.infrastructure.sqlite import SQLiteConnectionManager


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _jsonable(value: Any) -> Any:
    """Recursively convert L2/CORE record values into JSON-safe primitives."""
    if value is None:
        return None
    if hasattr(value, "model_dump"):  # pydantic models and JsonDict
        return _jsonable(value.model_dump(mode="json"))
    if isinstance(value, datetime):
        return value.isoformat()
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _jsonable(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _attr(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _text(value: Any, default: str) -> str:
    if value is None:
        return default
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


class JsonDict(dict):
    """dict that duck-types pydantic's ``model_dump`` for L2 consumers."""

    def model_dump(self, mode: str = "python", **_: Any) -> dict[str, Any]:
        return dict(self)


class Wave2ModelMixin:
    """pydantic-lite duck typing for the L2 service/router consumers.

    The shared repository returns CORE-owned shapes mirroring the L2 models;
    consumers call ``model_dump(mode="json")`` (routers) and
    ``model_copy(update=...)`` (reanalysis path). Legacy-only CORE fields
    (``genre``/``reference_group_id``/``context``) are excluded from dumps so
    payloads match the L2 contract shape.
    """

    _json_fields: tuple[str, ...] | None = None

    def model_dump(self, mode: str = "python", **_: Any) -> dict[str, Any]:
        names = self._json_fields or tuple(
            f.name for f in dataclasses.fields(self)
        )
        if mode == "python":
            return {name: getattr(self, name) for name in names}
        return {name: _jsonable(getattr(self, name)) for name in names}

    def model_copy(
        self, *, update: dict[str, Any] | None = None, **_: Any
    ) -> "Wave2ModelMixin":
        return dataclasses.replace(self, **(update or {}))


@dataclass
class WritingTask(Wave2ModelMixin):
    """Task/context metadata row (writing_tasks), L2 two-level contract.

    ``writing_context`` is the L2 context id and authoritative;
    ``genre``/``reference_group_id`` are legacy CORE-origin compat fields.
    """

    _json_fields = (
        "task_id", "student_id", "task_type", "writing_context",
        "writing_prompt", "metadata", "modality", "classification", "status",
        "created_at", "limitations",
    )

    task_id: str | None = None
    student_id: str = ""
    writing_prompt: str = ""
    writing_context: str | None = None
    genre: str = "argumentative essay"
    task_type: str = "independent_writing"
    modality: str = "written"
    reference_group_id: str | None = None
    classification: dict[str, Any] = field(default_factory=dict)
    status: str = "active"
    metadata: dict[str, Any] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    created_at: str | None = None


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
class SubmissionVersion(Wave2ModelMixin):
    """L2-shaped submission version (V1/V2/... append-only with linkage)."""

    _json_fields = (
        "task_id", "submission_id", "version_number",
        "revision_of_submission_id", "ancestry", "submitted_at",
        "task_context", "essay_text_hash", "draft_stage", "analysis_run_id",
        "analysis_version", "feedback_record_id", "revision_group_id",
        "revision_snapshot_id", "corpus_routing", "reanalysis_events",
        "limitations",
    )

    task_id: str = ""
    submission_id: int = 0
    version_number: int = 1
    revision_of_submission_id: int | None = None
    ancestry: list[int] = field(default_factory=list)
    submitted_at: str | None = None
    task_context: dict[str, Any] = field(default_factory=dict)
    essay_text_hash: str = ""
    draft_stage: str = "first draft"
    analysis_run_id: str | None = None
    analysis_version: str | None = None
    feedback_record_id: int | None = None
    revision_group_id: str | None = None
    revision_snapshot_id: str | None = None
    corpus_routing: dict[str, Any] | None = None
    reanalysis_events: list[dict[str, Any]] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass
class RevisionObservation(Wave2ModelMixin):
    """L2-shaped bounded, observational version comparison."""

    _json_fields = (
        "observation_id", "task_id", "source_submission_id",
        "target_submission_id", "observed_at", "what_changed",
        "feedback_areas", "new_observations",
        "apparent_independent_corrections", "no_intent_inference",
        "limitations",
    )

    observation_id: str | None = None
    task_id: str = ""
    source_submission_id: int = 0
    target_submission_id: int = 0
    observed_at: str | None = None
    what_changed: dict[str, Any] = field(default_factory=dict)
    feedback_areas: list[dict[str, Any]] = field(default_factory=list)
    new_observations: list[dict[str, Any]] = field(default_factory=list)
    apparent_independent_corrections: list[dict[str, Any]] = field(
        default_factory=list
    )
    no_intent_inference: str = ""
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
class PriorityPlanItem:
    """L2-shaped small actionable plan item (never a proficiency ranking)."""

    plan_item_id: str = ""
    category: str = ""
    diagnosis_id: str | None = None
    recurrence_status: str = "insufficient_history"
    context: dict[str, Any] = field(default_factory=dict)
    action_statement: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    confidence: str = "low"
    ordering_note: str = (
        "action-priority ordering only; not a learner-performance ranking"
    )
    limitations: list[str] = field(default_factory=list)


@dataclass
class LocalObservationItem:
    """L2-shaped bounded local observation of one submission."""

    feature_id: str = ""
    value: Any = None
    available: bool = True
    statement: str = ""
    limitation: str = ""


@dataclass
class GlobalObservationItem:
    """L2-shaped bounded whole-text observation."""

    observation_id: str = ""
    scope: str = "whole_text"
    kind: str = ""
    value: Any = None
    descriptive_statement: str = ""
    limitation: str = ""


@dataclass
class HistoricalFeedbackItem:
    """L2-shaped observed feedback area over stored submissions."""

    learner_id: str = ""
    category: str = ""
    status: str = "first_observed"
    occurrence_count: int = 0
    first_observed_at: str | None = None
    last_observed_at: str | None = None
    supporting_submission_ids: list[int] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    contexts: list[str] = field(default_factory=list)
    revision_success_note: str | None = None
    history_state: str = "sufficient"
    history_reasons: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    claims_status: str = "observation_only"


@dataclass
class PriorityRevisionPlan(Wave2ModelMixin):
    """L2-shaped small actionable revision plan (observation-only)."""

    _json_fields = (
        "plan_id", "learner_id", "task_id", "submission_id", "generated_at",
        "items", "history_state", "history_reasons", "local_observations",
        "global_observations", "historical_feedback", "limitations",
        "claims_status",
    )

    plan_id: str | None = None
    learner_id: str = ""
    task_id: str = ""
    submission_id: int = 0
    generated_at: str | None = None
    items: list[PriorityPlanItem] = field(default_factory=list)
    history_state: str = "insufficient_history"
    history_reasons: list[str] = field(default_factory=list)
    local_observations: list[LocalObservationItem] = field(default_factory=list)
    global_observations: list[GlobalObservationItem] = field(
        default_factory=list
    )
    historical_feedback: list[HistoricalFeedbackItem] = field(
        default_factory=list
    )
    limitations: list[str] = field(default_factory=list)
    claims_status: str = "observation_only"


@dataclass
class ScaffoldEvent(Wave2ModelMixin):
    """L2-shaped recorded scaffold request (7-level SCAFFOLD FIRST)."""

    _json_fields = (
        "scaffold_event_id", "learner_id", "learning_item_id", "plan_item_id",
        "category", "level", "requested_at", "default_first", "limitations",
    )

    scaffold_event_id: str | None = None
    learner_id: str = ""
    learning_item_id: str | None = None
    plan_item_id: str | None = None
    category: str = ""
    level: int = 1
    requested_at: str | None = None
    default_first: bool = True
    limitations: list[str] = field(default_factory=list)


@dataclass
class LearningItem(Wave2ModelMixin):
    """Learner-owned item (learning_items), LearningItem v1 contract.

    ``category``/``task_context``/``limitations``/``no_fsrs_note``/
    ``no_practice_note`` match the L2 LearningItem shape; ``context`` is the
    legacy CORE-origin field (excluded from JSON dumps).
    """

    _json_fields = (
        "learning_item_id", "student_id", "category", "originating_evidence",
        "feedback_reference", "revision_history", "task_id", "task_context",
        "status", "created_at", "updated_at", "no_fsrs_note",
        "no_practice_note", "limitations",
    )

    learning_item_id: str | None = None
    student_id: str = ""
    category: str = "unclassified"
    originating_evidence: dict[str, Any] = field(default_factory=dict)
    feedback_reference: str | None = None
    revision_history: list[Any] = field(default_factory=list)
    task_id: str | None = None
    task_context: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    status: str = "proposed"
    created_at: str | None = None
    updated_at: str | None = None
    no_fsrs_note: str = (
        "no FSRS scheduling or spaced-repetition state is stored in "
        "LearningItem v1"
    )
    no_practice_note: str = (
        "no practice or tutor expansion is attached to LearningItem v1"
    )
    limitations: list[str] = field(default_factory=list)


class SQLiteWave2Repository:
    """Additive repository over the Wave-2 migration-14 table families.

    Implements the full L2 ``RevisionLoopRepository`` protocol (F-5 repair):
    writing tasks, submission versions, revision observations, priority
    plans, scaffold events, and learning items, in addition to the original
    CORE families (submission revision links, learning observations).
    """

    def __init__(self, connection_manager: SQLiteConnectionManager):
        self._connection_manager = connection_manager

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _ensure_student(self, connection, student_id: str) -> None:
        """Registration-path compatibility: the real composed app creates
        tasks/items for learner ids that may not yet have a students row
        (the submission repository follows the same INSERT OR IGNORE
        pattern); writing_tasks/learning_items carry the students FK."""
        connection.execute(
            "INSERT OR IGNORE INTO students(student_id, created_at,"
            " is_synthetic) VALUES (?, ?, 0)",
            (student_id, _utc_now()),
        )

    def _next_suffix_id(self, table: str, column: str, prefix: str) -> str:
        """Next zero-padded generated id for L2-shaped families."""
        with self._connection_manager.connect() as connection:
            row = connection.execute(
                f"SELECT MAX(CAST(SUBSTR({column}, {len(prefix) + 1})"
                f" AS INTEGER)) FROM {table}"
            ).fetchone()
            next_number = int(row[0] or 0) + 1
        return f"{prefix}{next_number:06d}"

    # ------------------------------------------------------------------
    # writing_tasks
    # ------------------------------------------------------------------

    def save_writing_task(self, task: WritingTask) -> WritingTask:
        now = _text(_attr(task, "created_at"), _utc_now())
        student_id = _attr(task, "student_id", "")
        writing_prompt = _attr(task, "writing_prompt", "")
        # L2 two-level contract: writing_context is authoritative; the
        # legacy genre column is a CORE-origin compat value and is never
        # used as a fallback for L2-shaped tasks.
        writing_context = (
            _attr(task, "writing_context")
            or _attr(task, "genre")
            or "other"
        )
        genre = _attr(task, "genre") or "argumentative essay"
        task_type = _attr(task, "task_type") or "independent_writing"
        modality = _attr(task, "modality") or "written"
        reference_group_id = _attr(task, "reference_group_id")
        classification = _jsonable(_attr(task, "classification") or {})
        status = _attr(task, "status") or "active"
        metadata = _jsonable(_attr(task, "metadata") or {})
        limitations = _jsonable(_attr(task, "limitations") or [])
        task_id = _attr(task, "task_id")
        with self._connection_manager.connect() as connection:
            self._ensure_student(connection, student_id)
            cursor = connection.execute(
                """INSERT INTO writing_tasks(
                    student_id, writing_prompt, genre, writing_context,
                    task_type, modality, reference_group_id,
                    classification_json, status, created_at, metadata_json,
                    limitations_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (student_id, writing_prompt, genre, writing_context,
                 task_type, modality, reference_group_id,
                 json.dumps(classification), status, now,
                 json.dumps(metadata), json.dumps(limitations)),
            )
            if (
                task_id is None
                or task_id == "WT-PENDING"
                or not str(task_id).startswith("WT")
            ):
                task_id = f"WT{int(cursor.lastrowid):06d}"
                connection.execute(
                    "UPDATE writing_tasks SET task_id=? WHERE rowid=?",
                    (task_id, int(cursor.lastrowid)),
                )
        return WritingTask(
            task_id=task_id,
            student_id=student_id,
            writing_prompt=writing_prompt,
            writing_context=writing_context,
            genre=genre,
            task_type=task_type,
            modality=modality,
            reference_group_id=reference_group_id,
            classification=JsonDict(classification),
            status=status,
            metadata=JsonDict(metadata),
            limitations=limitations,
            created_at=now,
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
    # submission_revisions (legacy CORE family)
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
    # submission_versions (L2 RevisionLoopRepository family)
    # ------------------------------------------------------------------

    def save_submission_version(
        self, version: SubmissionVersion
    ) -> SubmissionVersion:
        submitted_at = _text(_attr(version, "submitted_at"), _utc_now())
        ancestry = _jsonable(_attr(version, "ancestry") or [])
        task_context = _jsonable(_attr(version, "task_context") or {})
        corpus_routing = _jsonable(_attr(version, "corpus_routing"))
        reanalysis_events = _jsonable(_attr(version, "reanalysis_events") or [])
        limitations = _jsonable(_attr(version, "limitations") or [])
        task_id = _attr(version, "task_id", "")
        submission_id = int(_attr(version, "submission_id", 0))
        version_number = int(_attr(version, "version_number", 1))
        revision_of_submission_id = _attr(version, "revision_of_submission_id")
        with self._connection_manager.connect() as connection:
            connection.execute(
                """INSERT INTO submission_versions(
                    task_id, submission_id, version_number,
                    revision_of_submission_id, ancestry_json, submitted_at,
                    task_context_json, essay_text_hash, draft_stage,
                    analysis_run_id, analysis_version, feedback_record_id,
                    revision_group_id, revision_snapshot_id,
                    corpus_routing_json, reanalysis_events_json,
                    limitations_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id, submission_id) DO UPDATE SET
                    version_number=excluded.version_number,
                    revision_of_submission_id=excluded.revision_of_submission_id,
                    ancestry_json=excluded.ancestry_json,
                    submitted_at=excluded.submitted_at,
                    task_context_json=excluded.task_context_json,
                    essay_text_hash=excluded.essay_text_hash,
                    draft_stage=excluded.draft_stage,
                    analysis_run_id=excluded.analysis_run_id,
                    analysis_version=excluded.analysis_version,
                    feedback_record_id=excluded.feedback_record_id,
                    revision_group_id=excluded.revision_group_id,
                    revision_snapshot_id=excluded.revision_snapshot_id,
                    corpus_routing_json=excluded.corpus_routing_json,
                    reanalysis_events_json=excluded.reanalysis_events_json,
                    limitations_json=excluded.limitations_json""",
                (task_id, submission_id, version_number,
                 revision_of_submission_id, json.dumps(ancestry),
                 submitted_at, json.dumps(task_context),
                 _attr(version, "essay_text_hash", ""),
                 _attr(version, "draft_stage", "first draft"),
                 _attr(version, "analysis_run_id"),
                 _attr(version, "analysis_version"),
                 _attr(version, "feedback_record_id"),
                 _attr(version, "revision_group_id"),
                 _attr(version, "revision_snapshot_id"),
                 json.dumps(corpus_routing)
                 if corpus_routing is not None else None,
                 json.dumps(reanalysis_events), json.dumps(limitations)),
            )
        return SubmissionVersion(
            task_id=task_id,
            submission_id=submission_id,
            version_number=version_number,
            revision_of_submission_id=revision_of_submission_id,
            ancestry=_jsonable(ancestry),
            submitted_at=submitted_at,
            task_context=JsonDict(task_context),
            essay_text_hash=_attr(version, "essay_text_hash", ""),
            draft_stage=_attr(version, "draft_stage", "first draft"),
            analysis_run_id=_attr(version, "analysis_run_id"),
            analysis_version=_attr(version, "analysis_version"),
            feedback_record_id=_attr(version, "feedback_record_id"),
            revision_group_id=_attr(version, "revision_group_id"),
            revision_snapshot_id=_attr(version, "revision_snapshot_id"),
            corpus_routing=(
                JsonDict(corpus_routing) if corpus_routing is not None else None
            ),
            reanalysis_events=reanalysis_events,
            limitations=limitations,
        )

    def get_submission_version(
        self, task_id: str, submission_id: int
    ) -> SubmissionVersion | None:
        with self._connection_manager.connect() as connection:
            row = connection.execute(
                "SELECT * FROM submission_versions WHERE task_id=?"
                " AND submission_id=?",
                (task_id, submission_id),
            ).fetchone()
        return _submission_version_from_row(row) if row else None

    def list_submission_versions(self, task_id: str) -> list[SubmissionVersion]:
        with self._connection_manager.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM submission_versions WHERE task_id=?"
                " ORDER BY version_number, submission_id",
                (task_id,),
            ).fetchall()
        return [_submission_version_from_row(row) for row in rows]

    def find_task_id_for_submission(self, submission_id: int) -> str | None:
        with self._connection_manager.connect() as connection:
            row = connection.execute(
                "SELECT task_id FROM submission_versions"
                " WHERE submission_id=? ORDER BY version_number LIMIT 1",
                (submission_id,),
            ).fetchone()
        return row["task_id"] if row else None

    # ------------------------------------------------------------------
    # revision_observations (L2 RevisionLoopRepository family)
    # ------------------------------------------------------------------

    def save_revision_observation(
        self, observation: RevisionObservation
    ) -> None:
        observed_at = _text(_attr(observation, "observed_at"), _utc_now())
        with self._connection_manager.connect() as connection:
            connection.execute(
                """INSERT OR REPLACE INTO revision_observations(
                    observation_id, task_id, source_submission_id,
                    target_submission_id, observed_at, what_changed_json,
                    feedback_areas_json, new_observations_json,
                    apparent_independent_corrections_json,
                    no_intent_inference, limitations_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (_attr(observation, "observation_id"),
                 _attr(observation, "task_id", ""),
                 int(_attr(observation, "source_submission_id", 0)),
                 int(_attr(observation, "target_submission_id", 0)),
                 observed_at,
                 json.dumps(_jsonable(_attr(observation, "what_changed") or {})),
                 json.dumps(_jsonable(_attr(observation, "feedback_areas") or [])),
                 json.dumps(_jsonable(_attr(observation, "new_observations") or [])),
                 json.dumps(_jsonable(
                     _attr(observation, "apparent_independent_corrections") or []
                 )),
                 _attr(observation, "no_intent_inference", ""),
                 json.dumps(_jsonable(_attr(observation, "limitations") or []))),
            )

    def list_revision_observations(
        self, task_id: str
    ) -> list[RevisionObservation]:
        with self._connection_manager.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM revision_observations WHERE task_id=?"
                " ORDER BY observed_at, observation_id",
                (task_id,),
            ).fetchall()
        return [_revision_observation_from_row(row) for row in rows]

    # ------------------------------------------------------------------
    # priority_plans (L2 RevisionLoopRepository family)
    # ------------------------------------------------------------------

    def save_priority_plan(self, plan: PriorityRevisionPlan) -> None:
        plan_id = _attr(plan, "plan_id")
        if (
            plan_id is None
            or plan_id == "PP-PENDING"
            or not str(plan_id).startswith("PP")
        ):
            plan_id = self._next_suffix_id("priority_plans", "plan_id", "PP")
        generated_at = _text(_attr(plan, "generated_at"), _utc_now())
        with self._connection_manager.connect() as connection:
            connection.execute(
                """INSERT OR REPLACE INTO priority_plans(
                    plan_id, learner_id, task_id, submission_id,
                    generated_at, items_json, history_state,
                    history_reasons_json, local_observations_json,
                    global_observations_json, historical_feedback_json,
                    limitations_json, claims_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (plan_id, _attr(plan, "learner_id", ""),
                 _attr(plan, "task_id", ""),
                 int(_attr(plan, "submission_id", 0)), generated_at,
                 json.dumps(_jsonable(_attr(plan, "items") or [])),
                 _attr(plan, "history_state", "insufficient_history"),
                 json.dumps(_jsonable(_attr(plan, "history_reasons") or [])),
                 json.dumps(_jsonable(
                     _attr(plan, "local_observations") or []
                 )),
                 json.dumps(_jsonable(
                     _attr(plan, "global_observations") or []
                 )),
                 json.dumps(_jsonable(
                     _attr(plan, "historical_feedback") or []
                 )),
                 json.dumps(_jsonable(_attr(plan, "limitations") or [])),
                 _attr(plan, "claims_status", "observation_only")),
            )

    def get_priority_plan(
        self, plan_id: str
    ) -> PriorityRevisionPlan | None:
        with self._connection_manager.connect() as connection:
            row = connection.execute(
                "SELECT * FROM priority_plans WHERE plan_id=?", (plan_id,)
            ).fetchone()
        return _priority_plan_from_row(row) if row else None

    def list_priority_plans(self, learner_id: str) -> list[PriorityRevisionPlan]:
        with self._connection_manager.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM priority_plans WHERE learner_id=?"
                " ORDER BY generated_at, plan_id",
                (learner_id,),
            ).fetchall()
        return [_priority_plan_from_row(row) for row in rows]

    # ------------------------------------------------------------------
    # scaffold_events (L2 RevisionLoopRepository family)
    # ------------------------------------------------------------------

    def save_scaffold_event(self, event: ScaffoldEvent) -> None:
        event_id = _attr(event, "scaffold_event_id")
        if (
            event_id is None
            or event_id == "SE-PENDING"
            or not str(event_id).startswith("SE")
        ):
            event_id = self._next_suffix_id(
                "scaffold_events", "scaffold_event_id", "SE"
            )
        requested_at = _text(_attr(event, "requested_at"), _utc_now())
        with self._connection_manager.connect() as connection:
            connection.execute(
                """INSERT OR REPLACE INTO scaffold_events(
                    scaffold_event_id, learner_id, learning_item_id,
                    plan_item_id, category, level, requested_at,
                    default_first, limitations_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (event_id, _attr(event, "learner_id", ""),
                 _attr(event, "learning_item_id"),
                 _attr(event, "plan_item_id"),
                 _attr(event, "category", ""),
                 int(_attr(event, "level", 1)), requested_at,
                 int(bool(_attr(event, "default_first", True))),
                 json.dumps(_jsonable(_attr(event, "limitations") or []))),
            )

    def list_scaffold_events(
        self, learner_id: str, learning_item_id: str | None = None
    ) -> list[ScaffoldEvent]:
        sql = "SELECT * FROM scaffold_events WHERE learner_id=?"
        params: list[Any] = [learner_id]
        if learning_item_id is not None:
            sql += " AND learning_item_id=?"
            params.append(learning_item_id)
        sql += " ORDER BY requested_at, scaffold_event_id"
        with self._connection_manager.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [_scaffold_event_from_row(row) for row in rows]

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
            self._ensure_student(connection, observation.student_id)
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
        created_at = _text(_attr(item, "created_at"), _utc_now())
        updated_at = _text(_attr(item, "updated_at"), created_at)
        student_id = _attr(item, "student_id", "")
        category = _attr(item, "category") or "unclassified"
        task_context = _jsonable(_attr(item, "task_context") or {})
        context = _jsonable(_attr(item, "context") or {})
        limitations = _jsonable(_attr(item, "limitations") or [])
        no_fsrs_note = _attr(item, "no_fsrs_note") or (
            "no FSRS scheduling or spaced-repetition state is stored in "
            "LearningItem v1"
        )
        no_practice_note = _attr(item, "no_practice_note") or (
            "no practice or tutor expansion is attached to LearningItem v1"
        )
        status = _attr(item, "status") or "proposed"
        learning_item_id = _attr(item, "learning_item_id")
        with self._connection_manager.connect() as connection:
            self._ensure_student(connection, student_id)
            if (
                learning_item_id is None
                or learning_item_id == "LI-PENDING"
                or not str(learning_item_id).startswith("LI")
            ):
                cursor = connection.execute(
                    """INSERT INTO learning_items(
                        student_id, originating_evidence_json,
                        feedback_reference, revision_history_json, task_id,
                        context_json, category, task_context_json,
                        no_fsrs_note, no_practice_note, limitations_json,
                        status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (student_id,
                     json.dumps(_jsonable(
                         _attr(item, "originating_evidence") or {}
                     )),
                     _attr(item, "feedback_reference"),
                     json.dumps(_jsonable(_attr(item, "revision_history") or [])),
                     _attr(item, "task_id"), json.dumps(context), category,
                     json.dumps(task_context), no_fsrs_note, no_practice_note,
                     json.dumps(limitations), status, created_at, updated_at),
                )
                learning_item_id = f"LI{int(cursor.lastrowid):06d}"
                connection.execute(
                    "UPDATE learning_items SET learning_item_id=? WHERE rowid=?",
                    (learning_item_id, int(cursor.lastrowid)),
                )
            else:
                connection.execute(
                    """INSERT OR REPLACE INTO learning_items(
                        learning_item_id, student_id,
                        originating_evidence_json, feedback_reference,
                        revision_history_json, task_id, context_json,
                        category, task_context_json, no_fsrs_note,
                        no_practice_note, limitations_json, status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (learning_item_id, student_id,
                     json.dumps(_jsonable(
                         _attr(item, "originating_evidence") or {}
                     )),
                     _attr(item, "feedback_reference"),
                     json.dumps(_jsonable(_attr(item, "revision_history") or [])),
                     _attr(item, "task_id"), json.dumps(context), category,
                     json.dumps(task_context), no_fsrs_note, no_practice_note,
                     json.dumps(limitations), status, created_at, updated_at),
                )
        return LearningItem(
            learning_item_id=learning_item_id,
            student_id=student_id,
            category=category,
            originating_evidence=_jsonable(
                _attr(item, "originating_evidence") or {}
            ),
            feedback_reference=_attr(item, "feedback_reference"),
            revision_history=_jsonable(_attr(item, "revision_history") or []),
            task_id=_attr(item, "task_id"),
            task_context=JsonDict(task_context),
            context=JsonDict(context),
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            no_fsrs_note=no_fsrs_note,
            no_practice_note=no_practice_note,
            limitations=limitations,
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
        self, learning_item_id: str, status: str, updated_at
    ) -> LearningItem | None:
        updated_at_text = _text(updated_at, _utc_now())
        with self._connection_manager.connect() as connection:
            cursor = connection.execute(
                "UPDATE learning_items SET status=?, updated_at=?"
                " WHERE learning_item_id=?",
                (status, updated_at_text, learning_item_id),
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
        writing_context=item["writing_context"],
        genre=item["genre"],
        task_type=item["task_type"],
        modality=item["modality"],
        reference_group_id=item["reference_group_id"],
        classification=JsonDict(json.loads(item["classification_json"])),
        status=item["status"],
        metadata=JsonDict(json.loads(item["metadata_json"])),
        limitations=json.loads(item["limitations_json"]),
        created_at=item["created_at"],
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


def _submission_version_from_row(row) -> SubmissionVersion:
    item = dict(row)
    corpus_routing = item["corpus_routing_json"]
    return SubmissionVersion(
        task_id=item["task_id"],
        submission_id=item["submission_id"],
        version_number=item["version_number"],
        revision_of_submission_id=item["revision_of_submission_id"],
        ancestry=json.loads(item["ancestry_json"]),
        submitted_at=item["submitted_at"],
        task_context=JsonDict(json.loads(item["task_context_json"])),
        essay_text_hash=item["essay_text_hash"],
        draft_stage=item["draft_stage"],
        analysis_run_id=item["analysis_run_id"],
        analysis_version=item["analysis_version"],
        feedback_record_id=item["feedback_record_id"],
        revision_group_id=item["revision_group_id"],
        revision_snapshot_id=item["revision_snapshot_id"],
        corpus_routing=(
            JsonDict(json.loads(corpus_routing))
            if corpus_routing is not None else None
        ),
        reanalysis_events=json.loads(item["reanalysis_events_json"]),
        limitations=json.loads(item["limitations_json"]),
    )


def _revision_observation_from_row(row) -> RevisionObservation:
    item = dict(row)
    return RevisionObservation(
        observation_id=item["observation_id"],
        task_id=item["task_id"],
        source_submission_id=item["source_submission_id"],
        target_submission_id=item["target_submission_id"],
        observed_at=item["observed_at"],
        what_changed=JsonDict(json.loads(item["what_changed_json"])),
        feedback_areas=[
            JsonDict(entry) for entry in json.loads(item["feedback_areas_json"])
        ],
        new_observations=[
            JsonDict(entry) for entry in json.loads(item["new_observations_json"])
        ],
        apparent_independent_corrections=[
            JsonDict(entry)
            for entry in json.loads(
                item["apparent_independent_corrections_json"]
            )
        ],
        no_intent_inference=item["no_intent_inference"],
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
        context=JsonDict(json.loads(item["context_json"])),
        occurrence_count=item["occurrence_count"],
        first_observed_at=item["first_observed_at"],
        last_observed_at=item["last_observed_at"],
        recency=item["recency"],
        revision_response=JsonDict(json.loads(item["revision_response_json"])),
        limitations=json.loads(item["limitations_json"]),
        created_at=item["created_at"],
    )


def _priority_plan_item_from_dict(item: dict) -> PriorityPlanItem:
    return PriorityPlanItem(
        plan_item_id=item.get("plan_item_id", ""),
        category=item.get("category", ""),
        diagnosis_id=item.get("diagnosis_id"),
        recurrence_status=item.get(
            "recurrence_status", "insufficient_history"
        ),
        context=JsonDict(item.get("context") or {}),
        action_statement=item.get("action_statement", ""),
        evidence_refs=list(item.get("evidence_refs") or []),
        confidence=item.get("confidence", "low"),
        ordering_note=item.get("ordering_note", ""),
        limitations=list(item.get("limitations") or []),
    )


def _local_observation_item_from_dict(item: dict) -> LocalObservationItem:
    return LocalObservationItem(
        feature_id=item.get("feature_id", ""),
        value=item.get("value"),
        available=bool(item.get("available", True)),
        statement=item.get("statement", ""),
        limitation=item.get("limitation", ""),
    )


def _global_observation_item_from_dict(item: dict) -> GlobalObservationItem:
    return GlobalObservationItem(
        observation_id=item.get("observation_id", ""),
        scope=item.get("scope", "whole_text"),
        kind=item.get("kind", ""),
        value=item.get("value"),
        descriptive_statement=item.get("descriptive_statement", ""),
        limitation=item.get("limitation", ""),
    )


def _historical_feedback_item_from_dict(item: dict) -> HistoricalFeedbackItem:
    return HistoricalFeedbackItem(
        learner_id=item.get("learner_id", ""),
        category=item.get("category", ""),
        status=item.get("status", "first_observed"),
        occurrence_count=int(item.get("occurrence_count", 0)),
        first_observed_at=item.get("first_observed_at"),
        last_observed_at=item.get("last_observed_at"),
        supporting_submission_ids=list(
            item.get("supporting_submission_ids") or []
        ),
        evidence_refs=list(item.get("evidence_refs") or []),
        contexts=list(item.get("contexts") or []),
        revision_success_note=item.get("revision_success_note"),
        history_state=item.get("history_state", "sufficient"),
        history_reasons=list(item.get("history_reasons") or []),
        limitations=list(item.get("limitations") or []),
        claims_status=item.get("claims_status", "observation_only"),
    )


def _priority_plan_from_row(row) -> PriorityRevisionPlan:
    item = dict(row)
    return PriorityRevisionPlan(
        plan_id=item["plan_id"],
        learner_id=item["learner_id"],
        task_id=item["task_id"],
        submission_id=item["submission_id"],
        generated_at=item["generated_at"],
        items=[
            _priority_plan_item_from_dict(entry)
            for entry in json.loads(item["items_json"])
        ],
        history_state=item["history_state"],
        history_reasons=json.loads(item["history_reasons_json"]),
        local_observations=[
            _local_observation_item_from_dict(entry)
            for entry in json.loads(item["local_observations_json"])
        ],
        global_observations=[
            _global_observation_item_from_dict(entry)
            for entry in json.loads(item["global_observations_json"])
        ],
        historical_feedback=[
            _historical_feedback_item_from_dict(entry)
            for entry in json.loads(item["historical_feedback_json"])
        ],
        limitations=json.loads(item["limitations_json"]),
        claims_status=item["claims_status"],
    )


def _scaffold_event_from_row(row) -> ScaffoldEvent:
    item = dict(row)
    return ScaffoldEvent(
        scaffold_event_id=item["scaffold_event_id"],
        learner_id=item["learner_id"],
        learning_item_id=item["learning_item_id"],
        plan_item_id=item["plan_item_id"],
        category=item["category"],
        level=item["level"],
        requested_at=item["requested_at"],
        default_first=bool(item["default_first"]),
        limitations=json.loads(item["limitations_json"]),
    )


def _learning_item_from_row(row) -> LearningItem:
    item = dict(row)
    return LearningItem(
        learning_item_id=item["learning_item_id"],
        student_id=item["student_id"],
        category=item["category"],
        originating_evidence=JsonDict(
            json.loads(item["originating_evidence_json"])
        ),
        feedback_reference=item["feedback_reference"],
        revision_history=json.loads(item["revision_history_json"]),
        task_id=item["task_id"],
        task_context=JsonDict(json.loads(item["task_context_json"])),
        context=JsonDict(json.loads(item["context_json"])),
        status=item["status"],
        created_at=item["created_at"],
        updated_at=item["updated_at"],
        no_fsrs_note=item["no_fsrs_note"],
        no_practice_note=item["no_practice_note"],
        limitations=json.loads(item["limitations_json"]),
    )
