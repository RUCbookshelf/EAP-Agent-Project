"""API-only dependency helpers for feature routers.

These helpers expose application services built by the composition root
(app/api/main.py) through FastAPI dependency injection. No domain behavior
lives here.
"""

from __future__ import annotations

from fastapi import HTTPException, Request


def get_settings(request: Request):
    return request.app.state.settings


def get_repository(request: Request):
    return request.app.state.repository


def get_submission_service(request: Request):
    return request.app.state.submission_service


def get_analyzer(request: Request):
    return request.app.state.analyzer


def get_metrics(request: Request):
    return request.app.state.metrics


def get_configurations(request: Request):
    return request.app.state.configurations


def get_dashboards(request: Request):
    return request.app.state.dashboards


def get_reanalysis(request: Request):
    return request.app.state.reanalysis


def get_journey_service(request: Request):
    return request.app.state.journey_service


def get_revisions(request: Request):
    return request.app.state.revisions


def get_calf(request: Request):
    return request.app.state.calf


def get_learner_profiles(request: Request):
    return request.app.state.learner_profiles


def get_admin_reanalysis(request: Request):
    return request.app.state.admin_reanalysis


def get_research(request: Request):
    return request.app.state.research


def get_practice_submission_reader(request: Request):
    return request.app.state.practice_submission_reader


def get_practice_reader(request: Request):
    return request.app.state.practice_reader


def get_practice_writer(request: Request):
    return request.app.state.practice_writer


def get_practice_student_reader(request: Request):
    return request.app.state.practice_student_reader


def get_practice_service(request: Request):
    return request.app.state.practice_service


def require_student(repository, student_id: str) -> dict:
    """Return the student row or raise the canonical 404 used by the API."""
    student = repository.get_student(student_id)
    if student is None:
        raise HTTPException(404, "Student not found.")
    return student
