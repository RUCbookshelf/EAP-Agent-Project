"""v0.9.6-DP0-B live production-path verification driver (audit-only).

Submits the three approved frozen D0 cases (D0-01, D0-02, D0-05) through the
normal POST /api/v1/submissions endpoint against the isolated audit API.
Enforces the DP0 production-submission cap, verifies frozen essay hashes
before every submission, redacts essay content from all records, and parses
the sanitized provider-call log lines for finish_reason/token/duration
evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT / "live_state.json"
RESULTS_PATH = ROOT / "live_provider_results.json"
CORPUS_PATH = ROOT.parent / "v0.9.6-d0" / "audit_corpus_essays.json"
FROZEN_HASHES = {
    "D0-01": "F683F4C899BD0E2E146E9085D890CD8D1B2D659EF2083A0B087B1F816E410773",
    "D0-02": "40A93EB7A698C92641CB4332C4D605FF6F246341A8D08F457E805557E1ADE0A3",
    "D0-05": "B5F1A9FBB908F4CD4BB674534F8285C52DB96FC3A6EE4EF174A2BBA6485B1BFE",
}
MAX_PRODUCTION_SUBMISSIONS = 5


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"submissions": [], "count": 0}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def load_cases() -> dict:
    raw = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    return {case["case_id"]: case for case in raw["corpus"]}


def read_log_tail(log_path: Path, offset: int) -> tuple[list[str], int]:
    if not log_path.exists():
        return [], offset
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    new_lines = lines[offset:]
    return new_lines, len(lines)


def parse_provider_lines(lines: list[str]) -> list[dict]:
    parsed = []
    for line in lines:
        if "writing_feedback.provider" not in line or "provider_call" not in line:
            continue
        fields = {}
        for part in line.split(" "):
            if "=" in part:
                key, _, value = part.partition("=")
                fields[key] = value
        parsed.append(fields)
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="DP0-B live driver")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--log-path", default=r"C:\tmp\v096dp0\api.err")
    parser.add_argument("cases", nargs="*", default=["D0-01", "D0-02", "D0-05"])
    parser.add_argument("--force", action="store_true", help="resubmit a case already in state")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    log_path = Path(args.log_path)
    state = load_state()
    cases = load_cases()

    for case_id in args.cases:
        if state["count"] >= MAX_PRODUCTION_SUBMISSIONS:
            raise SystemExit(f"ABORT: production submission limit {MAX_PRODUCTION_SUBMISSIONS} reached.")
        if any(item.get("case_id") == case_id for item in state["submissions"]) and not args.force:
            print(f"skip {case_id}: already submitted")
            continue
        case = cases[case_id]
        essay_hash = sha256_text(case["essay_text"]).upper()
        if essay_hash != FROZEN_HASHES[case_id]:
            raise SystemExit(f"ABORT: {case_id} hash mismatch ({essay_hash})")
        log_offset = len(log_path.read_text(encoding="utf-8", errors="replace").splitlines()) if log_path.exists() else 0
        payload = {
            "student_id": f"AUDIT-DP0-{case_id[-2:]}",
            "writing_prompt": case["writing_prompt"],
            "genre": case["genre"],
            "draft_stage": case["draft_stage"],
            "timed": case["timed"],
            "tool_use": case["tool_use"],
            "essay_text": case["essay_text"],
        }
        start = time.time()
        try:
            response = requests.post(f"{base_url}/api/v1/submissions", json=payload, timeout=(10, 180))
        except requests.RequestException as exc:
            record = {"case_id": case_id, "essay_sha256": essay_hash,
                      "transport_error": f"{type(exc).__name__}: {str(exc)[:200]}",
                      "request_duration_seconds": round(time.time() - start, 2)}
            state["submissions"].append({"case_id": case_id})
            state["count"] += 1
            save_state(state)
            print(json.dumps(record, ensure_ascii=False, indent=2))
            continue
        duration = round(time.time() - start, 2)
        new_lines, _ = read_log_tail(log_path, log_offset)
        provider_calls = parse_provider_lines(new_lines)
        if response.status_code != 201:
            record = {
                "case_id": case_id, "essay_sha256": essay_hash,
                "http_status": response.status_code,
                "http_body_preview": response.text[:500],
                "request_duration_seconds": duration,
                "provider_calls": provider_calls,
            }
            state["submissions"].append({"case_id": case_id})
            state["count"] += 1
            save_state(state)
            print(json.dumps(record, ensure_ascii=False, indent=2))
            continue
        data = response.json()
        provider = data.get("feedback_result", {})
        provider_status = provider.get("feedback_provider_status") or {}
        feedback = provider.get("feedback") or {}
        record = {
            "case_id": case_id,
            "student_id": payload["student_id"],
            "essay_sha256": essay_hash,
            "submission_id": data.get("submission_id"),
            "request_duration_seconds": duration,
            "provider": {
                "provider_name": provider.get("provider_name"),
                "model_name": provider.get("model_name"),
                "success_status": provider.get("success_status"),
                "validation_status": provider.get("validation_status"),
                "retry_count": provider.get("retry_count"),
                "fallback_reason": provider.get("fallback_reason"),
                "provider_status": {
                    "status": provider_status.get("status"),
                    "request_status": provider_status.get("request_status"),
                    "correction_attempted": provider_status.get("correction_attempted"),
                    "correction_validation_status": provider_status.get("correction_validation_status"),
                    "fallback_used": provider_status.get("fallback_used"),
                    "retry_count": provider_status.get("retry_count"),
                },
            },
            "provider_calls": provider_calls,
            "analysis": {
                "analyzer_version": (data.get("analysis") or {}).get("analyzer_version"),
                "metric_result_count": len((data.get("analysis") or {}).get("metric_results") or []),
            },
            "priority_result_observational": {
                "selected": bool(feedback.get("priority_feedback")),
                "count": len(feedback.get("priority_feedback") or []),
                "families": [item.get("category") for item in feedback.get("priority_feedback") or []],
            },
            "feedback_status": {
                "prompt_version": provider.get("prompt_version"),
                "schema_version": provider.get("schema_version"),
                "exercise_count": len(feedback.get("exercises") or []),
                "ui_empty_states": data.get("ui_empty_states") or [],
            },
            "longitudinal_assessment": {
                "status": (data.get("longitudinal_assessment") or {}).get("status"),
                "comparable_task_count": (data.get("longitudinal_assessment") or {}).get("comparable_task_count"),
            },
        }
        state["submissions"].append({"case_id": case_id, "submission_id": record["submission_id"]})
        state["count"] += 1
        save_state(state)
        existing = []
        if RESULTS_PATH.exists():
            existing = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                existing = existing.get("records", [])
        existing.append(record)
        RESULTS_PATH.write_text(
            json.dumps({"audit_stage": "v0.9.6-DP0-B", "records": existing},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
