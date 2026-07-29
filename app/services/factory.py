from __future__ import annotations

from app.analyzer import BasicAnalyzer
from app.config import Settings
from app.diagnosis import HeuristicDiagnoser
from app.llm import DeepSeekProvider, LocalDemoProvider, ProviderRouter
from .submission import SubmissionRepository, SubmissionService
from .learner_profile import LearnerProfileService


def build_router(settings: Settings) -> ProviderRouter:
    local = LocalDemoProvider()
    primary = local if settings.llm_provider == "local" else DeepSeekProvider(
        settings.deepseek_api_key, settings.deepseek_base_url, settings.deepseek_model
    )
    return ProviderRouter(primary, local)


def build_submission_service(
    settings: Settings, repository: SubmissionRepository
) -> SubmissionService:
    profile_service = LearnerProfileService(repository)
    return SubmissionService(
        repository=repository,
        analyzer=BasicAnalyzer(),
        diagnoser=HeuristicDiagnoser(),
        router=build_router(settings),
        learner_profile_service=profile_service,
    )
