"""Wave-2 L2 modules: context-aware revision loop + personalized bridge.

Goal PDW2-C-L2-REVISION-SCAFFOLD. All outputs are bounded and
observation-only: observed evidence, diagnostic inference, feedback
recommendation and learning outcome remain distinct; no mastery,
proficiency, or learning-gain claims are made anywhere in this package.
"""

from __future__ import annotations

from app.l2.wave2.corpus_routing import (
    CorpusRoutingProtocol,
    LocalWrittenCorpusRouter,
    WrittenCorpusRoutingRequest,
)
from app.l2.wave2.models import (
    LearningItem,
    PriorityRevisionPlan,
    RevisionObservation,
    ScaffoldEvent,
    SubmissionVersion,
    WritingTask,
    WritingTaskMetadata,
)
from app.l2.wave2.personalized import PersonalizedBridgeService
from app.l2.wave2.pipeline import (
    ExistingWritingPipeline,
    ReanalysisResult,
    WritingPipelinePort,
)
from app.l2.wave2.repository import (
    InMemoryRevisionLoopRepository,
    RevisionLoopRepository,
)
from app.l2.wave2.revision_loop import (
    RevisionLoopService,
    build_revision_observation,
)

__all__ = [
    "CorpusRoutingProtocol",
    "ExistingWritingPipeline",
    "InMemoryRevisionLoopRepository",
    "LearningItem",
    "LocalWrittenCorpusRouter",
    "PersonalizedBridgeService",
    "PriorityRevisionPlan",
    "ReanalysisResult",
    "RevisionLoopRepository",
    "RevisionLoopService",
    "RevisionObservation",
    "ScaffoldEvent",
    "SubmissionVersion",
    "WritingPipelinePort",
    "WritingTask",
    "WritingTaskMetadata",
    "WrittenCorpusRoutingRequest",
    "build_revision_observation",
]
