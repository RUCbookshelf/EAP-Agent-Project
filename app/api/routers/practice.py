"""Practice router: targets, exercises, attempts, evaluations, engagement, and transfer evidence."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_repository, require_student
from app.practice.service import PracticeService

router = APIRouter()


@router.get("/api/v1/students/{student_id}/practice-targets")
def get_practice_targets(student_id: str, repository=Depends(get_repository)) -> list[dict]:
    require_student(repository, student_id)
    return repository.list_practice_targets(student_id)


@router.post("/api/v1/practice-targets")
def create_practice_target(payload: dict, repository=Depends(get_repository)) -> dict:
    svc = PracticeService(repository)
    target = svc.create_practice_target(
        student_id=payload.get("student_id", ""),
        source_submission_id=payload.get("source_submission_id", 0),
        source_diagnosis_id=payload.get("source_diagnosis_id", ""),
        target_code=payload.get("target_code", ""),
        target_label=payload.get("target_label", ""),
        gate_status=payload.get("gate_status", "selected"),
    )
    if target.get("status") != "practice_not_available":
        target = repository.save_practice_target(target)
    return target


@router.post("/api/v1/practice-targets/{practice_target_id}/exercises")
def create_exercise(practice_target_id: str, payload: dict, repository=Depends(get_repository)) -> dict:
    existing_target = repository.get_practice_target(practice_target_id)
    if existing_target is None:
        raise HTTPException(404, "Practice target not found.")
    svc = PracticeService(repository)
    exercise = svc.generate_exercise(existing_target, payload.get("source_text", ""))
    if exercise.get("status") != "practice_not_available":
        exercise = repository.save_exercise_instance(exercise)
    return exercise


@router.get("/api/v1/practice-targets/{practice_target_id}/exercises")
def get_exercises(practice_target_id: str, repository=Depends(get_repository)) -> list[dict]:
    if repository.get_practice_target(practice_target_id) is None:
        raise HTTPException(404, "Practice target not found.")
    return repository.list_exercise_instances(practice_target_id=practice_target_id)


@router.post("/api/v1/exercises/{exercise_id}/attempts")
def submit_exercise_attempt(exercise_id: str, payload: dict, repository=Depends(get_repository)) -> dict:
    existing = repository.get_exercise_instance(exercise_id)
    if existing is None:
        raise HTTPException(404, "Exercise instance not found.")
    attempts = repository.list_exercise_attempts(exercise_id)
    next_num = len(attempts) + 1
    svc = PracticeService(repository)
    attempt = svc.submit_attempt(exercise_id, payload.get("student_id", ""), payload.get("response_text", ""), next_num)
    if attempt.get("status") != "invalid_input":
        attempt = repository.save_exercise_attempt(attempt)
        # Conservative rule-based evaluation, persisted with the attempt.
        # Best-effort: the attempt record remains authoritative.
        try:
            target = repository.get_practice_target(existing.get("practice_target_id", ""))
            source_text = ""
            if target and target.get("source_submission_id"):
                bundle = repository.get_submission_bundle(int(target["source_submission_id"]))
                source_text = (bundle or {}).get("essay_text") or ""
            evaluation = svc.evaluate_attempt(attempt, target or {}, source_text)
            attempt["evaluation"] = repository.save_practice_evaluation(evaluation)
        except Exception:
            attempt["evaluation"] = None
    return attempt


@router.get("/api/v1/exercises/{exercise_id}/attempts")
def get_exercise_attempts(exercise_id: str, repository=Depends(get_repository)) -> list[dict]:
    if repository.get_exercise_instance(exercise_id) is None:
        raise HTTPException(404, "Exercise instance not found.")
    return repository.list_exercise_attempts(exercise_id)


@router.get("/api/v1/students/{student_id}/engagement-traces")
def get_engagement_traces(student_id: str, repository=Depends(get_repository)) -> list[dict]:
    require_student(repository, student_id)
    return repository.list_feedback_engagement_traces(student_id)


@router.get("/api/v1/students/{student_id}/transfer-evidence")
def get_transfer_evidence(student_id: str, repository=Depends(get_repository)) -> list[dict]:
    require_student(repository, student_id)
    return repository.list_transfer_evidence_candidates(student_id)
