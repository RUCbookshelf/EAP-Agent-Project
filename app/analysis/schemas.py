from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.schemas import utc_now


HumanVerificationStatus = Literal[
    "automatic_unverified", "automatically_cross_checked", "human_reviewed",
    "human_confirmed", "rejected", "not_applicable",
]
MetricConfidence = Literal["high", "medium", "low", "insufficient", "not_applicable"]


class QualityFlag(BaseModel):
    flag_id: str = Field(pattern=r"^Q\d{3}$")
    category: str
    text_span: str
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    confidence: Literal["low", "medium", "high"]
    recommended_action: str


class InputQualityResult(BaseModel):
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    analysis_text_changed: bool = False
    analysis_text_hash: str
    limitations: list[str] = Field(default_factory=list)


class ResourceVersion(BaseModel):
    resource_id: str
    version: str
    content_hash: str | None = None
    limitations: list[str] = Field(default_factory=list)


class AlgorithmVersion(BaseModel):
    algorithm_id: str
    version: str
    implementation: str
    parameter_schema: dict[str, Any] = Field(default_factory=dict)
    compatible_input_versions: list[str] = Field(default_factory=list)
    output_schema_version: str
    status: Literal["active", "experimental", "deprecated"] = "active"
    limitations: list[str] = Field(default_factory=list)


class MetricDefinition(BaseModel):
    metric_id: str
    metric_version: str
    label: str
    unit: str
    value_type: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class MetricResult(BaseModel):
    metric_id: str
    metric_version: str
    value: Any = None
    unit: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    analyzer_version: str
    resource_versions: dict[str, str] = Field(default_factory=dict)
    verification_status: HumanVerificationStatus = "automatic_unverified"
    status: Literal["available", "insufficient_data", "not_applicable"] = "available"
    measurement_status: Literal[
        "available", "insufficient_data", "not_applicable", "research_metric",
        "descriptive_proxy", "automatic_candidate", "manual_annotation_required",
        "unavailable", "deprecated",
    ] = "available"
    automation_level: Literal[
        "deterministic", "rule_based", "parser_dependent",
        "external_resource_dependent", "manual", "hybrid",
    ] | None = None
    construct_id: str | None = None
    subconstruct_id: str | None = None
    analysis_unit_version: str | None = None
    numerator: Any = None
    denominator: Any = None
    intermediate_values: dict[str, Any] = Field(default_factory=dict)
    confidence: MetricConfidence = "insufficient"
    confidence_reasons: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    eligible_for_diagnosis: bool = False
    eligible_for_longitudinal_comparison: bool = False
    eligible_for_revision_priority: bool = False
    eligible_for_targeted_practice: bool = False
    measurement_metadata: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class AnalysisRun(BaseModel):
    analysis_run_id: str | None = None
    essay_id: int | None = None
    analyzer_id: str
    analyzer_version: str
    backend: str
    nlp_library: str | None = None
    nlp_library_version: str | None = None
    nlp_model_name: str | None = None
    nlp_model_version: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    resource_versions: dict[str, str] = Field(default_factory=dict)
    configuration_version: str
    fallback_used: bool = False
    fallback_reason: str | None = None
    analysis_duration_ms: float = Field(ge=0)
    created_at: datetime = Field(default_factory=utc_now)
    limitations: list[str] = Field(default_factory=list)
