"""Student View pages — thin compatibility facade (v0.9.5-C, v0.9.5-D).

Feature implementations live in app/ui/features/student/* (one module per
visible page plus small shared helper modules). This module only re-exports
the public renderers and the helpers covered by existing tests/consumers;
no renderer, state, API-call, or business-display logic lives here.

Compatibility note (v0.9.5-D): the private-helper exports below are
compatibility-only and DEPRECATED for new code. New code must import helpers
from their true feature-owner modules, e.g.:

    from app.ui.features.student.home import _home_action_contract
    from app.ui.features.student.session import _writing_saved_for_learner

Public renderer imports through this facade remain supported.
"""

from __future__ import annotations

from app.ui.features.student.adaptive import render_adaptive_learning_page
from app.ui.features.student.feedback import render_feedback_content, render_feedback_page
from app.ui.features.student.formatting import _feedback_category_label, _short_timestamp
from app.ui.features.student.home import _home_action_contract, render_student_home
from app.ui.features.student.journey import (
    _journey_action_contract,
    _journey_description_params,
    _journey_evidence_label,
    _journey_source_label,
    render_learning_journey_page,
)
from app.ui.features.student.navigation import _navigate_student_page
from app.ui.features.student.practice import (
    _practice_constraint_label,
    _practice_instruction,
    _practice_status_label,
    render_practice_page,
)
from app.ui.features.student.revision import (
    _revision_observation_text,
    _revision_saved_for_source,
    _revision_status_label,
    render_revision_page,
)
from app.ui.features.student.session import _writing_saved_for_learner
from app.ui.features.student.writing import render_writing_page

__all__ = [
    "render_adaptive_learning_page",
    "render_student_home",
    "render_writing_page",
    "render_feedback_content",
    "render_feedback_page",
    "render_revision_page",
    "render_practice_page",
    "render_learning_journey_page",
    "_navigate_student_page",
    "_home_action_contract",
    "_short_timestamp",
    "_writing_saved_for_learner",
    "_feedback_category_label",
    "_practice_instruction",
    "_practice_constraint_label",
    "_practice_status_label",
    "_revision_saved_for_source",
    "_revision_observation_text",
    "_revision_status_label",
    "_journey_description_params",
    "_journey_evidence_label",
    "_journey_source_label",
    "_journey_action_contract",
]
