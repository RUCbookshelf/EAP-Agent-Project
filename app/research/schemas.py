from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.schemas import utc_now


class ExportSchemaVersion(StrEnum):
    V0_1 = 'research-export-v0.1'


class PrivacyMode(StrEnum):
    INTERNAL_RESEARCH = 'internal_research'
    PSEUDONYMIZED = 'pseudonymized'
    MINIMAL_ANONYMOUS = 'minimal_anonymous'


class ExportFormat(StrEnum):
    JSONL = 'jsonl'
    CSV = 'csv'


class ExportJobStatus(StrEnum):
    PREVIEW = 'preview'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'


class PiiCategory(StrEnum):
    PERSON = 'person'
    EMAIL = 'email'
    PHONE = 'phone'
    INSTITUTION = 'institution'
    LOCATION = 'location'
    STUDENT_ID = 'student_id'
    SOCIAL_HANDLE = 'social_handle'


class PiiReviewStatus(StrEnum):
    CANDIDATE = 'candidate'
    CONFIRMED = 'confirmed'
    REJECTED = 'rejected'
    REDACTED = 'redacted'


class PiiAction(StrEnum):
    CONFIRM = 'confirm'
    REJECT = 'reject'
    REDACT = 'redact'


class HumanReviewDecision(StrEnum):
    CORRECT = 'correct'
    PARTIALLY_CORRECT = 'partially_correct'
    INCORRECT = 'incorrect'
    UNCERTAIN = 'uncertain'
    NOT_REVIEWED = 'not_reviewed'
    NOT_APPLICABLE = 'not_applicable'


class HumanReviewTarget(StrEnum):
    DIAGNOSIS = 'diagnosis'
    EVIDENCE = 'evidence'
    FEEDBACK = 'feedback'
    REVISION = 'revision'
    TASK_COMPARABILITY = 'task_comparability'


class HumanReviewStatus(StrEnum):
    DRAFT = 'draft'
    COMPLETED = 'completed'
    SUPERSEDED = 'superseded'


class DataQualityCategory(StrEnum):
    COMPLETE = 'complete'
    PARTIALLY_COMPLETE = 'partially_complete'
    MISSING = 'missing'
    EXCLUDED = 'excluded'
    REVIEW_REQUIRED = 'review_required'
    UNAVAILABLE = 'unavailable'



class ExportRecord(BaseModel):
    model_config = ConfigDict(extra='forbid')
    export_schema_version: str = ExportSchemaVersion.V0_1.value
    record_type: str
    record_id: str
    source_database_id: int | str | None = None
    student_pseudonym: str | None = None
    submission_id: int | None = None
    revision_group_id: str | None = None
    task_cluster_id: str | None = None
    analysis_run_id: str | None = None
    algorithm_version: str | None = None
    configuration_version: str | None = None
    source_timestamp: str | None = None
    export_timestamp: str = Field(default_factory=lambda: utc_now().isoformat())
    data_origin: str = 'system_generated'
    inclusion_status: str = 'included'
    exclusion_reason: str | None = None
    limitations: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)


class ExportFilter(BaseModel):
    model_config = ConfigDict(extra='forbid')
    student_ids: list[str] | None = None
    pseudonyms: list[str] | None = None
    date_from: str | None = None
    date_to: str | None = None
    genres: list[str] | None = None
    draft_stages: list[str] | None = None
    revision_group_ids: list[str] | None = None
    independent_tasks_only: bool | None = None
    task_cluster_ids: list[str] | None = None
    timed_only: bool | None = None
    tool_use: list[str] | None = None
    analyzer_versions: list[str] | None = None
    metric_versions: list[str] | None = None
    diagnostic_statuses: list[str] | None = None
    providers: list[str] | None = None
    fallback_status: str | None = None
    human_review_status: str | None = None
    data_sufficiency_status: str | None = None
    privacy_mode: PrivacyMode = PrivacyMode.PSEUDONYMIZED
    formats: list[ExportFormat] = Field(default_factory=lambda: [ExportFormat.JSONL])


class ExportJob(BaseModel):
    model_config = ConfigDict(extra='forbid')
    export_id: str | None = Field(default=None, pattern=r'^EXP\d{6}$')
    export_schema_version: str = ExportSchemaVersion.V0_1.value
    filter_spec: ExportFilter
    privacy_mode: PrivacyMode
    formats: list[ExportFormat]
    status: ExportJobStatus = ExportJobStatus.PREVIEW
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    completed_at: str | None = None
    export_directory: str | None = None
    file_count: int = 0
    record_counts: dict[str, int] = Field(default_factory=dict)
    excluded_counts: dict[str, int] = Field(default_factory=dict)
    manifest_path: str | None = None


class ExportManifest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    export_id: str = Field(pattern=r'^EXP\d{6}$')
    export_schema_version: str = ExportSchemaVersion.V0_1.value
    created_at: str
    application_version: str = '0.8.2'
    git_commit: str | None = None
    database_migration_version: int | None = None
    active_configuration_version: str | None = None
    analyzer_version: str | None = None
    metric_registry_version: str | None = None
    calf_registry_version: str | None = None
    diagnostic_gate_version: str | None = None
    feedback_prompt_version: str | None = None
    export_formats: list[str]
    export_scope: str
    applied_filters: dict[str, Any]
    included_record_counts: dict[str, int]
    excluded_record_counts: dict[str, int]
    privacy_mode: str
    removed_fields: list[str]
    generalized_fields: list[str]
    pseudonym_strategy: str | None = None
    hashing_strategy: str | None = None
    random_seed: int | None = None
    files: list[dict[str, str]]
    known_limitations: list[str] = Field(default_factory=list)



class PiiCandidate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    pii_candidate_id: str | None = Field(default=None, pattern=r'^PII\d{6}$')
    submission_id: int = Field(ge=1)
    category: PiiCategory
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    matched_text: str
    confidence: str = 'medium'
    rule_id: str
    review_status: PiiReviewStatus = PiiReviewStatus.CANDIDATE
    action: PiiAction | None = None
    reviewer_id: str | None = None
    reviewed_at: str | None = None
    replacement_marker: str | None = None


class PiiReview(BaseModel):
    model_config = ConfigDict(extra='forbid')
    pii_candidate_id: str
    action: PiiAction
    reviewer_id: str
    reviewed_at: str = Field(default_factory=lambda: utc_now().isoformat())


class HumanReviewCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    target_type: HumanReviewTarget
    target_id: str
    reviewer_id: str = Field(min_length=1, max_length=100)
    decision: HumanReviewDecision
    confidence: str = 'medium'
    reason_code: str | None = None
    comment: str = ''
    guideline_version: str = 'human-review-v0.1'


class HumanReview(BaseModel):
    model_config = ConfigDict(extra='forbid')
    review_id: str | None = Field(default=None, pattern=r'^HR\d{6}$')
    target_type: HumanReviewTarget
    target_id: str
    reviewer_id: str
    decision: HumanReviewDecision
    confidence: str
    reason_code: str | None = None
    comment: str
    guideline_version: str
    review_status: HumanReviewStatus = HumanReviewStatus.COMPLETED
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    updated_at: str | None = None
    superseded_by: str | None = None
    source_system_result_snapshot: dict[str, Any] | None = None


class DataQualityItem(BaseModel):
    model_config = ConfigDict(extra='forbid')
    category: str
    status: DataQualityCategory
    count: int = 0
    record_ids: list[str] = Field(default_factory=list)
    description: str = ''


class DataQualityReport(BaseModel):
    model_config = ConfigDict(extra='forbid')
    report_id: str | None = Field(default=None, pattern=r'^DQ\d{6}$')
    export_id: str | None = None
    generated_at: str = Field(default_factory=lambda: utc_now().isoformat())
    items: list[DataQualityItem] = Field(default_factory=list)
    summary: str = ''
    limitations: list[str] = Field(default_factory=list)


class DatasetSplitRecord(BaseModel):
    student_pseudonym: str
    split: Literal['train', 'validation', 'test']
    submission_count: int = 0


class DatasetSplitManifest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    split_id: str | None = Field(default=None, pattern=r'^DS\d{6}$')
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    random_seed: int
    train_ratio: float = Field(gt=0, lt=1)
    validation_ratio: float = Field(gt=0, lt=1)
    test_ratio: float = Field(gt=0, lt=1)
    student_count: int = 0
    train_count: int = 0
    validation_count: int = 0
    test_count: int = 0
    rounding_behavior: str = 'floor_with_remainder_to_train'
    records: list[DatasetSplitRecord] = Field(default_factory=list)
    interpretation_boundary: str = (
        'This dataset split is infrastructure only and does not indicate that '
        'the exported data are suitable for model training.'
    )


class ResearchExportSchema(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: str = ExportSchemaVersion.V0_1.value
    record_types: list[str] = Field(default_factory=lambda: [
        'submission', 'analysis_run', 'metric_result', 'calf_metric_result',
        'diagnostic_signal', 'selected_revision_priority', 'feedback',
        'targeted_practice', 'revision_comparison', 'learner_profile_snapshot',
        'history_evidence', 'provider_execution_metadata', 'human_review_annotation',
    ])
    required_fields: list[str] = Field(default_factory=lambda: [
        'export_schema_version', 'record_type', 'record_id', 'source_database_id',
        'student_pseudonym', 'export_timestamp', 'data_origin',
    ])
    export_formats: list[str] = Field(default_factory=lambda: ['jsonl', 'csv', 'manifest'])
    privacy_modes: list[str] = Field(default_factory=lambda: ['internal_research', 'pseudonymized', 'minimal_anonymous'])
    interpretation_boundary: str = (
        'Exported records are prototype research data. They are not training-ready data, '
        'gold-standard annotations, or validated measurements. Human review records are '
        'expert opinion, not ground truth.'
    )
