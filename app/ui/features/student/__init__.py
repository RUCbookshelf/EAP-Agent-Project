"""Student feature modules (v0.9.5-C).

Ownership: navigation.py (cross-feature page navigation), formatting.py
(cross-feature display formatting), session.py (cross-feature submission
session lock), and one module per visible Student page.
"""

from __future__ import annotations

from app.ui.features.student.feedback import render_feedback_content, render_feedback_page
from app.ui.features.student.home import render_student_home
from app.ui.features.student.journey import render_learning_journey_page
from app.ui.features.student.practice import render_practice_page
from app.ui.features.student.revision import render_revision_page
from app.ui.features.student.writing import render_writing_page

__all__ = [
    "render_student_home",
    "render_writing_page",
    "render_feedback_content",
    "render_feedback_page",
    "render_revision_page",
    "render_practice_page",
    "render_learning_journey_page",
]
