"""Submissions router: creation, retrieval, and diagnostic audit."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_repository, get_submission_service
from app.api.schemas import (
    SubmissionCreateRequest,
    SubmissionRecordResponse,
    SubmissionResponse,
)

router = APIRouter()


@router.post("/api/v1/submissions", response_model=SubmissionResponse, status_code=201)
def create_submission(
    payload: SubmissionCreateRequest,
    submission_service=Depends(get_submission_service),
) -> SubmissionResponse:
    try:
        result = submission_service.submit(payload)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    return SubmissionResponse(
        submission_id=result.essay_id, analysis=result.analysis, diagnosis=result.diagnosis,
        feedback_result=result.provider, history=result.history,
        revision_snapshot=result.revision_snapshot,
        diagnostic_calibration=result.diagnostic_calibration,
        feedback_provider_status=result.provider.feedback_provider_status,
        longitudinal_assessment=result.longitudinal_assessment,
        revision_group_summary=result.revision_group_summary,
        within_task_revision_trajectory=result.within_task_revision_trajectory,
        ui_empty_states=result.ui_empty_states,
    )


@router.get("/api/v1/submissions/{submission_id}/diagnostic-audit")
def diagnostic_audit(submission_id: int, repository=Depends(get_repository)) -> dict:
    if repository.get_submission_bundle(submission_id) is None:
        raise HTTPException(404, "Submission not found.")
    calibration = repository.get_diagnostic_calibration(submission_id)
    if calibration is None:
        raise HTTPException(404, "No v0.6.1 diagnostic calibration exists for this submission.")
    return calibration.model_dump(mode="json")


@router.get("/api/v1/submissions/{submission_id}", response_model=SubmissionRecordResponse)
def get_submission(submission_id: int, repository=Depends(get_repository)) -> SubmissionRecordResponse:
    row = repository.get_submission_bundle(submission_id)
    if row is None:
        raise HTTPException(404, "Submission not found.")
    submission_id_value = row.pop("essay_id")
    analysis = row.pop("metrics")
    return SubmissionRecordResponse(
        submission_id=submission_id_value, analysis=analysis,
        **{k: v for k, v in row.items() if k in SubmissionRecordResponse.model_fields},
    )
