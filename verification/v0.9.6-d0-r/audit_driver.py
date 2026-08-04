from __future__ import annotations

"""v0.9.6-D0-R audit driver (audit-only; no production changes).

Subcommands:
  hashes  - recompute the five frozen corpus SHA-256 hashes and compare them
            with the frozen manifest (writes corpus_hash_revalidation.json).
  submit  - submit frozen cases through POST /api/v1/submissions on the
            isolated D0-R audit API, enforcing the 9-submission and
            12-provider-attempt budgets and recording redacted metadata.

Full provider feedback payloads are cached locally under
C:\\tmp\\v096d0r\\payloads (never committed); committed artifacts contain
hashes, counts, and match booleans only.
"""

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
CORPUS_PATH = ROOT.parent / "v0.9.6-d0" / "audit_corpus_essays.json"
MANIFEST_PATH = ROOT.parent / "v0.9.6-d0" / "audit_corpus_manifest.json"
RESULTS_PATH = ROOT / "corpus_results.json"
METADATA_PATH = ROOT / "provider_metadata_results.json"
WORKSPACE = Path(r"C:\tmp\v096d0r")
STATE_PATH = WORKSPACE / "state.json"
PAYLOAD_DIR = WORKSPACE / "payloads"

MAX_SUBMISSIONS = 9
MAX_PROVIDER_ATTEMPTS = 12

FROZEN_HASHES = {
    "D0-01": "F683F4C899BD0E2E146E9085D890CD8D1B2D659EF2083A0B087B1F816E410773",
    "D0-02": "40A93EB7A698C92641CB4332C4D605FF6F246341A8D08F457E805557E1ADE0A3",
    "D0-03": "E774C4F33113CD968A9E261F7012B368DD26ADDAAE7E3114D2CA30C91736C432",
    "D0-04": "DD96EBBE276C98CD4300702CB4F9F9EF65A8C5D390389426AB035FAD2A9898D4",
    "D0-05": "B5F1A9FBB908F4CD4BB674534F8285C52DB96FC3A6EE4EF174A2BBA6485B1BFE",
}


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"submissions": [], "provider_attempt_count": 0}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_cases() -> dict[str, dict]:
    raw = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    return {case["case_id"]: case for case in raw["corpus"]}


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def read_log_tail(log_path: Path, offset: int) -> tuple[list[str], int]:
    if not log_path.exists():
        return [], offset
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[offset:], len(lines)


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


def provider_int(fields: dict, key: str):
    value = fields.get(key)
    try:
        return int(value) if value not in (None, "None") else None
    except (TypeError, ValueError):
        return value


def summarize_signal(signal: dict) -> dict:
    return {
        "diagnosis_id": signal.get("diagnosis_id"),
        "category": signal.get("category"),
        "priority_score": signal.get("priority_score"),
        "confidence": signal.get("confidence"),
        "evidence_relevance_status": signal.get("evidence_relevance_status"),
        "selection_status": signal.get("selection_status"),
        "selection_reason": signal.get("selection_reason"),
        "gate_result": signal.get("gate_result"),
    }


def classify_case(record: dict) -> str:
    provider = record["provider"]
    if provider["feedback_provider_status"].get("fallback_used") or provider.get("provider_name") == "local":
        return "FALLBACK_RESULT"
    if provider.get("success_status") != "success":
        return "PROVIDER_FAILURE"
    if provider.get("validation_status") != "passed":
        return "LIVE_PROVIDER_INVALID_RESULT"
    if record["priority_result"]["count"] == 0:
        return "LIVE_PROVIDER_SUCCESS_NO_PRIORITY"
    return "LIVE_PROVIDER_SUCCESS"


def run_hashes() -> None:
    cases = load_cases()
    manifest = load_manifest()
    manifest_hashes = {case["case_id"]: case["sha256"] for case in manifest["cases"]}
    checks = []
    all_match = True
    for case_id in sorted(cases):
        essay_hash = sha256_text(cases[case_id]["essay_text"])
        expected = manifest_hashes.get(case_id)
        match = essay_hash == expected
        all_match = all_match and match
        checks.append({
            "case_id": case_id,
            "computed_sha256": essay_hash,
            "frozen_manifest_sha256": expected,
            "match": match,
            "char_count": len(cases[case_id]["essay_text"]),
        })
    result = {
        "audit_stage": "v0.9.6-D0-R",
        "phase": "Phase 1 - corpus hash revalidation",
        "fixture": "verification/v0.9.6-d0/audit_corpus_essays.json",
        "all_hashes_match": all_match,
        "cases": checks,
    }
    (ROOT / "corpus_hash_revalidation.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    print(json.dumps(result, indent=2, ensure_ascii=True))
    if not all_match:
        raise SystemExit("ABORT: frozen corpus hash mismatch")


def submit_case(case_id: str, student_id: str, base_url: str, log_path: Path,
                state: dict, existing: list[dict], force: bool = False) -> None:
    if state["count"] >= MAX_SUBMISSIONS:
        raise SystemExit(f"ABORT: submission limit {MAX_SUBMISSIONS} reached.")
    if any(item.get("case_id") == case_id and item.get("student_id") == student_id for item in state["submissions"]) and not force:
        print(f"skip {case_id}: already submitted")
        return
    cases = load_cases()
    case = cases[case_id]
    essay_hash = sha256_text(case["essay_text"])
    if essay_hash != FROZEN_HASHES[case_id]:
        raise SystemExit(f"ABORT: {case_id} hash mismatch ({essay_hash})")
    log_offset = (
        len(log_path.read_text(encoding="utf-8", errors="replace").splitlines())
        if log_path.exists() else 0
    )
    payload = {
        "student_id": student_id,
        "writing_prompt": case["writing_prompt"],
        "genre": case["genre"],
        "draft_stage": case["draft_stage"],
        "timed": case["timed"],
        "tool_use": case["tool_use"],
        "essay_text": case["essay_text"],
    }
    start = time.time()
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        response = requests.post(f"{base_url}/api/v1/submissions", json=payload, timeout=(10, 180))
    except requests.RequestException as exc:
        duration = round(time.time() - start, 2)
        record = {
            "case_id": case_id, "student_id": student_id, "essay_sha256": essay_hash,
            "classification": "PROVIDER_FAILURE",
            "transport_error": f"{type(exc).__name__}: {str(exc)[:200]}",
            "request_started_at": started_at, "request_duration_seconds": duration,
        }
        state["submissions"].append({"case_id": case_id, "student_id": student_id})
        state["count"] += 1
        save_state(state)
        existing.append(record)
        write_results(existing)
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return
    duration = round(time.time() - start, 2)
    new_lines, _ = read_log_tail(log_path, log_offset)
    provider_calls = parse_provider_lines(new_lines)
    state["provider_attempt_count"] += len(provider_calls)
    if state["provider_attempt_count"] > MAX_PROVIDER_ATTEMPTS:
        raise SystemExit("ABORT: provider-attempt budget exceeded")
    save_state(state)

    if response.status_code != 201:
        record = {
            "case_id": case_id, "student_id": student_id, "essay_sha256": essay_hash,
            "classification": "PIPELINE_FAILURE",
            "http_status": response.status_code,
            "http_body_preview": response.text[:300],
            "request_started_at": started_at, "request_duration_seconds": duration,
            "provider_calls": provider_calls,
        }
        state["submissions"].append({"case_id": case_id, "student_id": student_id})
        state["count"] += 1
        save_state(state)
        existing.append(record)
        write_results(existing)
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return

    data = response.json()
    provider = data.get("feedback_result") or {}
    provider_status = provider.get("feedback_provider_status") or {}
    feedback = provider.get("feedback") or {}
    priority_items = feedback.get("priority_feedback") or []
    analysis = data.get("analysis") or {}
    diagnosis = data.get("diagnosis") or {}
    calibration = data.get("diagnostic_calibration") or {}

    gate_summary = {
        "selected_priorities": [summarize_signal(s) for s in calibration.get("selected_priorities") or []],
        "monitored_signals": [summarize_signal(s) for s in calibration.get("monitored_signals") or []],
        "suppressed_count": len(calibration.get("suppressed_diagnostics") or []),
        "verified_strength_count": len(calibration.get("verified_strengths") or []),
        "diagnosis_improvement_priorities": [
            summarize_signal(s) for s in diagnosis.get("improvement_priorities") or []
        ],
    }
    record = {
        "case_id": case_id,
        "student_id": student_id,
        "essay_sha256": essay_hash,
        "submission_id": data.get("submission_id"),
        "request_started_at": started_at,
        "request_ended_at": datetime.now(timezone.utc).isoformat(),
        "request_duration_seconds": duration,
        "provider": {
            "provider_name": provider.get("provider_name"),
            "model_name": provider.get("model_name"),
            "success_status": provider.get("success_status"),
            "validation_status": provider.get("validation_status"),
            "retry_count": provider.get("retry_count"),
            "fallback_reason": provider.get("fallback_reason"),
            "prompt_version": provider.get("prompt_version"),
            "schema_version": provider.get("schema_version"),
            "feedback_provider_status": {
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
            "analysis_run_id": analysis.get("analysis_run_id"),
            "analyzer_id": analysis.get("analyzer_id"),
            "analyzer_version": analysis.get("analyzer_version"),
            "metric_result_count": len(analysis.get("metric_results") or []),
            "fallback_used": analysis.get("fallback_used"),
        },
        "gate": gate_summary,
        "priority_result": {
            "selected": bool(priority_items),
            "count": len(priority_items),
            "families": [item.get("category") for item in priority_items],
            "diagnosis_ids": [item.get("diagnosis_id") for item in priority_items],
            "evidence_hashes": [
                {
                    "category": item.get("category"),
                    "diagnosis_id": item.get("diagnosis_id"),
                    "evidence_quote_sha256": sha256_text(item.get("evidence_quote") or ""),
                    "evidence_quote_length": len(item.get("evidence_quote") or ""),
                    "explanation_length": len(item.get("explanation") or ""),
                    "revision_guidance_length": len(item.get("revision_guidance") or ""),
                }
                for item in priority_items
            ],
        },
        "feedback_status": {
            "prompt_version": provider.get("prompt_version"),
            "schema_version": provider.get("schema_version"),
            "exercise_count": len(feedback.get("exercises") or []),
            "uncertainty_note_length": len(feedback.get("uncertainty_note") or ""),
            "ui_empty_states": data.get("ui_empty_states") or [],
        },
        "longitudinal_assessment": {
            "status": (data.get("longitudinal_assessment") or {}).get("status"),
            "comparable_task_count": (data.get("longitudinal_assessment") or {}).get("comparable_task_count"),
        },
    }
    record["classification"] = classify_case(record)
    state["submissions"].append({
        "case_id": case_id, "student_id": student_id,
        "submission_id": record["submission_id"],
    })
    state["count"] += 1
    save_state(state)
    existing.append(record)
    write_results(existing)

    PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)
    cache = {
        "case_id": case_id,
        "student_id": student_id,
        "submission_id": record["submission_id"],
        "essay_sha256": essay_hash,
        "response": data,
        "essay_text": case["essay_text"],
        "writing_prompt": case["writing_prompt"],
    }
    (PAYLOAD_DIR / f"{case_id}-{record['submission_id']}.json").write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(record, ensure_ascii=False, indent=2))


def write_results(existing: list[dict]) -> None:
    RESULTS_PATH.write_text(
        json.dumps({
            "audit_stage": "v0.9.6-D0-R",
            "records": existing,
            "note": "redacted; full provider payloads cached locally under C:\\tmp\\v096d0r\\payloads only",
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    METADATA_PATH.write_text(
        json.dumps({
            "audit_stage": "v0.9.6-D0-R",
            "records": [
                {
                    "case_id": r.get("case_id"),
                    "submission_id": r.get("submission_id"),
                    "provider_calls": r.get("provider_calls", []),
                }
                for r in existing
            ],
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="v0.9.6-D0-R audit driver")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("hashes")
    submit_parser = sub.add_parser("submit")
    submit_parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    submit_parser.add_argument("--log-path", default=str(WORKSPACE / "api.err"))
    submit_parser.add_argument("--student-prefix", default="AUDIT-D0R")
    submit_parser.add_argument("--student-id", default=None, help="explicit isolated audit student id (repeat/recovery cases)")
    submit_parser.add_argument("cases", nargs="+")
    submit_parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.command == "hashes":
        run_hashes()
        return

    state = load_state()
    state.setdefault("count", len(state.get("submissions", [])))
    existing = []
    if RESULTS_PATH.exists():
        existing = json.loads(RESULTS_PATH.read_text(encoding="utf-8")).get("records", [])
    for case_id in args.cases:
        student_id = args.student_id or f"{args.student_prefix}-{case_id[-2:] if case_id.startswith('D0-') else case_id}"
        submit_case(case_id, student_id, args.base_url.rstrip("/"), Path(args.log_path),
                    state, existing, force=args.force)
    print(json.dumps({
        "submissions_count": state["count"],
        "provider_attempt_count": state["provider_attempt_count"],
        "limits": {"max_submissions": MAX_SUBMISSIONS, "max_provider_attempts": MAX_PROVIDER_ATTEMPTS},
    }, indent=2))


if __name__ == "__main__":
    main()
