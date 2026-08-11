"""Locally-defined repository protocol for the Wave-2 revision loop.

Goal PDW2-C-L2-REVISION-SCAFFOLD: the L2 branch does not contain the CORE
Wave-2 persistence (``app.infrastructure.sqlite.repositories.wave2`` or the
migration-14 DDL; those land at integration). This module therefore defines
the persistence boundary LOCALLY with the same semantics as the CORE
contract (writing tasks; submission revisions with ancestry/timestamps/
task-context/analysis/feedback links; learning observations/items) and ships
an in-memory implementation. A self-contained TEST-ONLY SQLite
implementation lives in ``sqlite_repository.py``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from app.l2.wave2.models import (
    LearningItem,
    LearningItemStatus,
    PriorityRevisionPlan,
    RevisionObservation,
    ScaffoldEvent,
    SubmissionVersion,
    WritingTask,
)


@runtime_checkable
class RevisionLoopRepository(Protocol):
    """Persistence boundary for the revision loop + personalized bridge."""

    def save_writing_task(self, task: WritingTask) -> WritingTask: ...

    def get_writing_task(self, task_id: str) -> WritingTask | None: ...

    def list_writing_tasks(self, student_id: str) -> list[WritingTask]: ...

    def save_submission_version(self, version: SubmissionVersion) -> SubmissionVersion: ...

    def get_submission_version(
        self, task_id: str, submission_id: int,
    ) -> SubmissionVersion | None: ...

    def list_submission_versions(self, task_id: str) -> list[SubmissionVersion]: ...

    def find_task_id_for_submission(self, submission_id: int) -> str | None: ...

    def save_revision_observation(self, observation: RevisionObservation) -> None: ...

    def list_revision_observations(self, task_id: str) -> list[RevisionObservation]: ...

    def save_priority_plan(self, plan: PriorityRevisionPlan) -> None: ...

    def get_priority_plan(self, plan_id: str) -> PriorityRevisionPlan | None: ...

    def list_priority_plans(self, learner_id: str) -> list[PriorityRevisionPlan]: ...

    def save_scaffold_event(self, event: ScaffoldEvent) -> None: ...

    def list_scaffold_events(
        self, learner_id: str, learning_item_id: str | None = None,
    ) -> list[ScaffoldEvent]: ...

    def save_learning_item(self, item: LearningItem) -> LearningItem: ...

    def get_learning_item(self, learning_item_id: str) -> LearningItem | None: ...

    def list_learning_items(
        self, student_id: str, status: LearningItemStatus | None = None,
    ) -> list[LearningItem]: ...

    def update_learning_item_status(
        self, learning_item_id: str, status: LearningItemStatus,
        updated_at: datetime,
    ) -> LearningItem | None: ...


class InMemoryRevisionLoopRepository:
    """In-memory implementation (tests and branch-local default)."""

    def __init__(self) -> None:
        self._tasks: dict[str, WritingTask] = {}
        self._versions: dict[tuple[str, int], SubmissionVersion] = {}
        self._observations: dict[str, RevisionObservation] = {}
        self._plans: dict[str, PriorityRevisionPlan] = {}
        self._scaffold_events: list[ScaffoldEvent] = []
        self._learning_items: dict[str, LearningItem] = {}
        self._counters: dict[str, int] = {}

    def _next_id(self, prefix: str) -> str:
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return f"{prefix}{self._counters[prefix]:06d}"

    def save_writing_task(self, task: WritingTask) -> WritingTask:
        if task.task_id == "WT-PENDING" or not task.task_id.startswith("WT"):
            task = task.model_copy(update={"task_id": self._next_id("WT")})
        self._tasks[task.task_id] = task
        return task

    def get_writing_task(self, task_id: str) -> WritingTask | None:
        return self._tasks.get(task_id)

    def list_writing_tasks(self, student_id: str) -> list[WritingTask]:
        return [
            task for task in self._tasks.values()
            if task.student_id == student_id
        ]

    def save_submission_version(self, version: SubmissionVersion) -> SubmissionVersion:
        self._versions[(version.task_id, version.submission_id)] = version
        return version

    def get_submission_version(
        self, task_id: str, submission_id: int,
    ) -> SubmissionVersion | None:
        return self._versions.get((task_id, submission_id))

    def list_submission_versions(self, task_id: str) -> list[SubmissionVersion]:
        versions = [
            version
            for (version_task_id, _), version in self._versions.items()
            if version_task_id == task_id
        ]
        return sorted(versions, key=lambda version: version.version_number)

    def find_task_id_for_submission(self, submission_id: int) -> str | None:
        for (task_id, stored_submission_id), _ in self._versions.items():
            if stored_submission_id == submission_id:
                return task_id
        return None

    def save_revision_observation(self, observation: RevisionObservation) -> None:
        self._observations[observation.observation_id] = observation

    def list_revision_observations(self, task_id: str) -> list[RevisionObservation]:
        return [
            observation for observation in self._observations.values()
            if observation.task_id == task_id
        ]

    def save_priority_plan(self, plan: PriorityRevisionPlan) -> None:
        if plan.plan_id == "PP-PENDING" or not plan.plan_id.startswith("PP"):
            plan = plan.model_copy(update={"plan_id": self._next_id("PP")})
        self._plans[plan.plan_id] = plan

    def get_priority_plan(self, plan_id: str) -> PriorityRevisionPlan | None:
        return self._plans.get(plan_id)

    def list_priority_plans(self, learner_id: str) -> list[PriorityRevisionPlan]:
        return [
            plan for plan in self._plans.values()
            if plan.learner_id == learner_id
        ]

    def save_scaffold_event(self, event: ScaffoldEvent) -> None:
        if event.scaffold_event_id == "SE-PENDING" or not event.scaffold_event_id.startswith("SE"):
            event = event.model_copy(
                update={"scaffold_event_id": self._next_id("SE")},
            )
        self._scaffold_events.append(event)

    def list_scaffold_events(
        self, learner_id: str, learning_item_id: str | None = None,
    ) -> list[ScaffoldEvent]:
        events = [
            event for event in self._scaffold_events
            if event.learner_id == learner_id
            and (learning_item_id is None or event.learning_item_id == learning_item_id)
        ]
        return sorted(events, key=lambda event: event.requested_at)

    def save_learning_item(self, item: LearningItem) -> LearningItem:
        if item.learning_item_id == "LI-PENDING" or not item.learning_item_id.startswith("LI"):
            item = item.model_copy(update={"learning_item_id": self._next_id("LI")})
        self._learning_items[item.learning_item_id] = item
        return item

    def get_learning_item(self, learning_item_id: str) -> LearningItem | None:
        return self._learning_items.get(learning_item_id)

    def list_learning_items(
        self, student_id: str, status: LearningItemStatus | None = None,
    ) -> list[LearningItem]:
        items = [
            item for item in self._learning_items.values()
            if item.student_id == student_id
            and (status is None or item.status == status)
        ]
        return sorted(items, key=lambda item: item.updated_at)

    def update_learning_item_status(
        self, learning_item_id: str, status: LearningItemStatus,
        updated_at: datetime,
    ) -> LearningItem | None:
        item = self._learning_items.get(learning_item_id)
        if item is None:
            return None
        updated = item.model_copy(update={"status": status, "updated_at": updated_at})
        self._learning_items[learning_item_id] = updated
        return updated


__all__ = ["InMemoryRevisionLoopRepository", "RevisionLoopRepository"]
