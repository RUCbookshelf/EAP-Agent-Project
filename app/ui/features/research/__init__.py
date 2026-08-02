"""Research feature modules (v0.9.5-C).

One module per visible Research page. Research features are self-contained
(the only module-level constant, CALF_CLASSIFICATION, belongs to the CALF
feature).
"""

from __future__ import annotations

from app.ui.features.research.calf import render_research_calf
from app.ui.features.research.data import render_research_data
from app.ui.features.research.evidence import render_research_evidence
from app.ui.features.research.learning_process import render_research_learning_process
from app.ui.features.research.overview import render_research_overview
from app.ui.features.research.system_audit import render_research_system_audit

__all__ = [
    "render_research_overview",
    "render_research_evidence",
    "render_research_calf",
    "render_research_learning_process",
    "render_research_data",
    "render_research_system_audit",
]
