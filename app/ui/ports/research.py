"""Research feature API Ports (v0.9.5-D).

Each Protocol declares only the WritingFeedbackApiClient methods its owning
feature calls. Method names, argument names/order, and defaults mirror the
concrete client; return types are conservative frontend-safe JSON types.
"""

from __future__ import annotations

from typing import Any, Protocol


class ResearchOverviewApiPort(Protocol):
    def health(self) -> dict[str, Any]: ...

    def research_data_quality(self) -> dict[str, Any]: ...


class ResearchEvidenceApiPort(Protocol):
    def get_analyses(self, submission_id: int) -> dict[str, Any]: ...

    def get_diagnostic_audit(self, submission_id: int) -> dict[str, Any]: ...

    def get_submission(self, submission_id: int) -> dict[str, Any]: ...


class ResearchCalfApiPort(Protocol):
    """CALF feature contract.

    The CALF Measures page reads its data from the session submission result
    and makes no API client calls; the Port is intentionally empty.
    """


class ResearchLearningProcessApiPort(Protocol):
    def get_engagement_traces(self, student_id: str) -> list[dict[str, Any]]: ...

    def get_journey(self, student_id: str) -> dict[str, Any]: ...

    def get_practice_targets(self, student_id: str) -> list[dict[str, Any]]: ...

    def get_transfer_evidence(self, student_id: str) -> list[dict[str, Any]]: ...


class ResearchDataApiPort(Protocol):
    def create_dataset_split(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def create_human_review(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def get_pii_candidates(self, submission_id: int) -> list[dict[str, Any]]: ...

    def research_data_quality(self) -> dict[str, Any]: ...

    def research_export_history(self) -> list[dict[str, Any]]: ...

    def research_export_preview(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def research_export_run(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class ResearchSystemAuditApiPort(Protocol):
    def get_configurations(self) -> dict[str, Any]: ...

    def get_diagnostic_audit(self, submission_id: int) -> dict[str, Any]: ...

    def preview_learner_model(
        self, student_id: str, strategy: str
    ) -> dict[str, Any]: ...

    def rebuild_learner_model(
        self, student_id: str, strategy: str
    ) -> dict[str, Any]: ...
