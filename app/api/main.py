from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.schemas import (
    ErrorResponse, HealthResponse, HistoryResponse, PlannedLongitudinalResponse,
    StudentResponse, SubmissionCreateRequest, SubmissionRecordResponse,
    SubmissionResponse, VersionResponse,
)
from app.config import Settings, load_settings
from app.database import Database
from app.services import SubmissionService, build_submission_service


def _error(status: int, code: str, message: str, details=None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "details": details}})


def create_app(
    settings: Settings | None = None,
    *,
    repository: Database | None = None,
    submission_service: SubmissionService | None = None,
) -> FastAPI:
    settings = settings or load_settings()
    repository = repository or Database(settings.database_path)
    repository.initialize()
    submission_service = submission_service or build_submission_service(settings, repository)
    api = FastAPI(title="Writing Feedback API", version=settings.application_version)
    api.state.settings = settings
    api.state.repository = repository
    api.state.submission_service = submission_service

    @api.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        details = [{"location": list(item["loc"]), "message": item["msg"], "type": item["type"]} for item in exc.errors()]
        return _error(422, "validation_error", "The request did not satisfy the API schema.", details)

    @api.exception_handler(HTTPException)
    async def http_handler(_: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else "The requested resource is unavailable."
        return _error(exc.status_code, "not_found" if exc.status_code == 404 else "request_error", detail)

    @api.exception_handler(Exception)
    async def unexpected_handler(_: Request, __: Exception):
        return _error(500, "internal_error", "The operation could not be completed. No secret or internal stack is exposed.")

    @api.get("/api/v1/system/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        connected = repository.ping()
        return HealthResponse(
            status="ok" if connected else "degraded",
            application_version=settings.application_version,
            api_version=settings.api_version,
            database_status="connected" if connected else "unavailable",
            database_migration_version=repository.migration_version() if connected else 0,
            prompt_version=settings.prompt_version,
            schema_version="structured-feedback-v0.1.1",
            llm_provider=settings.llm_provider,
            llm_api_configured=bool(settings.deepseek_api_key) if settings.llm_provider == "deepseek" else False,
        )

    @api.get("/api/v1/system/version", response_model=VersionResponse)
    def version() -> VersionResponse:
        return VersionResponse(
            application_version=settings.application_version, api_version=settings.api_version,
            prompt_version=settings.prompt_version, schema_version="structured-feedback-v0.1.1",
            analysis_version=settings.analysis_version, diagnosis_version=settings.diagnosis_version,
            database_migration_version=repository.migration_version(),
        )

    @api.post("/api/v1/submissions", response_model=SubmissionResponse, status_code=201)
    def create_submission(payload: SubmissionCreateRequest) -> SubmissionResponse:
        result = submission_service.submit(payload)
        return SubmissionResponse(
            submission_id=result.essay_id, analysis=result.analysis, diagnosis=result.diagnosis,
            feedback_result=result.provider, history=result.history,
        )

    @api.get("/api/v1/submissions/{submission_id}", response_model=SubmissionRecordResponse)
    def get_submission(submission_id: int) -> SubmissionRecordResponse:
        row = repository.get_submission_bundle(submission_id)
        if row is None:
            raise HTTPException(404, "Submission not found.")
        submission_id_value = row.pop("essay_id")
        analysis = row.pop("metrics")
        return SubmissionRecordResponse(
            submission_id=submission_id_value, analysis=analysis,
            **{k: v for k, v in row.items() if k in SubmissionRecordResponse.model_fields},
        )

    def require_student(student_id: str) -> dict:
        student = repository.get_student(student_id)
        if student is None:
            raise HTTPException(404, "Student not found.")
        return student

    @api.get("/api/v1/students/{student_id}", response_model=StudentResponse)
    def get_student(student_id: str) -> StudentResponse:
        item = require_student(student_id)
        item["is_synthetic"] = bool(item["is_synthetic"])
        return StudentResponse.model_validate(item)

    @api.get("/api/v1/students/{student_id}/history", response_model=HistoryResponse)
    def get_history(student_id: str) -> HistoryResponse:
        require_student(student_id)
        return HistoryResponse(
            student_id=student_id,
            submissions=repository.list_student_submissions(student_id),
            history_records=repository.list_student_history(student_id),
        )

    def planned(student_id: str) -> PlannedLongitudinalResponse:
        student = require_student(student_id)
        count = int(student["submission_count"])
        status = "insufficient_history" if count < 2 else "planned_for_v0.3"
        return PlannedLongitudinalResponse(
            student_id=student_id, status=status, submission_count=count,
            message="Formal prototype longitudinal analysis is planned for v0.3.",
            limitations=["No proficiency, CEFR, score, or validated growth conclusion is available."],
        )

    @api.get("/api/v1/students/{student_id}/profile", response_model=PlannedLongitudinalResponse)
    def get_profile(student_id: str) -> PlannedLongitudinalResponse:
        return planned(student_id)

    @api.get("/api/v1/students/{student_id}/progress", response_model=PlannedLongitudinalResponse)
    def get_progress(student_id: str) -> PlannedLongitudinalResponse:
        return planned(student_id)

    return api


app = create_app()
