"""Repair R1 read-only fail-closed probes (isolated temp database).

Covers D3 (FK-nonexistent activity -> 404, no write), D4 (duplicate
PA/RE IDs -> 409, original row intact), D5 (cross-student event/activity
-> 403, no write), C9 (naive/non-UTC datetime -> 422, no write), and the
unchanged valid happy path (200, three channels, provenance).
"""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.config import Settings
from app.infrastructure.sqlite.repositories.wave2 import (
    LearningItem,
    SQLiteWave2Repository,
)
from app.review.models import (
    Rating,
    ReviewEvent,
    PracticeActivity,
    PracticeActivityStatus,
    SchedulerIdentity,
    SchedulerStateSnapshot,
    SchedulingResult,
)
from app.review.protocols import ReviewRepositoryConflictError
from app.review.scheduler import FSRSSchedulerAdapter
from app.review.service import ReviewError


T0 = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)


def _seed(api) -> SQLiteWave2Repository:
    wave2 = SQLiteWave2Repository(api.state.repository._connection_manager)
    wave2.save_learning_item(
        LearningItem(
            learning_item_id="LI000001",
            student_id="S1",
            category="grammar",
        )
    )
    wave2.save_learning_item(
        LearningItem(
            learning_item_id="LI000002",
            student_id="S2",
            category="grammar",
        )
    )
    return wave2


def _db_rows(api, table: str) -> list[dict]:
    with api.state.repository._connection_manager.connect() as connection:
        rows = connection.execute(f"SELECT * FROM {table}").fetchall()
    return [dict(row) for row in rows]


def _review_event(review_event_id: str, **overrides) -> ReviewEvent:
    values = dict(
        review_event_id=review_event_id,
        student_id="S1",
        learning_item_id="LI000001",
        reviewed_at=T0,
        system_provisional_rating=Rating.GOOD,
        learner_self_rating=Rating.HARD,
        final_scheduler_rating=Rating.HARD,
        rating_rule_version="rating-rule-v1.0.0",
        scheduler_implementation="py-fsrs",
        scheduler_version="6.3.2",
        state_before=SchedulerStateSnapshot(card_id=7, due=T0),
        state_after=SchedulerStateSnapshot(
            card_id=7, state="learning", step=1, due=T0
        ),
        scheduling_result=SchedulingResult(next_due=T0),
        provenance={"source": "probe", "batch": 1},
    )
    values.update(overrides)
    return ReviewEvent(**values)


def _state_row(review_event_id: str) -> dict[str, object]:
    identity = FSRSSchedulerAdapter().identity()
    return {
        "learning_item_id": "LI000001",
        "student_id": "S1",
        "identity": identity.model_dump(mode="json"),
        "state": SchedulerStateSnapshot(
            card_id=7, state="review", stability=2.3065, due=T0
        ).model_dump(mode="json"),
        "rating_rule_version": "rating-rule-v1.0.0",
        "updated_at": "2026-01-01T08:00:00+00:00",
        "last_review_event_id": review_event_id,
    }


def main() -> int:
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        results.append((name, ok, detail))
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")

    with tempfile.TemporaryDirectory() as tmpdir:
        settings = Settings(
            database_path=Path(tmpdir) / "probe.db",
            llm_provider="local",
            deepseek_api_key=None,
            deepseek_base_url="https://example.invalid",
            deepseek_model="deepseek-test",
        )
        api = create_app(settings)
        _seed(api)
        client = TestClient(api, raise_server_exceptions=False)
        service = api.state.review_service
        repository = api.state.review_repository

        # P1 happy path unchanged: 200, three channels, provenance.
        resp = client.post(
            "/api/v1/review/events",
            json={
                "student_id": "S1",
                "learning_item_id": "LI000001",
                "reviewed_at": T0.isoformat(),
                "system_provisional_rating": "good",
                "learner_self_rating": "hard",
                "provenance": {"source": "probe", "round": 1},
            },
        )
        body = resp.json()
        ok = (
            resp.status_code == 200
            and body["system_provisional_rating"] == "good"
            and body["learner_self_rating"] == "hard"
            and body["final_scheduler_rating"] == "hard"
            and body["scheduler_implementation"] == "py-fsrs"
            and body["scheduler_version"] == "6.3.2"
            and body["provenance"] == {"source": "probe", "round": 1}
        )
        check(
            "P1 happy path (200, three channels, provenance)",
            ok,
            f"status={resp.status_code}",
        )
        events_before = len(_db_rows(api, "review_events"))

        # P2 D3: nonexistent practice_activity_id -> 404, no write.
        resp = client.post(
            "/api/v1/review/events",
            json={
                "student_id": "S1",
                "learning_item_id": "LI000001",
                "practice_activity_id": "PA-NOPE",
                "reviewed_at": T0.isoformat(),
                "system_provisional_rating": "good",
            },
        )
        no_write = (
            len(_db_rows(api, "review_events")) == events_before
            and len(_db_rows(api, "learning_item_scheduler_states")) == 1
        )
        service_kind = None
        try:
            service.record_review(
                student_id="S1",
                learning_item_id="LI000001",
                reviewed_at=T0,
                system_provisional_rating=Rating.GOOD,
                practice_activity_id="PA-NOPE",
            )
        except ReviewError as exc:
            service_kind = exc.kind
        check(
            "P2 nonexistent activity -> 404, no write",
            resp.status_code == 404
            and "No durable PracticeActivity exists" in resp.text
            and service_kind == "practice_activity_not_found"
            and no_write,
            f"status={resp.status_code} kind={service_kind}",
        )

        # P3 D4: duplicate practice-activity ID -> 409, original row intact.
        first = client.post(
            "/api/v1/review/practice-activities",
            json={
                "activity_id": "PA-OWNED",
                "student_id": "S1",
                "learning_item_id": "LI000001",
                "activity_type": "blank_fill",
                "status": "completed",
                "occurred_at": T0.isoformat(),
                "provenance": {"source": "probe", "batch": 1},
            },
        )
        second = client.post(
            "/api/v1/review/practice-activities",
            json={
                "activity_id": "PA-OWNED",
                "student_id": "S1",
                "learning_item_id": "LI000001",
                "activity_type": "blank_fill",
                "status": "completed",
                "occurred_at": T0.isoformat(),
                "provenance": {"source": "probe", "batch": 2},
            },
        )
        pa_rows = _db_rows(api, "practice_activities")
        original = [
            r for r in pa_rows if r["activity_id"] == "PA-OWNED"
        ]
        original_intact = (
            len(pa_rows) == 1
            and len(original) == 1
            and json.loads(original[0]["provenance_json"])
            == {"source": "probe", "batch": 1}
        )
        service_kind = None
        try:
            service.record_practice_activity(
                PracticeActivity(
                    activity_id="PA-OWNED",
                    student_id="S1",
                    learning_item_id="LI000001",
                    activity_type="blank_fill",
                    status=PracticeActivityStatus.COMPLETED,
                    occurred_at=T0,
                    provenance={"source": "probe", "batch": 2},
                )
            )
        except ReviewError as exc:
            service_kind = exc.kind
        check(
            "P3 duplicate activity ID -> 409, original intact",
            first.status_code == 200
            and second.status_code == 409
            and "already exists" in second.text
            and service_kind == "practice_activity_already_exists"
            and original_intact,
            f"first={first.status_code} second={second.status_code} "
            f"kind={service_kind} rows={len(pa_rows)}",
        )

        # P4 D4: duplicate review-event ID -> conflict, original row intact.
        try:
            repository.record_review_event(
                _review_event("RE-REP0-DUP"), _state_row("RE-REP0-DUP")
            )
            first_re = True
        except ReviewRepositoryConflictError:
            first_re = False
        dup_kind = None
        try:
            repository.record_review_event(
                _review_event("RE-REP0-DUP"), _state_row("RE-REP0-DUP")
            )
            dup_ok = False
        except ReviewRepositoryConflictError as exc:
            dup_kind = exc.kind
            dup_ok = True
        re_rows = [
            r for r in _db_rows(api, "review_events")
            if r["review_event_id"] == "RE-REP0-DUP"
        ]
        re_intact = (
            len(re_rows) == 1
            and json.loads(re_rows[0]["provenance_json"])
            == {"source": "probe", "batch": 1}
        )
        check(
            "P4 duplicate review-event ID -> 409 signal, original intact",
            first_re and dup_ok and dup_kind == "review_event_already_exists"
            and re_intact,
            f"kind={dup_kind} rows={len(re_rows)}",
        )
        # P4 legitimately persisted one event; re-snapshot for no-write
        # assertions in the remaining probes.
        events_before = len(_db_rows(api, "review_events"))

        # P5 D5: cross-student review event -> 403, no write.
        resp = client.post(
            "/api/v1/review/events",
            json={
                "student_id": "S2",
                "learning_item_id": "LI000001",
                "reviewed_at": T0.isoformat(),
                "system_provisional_rating": "good",
            },
        )
        no_write = len(_db_rows(api, "review_events")) == events_before
        service_kind = None
        try:
            service.record_review(
                student_id="S2",
                learning_item_id="LI000001",
                reviewed_at=T0,
                system_provisional_rating=Rating.GOOD,
            )
        except ReviewError as exc:
            service_kind = exc.kind
        check(
            "P5 cross-student event -> 403, no write",
            resp.status_code == 403
            and "does not match the owner" in resp.text
            and service_kind == "learning_item_owner_mismatch"
            and no_write,
            f"status={resp.status_code} kind={service_kind}",
        )

        # P6 D5: event linking another student's activity -> 403, no write.
        other = client.post(
            "/api/v1/review/practice-activities",
            json={
                "activity_id": "PA-S2",
                "student_id": "S2",
                "learning_item_id": "LI000002",
                "activity_type": "blank_fill",
                "status": "completed",
                "occurred_at": T0.isoformat(),
            },
        )
        resp = client.post(
            "/api/v1/review/events",
            json={
                "student_id": "S1",
                "learning_item_id": "LI000001",
                "practice_activity_id": "PA-S2",
                "reviewed_at": T0.isoformat(),
                "system_provisional_rating": "good",
            },
        )
        no_write = len(_db_rows(api, "review_events")) == events_before
        service_kind = None
        try:
            service.record_review(
                student_id="S1",
                learning_item_id="LI000001",
                reviewed_at=T0,
                system_provisional_rating=Rating.GOOD,
                practice_activity_id="PA-S2",
            )
        except ReviewError as exc:
            service_kind = exc.kind
        check(
            "P6 cross-student activity link -> 403, no write",
            other.status_code == 200
            and resp.status_code == 403
            and "belongs to student" in resp.text
            and service_kind == "practice_activity_owner_mismatch"
            and no_write,
            f"status={resp.status_code} kind={service_kind}",
        )

        # P7 D5: practice activity with mismatched owner -> 403, no write.
        pa_before = len(_db_rows(api, "practice_activities"))
        resp = client.post(
            "/api/v1/review/practice-activities",
            json={
                "activity_id": "PA-WRONG-OWNER",
                "student_id": "S2",
                "learning_item_id": "LI000001",
                "activity_type": "blank_fill",
                "status": "completed",
                "occurred_at": T0.isoformat(),
            },
        )
        no_write = len(_db_rows(api, "practice_activities")) == pa_before
        service_kind = None
        try:
            service.record_practice_activity(
                PracticeActivity(
                    activity_id="PA-WRONG-OWNER",
                    student_id="S2",
                    learning_item_id="LI000001",
                    activity_type="blank_fill",
                    status=PracticeActivityStatus.COMPLETED,
                    occurred_at=T0,
                )
            )
        except ReviewError as exc:
            service_kind = exc.kind
        check(
            "P7 mismatched activity owner -> 403, no write",
            resp.status_code == 403
            and "does not match the owner" in resp.text
            and service_kind == "practice_activity_owner_mismatch"
            and no_write,
            f"status={resp.status_code} kind={service_kind}",
        )

        # P8 C9: naive datetime -> 422, no write (router boundary).
        resp = client.post(
            "/api/v1/review/events",
            json={
                "student_id": "S1",
                "learning_item_id": "LI000001",
                "reviewed_at": "2026-01-01T08:00:00",
                "system_provisional_rating": "good",
            },
        )
        no_write = len(_db_rows(api, "review_events")) == events_before
        check(
            "P8 naive datetime -> 422, no write",
            resp.status_code == 422 and no_write,
            f"status={resp.status_code}",
        )

        # P9 C9: non-UTC datetime -> 422, no write.
        resp = client.post(
            "/api/v1/review/events",
            json={
                "student_id": "S1",
                "learning_item_id": "LI000001",
                "reviewed_at": "2026-01-01T08:00:00+08:00",
                "system_provisional_rating": "good",
            },
        )
        no_write = len(_db_rows(api, "review_events")) == events_before
        check(
            "P9 non-UTC datetime -> 422, no write",
            resp.status_code == 422 and no_write,
            f"status={resp.status_code}",
        )

        # P10 C9: service-level stable ReviewError for naive datetime.
        try:
            service.record_review(
                student_id="S1",
                learning_item_id="LI000001",
                reviewed_at=datetime(2026, 1, 1, 8, 0, 0),
                system_provisional_rating=Rating.GOOD,
            )
            service_kind = None
        except ReviewError as exc:
            service_kind = exc.kind
        check(
            "P10 service-level naive datetime -> invalid_reviewed_at",
            service_kind == "invalid_reviewed_at",
            f"kind={service_kind}",
        )

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} probes passed")
    for name, ok, detail in failed:
        print(f"FAILED: {name}: {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
