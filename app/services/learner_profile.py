from __future__ import annotations

from datetime import date
from typing import Any, Protocol, runtime_checkable

from app.core import LearnerProfileSnapshot

from .progress import ProgressService


@runtime_checkable
class LearnerProfileReadPort(Protocol):
    def get_latest_learner_profile(self, student_id: str) -> dict[str, Any] | None: ...
    def list_learner_profile_snapshots(self, student_id: str) -> list[dict[str, Any]]: ...


class LearnerProfileService:
    def __init__(
        self,
        repository: LearnerProfileReadPort,
        progress_service: ProgressService,
    ) -> None:
        self.repository = repository
        self.progress = progress_service

    def recalculate(self, student_id: str, **filters) -> LearnerProfileSnapshot:
        return self.progress.create_snapshot(student_id, **filters)

    def latest_or_recalculate(self, student_id: str) -> LearnerProfileSnapshot:
        latest = self.repository.get_latest_learner_profile(student_id)
        if latest:
            snapshot = LearnerProfileSnapshot.model_validate(latest)
            if snapshot.profile_version == "learner-profile-v0.7.0":
                return snapshot
        return self.recalculate(student_id)

    def history(self, student_id: str) -> list[dict]:
        return self.repository.list_learner_profile_snapshots(student_id)
