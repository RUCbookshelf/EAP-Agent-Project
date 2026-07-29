from __future__ import annotations

from app.analyzer import BasicAnalyzer
from app.analysis import AnalyzerCoordinator, AnalyzerRegistry, SpacyAnalyzer, UnavailableAnalyzer
from app.config import Settings
from app.diagnosis import NlpHeuristicDiagnoser
from app.llm import DeepSeekProvider, LocalDemoProvider, ProviderRouter
from .submission import SubmissionRepository, SubmissionService
from .learner_profile import LearnerProfileService


def build_router(settings: Settings) -> ProviderRouter:
    local = LocalDemoProvider()
    primary = local if settings.llm_provider == "local" else DeepSeekProvider(
        settings.deepseek_api_key, settings.deepseek_base_url, settings.deepseek_model
    )
    return ProviderRouter(primary, local)


def build_analyzer(settings: Settings) -> AnalyzerCoordinator:
    basic = BasicAnalyzer()
    registry = AnalyzerRegistry([basic])
    try:
        spacy_analyzer = SpacyAnalyzer(
            model_name=settings.spacy_model, mattr_window=settings.mattr_window,
            local_repetition_window=settings.local_repetition_window,
            long_sentence_threshold=settings.long_sentence_threshold,
            configuration_version=settings.analysis_configuration_version,
        )
    except Exception as exc:
        spacy_analyzer = UnavailableAnalyzer(
            "spacy", "spacy-analyzer-v0.4.0",
            f"spaCy resource unavailable ({type(exc).__name__}): {str(exc)[:180]}",
        )
    registry.register(spacy_analyzer)
    if settings.active_analyzer not in {item["analyzer_id"] for item in registry.describe()}:
        raise ValueError(f"ACTIVE_ANALYZER is not registered: {settings.active_analyzer}")
    return AnalyzerCoordinator(registry, settings.active_analyzer, settings.fallback_analyzer)


def build_submission_service(
    settings: Settings, repository: SubmissionRepository
) -> SubmissionService:
    profile_service = LearnerProfileService(repository)
    return SubmissionService(
        repository=repository,
        analyzer=build_analyzer(settings),
        diagnoser=NlpHeuristicDiagnoser(),
        router=build_router(settings),
        learner_profile_service=profile_service,
    )
