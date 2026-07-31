"""Page modules for the writing-feedback-mvp Streamlit interface."""

from app.ui.pages.student_pages import (
    render_student_home,
    render_writing_page,
    render_feedback_page,
    render_revision_page,
    render_practice_page,
    render_learning_journey_page,
)

from app.ui.pages.research_pages import (
    render_research_overview,
    render_research_evidence,
    render_research_calf,
    render_research_learning_process,
    render_research_data,
    render_research_system_audit,
)

__all__ = [
    "render_student_home",
    "render_writing_page",
    "render_feedback_page",
    "render_revision_page",
    "render_practice_page",
    "render_learning_journey_page",
    "render_research_overview",
    "render_research_evidence",
    "render_research_calf",
    "render_research_learning_process",
    "render_research_data",
    "render_research_system_audit",
]
