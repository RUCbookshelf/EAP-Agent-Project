"""Frontend API Ports (v0.9.5-D).

Narrow feature-owned structural contracts. Each visible feature depends only
on the Port that declares the client methods it actually calls. The concrete
HTTP implementation remains WritingFeedbackApiClient (app/ui/api_client.py),
which satisfies every Port structurally.
"""

from __future__ import annotations

from app.ui.ports.research import (
    ResearchCalfApiPort,
    ResearchDataApiPort,
    ResearchEvidenceApiPort,
    ResearchLearningProcessApiPort,
    ResearchOverviewApiPort,
    ResearchSystemAuditApiPort,
)
from app.ui.ports.student import (
    StudentFeedbackApiPort,
    StudentHomeApiPort,
    StudentJourneyApiPort,
    StudentPracticeApiPort,
    StudentRevisionApiPort,
    StudentWritingApiPort,
)

__all__ = [
    "StudentHomeApiPort",
    "StudentWritingApiPort",
    "StudentFeedbackApiPort",
    "StudentPracticeApiPort",
    "StudentRevisionApiPort",
    "StudentJourneyApiPort",
    "ResearchOverviewApiPort",
    "ResearchEvidenceApiPort",
    "ResearchCalfApiPort",
    "ResearchLearningProcessApiPort",
    "ResearchDataApiPort",
    "ResearchSystemAuditApiPort",
]
