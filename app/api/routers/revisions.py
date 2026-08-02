"""Revisions router: candidates, groups, snapshots, comparison, and trajectory reads."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_repository, get_revisions, require_student
from app.api.schemas import RevisionCreateRequest, RevisionGroupResponse

router = APIRouter()


@router.get("/api/v1/submissions/{submission_id}/revision-candidates")
def revision_candidates(submission_id: int, revisions=Depends(get_revisions)) -> dict:
    try:
        return {"submission_id": submission_id, "candidates": revisions.candidates(submission_id)}
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None


@router.get("/api/v1/students/{student_id}/revision-candidates")
def student_revision_candidates(
    student_id: str,
    repository=Depends(get_repository),
) -> dict:
    require_student(repository, student_id)
    items = repository.list_student_submissions(student_id)
    return {"student_id": student_id, "candidates": list(reversed(items))}


@router.post("/api/v1/revisions", response_model=RevisionGroupResponse, status_code=201)
def create_revision(
    payload: RevisionCreateRequest,
    revisions=Depends(get_revisions),
) -> RevisionGroupResponse:
    try:
        snapshot = revisions.create_relationship(payload.source_submission_id, payload.target_submission_id)
        group = revisions.group(snapshot.revision_group_id)
        return RevisionGroupResponse(group=group, latest_snapshot=snapshot,
                                     snapshot_history_count=len(revisions.history(group.revision_group_id)))
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@router.get("/api/v1/revisions/{revision_group_id}", response_model=RevisionGroupResponse)
def get_revision_group(revision_group_id: str, revisions=Depends(get_revisions)) -> RevisionGroupResponse:
    try:
        group = revisions.group(revision_group_id)
        history = revisions.history(revision_group_id)
        return RevisionGroupResponse(group=group, latest_snapshot=history[-1] if history else None,
                                     snapshot_history_count=len(history))
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None


@router.get("/api/v1/revisions/{revision_group_id}/comparison")
def get_revision_comparison(revision_group_id: str, revisions=Depends(get_revisions)):
    try:
        return revisions.latest(revision_group_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None


@router.get("/api/v1/revisions/{revision_group_id}/trajectory")
def get_revision_trajectory(revision_group_id: str, revisions=Depends(get_revisions)):
    try:
        return revisions.trajectory(revision_group_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None


@router.get("/api/v1/submissions/{submission_id}/revision-analysis")
def get_submission_revision_analysis(
    submission_id: int,
    repository=Depends(get_repository),
    revisions=Depends(get_revisions),
) -> dict:
    group = repository.get_revision_group_for_submission(submission_id)
    if group is None:
        raise HTTPException(404, "Submission is not part of a revision group.")
    history = revisions.history(group.revision_group_id)
    relevant = [item for item in history if item.target_submission_id == submission_id or item.source_submission_id == submission_id]
    return {"group": group, "latest_snapshot": relevant[-1] if relevant else None,
            "snapshot_history": relevant}
