"""WU7 — Corpus Intelligence query boundary tests (fixture-based)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app.corpus.errors import CorpusInvalidRequestError, CorpusUnavailableError
from app.corpus.groups import ReferenceGroupIndex
from app.corpus.intelligence import CorpusIntelligence
from app.corpus.resource import load_corpus_resource


def _make_fixture_resource(tmp_path: Path) -> Path:
    """Build a minimal resource package with one distribution record."""
    from tests.corpus.test_resource import _make_package

    readiness, prepared = _make_package(tmp_path, row_count=40)
    return readiness


def _make_intelligence(tmp_path: Path) -> CorpusIntelligence:
    readiness = _make_fixture_resource(tmp_path)
    resource = load_corpus_resource(readiness_dir=readiness, prepared_root=tmp_path / "prepared")
    # Build a small group index over fixture manifest with min-N 5
    import csv

    rows = []
    with open(readiness / "data" / "corpus_manifest.csv", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    # fix manifest rows so they carry prompt/genre metadata
    for i, row in enumerate(rows):
        row["document_id"] = f"W{i:04d}"
        row["prompt_id"] = "ARG17"
        row["genre"] = "argumentative"
        row["timed_status"] = "timed"
        row["grade"] = "1"
        row["major_type"] = "english_major"
        row["entry_year"] = "2006"
    index = ReferenceGroupIndex(manifest=rows, min_n=5)
    dist = {
        "reference_group_id": "RG-prompt_id=ARG17",
        "feature_id": "text_length_tokens",
        "feature_set_version": "corpus-features-v0.1.0",
        "reference_group_version": "reference-groups-v0.1.0",
        "distribution_version": "reference-distributions-v0.1.0",
        "corpus_package_id": "sweccl2-weccl20-v0.1.0",
        "manifest_hash": resource.manifest_hash,
        "n_effective": 40,
        "n_missing": 0,
        "n_raw": 40,
        "mean": 250.0,
        "median": 248.0,
        "std": 30.0,
        "iqr": 40.0,
        "quantiles": {"5": 200.0, "25": 230.0, "50": 248.0, "75": 270.0, "95": 300.0},
        "minimum": 180.0,
        "maximum": 340.0,
        "availability": "available",
        "validity_flags": [],
        "duplicate_policy": "effective_sample_excludes_non_canonical_duplicate_members",
    }
    data_dir = tmp_path / "intel-data"
    data_dir.mkdir()
    (data_dir / "reference_distributions.jsonl").write_text(
        json.dumps(dist) + "\n", encoding="utf-8"
    )
    return CorpusIntelligence(resource=resource, index=index, data_dir=data_dir)


def test_get_corpus_version(tmp_path: Path) -> None:
    ci = _make_intelligence(tmp_path)
    version = ci.get_corpus_version()
    assert version["corpus_package_id"] == "sweccl2-weccl20-v0.1.0"
    assert version["manifest_hash"]
    assert version["license_status"]


def test_get_feature_definition(tmp_path: Path) -> None:
    ci = _make_intelligence(tmp_path)
    definition = ci.get_feature_definition("text_length_tokens")
    assert definition["feature_id"] == "text_length_tokens"
    assert definition["feature_set_version"] == "corpus-features-v0.1.0"
    with pytest.raises(CorpusInvalidRequestError):
        ci.get_feature_definition("no_such_feature")


def test_get_reference_group(tmp_path: Path) -> None:
    ci = _make_intelligence(tmp_path)
    group = ci.get_reference_group("RG-prompt_id=ARG17")
    assert group.n_effective == 40
    with pytest.raises(CorpusInvalidRequestError):
        ci.get_reference_group("RG-unknown")


def test_resolve_with_fallback(tmp_path: Path) -> None:
    ci = _make_intelligence(tmp_path)
    group, fallback = ci.resolve_reference_group(prompt_id="ARG99")
    assert group.reference_group_id == "RG-genre=argumentative"
    assert fallback == "RG-prompt_id=ARG99"


def test_get_feature_distribution(tmp_path: Path) -> None:
    ci = _make_intelligence(tmp_path)
    result = ci.get_feature_distribution(
        reference_group_id="RG-prompt_id=ARG17", feature_id="text_length_tokens"
    )
    assert result.availability == "available"
    assert result.distribution is not None
    assert result.distribution.median == 248.0
    assert result.learner_exposure == "research_only"
    assert result.manifest_hash == ci.resource.manifest_hash


def test_missing_distribution_unavailable(tmp_path: Path) -> None:
    ci = _make_intelligence(tmp_path)
    with pytest.raises(CorpusUnavailableError):
        ci.get_feature_distribution(
            reference_group_id="RG-prompt_id=ARG17", feature_id="connective_density"
        )


def test_unknown_feature_rejected(tmp_path: Path) -> None:
    ci = _make_intelligence(tmp_path)
    with pytest.raises(CorpusInvalidRequestError):
        ci.get_feature_distribution(reference_group_id="RG-prompt_id=ARG17", feature_id="bad")
