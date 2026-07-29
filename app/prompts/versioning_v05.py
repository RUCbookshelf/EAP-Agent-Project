from __future__ import annotations

from .versioning_v04 import canonical_json, sha256_text
from pathlib import Path
import json


PROMPT_VERSION = "feedback-prompt-v0.5.0"
SCHEMA_VERSION = "structured-feedback-v0.5.0"
SYSTEM_TEMPLATE_PATH = Path(__file__).with_name("system_prompt_v0_5_0.txt")
PROMPT_MANIFEST_PATH = Path(__file__).with_name("prompt_manifest_v0_5_0.json")
USER_TEMPLATE_CONTRACT = {
    "base": "feedback-prompt-v0.4.0 analysis/submission/history contract",
    "revision_snapshot": [
        "revision_snapshot_id", "revision_group_id", "source_submission_id", "target_submission_id",
        "comparability", "paragraph_alignments", "sentence_alignments", "token_changes",
        "metric_changes", "diagnosis_trajectories", "uptake_candidates", "revision_evidence",
        "major_rewrite", "analyzer_versions", "algorithm_versions", "resource_versions",
        "configuration_version", "generated_at", "limitations",
    ],
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
    expected = {"prompt_version": PROMPT_VERSION, "schema_version": SCHEMA_VERSION,
                "system_template_file": SYSTEM_TEMPLATE_PATH.name,
                "system_template_hash": system_template_hash(), "user_template_hash": user_template_hash()}
    mismatches = [name for name, value in expected.items() if manifest.get(name) != value]
    if mismatches:
        raise RuntimeError("Prompt version manifest mismatch for: " + ", ".join(mismatches))
    return manifest

