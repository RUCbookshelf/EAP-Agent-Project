"""Service lifecycle state model for the writing-feedback-mvp.

Provides thread-safe service state tracking, startup stage timing,
and sanitized health information. No database, spaCy, or provider
dependencies -- importable without heavyweight initialization.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ServiceState(str, Enum):
    STARTING = "starting"
    READY = "ready"
    DEGRADED = "degraded"
    FAILED = "failed"
    STOPPING = "stopping"


@dataclass
class StageTiming:
    stage: str
    start_ts: float
    end_ts: float | None = None
    success: bool | None = None
    error_category: str | None = None

    @property
    def elapsed_ms(self) -> float | None:
        if self.end_ts is None:
            return None
        return (self.end_ts - self.start_ts) * 1000


@dataclass
class ServiceLifecycle:
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    state: ServiceState = ServiceState.STARTING
    started_at: float = field(default_factory=time.monotonic)
    ready_at: float | None = None
    stages: list[StageTiming] = field(default_factory=list)
    application_version: str = "unknown"
    migration_version: int | None = None
    active_configuration: str | None = None
    database_status: str = "unknown"
    active_analyzer: str | None = None
    active_analyzer_version: str | None = None
    nlp_model_name: str | None = None
    nlp_model_installed: bool = False
    nlp_model_version: str | None = None
    analyzer_fallback_active: bool = False
    analyzer_fallback_reason: str | None = None
    llm_provider: str | None = None
    llm_api_configured: bool = False
    failed_stage: str | None = None
    failure_category: str | None = None
    degraded_components: list[str] = field(default_factory=list)
    prompt_version: str | None = None
    schema_version: str = "structured-feedback-v0.7.1"

    def transition(self, new_state: ServiceState) -> None:
        with self._lock:
            self.state = new_state
            if new_state == ServiceState.READY and self.ready_at is None:
                self.ready_at = time.monotonic()

    def start_stage(self, name: str) -> StageTiming:
        stage = StageTiming(stage=name, start_ts=time.monotonic())
        with self._lock:
            self.stages.append(stage)
        return stage

    def complete_stage(self, stage: StageTiming, success: bool = True,
                       error_category: str | None = None) -> None:
        stage.end_ts = time.monotonic()
        stage.success = success
        stage.error_category = error_category

    @property
    def startup_elapsed_ms(self) -> float:
        if self.ready_at is not None:
            return (self.ready_at - self.started_at) * 1000
        return (time.monotonic() - self.started_at) * 1000

    def health_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "status": "ok" if self.state in (ServiceState.READY, ServiceState.DEGRADED) else self.state.value,
                "lifecycle_state": self.state.value,
                "application_version": self.application_version,
                "api_version": "v1",
                "database_status": self.database_status,
                "database_migration_version": self.migration_version,
                "prompt_version": self.prompt_version,
                "schema_version": self.schema_version,
                "llm_provider": self.llm_provider,
                "llm_api_configured": self.llm_api_configured,
                "active_analyzer": self.active_analyzer,
                "active_analyzer_version": self.active_analyzer_version,
                "spacy_installed": True,
                "nlp_model_name": self.nlp_model_name,
                "nlp_model_installed": self.nlp_model_installed,
                "nlp_model_version": self.nlp_model_version,
                "analyzer_fallback_active": self.analyzer_fallback_active,
                "analyzer_fallback_reason": self.analyzer_fallback_reason,
                "degraded_components": self.degraded_components,
                "failure_category": self.failure_category,
                "startup_elapsed_ms": round(self.startup_elapsed_ms, 1),
            }


lifecycle = ServiceLifecycle()
