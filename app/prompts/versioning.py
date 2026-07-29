from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


PROMPT_VERSION = "feedback-prompt-v0.3.0"
SCHEMA_VERSION = "structured-feedback-v0.1.1"
SYSTEM_TEMPLATE_PATH = Path(__file__).with_name("system_prompt_v0_3_0.txt")
PROMPT_MANIFEST_PATH = Path(__file__).with_name("prompt_manifest_v0_3_0.json")
USER_TEMPLATE_CONTRACT = {
    "submission": [
        "essay_text", "writing_prompt", "genre", "draft_stage", "timed",
        "time_limit_minutes", "tool_use", "submitted_at",
    ],
    "metrics": "list[name,value]",
    "diagnoses": "list[diagnosis_id,category,evidence,source_metrics,interpretation,confidence,limitation,rule_version,kind]",
    "learner_history": [
        "comparability_status", "comparable_submission_count", "history_evidence",
        "summary", "limitations", "comparability_reasons",
    ],
    "learner_profile_snapshot": [
        "snapshot_id", "baseline_status", "included_submission_ids", "metric_trends",
        "persistent_issues", "recently_reduced_issues", "current_priority_candidates",
        "confidence_summary", "limitations", "analysis_version", "configuration_version",
    ],
    "required_schema": SCHEMA_VERSION,
}


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def system_template() -> str:
    return SYSTEM_TEMPLATE_PATH.read_text(encoding="utf-8")


def system_template_hash() -> str:
    return sha256_text(system_template())


def user_template_hash() -> str:
    return sha256_text(canonical_json(USER_TEMPLATE_CONTRACT))


def rendered_prompt_hash(messages: list[dict[str, str]]) -> str:
    return sha256_text(canonical_json(messages))


def validate_prompt_versioning() -> dict[str, str]:
    """Fail closed when template content drifts without a synchronized manifest/version update."""
    manifest = json.loads(PROMPT_MANIFEST_PATH.read_text(encoding="utf-8"))
    expected = {
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "system_template_file": SYSTEM_TEMPLATE_PATH.name,
        "system_template_hash": system_template_hash(),
        "user_template_hash": user_template_hash(),
    }
    mismatches = [
        name for name, value in expected.items() if manifest.get(name) != value
    ]
    if mismatches:
        raise RuntimeError(
            "Prompt version manifest mismatch for: " + ", ".join(mismatches)
            + ". Update the template version and manifest together."
        )
    return manifest
