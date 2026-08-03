"""Analysis router: analysis runs and local reanalysis."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_analysis_runs_reader, get_reanalysis, get_submission_bundle_reader
from app.api.schemas import ReanalysisResponse

router = APIRouter()


@router.get("/api/v1/submissions/{submission_id}/analyses")
def get_analyses(submission_id: int,
                 bundle_reader=Depends(get_submission_bundle_reader),
                 runs_reader=Depends(get_analysis_runs_reader)) -> dict:
    if bundle_reader.get_submission_bundle(submission_id) is None:
        raise HTTPException(404, "Submission not found.")
    return {"submission_id": submission_id, "analysis_runs": runs_reader.list_analysis_runs(submission_id)}


@router.post("/api/v1/submissions/{submission_id}/analyses", response_model=ReanalysisResponse, status_code=201)
def reanalyze_submission(submission_id: int, reanalysis=Depends(get_reanalysis)) -> ReanalysisResponse:
    try:
        result = reanalysis.run(submission_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None
    return ReanalysisResponse(submission_id=submission_id, analysis=result, llm_called=False)
