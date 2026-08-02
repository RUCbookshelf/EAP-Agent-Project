"""CALF router: constructs, metrics, analysis units, syntactic units, and error annotations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_calf, get_reanalysis, get_repository
from app.calf import ErrorAnnotation

router = APIRouter()


@router.get("/api/v1/calf/constructs")
def calf_constructs(calf=Depends(get_calf)) -> dict:
    return {"constructs": [item.model_dump(mode="json") for item in calf.registry.list_constructs()]}


@router.get("/api/v1/calf/metrics")
def calf_metrics(
    construct_id: str | None = None, subconstruct_id: str | None = None,
    measurement_status: str | None = None, automation_level: str | None = None,
    diagnosis_eligible: bool | None = None, longitudinal_eligible: bool | None = None,
    manual_annotation_required: bool | None = None,
    calf=Depends(get_calf),
) -> dict:
    return {"metrics": [item.model_dump(mode="json") for item in calf.registry.list_specifications(
        construct_id=construct_id, subconstruct_id=subconstruct_id,
        measurement_status=measurement_status, automation_level=automation_level,
        diagnosis_eligible=diagnosis_eligible, longitudinal_eligible=longitudinal_eligible,
        manual_annotation_required=manual_annotation_required,
    )]}


@router.get("/api/v1/calf/metrics/{metric_id}")
def calf_metric(metric_id: str, metric_version: str | None = None, calf=Depends(get_calf)) -> dict:
    try:
        return calf.registry.get_specification(metric_id, metric_version).model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from None


@router.get("/api/v1/calf/analysis-units")
def calf_analysis_unit_registry(calf=Depends(get_calf)) -> dict:
    return {"analysis_units": [item.model_dump(mode="json") for item in calf.registry.list_units()]}


@router.get("/api/v1/submissions/{submission_id}/calf")
def submission_calf(submission_id: int, calf=Depends(get_calf)) -> dict:
    try:
        return calf.submission_report(submission_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None


@router.get("/api/v1/submissions/{submission_id}/analysis-units")
def submission_analysis_units(
    submission_id: int, analysis_run_id: str | None = None,
    repository=Depends(get_repository),
) -> dict:
    if repository.get_submission_bundle(submission_id) is None:
        raise HTTPException(404, "Submission not found.")
    return {"submission_id": submission_id,
            "analysis_units": repository.list_analysis_units(submission_id, analysis_run_id)}


@router.get("/api/v1/submissions/{submission_id}/syntactic-units")
def submission_syntactic_units(submission_id: int, repository=Depends(get_repository)) -> dict:
    if repository.get_submission_bundle(submission_id) is None:
        raise HTTPException(404, "Submission not found.")
    items = repository.list_analysis_units(submission_id)
    return {"submission_id": submission_id, "syntactic_units": [
        item for item in items if item["unit_id"] in {
            "sentence", "clause_candidate", "t_unit_candidate", "validated_clause", "validated_t_unit"
        }
    ]}


@router.get("/api/v1/submissions/{submission_id}/error-annotations")
def get_error_annotations(submission_id: int, repository=Depends(get_repository)) -> dict:
    if repository.get_submission_bundle(submission_id) is None:
        raise HTTPException(404, "Submission not found.")
    items = repository.list_error_annotations(submission_id)
    return {"submission_id": submission_id,
            "error_annotations": [item.model_dump(mode="json") for item in items]}


@router.post("/api/v1/submissions/{submission_id}/error-annotations/import", status_code=201)
def import_error_annotations(
    submission_id: int, annotations: list[ErrorAnnotation],
    calf=Depends(get_calf),
) -> dict:
    try:
        items = calf.import_error_annotations(submission_id, annotations)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    return {"submission_id": submission_id,
            "error_annotations": [item.model_dump(mode="json") for item in items]}


@router.get("/api/v1/students/{student_id}/calf-trajectories")
def calf_trajectories(student_id: str, calf=Depends(get_calf)) -> dict:
    try:
        return calf.trajectories(student_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None


@router.post("/api/v1/submissions/{submission_id}/calf/reanalyze", status_code=201)
def calf_reanalyze(
    submission_id: int,
    reanalysis=Depends(get_reanalysis),
    calf=Depends(get_calf),
) -> dict:
    try:
        result = reanalysis.run(submission_id)
        return {"submission_id": submission_id, "analysis": result,
                "calf": calf.submission_report(submission_id), "llm_called": False,
                "history_overwritten": False}
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None
