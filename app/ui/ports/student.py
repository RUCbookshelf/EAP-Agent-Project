"""Student feature API Ports (v0.9.5-D).

Each Protocol declares only the WritingFeedbackApiClient methods its owning
feature calls. Method names, argument names/order, and defaults mirror the
concrete client; return types are conservative frontend-safe JSON types.
"""

from __future__ import annotations

from typing import Any, Protocol


class StudentHomeApiPort(Protocol):
    def get_journey(self, student_id: str) -> dict[str, Any]: ...

    def get_practice_targets(self, student_id: str) -> list[dict[str, Any]]: ...


class StudentWritingApiPort(Protocol):
    def get_student_revision_candidates(self, student_id: str) -> dict[str, Any]: ...

    def get_submission(self, submission_id: int) -> dict[str, Any]: ...

    def submit(self, submission: dict[str, Any]) -> dict[str, Any]: ...


class StudentFeedbackApiPort(Protocol):
    def get_student_revision_candidates(self, student_id: str) -> dict[str, Any]: ...


class StudentPracticeApiPort(Protocol):
    def complete_practice_target(
        self, practice_target_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]: ...

    def create_practice_target(
        self, payload: dict[str, Any]
    ) -> dict[str, Any]: ...

    def create_exercise(
        self, practice_target_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]: ...

    def get_exercise_attempts(self, exercise_id: str) -> list[dict[str, Any]]: ...

    def get_exercise_instances(
        self, practice_target_id: str
    ) -> list[dict[str, Any]]: ...

    def get_practice_targets(self, student_id: str) -> list[dict[str, Any]]: ...

    def get_practice_target_context(
        self, student_id: str, practice_target_id: str
    ) -> dict[str, Any]: ...

    def get_practice_target_evaluations(
        self, student_id: str, practice_target_id: str
    ) -> list[dict[str, Any]]: ...

    def submit_exercise_attempt(
        self, exercise_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]: ...


class StudentRevisionApiPort(Protocol):
    def get_practice_targets(self, student_id: str) -> list[dict[str, Any]]: ...

    def get_student_revision_candidates(self, student_id: str) -> dict[str, Any]: ...

    def get_submission(self, submission_id: int) -> dict[str, Any]: ...

    def submit_linked_revision(self, submission: dict[str, Any]) -> dict[str, Any]: ...


class StudentJourneyApiPort(Protocol):
    def get_journey(self, student_id: str) -> dict[str, Any]: ...
