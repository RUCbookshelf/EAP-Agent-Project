"""DP0-A diagnostic harness tests (audit-only; no provider calls, no production changes).

Covers the DP0-A required diagnostic-test surface:
- call-budget enforcement rules;
- secret / essay / prompt redaction in committed artifacts;
- frozen D0-01 essay hash verification;
- probe metadata capture;
- root-cause classification consistency with probe evidence;
- production-source integrity (no app/ or migrations/ changes).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import diagnostic_driver as driver


DP0_DIR = Path(__file__).resolve().parent
REPO_ROOT = DP0_DIR.parents[1]
MAX_DIRECT_CALLS = driver.MAX_DIRECT_CALLS


def load(name: str):
    return json.loads((DP0_DIR / name).read_text(encoding="utf-8"))


def test_frozen_d01_hash_verification():
    case = driver.frozen_d01()
    assert case["case_id"] == "D0-01"
    assert driver.sha256_text(case["essay_text"]).upper() == driver.FROZEN_D001_SHA256
    assert driver.FROZEN_D001_SHA256 == "F683F4C899BD0E2E146E9085D890CD8D1B2D659EF2083A0B087B1F816E410773"


def test_call_budget_limit_is_three():
    assert MAX_DIRECT_CALLS == 3
    budget = load("provider_call_budget.json")
    assert budget["direct_diagnostic_calls"] <= MAX_DIRECT_CALLS
    assert len(budget["calls"]) == budget["direct_diagnostic_calls"]


def test_probe_records_are_unique_and_ordered():
    probes = load("diagnostic_probes.json")["probes"]
    ids = [item["probe"] for item in probes]
    assert ids == sorted(ids)
    assert len(ids) == len(set(ids))
    assert "A" in ids and "B" in ids
    assert "C" not in ids, "Probe C must not run when Probe B restored completion"


def test_probe_metadata_capture():
    probes = {item["probe"]: item for item in load("diagnostic_probes.json")["probes"]}
    for probe in ("A", "B"):
        record = probes[probe]
        for field in ("response_id", "returned_model", "finish_reason",
                      "system_fingerprint", "usage", "content_length",
                      "content_sha256", "json_parse_status", "duration_seconds",
                      "essay_sha256", "max_tokens", "timeout"):
            assert field in record, f"probe {probe} missing {field}"
        assert record["model"] == "deepseek-v4-pro"
        assert record["essay_sha256"] == driver.FROZEN_D001_SHA256
    assert probes["A"]["usage"]["completion_tokens"] == 1800
    assert probes["A"]["finish_reason"] == "length"
    assert probes["B"]["finish_reason"] == "stop"
    assert probes["B"]["usage"].get("reasoning_tokens", 0) == 0


def test_redaction_no_credentials_or_essay_text_in_artifacts():
    sensitive_markers = [
        "sk-", "Bearer sk-", "DEEPSEEK_API_KEY=",
        "really practical",  # distinctive frozen D0-01 essay phrase
        "Governments should spend more money on buses",  # D0-02 phrase
        "essay_text\": \"",  # full essay payload must not be embedded
    ]
    for name in ("diagnostic_probes.json", "raw_response_metadata.json",
                 "provider_call_budget.json", "request_path_before.json",
                 "request_payload_inventory.json", "root_cause_classification.json",
                 "proposed_repair.json", "provider_documentation_check.json"):
        text = (DP0_DIR / name).read_text(encoding="utf-8")
        for marker in sensitive_markers:
            assert marker not in text, f"{name} contains sensitive marker {marker!r}"


def test_no_reasoning_content_stored():
    probes = {item["probe"]: item for item in load("diagnostic_probes.json")["probes"]}
    for probe in ("A", "B"):
        record = probes[probe]
        assert record.get("reasoning_content") is None, "raw reasoning content must never be stored"
        assert record.get("reasoning_content_length", 0) >= 0
        assert record.get("has_reasoning_content") in (True, False)


def test_root_cause_classification_consistent_with_probe_evidence():
    classification = load("root_cause_classification.json")
    probes = {item["probe"]: item for item in load("diagnostic_probes.json")["probes"]}
    assert classification["factor_classifications"]["thinking_mode_default"]["classification"] == "PROVEN_PRIMARY"
    assert classification["factor_classifications"]["output_token_budget"]["classification"] == "PROVEN_CONTRIBUTING"
    assert classification["factor_classifications"]["json_mode_request_compliance"]["classification"] == "RULED_OUT"
    assert probes["A"]["finish_reason"] == "length"
    assert probes["B"]["finish_reason"] == "stop"
    assert "thinking" in classification["primary_root_cause"].lower()


def test_proposed_repair_bounds():
    repair = load("proposed_repair.json")
    timeout = repair["time_budgets"]["per_call_timeout"]
    assert 30.0 <= timeout <= 90.0
    assert repair["time_budgets"]["two_attempt_budget_max"] < 150.0
    assert repair["time_budgets"]["submission_client_timeout"] == 180.0
    for change in repair["proposed_changes"]:
        assert change["file"].startswith(("app/llm/", "app/config/", "app/services/"))
    assert repair["unchanged_by_proposal"]["model"].startswith("deepseek-v4-pro")
    assert repair["unchanged_by_proposal"]["active_configuration_version"].startswith("config-v0.9.0")


def test_production_source_integrity():
    result = subprocess.run(
        ["git", "diff", "--name-only", "--", "app", "migrations"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "", f"unexpected app/migrations changes: {result.stdout}"
    untracked = subprocess.run(
        ["git", "status", "--porcelain", "--", "app", "migrations"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=30,
    )
    assert untracked.stdout.strip() == "", f"unexpected app/migrations status: {untracked.stdout}"


def test_driver_state_no_db_inserts():
    probes = load("diagnostic_probes.json")["probes"]
    for record in probes:
        assert record.get("provider_call_used", True) is True
        # Direct probe records must not contain submission/database artifacts.
        assert "submission_id" not in record
