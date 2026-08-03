"""System router: lifecycle and version endpoints (v0.9.5-B canonical health)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import (
    get_analyzer,
    get_configurations,
    get_metrics,
    get_settings,
    get_submission_service,
    get_system_migration_reader,
)
from app.api.schemas import HealthResponse, VersionResponse
from app.lifecycle import ServiceState, lifecycle

router = APIRouter()


@router.get("/api/v1/system/live")
def liveness():
    return {"status": "ok", "lifecycle_state": lifecycle.state.value}


@router.get("/api/v1/system/ready")
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


@router.get("/api/v1/system/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Canonical lifecycle-based health representation (single registration)."""
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


@router.get("/api/v1/system/version", response_model=VersionResponse)
def version(
    settings=Depends(get_settings),
    migration_reader=Depends(get_system_migration_reader),
    analyzer=Depends(get_analyzer),
    metrics=Depends(get_metrics),
    configurations=Depends(get_configurations),
    submission_service=Depends(get_submission_service),
) -> VersionResponse:
    registry_versions: dict[str, list[str]] = {}
    for metric in metrics.list():
        registry_versions.setdefault(metric.metric_id, []).append(metric.metric_version)
    active_configuration = configurations.active()
    return VersionResponse(
        application_version=settings.application_version, api_version=settings.api_version,
        prompt_version=active_configuration.payload.active_prompt_version, schema_version="structured-feedback-v0.7.1",
        analysis_version=settings.analysis_version, diagnosis_version=settings.diagnosis_version,
        database_migration_version=migration_reader.migration_version(),
        active_analyzer=getattr(analyzer, "active_analyzer", getattr(analyzer, "analyzer_id", "unknown")),
        nlp_library_version=getattr(getattr(analyzer, "registry", None).get("spacy"), "spacy", None).__version__ if getattr(analyzer, "registry", None) and hasattr(getattr(analyzer, "registry", None).get("spacy"), "spacy") else None,
        nlp_model_name=settings.spacy_model,
        nlp_model_version=getattr(getattr(analyzer, "registry", None).get("spacy"), "model_version", None) if getattr(analyzer, "registry", None) else None,
        metric_versions=registry_versions,
        provider=getattr(submission_service.router.primary, "provider_name", settings.llm_provider),
        model=getattr(submission_service.router.primary, "model_name", settings.deepseek_model),
        active_configuration_version=active_configuration.version,
    )
