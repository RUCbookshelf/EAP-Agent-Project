"""v0.9.5-B minimal FastAPI runtime smoke (isolated database).

Starts the production application against an isolated temporary SQLite
database with the local provider, verifies lifecycle endpoints, one
submission write/read, one Practice read, one Journey read, one Research
read, restart recovery, and clean port shutdown. No browser matrix.

Isolation: DATABASE_URL is cleared and DATABASE_PATH points into a fresh
temporary directory, so the running API can never touch the project's dev
database. The first essay id must be 1 on the fresh database.

Usage:
    python verification/v0.9.5-b/runtime_smoke.py --python <venv python>
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

import httpx

from scripts.service_processes import (
    require_free_port,
    start_api,
    stop_process,
    wait_http,
)


def _port_free(host: str, port: int) -> bool:
    with socket.socket() as sock:
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def _wait_ready(client: httpx.Client, base: str, timeout: float = 180.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            response = client.get(f"{base}/api/v1/system/ready", timeout=3)
            if response.status_code == 200 and response.json().get("ready") is True:
                return response.json()
        except httpx.HTTPError:
            pass
        time.sleep(1.0)
    raise RuntimeError("API did not become ready in time.")


def _isolated_db_essay_count(db_path: Path) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        return int(conn.execute("SELECT COUNT(*) FROM essays").fetchone()[0])
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="v0.9.5-B runtime smoke.")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8011, type=int)
    args = parser.parse_args()

    results: dict[str, object] = {}
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "v095b_smoke.db"
        env = os.environ.copy()
        env["DATABASE_URL"] = ""  # force fallback to DATABASE_PATH (isolation)
        env["DATABASE_PATH"] = str(db_path)
        env["LLM_PROVIDER"] = "local"
        env["API_BASE_URL"] = f"http://{args.host}:{args.port}"
        base = env["API_BASE_URL"]
        results["isolated_database_path"] = str(db_path)

        require_free_port(args.host, args.port)
        api = None
        try:
            # --- First start: lifecycle during startup ---
            api = start_api(args.python, args.host, args.port, env)
            wait_http(f"{base}/api/v1/system/live", timeout=30)
            with httpx.Client(base_url=base, timeout=10) as client:
                live = client.get("/api/v1/system/live")
                results["live_during_startup"] = live.json()

                ready_body = _wait_ready(client, base)
                results["ready_after_startup"] = ready_body

                health = client.get("/api/v1/system/health")
                health_body = health.json()
                results["health_after_startup"] = {
                    "status": health_body.get("status"),
                    "database_status": health_body.get("database_status"),
                    "database_migration_version": health_body.get("database_migration_version"),
                    "application_version": health_body.get("application_version"),
                    "active_analyzer": health_body.get("active_analyzer"),
                }
                assert health.status_code == 200
                assert health_body["status"] == "ok"
                assert health_body["database_status"] == "connected"
                assert health_body["database_migration_version"] == 12

                version = client.get("/api/v1/system/version")
                results["active_configuration"] = version.json().get("active_configuration_version")
                assert version.json()["active_configuration_version"] == "config-v0.9.0"

                submission_payload = {
                    "student_id": "V095B_SMOKE",
                    "writing_prompt": "Should cities add more parks?",
                    "genre": "argumentative essay",
                    "draft_stage": "first draft",
                    "timed": False,
                    "tool_use": "none",
                    "essay_text": (
                        "Cities should add more parks because parks give residents space to "
                        "exercise and relax. Therefore, city leaders should protect green spaces."
                    ),
                }
                created = client.post("/api/v1/submissions", json=submission_payload)
                assert created.status_code == 201, created.text[:300]
                submission_id = created.json()["submission_id"]
                assert submission_id == 1, f"isolated DB must start at essay id 1, got {submission_id}"
                results["submission_write"] = {"status": 201, "submission_id": submission_id}

                fetched = client.get(f"/api/v1/submissions/{submission_id}")
                assert fetched.status_code == 200
                results["submission_read"] = {"status": fetched.status_code}

                practice = client.get("/api/v1/students/V095B_SMOKE/practice-targets")
                assert practice.status_code == 200
                results["practice_read"] = {"status": practice.status_code, "count": len(practice.json())}

                journey = client.get("/api/v1/students/V095B_SMOKE/journey")
                assert journey.status_code == 200
                results["journey_read"] = {"status": journey.status_code}

                research = client.get("/api/v1/research/export/schema")
                assert research.status_code == 200
                results["research_read"] = {"status": research.status_code}

            # Confirmation that the API really used the isolated database.
            essay_count = _isolated_db_essay_count(db_path)
            results["isolated_db_essay_count"] = essay_count
            assert essay_count == 1

            # --- Failure injection: kill the API process ---
            stop_process(api)
            api = None
            time.sleep(1.0)
            port_freed = _port_free(args.host, args.port)
            results["port_freed_after_kill"] = port_freed
            assert port_freed, "Port was still in use after process stop."

            # --- Recovery: restart against the same isolated database ---
            api = start_api(args.python, args.host, args.port, env)
            wait_http(f"{base}/api/v1/system/live", timeout=30)
            with httpx.Client(base_url=base, timeout=10) as client:
                ready_body = _wait_ready(client, base)
                results["ready_after_recovery"] = ready_body
                health = client.get("/api/v1/system/health")
                health_body = health.json()
                results["health_after_recovery"] = {
                    "status": health_body.get("status"),
                    "database_status": health_body.get("database_status"),
                }
                assert health_body["status"] == "ok"
                assert health_body["database_status"] == "connected"
        finally:
            stop_process(api)
            time.sleep(1.0)
            results["port_free_after_clean_stop"] = _port_free(args.host, args.port)

    results["status"] = "PASS"
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
