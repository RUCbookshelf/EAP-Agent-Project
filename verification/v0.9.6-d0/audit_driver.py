"""v0.9.6-D0 audit-only driver.

Uses only public production interfaces (POST /api/v1/submissions and public
read endpoints). No production monkeypatching, no database inserts outside
normal APIs, no fake analyzers. Essay text is never written to logs; only
case ids, hashes, timings, provider statuses, and evidence quotes (synthetic
audit text) are recorded in the JSON artifacts.

Enforces the preregistered maximum of 8 production submissions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT / "driver_state.json"
CORPUS_PATH = ROOT / "audit_corpus_essays.json"
RESULTS_PATH = ROOT / "corpus_results.json"
PREFLIGHT_PATH = ROOT / "preflight_result.json"
MAX_SUBMISSIONS = 8


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"submissions": [], "count": 0}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_cases() -> dict:
    raw = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    return {case["case_id"]: case for case in raw["corpus"]}


def submit(base_url: str, case: dict, student_id: str, kind: str, state: dict) -> dict:
    if state["count"] >= MAX_SUBMISSIONS:
        raise SystemExit(f"ABORT: submission limit {MAX_SUBMISSIONS} reached.")
    payload = {
        "student_id": student_id,
        "writing_prompt": case["writing_prompt"],
        "genre": case["genre"],
        "draft_stage": case["draft_stage"],
        "timed": case["timed"],
        "tool_use": case["tool_use"],
        "essay_text": case["essay_text"],
    }
    essay_hash = sha256_text(case["essay_text"])
    start = time.time()
    try:
        response = requests.post(
            f"{base_url}/api/v1/submissions", json=payload, timeout=(10, 180)
        )
    except requests.RequestException as exc:
        record = {
            "kind": kind, "case_id": case["case_id"], "student_id": student_id,
            "essay_sha256": essay_hash, "request_duration_seconds": round(time.time() - start, 2),
            "transport_error": f"{type(exc).__name__}: {str(exc)[:200]}",
        }
        state["submissions"].append(record)
        state["count"] += 1
        save_state(state)
        return record
    duration = round(time.time() - start, 2)
    if response.status_code != 201:
        record = {
            "kind": kind, "case_id": case["case_id"], "student_id": student_id,
            "essay_sha256": essay_hash, "request_duration_seconds": duration,
            "http_status": response.status_code,
            "http_body_preview": response.text[:500],
        }
        state["submissions"].append(record)
        state["count"] += 1
        save_state(state)
        return record
    data = response.json()
    record = summarize(base_url, kind, case, student_id, essay_hash, duration, data)
    state["submissions"].append({"kind": kind, "case_id": case["case_id"],
                                 "student_id": student_id, "submission_id": record["submission_id"]})
    state["count"] += 1
    save_state(state)
    return record


def summarize(base_url: str, kind: str, case: dict, student_id: str,
              essay_hash: str, duration: float, data: dict) -> dict:
    provider = data.get("feedback_result", {})
    provider_status = provider.get("feedback_provider_status") or {}
    calibration = data.get("diagnostic_calibration") or {}
    feedback = provider.get("feedback") or {}
    priorities = feedback.get("priority_feedback") or []
    diagnosis = data.get("diagnosis") or {}
    gate_priorities = (diagnosis.get("improvement_priorities") or [])
    evidence_checks = []
    essay_text = case["essay_text"]
    for item in priorities:
        quote = item.get("evidence_quote", "")
        evidence_checks.append({
            "diagnosis_id": item.get("diagnosis_id"),
            "category": item.get("category"),
            "quote_sha256": sha256_text(quote),
            "exact_substring_match": quote in essay_text,
            "normalized_match": " ".join(quote.split()) in " ".join(essay_text.split()),
        })
    return {
        "kind": kind,
        "case_id": case["case_id"],
        "student_id": student_id,
        "essay_sha256": essay_hash,
        "essay_word_count": len(essay_text.split()),
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
                "fallback_used": provider_status.get("fallback_used"),
                "fallback_reason_code": provider_status.get("fallback_reason_code"),
                "server_repair_used": provider_status.get("server_repair_used"),
                "server_repair_fields": provider_status.get("server_repair_fields"),
                "retry_count": provider_status.get("retry_count"),
            },
        },
        "analysis": {
            "analysis_run_id": (data.get("analysis") or {}).get("analysis_run_id"),
            "analyzer_id": (data.get("analysis") or {}).get("analyzer_id"),
            "analyzer_version": (data.get("analysis") or {}).get("analyzer_version"),
            "fallback_used": (data.get("analysis") or {}).get("fallback_used"),
            "configuration_version": (data.get("analysis") or {}).get("configuration_version"),
            "metric_result_count": len((data.get("analysis") or {}).get("metric_results") or []),
        },
        "diagnostic_gate": {
            "selected_priorities": [
                {
                    "diagnosis_id": item.get("diagnosis_id"),
                    "category": item.get("category"),
                    "confidence": item.get("confidence"),
                    "priority_score": item.get("priority_score"),
                    "evidence_relevance_status": item.get("evidence_relevance_status"),
                }
                for item in gate_priorities
            ],
            "monitored_count": len(diagnosis.get("monitored_signals") or []),
            "suppressed_count": len(diagnosis.get("suppressed_signals") or []),
        },
        "priority_result": {
            "selected": bool(priorities),
            "count": len(priorities),
            "items": [
                {
                    "diagnosis_id": item.get("diagnosis_id"),
                    "category": item.get("category"),
                    "evidence_quote": item.get("evidence_quote"),
                    "explanation": item.get("explanation"),
                    "revision_guidance": item.get("revision_guidance"),
                }
                for item in priorities
            ],
        },
        "evidence_checks": evidence_checks,
        "feedback_status": {
            "prompt_version": provider.get("prompt_version"),
            "schema_version": provider.get("schema_version"),
            "exercise_count": len(feedback.get("exercises") or []),
            "ui_empty_states": data.get("ui_empty_states") or [],
        },
        "history": {
            "comparability_status": (data.get("history") or {}).get("comparability_status"),
            "comparable_count": (data.get("history") or {}).get("comparable_submission_count"),
        },
        "longitudinal_assessment": {
            "status": (data.get("longitudinal_assessment") or {}).get("status"),
            "comparable_task_count": (data.get("longitudinal_assessment") or {}).get("comparable_task_count"),
        },
    }


def record_artifact(path: Path, records: list[dict]) -> None:
    existing = []
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(existing, dict):
            existing = existing.get("records", [])
    existing.extend(records)
    path.write_text(
        json.dumps({"audit_stage": "v0.9.6-D0", "records": existing},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="v0.9.6-D0 audit driver")
    parser.add_argument("command", choices=["preflight", "recover", "corpus", "repeat", "status"])
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--case", default=None, help="case id for repeat")
    parser.add_argument("--student", default=None, help="student id for repeat")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    state = load_state()
    cases = load_cases()

    if args.command == "status":
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return

    if args.command == "preflight":
        if any(item.get("kind") == "preflight" for item in state["submissions"]):
            print("Preflight already recorded; use corpus/repeat/status.")
            return
        record = submit(base_url, cases["D0-01"], "AUDIT-D0-01", "preflight", state)
        record_artifact(PREFLIGHT_PATH, [record])
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return

    if args.command == "recover":
        if not args.student:
            raise SystemExit("recover requires --student (one bounded preflight recovery attempt)")
        record = submit(base_url, cases["D0-01"], args.student, "preflight_retry", state)
        record_artifact(PREFLIGHT_PATH, [record])
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return
    if args.command == "corpus":
        for case_id in ["D0-01", "D0-02", "D0-03", "D0-04", "D0-05"]:
            done = {item.get("case_id") for item in state["submissions"]}
            if case_id in done:
                print(f"skip {case_id}: already submitted")
                continue
            record = submit(base_url, cases[case_id], cases[case_id]["student_id"], "corpus", state)
            record_artifact(RESULTS_PATH, [record])
            print(f"{case_id}: submission_id={record.get('submission_id')} "
                  f"provider={record.get('provider', {}).get('success_status')} "
                  f"priority={record.get('priority_result', {}).get('selected')}")
        return

    if args.command == "repeat":
        if not args.case or not args.student:
            raise SystemExit("repeat requires --case and --student")
        case = cases[args.case]
        record = submit(base_url, case, args.student, "repeat", state)
        record_artifact(RESULTS_PATH, [record])
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return


if __name__ == "__main__":
    main()

