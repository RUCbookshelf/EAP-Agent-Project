from __future__ import annotations

from app.analyzer import Analyzer
from app.diagnosis import Diagnoser
from app.learner import LearnerHistoryService
from app.llm import FeedbackContext, ProviderRouter
from app.models import EssaySubmission, PipelineResult
from app.repositories import (
    DiagnosisRepository,
    EssayRepository,
    FeedbackRepository,
    LearnerHistoryRepository,
    MetricRepository,
    SystemVersionRepository,
)


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
    ) -> None:
        self.repository = repository
        self.analyzer = analyzer
        self.diagnoser = diagnoser
        self.router = router
        self.history = LearnerHistoryService(repository)
        self.repository.record_versions({
            "application": "0.2.0",
            "analysis": getattr(analyzer, "version", "unknown"),
            "diagnosis": getattr(diagnoser, "version", "unknown"),
            "feedback_schema": "structured-feedback-v0.1.1",
            "api": "v1",
        })

    def submit(self, submission: EssaySubmission, *, synthetic: bool = False) -> PipelineResult:
        essay_id = self.repository.save_essay(submission, synthetic=synthetic)
        analysis = self.analyzer.analyze(submission.essay_text)
        self.repository.save_analysis(essay_id, analysis)
        diagnosis = self.diagnoser.diagnose(analysis)
        self.repository.save_diagnosis(essay_id, diagnosis)
        history = self.history.summarize(essay_id, submission, analysis, diagnosis)
        context = FeedbackContext(submission, analysis, diagnosis, history)
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
        )
