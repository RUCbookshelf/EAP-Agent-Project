"""Journey router: Student Learning Journey read endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_repository, require_student
from app.journey.service import JourneyService

router = APIRouter()


@router.get("/api/v1/students/{student_id}/journey")
def get_student_journey(student_id: str, repository=Depends(get_repository)) -> dict:
    require_student(repository, student_id)
    return JourneyService(repository).get_journey(student_id)
