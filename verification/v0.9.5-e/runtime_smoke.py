"""v0.9.5-E controlled FastAPI smoke against one guarded temporary database."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import httpx


OUTPUT = Path(__file__).with_name("runtime_smoke_result.json")
REPETITION_ESSAY = (
    "People should protect the environment. People should recycle more. "
    "People should save water. People should plant trees. People should reduce waste. "
    "People should use public transport. People should teach children about nature. "
    "People should value clean air."
)


def port_free(host: str, port: int) -> bool:
    with socket.socket() as sock:
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def wait_for(client: httpx.Client, path: str, predicate, timeout: float = 180.0) -> dict:
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            response = client.get(path, timeout=3)
            last = response
            if response.status_code == 200 and predicate(response.json()):
                return response.json()
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    detail = last.text[:200] if last is not None else "no response"
    raise RuntimeError(f"Timed out waiting for {path}: {detail}")


def start_api(python: str, host: str, port: int, env: dict[str, str], log_path: Path):
    log_handle = log_path.open("a", encoding="utf-8")
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = subprocess.Popen(
        [python, "-m", "uvicorn", "app.api.main:app", "--host", host, "--port", str(port)],
        cwd=ROOT,
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        creationflags=flags,
    )
    return process, log_handle


def stop_api(process, log_handle) -> None:
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    if log_handle is not None:
        log_handle.close()


def database_state(path: Path) -> dict:
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        tables = [
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
        return {
            "migration": int(connection.execute("PRAGMA user_version").fetchone()[0]),
            "table_count": len(tables),
            "essay_count": int(connection.execute("SELECT COUNT(*) FROM essays").fetchone()[0]),
            "analysis_run_count": int(connection.execute("SELECT COUNT(*) FROM analysis_runs").fetchone()[0]),
            "feedback_count": int(connection.execute("SELECT COUNT(*) FROM feedback_records").fetchone()[0]),
            "revision_group_count": int(connection.execute("SELECT COUNT(*) FROM revision_groups").fetchone()[0]),
            "practice_target_count": int(connection.execute("SELECT COUNT(*) FROM practice_targets").fetchone()[0]),
            "attempt_count": int(connection.execute("SELECT COUNT(*) FROM exercise_attempts").fetchone()[0]),
            "review_count": int(connection.execute("SELECT COUNT(*) FROM human_reviews").fetchone()[0]),
            "integrity": connection.execute("PRAGMA integrity_check").fetchone()[0],
            "foreign_key_violations": len(connection.execute("PRAGMA foreign_key_check").fetchall()),
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8015, type=int)
    args = parser.parse_args()

    assert "DATABASE_URL" not in os.environ
    assert os.getenv("PYTHON_DOTENV_DISABLED", "").casefold() in {"1", "true", "yes", "on"}
    assert os.getenv("LLM_PROVIDER") == "local"
    temp_root = Path(os.environ["V095E_TEMP_ROOT"]).resolve()
    db_path = Path(os.environ["DATABASE_PATH"]).resolve()
    assert db_path.is_relative_to(temp_root)
    assert db_path.exists()
    assert ROOT / "data" not in db_path.parents
    log_path = temp_root / "api.log"
    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    env["DATABASE_PATH"] = str(db_path)
    env["LLM_PROVIDER"] = "local"
    env["PYTHON_DOTENV_DISABLED"] = "1"
    base = f"http://{args.host}:{args.port}"
    result: dict[str, object] = {
        "status": "RUNNING",
        "temporary_database_path": str(db_path),
        "host": args.host,
        "port": args.port,
    }
    process = log_handle = None
    try:
        assert port_free(args.host, args.port)
        process, log_handle = start_api(args.python, args.host, args.port, env, log_path)
        result["first_pid"] = process.pid
        with httpx.Client(base_url=base, timeout=30) as client:
            live = wait_for(
                client,
                "/api/v1/system/live",
                lambda body: body.get("status") == "ok" and body.get("lifecycle_state") == "ready",
                30,
            )
            ready = wait_for(client, "/api/v1/system/ready", lambda body: body.get("ready") is True)
            health_response = client.get("/api/v1/system/health")
            health_response.raise_for_status()
            health = health_response.json()
            assert health["status"] == "ok"
            assert health["database_status"] == "connected"
            assert health["database_migration_version"] == 12
            result["lifecycle"] = {"live": live, "ready": ready, "health": health["status"]}

            first_payload = {
                "student_id": "V095E_SMOKE",
                "writing_prompt": "What actions matter for sustainability?",
                "genre": "argumentative essay",
                "draft_stage": "first draft",
                "timed": False,
                "tool_use": "none",
                "essay_text": REPETITION_ESSAY,
            }
            first = client.post("/api/v1/submissions", json=first_payload)
            assert first.status_code == 201, first.text[:300]
            first_body = first.json()
            first_id = first_body["submission_id"]
            assert first_id == 1
            assert first_body["analysis"]["analysis_run_id"] == "AR000001"
            assert first_body["feedback_result"]
            fetched = client.get(f"/api/v1/submissions/{first_id}")
            fetched.raise_for_status()
            assert fetched.json()["student_id"] == "V095E_SMOKE"

            second_payload = {
                **first_payload,
                "draft_stage": "revised draft",
                "revision_of_submission_id": first_id,
                "essay_text": (
                    "Residents should protect the environment by recycling, saving water, "
                    "planting trees, reducing waste, and using public transport."
                ),
            }
            second = client.post("/api/v1/submissions", json=second_payload)
            assert second.status_code == 201, second.text[:300]
            second_body = second.json()
            second_id = second_body["submission_id"]
            group_id = second_body["revision_snapshot"]["revision_group_id"]
            revision = client.get(f"/api/v1/revisions/{group_id}")
            comparison = client.get(f"/api/v1/revisions/{group_id}/comparison")
            assert revision.status_code == comparison.status_code == 200

            priority = next(
                item for item in first_body["diagnosis"]["improvement_priorities"]
                if item.get("selection_status") == "selected_priority"
            )
            target_response = client.post("/api/v1/practice-targets", json={
                "student_id": "V095E_SMOKE",
                "source_submission_id": first_id,
                "source_diagnosis_id": priority["diagnosis_id"],
                "target_code": "lexical_repetition_local",
                "target_label": priority["interpretation"],
                "gate_status": "selected",
            })
            assert target_response.status_code in {200, 201}, target_response.text[:300]
            target = target_response.json()
            exercise_response = client.post(
                f"/api/v1/practice-targets/{target['practice_target_id']}/exercises",
                json={"source_text": REPETITION_ESSAY},
            )
            assert exercise_response.status_code in {200, 201}
            exercise = exercise_response.json()
            attempt_response = client.post(
                f"/api/v1/exercises/{exercise['exercise_id']}/attempts",
                json={"student_id": "V095E_SMOKE", "response_text": "A valid response reducing repetition."},
            )
            assert attempt_response.status_code in {200, 201}
            attempt = attempt_response.json()
            assert attempt["evaluation"]["evaluation_id"].startswith("PE")

            profile = client.get("/api/v1/students/V095E_SMOKE/profile")
            progress = client.get("/api/v1/students/V095E_SMOKE/progress")
            journey = client.get("/api/v1/students/V095E_SMOKE/journey")
            assert profile.status_code == progress.status_code == journey.status_code == 200
            assert journey.json()["events"]

            review_response = client.post("/api/v1/research/reviews", json={
                "target_type": "diagnosis",
                "target_id": priority["diagnosis_id"],
                "reviewer_id": "V095E",
                "decision": "correct",
                "confidence": "medium",
                "comment": "runtime smoke",
            })
            assert review_response.status_code == 200
            review_id = review_response.json()["review_id"]
            reviews = client.get("/api/v1/research/reviews?target_type=diagnosis")
            assert reviews.status_code == 200
            assert any(item["review_id"] == review_id for item in reviews.json())
            result["workflows"] = {
                "submission_ids": [first_id, second_id],
                "analysis_run_id": first_body["analysis"]["analysis_run_id"],
                "revision_group_id": group_id,
                "practice_target_id": target["practice_target_id"],
                "exercise_id": exercise["exercise_id"],
                "attempt_id": attempt["attempt_id"],
                "review_id": review_id,
                "profile": profile.status_code,
                "progress": progress.status_code,
                "journey": journey.status_code,
            }

        stop_api(process, log_handle)
        process = log_handle = None
        time.sleep(1)
        assert port_free(args.host, args.port)
        first_state = database_state(db_path)
        assert first_state["migration"] == 12 and first_state["table_count"] == 33
        assert first_state["essay_count"] == 2
        assert first_state["analysis_run_count"] >= 2
        assert first_state["feedback_count"] == 2
        assert first_state["revision_group_count"] == 1
        assert first_state["practice_target_count"] == 1
        assert first_state["attempt_count"] == 1
        assert first_state["review_count"] == 1
        assert first_state["integrity"] == "ok" and first_state["foreign_key_violations"] == 0
        result["state_before_restart"] = first_state
        result["port_free_before_restart"] = True

        process, log_handle = start_api(args.python, args.host, args.port, env, log_path)
        result["restart_pid"] = process.pid
        with httpx.Client(base_url=base, timeout=30) as client:
            wait_for(client, "/api/v1/system/ready", lambda body: body.get("ready") is True)
            assert client.get(f"/api/v1/submissions/{first_id}").status_code == 200
            assert client.get(f"/api/v1/submissions/{second_id}").status_code == 200
            assert client.get(f"/api/v1/revisions/{group_id}").status_code == 200
            attempts = client.get(f"/api/v1/exercises/{exercise['exercise_id']}/attempts")
            assert attempts.status_code == 200 and len(attempts.json()) == 1
            reviews = client.get("/api/v1/research/reviews?target_type=diagnosis")
            assert reviews.status_code == 200 and any(item["review_id"] == review_id for item in reviews.json())
        result["restart_persistence"] = "PASS"
        result["status"] = "PASS"
        OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception:
        if log_path.exists():
            print(log_path.read_text(encoding="utf-8", errors="replace")[-4000:], file=sys.stderr)
        raise
    finally:
        stop_api(process, log_handle)
        time.sleep(1)
        result["port_free_after_cleanup"] = port_free(args.host, args.port)
        if result.get("status") == "PASS":
            OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
