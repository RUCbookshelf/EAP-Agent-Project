from __future__ import annotations

from app.analyzer import BasicAnalyzer
from app.analysis import AnalyzerCoordinator, AnalyzerRegistry, SpacyAnalyzer, UnavailableAnalyzer
from app.config import Settings
from app.diagnosis import NlpHeuristicDiagnoser
from app.llm import DeepSeekProvider, LocalDemoProvider, ProviderRouter
from .submission import SubmissionRepository, SubmissionService
from .learner_profile import LearnerProfileReadPort, LearnerProfileService
from .progress import ActiveConfigurationPort, LearnerProgressPort, ProgressService
from .revision import RevisionService
from .configuration import settings_from_configuration
from app.repositories import RevisionRepository
from app.calibration import DiagnosticCalibrationService
from app.configuration import ConfigurationPayload
from app.feedback import FeedbackReliabilityService


def build_router(
    settings: Settings, configuration: ConfigurationPayload | None = None,
) -> ProviderRouter:
    local = LocalDemoProvider()
    primary = local if settings.llm_provider == "local" else DeepSeekProvider(
        settings.deepseek_api_key, settings.deepseek_base_url, settings.deepseek_model,
        max_tokens=settings.llm_max_tokens,
    )
    router = ProviderRouter(
        primary, local, reliability=FeedbackReliabilityService(configuration)
    )
    router.temperature = settings.llm_temperature
    return router


def build_analyzer(settings: Settings) -> AnalyzerCoordinator:
    basic = BasicAnalyzer()
    registry = AnalyzerRegistry([basic])
    try:
        spacy_analyzer = SpacyAnalyzer(
            model_name=settings.spacy_model, mattr_window=settings.mattr_window,
            local_repetition_window=settings.local_repetition_window,
            long_sentence_threshold=settings.long_sentence_threshold,
            configuration_version=settings.analysis_configuration_version,
            mtld_threshold=settings.calf_mtld_factor_threshold,
            mtld_calculate_reverse=settings.calf_mtld_calculate_reverse,
            mtld_minimum_tokens=settings.calf_mtld_minimum_tokens,
            hdd_sample_size=settings.calf_hdd_sample_size,
        )
    except Exception as exc:
        spacy_analyzer = UnavailableAnalyzer(
            "spacy", "spacy-analyzer-v0.8.0",
            f"spaCy resource unavailable ({type(exc).__name__}): {str(exc)[:180]}",
        )
    registry.register(spacy_analyzer)
    if settings.active_analyzer not in {item["analyzer_id"] for item in registry.describe()}:
        raise ValueError(f"ACTIVE_ANALYZER is not registered: {settings.active_analyzer}")
    return AnalyzerCoordinator(
        registry, settings.active_analyzer, settings.fallback_analyzer,
        configuration_version=settings.analysis_configuration_version,
    )


def build_submission_service(
    settings: Settings,
    repository: SubmissionRepository,
    *,
    learner_repository: LearnerProgressPort | LearnerProfileReadPort | None = None,
    configuration_repository: ActiveConfigurationPort | None = None,
    revision_repository: RevisionRepository,
) -> SubmissionService:
    learner_dependency = learner_repository if learner_repository is not None else repository
    configuration_dependency = (
        configuration_repository if configuration_repository is not None else repository
    )
    active_configuration = None
    try:
        active_configuration = configuration_dependency.get_active_configuration()
        settings = settings_from_configuration(settings, active_configuration)
    except (LookupError, RuntimeError):
        pass
    progress_service = ProgressService(
        learner_repository=learner_dependency,
        configuration_repository=configuration_dependency,
    )
    profile_service = LearnerProfileService(
        repository=learner_dependency,
        progress_service=progress_service,
    )
    return SubmissionService(
        repository=repository,
        analyzer=build_analyzer(settings),
        diagnoser=NlpHeuristicDiagnoser(),
        router=build_router(settings, active_configuration.payload if active_configuration else None),
        learner_profile_service=profile_service,
        revision_service=RevisionService(revision_repository),
        calibrator=DiagnosticCalibrationService(
            active_configuration.payload if active_configuration else ConfigurationPayload()
        ),
        calf_configuration=active_configuration.payload if active_configuration else ConfigurationPayload(),
    )
