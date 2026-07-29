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
    RevisionCreateRequest, RevisionGroupResponse,
    ConfigurationRollbackRequest,
)
from app.config import Settings, load_settings
from app.database import Database
from app.services import (
    AdminReanalysisService, ConfigurationService, DashboardService, ReanalysisRequest,
    SubmissionService, build_submission_service, ReanalysisService, RevisionService,
)
from app.services.factory import build_analyzer
from app.services import LearnerProfileService
from app.core import LearnerProfileSnapshot
from app.analysis import default_metric_registry
from app.configuration import ConfigurationCreate, ConfigurationVersion
from app.services.configuration import settings_from_configuration
from app.calibration import DiagnosticCalibrationService


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
    metrics = default_metric_registry()
    configurations = ConfigurationService(repository, analyzer.registry, metrics)
    dashboards = DashboardService(repository, metrics)
    reanalysis = ReanalysisService(repository, analyzer)
    revisions = RevisionService(repository)
    api.state.reanalysis = reanalysis
    api.state.revisions = revisions
    api.state.configurations = configurations
    api.state.dashboards = dashboards
    api.state.admin_reanalysis = AdminReanalysisService(
        repository, settings, configurations, submission_service,
    )

    def apply_runtime_configuration(configuration: ConfigurationVersion) -> None:
        nonlocal analyzer
        effective = settings_from_configuration(settings, configuration)
        analyzer = build_analyzer(effective)
        submission_service.analyzer = analyzer
        reanalysis.analyzer = analyzer
        configurations.registry.analyzers = analyzer.registry
        submission_service.router.temperature = configuration.payload.llm_temperature
        submission_service.calibrator = DiagnosticCalibrationService(configuration.payload)
        if hasattr(submission_service.router.primary, "max_tokens"):
            submission_service.router.primary.max_tokens = configuration.payload.llm_max_tokens

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
            schema_version="structured-feedback-v0.6.1",
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
        registry_versions: dict[str, list[str]] = {}
        for metric in metrics.list():
            registry_versions.setdefault(metric.metric_id, []).append(metric.metric_version)
        active_configuration = configurations.active()
        return VersionResponse(
            application_version=settings.application_version, api_version=settings.api_version,
            prompt_version=active_configuration.payload.active_prompt_version, schema_version="structured-feedback-v0.6.1",
            analysis_version=settings.analysis_version, diagnosis_version=settings.diagnosis_version,
            database_migration_version=repository.migration_version(),
            active_analyzer=getattr(analyzer, "active_analyzer", getattr(analyzer, "analyzer_id", "unknown")),
            nlp_library_version=getattr(getattr(analyzer, "registry", None).get("spacy"), "spacy", None).__version__ if getattr(analyzer, "registry", None) and hasattr(getattr(analyzer, "registry", None).get("spacy"), "spacy") else None,
            nlp_model_name=settings.spacy_model,
            nlp_model_version=getattr(getattr(analyzer, "registry", None).get("spacy"), "model_version", None) if getattr(analyzer, "registry", None) else None,
            metric_versions=registry_versions,
            provider=getattr(submission_service.router.primary, "provider_name", settings.llm_provider),
            model=getattr(submission_service.router.primary, "model_name", settings.deepseek_model),
            active_configuration_version=active_configuration.version,
        )

    @api.post("/api/v1/submissions", response_model=SubmissionResponse, status_code=201)
    def create_submission(payload: SubmissionCreateRequest) -> SubmissionResponse:
        try:
            result = submission_service.submit(payload)
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from None
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        return SubmissionResponse(
            submission_id=result.essay_id, analysis=result.analysis, diagnosis=result.diagnosis,
            feedback_result=result.provider, history=result.history,
            revision_snapshot=result.revision_snapshot,
            diagnostic_calibration=result.diagnostic_calibration,
        )

    @api.get("/api/v1/submissions/{submission_id}/diagnostic-audit")
    def diagnostic_audit(submission_id: int) -> dict:
        if repository.get_submission_bundle(submission_id) is None:
            raise HTTPException(404, "Submission not found.")
        calibration = repository.get_diagnostic_calibration(submission_id)
        if calibration is None:
            raise HTTPException(404, "No v0.6.1 diagnostic calibration exists for this submission.")
        return calibration.model_dump(mode="json")

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

    @api.get("/api/v1/submissions/{submission_id}/revision-candidates")
    def revision_candidates(submission_id: int) -> dict:
        try:
            return {"submission_id": submission_id, "candidates": revisions.candidates(submission_id)}
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from None

    @api.get("/api/v1/students/{student_id}/revision-candidates")
    def student_revision_candidates(student_id: str) -> dict:
        require_student(student_id)
        items = repository.list_student_submissions(student_id)
        return {"student_id": student_id, "candidates": list(reversed(items))}

    @api.post("/api/v1/revisions", response_model=RevisionGroupResponse, status_code=201)
    def create_revision(payload: RevisionCreateRequest) -> RevisionGroupResponse:
        try:
            snapshot = revisions.create_relationship(payload.source_submission_id, payload.target_submission_id)
            group = revisions.group(snapshot.revision_group_id)
            return RevisionGroupResponse(group=group, latest_snapshot=snapshot,
                                         snapshot_history_count=len(revisions.history(group.revision_group_id)))
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from None
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @api.get("/api/v1/revisions/{revision_group_id}", response_model=RevisionGroupResponse)
    def get_revision_group(revision_group_id: str) -> RevisionGroupResponse:
        try:
            group = revisions.group(revision_group_id)
            history = revisions.history(revision_group_id)
            return RevisionGroupResponse(group=group, latest_snapshot=history[-1] if history else None,
                                         snapshot_history_count=len(history))
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from None

    @api.get("/api/v1/revisions/{revision_group_id}/comparison")
    def get_revision_comparison(revision_group_id: str):
        try:
            return revisions.latest(revision_group_id)
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from None

    @api.get("/api/v1/submissions/{submission_id}/revision-analysis")
    def get_submission_revision_analysis(submission_id: int) -> dict:
        group = repository.get_revision_group_for_submission(submission_id)
        if group is None:
            raise HTTPException(404, "Submission is not part of a revision group.")
        history = revisions.history(group.revision_group_id)
        relevant = [item for item in history if item.target_submission_id == submission_id or item.source_submission_id == submission_id]
        return {"group": group, "latest_snapshot": relevant[-1] if relevant else None,
                "snapshot_history": relevant}

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

    @api.get("/api/v1/students/{student_id}/dashboard")
    def get_dashboard(student_id: str, metric_id: str = Query(default="word_count", max_length=100)) -> dict:
        require_student(student_id)
        try:
            return dashboards.build(student_id, metric_id)
        except (LookupError, ValueError) as exc:
            raise HTTPException(422 if isinstance(exc, ValueError) else 404, str(exc)) from None

    @api.get("/api/v1/admin/configurations")
    def list_configurations() -> dict:
        return {
            "active_configuration_id": configurations.active().configuration_id,
            "configurations": [item.model_dump(mode="json") for item in configurations.list()],
            "audit": configurations.audit(),
            "security_note": "Only non-sensitive research parameters are versioned; local-only administration.",
        }

    @api.post("/api/v1/admin/configurations", response_model=ConfigurationVersion, status_code=201)
    def create_configuration(payload: ConfigurationCreate) -> ConfigurationVersion:
        return configurations.create(payload)

    @api.post("/api/v1/admin/configurations/{configuration_id}/validate", response_model=ConfigurationVersion)
    def validate_configuration(configuration_id: str) -> ConfigurationVersion:
        try:
            return configurations.validate(configuration_id)
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from None
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @api.post("/api/v1/admin/configurations/{configuration_id}/activate", response_model=ConfigurationVersion)
    def activate_configuration(configuration_id: str) -> ConfigurationVersion:
        try:
            activated = configurations.activate(configuration_id)
            apply_runtime_configuration(activated)
            return activated
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from None
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @api.post("/api/v1/admin/configurations/{configuration_id}/rollback", response_model=ConfigurationVersion)
    def rollback_configuration(configuration_id: str, payload: ConfigurationRollbackRequest) -> ConfigurationVersion:
        try:
            activated = configurations.rollback(configuration_id, reason=payload.reason, actor=payload.actor)
            apply_runtime_configuration(activated)
            return activated
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from None
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @api.get("/api/v1/admin/algorithms")
    def list_algorithms() -> dict:
        return {"algorithms": configurations.registries()["algorithms"]}

    @api.get("/api/v1/admin/metrics")
    def list_metrics() -> dict:
        return {"metrics": configurations.registries()["metrics"]}

    @api.get("/api/v1/admin/registries")
    def list_registries() -> dict:
        return configurations.registries()

    @api.post("/api/v1/admin/reanalysis/preview")
    def preview_admin_reanalysis(payload: ReanalysisRequest) -> dict:
        try:
            return api.state.admin_reanalysis.preview(payload)
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from None
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @api.post("/api/v1/admin/reanalysis/run")
    def run_admin_reanalysis(payload: ReanalysisRequest) -> dict:
        try:
            return api.state.admin_reanalysis.run(payload)
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from None
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
