from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.schemas import utc_now


ConfigurationStatus = Literal["draft", "validated", "active", "inactive", "archived"]


class ConfigurationPayload(BaseModel):
    """Versioned, deliberately non-sensitive research parameters."""

    model_config = ConfigDict(extra="forbid")

    active_analyzer: Literal["spacy", "basic"] = "spacy"
    fallback_analyzer: Literal["basic"] = "basic"
    mattr_window: int = Field(default=50, ge=10, le=500)
    local_repetition_window: int = Field(default=30, ge=5, le=200)
    long_sentence_threshold: int = Field(default=30, ge=10, le=100)
    prompt_keyword_weight: float = Field(default=0.35, ge=0, le=1)
    repetition_threshold: int = Field(default=3, ge=2, le=20)
    connective_resource_version: str = Field(default="connectives-v0.4.0", min_length=1, max_length=100)
    comparability_rule_version: str = Field(default="comparability-v0.3.0", min_length=1, max_length=100)
    minimum_baseline_points: int = Field(default=3, ge=2, le=20)
    persistent_threshold: int = Field(default=3, ge=2, le=20)
    recently_reduced_window: int = Field(default=2, ge=1, le=10)
    trend_relative_change: float = Field(default=0.10, ge=0.01, le=1)
    low_variability_cv: float = Field(default=0.10, ge=0, le=2)
    high_variability_cv: float = Field(default=0.30, ge=0, le=3)
    feedback_priority_count: int = Field(default=2, ge=1, le=3)
    llm_temperature: float = Field(default=0.2, ge=0, le=2)
    llm_max_tokens: int = Field(default=1800, ge=128, le=8192)
    active_prompt_version: Literal[
        "feedback-prompt-v0.3.0", "feedback-prompt-v0.4.0", "feedback-prompt-v0.5.0"
    ] = "feedback-prompt-v0.5.0"
    revision_alignment_version: Literal["local-sequence-alignment-v0.5.0"] = "local-sequence-alignment-v0.5.0"
    uptake_rule_version: Literal["feedback-uptake-v0.5.0"] = "feedback-uptake-v0.5.0"

    @model_validator(mode="after")
    def ordered_variability_thresholds(self) -> "ConfigurationPayload":
        if self.low_variability_cv >= self.high_variability_cv:
            raise ValueError("low_variability_cv must be below high_variability_cv")
        return self


class ConfigurationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payload: ConfigurationPayload
    change_note: str = Field(min_length=3, max_length=500)
    created_by: str = Field(default="local_researcher", min_length=1, max_length=100)


class ConfigurationVersion(BaseModel):
    configuration_id: str = Field(pattern=r"^CFG\d{6}$")
    version: str = Field(pattern=r"^config-v0\.6\.\d+$")
    status: ConfigurationStatus
    created_at: datetime = Field(default_factory=utc_now)
    created_by: str
    parent_version: str | None = None
    payload: ConfigurationPayload
    schema_version: str = "configuration-schema-v0.6.0"
    change_note: str
    validation_status: Literal["not_validated", "passed", "failed"] = "not_validated"
    validation_errors: list[str] = Field(default_factory=list)
    activated_at: datetime | None = None
    deactivated_at: datetime | None = None
    content_hash: str


class ConfigurationAudit(BaseModel):
    audit_id: str = Field(pattern=r"^CA\d{6}$")
    configuration_id: str
    action: Literal["create", "validate", "activate", "rollback"]
    actor: str
    reason: str
    created_at: datetime
    details: dict = Field(default_factory=dict)


def configuration_hash(payload: ConfigurationPayload) -> str:
    canonical = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()
