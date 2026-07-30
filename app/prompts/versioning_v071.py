from __future__ import annotations

from pathlib import Path
import json

from .versioning_v04 import canonical_json, sha256_text


PROMPT_VERSION = "feedback-prompt-v0.7.1"
SCHEMA_VERSION = "structured-feedback-v0.7.1"
SYSTEM_TEMPLATE_PATH = Path(__file__).with_name("system_prompt_v0_7_1.txt")
PROMPT_MANIFEST_PATH = Path(__file__).with_name("prompt_manifest_v0_7_1.json")
USER_TEMPLATE_CONTRACT = {
    "submission": "current task metadata and essay",
    "diagnoses": "current calibrated selected priorities and verified strengths",
    "diagnostic_calibration": "v0.6.1 screened gate payload",
    "learner_model_context": [
        "current_learning_targets", "relevant_diagnostic_trajectories",
        "relevant_history_evidence", "data_sufficiency", "limitations",
    ],
    "longitudinal_facts": [
        "status", "scope", "comparable_task_count", "minimum_required",
        "revision_group_count", "draft_count", "history_evidence_ids", "limitations",
    ],
    "revision_snapshot": "optional validated revision evidence",
    "required_schema": SCHEMA_VERSION,
}


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
