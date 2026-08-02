from __future__ import annotations

from app.analyzer import Analyzer, BasicAnalyzer
from app.config import Settings
from app.database import Database
from app.diagnosis import Diagnoser, HeuristicDiagnoser
from app.learner import LearnerHistoryService
from app.llm import DeepSeekProvider, FeedbackContext, LocalDemoProvider, ProviderRouter
from app.models import EssaySubmission, PipelineResult
from app.services.submission import SubmissionService
from app.services.learner_profile import LearnerProfileService
from app.services.progress import ProgressService
from app.services.revision import RevisionService


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
            "application": settings.application_version, "analysis": settings.analysis_version,
            "diagnosis": settings.diagnosis_version, "prompt": settings.prompt_version,
            "feedback_schema": "structured-feedback-v0.7.1",
        })
        progress_service = ProgressService(
            learner_repository=self.database._learner_repository,
            configuration_repository=self.database._configuration_repository,
        )
        learner_profile_service = LearnerProfileService(
            repository=self.database._learner_repository,
            progress_service=progress_service,
        )
        self._service = SubmissionService(
            repository=self.database,
            analyzer=self.analyzer,
            diagnoser=self.diagnoser,
            router=self.router,
            learner_profile_service=learner_profile_service,
            revision_service=RevisionService(self.database._revision_repository),
        )

    def submit(self, submission: EssaySubmission, *, synthetic: bool = False) -> PipelineResult:
        return self._service.submit(submission, synthetic=synthetic)
