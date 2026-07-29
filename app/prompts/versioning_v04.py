from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


PROMPT_VERSION = "feedback-prompt-v0.4.0"
SCHEMA_VERSION = "structured-feedback-v0.1.1"
SYSTEM_TEMPLATE_PATH = Path(__file__).with_name("system_prompt_v0_4_0.txt")
PROMPT_MANIFEST_PATH = Path(__file__).with_name("prompt_manifest_v0_4_0.json")
USER_TEMPLATE_CONTRACT = {
    "submission": ["essay_text", "writing_prompt", "genre", "draft_stage", "timed", "time_limit_minutes", "tool_use", "submitted_at"],
    "analysis_evidence": [
        "analysis_run_id", "analyzer_id", "analyzer_version", "backend", "nlp_library",
        "nlp_library_version", "nlp_model_name", "nlp_model_version", "parameters",
        "resource_versions", "configuration_version", "fallback_used", "fallback_reason",
        "input_quality", "lexical_features", "prompt_keywords", "detected_connectives",
        "syntactic_candidates", "metric_results", "limitations",
    ],
    "metrics": "list[name,value]",
    "diagnoses": "list[diagnosis_id,category,evidence,source_metrics,interpretation,confidence,limitation,rule_version,kind]",
    "learner_history": ["comparability_status", "comparable_submission_count", "history_evidence", "summary", "limitations", "comparability_reasons"],
    "learner_profile_snapshot": ["snapshot_id", "baseline_status", "included_submission_ids", "metric_trends", "persistent_issues", "recently_reduced_issues", "current_priority_candidates", "confidence_summary", "limitations", "analysis_version", "configuration_version"],
    "required_schema": SCHEMA_VERSION,
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def system_template() -> str:
    return SYSTEM_TEMPLATE_PATH.read_text(encoding="utf-8")


def system_template_hash() -> str:
    return sha256_text(system_template())


def user_template_hash() -> str:
    return sha256_text(canonical_json(USER_TEMPLATE_CONTRACT))


def rendered_prompt_hash(messages: list[dict[str, str]]) -> str:
    return sha256_text(canonical_json(messages))


def validate_prompt_versioning() -> dict[str, str]:
    manifest = json.loads(PROMPT_MANIFEST_PATH.read_text(encoding="utf-8"))
    expected = {
        "prompt_version": PROMPT_VERSION, "schema_version": SCHEMA_VERSION,
        "system_template_file": SYSTEM_TEMPLATE_PATH.name,
        "system_template_hash": system_template_hash(), "user_template_hash": user_template_hash(),
    }
    mismatches = [name for name, value in expected.items() if manifest.get(name) != value]
    if mismatches:
        raise RuntimeError("Prompt version manifest mismatch for: " + ", ".join(mismatches))
    return manifest

