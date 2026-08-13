"""Repair R3 read-only probe: what the REAL fsrs==6.3.2 scheduler does for
impossible / boundary state-rating vectors (Case B invalid-transition
coverage), plus model-boundary fail-closed rejections.

Runs against the pinned real library through the real FSRSSchedulerAdapter;
output is recorded in probe-real-fsrs-transitions.log and pinned as exact
vectors in tests/review/test_scheduler_invalid_transitions.py.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone

from app.review.models import Rating, SchedulerStateSnapshot
from app.review.scheduler import FSRSSchedulerAdapter


T0 = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 1, 5, 8, 0, 0, tzinfo=timezone.utc)


def _fmt(value) -> str:
    if isinstance(value, SchedulerStateSnapshot):
        return value.model_dump(mode="json")
    return repr(value)


def main() -> int:
    adapter = FSRSSchedulerAdapter()
    identity = adapter.identity()
    print(f"library_version={identity.library_version}")
    print(f"implementation={identity.implementation}")
    print(f"algorithm={identity.algorithm}")
    print(f"learning_steps={identity.parameters['learning_steps']}")
    print(f"relearning_steps={identity.parameters['relearning_steps']}")
    print()

    initial = adapter.new_state(card_id=1, due=T0)
    first_state, _ = adapter.review(initial, Rating.GOOD, T0)
    second_state, _ = adapter.review(first_state, Rating.GOOD, first_state.due)
    print("after first GOOD (learning, step 1):", _fmt(first_state))
    print("after second GOOD (review):", _fmt(second_state))
    print()

    probes: list[tuple[str, SchedulerStateSnapshot, Rating, datetime]] = [
        # Learning step beyond learning_steps length (2) is impossible via
        # the normal lifecycle; feed it to the real library anyway.
        (
            "learning step=2 GOOD (step overflow)",
            SchedulerStateSnapshot(
                card_id=1, state="learning", step=2, due=T0
            ),
            Rating.GOOD,
            T0,
        ),
        (
            "learning step=2 AGAIN (step overflow)",
            SchedulerStateSnapshot(
                card_id=1, state="learning", step=2, due=T0
            ),
            Rating.AGAIN,
            T0,
        ),
        # Relearning step beyond relearning_steps length (1).
        (
            "relearning step=1 GOOD (step overflow)",
            SchedulerStateSnapshot(
                card_id=1, state="relearning", step=1, due=T0
            ),
            Rating.GOOD,
            T0,
        ),
        # Review state carrying a residual step (normally None).
        (
            "review state with step=0 GOOD",
            SchedulerStateSnapshot(
                card_id=1, state="review", step=0, due=T0
            ),
            Rating.GOOD,
            T0,
        ),
        # Learning state with step=None (normally 0 after first review).
        (
            "learning state step=None GOOD",
            SchedulerStateSnapshot(
                card_id=1, state="learning", step=None, due=T0
            ),
            Rating.GOOD,
            T0,
        ),
        # Review state with no stability/difficulty history.
        (
            "review state stability=None GOOD",
            SchedulerStateSnapshot(
                card_id=1, state="review", due=T0
            ),
            Rating.GOOD,
            T0,
        ),
        # Overdue review: new state at T0, reviewed 4 days later.
        (
            "overdue new-card review GOOD",
            adapter.new_state(card_id=1, due=T0),
            Rating.GOOD,
            LATER,
        ),
        # Second review on an overdue review-state card.
        (
            "overdue review-state review GOOD",
            second_state,
            Rating.GOOD,
            LATER,
        ),
        # card_id=None tolerance.
        (
            "card_id=None review GOOD",
            adapter.new_state(card_id=None, due=T0),
            Rating.GOOD,
            T0,
        ),
    ]

    for name, state, rating, reviewed_at in probes:
        try:
            new_state, result = adapter.review(state, rating, reviewed_at)
            print(f"OK   {name}")
            print(f"     in  = {_fmt(state)}")
            print(f"     out = {_fmt(new_state)}")
            print(
                f"     result = next_due={result.next_due!r} "
                f"state={result.state!r} step={result.step!r} "
                f"stability={result.stability!r} difficulty={result.difficulty!r}"
            )
        except Exception as exc:  # noqa: BLE001 - record exact real behavior
            print(f"RAISE {name}: {type(exc).__name__}: {exc}")
        print()

    # Contract-invalid vectors: model boundary must reject before the real
    # scheduler is ever consulted.
    rejections = [
        ("state='mastered'", dict(state="mastered")),
        ("step=-1", dict(step=-1)),
        ("state='graduated'", dict(state="graduated")),
    ]
    for name, overrides in rejections:
        try:
            SchedulerStateSnapshot(**overrides)
            print(f"ACCEPTED {name} (unexpected)")
        except Exception as exc:  # noqa: BLE001
            print(f"REJECT {name}: {type(exc).__name__}")
    print()

    # Invalid rating text through the adapter's Rating mapping (misuse path;
    # the product contract rejects it in the service before the adapter).
    try:
        adapter.review(initial, "excellent", T0)  # type: ignore[arg-type]
        print("ACCEPTED invalid rating string (unexpected)")
    except Exception as exc:  # noqa: BLE001
        print(f"REJECT invalid rating string: {type(exc).__name__}: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
