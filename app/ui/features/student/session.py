"""Shared Student session-state helper (v0.9.5-C).

Ownership: `_writing_saved_for_learner` is used by Writing, Feedback, and
Revision and lives here once. Behavior is unchanged from the pre-extraction
module.
"""

from __future__ import annotations


def _writing_saved_for_learner(result: dict | None, student_id: str) -> bool:
    """A saved UI result locks only the learner who created that submission."""
    if not result or not student_id.strip():
        return False
    return result.get("ui_submission", {}).get("student_id") == student_id.strip()
