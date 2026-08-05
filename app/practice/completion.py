"""Practice-cycle completion service (v0.9.7-B WU5).

One explicit student action persists the idempotent ACTIVE -> COMPLETED
transition for a learner-owned Practice target.

Frozen semantics (docs/development/V0.9.7_B_WU5_PROTOCOL.md):

- Eligibility is derived from persisted records only: at least one
  SUBMITTED attempt belonging to the learner on an exercise of the target.
- Evaluation availability is never a completion or mastery gate.
- Completion is activity completion, not learning-outcome certification.
- Repeated or concurrent completion is idempotent: one completed target,
  no duplicate writes, no status conflict.
- Unsupported statuses return a controlled error; no silent reactivation.
"""

from __future__ import annotations

import json
from typing import Any

from app.models.schemas import utc_now
from app.practice.ports import PracticeReadPort, PracticeWritePort
from app.practice.schemas import AttemptStatus, PracticeTargetStatus


class PracticeCompletionError(Exception):
    """Controlled completion failure with a stable machine-readable kind.

    Kinds: target_not_found | cross_student | malformed_priority |
    no_eligible_attempt | unsupported_status.
    """

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind
        self.message = message


class PracticeTargetCompletionService:
    """Own completion lookup, ownership, eligibility, transition, and
    idempotency; business rules never live in the router."""

    def __init__(
        self,
        practice_reader: PracticeReadPort,
        practice_writer: PracticeWritePort,
    ):
        self._practice_reader = practice_reader
        self._practice_writer = practice_writer

    def complete_target(
        self, *, student_id: str, practice_target_id: str
    ) -> dict[str, Any]:
        """Mark one learner-owned target COMPLETED and return the persisted
        target. Idempotent: a completed target returns unchanged."""
        try:
            target = self._practice_reader.get_practice_target(practice_target_id)
        except json.JSONDecodeError:
            raise PracticeCompletionError(
                "malformed_priority", "Stored target record is malformed."
            ) from None
        if target is None:
            raise PracticeCompletionError(
                "target_not_found", "Practice target not found."
            )
        if target.get("student_id") != student_id:
            raise PracticeCompletionError(
                "cross_student",
                "Practice target does not belong to the requested learner.",
            )
        status = target.get("status")
        if status == PracticeTargetStatus.COMPLETED.value:
            return target
        if status != PracticeTargetStatus.ACTIVE.value:
            raise PracticeCompletionError(
                "unsupported_status",
                f"Practice target cannot be completed from status '{status}'.",
            )
        if not self._has_eligible_attempt(student_id, practice_target_id):
            raise PracticeCompletionError(
                "no_eligible_attempt",
                "Practice target requires a persisted learner attempt.",
            )
        completed = self._practice_writer.update_practice_target_status(
            practice_target_id,
            PracticeTargetStatus.COMPLETED.value,
            utc_now().isoformat(),
        )
        if completed is None:
            raise PracticeCompletionError(
                "target_not_found", "Practice target not found."
            )
        return completed

    def _has_eligible_attempt(self, student_id: str, practice_target_id: str) -> bool:
        """One persisted SUBMITTED attempt owned by the learner on an
        exercise belonging to the target. Session state is never proof."""
        try:
            exercises = self._practice_reader.list_exercise_instances(
                practice_target_id=practice_target_id
            )
        except json.JSONDecodeError:
            return False
        for exercise in exercises:
            try:
                attempts = self._practice_reader.list_exercise_attempts(
                    exercise.get("exercise_id", "")
                )
            except json.JSONDecodeError:
                continue
            for attempt in attempts:
                if (
                    attempt.get("student_id") == student_id
                    and attempt.get("status") == AttemptStatus.SUBMITTED.value
                ):
                    return True
        return False
