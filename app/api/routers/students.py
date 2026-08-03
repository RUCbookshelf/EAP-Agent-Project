"""Students router: learner lookup, profile, progress, learner-model, and dashboard reads."""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import (
    get_dashboards,
    get_learner_profiles,
    get_student_learner_reader,
    get_student_lookup,
    get_student_submission_list,
    require_student,
)
from app.api.schemas import (
    HistoryResponse,
    LearnerModelBuildRequest,
    LearnerProfileResponse,
    StudentResponse,
)
from app.core import LearnerProfileSnapshot

router = APIRouter()


def _learner_model_snapshot(student_id: str, student_lookup, learner_profiles) -> LearnerProfileSnapshot:
    require_student(student_lookup, student_id)
    return learner_profiles.latest_or_recalculate(student_id)


@router.get("/api/v1/students/{student_id}", response_model=StudentResponse)
def get_student(student_id: str, student_lookup=Depends(get_student_lookup)) -> StudentResponse:
    item = require_student(student_lookup, student_id)
    item["is_synthetic"] = bool(item["is_synthetic"])
    return StudentResponse.model_validate(item)


@router.get("/api/v1/students/{student_id}/history", response_model=HistoryResponse)
def get_history(
    student_id: str,
    student_lookup=Depends(get_student_lookup),
    student_submission_list=Depends(get_student_submission_list),
    learner_reader=Depends(get_student_learner_reader),
) -> HistoryResponse:
    require_student(student_lookup, student_id)
    return HistoryResponse(
        student_id=student_id,
        submissions=student_submission_list.list_student_submissions(student_id),
        history_records=learner_reader.list_student_history(student_id),
    )


@router.get("/api/v1/students/{student_id}/profile", response_model=LearnerProfileResponse)
def get_profile(
    student_id: str,
    student_lookup=Depends(get_student_lookup),
    learner_profiles=Depends(get_learner_profiles),
) -> LearnerProfileResponse:
    student = require_student(student_lookup, student_id)
    snapshot = learner_profiles.latest_or_recalculate(student_id)
    return LearnerProfileResponse(
        student_id=student_id, submission_count=int(student["submission_count"]),
        comparable_submission_count=len(snapshot.included_submission_ids),
        latest_snapshot=snapshot, analysis_version=snapshot.analysis_version,
        history_sufficiency=snapshot.baseline_status,
        persistent_issues=snapshot.persistent_issues,
        recently_reduced_issues=snapshot.recently_reduced_issues,
        current_priority_candidates=snapshot.current_priority_candidates,
        limitations=snapshot.limitations,
        snapshot_history_count=len(learner_profiles.history(student_id)),
    )


@router.get("/api/v1/students/{student_id}/progress", response_model=LearnerProfileSnapshot)
def get_progress(
    student_id: str,
    metric: Literal[
        "word_count", "sentence_count", "paragraph_count", "average_sentence_length",
        "unique_word_count", "type_token_ratio", "connective_count", "repeated_content_words",
    ] | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    comparable_only: bool = True,
    analysis_version: str | None = Query(default=None, max_length=100),
    student_lookup=Depends(get_student_lookup),
    learner_profiles=Depends(get_learner_profiles),
) -> LearnerProfileSnapshot:
    require_student(student_lookup, student_id)
    if start_date and end_date and start_date > end_date:
        raise HTTPException(422, "start_date must not be after end_date.")
    try:
        return learner_profiles.recalculate(
            student_id, metric=metric, start_date=start_date, end_date=end_date,
            comparable_only=comparable_only, analysis_version=analysis_version,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@router.get("/api/v1/students/{student_id}/learner-model")
def get_learner_model(
    student_id: str,
    student_lookup=Depends(get_student_lookup),
    learner_profiles=Depends(get_learner_profiles),
) -> LearnerProfileSnapshot:
    return _learner_model_snapshot(student_id, student_lookup, learner_profiles)


@router.get("/api/v1/students/{student_id}/learner-model/task-clusters")
def get_task_clusters(
    student_id: str,
    student_lookup=Depends(get_student_lookup),
    learner_profiles=Depends(get_learner_profiles),
) -> dict:
    snapshot = _learner_model_snapshot(student_id, student_lookup, learner_profiles)
    return {"student_id": student_id, "snapshot_id": snapshot.snapshot_id,
            "task_clusters": snapshot.task_clusters}


@router.get("/api/v1/students/{student_id}/learner-model/metric-trajectories")
def get_metric_trajectories(
    student_id: str,
    student_lookup=Depends(get_student_lookup),
    learner_profiles=Depends(get_learner_profiles),
) -> dict:
    snapshot = _learner_model_snapshot(student_id, student_lookup, learner_profiles)
    return {"student_id": student_id, "snapshot_id": snapshot.snapshot_id,
            "metric_trajectories": snapshot.metric_trajectories}


@router.get("/api/v1/students/{student_id}/learner-model/diagnostic-trajectories")
def get_diagnostic_trajectories(
    student_id: str,
    student_lookup=Depends(get_student_lookup),
    learner_profiles=Depends(get_learner_profiles),
) -> dict:
    snapshot = _learner_model_snapshot(student_id, student_lookup, learner_profiles)
    return {"student_id": student_id, "snapshot_id": snapshot.snapshot_id,
            "diagnostic_trajectories": snapshot.diagnostic_trajectories}


@router.get("/api/v1/students/{student_id}/learner-model/learning-targets")
def get_learning_targets(
    student_id: str,
    student_lookup=Depends(get_student_lookup),
    learner_profiles=Depends(get_learner_profiles),
) -> dict:
    snapshot = _learner_model_snapshot(student_id, student_lookup, learner_profiles)
    return {"student_id": student_id, "snapshot_id": snapshot.snapshot_id,
            "current_learning_targets": snapshot.current_learning_targets,
            "strength_patterns": snapshot.strength_patterns,
            "data_sufficiency": snapshot.data_sufficiency}


@router.get("/api/v1/students/{student_id}/learner-model/history-evidence")
def get_history_evidence(
    student_id: str,
    student_lookup=Depends(get_student_lookup),
    learner_reader=Depends(get_student_learner_reader),
) -> dict:
    require_student(student_lookup, student_id)
    return {"student_id": student_id,
            "history_evidence": learner_reader.list_history_evidence(student_id)}


@router.get("/api/v1/students/{student_id}/learner-model/snapshots")
def list_learner_model_snapshots(
    student_id: str,
    student_lookup=Depends(get_student_lookup),
    learner_reader=Depends(get_student_learner_reader),
) -> dict:
    require_student(student_lookup, student_id)
    snapshots = learner_reader.list_learner_profile_snapshots(student_id)
    return {"student_id": student_id, "snapshots": snapshots, "count": len(snapshots)}


@router.get("/api/v1/students/{student_id}/learner-model/snapshots/{snapshot_id}")
def get_learner_model_snapshot(
    student_id: str, snapshot_id: str,
    student_lookup=Depends(get_student_lookup),
    learner_reader=Depends(get_student_learner_reader),
) -> dict:
    require_student(student_lookup, student_id)
    item = next((snapshot for snapshot in learner_reader.list_learner_profile_snapshots(student_id)
                 if snapshot.get("snapshot_id") == snapshot_id), None)
    if item is None:
        raise HTTPException(404, "Learner profile snapshot not found.")
    return item


@router.post("/api/v1/students/{student_id}/learner-model/preview")
def preview_learner_model(
    student_id: str, payload: LearnerModelBuildRequest,
    student_lookup=Depends(get_student_lookup),
    learner_profiles=Depends(get_learner_profiles),
) -> LearnerProfileSnapshot:
    student = require_student(student_lookup, student_id)
    if int(student["submission_count"]) > payload.max_submissions:
        raise HTTPException(422, "Submission count exceeds the bounded learner-model preview limit.")
    return learner_profiles.recalculate(
        student_id, representative_draft_strategy=payload.representative_draft_strategy,
        persist=False,
    )


@router.post("/api/v1/students/{student_id}/learner-model/rebuild", status_code=201)
def rebuild_learner_model(
    student_id: str, payload: LearnerModelBuildRequest,
    student_lookup=Depends(get_student_lookup),
    learner_profiles=Depends(get_learner_profiles),
) -> LearnerProfileSnapshot:
    student = require_student(student_lookup, student_id)
    if int(student["submission_count"]) > payload.max_submissions:
        raise HTTPException(422, "Submission count exceeds the bounded learner-model rebuild limit.")
    return learner_profiles.recalculate(
        student_id, representative_draft_strategy=payload.representative_draft_strategy,
        persist=True,
    )


@router.get("/api/v1/students/{student_id}/dashboard")
def get_dashboard(
    student_id: str,
    metric_id: str = Query(default="word_count", max_length=100),
    student_lookup=Depends(get_student_lookup),
    dashboards=Depends(get_dashboards),
) -> dict:
    require_student(student_lookup, student_id)
    try:
        return dashboards.build(student_id, metric_id)
    except (LookupError, ValueError) as exc:
        raise HTTPException(422 if isinstance(exc, ValueError) else 404, str(exc)) from None
