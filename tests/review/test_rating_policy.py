"""Rating-rule tests: channels preserved, conservative resolution only."""

from __future__ import annotations

from app.review.models import RATING_ORDINALS, Rating
from app.review.rating_policy import RATING_RULE_VERSION, resolve_final_rating


def test_rating_space_is_ordered_and_matches_fsrs():
    assert RATING_ORDINALS == {
        Rating.AGAIN: 1,
        Rating.HARD: 2,
        Rating.GOOD: 3,
        Rating.EASY: 4,
    }


def test_no_learner_self_rating_uses_system_provisional():
    assert resolve_final_rating(Rating.GOOD) == Rating.GOOD
    assert resolve_final_rating(Rating.AGAIN) == Rating.AGAIN


def test_learner_more_conservative_wins():
    assert resolve_final_rating(Rating.GOOD, Rating.AGAIN) == Rating.AGAIN
    assert resolve_final_rating(Rating.EASY, Rating.HARD) == Rating.HARD


def test_learner_more_optimistic_never_inflates():
    assert resolve_final_rating(Rating.GOOD, Rating.EASY) == Rating.GOOD
    assert resolve_final_rating(Rating.HARD, Rating.GOOD) == Rating.HARD


def test_ties_resolve_to_system_channel():
    assert resolve_final_rating(Rating.HARD, Rating.HARD) == Rating.HARD


def test_final_is_always_one_of_the_input_channels():
    """Not a weighted average: the final rating is always an input channel."""
    for system in Rating:
        for learner in Rating:
            final = resolve_final_rating(system, learner)
            assert final in (system, learner)


def test_rule_version_is_explicit():
    assert RATING_RULE_VERSION == "rating-rule-v1.0.0"
