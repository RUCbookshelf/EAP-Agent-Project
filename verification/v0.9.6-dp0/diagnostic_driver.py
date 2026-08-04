"""v0.9.6-DP0-A audit-only diagnostic driver.

Reproduces the production structured-feedback request payload (PromptBuilder
v0.7.1 path) and makes bounded DIRECT DeepSeek calls that capture raw
response metadata (response id, returned model, finish_reason, usage,
content length, JSON parse status) that the production adapter discards.

Rules enforced here:
- maximum 3 direct diagnostic provider calls across DP0-A;
- frozen D0-01 essay SHA-256 verified before every probe;
- no fallback, no database insert, no monkeypatching of production code;
- credentials, essay text, and prompt content are never printed or stored;
- only lengths, hashes, statuses, and structural summaries are recorded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from app.config import load_settings
from app.calf import append_product_fluency_metric
from app.calibration import DiagnosticCalibrationService
from app.configuration import ConfigurationPayload
from app.diagnosis import NlpHeuristicDiagnoser
from app.feedback import FeedbackReliabilityService
from app.learner import LearnerHistoryService, PriorRecordsPort
from app.llm.base import FeedbackContext
from app.models import EssaySubmission
from app.prompts import PromptBuilder
from app.services.factory import build_analyzer


ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT / "diagnostic_probes.json"
BUDGET_PATH = ROOT / "provider_call_budget.json"
CORPUS_PATH = ROOT.parent / "v0.9.6-d0" / "audit_corpus_essays.json"
FROZEN_D001_SHA256 = "F683F4C899BD0E2E146E9085D890CD8D1B2D659EF2083A0B087B1F816E410773"
MAX_DIRECT_CALLS = 3


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


class _EmptyPriorPort(PriorRecordsPort):
    def prior_records(self, submission: EssaySubmission) -> list[dict]:
        return []


def frozen_d01() -> dict:
    raw = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    case = next(item for item in raw["corpus"] if item["case_id"] == "D0-01")
    actual = sha256_text(case["essay_text"]).upper()
    if actual != FROZEN_D001_SHA256:
        raise SystemExit(
            f"ABORT: frozen D0-01 essay hash mismatch (expected {FROZEN_D001_SHA256}, got {actual})"
        )
    return case


def build_production_bundle(case: dict) -> dict:
    """Recreate the production v0.7.1 prompt payload for the frozen essay."""
    settings = load_settings()
    if not settings.deepseek_api_key:
        raise SystemExit("ABORT: DEEPSEEK_API_KEY is not configured")
    config = ConfigurationPayload()
    submission = EssaySubmission(
        student_id=case["student_id"],
        writing_prompt=case["writing_prompt"],
        genre=case["genre"],
        draft_stage=case["draft_stage"],
        timed=case["timed"],
        tool_use=case["tool_use"],
        essay_text=case["essay_text"],
    )
    analyzer = build_analyzer(settings)
    analysis = analyzer.analyze(
        submission.essay_text, writing_prompt=submission.writing_prompt,
        draft_stage=submission.draft_stage, tool_use=submission.tool_use,
    )
    analysis = append_product_fluency_metric(
        analysis, submission, accepted_timing_quality=config.calf_accepted_timing_quality
    )
    raw = NlpHeuristicDiagnoser().diagnose(analysis)
    calibration = DiagnosticCalibrationService(config).calibrate(
        submission, analysis, raw, prior_selected_categories=set()
    )
    diagnosis = calibration.selected_diagnosis
    history = LearnerHistoryService(_EmptyPriorPort()).summarize(
        0, submission, analysis, diagnosis
    )
    context = FeedbackContext(
        submission, analysis, diagnosis, history, None, None,
        calibration.prompt_payload() if calibration else None,
    )
    assessment = FeedbackReliabilityService(config).assessment(context)
    context = FeedbackContext(
        submission, analysis, diagnosis, history, None, None,
        calibration.prompt_payload() if calibration else None,
        assessment,
    )
    bundle = PromptBuilder().build(context)
    user_text = bundle.messages[1]["content"]
    return {
        "messages": bundle.messages,
        "prompt_version": bundle.prompt_version,
        "rendered_prompt_hash": bundle.rendered_prompt_hash,
        "system_chars": len(bundle.messages[0]["content"]),
        "user_chars": len(user_text),
        "total_chars": sum(len(m["content"]) for m in bundle.messages),
        "gate_selected_priorities": [
            {"diagnosis_id": item.diagnosis_id, "category": item.category,
             "confidence": item.confidence, "priority_score": item.priority_score}
            for item in diagnosis.improvement_priorities
        ],
        "payload_deltas_vs_production": [
            "learner_profile_snapshot is None in the probe (production computes a first-submission snapshot); learner_model_context is therefore None",
            "longitudinal_facts.comparable_task_count is 0 in the probe (production records 1 for the current submission)",
            "status/longitudinal semantics otherwise identical (unavailable)"
        ],
    }


def direct_call(bundle: dict, *, thinking: dict | None, max_tokens: int,
                timeout: float, settings) -> dict:
    payload = {
        "model": settings.deepseek_model,
        "messages": bundle["messages"],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    if thinking is not None:
        payload["thinking"] = thinking
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        f"{settings.deepseek_base_url}/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {settings.deepseek_api_key}",
                 "Content-Type": "application/json"},
        method="POST",
    )
    record = {
        "thinking": thinking,
        "max_tokens": max_tokens,
        "timeout": timeout,
        "request_body_chars": len(body),
    }
    start = time.time()
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
        record["http_status"] = 200
    except HTTPError as exc:
        body_bytes = exc.read()[:400]
        record["http_status"] = exc.code
        record["http_error_body_sha256"] = sha256_text(body_bytes.decode("utf-8", "replace"))
        record["http_error_type"] = "HTTPError"
        record["duration_seconds"] = round(time.time() - start, 2)
        return record
    except (URLError, TimeoutError) as exc:
        record["http_status"] = None
        record["error_class"] = type(exc).__name__
        record["error_message"] = str(exc)[:200]
        record["duration_seconds"] = round(time.time() - start, 2)
        return record
    record["duration_seconds"] = round(time.time() - start, 2)
    record["response_id"] = None
    record["returned_model"] = None
    record["finish_reason"] = None
    record["system_fingerprint"] = None
    record["usage"] = None
    try:
        parsed = json.loads(raw)
        record["json_parse_status"] = "success"
    except json.JSONDecodeError as exc:
        record["json_parse_status"] = "failed"
        record["json_error_offset"] = exc.pos
        record["json_error_message"] = f"{exc.msg} at line {exc.lineno} column {exc.colno}"
        parsed = None
    record["content_length"] = len(raw)
    record["content_sha256"] = sha256_text(raw)
    if parsed is not None:
        try:
            choice = parsed["choices"][0]
            record["response_id"] = parsed.get("id")
            record["returned_model"] = parsed.get("model")
            record["finish_reason"] = choice.get("finish_reason")
            record["system_fingerprint"] = parsed.get("system_fingerprint")
            record["usage"] = parsed.get("usage")
            message = choice.get("message") or {}
            content = (message.get("content") or "").strip()
            record["message_content_length"] = len(content)
            record["message_content_sha256"] = sha256_text(content)
            record["has_reasoning_content"] = "reasoning_content" in message
            record["reasoning_content_length"] = len(message.get("reasoning_content") or "")
        except (KeyError, IndexError, TypeError) as exc:
            record["response_structure_error"] = type(exc).__name__
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description="DP0-A diagnostic driver")
    parser.add_argument("probe", choices=["A", "B", "C", "correction-inventory"])
    args = parser.parse_args()
    probes = load_json(STATE_PATH, {"probes": []})
    budget = load_json(BUDGET_PATH, {"direct_diagnostic_calls": 0, "calls": []})
    if budget["direct_diagnostic_calls"] >= MAX_DIRECT_CALLS:
        raise SystemExit(f"ABORT: direct diagnostic call limit {MAX_DIRECT_CALLS} reached.")
    if any(item["probe"] == args.probe for item in probes["probes"]):
        raise SystemExit(f"ABORT: probe {args.probe} already recorded.")

    settings = load_settings()
    case = frozen_d01()
    bundle = build_production_bundle(case)

    if args.probe == "correction-inventory":
        correction = PromptBuilder().correction(
            type("B", (), {"messages": bundle["messages"], "user_payload": {},
                           "prompt_version": bundle["prompt_version"]})(),
            "priority_feedback[0] evidence_quote is not a verbatim essay substring",
        )
        correction_chars = sum(len(m["content"]) for m in correction.messages)
        print(json.dumps({
            "probe": "correction-inventory",
            "prompt_version": correction.prompt_version,
            "messages_count": len(correction.messages),
            "system_chars": len(correction.messages[0]["content"]),
            "user_chars": len(correction.messages[1]["content"]),
            "correction_message_chars": len(correction.messages[2]["content"]),
            "total_request_chars": correction_chars,
            "sample_failure_text_len": len("priority_feedback[0] evidence_quote is not a verbatim essay substring"),
            "provider_call_used": False,
        }, ensure_ascii=False, indent=2))
        return

    plan = {
        "A": {"thinking": None, "max_tokens": 1800, "timeout": 30.0,
              "label": "current production settings (metadata capture)"},
        "B": {"thinking": {"type": "disabled"}, "max_tokens": 1800, "timeout": 30.0,
              "label": "one-factor: explicitly disable thinking"},
        "C": {"thinking": {"type": "disabled"}, "max_tokens": 4096, "timeout": 30.0,
              "label": "one-factor (after B failure): output budget 4096, thinking disabled"},
    }[args.probe]
    if args.probe == "C":
        prior = {item["probe"]: item for item in probes["probes"]}
        if prior.get("B", {}).get("finish_reason") not in {"length", None} and \
                prior.get("B", {}).get("json_parse_status") != "failed":
            raise SystemExit("ABORT: probe C requires probe B to have failed with truncation/parse failure.")

    record = direct_call(
        bundle, thinking=plan["thinking"], max_tokens=plan["max_tokens"],
        timeout=plan["timeout"], settings=settings,
    )
    record["probe"] = args.probe
    record["probe_label"] = plan["label"]
    record["essay_sha256"] = FROZEN_D001_SHA256
    record["model"] = settings.deepseek_model
    record["prompt_version"] = bundle["prompt_version"]
    record["rendered_prompt_hash"] = bundle["rendered_prompt_hash"]
    record["system_prompt_chars"] = bundle["system_chars"]
    record["user_prompt_chars"] = bundle["user_chars"]
    record["total_request_chars"] = bundle["total_chars"]
    record["gate_selected_priorities"] = bundle["gate_selected_priorities"]
    record["payload_deltas_vs_production"] = bundle["payload_deltas_vs_production"]

    probes["probes"].append(record)
    save_json(STATE_PATH, probes)
    budget["direct_diagnostic_calls"] += 1
    budget["calls"].append({"probe": args.probe, "model": record["model"],
                            "http_status": record.get("http_status"),
                            "finish_reason": record.get("finish_reason"),
                            "json_parse_status": record.get("json_parse_status"),
                            "duration_seconds": record.get("duration_seconds")})
    save_json(BUDGET_PATH, budget)
    print(json.dumps(record, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
