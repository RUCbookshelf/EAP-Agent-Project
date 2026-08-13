"""V1 independent probe 4: single composition + namespace + semantic scans.

Static AST scans over app/review + app/api for forbidden semantics and
second-runtime markers; OpenAPI namespace check (5 review routes once, Wave-2
routes present); live API response key scan for forbidden tokens.
"""

from __future__ import annotations

import ast
import re
import sys
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


T0 = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
RESULTS: list[dict] = []


def check(name: str, ok: bool, detail: str) -> None:
    RESULTS.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


FORBIDDEN = [
    "mastery",
    "proficiency",
    "ability",
    "learning_gain",
    "learning_gains",
    "validated_acquisition",
    "score",
    "percentage",
    "cefr",
    "cet_band",
]


def scan_identifiers(path: Path, forbidden: list[str]) -> list[str]:
    hits: list[str] = []
    for py in path.rglob("*.py"):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        names = {
            node.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Name)
        } | {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
        } | {
            node.arg
            for node in ast.walk(tree)
            if isinstance(node, ast.arg)
        }
        for token in forbidden:
            for name in names:
                if re.fullmatch(token, name, flags=re.IGNORECASE):
                    hits.append(f"{py}:{token}={name}")
    return hits


def main() -> None:
    root = Path(__file__).resolve().parents[6]

    # 1. AST scan over app/review.
    hits = scan_identifiers(root / "app" / "review", FORBIDDEN)
    check(
        "app/review AST: no mastery/proficiency/ability/learning-gain/score/percentage/CEFR tokens",
        not hits,
        f"hits={hits}",
    )

    # 2. Second-runtime markers in app/review.
    markers = []
    for py in (root / "app" / "review").rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for marker in ["threading", "socket", "uvicorn", "event_bus", "EventBus"]:
            if marker in text and "no event bus" not in text:
                markers.append(f"{py.name}:{marker}")
    check(
        "app/review: no threading/socket/uvicorn/event-bus markers",
        not markers,
        f"markers={markers}",
    )

    # 3. One composition: single FSRSSchedulerAdapter() and ReviewService wiring.
    main_text = (root / "app" / "api" / "main.py").read_text(encoding="utf-8")
    check(
        "main.py contains exactly one FSRSSchedulerAdapter construction",
        main_text.count("FSRSSchedulerAdapter()") == 1,
        f"count={main_text.count('FSRSSchedulerAdapter()')}",
    )
    check(
        "main.py contains exactly one ReviewService construction",
        main_text.count("ReviewService(") == 1,
        f"count={main_text.count('ReviewService(')}",
    )

    # 4. fsrs imported only inside app/review.
    fsrs_imports = []
    for py in (root / "app").rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        if re.search(r"^\s*(from fsrs|import fsrs)", text, re.MULTILINE):
            fsrs_imports.append(str(py.relative_to(root)))
    check(
        "fsrs imported only in app/review",
        all("app\\review" in p or "app/review" in p for p in fsrs_imports),
        f"imports={fsrs_imports}",
    )

    # 5. OpenAPI namespace: 5 review routes exactly once; Wave-2 routes present.
    db_path = OUT / "compose.db"
    db_path.unlink(missing_ok=True)
    settings = Settings(
        database_path=db_path,
        llm_provider="local",
        deepseek_api_key=None,
        deepseek_base_url="https://example.invalid",
        deepseek_model="deepseek-test",
    )
    api = create_app(settings)
    client = TestClient(api, raise_server_exceptions=False)
    spec = client.get("/openapi.json").json()
    paths = sorted(spec["paths"].keys())
    review_routes = [p for p in paths if p.startswith("/api/v1/review/")]
    wave2_routes = [p for p in paths if "/wave2/" in p]
    check(
        "exactly 5 review routes in the one API namespace",
        len(review_routes) == 5,
        f"review routes={review_routes}",
    )
    check(
        "each review route defined exactly once",
        len(review_routes) == len(set(review_routes)),
        str(review_routes),
    )
    check(
        "Wave-2 routes still registered (18 expected)",
        len(wave2_routes) == 18,
        f"wave2 routes={len(wave2_routes)}",
    )

    # 6. Live API response key scan.
    wave2 = SQLiteWave2Repository(api.state.repository._connection_manager)
    wave2.save_learning_item(
        LearningItem(learning_item_id="LI000001", student_id="S1", category="grammar")
    )
    r = client.post(
        "/api/v1/review/events",
        json={
            "student_id": "S1",
            "learning_item_id": "LI000001",
            "reviewed_at": T0.isoformat(),
            "system_provisional_rating": "good",
            "learner_self_rating": "hard",
        },
    )
    assert r.status_code == 200, r.text
    response_body = r.json()

    def walk_keys(obj) -> list[str]:
        keys = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                keys.append(k.lower())
                keys.extend(walk_keys(v))
        elif isinstance(obj, list):
            for v in obj:
                keys.extend(walk_keys(v))
        return keys

    keys = walk_keys(response_body)
    leaked = [
        t
        for t in FORBIDDEN
        if any(re.search(rf"\b{t}\b", k, flags=re.IGNORECASE) for k in keys)
    ]
    check(
        "API event response keys carry no forbidden semantics",
        not leaked,
        f"keys={sorted(set(keys))} leaked={leaked}",
    )

    # 7. Schedule response also clean.
    sched = client.get("/api/v1/review/schedule/LI000001")
    sched_keys = walk_keys(sched.json()) if sched.status_code == 200 else []
    leaked2 = [
        t
        for t in FORBIDDEN
        if any(re.search(rf"\b{t}\b", k, flags=re.IGNORECASE) for k in sched_keys)
    ]
    check(
        "schedule response keys carry no forbidden semantics",
        not leaked2,
        f"status={sched.status_code} keys={sorted(set(sched_keys))} leaked={leaked2}",
    )

    ok = sum(1 for r in RESULTS if r["ok"])
    print(f"\nSUMMARY {ok}/{len(RESULTS)} passed")
    raise SystemExit(0 if ok == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
