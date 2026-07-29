from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.schemas import DiagnosisResult, DiagnosisSignal, utc_now


class MetricConfidenceSummary(BaseModel):
    by_metric: dict[str, dict[str, Any]] = Field(default_factory=dict)
    counts: dict[str, int] = Field(default_factory=dict)


class DiagnosticCalibrationResult(BaseModel):
    calibration_id: str | None = None
    essay_id: int | None = None
    analysis_run_id: str | None = None
    calibration_version: str = "diagnostic-calibration-v0.6.1"
    gate_version: str = "diagnostic-gate-v0.6.1"
    priority_version: str = "diagnostic-priority-v0.6.1"
    evidence_validation_version: str = "evidence-relevance-v0.6.1"
    diagnosis_version: str = "prototype-diagnosis-v0.6.1"
    configuration_version: str
    metric_confidence_summary: MetricConfidenceSummary
    raw_signals: list[DiagnosisSignal] = Field(default_factory=list)
    monitored_signals: list[DiagnosisSignal] = Field(default_factory=list)
    eligible_diagnoses: list[DiagnosisSignal] = Field(default_factory=list)
    selected_priorities: list[DiagnosisSignal] = Field(default_factory=list, max_length=2)
    suppressed_diagnostics: list[DiagnosisSignal] = Field(default_factory=list)
    verified_strengths: list[DiagnosisSignal] = Field(default_factory=list, max_length=1)
    descriptive_signals: list[DiagnosisSignal] = Field(default_factory=list)
    exercise_generation: dict[str, int | bool] = Field(default_factory=dict)
    selected_diagnosis: DiagnosisResult
    limitations: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

    def prompt_payload(self) -> dict[str, Any]:
        return {
            "selected_priorities": [item.model_dump(mode="json") for item in self.selected_priorities],
            "verified_strengths": [item.model_dump(mode="json") for item in self.verified_strengths],
            "descriptive_signals": [item.model_dump(mode="json") for item in self.descriptive_signals],
            "monitored_signal_summary": [
                {"category": item.category, "selection_reason": item.selection_reason}
                for item in self.monitored_signals
            ],
            "metric_confidence_summary": self.metric_confidence_summary.model_dump(mode="json"),
            "analysis_limitations": self.limitations,
            "exercise_generation": self.exercise_generation,
            "gate_version": self.gate_version,
            "priority_version": self.priority_version,
            "evidence_validation_version": self.evidence_validation_version,
            "configuration_version": self.configuration_version,
        }
