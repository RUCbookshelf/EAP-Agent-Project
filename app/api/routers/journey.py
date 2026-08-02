"""Journey router: Student Learning Journey read endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_journey_service, require_student

router = APIRouter()


@router.get("/api/v1/students/{student_id}/journey")
def get_student_journey(student_id: str, journey_service=Depends(get_journey_service)) -> dict:
    require_student(journey_service.student_reader, student_id)
    return journey_service.get_journey(student_id)
