"""Practice router: targets, exercises, attempts, evaluations, engagement, and transfer evidence."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import (
    get_practice_reader,
    get_practice_service,
    get_practice_student_reader,
    get_practice_submission_reader,
    get_practice_writer,
    require_student,
)

router = APIRouter()


_STATUS_BY_MAPPING_KIND = {
    "invalid_reference": 422,
    "cross_student": 403,
    "source_not_found": 404,
    "malformed_priority": 422,
    "unresolved_priority": 422,
    "unsupported_category": 422,
}


def _resolve_priority_contract(payload: dict, submission_reader) -> dict:
    """Resolve and validate the persisted priority referenced by the payload.

    Priority-derived requests must not supply authoritative priority content:
    every target field is loaded from persistence and client-supplied values
    that conflict with the resolved contract are rejected.
    """
    from app.practice.mapping import (
        PriorityMappingError,
        PriorityPracticeMappingService,
    )

    mapper = PriorityPracticeMappingService(submission_reader)
    try:
        contract = mapper.resolve_target_contract(
            student_id=payload.get("student_id", ""),
            source_submission_id=payload.get("source_submission_id", 0),
            source_priority_id=payload.get("source_priority_id"),
        )
    except PriorityMappingError as exc:
        status = _STATUS_BY_MAPPING_KIND.get(exc.kind, 422)
        raise HTTPException(
            status,
            "The priority reference could not be resolved to a valid practice target.",
        ) from exc
    for key, authoritative in (
        ("target_code", contract.target_code),
        ("target_label", contract.target_label),
    ):
        supplied = payload.get(key)
        if supplied is not None and supplied != authoritative:
            raise HTTPException(
                422, f"{key} conflicts with the resolved priority.")
    supplied_evidence = payload.get("evidence_ids")
    if supplied_evidence is not None and supplied_evidence != contract.evidence_ids:
        raise HTTPException(422, "evidence_ids conflict with the resolved priority.")
    return contract


@router.get("/api/v1/students/{student_id}/practice-targets")
def get_practice_targets(student_id: str,
                         student_reader=Depends(get_practice_student_reader),
                         practice_reader=Depends(get_practice_reader)) -> list[dict]:
    require_student(student_reader, student_id)
    return practice_reader.list_practice_targets(student_id)


@router.post("/api/v1/practice-targets")
def create_practice_target(payload: dict,
                           practice_writer=Depends(get_practice_writer),
                           practice_service=Depends(get_practice_service),
                           practice_submission_reader=Depends(get_practice_submission_reader)) -> dict:
    svc = practice_service
    source_priority_id = payload.get("source_priority_id")
    if source_priority_id is not None:
        contract = _resolve_priority_contract(payload, practice_submission_reader)
        target = svc.create_practice_target(
            student_id=contract.student_id,
            source_submission_id=contract.source_submission_id,
            source_diagnosis_id=contract.source_diagnosis_id,
            target_code=contract.target_code,
            target_label=contract.target_label,
            source_priority_id=contract.source_priority_id,
            evidence_ids=contract.evidence_ids,
            gate_status=contract.diagnostic_gate_status,
        )
    else:
        target = svc.create_practice_target(
            student_id=payload.get("student_id", ""),
            source_submission_id=payload.get("source_submission_id", 0),
            source_diagnosis_id=payload.get("source_diagnosis_id", ""),
            target_code=payload.get("target_code", ""),
            target_label=payload.get("target_label", ""),
            source_priority_id=None,
            evidence_ids=payload.get("evidence_ids") or [],
            gate_status=payload.get("gate_status", "selected"),
        )
    if target.get("status") != "practice_not_available":
        target = practice_writer.save_practice_target(target)
    return target


@router.post("/api/v1/practice-targets/{practice_target_id}/exercises")
def create_exercise(practice_target_id: str, payload: dict,
                    practice_reader=Depends(get_practice_reader),
                    practice_writer=Depends(get_practice_writer),
                    practice_service=Depends(get_practice_service)) -> dict:
    existing_target = practice_reader.get_practice_target(practice_target_id)
    if existing_target is None:
        raise HTTPException(404, "Practice target not found.")
    exercise = practice_service.generate_exercise(existing_target, payload.get("source_text", ""))
    if exercise.get("status") != "practice_not_available":
        exercise = practice_writer.save_exercise_instance(exercise)
    return exercise


@router.get("/api/v1/practice-targets/{practice_target_id}/exercises")
def get_exercises(practice_target_id: str,
                  practice_reader=Depends(get_practice_reader)) -> list[dict]:
    if practice_reader.get_practice_target(practice_target_id) is None:
        raise HTTPException(404, "Practice target not found.")
    return practice_reader.list_exercise_instances(practice_target_id=practice_target_id)


@router.post("/api/v1/exercises/{exercise_id}/attempts")
def submit_exercise_attempt(exercise_id: str, payload: dict,
                            practice_reader=Depends(get_practice_reader),
                            practice_writer=Depends(get_practice_writer),
                            practice_submission_reader=Depends(get_practice_submission_reader),
                            practice_service=Depends(get_practice_service)) -> dict:
    existing = practice_reader.get_exercise_instance(exercise_id)
    if existing is None:
        raise HTTPException(404, "Exercise instance not found.")
    attempts = practice_reader.list_exercise_attempts(exercise_id)
    next_num = len(attempts) + 1
    attempt = practice_service.submit_attempt(exercise_id, payload.get("student_id", ""), payload.get("response_text", ""), next_num)
    if attempt.get("status") != "invalid_input":
        attempt = practice_writer.save_exercise_attempt(attempt)
        # Conservative rule-based evaluation, persisted with the attempt.
        # Best-effort: the attempt record remains authoritative.
        try:
            target = practice_reader.get_practice_target(existing.get("practice_target_id", ""))
            source_text = ""
            if target and target.get("source_submission_id"):
                bundle = practice_submission_reader.get_submission_bundle(int(target["source_submission_id"]))
                source_text = (bundle or {}).get("essay_text") or ""
            evaluation = practice_service.evaluate_attempt(attempt, target or {}, source_text)
            attempt["evaluation"] = practice_writer.save_practice_evaluation(evaluation)
        except Exception:
            attempt["evaluation"] = None
    return attempt


@router.get("/api/v1/exercises/{exercise_id}/attempts")
def get_exercise_attempts(exercise_id: str,
                           practice_reader=Depends(get_practice_reader)) -> list[dict]:
    if practice_reader.get_exercise_instance(exercise_id) is None:
        raise HTTPException(404, "Exercise instance not found.")
    return practice_reader.list_exercise_attempts(exercise_id)


@router.get("/api/v1/students/{student_id}/engagement-traces")
def get_engagement_traces(student_id: str,
                           student_reader=Depends(get_practice_student_reader),
                           practice_reader=Depends(get_practice_reader)) -> list[dict]:
    require_student(student_reader, student_id)
    return practice_reader.list_feedback_engagement_traces(student_id)


@router.get("/api/v1/students/{student_id}/transfer-evidence")
def get_transfer_evidence(student_id: str,
                           student_reader=Depends(get_practice_student_reader),
                           practice_reader=Depends(get_practice_reader)) -> list[dict]:
    require_student(student_reader, student_id)
    return practice_reader.list_transfer_evidence_candidates(student_id)
