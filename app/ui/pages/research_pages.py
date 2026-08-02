"""Research View pages — thin compatibility facade (v0.9.5-C, v0.9.5-D).

Feature implementations live in app/ui/features/research/* (one module per
visible Research page). This module only re-exports the public renderers;
no renderer, state, API-call, or business-display logic lives here.

Compatibility note (v0.9.5-D): this module is compatibility-only for public
renderer imports. New code should import renderers from their feature-owner
modules under app.ui.features.research.*.
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
