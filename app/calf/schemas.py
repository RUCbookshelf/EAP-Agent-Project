from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.models.schemas import utc_now


class ConstructStatus(StrEnum):
    PROTOTYPE = "prototype"
    RESEARCH_READY = "research_ready"
    VALIDATION_PENDING = "validation_pending"
    UNAVAILABLE = "unavailable"
    DEPRECATED = "deprecated"


class MeasurementStatus(StrEnum):
    RESEARCH_METRIC = "research_metric"
    DESCRIPTIVE_PROXY = "descriptive_proxy"
    AUTOMATIC_CANDIDATE = "automatic_candidate"
    MANUAL_ANNOTATION_REQUIRED = "manual_annotation_required"
    UNAVAILABLE = "unavailable"
    DEPRECATED = "deprecated"


class AutomationLevel(StrEnum):
    DETERMINISTIC = "deterministic"
    RULE_BASED = "rule_based"
    PARSER_DEPENDENT = "parser_dependent"
    EXTERNAL_RESOURCE_DEPENDENT = "external_resource_dependent"
    MANUAL = "manual"
    HYBRID = "hybrid"


class MetricLifecycle(StrEnum):
    DRAFT = "draft"
    PROTOTYPE = "prototype"
    ACTIVE_RESEARCH = "active_research"
    VALIDATION_PENDING = "validation_pending"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class UnitValidationStatus(StrEnum):
    AUTOMATIC_CANDIDATE = "automatic_candidate"
    VALIDATED_AUTOMATIC = "validated_automatic"
    HUMAN_CONFIRMED = "human_confirmed"
    REJECTED = "rejected"
    NOT_AVAILABLE = "not_available"


class TimingSource(StrEnum):
    CLIENT_TIMER = "client_timer"
    SERVER_TIMESTAMP = "server_timestamp"
    MANUAL_REPORT = "manual_report"
    IMPORTED = "imported"
    UNKNOWN = "unknown"


class TimingQuality(StrEnum):
    VERIFIED = "verified"
    ESTIMATED = "estimated"
    SELF_REPORTED = "self_reported"
    INCOMPLETE = "incomplete"
    UNAVAILABLE = "unavailable"


class CalfConstruct(BaseModel):
    model_config = ConfigDict(extra="forbid")

    construct_id: str
    display_name: str
    definition: str
    subconstructs: list[str]
    status: ConstructStatus = ConstructStatus.PROTOTYPE
    construct_version: str = "0.8.0"
    interpretation_boundary: str
    reference_ids: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class MeasurementSpecification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_id: str
    metric_version: str
    specification_version: str = "measurement-specification-v0.8.0"
    construct_id: str
    subconstruct_id: str
    display_name: str
    definition: str
    measurement_status: MeasurementStatus
    automation_level: AutomationLevel
    lifecycle: MetricLifecycle
    analysis_unit: str
    analysis_unit_version: str
    formula_description: str
    numerator_description: str | None = None
    denominator_description: str | None = None
    normalization: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    minimum_data_requirements: dict[str, Any]
    input_requirements: list[str] = Field(default_factory=list)
    output_unit: str
    expected_range: dict[str, float | None] | None = None
    direction_is_not_quality: bool = True
    eligible_for_student_feedback: bool = False
    eligible_for_diagnosis: bool = False
    eligible_for_revision_priority: bool = False
    eligible_for_targeted_practice: bool = False
    eligible_for_longitudinal_tracking: bool = False
    version_compatibility_rule: str = "exact"
    analyzer_requirement: str | None = None
    resource_requirements: list[str] = Field(default_factory=list)
    manual_annotation_required: bool = False
    fixture_ids: list[str] = Field(default_factory=list)
    reference_ids: list[str]
    known_limitations: list[str]

    @model_validator(mode="after")
    def research_activation_is_auditable(self) -> "MeasurementSpecification":
        if self.lifecycle == MetricLifecycle.ACTIVE_RESEARCH:
            required = {
                "formula": bool(self.formula_description.strip()),
                "analysis_unit": bool(self.analysis_unit.strip()),
                "minimum_data": bool(self.minimum_data_requirements),
                "fixtures": bool(self.fixture_ids),
                "reference": bool(self.reference_ids),
                "limitations": bool(self.known_limitations),
            }
            missing = [name for name, present in required.items() if not present]
            if missing:
                raise ValueError(f"Active research metric lacks: {', '.join(missing)}")
        return self


class AnalysisUnitDefinition(BaseModel):
    unit_id: str
    unit_version: str
    display_name: str
    generation_method: str
    analyzer_requirement: str | None = None
    parent_unit: str | None = None
    default_validation_status: UnitValidationStatus
    limitations: list[str]


class AnalysisUnitRecord(BaseModel):
    unit_record_id: str | None = None
    submission_id: int | None = None
    analysis_run_id: str | None = None
    unit_id: str
    unit_version: str
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    source_text: str
    source_sentence_id: str | None = None
    parent_unit_record_id: str | None = None
    child_unit_record_ids: list[str] = Field(default_factory=list)
    rule_ids: list[str] = Field(default_factory=list)
    analyzer_id: str
    parser_evidence: dict[str, Any] = Field(default_factory=dict)
    confidence: str
    validation_status: UnitValidationStatus
    annotator_id: str | None = None
    annotation_timestamp: datetime | None = None
    manual_decision: str | None = None
    corrected_start_offset: int | None = Field(default=None, ge=0)
    corrected_end_offset: int | None = Field(default=None, ge=0)
    annotation_guideline_version: str | None = None
    adjudication_status: str | None = None
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def valid_offsets_and_confirmation(self) -> "AnalysisUnitRecord":
        if self.end_offset < self.start_offset:
            raise ValueError("end_offset must not be before start_offset")
        if self.validation_status == UnitValidationStatus.HUMAN_CONFIRMED:
            if not self.annotator_id or not self.annotation_timestamp or self.manual_decision != "accept":
                raise ValueError("Human-confirmed units require annotator, timestamp, and accept decision")
            if self.unit_id not in {"validated_clause", "validated_t_unit", "validated_error_span"}:
                raise ValueError("A candidate unit cannot retain its candidate name after human confirmation")
        return self


class ErrorAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_annotation_id: str | None = Field(default=None, pattern=r"^EA\d{6}$")
    submission_id: int = Field(ge=1)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    original_text: str
    error_category: str
    correction: str | None = None
    annotation_source: str
    annotation_status: str
    annotator_id: str | None = None
    annotation_timestamp: datetime = Field(default_factory=utc_now)
    guideline_version: str
    confidence: str
    adjudication_status: str | None = None

    @model_validator(mode="after")
    def validate_annotation(self) -> "ErrorAnnotation":
        sources = {"human", "imported_corpus", "automatic_candidate", "external_tool", "llm_candidate"}
        if self.annotation_source not in sources:
            raise ValueError("Unsupported annotation_source")
        if self.end_offset <= self.start_offset:
            raise ValueError("Error annotation end_offset must be greater than start_offset")
        if self.annotation_source == "human" and not self.annotator_id:
            raise ValueError("Human annotation requires annotator_id")
        return self

    @computed_field
    @property
    def eligible_for_formal_accuracy(self) -> bool:
        return self.annotation_source in {"human", "imported_corpus"} and self.annotation_status == "confirmed"
