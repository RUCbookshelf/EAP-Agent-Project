"""Admin router: configuration administration, registries, and admin reanalysis."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.deps import get_admin_reanalysis, get_configurations
from app.api.schemas import ConfigurationRollbackRequest, ConfigurationVersion
from app.calibration import DiagnosticCalibrationService
from app.configuration import ConfigurationCreate
from app.feedback import FeedbackReliabilityService
from app.services import ReanalysisRequest
from app.services.configuration import settings_from_configuration
from app.services.factory import build_analyzer

router = APIRouter()


def _apply_runtime_configuration(request: Request, configuration) -> None:
    """Apply an activated configuration to the running API services."""
    state = request.app.state
    effective = settings_from_configuration(state.settings, configuration)
    analyzer = build_analyzer(effective)
    state.analyzer = analyzer
    state.submission_service.analyzer = analyzer
    state.reanalysis.analyzer = analyzer
    state.configurations.registry.analyzers = analyzer.registry
    state.submission_service.router.temperature = configuration.payload.llm_temperature
    state.submission_service.calibrator = DiagnosticCalibrationService(configuration.payload)
    state.submission_service.router.reliability = FeedbackReliabilityService(configuration.payload)
    state.submission_service.calf_configuration = configuration.payload
    if hasattr(state.submission_service.router.primary, "max_tokens"):
        state.submission_service.router.primary.max_tokens = configuration.payload.llm_max_tokens


@router.get("/api/v1/admin/configurations")
def list_configurations(configurations=Depends(get_configurations)) -> dict:
    return {
        "active_configuration_id": configurations.active().configuration_id,
        "configurations": [item.model_dump(mode="json") for item in configurations.list()],
        "audit": configurations.audit(),
        "security_note": "Only non-sensitive research parameters are versioned; local-only administration.",
    }


@router.post("/api/v1/admin/configurations", response_model=ConfigurationVersion, status_code=201)
def create_configuration(
    payload: ConfigurationCreate,
    configurations=Depends(get_configurations),
) -> ConfigurationVersion:
    return configurations.create(payload)


@router.post("/api/v1/admin/configurations/{configuration_id}/validate", response_model=ConfigurationVersion)
def validate_configuration(
    configuration_id: str,
    configurations=Depends(get_configurations),
) -> ConfigurationVersion:
    try:
        return configurations.validate(configuration_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@router.post("/api/v1/admin/configurations/{configuration_id}/activate", response_model=ConfigurationVersion)
def activate_configuration(
    configuration_id: str,
    request: Request,
    configurations=Depends(get_configurations),
) -> ConfigurationVersion:
    try:
        activated = configurations.activate(configuration_id)
        _apply_runtime_configuration(request, activated)
        return activated
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@router.post("/api/v1/admin/configurations/{configuration_id}/rollback", response_model=ConfigurationVersion)
def rollback_configuration(
    configuration_id: str,
    payload: ConfigurationRollbackRequest,
    request: Request,
    configurations=Depends(get_configurations),
) -> ConfigurationVersion:
    try:
        activated = configurations.rollback(configuration_id, reason=payload.reason, actor=payload.actor)
        _apply_runtime_configuration(request, activated)
        return activated
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@router.get("/api/v1/admin/algorithms")
def list_algorithms(configurations=Depends(get_configurations)) -> dict:
    return {"algorithms": configurations.registries()["algorithms"]}


@router.get("/api/v1/admin/metrics")
def list_metrics(configurations=Depends(get_configurations)) -> dict:
    return {"metrics": configurations.registries()["metrics"]}


@router.get("/api/v1/admin/registries")
def list_registries(configurations=Depends(get_configurations)) -> dict:
    return configurations.registries()


@router.post("/api/v1/admin/reanalysis/preview")
def preview_admin_reanalysis(
    payload: ReanalysisRequest,
    admin_reanalysis=Depends(get_admin_reanalysis),
) -> dict:
    try:
        return admin_reanalysis.preview(payload)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@router.post("/api/v1/admin/reanalysis/run")
def run_admin_reanalysis(
    payload: ReanalysisRequest,
    admin_reanalysis=Depends(get_admin_reanalysis),
) -> dict:
    try:
        return admin_reanalysis.run(payload)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
