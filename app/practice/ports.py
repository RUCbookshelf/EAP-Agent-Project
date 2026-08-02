"""Consumer-owned Practice persistence contracts (v0.9.5-F6D).

Exactly the Repository methods directly called by the active Practice Router
at HEAD. No Journey-only, Research-only, test-only, or deferred writer
capabilities are exposed.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PracticeSubmissionReadPort(Protocol):
    """Submission-owned bundle read used by the Practice Router."""

    def get_submission_bundle(self, essay_id: int) -> dict[str, Any] | None: ...


@runtime_checkable
class PracticeReadPort(Protocol):
    """Practice-owned read contract used by the Practice Router."""

    def list_practice_targets(self, student_id: str) -> list[dict]: ...

    def get_practice_target(self, pid: str) -> dict | None: ...

    def list_exercise_instances(self, practice_target_id=None, student_id=None) -> list[dict]: ...

    def get_exercise_instance(self, eid: str) -> dict | None: ...

    def list_exercise_attempts(self, exercise_id: str) -> list[dict]: ...

    def list_feedback_engagement_traces(self, student_id: str) -> list[dict]: ...

    def list_transfer_evidence_candidates(self, student_id: str) -> list[dict]: ...


@runtime_checkable
class PracticeWritePort(Protocol):
    """Practice-owned write contract used by the Practice Router."""

    def save_practice_target(self, target: dict) -> dict: ...

    def save_exercise_instance(self, instance: dict) -> dict: ...

    def save_exercise_attempt(self, attempt: dict) -> dict: ...

    def save_practice_evaluation(self, evaluation: dict) -> dict: ...
