"""Writing Feedback API -- v0.9.3-A lifecycle-aware entry point.

Liveness, readiness, and health endpoints are available immediately after
the ASGI server starts. Heavy initialization (spaCy, database, services)
runs inside a FastAPI lifespan context manager so the server remains
responsive during startup.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
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
    LearnerModelBuildRequest,
)
from app.config import Settings, load_settings
from app.database import Database
from app.lifecycle import ServiceState, lifecycle
from app.services import (
    AdminReanalysisService, CalfService, ConfigurationService, DashboardService, ReanalysisRequest,
    SubmissionService, build_submission_service, ReanalysisService, RevisionService,
)
from app.services.factory import build_analyzer
from app.services import LearnerProfileService
from app.core import LearnerProfileSnapshot
from app.analysis import default_metric_registry
from app.configuration import ConfigurationCreate, ConfigurationVersion
from app.services.configuration import settings_from_configuration
from app.calibration import DiagnosticCalibrationService
from app.feedback import FeedbackReliabilityService
from app.calf import ErrorAnnotation
from app.practice.service import PracticeService


def _error(status: int, code: str, message: str, details=None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": details}},
    )


def _package_available(package: str) -> bool:
    try:
        import importlib.util
        return importlib.util.find_spec(package) is not None
    except (ImportError, ValueError):
        return False


def _register_business_routes(api: FastAPI) -> None:
    """Register all business routes. Called inside lifespan after init succeeds."""
    settings = api.state.settings
    repository = api.state.repository
    submission_service = api.state.submission_service
    analyzer = api.state.analyzer
    metrics = api.state.metrics
    configurations = api.state.configurations
    dashboards = api.state.dashboards
    reanalysis = api.state.reanalysis
    revisions = api.state.revisions
    calf = api.state.calf
    learner_profiles = api.state.learner_profiles

    def apply_runtime_configuration(configuration: ConfigurationVersion) -> None:
        nonlocal analyzer
        effective = settings_from_configuration(settings, configuration)
        analyzer = build_analyzer(effective)
        submission_service.analyzer = analyzer
        reanalysis.analyzer = analyzer
        configurations.registry.analyzers = analyzer.registry
        submission_service.router.temperature = configuration.payload.llm_temperature
        submission_service.calibrator = DiagnosticCalibrationService(configuration.payload)
        submission_service.router.reliability = FeedbackReliabilityService(configuration.payload)
        submission_service.calf_configuration = configuration.payload
        if hasattr(submission_service.router.primary, "max_tokens"):
            submission_service.router.primary.max_tokens = configuration.payload.llm_max_tokens

    from app.research.service import ResearchDataService  # noqa: F811
    from app.research.schemas import ExportJob, HumanReviewCreate, PiiReview  # noqa: F811

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
            schema_version="structured-feedback-v0.7.1",
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
            prompt_version=active_configuration.payload.active_prompt_version, schema_version="structured-feedback-v0.7.1",
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
            feedback_provider_status=result.provider.feedback_provider_status,
            longitudinal_assessment=result.longitudinal_assessment,
            revision_group_summary=result.revision_group_summary,
            within_task_revision_trajectory=result.within_task_revision_trajectory,
            ui_empty_states=result.ui_empty_states,
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

    @api.get("/api/v1/calf/constructs")
    def calf_constructs() -> dict:
        return {"constructs": [item.model_dump(mode="json") for item in calf.registry.list_constructs()]}

    @api.get("/api/v1/calf/metrics")
    def calf_metrics(
        construct_id: str | None = None, subconstruct_id: str | None = None,
        measurement_status: str | None = None, automation_level: str | None = None,
        diagnosis_eligible: bool | None = None, longitudinal_eligible: bool | None = None,
        manual_annotation_required: bool | None = None,
    ) -> dict:
        return {"metrics": [item.model_dump(mode="json") for item in calf.registry.list_specifications(
            construct_id=construct_id, subconstruct_id=subconstruct_id,
            measurement_status=measurement_status, automation_level=automation_level,
            diagnosis_eligible=diagnosis_eligible, longitudinal_eligible=longitudinal_eligible,
            manual_annotation_required=manual_annotation_required,
        )]}

    @api.get("/api/v1/calf/metrics/{metric_id}")
    def calf_metric(metric_id: str, metric_version: str | None = None) -> dict:
        try:
            return calf.registry.get_specification(metric_id, metric_version).model_dump(mode="json")
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from None

    @api.get("/api/v1/calf/analysis-units")
    def calf_analysis_unit_registry() -> dict:
        return {"analysis_units": [item.model_dump(mode="json") for item in calf.registry.list_units()]}

    @api.get("/api/v1/submissions/{submission_id}/calf")
    def submission_calf(submission_id: int) -> dict:
        try:
            return calf.submission_report(submission_id)
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from None

    @api.get("/api/v1/submissions/{submission_id}/analysis-units")
    def submission_analysis_units(submission_id: int, analysis_run_id: str | None = None) -> dict:
        if repository.get_submission_bundle(submission_id) is None:
            raise HTTPException(404, "Submission not found.")
        return {"submission_id": submission_id,
                "analysis_units": repository.list_analysis_units(submission_id, analysis_run_id)}

    @api.get("/api/v1/submissions/{submission_id}/syntactic-units")
    def submission_syntactic_units(submission_id: int) -> dict:
        if repository.get_submission_bundle(submission_id) is None:
            raise HTTPException(404, "Submission not found.")
        items = repository.list_analysis_units(submission_id)
        return {"submission_id": submission_id, "syntactic_units": [
            item for item in items if item["unit_id"] in {
                "sentence", "clause_candidate", "t_unit_candidate", "validated_clause", "validated_t_unit"
            }
        ]}

    @api.get("/api/v1/submissions/{submission_id}/error-annotations")
    def get_error_annotations(submission_id: int) -> dict:
        if repository.get_submission_bundle(submission_id) is None:
            raise HTTPException(404, "Submission not found.")
        items = repository.list_error_annotations(submission_id)
        return {"submission_id": submission_id,
                "error_annotations": [item.model_dump(mode="json") for item in items]}

    @api.post("/api/v1/submissions/{submission_id}/error-annotations/import", status_code=201)
    def import_error_annotations(submission_id: int, annotations: list[ErrorAnnotation]) -> dict:
        try:
            items = calf.import_error_annotations(submission_id, annotations)
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from None
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        return {"submission_id": submission_id,
                "error_annotations": [item.model_dump(mode="json") for item in items]}

    @api.get("/api/v1/students/{student_id}/calf-trajectories")
    def calf_trajectories(student_id: str) -> dict:
        try:
            return calf.trajectories(student_id)
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from None

    @api.post("/api/v1/submissions/{submission_id}/calf/reanalyze", status_code=201)
    def calf_reanalyze(submission_id: int) -> dict:
        try:
            result = reanalysis.run(submission_id)
            return {"submission_id": submission_id, "analysis": result,
                    "calf": calf.submission_report(submission_id), "llm_called": False,
                    "history_overwritten": False}
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from None

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

    @api.get("/api/v1/revisions/{revision_group_id}/trajectory")
    def get_revision_trajectory(revision_group_id: str):
        try:
            return revisions.trajectory(revision_group_id)
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

    def learner_model_snapshot(student_id: str) -> LearnerProfileSnapshot:
        require_student(student_id)
        return learner_profiles.latest_or_recalculate(student_id)

    @api.get("/api/v1/students/{student_id}/learner-model")
    def get_learner_model(student_id: str) -> LearnerProfileSnapshot:
        return learner_model_snapshot(student_id)

    @api.get("/api/v1/students/{student_id}/learner-model/task-clusters")
    def get_task_clusters(student_id: str) -> dict:
        snapshot = learner_model_snapshot(student_id)
        return {"student_id": student_id, "snapshot_id": snapshot.snapshot_id,
                "task_clusters": snapshot.task_clusters}

    @api.get("/api/v1/students/{student_id}/learner-model/metric-trajectories")
    def get_metric_trajectories(student_id: str) -> dict:
        snapshot = learner_model_snapshot(student_id)
        return {"student_id": student_id, "snapshot_id": snapshot.snapshot_id,
                "metric_trajectories": snapshot.metric_trajectories}

    @api.get("/api/v1/students/{student_id}/learner-model/diagnostic-trajectories")
    def get_diagnostic_trajectories(student_id: str) -> dict:
        snapshot = learner_model_snapshot(student_id)
        return {"student_id": student_id, "snapshot_id": snapshot.snapshot_id,
                "diagnostic_trajectories": snapshot.diagnostic_trajectories}

    @api.get("/api/v1/students/{student_id}/learner-model/learning-targets")
    def get_learning_targets(student_id: str) -> dict:
        snapshot = learner_model_snapshot(student_id)
        return {"student_id": student_id, "snapshot_id": snapshot.snapshot_id,
                "current_learning_targets": snapshot.current_learning_targets,
                "strength_patterns": snapshot.strength_patterns,
                "data_sufficiency": snapshot.data_sufficiency}

    @api.get("/api/v1/students/{student_id}/learner-model/history-evidence")
    def get_history_evidence(student_id: str) -> dict:
        require_student(student_id)
        return {"student_id": student_id,
                "history_evidence": repository.list_history_evidence(student_id)}

    @api.get("/api/v1/students/{student_id}/learner-model/snapshots")
    def list_learner_model_snapshots(student_id: str) -> dict:
        require_student(student_id)
        snapshots = repository.list_learner_profile_snapshots(student_id)
        return {"student_id": student_id, "snapshots": snapshots, "count": len(snapshots)}

    @api.get("/api/v1/students/{student_id}/learner-model/snapshots/{snapshot_id}")
    def get_learner_model_snapshot(student_id: str, snapshot_id: str) -> dict:
        require_student(student_id)
        item = next((snapshot for snapshot in repository.list_learner_profile_snapshots(student_id)
                     if snapshot.get("snapshot_id") == snapshot_id), None)
        if item is None:
            raise HTTPException(404, "Learner profile snapshot not found.")
        return item

    @api.post("/api/v1/students/{student_id}/learner-model/preview")
    def preview_learner_model(student_id: str, payload: LearnerModelBuildRequest) -> LearnerProfileSnapshot:
        student = require_student(student_id)
        if int(student["submission_count"]) > payload.max_submissions:
            raise HTTPException(422, "Submission count exceeds the bounded learner-model preview limit.")
        return learner_profiles.recalculate(
            student_id, representative_draft_strategy=payload.representative_draft_strategy,
            persist=False,
        )

    @api.post("/api/v1/students/{student_id}/learner-model/rebuild", status_code=201)
    def rebuild_learner_model(student_id: str, payload: LearnerModelBuildRequest) -> LearnerProfileSnapshot:
        student = require_student(student_id)
        if int(student["submission_count"]) > payload.max_submissions:
            raise HTTPException(422, "Submission count exceeds the bounded learner-model rebuild limit.")
        return learner_profiles.recalculate(
            student_id, representative_draft_strategy=payload.representative_draft_strategy,
            persist=True,
        )

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

    @api.get("/api/v1/students/{student_id}/practice-targets")
    def get_practice_targets(student_id: str) -> list[dict]:
        require_student(student_id)
        return repository.list_practice_targets(student_id)
    @api.post("/api/v1/practice-targets")
    def create_practice_target(payload: dict) -> dict:
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
    @api.post("/api/v1/practice-targets/{practice_target_id}/exercises")
    def create_exercise(practice_target_id: str, payload: dict) -> dict:
        existing_target = repository.get_practice_target(practice_target_id)
        if existing_target is None:
            raise HTTPException(404, "Practice target not found.")
        svc = PracticeService(repository)
        exercise = svc.generate_exercise(existing_target, payload.get("source_text", ""))
        if exercise.get("status") != "practice_not_available":
            exercise = repository.save_exercise_instance(exercise)
        return exercise
    @api.post("/api/v1/exercises/{exercise_id}/attempts")
    def submit_exercise_attempt(exercise_id: str, payload: dict) -> dict:
        existing = repository.get_exercise_instance(exercise_id)
        if existing is None:
            raise HTTPException(404, "Exercise instance not found.")
        attempts = repository.list_exercise_attempts(exercise_id)
        next_num = len(attempts) + 1
        svc = PracticeService(repository)
        attempt = svc.submit_attempt(exercise_id, payload.get("student_id", ""), payload.get("response_text", ""), next_num)
        if attempt.get("status") != "invalid_input":
            attempt = repository.save_exercise_attempt(attempt)
        return attempt
    @api.get("/api/v1/students/{student_id}/engagement-traces")
    def get_engagement_traces(student_id: str) -> list[dict]:
        require_student(student_id)
        return repository.list_feedback_engagement_traces(student_id)
    @api.get("/api/v1/students/{student_id}/transfer-evidence")
    def get_transfer_evidence(student_id: str) -> list[dict]:
        require_student(student_id)
        return repository.list_transfer_evidence_candidates(student_id)
    @api.get("/api/v1/research/export/schema")
    def research_export_schema() -> dict:
        return ResearchDataService(repository).schema()

    @api.post("/api/v1/research/export/preview")
    def research_export_preview(payload: dict) -> dict:
        try:
            job = ExportJob(**payload)
        except Exception as e:
            raise HTTPException(422, str(e)) from None
        return ResearchDataService(repository).preview(job)

    @api.post("/api/v1/research/export/run")
    def research_export_run(payload: dict) -> dict:
        try:
            job = ExportJob(**payload)
        except Exception as e:
            raise HTTPException(422, str(e)) from None
        try:
            return ResearchDataService(repository).run_export(
                job,
                git_commit=api.state.git_commit if hasattr(api.state, 'git_commit') else None,
                migration_version=getattr(api.state, 'migration_version', None),
                config_version=getattr(api.state, 'config_version', None),
            )
        except Exception as e:
            raise HTTPException(500, str(e)) from None

    @api.get("/api/v1/research/export/{export_id}")
    def research_export_status(export_id: str) -> dict:
        import glob
        pattern = f"research_exports/*/manifest.json"
        for p in Path(pattern.replace('*', '*')).parent.glob('*/manifest.json') if Path(pattern).parent else []:
            pass
        return {"export_id": export_id, "status": "unknown"}

    @api.get("/api/v1/research/data-quality")
    def research_data_quality() -> dict:
        return ResearchDataService(repository).data_quality_report().model_dump(mode='json')

    @api.get("/api/v1/submissions/{submission_id}/pii-candidates")
    def pii_candidates(submission_id: int) -> list[dict]:
        try:
            return ResearchDataService(repository).scan_pii(submission_id)
        except LookupError as e:
            raise HTTPException(404, str(e)) from None

    @api.post("/api/v1/submissions/{submission_id}/pii-review")
    def pii_review(submission_id: int, payload: dict) -> dict:
        reviews = [PiiReview(**item) for item in payload.get('reviews', [])]
        return ResearchDataService(repository).apply_pii_review(submission_id, reviews)

    @api.post("/api/v1/research/reviews")
    def create_human_review(payload: dict) -> dict:
        try:
            review = HumanReviewCreate(**payload)
            result = ResearchDataService(repository).create_human_review(review)
            return result.model_dump(mode='json')
        except Exception as e:
            raise HTTPException(422, str(e)) from None

    @api.get("/api/v1/research/reviews")
    def list_human_reviews(target_type: str | None = None, target_id: str | None = None) -> list[dict]:
        return ResearchDataService(repository).get_human_reviews(target_type, target_id)
    return api


def _run_startup(api: FastAPI) -> None:
    """Run initialization stages in a background thread.

    Runs inside a daemon thread spawned by the lifespan so the ASGI server
    can serve lifecycle endpoints (/live, /ready, /health) while heavy
    initialization (spaCy, database, services) is still in progress.
    """
    import logging
    logger = logging.getLogger("writing_feedback.startup")

    # Stage 1: Settings
    stage = lifecycle.start_stage("load_settings")
    try:
        settings = load_settings()
        lifecycle.application_version = settings.application_version
        lifecycle.prompt_version = settings.prompt_version
        lifecycle.complete_stage(stage, success=True)
        logger.info("Stage load_settings: OK (%.0fms)", stage.elapsed_ms)
    except Exception as exc:
        lifecycle.complete_stage(stage, success=False, error_category=type(exc).__name__)
        lifecycle.transition(ServiceState.FAILED)
        lifecycle.failed_stage = "load_settings"
        lifecycle.failure_category = type(exc).__name__
        logger.error("Stage load_settings: FAILED (%s)", type(exc).__name__)
        return

    # Stage 2: Database
    stage = lifecycle.start_stage("database_init")
    try:
        repository = Database(settings.database_path)
        repository.initialize()
        mv = repository.migration_version()
        lifecycle.database_status = "connected"
        lifecycle.migration_version = mv
        lifecycle.complete_stage(stage, success=True)
        logger.info("Stage database_init: OK migration=%d (%.0fms)", mv, stage.elapsed_ms)
    except Exception as exc:
        lifecycle.complete_stage(stage, success=False, error_category=type(exc).__name__)
        lifecycle.database_status = "unavailable"
        lifecycle.transition(ServiceState.FAILED)
        lifecycle.failed_stage = "database_init"
        lifecycle.failure_category = type(exc).__name__
        logger.error("Stage database_init: FAILED (%s)", type(exc).__name__)
        return

    # Stage 3: Analyzer (spaCy)
    stage = lifecycle.start_stage("build_analyzer")
    try:
        analyzer = build_analyzer(settings)
        lifecycle.active_analyzer = getattr(analyzer, "active_analyzer", "basic")
        lifecycle.active_analyzer_version = getattr(analyzer, "version", "unknown")
        lifecycle.nlp_model_name = settings.spacy_model
        spacy_reg = getattr(analyzer, "registry", {})
        spacy_impl = spacy_reg.get("spacy") if isinstance(spacy_reg, dict) else None
        lifecycle.nlp_model_installed = bool(getattr(spacy_impl, "nlp", None)) if spacy_impl else False
        lifecycle.nlp_model_version = getattr(spacy_impl, "model_version", None) if spacy_impl else None
        lifecycle.analyzer_fallback_active = getattr(analyzer, "fallback_active", False)
        lifecycle.complete_stage(stage, success=True)
        logger.info("Stage build_analyzer: OK analyzer=%s (%.0fms)", lifecycle.active_analyzer, stage.elapsed_ms)
    except Exception as exc:
        lifecycle.complete_stage(stage, success=False, error_category=type(exc).__name__)
        lifecycle.transition(ServiceState.FAILED)
        lifecycle.failed_stage = "build_analyzer"
        lifecycle.failure_category = type(exc).__name__
        logger.error("Stage build_analyzer: FAILED (%s)", type(exc).__name__)
        return

    # Stage 4: Business services
    stage = lifecycle.start_stage("build_services")
    try:
        sub_svc = build_submission_service(settings, repository)
        lps = LearnerProfileService(repository)
        m_registry = default_metric_registry()
        cfgs = ConfigurationService(repository, analyzer.registry, m_registry)
        dbs = DashboardService(repository, m_registry)
        reanalysis_svc = ReanalysisService(repository, analyzer)
        rvs = RevisionService(repository)
        clf = CalfService(repository)

        lifecycle.llm_provider = settings.llm_provider
        lifecycle.llm_api_configured = bool(settings.deepseek_api_key) if settings.llm_provider == "deepseek" else False

        try:
            active_cfg = repository.get_active_configuration()
            lifecycle.active_configuration = active_cfg.version
        except RuntimeError:
            lifecycle.active_configuration = None

        lifecycle.complete_stage(stage, success=True)
        logger.info("Stage build_services: OK (%.0fms)", stage.elapsed_ms)
    except Exception as exc:
        lifecycle.complete_stage(stage, success=False, error_category=type(exc).__name__)
        lifecycle.transition(ServiceState.FAILED)
        lifecycle.failed_stage = "build_services"
        lifecycle.failure_category = type(exc).__name__
        logger.error("Stage build_services: FAILED (%s)", type(exc).__name__)
        return

    # Optional-component check: DeepSeek configured but key missing -> degraded
    # (existing validated behavior falls back to LocalDemo; DeepSeek stays disabled)
    if settings.llm_provider == "deepseek" and not settings.deepseek_api_key:
        lifecycle.degraded_components.append("provider_unavailable")
        logger.warning("Optional provider unavailable: DeepSeek key missing; LocalDemo fallback active")

    # Store on app state
    api.state.settings = settings
    api.state.repository = repository
    api.state.submission_service = sub_svc
    api.state.learner_profiles = lps
    api.state.analyzer = analyzer
    api.state.metrics = m_registry
    api.state.configurations = cfgs
    api.state.dashboards = dbs
    api.state.reanalysis = reanalysis_svc
    api.state.revisions = rvs
    api.state.calf = clf
    api.state.admin_reanalysis = AdminReanalysisService(
        repository, settings, cfgs, sub_svc,
    )

    # Register business routes
    _register_business_routes(api)

    if lifecycle.degraded_components:
        lifecycle.transition(ServiceState.DEGRADED)
        logger.info("Startup complete: state=degraded total=%.0fms components=%s",
                     lifecycle.startup_elapsed_ms, lifecycle.degraded_components)
    else:
        lifecycle.transition(ServiceState.READY)
        logger.info("Startup complete: ready total=%.0fms stages=%d",
                     lifecycle.startup_elapsed_ms, len(lifecycle.stages))


@asynccontextmanager
async def _lifespan(api: FastAPI):
    """Lifespan: yields immediately; initialization runs in a background thread.

    This keeps the lightweight HTTP service observable (liveness responds with
    lifecycle_state=starting) while heavy initialization is still in progress.
    """
    import threading
    lifecycle.transition(ServiceState.STARTING)
    threading.Thread(
        target=_run_startup, args=(api,), daemon=True, name="startup-init",
    ).start()
    yield
    lifecycle.transition(ServiceState.STOPPING)


def _build_full_app(
    settings: Settings,
    *,
    repository: Database | None = None,
    submission_service: SubmissionService | None = None,
) -> FastAPI:
    """Build a fully-initialized app immediately (used by tests)."""
    if settings is None:
        settings = load_settings()
    if repository is None:
        repository = Database(settings.database_path)
    repository.initialize()
    if submission_service is None:
        submission_service = build_submission_service(settings, repository)
    learner_profiles = LearnerProfileService(repository)
    analyzer = submission_service.analyzer if hasattr(submission_service, "analyzer") else build_analyzer(settings)
    metrics = default_metric_registry()
    configurations = ConfigurationService(repository, analyzer.registry, metrics)
    dashboards = DashboardService(repository, metrics)
    reanalysis = ReanalysisService(repository, analyzer)
    revisions = RevisionService(repository)
    calf = CalfService(repository)

    lifecycle.application_version = settings.application_version
    lifecycle.prompt_version = settings.prompt_version
    lifecycle.database_status = "connected"
    lifecycle.migration_version = repository.migration_version()
    lifecycle.active_analyzer = getattr(analyzer, "active_analyzer", "basic")
    lifecycle.active_analyzer_version = getattr(analyzer, "version", "unknown")
    lifecycle.nlp_model_name = settings.spacy_model
    lifecycle.llm_provider = settings.llm_provider
    lifecycle.llm_api_configured = bool(settings.deepseek_api_key) if settings.llm_provider == "deepseek" else False
    lifecycle.transition(ServiceState.READY)

    api = FastAPI(title="Writing Feedback API", version="0.8.0")
    api.state.settings = settings
    api.state.repository = repository
    api.state.submission_service = submission_service
    api.state.learner_profiles = learner_profiles
    api.state.analyzer = analyzer
    api.state.metrics = metrics
    api.state.configurations = configurations
    api.state.dashboards = dashboards
    api.state.reanalysis = reanalysis
    api.state.revisions = revisions
    api.state.calf = calf
    api.state.admin_reanalysis = AdminReanalysisService(repository, settings, configurations, submission_service)

    _register_business_routes(api)
    _register_lifecycle_routes(api)
    return api


def _register_lifecycle_routes(api: FastAPI) -> None:
    """Register liveness, readiness, and health endpoints."""

    @api.get("/api/v1/system/live")
    def liveness():
        return {"status": "ok", "lifecycle_state": lifecycle.state.value}

    @api.get("/api/v1/system/ready")
    def readiness():
        ready = lifecycle.state in (ServiceState.READY, ServiceState.DEGRADED)
        resp = {"status": lifecycle.state.value, "ready": ready}
        if lifecycle.state == ServiceState.DEGRADED:
            resp["degraded_components"] = lifecycle.degraded_components
        if not ready:
            resp["failure_category"] = lifecycle.failure_category
            resp["failed_stage"] = lifecycle.failed_stage
            resp["startup_elapsed_ms"] = round(lifecycle.startup_elapsed_ms, 1)
        return resp

    @api.get("/api/v1/system/health", response_model=HealthResponse)
    def health():
        h = lifecycle.health_dict()
        # Backward-compatible status mapping: ready -> ok, everything else -> degraded.
        # Full state detail is available via /live and /ready.
        status = "ok" if h["lifecycle_state"] == "ready" else "degraded"
        db_status = h["database_status"] if h["database_status"] in ("connected", "unavailable") else "unavailable"
        return HealthResponse(
            status=status,
            database_status=db_status,
            application_version=h["application_version"],
            api_version=h["api_version"],

            database_migration_version=h["database_migration_version"] or 0,
            prompt_version=h["prompt_version"] or "unknown",
            schema_version=h["schema_version"],
            llm_provider=h["llm_provider"] or "unknown",
            llm_api_configured=h["llm_api_configured"],
            active_analyzer=h["active_analyzer"] or "unknown",
            active_analyzer_version=h["active_analyzer_version"] or "unknown",
            spacy_installed=h["spacy_installed"],
            nlp_model_name=h["nlp_model_name"] or "N/A",
            nlp_model_installed=h["nlp_model_installed"],
            nlp_model_version=h["nlp_model_version"],
            analyzer_fallback_active=h["analyzer_fallback_active"],
            analyzer_fallback_reason=h["analyzer_fallback_reason"],
        )


def create_app(
    settings: Settings | None = None,
    *,
    repository: Database | None = None,
    submission_service: SubmissionService | None = None,
) -> FastAPI:
    """Create the FastAPI application.

    When settings is None (production mode): uses lifespan for lazy init. When settings is provided (test mode): builds fully immediately. Optional repository and submission_service allow dependency injection.
    When settings is provided (test mode): builds fully immediately.
    """
    if settings is not None or repository is not None or submission_service is not None:
        return _build_full_app(settings, repository=repository, submission_service=submission_service)

    api = FastAPI(
        title="Writing Feedback API",
        version="0.8.0",
        lifespan=_lifespan,
    )

    @api.middleware("http")
    async def readiness_gate(request: Request, call_next):
        """Return 503 for business routes while initialization is incomplete."""
        path = request.url.path
        lifecycle_paths = (
            "/api/v1/system/live",
            "/api/v1/system/ready",
            "/api/v1/system/health",
            "/docs", "/docs/", "/redoc", "/openapi.json",
        )
        if not path.startswith(lifecycle_paths) and lifecycle.state not in (
            ServiceState.READY, ServiceState.DEGRADED,
        ):
            return JSONResponse(
                status_code=503,
                content={"error": {"code": "not_ready", "message": "API is starting; please retry.", "details": None}},
            )
        return await call_next(request)

    _register_lifecycle_routes(api)
    return api

    @api.get("/api/v1/system/live")
    def liveness():
        return {"status": "ok", "lifecycle_state": lifecycle.state.value}

    @api.get("/api/v1/system/ready")
    def readiness():
        ready = lifecycle.state in (ServiceState.READY, ServiceState.DEGRADED)
        resp = {"status": lifecycle.state.value, "ready": ready}
        if lifecycle.state == ServiceState.DEGRADED:
            resp["degraded_components"] = lifecycle.degraded_components
        if not ready:
            resp["failure_category"] = lifecycle.failure_category
            resp["failed_stage"] = lifecycle.failed_stage
            resp["startup_elapsed_ms"] = round(lifecycle.startup_elapsed_ms, 1)
        return resp

    @api.get("/api/v1/system/health", response_model=HealthResponse)
    def health():
        h = lifecycle.health_dict()
        # Backward-compatible status mapping: ready -> ok, everything else -> degraded.
        # Full state detail is available via /live and /ready.
        status = "ok" if h["lifecycle_state"] == "ready" else "degraded"
        db_status = h["database_status"] if h["database_status"] in ("connected", "unavailable") else "unavailable"
        return HealthResponse(
            status=status,
            database_status=db_status,
            application_version=h["application_version"],
            api_version=h["api_version"],

            database_migration_version=h["database_migration_version"] or 0,
            prompt_version=h["prompt_version"] or "unknown",
            schema_version=h["schema_version"],
            llm_provider=h["llm_provider"] or "unknown",
            llm_api_configured=h["llm_api_configured"],
            active_analyzer=h["active_analyzer"] or "unknown",
            active_analyzer_version=h["active_analyzer_version"] or "unknown",
            spacy_installed=h["spacy_installed"],
            nlp_model_name=h["nlp_model_name"] or "N/A",
            nlp_model_installed=h["nlp_model_installed"],
            nlp_model_version=h["nlp_model_version"],
            analyzer_fallback_active=h["analyzer_fallback_active"],
            analyzer_fallback_reason=h["analyzer_fallback_reason"],
        )

    return api


app = create_app()
