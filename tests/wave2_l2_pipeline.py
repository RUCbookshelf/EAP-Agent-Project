"""Shared Wave-2 Goal C test helper: build the REAL existing pipeline.

The revision loop and personalized bridge must call the existing
Writing Intelligence pipeline (analyzer -> diagnosis -> feedback router ->
revision relationships -> history), never a disconnected revision-only
service. This helper constructs the real services exactly like the existing
composition root (``app.services.factory.build_submission_service``) with a
deterministic regex analyzer and the local demo provider.
"""

from __future__ import annotations

from app.calibration import DiagnosticCalibrationService
from app.config import Settings
from app.configuration import ConfigurationPayload
from app.database import Database
from app.diagnosis import HeuristicDiagnoser
from app.feedback import FeedbackReliabilityService
from app.llm import LocalDemoProvider, ProviderRouter
from app.l2.wave2.pipeline import ExistingWritingPipeline
from app.services import (
    LearnerProfileService,
    ProgressService,
    ReanalysisService,
    RevisionService,
    SubmissionService,
)
from app.services.factory import build_analyzer


def build_real_pipeline(tmp_path, *, database_name: str = "wave2.db"):
    """Return (pipeline, repository, submission_service) with the real pipeline."""
    settings = Settings(
        database_path=tmp_path / database_name,
        llm_provider="local",
        deepseek_api_key=None,
        deepseek_base_url="https://example.invalid",
        deepseek_model="deepseek-test",
        active_analyzer="basic",
    )
    repository = Database(settings.database_path)
    repository.initialize()
    analyzer = build_analyzer(settings)
    progress = ProgressService(
        learner_repository=repository._learner_repository,
        configuration_repository=repository._configuration_repository,
    )
    profile = LearnerProfileService(
        repository=repository._learner_repository, progress_service=progress,
    )
    submission_service = SubmissionService(
        system_repository=repository._system_repository,
        submission_repository=repository._submission_repository,
        analysis_repository=repository._analysis_repository,
        calibration_repository=repository._calf_repository,
        analyzer=analyzer,
        diagnoser=HeuristicDiagnoser(),
        router=ProviderRouter(
            LocalDemoProvider(),
            LocalDemoProvider(),
            reliability=FeedbackReliabilityService(None),
        ),
        learner_profile_service=profile,
        revision_service=RevisionService(repository._revision_repository),
        calibrator=None,
        calf_configuration=ConfigurationPayload(),
    )
    reanalysis = ReanalysisService(
        repository._submission_repository,
        repository._analysis_repository,
        analyzer,
    )
    pipeline = ExistingWritingPipeline(submission_service, reanalysis)
    return pipeline, repository, submission_service


# Deterministic essay fixtures for the regex analyzer (BasicAnalyzer) plus
# the prototype heuristic diagnoser (prototype-diagnosis-v0.1.1).

# V1: short + repetitive -> essay_length + lexical_repetition priorities.
V1_SHORT_REPETITIVE = (
    "Parks are good. Parks help health. Parks help community. "
    "Parks need space. Parks make people happy. Cities should build parks."
)

# V2: lengthened, varied, with connectives -> no length/repetition flags.
V2_LONG_VARIED = (
    "Living and learning abroad offers valuable experiences that are hard to "
    "obtain at home. Life in a new country develops independence, because "
    "learners manage money, housing, and daily routines themselves. Direct "
    "exposure to another language improves communication skills through "
    "everyday conversation. New friendships across cultures widen personal "
    "perspectives. However, this experience also brings challenges, such as "
    "homesickness, higher costs, and unfamiliar regulations. These "
    "difficulties can be managed with careful planning and support from "
    "universities. Therefore, applicants should weigh these benefits against "
    "the difficulties before making a final decision. In conclusion, time "
    "abroad can be rewarding when preparation is thorough. Universities "
    "provide orientation programs and counseling services that help newcomers "
    "adapt. Regular contact with family and friends reduces feelings of "
    "isolation. Part-time work can cover some expenses and build professional "
    "experience. Each applicant should examine their own goals, budget, and "
    "support network carefully."
)

# Task B V1: short but NOT repetitive, two sentences -> essay_length only
# (single improvement priority that passes the existing feedback validation).
V1_SHORT_NON_REPETITIVE = (
    "Many cities should build more parks. Green spaces support health and "
    "community life."
)


def categories_of(bundle: dict) -> set[str]:
    """Improvement-priority categories stored in one submission bundle."""
    return {
        item["category"]
        for item in (bundle.get("diagnosis") or {}).get("improvement_priorities", [])
        if item.get("category")
    }


def feedback_categories_of(bundle: dict) -> set[str]:
    """Feedback priority-item categories stored in one submission bundle."""
    return {
        item["category"]
        for item in (bundle.get("feedback") or {}).get("priority_feedback", [])
        if item.get("category")
    }
