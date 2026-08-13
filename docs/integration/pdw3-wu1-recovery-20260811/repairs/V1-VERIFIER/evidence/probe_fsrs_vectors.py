"""V1 independent probe 1: real fsrs==6.3.2 identity + deterministic vectors.

Cross-checks the app adapter against RAW library computation (no app code in
the reference path) for next-review and repeat-review vectors, records the
rating/state lifecycle through the real scheduler, and asserts invalid
transitions fail closed.
"""

from __future__ import annotations

import importlib.metadata
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[6]))

from fsrs import Card, Rating as FSRsRating, Scheduler, State

from app.review.models import Rating
from app.review.scheduler import FSRSSchedulerAdapter


T0 = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
RESULTS: list[dict] = []


def check(name: str, ok: bool, detail: str) -> None:
    RESULTS.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def raw_vector(
    state: State,
    step: int,
    rating: FSRsRating,
    reviewed_at: datetime,
    *,
    stability: float | None = None,
    difficulty: float | None = None,
    last_review: datetime | None = None,
) -> tuple[dict, float, float, float]:
    """Pure py-fsrs 6.3.2 computation, no app code."""
    scheduler = Scheduler(desired_retention=0.9, enable_fuzzing=False)
    card = Card(
        card_id=7,
        state=state,
        step=step,
        stability=stability,
        difficulty=difficulty,
        due=reviewed_at,
        last_review=last_review,
    )
    new_card, _ = scheduler.review_card(card, rating, review_datetime=reviewed_at)
    return (
        {
            "state": new_card.state.name,
            "step": new_card.step,
            "due": new_card.due,
            "last_review": new_card.last_review,
        },
        new_card.stability,
        new_card.difficulty,
        new_card.due,
    )


def main() -> None:
    # 1. Version identity.
    try:
        import fsrs

        has_attr = hasattr(fsrs, "__version__")
        check(
            "no fsrs.__version__ in 6.3.2 (packet probe nuance)",
            has_attr is False,
            f"hasattr(fsrs,'__version__')={has_attr}",
        )
    except Exception as exc:  # pragma: no cover
        check("fsrs import", False, repr(exc))
    installed = importlib.metadata.version("fsrs")
    check(
        "importlib.metadata version == 6.3.2",
        installed == "6.3.2",
        f"importlib.metadata.version('fsrs')={installed}",
    )

    adapter = FSRSSchedulerAdapter()
    identity = adapter.identity()
    check(
        "adapter identity",
        (
            identity.implementation == "py-fsrs"
            and identity.library_version == "6.3.2"
            and identity.algorithm == "FSRS"
            and identity.parameters.get("enable_fuzzing") is False
            and identity.parameters.get("desired_retention") == 0.9
        ),
        json.dumps(identity.model_dump(mode="json"))[:400],
    )

    # 2. Deterministic vectors: adapter vs RAW library computation.
    fresh = adapter.new_state(card_id=7, due=T0)
    state_after, result = adapter.review(fresh, Rating.GOOD, T0)
    r_state, r_stab, r_diff, r_due = raw_vector(State.Learning, 0, FSRsRating.Good, T0)
    check(
        "first Good vector matches raw py-fsrs",
        (
            state_after.state == "learning"
            and state_after.step == r_state["step"]
            and abs(state_after.stability - r_stab) < 1e-12
            and abs(state_after.difficulty - r_diff) < 1e-12
            and state_after.due == r_due
        ),
        (
            f"adapter(step={state_after.step}, stability={state_after.stability!r}, "
            f"difficulty={state_after.difficulty!r}, due={state_after.due}) "
            f"raw(step={r_state['step']}, stability={r_stab!r}, difficulty={r_diff!r}, due={r_due})"
        ),
    )

    # Repeat review (second Good from Learning step 1) -> Review state, +2 days.
    state_after2, result2 = adapter.review(state_after, Rating.GOOD, T0)
    r_state2, r_stab2, r_diff2, r_due2 = raw_vector(
        State.Learning,
        state_after.step,
        FSRsRating.Good,
        T0,
        stability=state_after.stability,
        difficulty=state_after.difficulty,
        last_review=state_after.last_review,
    )
    check(
        "second Good (repeat) vector matches raw py-fsrs",
        (
            state_after2.state == "review"
            and state_after2.step == r_state2["step"]
            and abs(state_after2.stability - r_stab2) < 1e-12
            and abs(state_after2.difficulty - r_diff2) < 1e-12
            and state_after2.due == r_due2
        ),
        (
            f"adapter(step={state_after2.step}, stability={state_after2.stability!r}, "
            f"difficulty={state_after2.difficulty!r}, due={state_after2.due}) "
            f"raw(step={r_state2['step']}, stability={r_stab2!r}, difficulty={r_diff2!r}, due={r_due2})"
        ),
    )

    # Determinism: identical vector twice.
    again1, _ = adapter.review(state_after2, Rating.AGAIN, T0)
    again2, _ = adapter.review(state_after2, Rating.AGAIN, T0)
    check(
        "identical repeat vectors (fuzzing off)",
        again1.model_dump(mode="json") == again2.model_dump(mode="json"),
        f"same state/step/stability/difficulty/due: {again1.model_dump(mode='json')}",
    )

    # 3. Rating/state lifecycle through the real scheduler.
    lifecycle = []
    cur = fresh
    for label, rating in [
        ("Good->Learning", Rating.GOOD),
        ("Good->Review", Rating.GOOD),
        ("Again->Relearning", Rating.AGAIN),
        ("Good->Review", Rating.GOOD),
    ]:
        cur, _ = adapter.review(cur, rating, T0)
        lifecycle.append((label, cur.state, cur.step))
    check(
        "New->Learning->Review->Relearning->Review through real scheduler",
        [l[1] for l in lifecycle]
        == ["learning", "review", "relearning", "review"],
        str(lifecycle),
    )

    # Easy on fresh -> Review immediately (fsrs 6.3.2 behavior).
    easy_state, _ = adapter.review(fresh, Rating.EASY, T0)
    check(
        "Easy on fresh -> Review immediately",
        easy_state.state == "review" and easy_state.step is None,
        f"state={easy_state.state}, step={easy_state.step}, due={easy_state.due}",
    )

    # 4. Invalid transitions fail closed through the real scheduler.
    # (a) Relearning with step beyond relearning_steps (600s single step).
    over_relearn = adapter.new_state(card_id=7, due=T0)
    over_relearn.state = "relearning"
    over_relearn.step = 5
    try:
        adapter.review(over_relearn, Rating.GOOD, T0)
        check("relearning step overflow fails closed", False, "no exception raised")
    except (AssertionError, ValueError) as exc:
        check(
            "relearning step overflow fails closed",
            True,
            f"{type(exc).__name__}: {str(exc)[:120]}",
        )

    # (b) Review state with residual step (invalid combination).
    residual = adapter.new_state(card_id=7, due=T0)
    residual.state = "review"
    residual.step = 2
    try:
        adapter.review(residual, Rating.GOOD, T0)
        check("review state with residual step fails closed", False, "no exception")
    except (AssertionError, ValueError) as exc:
        check(
            "review state with residual step fails closed",
            True,
            f"{type(exc).__name__}: {str(exc)[:120]}",
        )

    # (c) Invalid app-level rating coercion (service-level fail-closed).
    from app.review.service import _coerce_rating

    bad = 0
    for value in ["excellent", "3", 3, None, "", "GOOD"]:
        try:
            _coerce_rating(value, name="probe")
        except ValueError:
            bad += 1
    check(
        "invalid rating values rejected by service coercion",
        bad == 6,
        f"rejected {bad}/6 (excellent, '3', 3, None, '', 'GOOD')",
    )

    ok = sum(1 for r in RESULTS if r["ok"])
    print(f"\nSUMMARY {ok}/{len(RESULTS)} passed")
    raise SystemExit(0 if ok == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
