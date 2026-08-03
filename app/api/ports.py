"""API-owned consumer Ports for residual production Router persistence reads.

Each Port contains exactly the methods directly called by the active Router
at HEAD; each is satisfied by one facade-owned aggregate Repository. No
combined API Repository Port is created.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.calf import ErrorAnnotation
from app.calibration import DiagnosticCalibrationResult
from app.revision import RevisionGroup


@runtime_checkable
class SubmissionBundleReadPort(Protocol):
    """Submission-owned bundle read (analysis, calf, submissions Routers)."""

    def get_submission_bundle(self, essay_id: int) -> dict[str, Any] | None: ...


@runtime_checkable
class StudentLookupPort(Protocol):
    """Learner-owned student lookup (require_student)."""

    def get_student(self, student_id: str) -> dict[str, Any] | None: ...


@runtime_checkable
class AnalysisRunReadPort(Protocol):
    """Analysis-owned run listing (analysis Router)."""

    def list_analysis_runs(self, essay_id: int) -> list[dict[str, Any]]: ...


@runtime_checkable
class CalfReadPort(Protocol):
    """CALF-owned reads (calf Router)."""

    def list_analysis_units(self, submission_id: int, analysis_run_id: str | None = None) -> list[dict[str, Any]]: ...

    def list_error_annotations(self, submission_id: int) -> list[ErrorAnnotation]: ...


@runtime_checkable
class ResearchExportWritePort(Protocol):
    """Research-owned export-job write (research Router, best-effort)."""

    def save_export_job(self, job: dict) -> dict: ...


@runtime_checkable
class StudentSubmissionListPort(Protocol):
    """Submission-owned student submission listing (students, revisions Routers)."""

    def list_student_submissions(self, student_id: str) -> list[dict[str, Any]]: ...


@runtime_checkable
class RevisionGroupLookupPort(Protocol):
    """Revision-owned group lookup (revisions Router)."""

    def get_revision_group_for_submission(self, submission_id: int) -> RevisionGroup | None: ...


@runtime_checkable
class StudentLearnerReadPort(Protocol):
    """Learner-owned profile/history reads (students Router)."""

    def list_student_history(self, student_id: str) -> list[dict[str, Any]]: ...

    def list_history_evidence(self, student_id: str) -> list[dict[str, Any]]: ...

    def list_learner_profile_snapshots(self, student_id: str) -> list[dict[str, Any]]: ...


@runtime_checkable
class SubmissionCalibrationReadPort(Protocol):
    """CALF-owned calibration read (submissions Router)."""

    def get_diagnostic_calibration(self, essay_id: int) -> DiagnosticCalibrationResult | None: ...


@runtime_checkable
class SystemMigrationPort(Protocol):
    """System-owned migration inspection (system Router)."""

    def migration_version(self) -> int: ...
