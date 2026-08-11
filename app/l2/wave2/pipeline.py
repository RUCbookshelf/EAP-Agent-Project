"""Real-pipeline adapter for the Wave-2 revision loop.

Goal PDW2-C-L2-REVISION-SCAFFOLD: submissions and reanalyses re-enter the
EXISTING Writing Intelligence pipeline -- the composition-root
``SubmissionService`` (analyzer -> diagnoser -> calibration -> feedback
router -> revision relationships -> history) and the existing
``ReanalysisService`` (append-only real analyzer runs) plus
``SubmissionService.regenerate_feedback`` (real feedback regeneration). No
disconnected revision-only service is built here.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from app.models import EssaySubmission
from app.models.schemas import utc_now


def essay_text_hash(text: str) -> str:
    """Stable content hash used as an evidence link on version records."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ReanalysisResult(BaseModel):
    """Outcome of re-running the existing pipeline for one submission."""

    model_config = ConfigDict(extra="forbid")

    submission_id: int = Field(ge=1)
    analysis_run_id: str
    analysis_version: str
    feedback_record_id: int | None = None
    provider_status: str | None = None
    reanalyzed_at: datetime = Field(default_factory=utc_now)
    limitations: list[str] = Field(default_factory=list)


@runtime_checkable
class WritingPipelinePort(Protocol):
    """Boundary over the existing Writing Intelligence pipeline."""

    def submit(self, submission: EssaySubmission) -> dict[str, Any]: ...

    def reanalyze(self, submission_id: int) -> ReanalysisResult: ...

    def get_submission_bundle(self, essay_id: int) -> dict[str, Any] | None: ...

    def list_student_submissions(self, student_id: str) -> list[dict[str, Any]]: ...


class ExistingWritingPipeline:
    """Adapter over the existing composition-root services."""

    def __init__(self, submission_service, reanalysis_service) -> None:
        self._submission_service = submission_service
        self._reanalysis_service = reanalysis_service

    def submit(self, submission: EssaySubmission) -> dict[str, Any]:
        result = self._submission_service.submit(submission)
        analysis = result.analysis
        revision_snapshot = result.revision_snapshot
        return {
            "essay_id": result.essay_id,
            "analysis_run_id": analysis.analysis_run_id,
            "analysis_version": analysis.analysis_version,
            "analysis": analysis,
            "diagnosis": result.diagnosis,
            "provider": result.provider,
            "revision_group_id": (
                revision_snapshot.revision_group_id if revision_snapshot else None
            ),
            "revision_snapshot_id": (
                revision_snapshot.revision_snapshot_id if revision_snapshot else None
            ),
            "revision_snapshot": revision_snapshot,
            "history": result.history,
        }

    def reanalyze(self, submission_id: int) -> ReanalysisResult:
        # Existing real analyzer path (append-only AnalysisRun).
        analysis = self._reanalysis_service.run(submission_id)
        # Existing real feedback path (reuses the stored diagnosis and the
        # real provider router; never creates or overwrites the essay).
        provider = self._submission_service.regenerate_feedback(
            submission_id, analysis,
        )
        bundle = self.get_submission_bundle(submission_id)
        return ReanalysisResult(
            submission_id=submission_id,
            analysis_run_id=analysis.analysis_run_id,
            analysis_version=analysis.analysis_version,
            feedback_record_id=(
                bundle.get("feedback_id") if bundle is not None else None
            ),
            provider_status=provider.success_status,
            limitations=[
                "Reanalysis appends new runs; it does not retroactively "
                "validate earlier outputs or claim learning outcomes.",
            ],
        )

    def get_submission_bundle(self, essay_id: int) -> dict[str, Any] | None:
        return self._submission_service.submission_repository.get_submission_bundle(
            essay_id
        )

    def list_student_submissions(self, student_id: str) -> list[dict[str, Any]]:
        rows = (
            self._submission_service.submission_repository.list_student_submissions(
                student_id
            )
        )
        bundles: list[dict[str, Any]] = []
        for row in rows:
            bundle = self.get_submission_bundle(int(row["essay_id"]))
            if bundle is not None:
                bundles.append(bundle)
        return sorted(
            bundles,
            key=lambda item: (item.get("submitted_at") or "", int(item["essay_id"])),
        )


__all__ = [
    "ExistingWritingPipeline",
    "ReanalysisResult",
    "WritingPipelinePort",
    "essay_text_hash",
]
