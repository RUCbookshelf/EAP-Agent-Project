"""Learner-owned Practice evaluation read path (v0.9.7-B WU5).

Read-only view of the persisted rule-based evaluations for one Practice
target. Availability is derived from persisted attempt/evaluation
associations only:

- the target must exist and belong to the learner;
- an evaluation is returned only when its attempt exists, the attempt
  belongs to the learner, and the attempt belongs to an exercise of the
  target;
- malformed or unrelated evaluation rows are treated as a controlled
  unavailable state (skipped, never a page crash);
- no evaluation is fabricated and no evaluation algorithm is changed.
"""

from __future__ import annotations

import json
from typing import Any

from app.practice.mapping import PriorityMappingError
from app.practice.ports import PracticeReadPort


class PracticeEvaluationReadService:
    """Read persisted evaluations for one learner-owned target."""

    def __init__(self, practice_reader: PracticeReadPort):
        self._practice_reader = practice_reader

    def list_attempt_evaluations(
        self, *, student_id: str, practice_target_id: str
    ) -> list[dict[str, Any]]:
        """Return the valid evaluations attached to the learner's attempts
        on exercises belonging to the target.

        Raises PriorityMappingError for not-found (404) and cross-student
        (403) conditions; a malformed stored target or a malformed
        evaluation row degrades to a controlled unavailable result.
        """
        try:
            target = self._practice_reader.get_practice_target(practice_target_id)
        except json.JSONDecodeError:
            raise PriorityMappingError(
                "malformed_priority", "Stored target record is malformed."
            ) from None
        if target is None:
            raise PriorityMappingError("source_not_found", "Practice target not found.")
        if target.get("student_id") != student_id:
            raise PriorityMappingError(
                "cross_student",
                "Practice target does not belong to the requested learner.",
            )
        evaluations: list[dict[str, Any]] = []
        try:
            exercises = self._practice_reader.list_exercise_instances(
                practice_target_id=practice_target_id
            )
        except json.JSONDecodeError:
            return []
        for exercise in exercises:
            exercise_id = exercise.get("exercise_id", "")
            try:
                attempts = self._practice_reader.list_exercise_attempts(exercise_id)
            except json.JSONDecodeError:
                continue
            for attempt in attempts:
                if attempt.get("student_id") != student_id:
                    continue
                try:
                    rows = self._practice_reader.list_practice_evaluations(
                        attempt_id=attempt.get("attempt_id", "")
                    )
                except json.JSONDecodeError:
                    # Malformed evaluation row: controlled unavailable for
                    # this attempt; other attempts stay readable.
                    continue
                for evaluation in rows:
                    if evaluation.get("practice_target_id") == practice_target_id:
                        evaluations.append(evaluation)
        return evaluations
