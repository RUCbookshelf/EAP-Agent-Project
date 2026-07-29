from __future__ import annotations

from app.analyzer import Analyzer
from app.diagnosis import Diagnoser
from app.learner import LearnerHistoryService
from app.llm import FeedbackContext, ProviderRouter
from app.models import AnalysisResult, DiagnosisResult, EssaySubmission, HistoryResult, PipelineResult
from app.repositories import (
    DiagnosisRepository,
    EssayRepository,
    FeedbackRepository,
    LearnerHistoryRepository,
    MetricRepository,
    SystemVersionRepository,
)
from typing import TYPE_CHECKING
from app.calibration import DiagnosticCalibrationService

if TYPE_CHECKING:
    from app.services.learner_profile import LearnerProfileService
    from app.services.revision import RevisionService


class SubmissionRepository(
    EssayRepository,
    MetricRepository,
    DiagnosisRepository,
    FeedbackRepository,
    LearnerHistoryRepository,
    SystemVersionRepository,
):
    """Combined structural contract for the atomic submission workflow."""


class SubmissionService:
    """Framework-neutral application service for the protected feedback workflow."""

    def __init__(
        self,
        repository: SubmissionRepository,
        analyzer: Analyzer,
        diagnoser: Diagnoser,
        router: ProviderRouter,
        learner_profile_service: "LearnerProfileService | None" = None,
        revision_service: "RevisionService | None" = None,
        calibrator: DiagnosticCalibrationService | None = None,
    ) -> None:
        self.repository = repository
        self.analyzer = analyzer
        self.diagnoser = diagnoser
        self.router = router
        self.history = LearnerHistoryService(repository)
        self.learner_profile_service = learner_profile_service
        self.revision_service = revision_service
        self.calibrator = calibrator
        self.repository.record_versions({
            "application": "0.7.0",
            "analysis": getattr(analyzer, "version", "unknown"),
            "diagnosis": getattr(diagnoser, "version", "unknown"),
            "diagnostic_calibration": "diagnostic-calibration-v0.6.1",
            "feedback_schema": "structured-feedback-v0.7.0",
            "api": "v1",
            "metric_registry": "metric-registry-v0.6.1",
            "revision": "revision-analysis-v0.5.0",
            "configuration": "configuration-schema-v0.7.0",
            "learner_model": "learner-profile-v0.7.0",
            "visualization": "progress-visualization-data-v0.6.0",
        })

    def submit(self, submission: EssaySubmission, *, synthetic: bool = False) -> PipelineResult:
        if submission.revision_of_submission_id is not None:
            if self.revision_service is None:
                raise ValueError("Revision workflow is not configured.")
            self.revision_service.validate_relationship(
                submission.revision_of_submission_id, None, target_student_id=submission.student_id,
            )
        essay_id = self.repository.save_essay(submission, synthetic=synthetic)
        analysis = self.analyzer.analyze(
            submission.essay_text, writing_prompt=submission.writing_prompt,
            draft_stage=submission.draft_stage, tool_use=submission.tool_use,
        )
        analysis = self.repository.save_analysis_run(essay_id, analysis)
        self.repository.save_analysis(essay_id, analysis)
        raw_diagnosis = self.diagnoser.diagnose(analysis)
        prior_selected_categories: set[str] = set()
        if self.calibrator:
            for prior in self.repository.prior_records(submission):
                if prior.get("genre") != submission.genre:
                    continue
                diagnosis = prior.get("diagnosis") or {}
                prior_selected_categories.update(
                    item.get("category", "") for item in diagnosis.get("improvement_priorities", [])
                    if item.get("category")
                )
        calibration = (
            self.calibrator.calibrate(
                submission, analysis, raw_diagnosis,
                prior_selected_categories=prior_selected_categories,
            )
            if self.calibrator else None
        )
        diagnosis = calibration.selected_diagnosis if calibration else raw_diagnosis
        self.repository.save_diagnosis(essay_id, diagnosis)
        if calibration is not None and hasattr(self.repository, "save_diagnostic_calibration"):
            calibration = self.repository.save_diagnostic_calibration(essay_id, calibration)
        revision_snapshot = None
        if submission.revision_of_submission_id is not None and self.revision_service is not None:
            revision_snapshot = self.revision_service.create_relationship(
                submission.revision_of_submission_id, essay_id,
            )
        history = self.history.summarize(essay_id, submission, analysis, diagnosis)
        snapshot = None
        if self.learner_profile_service is not None:
            snapshot = self.learner_profile_service.recalculate(submission.student_id)
            history = self.learner_profile_service.progress.enrich_history(history, snapshot)
        context = FeedbackContext(
            submission, analysis, diagnosis, history, snapshot, revision_snapshot,
            calibration.prompt_payload() if calibration else None,
        )
        provider_result = self.router.generate(context)
        self.repository.save_feedback(essay_id, provider_result, analysis.analysis_version)
        self.repository.save_history(submission.student_id, essay_id, history)
        return PipelineResult(
            essay_id=essay_id,
            analysis=analysis,
            diagnosis=diagnosis,
            provider=provider_result,
            history=history,
            history_summary=history.summary,
            comparable_history_count=history.comparable_submission_count,
            revision_snapshot=revision_snapshot,
            diagnostic_calibration=calibration,
        )

    def regenerate_feedback(self, essay_id: int, analysis: AnalysisResult):
        """Explicit, auditable LLM path for an existing essay; never creates or overwrites the essay."""
        row = self.repository.get_submission_bundle(essay_id)
        if row is None:
            raise LookupError("Submission not found.")
        if not row.get("diagnosis"):
            raise ValueError("Stored structured diagnosis is unavailable.")
        submission = EssaySubmission.model_validate({
            name: row[name] for name in EssaySubmission.model_fields if name in row
        })
        history = HistoryResult(
            comparability_status=row.get("comparability_status") or "insufficient_history",
            comparable_submission_count=int(row.get("comparable_count") or 0),
            history_evidence=row.get("history_evidence") or [],
            summary=row.get("history_summary") or "数据不足，无法判断趋势。",
            limitations=row.get("limitations") or ["Historical evidence is unavailable."],
            comparability_reasons=row.get("comparability_reasons") or ["No stored comparable history."],
        )
        profile = (
            self.learner_profile_service.latest_or_recalculate(submission.student_id)
            if self.learner_profile_service else None
        )
        revision_snapshot = None
        if self.revision_service and row.get("revision_group_id"):
            latest = self.revision_service.latest(row["revision_group_id"])
            if latest.target_submission_id == essay_id:
                revision_snapshot = latest
        calibration = self.repository.get_diagnostic_calibration(essay_id) if hasattr(self.repository, "get_diagnostic_calibration") else None
        context = FeedbackContext(
            submission, analysis, DiagnosisResult.model_validate(row["diagnosis"]), history,
            profile, revision_snapshot, calibration.prompt_payload() if calibration else None,
        )
        result = self.router.generate(context)
        self.repository.save_feedback(essay_id, result, analysis.analysis_version)
        return result
