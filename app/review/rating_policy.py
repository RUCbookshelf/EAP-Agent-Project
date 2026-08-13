"""Versioned rating rule resolving the final scheduler rating (CORE, WU1).

The rating channels are preserved separately on every ``ReviewEvent``; this
module only resolves WHICH rating is fed to the FSRS scheduler. The rule is
explicit, deterministic, versioned, and deliberately conservative: it never
produces a more optimistic final rating than either available channel, so a
system/learner disagreement cannot inflate the schedule. It is NOT a
weighted average and it does not reinterpret the stored channels; later
bounded reconciliation remains possible for LEARNER/L2 by re-running a
newer rule version over the stored channels.
"""

from __future__ import annotations

from .models import RATING_ORDINALS, Rating


# Versioned identity stored on every ReviewEvent and scheduler-state row.
RATING_RULE_VERSION: str = "rating-rule-v1.0.0"


def resolve_final_rating(
    system_provisional: Rating,
    learner_self: Rating | None = None,
) -> Rating:
    """Conservative-minimum resolution of the final scheduler rating.

    - No learner self-rating -> the system provisional rating is final.
    - Learner self-rating provided -> the more conservative (lower ordinal)
      of the two channels is final (fail-closed: disagreement never extends
      the schedule).
    """
    if learner_self is None:
        return system_provisional
    if RATING_ORDINALS[learner_self] < RATING_ORDINALS[system_provisional]:
        return learner_self
    return system_provisional


__all__ = ["RATING_RULE_VERSION", "resolve_final_rating"]
