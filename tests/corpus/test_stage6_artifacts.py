"""Stage-6 machine-checkable artifact register and WU-E design record tests."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
L2_DATA = REPO_ROOT / "docs" / "corpus-intelligence" / "l2" / "data"

ALLOWED_CLASSES = {
    "RAW SOURCE",
    "NON-RECONSTRUCTIVE AGGREGATE ARTIFACT",
    "TEXTUAL/RECONSTRUCTIVE DERIVATIVE",
}
ALLOWED_DISPOSITIONS = {"PERMITTED", "CONDITIONAL", "FAIL-CLOSED"}


def _load(name: str) -> dict:
    with open(L2_DATA / name, encoding="utf-8") as f:
        return json.load(f)


def test_register_schema_and_classes() -> None:
    register = _load("stage6_artifact_register.json")
    assert register["goal_id"] == "CORPUS-STAGE6-WU-ABCE"
    assert register["binding_matrix"].endswith("CORPUS-LICENSING-REVIEW.md")
    assert register["authorization"].startswith("UD-04")
    assert set(register["artifact_classes"]) == ALLOWED_CLASSES
    assert set(register["dispositions"]) == ALLOWED_DISPOSITIONS
    assert register["fail_closed_categories"]


def test_no_stage6_artifact_is_textual_or_fail_closed() -> None:
    register = _load("stage6_artifact_register.json")
    for entry in register["artifacts"]:
        assert entry["artifact_class"] in ALLOWED_CLASSES
        assert entry["disposition"] in ALLOWED_DISPOSITIONS
        assert entry["artifact_class"] != "TEXTUAL/RECONSTRUCTIVE DERIVATIVE", entry["path"]
        assert entry["disposition"] != "FAIL-CLOSED", entry["path"]


def test_every_registered_artifact_exists_on_disk() -> None:
    register = _load("stage6_artifact_register.json")
    for entry in register["artifacts"]:
        path = REPO_ROOT / entry["path"]
        assert path.exists(), f"missing artifact: {entry['path']}"


def test_wu_e_design_record() -> None:
    design = _load("stage6_wu_e_evaluation_design.json")
    assert design["artifact_version"] == "stage6-wu-e-design-v0.1.0"
    assert design["artifact_class"] == "NON-RECONSTRUCTIVE AGGREGATE ARTIFACT"
    assert design["protected_block"]["count"] == 270
    assert design["protected_block"]["partitions_created"] is False
    assert design["protected_block"]["score_linkage"]["coverage"] == "270/270"
    assert design["protected_block"]["duplicate_policy"].startswith(
        "duplicate-group members are never split"
    )
    assert design["constraints"]
    assert design["licensing"]["fail_closed"]
    assert design["provenance"]["source_package"] == "sweccl2-weccl20-v0.1.0"
    assert len(design["provenance"]["manifest_hash"]) == 64


def test_wu_e_design_contains_no_corpus_text() -> None:
    design = _load("stage6_wu_e_evaluation_design.json")
    text = json.dumps(design)
    assert "<STU" not in text
    # no concrete corpus document identifiers and no raw-tree paths; the
    # corpus name and prompt-series labels appear only as provenance metadata
    assert re.search(r"(WARG|WEXP)\d", text) is None
    assert "WECCL20/" not in text and "WECCL20\\" not in text
    # document-series references are ID patterns only, never wording
    assert "WEXP####" in text
    assert "EXP01" in text
