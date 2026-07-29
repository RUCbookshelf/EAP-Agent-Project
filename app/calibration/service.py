from __future__ import annotations

from collections import Counter

from app.configuration import ConfigurationPayload
from app.models import AnalysisResult, DiagnosisResult, DiagnosisSignal, EssaySubmission

from .evidence import EvidenceRelevanceValidator
from .schemas import DiagnosticCalibrationResult, MetricConfidenceSummary


CONFIDENCE_VALUE = {"high": 1.0, "medium": 0.65, "low": 0.25, "insufficient": 0.0, "not_applicable": 0.0}


class DiagnosticCalibrationService:
    version = "diagnostic-calibration-v0.6.1"
    gate_version = "diagnostic-gate-v0.6.1"
    priority_version = "diagnostic-priority-v0.6.1"

    def __init__(self, configuration: ConfigurationPayload,
                 evidence: EvidenceRelevanceValidator | None = None) -> None:
        self.configuration = configuration
        self.evidence = evidence or EvidenceRelevanceValidator()

    def calibrate(self, submission: EssaySubmission, analysis: AnalysisResult,
                  raw: DiagnosisResult,
                  prior_selected_categories: set[str] | None = None) -> DiagnosticCalibrationResult:
        prior_selected_categories = prior_selected_categories or set()
        confidence_summary = self._metric_summary(analysis)
        metric_confidence = {
            metric_id: item.get("confidence", "insufficient")
            for metric_id, item in confidence_summary.by_metric.items()
        }
        raw_signals = [
            item.model_copy(update={"signal_id": item.signal_id or f"S{index:03d}", "selection_status": "raw_signal"})
            for index, item in enumerate(raw.raw_signals or raw.all_signals, 1)
        ]
        descriptive = [item for item in raw_signals if item.kind == "descriptive_signal"]
        strengths: list[DiagnosisSignal] = []
        eligible: list[DiagnosisSignal] = []
        monitored: list[DiagnosisSignal] = []
        suppressed: list[DiagnosisSignal] = []

        for signal in raw_signals:
            source_confidences = [metric_confidence.get(metric, "insufficient") for metric in signal.source_metrics]
            best_confidence = max(source_confidences, key=lambda value: CONFIDENCE_VALUE.get(value, 0), default="insufficient")
            relevance, candidates = self.evidence.assess_signal(signal, analysis)
            updated = signal.model_copy(update={
                "metric_confidence": best_confidence,
                "evidence_relevance_status": relevance,
                "evidence_quote_candidates": candidates,
                "evidence_metadata": {
                    **signal.evidence_metadata,
                    "genre_context": submission.genre,
                    "history_category_previously_selected": signal.category in prior_selected_categories,
                },
                "gate_rule": self._gate_rule(signal), "gate_version": self.gate_version,
            })
            if updated.kind == "descriptive_signal":
                continue
            if updated.kind == "strength":
                if relevance == "verified":
                    strengths.append(updated.model_copy(update={
                        "selection_status": "eligible_diagnosis", "gate_result": "admitted",
                        "selection_reason": "A specific text passage supports this observable textual feature.",
                    }))
                else:
                    suppressed.append(self._suppress(updated, "No specific relevant text evidence supports a positive finding."))
                continue
            gated = self._gate_improvement(updated)
            if gated.selection_status == "eligible_diagnosis":
                scored = self._score(gated)
                eligible.append(scored)
            elif gated.selection_status == "monitored_signal":
                monitored.append(gated)
            else:
                suppressed.append(gated)

        selected: list[DiagnosisSignal] = []
        limit = min(2, self.configuration.diagnostic_max_selected_priorities)
        for signal in sorted(eligible, key=lambda item: item.priority_score or 0, reverse=True):
            if len(selected) >= limit:
                suppressed.append(self._suppress(signal, "A higher-priority non-redundant diagnosis was selected."))
                continue
            if any(item.category == signal.category for item in selected):
                components = {**signal.score_components, "redundancy_penalty": -0.5}
                suppressed.append(self._suppress(signal.model_copy(update={"score_components": components}),
                                                  "A higher-priority diagnosis from the same category was selected."))
                continue
            if signal.confidence == "low" or signal.metric_confidence in {"low", "insufficient", "not_applicable"}:
                monitored.append(signal.model_copy(update={
                    "selection_status": "monitored_signal", "gate_result": "monitor",
                    "selection_reason": "Low-confidence evidence is retained for monitoring and not student feedback.",
                }))
                continue
            if (signal.priority_score or 0) < self.configuration.diagnostic_priority_threshold:
                monitored.append(signal.model_copy(update={
                    "selection_status": "monitored_signal", "gate_result": "monitor",
                    "selection_reason": "Priority score did not cross the configured conservative threshold.",
                }))
                continue
            selected.append(signal.model_copy(update={
                "diagnosis_id": f"D{len(selected)+1:03d}", "selection_status": "selected_priority",
                "gate_result": "admitted", "selection_reason": "Evidence, confidence and actionability crossed the configured selection threshold.",
            }))

        selected_strengths = strengths[:1]
        if selected_strengths:
            selected_strengths = [selected_strengths[0].model_copy(update={"diagnosis_id": "D900"})]
        selected_diagnosis = DiagnosisResult(
            strengths=selected_strengths, improvement_priorities=selected,
            descriptive_signals=descriptive, raw_signals=raw_signals,
            monitored_signals=monitored, suppressed_signals=suppressed,
            diagnosis_version="prototype-diagnosis-v0.6.1",
            calibration_version=self.version,
            limitation=(
                "Diagnostic admission and priority are transparent prototype rules, not validated educational or ability judgments."
            ),
        )
        return DiagnosticCalibrationResult(
            analysis_run_id=analysis.analysis_run_id,
            configuration_version=analysis.configuration_version,
            metric_confidence_summary=confidence_summary,
            raw_signals=raw_signals, monitored_signals=monitored,
            eligible_diagnoses=eligible, selected_priorities=selected,
            suppressed_diagnostics=suppressed, verified_strengths=selected_strengths,
            descriptive_signals=descriptive, selected_diagnosis=selected_diagnosis,
            exercise_generation={
                "max_for_high_confidence": self.configuration.exercise_max_for_high_confidence,
                "max_for_medium_confidence": self.configuration.exercise_max_for_medium_confidence,
                "max_for_low_confidence": self.configuration.exercise_max_for_low_confidence,
                "allow_for_monitored_signal": self.configuration.exercise_allow_for_monitored_signal,
            },
            limitations=[
                "All thresholds are unvalidated prototype defaults requiring literature and human calibration.",
                "Priority score is a workflow ranking, never a student ability or writing-quality score.",
            ],
        )

    def _gate_improvement(self, signal: DiagnosisSignal) -> DiagnosisSignal:
        if signal.evidence_relevance_status in {"irrelevant", "insufficient_evidence"}:
            return self._suppress(signal, "Specific evidence relevance was not verified.", insufficient=True)
        if signal.category == "lexical_repetition":
            data = signal.evidence_metadata
            count = int(data.get("count", 0)); density = float(data.get("density", 0))
            local = bool(data.get("local_cluster_detected"))
            penalized_term = bool(data.get("is_prompt_keyword") or data.get("is_necessary_task_term_candidate"))
            eligible = local or (
                count >= self.configuration.lexical_repetition_minimum_count
                and density >= self.configuration.lexical_repetition_minimum_density
                and not penalized_term
            )
            if not eligible:
                return signal.model_copy(update={
                    "selection_status": "monitored_signal", "gate_result": "monitor",
                    "selection_reason": "Distributed or task-related repetition did not meet the conservative count/density/local-cluster rule.",
                    "exclusion_reasons": ["No verified local cluster and conservative repetition thresholds were not jointly met."],
                })
        if signal.category == "connective_use" and not signal.evidence_metadata.get("specific_location"):
            return signal.model_copy(update={
                "selection_status": "monitored_signal", "gate_result": "monitor",
                "selection_reason": "Dictionary counts alone cannot establish a cohesion problem.",
                "exclusion_reasons": ["No specific adjacent-sentence or paragraph-boundary location was verified."],
            })
        if signal.category == "connective_use" and len(signal.evidence_metadata.get("function_categories", {})) >= 3:
            return signal.model_copy(update={
                "selection_status": "monitored_signal", "gate_result": "monitor",
                "selection_reason": "Several explicit connective functions were detected, so the isolated boundary candidate is not promoted automatically.",
                "exclusion_reasons": ["Multiple detected connective functions lower the priority of a dictionary-based concern."],
            })
        return signal.model_copy(update={"selection_status": "eligible_diagnosis", "gate_result": "admitted"})

    def _score(self, signal: DiagnosisSignal) -> DiagnosisSignal:
        data = signal.evidence_metadata
        components = {
            "evidence_strength": 1.0 if signal.evidence_relevance_status == "verified" else 0.4,
            "metric_confidence": CONFIDENCE_VALUE.get(signal.metric_confidence, 0.0),
            "diagnosis_confidence": CONFIDENCE_VALUE.get(signal.confidence, 0.0),
            "local_concentration": 1.0 if data.get("local_cluster_detected") else 0.3,
            "frequency_or_magnitude": min(1.0, float(data.get("density", data.get("magnitude", 0.5))) * 10),
            "actionability": 0.85 if signal.category in {"lexical_repetition", "sentence_structure_candidate"} else 0.65,
            "pedagogical_value": 0.7,
            "history_relevance": 0.8 if data.get("history_category_previously_selected") else 0.0,
            "genre_context": 0.5,
            "evidence_location_verified": 1.0 if signal.evidence_relevance_status == "verified" else 0.0,
            "redundancy_penalty": 0.0,
            "prompt_term_penalty": -self.configuration.lexical_repetition_prompt_keyword_penalty if data.get("is_prompt_keyword") else 0.0,
            "necessary_term_penalty": -self.configuration.lexical_repetition_necessary_term_penalty if data.get("is_necessary_task_term_candidate") else 0.0,
            "low_confidence_penalty": -0.3 if signal.confidence == "low" else 0.0,
        }
        positive = ["evidence_strength", "metric_confidence", "diagnosis_confidence", "local_concentration",
                    "frequency_or_magnitude", "actionability", "pedagogical_value", "history_relevance", "genre_context",
                    "evidence_location_verified"]
        score = sum(components[name] for name in positive) / len(positive)
        score += components["prompt_term_penalty"] + components["necessary_term_penalty"] + components["low_confidence_penalty"]
        return signal.model_copy(update={"priority_score": round(max(0.0, min(1.0, score)), 4), "score_components": components})

    def _gate_rule(self, signal: DiagnosisSignal) -> str:
        return {
            "lexical_repetition": "lexical-repetition-gate-v0.6.1",
            "connective_use": "connective-specific-location-gate-v0.6.1",
            "sentence_structure_candidate": "parser-candidate-gate-v0.6.1",
            "input_quality": "input-quality-span-gate-v0.6.1",
        }.get(signal.category, "general-evidence-gate-v0.6.1")

    @staticmethod
    def _suppress(signal: DiagnosisSignal, reason: str, *, insufficient: bool = False) -> DiagnosisSignal:
        return signal.model_copy(update={
            "selection_status": "insufficient_evidence" if insufficient else "suppressed",
            "gate_result": "excluded", "selection_reason": reason,
            "exclusion_reasons": [*signal.exclusion_reasons, reason],
        })

    @staticmethod
    def _metric_summary(analysis: AnalysisResult) -> MetricConfidenceSummary:
        by_metric = {
            item["metric_id"]: {
                "metric_version": item["metric_version"], "measurement_status": item.get("measurement_status", item.get("status")),
                "confidence": item.get("confidence", "insufficient"),
                "confidence_reasons": item.get("confidence_reasons", []), "risk_factors": item.get("risk_factors", []),
                "eligible_for_diagnosis": item.get("eligible_for_diagnosis", False),
                "eligible_for_longitudinal_comparison": item.get("eligible_for_longitudinal_comparison", False),
                "limitations": item.get("limitations", []),
            }
            for item in analysis.metric_results
        }
        return MetricConfidenceSummary(by_metric=by_metric, counts=dict(Counter(item["confidence"] for item in by_metric.values())))
