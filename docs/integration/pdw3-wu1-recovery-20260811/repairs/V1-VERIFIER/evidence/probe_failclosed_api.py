"""V1 independent probe 3: fail-closed API boundaries (real composition).

TestClient with raise_server_exceptions=False on a real temp DB. Each
negative case asserts the expected status/kind AND that no row was written.
"""

from __future__ import annotations

import sys
import json
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[6]))

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.config import Settings
from app.infrastructure.sqlite.repositories.wave2 import (
    LearningItem,
    SQLiteWave2Repository,
)
from app.review.models import Rating


T0 = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
RESULTS: list[dict] = []


def check(name: str, ok: bool, detail: str) -> None:
    RESULTS.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def count(api, table: str) -> int:
    with api.state.repository._connection_manager.connect() as connection:
        return connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def main() -> None:
    db_path = OUT / "failclosed.db"
    db_path.unlink(missing_ok=True)
    settings = Settings(
        database_path=db_path,
        llm_provider="local",
        deepseek_api_key=None,
        deepseek_base_url="https://example.invalid",
        deepseek_model="deepseek-test",
    )
    api = create_app(settings)
    wave2 = SQLiteWave2Repository(api.state.repository._connection_manager)
    wave2.save_learning_item(
        LearningItem(learning_item_id="LI000001", student_id="S1", category="grammar")
    )
    wave2.save_learning_item(
        LearningItem(learning_item_id="LI000002", student_id="S2", category="grammar")
    )
    client = TestClient(api, raise_server_exceptions=False)

    def post(path: str, payload: dict):
        return client.post(path, json=payload)

    # 1. Invalid rating -> 422, no writes.
    r = post(
        "/api/v1/review/events",
        {
            "student_id": "S1",
            "learning_item_id": "LI000001",
            "reviewed_at": T0.isoformat(),
            "system_provisional_rating": "excellent",
            "learner_self_rating": "hard",
        },
    )
    check(
        "invalid rating -> 422",
        r.status_code == 422,
        f"status={r.status_code} body={r.text[:200]}",
    )

    # 2. Unknown fields -> 422 (extra=forbid), no writes.
    r = post(
        "/api/v1/review/events",
        {
            "student_id": "S1",
            "learning_item_id": "LI000001",
            "reviewed_at": T0.isoformat(),
            "system_provisional_rating": "good",
            "learner_self_rating": "hard",
            "final_scheduler_rating": "easy",
        },
    )
    check(
        "client cannot inject final_scheduler_rating -> 422",
        r.status_code == 422,
        f"status={r.status_code} body={r.text[:160]}",
    )

    # 3. Malformed provenance -> 422, no writes.
    r = post(
        "/api/v1/review/events",
        {
            "student_id": "S1",
            "learning_item_id": "LI000001",
            "reviewed_at": T0.isoformat(),
            "system_provisional_rating": "good",
            "learner_self_rating": "hard",
            "provenance": ["not", "a", "dict"],
        },
    )
    check(
        "malformed provenance (list) -> 422",
        r.status_code == 422,
        f"status={r.status_code} body={r.text[:160]}",
    )

    # 4. Nonexistent learning item -> 404, no writes.
    r = post(
        "/api/v1/review/events",
        {
            "student_id": "S1",
            "learning_item_id": "LI-NOPE",
            "reviewed_at": T0.isoformat(),
            "system_provisional_rating": "good",
        },
    )
    check(
        "nonexistent learning_item -> 404",
        r.status_code == 404,
        f"status={r.status_code} body={r.text[:160]}",
    )

    # 5. Naive datetime -> 422, no writes.
    r = post(
        "/api/v1/review/events",
        {
            "student_id": "S1",
            "learning_item_id": "LI000001",
            "reviewed_at": "2026-01-01T08:00:00",
            "system_provisional_rating": "good",
        },
    )
    check(
        "naive reviewed_at -> 422",
        r.status_code == 422,
        f"status={r.status_code} body={r.text[:160]}",
    )

    # 6. Non-UTC offset datetime -> 422, no writes.
    r = post(
        "/api/v1/review/events",
        {
            "student_id": "S1",
            "learning_item_id": "LI000001",
            "reviewed_at": "2026-01-01T08:00:00+08:00",
            "system_provisional_rating": "good",
        },
    )
    check(
        "non-UTC reviewed_at -> 422",
        r.status_code == 422,
        f"status={r.status_code} body={r.text[:160]}",
    )

    # 7. Nonexistent practice_activity_id -> 404, no writes (inventory D3).
    r = post(
        "/api/v1/review/events",
        {
            "student_id": "S1",
            "learning_item_id": "LI000001",
            "practice_activity_id": "PA-NOPE",
            "reviewed_at": T0.isoformat(),
            "system_provisional_rating": "good",
        },
    )
    check(
        "nonexistent practice_activity_id -> 404 practice_activity_not_found",
        r.status_code == 404
        and "No durable PracticeActivity exists" in r.text,
        f"status={r.status_code} body={r.text[:200]}",
    )
    from app.review.service import ReviewError

    try:
        api.state.review_service.record_review(
            student_id="S1",
            learning_item_id="LI000001",
            reviewed_at=T0,
            system_provisional_rating=Rating.GOOD,
            practice_activity_id="PA-NOPE",
        )
        check(
            "service-level kind for missing activity",
            False,
            "no ReviewError raised",
        )
    except ReviewError as exc:
        check(
            "service-level kind for missing activity",
            exc.kind == "practice_activity_not_found",
            f"kind={exc.kind}",
        )

    # 8. Duplicate practice activity id -> 409, original intact (inventory D4).
    base = {
        "student_id": "S1",
        "learning_item_id": "LI000001",
        "activity_type": "blank_fill",
        "status": "completed",
        "occurred_at": T0.isoformat(),
    }
    r1 = post(
        "/api/v1/review/practice-activities",
        {**base, "activity_id": "PA-DUP", "provenance": {"batch": 1}},
    )
    r2 = post(
        "/api/v1/review/practice-activities",
        {**base, "activity_id": "PA-DUP", "provenance": {"batch": 2}},
    )
    with api.state.repository._connection_manager.connect() as connection:
        row = connection.execute(
            "SELECT provenance_json FROM practice_activities"
            " WHERE activity_id='PA-DUP'"
        ).fetchone()
    kept = json.loads(row[0]) if row is not None else None
    check(
        "duplicate PA id -> 409, original row intact",
        r1.status_code == 200
        and r2.status_code == 409
        and "already exists" in r2.text
        and kept == {"batch": 1},
        f"r1={r1.status_code} r2={r2.status_code} provenance={kept}",
    )

    # 9. Cross-student review event -> 403, no writes (inventory D5).
    r = post(
        "/api/v1/review/events",
        {
            "student_id": "S2",
            "learning_item_id": "LI000001",
            "reviewed_at": T0.isoformat(),
            "system_provisional_rating": "good",
        },
    )
    check(
        "cross-student event on S1 item -> 403 learning_item_owner_mismatch",
        r.status_code == 403
        and "does not match the owner" in r.text,
        f"status={r.status_code} body={r.text[:200]}",
    )

    # 10. Event linking another student's activity -> 403 (inventory D5).
    pa_s2 = post(
        "/api/v1/review/practice-activities",
        {
            "student_id": "S2",
            "learning_item_id": "LI000002",
            "activity_type": "blank_fill",
            "status": "completed",
            "occurred_at": T0.isoformat(),
        },
    )
    pa_s2_id = pa_s2.json()["activity_id"]
    r = post(
        "/api/v1/review/events",
        {
            "student_id": "S1",
            "learning_item_id": "LI000001",
            "practice_activity_id": pa_s2_id,
            "reviewed_at": T0.isoformat(),
            "system_provisional_rating": "good",
        },
    )
    check(
        "event linking S2 activity -> 403 practice_activity_owner_mismatch",
        r.status_code == 403
        and "belongs to student" in r.text,
        f"status={r.status_code} body={r.text[:200]}",
    )

    # 11. No writes on any rejection.
    with api.state.repository._connection_manager.connect() as connection:
        ev = connection.execute("SELECT COUNT(*) FROM review_events").fetchone()[0]
        pa = connection.execute("SELECT COUNT(*) FROM practice_activities").fetchone()[0]
        st = connection.execute(
            "SELECT COUNT(*) FROM learning_item_scheduler_states"
        ).fetchone()[0]
    check(
        "zero review rows after all rejections (append-only)",
        ev == 0 and pa == 2 and st == 0,
        f"review_events={ev} practice_activities={pa} scheduler_states={st}",
    )

    # 12. Happy path still works and writes exactly one row each.
    r = post(
        "/api/v1/review/events",
        {
            "student_id": "S1",
            "learning_item_id": "LI000001",
            "practice_activity_id": "PA-DUP",
            "reviewed_at": T0.isoformat(),
            "system_provisional_rating": "good",
            "learner_self_rating": "hard",
            "authentic_evidence_status": "insufficient",
            "provenance": {"source": "v1-probe", "batch": 1},
        },
    )
    body = r.json() if r.status_code == 200 else {}
    check(
        "happy path 200 with three rating channels + provenance",
        r.status_code == 200
        and body.get("system_provisional_rating") == "good"
        and body.get("learner_self_rating") == "hard"
        and body.get("final_scheduler_rating") == "hard"
        and body.get("rating_rule_version") == "rating-rule-v1.0.0"
        and body.get("scheduler_version") == "6.3.2",
        f"status={r.status_code} body keys={sorted(body.keys()) if body else None}",
    )
    with api.state.repository._connection_manager.connect() as connection:
        ev = connection.execute("SELECT COUNT(*) FROM review_events").fetchone()[0]
        st = connection.execute(
            "SELECT COUNT(*) FROM learning_item_scheduler_states"
        ).fetchone()[0]
    check(
        "happy path writes exactly one event + one state row",
        ev == 1 and st == 1,
        f"review_events={ev} scheduler_states={st}",
    )

    ok = sum(1 for r in RESULTS if r["ok"])
    print(f"\nSUMMARY {ok}/{len(RESULTS)} passed")
    raise SystemExit(0 if ok == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
