"""API-only dependency helpers for feature routers.

These helpers expose application services built by the composition root
(app/api/main.py) through FastAPI dependency injection. No domain behavior
lives here.
"""

from __future__ import annotations

from fastapi import HTTPException, Request

from app.api.ports import (
    AnalysisRunReadPort,
    CalfReadPort,
    ResearchExportWritePort,
    RevisionGroupLookupPort,
    StudentLearnerReadPort,
    StudentLookupPort,
    StudentSubmissionListPort,
    SubmissionBundleReadPort,
    SubmissionCalibrationReadPort,
    SystemMigrationPort,
)
from app.review.protocols import ReviewEvidenceLookupProtocol
from app.review.service import ReviewService


def get_settings(request: Request):
    return request.app.state.settings


def get_submission_bundle_reader(request: Request) -> SubmissionBundleReadPort:
    return request.app.state.submission_bundle_reader


def get_student_lookup(request: Request) -> StudentLookupPort:
    return request.app.state.student_lookup


def get_analysis_runs_reader(request: Request) -> AnalysisRunReadPort:
    return request.app.state.analysis_runs_reader


def get_calf_reader(request: Request) -> CalfReadPort:
    return request.app.state.calf_reader


def get_research_export_writer(request: Request) -> ResearchExportWritePort:
    return request.app.state.research_export_writer


def get_student_submission_list(request: Request) -> StudentSubmissionListPort:
    return request.app.state.student_submission_list


def get_revision_group_lookup(request: Request) -> RevisionGroupLookupPort:
    return request.app.state.revision_group_lookup


def get_student_learner_reader(request: Request) -> StudentLearnerReadPort:
    return request.app.state.student_learner_reader


def get_submission_calibration_reader(request: Request) -> SubmissionCalibrationReadPort:
    return request.app.state.submission_calibration_reader


def get_system_migration_reader(request: Request) -> SystemMigrationPort:
    return request.app.state.system_migration_reader


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


def get_review_service(request: Request) -> ReviewService:
    service = getattr(request.app.state, "review_service", None)
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="Review service is not available in this composition.",
        )
    return service


def get_review_evidence_lookup(
    request: Request,
) -> ReviewEvidenceLookupProtocol:
    lookup = getattr(request.app.state, "review_evidence_lookup", None)
    if lookup is None:
        raise HTTPException(
            status_code=503,
            detail="Review evidence lookup is not available in this composition.",
        )
    return lookup


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


def get_practice_target_creation_service(request: Request):
    return request.app.state.practice_target_creation_service


def get_practice_target_completion_service(request: Request):
    return request.app.state.practice_target_completion_service


def require_student(repository, student_id: str) -> dict:
    """Return the student row or raise the canonical 404 used by the API."""
    student = repository.get_student(student_id)
    if student is None:
        raise HTTPException(404, "Student not found.")
    return student
