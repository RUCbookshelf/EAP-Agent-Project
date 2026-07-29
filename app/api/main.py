from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.schemas import (
    ErrorResponse, HealthResponse, HistoryResponse, LearnerProfileResponse,
    StudentResponse, SubmissionCreateRequest, SubmissionRecordResponse,
    SubmissionResponse, VersionResponse,
    ReanalysisResponse,
)
from app.config import Settings, load_settings
from app.database import Database
from app.services import SubmissionService, build_submission_service, ReanalysisService
from app.services.factory import build_analyzer
from app.services import LearnerProfileService
from app.core import LearnerProfileSnapshot


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
    learner_profiles = LearnerProfileService(repository)
    api = FastAPI(title="Writing Feedback API", version=settings.application_version)
    api.state.settings = settings
    api.state.repository = repository
    api.state.submission_service = submission_service
    api.state.learner_profiles = learner_profiles
    analyzer = submission_service.analyzer if hasattr(submission_service, "analyzer") else build_analyzer(settings)
    reanalysis = ReanalysisService(repository, analyzer)
    api.state.reanalysis = reanalysis

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
        analyzer_health = analyzer.health() if hasattr(analyzer, "health") else {
            "active_analyzer": getattr(analyzer, "analyzer_id", "basic"),
            "active_analyzer_version": getattr(analyzer, "version", "unknown"),
            "available": True, "fallback_active": False, "fallback_reason": None,
        }
        selected = getattr(analyzer, "registry", None)
        active_impl = selected.get(analyzer.active_analyzer) if selected and hasattr(analyzer, "active_analyzer") else analyzer
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
            active_analyzer=analyzer_health["active_analyzer"],
            active_analyzer_version=analyzer_health["active_analyzer_version"],
            spacy_installed=hasattr(active_impl, "spacy") or analyzer_health["active_analyzer"] != "spacy" and _package_available("spacy"),
            nlp_model_name=settings.spacy_model,
            nlp_model_installed=hasattr(active_impl, "nlp"),
            nlp_model_version=getattr(active_impl, "model_version", None),
            analyzer_fallback_active=analyzer_health["fallback_active"],
            analyzer_fallback_reason=analyzer_health["fallback_reason"],
        )

    @api.get("/api/v1/system/version", response_model=VersionResponse)
    def version() -> VersionResponse:
        return VersionResponse(
            application_version=settings.application_version, api_version=settings.api_version,
            prompt_version=settings.prompt_version, schema_version="structured-feedback-v0.1.1",
            analysis_version=settings.analysis_version, diagnosis_version=settings.diagnosis_version,
            database_migration_version=repository.migration_version(),
            active_analyzer=settings.active_analyzer,
            nlp_library_version=getattr(getattr(analyzer, "registry", None).get("spacy"), "spacy", None).__version__ if getattr(analyzer, "registry", None) and hasattr(getattr(analyzer, "registry", None).get("spacy"), "spacy") else None,
            nlp_model_name=settings.spacy_model,
            nlp_model_version=getattr(getattr(analyzer, "registry", None).get("spacy"), "model_version", None) if getattr(analyzer, "registry", None) else None,
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

    @api.get("/api/v1/submissions/{submission_id}/analyses")
    def get_analyses(submission_id: int) -> dict:
        if repository.get_submission_bundle(submission_id) is None:
            raise HTTPException(404, "Submission not found.")
        return {"submission_id": submission_id, "analysis_runs": repository.list_analysis_runs(submission_id)}

    @api.post("/api/v1/submissions/{submission_id}/analyses", response_model=ReanalysisResponse, status_code=201)
    def reanalyze_submission(submission_id: int) -> ReanalysisResponse:
        try:
            result = reanalysis.run(submission_id)
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from None
        return ReanalysisResponse(submission_id=submission_id, analysis=result, llm_called=False)

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

    @api.get("/api/v1/students/{student_id}/profile", response_model=LearnerProfileResponse)
    def get_profile(student_id: str) -> LearnerProfileResponse:
        student = require_student(student_id)
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

    @api.get("/api/v1/students/{student_id}/progress", response_model=LearnerProfileSnapshot)
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
    ) -> LearnerProfileSnapshot:
        require_student(student_id)
        if start_date and end_date and start_date > end_date:
            raise HTTPException(422, "start_date must not be after end_date.")
        try:
            return learner_profiles.recalculate(
                student_id, metric=metric, start_date=start_date, end_date=end_date,
                comparable_only=comparable_only, analysis_version=analysis_version,
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    return api


def _package_available(package: str) -> bool:
    try:
        import importlib.util
        return importlib.util.find_spec(package) is not None
    except (ImportError, ValueError):
        return False


app = create_app()
