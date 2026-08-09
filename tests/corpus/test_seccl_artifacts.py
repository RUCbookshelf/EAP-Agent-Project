"""Machine-checkable verification of governed SECCL throughput artifacts."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SECCL_DATA = REPO_ROOT / "docs" / "corpus-intelligence" / "l2" / "data" / "seccl"

ALLOWED_CLASSES = {
    "RAW SOURCE",
    "NON-RECONSTRUCTIVE AGGREGATE ARTIFACT",
    "TEXTUAL/RECONSTRUCTIVE DERIVATIVE",
}
ALLOWED_DISPOSITIONS = {"PERMITTED", "CONDITIONAL", "FAIL-CLOSED"}


def _load(name: str) -> dict:
    with open(SECCL_DATA / name, encoding="utf-8") as f:
        return json.load(f)


def test_register_schema() -> None:
    register = _load("seccl_artifact_register.json")
    assert register["goal_id"] == "PDW1-CORPUS-THROUGHPUT-EXPANSION"
    assert set(register["artifact_classes"]) == ALLOWED_CLASSES
    assert set(register["dispositions"]) == ALLOWED_DISPOSITIONS
    assert register["fail_closed_categories"]


def test_no_registered_artifact_is_textual_or_fail_closed() -> None:
    register = _load("seccl_artifact_register.json")
    for entry in register["artifacts"]:
        assert entry["artifact_class"] != "TEXTUAL/RECONSTRUCTIVE DERIVATIVE", entry["path"]
        assert entry["disposition"] != "FAIL-CLOSED", entry["path"]


def test_every_registered_artifact_exists() -> None:
    register = _load("seccl_artifact_register.json")
    for entry in register["artifacts"]:
        path = REPO_ROOT / entry["path"]
        assert path.exists(), f"missing artifact: {entry['path']}"


def test_package_descriptor_provenance() -> None:
    d = _load("seccl_package_descriptor.json")
    assert d["corpus_package_id"] == "sweccl2-seccl20-v0.1.0"
    assert len(d["manifest_hash"]) == 64
    assert d["manifest_row_count"] == 2852
    assert d["owner"] == "CORPUS"
    assert d["learner_exposure"] == "research_only"
    assert d["exposure_class"] == "research_only"


def test_distributions_count_and_exposure() -> None:
    lines = [
        json.loads(line)
        for line in (SECCL_DATA / "seccl_reference_distributions.jsonl")
        .read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(lines) == 294  # 21 groups x 14 features
    for line in lines:
        assert line["learner_exposure"] == "research_only"
        assert line["exposure_class"] == "research_only"
        assert line["availability"] == "available"


def test_membership_excludes_merged_task123() -> None:
    with open(SECCL_DATA / "seccl_reference_group_membership.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows
    assert not any("TASK123" in r["document_id"] for r in rows)


def test_aggregates_contain_no_raw_text_or_paths() -> None:
    pattern = re.compile(
        r"(<SPOKEN|TASK \d|A:\\|PREPARED/|SECCL20/TEXTS|SWECCL 2\.0\\|"
        r"\b(proficiency|mastery|CEFR|ability|learning gain|level|score)\b)",
        re.IGNORECASE,
    )
    for path in SECCL_DATA.iterdir():
        if path.suffix in (".json", ".jsonl", ".csv"):
            text = path.read_text(encoding="utf-8", errors="replace")
            assert pattern.search(text) is None, f"leak in {path.name}"


def test_version_records() -> None:
    fsv = _load("seccl_feature_set_version.json")
    rgv = _load("seccl_reference_group_version.json")
    dv = _load("seccl_distribution_version.json")
    assert fsv["feature_set_version"] == "corpus-features-v0.1.0"
    assert len(fsv["features"]) == 14
    assert rgv["reference_group_version"] == "seccl-reference-groups-v0.1.0"
    assert rgv["approved_group_count"] == 21
    assert dv["distribution_version"] == "seccl-reference-distributions-v0.1.0"
    assert len(dv["manifest_hash"]) == 64
