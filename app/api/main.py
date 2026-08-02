"""Writing Feedback API -- v0.9.5-B composition root.

FastAPI application creation, lifespan wiring, middleware, exception handlers,
service construction, and router inclusion live here. Feature route handlers
are owned by feature router modules under app/api/routers/.

Liveness, readiness, and health endpoints are available immediately after
the ASGI server starts. Heavy initialization (spaCy, database, services)
runs inside a FastAPI lifespan context manager so the server remains
responsive during startup.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.analysis import default_metric_registry
from app.api.routers import (
    admin,
    analysis,
    calf,
    journey,
    practice,
    research,
    revisions,
    students,
    submissions,
    system,
)
from app.config import Settings, load_settings
from app.database import Database
from app.lifecycle import ServiceState, lifecycle
from app.research.service import ResearchDataService
from app.services import (
    AdminReanalysisService,
    CalfService,
    ConfigurationService,
    DashboardService,
    LearnerProfileService,
    ReanalysisService,
    RevisionService,
    SubmissionService,
    build_submission_service,
)
from app.services.factory import build_analyzer


# Business routers are included after the system router in both the production
# startup stage and the test/app-factory builder. The order mirrors the
# pre-v0.9.5-B production registration order.
_BUSINESS_ROUTERS = (
    submissions,
    analysis,
    calf,
    revisions,
    students,
    admin,
    practice,
    journey,
    research,
)


def _include_business_routers(api: FastAPI) -> None:
    for router_module in _BUSINESS_ROUTERS:
        api.include_router(router_module.router)


def _apply_analyzer_lifecycle(settings: Settings, analyzer) -> None:
    """Populate lifecycle analyzer/NLP facts (shared by startup and test builder)."""
    lifecycle.active_analyzer = getattr(analyzer, "active_analyzer", "basic")
    lifecycle.active_analyzer_version = getattr(analyzer, "version", "unknown")
    lifecycle.nlp_model_name = settings.spacy_model
    spacy_reg = getattr(analyzer, "registry", None)
    spacy_impl = spacy_reg.get("spacy") if spacy_reg is not None else None
    lifecycle.nlp_model_installed = bool(getattr(spacy_impl, "nlp", None)) if spacy_impl else False
    lifecycle.nlp_model_version = getattr(spacy_impl, "model_version", None) if spacy_impl else None
    lifecycle.analyzer_fallback_active = getattr(analyzer, "fallback_active", False)


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
        _apply_analyzer_lifecycle(settings, analyzer)
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
        research_svc = ResearchDataService(repository)

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
    api.state.research = research_svc
    api.state.admin_reanalysis = AdminReanalysisService(
        repository, settings, cfgs, sub_svc,
    )

    # Register feature routers (system router is already included at app creation)
    _include_business_routers(api)

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


def _register_request_middleware(api: FastAPI) -> None:
    """Request-ID middleware: generate/accept a request ID, set response header,
    and emit a sanitized structured request log line."""
    import logging

    @api.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        import uuid
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        request.state.request_id = request_id
        start = time.monotonic()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        logging.getLogger("writing_feedback.request").info(
            "request_id=%s method=%s path=%s status=%s elapsed_ms=%s lifecycle=%s",
            request_id, request.method, request.url.path, response.status_code,
            elapsed_ms, lifecycle.state.value,
        )
        return response


def _register_error_handlers(api: FastAPI) -> None:
    """Register canonical error handlers at app creation so the middleware
    stack (built on the first request) includes them."""
    from app.errors import ApiError, ErrorCategory

    def _req_id(request: Request) -> str | None:
        return getattr(request.state, "request_id", None)

    @api.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        field_errors = [{"location": list(item["loc"]), "message": item["msg"], "type": item["type"]} for item in exc.errors()]
        err = ApiError.from_category(
            ErrorCategory.INVALID_REQUEST, "request_validation",
            request_id=_req_id(request), http_status=422, field_errors=field_errors,
        )
        return JSONResponse(status_code=422, content=err.to_public_dict(include_detail=True))

    @api.exception_handler(HTTPException)
    async def http_handler(request: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else "The requested resource is unavailable."
        if exc.status_code == 404:
            err = ApiError.from_category(ErrorCategory.RESOURCE_NOT_FOUND, "request", request_id=_req_id(request), http_status=404, detail=detail)
        elif exc.status_code == 422:
            err = ApiError.from_category(ErrorCategory.INVALID_REQUEST, "request", request_id=_req_id(request), http_status=422, detail=detail)
        elif exc.status_code == 409:
            err = ApiError.from_category(ErrorCategory.CONFLICT_OR_DUPLICATE_REQUEST, "request", request_id=_req_id(request), http_status=409, detail=detail)
        elif exc.status_code == 403:
            err = ApiError.from_category(ErrorCategory.PERMISSION_OR_PRIVACY_REJECTION, "request", request_id=_req_id(request), http_status=403, detail=detail)
        elif exc.status_code == 503:
            err = ApiError.from_category(ErrorCategory.SERVICE_DEGRADED, "request", request_id=_req_id(request), http_status=503, detail=detail)
        else:
            err = ApiError.from_category(ErrorCategory.BACKEND_PROCESSING_ERROR, "request", request_id=_req_id(request), http_status=exc.status_code, detail=detail)
        return JSONResponse(status_code=exc.status_code, content=err.to_public_dict(include_detail=True))

    @api.exception_handler(Exception)
    async def unexpected_handler(request: Request, exc: Exception):
        import logging
        logging.getLogger("writing_feedback.request").exception(
            "Unhandled error request_id=%s", _req_id(request)
        )
        err = ApiError.from_category(
            ErrorCategory.BACKEND_PROCESSING_ERROR, "request",
            request_id=_req_id(request), http_status=500,
            detail="The operation could not be completed. No secret or internal stack is exposed.",
        )
        return JSONResponse(status_code=500, content=err.to_public_dict(include_detail=True))


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
    research = ResearchDataService(repository)

    lifecycle.application_version = settings.application_version
    lifecycle.prompt_version = settings.prompt_version
    lifecycle.database_status = "connected"
    lifecycle.migration_version = repository.migration_version()
    _apply_analyzer_lifecycle(settings, analyzer)
    lifecycle.llm_provider = settings.llm_provider
    lifecycle.llm_api_configured = bool(settings.deepseek_api_key) if settings.llm_provider == "deepseek" else False
    lifecycle.transition(ServiceState.READY)

    api = FastAPI(title="Writing Feedback API", version="0.8.0")
    _register_request_middleware(api)
    _register_error_handlers(api)
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
    api.state.research = research
    api.state.admin_reanalysis = AdminReanalysisService(repository, settings, configurations, submission_service)

    api.include_router(system.router)
    _include_business_routers(api)
    return api


def create_app(
    settings: Settings | None = None,
    *,
    repository: Database | None = None,
    submission_service: SubmissionService | None = None,
) -> FastAPI:
    """Create the FastAPI application.

    When settings is None (production mode): uses lifespan for lazy init.
    When settings is provided (test mode): builds fully immediately.
    Optional repository and submission_service allow dependency injection.
    """
    if settings is not None or repository is not None or submission_service is not None:
        return _build_full_app(settings, repository=repository, submission_service=submission_service)

    api = FastAPI(
        title="Writing Feedback API",
        version="0.8.0",
        lifespan=_lifespan,
    )
    _register_error_handlers(api)
    _register_request_middleware(api)

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

    api.include_router(system.router)
    return api


app = create_app()
