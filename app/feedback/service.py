from __future__ import annotations

from app.analyzer import Analyzer, BasicAnalyzer
from app.config import Settings
from app.database import Database
from app.diagnosis import Diagnoser, HeuristicDiagnoser
from app.learner import LearnerHistoryService
from app.llm import DeepSeekProvider, FeedbackContext, LocalDemoProvider, ProviderRouter
from app.models import EssaySubmission, PipelineResult


class FeedbackPipeline:
    def __init__(self, settings: Settings, *, database: Database | None = None,
                 analyzer: Analyzer | None = None, diagnoser: Diagnoser | None = None,
                 router: ProviderRouter | None = None):
        self.settings = settings
        self.database = database or Database(settings.database_path)
        self.analyzer = analyzer or BasicAnalyzer()
        self.diagnoser = diagnoser or HeuristicDiagnoser()
        if router is None:
            local = LocalDemoProvider()
            primary = local if settings.llm_provider == "local" else DeepSeekProvider(
                settings.deepseek_api_key, settings.deepseek_base_url, settings.deepseek_model,
            )
            router = ProviderRouter(primary, local)
        self.router = router
        self.history = LearnerHistoryService(self.database)
        self.database.initialize()
        self.database.record_versions({
            "application": "0.1.1", "analysis": settings.analysis_version,
            "diagnosis": settings.diagnosis_version, "prompt": settings.prompt_version,
            "feedback_schema": "structured-feedback-v0.1.1",
        })

    def submit(self, submission: EssaySubmission, *, synthetic: bool = False) -> PipelineResult:
        essay_id = self.database.save_essay(submission, synthetic=synthetic)
        analysis = self.analyzer.analyze(submission.essay_text)
        self.database.save_analysis(essay_id, analysis)
        diagnosis = self.diagnoser.diagnose(analysis)
        self.database.save_diagnosis(essay_id, diagnosis)
        history = self.history.summarize(essay_id, submission, analysis, diagnosis)
        context = FeedbackContext(submission, analysis, diagnosis, history)
        provider_result = self.router.generate(context)
        self.database.save_feedback(essay_id, provider_result, analysis.analysis_version)
        self.database.save_history(submission.student_id, essay_id, history)
        return PipelineResult(
            essay_id=essay_id, analysis=analysis, diagnosis=diagnosis, provider=provider_result,
            history=history, history_summary=history.summary,
            comparable_history_count=history.comparable_submission_count,
        )
