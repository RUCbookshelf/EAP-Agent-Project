"""Shared Student display formatting helpers (v0.9.5-C).

Ownership: `_short_timestamp` (Home, Journey) and `_feedback_category_label`
(Feedback, Revision) are used by more than one feature and live here once.
Behavior is unchanged from the pre-extraction module.
"""

from __future__ import annotations

from app.ui.locale import t


def _feedback_category_label(category: str, lang: str) -> str:
    """Use an approved learner-facing label when one exists."""
    key = f"student_feedback_category_{category}"
    localized = t(key, lang)
    return localized if localized != key else category.replace("_", " ").title()


def _short_timestamp(value: str) -> str:
    """Compact UTC timestamp for display (e.g., 2026-08-01 12:34)."""
    try:
        dt = __import__("datetime").datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(__import__("datetime").timezone.utc).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return str(value)[:16]
