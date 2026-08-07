"""WU1 — corpus resource registration tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.corpus.errors import CorpusResourceError
from app.corpus.resource import (
    MANIFEST_FILES,
    compute_manifest_hash,
    load_corpus_resource,
)


def _make_hash(data_dir: Path) -> str:
    h = hashlib.sha256()
    for name in MANIFEST_FILES:
        data = (data_dir / name).read_bytes()
        h.update(name.encode("utf-8"))
        h.update(b"\x00")
        h.update(data)
        h.update(b"\x00")
    return h.hexdigest()


def _make_package(tmp_path: Path, *, tamper: bool = False, row_count: int = 3) -> tuple[Path, Path]:
    readiness = tmp_path / "readiness"
    data = readiness / "data"
    data.mkdir(parents=True)
    for name in MANIFEST_FILES:
        content = b"a,b\n1,2\n" if name == "corpus_manifest.csv" else b"x\n"
        if name == "corpus_manifest.csv":
            content = ("a,b\n" + "\n".join(f"{i},{i}" for i in range(row_count)) + "\n").encode()
        (data / name).write_bytes(content)
    manifest_hash = _make_hash(data)
    if tamper:
        (data / "duplicate_report.csv").write_bytes(b"tampered")
    version = {
        "corpus_package_id": "sweccl2-weccl20-v0.1.0",
        "source_corpus": "SWECCL 2.0",
        "source_version": "2.0",
        "preparation_version": "0.1.0",
        "manifest_hash": manifest_hash,
        "usable_logical_text_count": row_count,
        "usable_variants": {"raw": row_count, "lemma": row_count, "tagged": row_count},
        "license_status": "PARTIALLY_DOCUMENTED",
        "known_limitations": ["fixture limitation"],
    }
    (readiness / "corpus_version.json").write_text(json.dumps(version), encoding="utf-8")
    prepared = tmp_path / "prepared"
    for variant in ("RAW", "LEMMA", "TAGGED"):
        (prepared / "WECCL20" / variant).mkdir(parents=True)
        for i in range(row_count):
            (prepared / "WECCL20" / variant / f"W{i:04d}.txt").write_text("text", encoding="utf-8")
    return readiness, prepared


def test_load_valid_resource(tmp_path: Path) -> None:
    readiness, prepared = _make_package(tmp_path)
    desc = load_corpus_resource(readiness_dir=readiness, prepared_root=prepared)
    assert desc.corpus_package_id == "sweccl2-weccl20-v0.1.0"
    assert desc.manifest_hash == _make_hash(readiness / "data")
    assert desc.manifest_row_count == 3
    assert desc.usable_variants == {"raw": 3, "lemma": 3, "tagged": 3}
    assert desc.license_status == "PARTIALLY_DOCUMENTED"
    assert desc.known_limitations == ("fixture limitation",)
    assert desc.preparation_version == "0.1.0"


def test_load_is_deterministic(tmp_path: Path) -> None:
    readiness, prepared = _make_package(tmp_path)
    a = load_corpus_resource(readiness_dir=readiness, prepared_root=prepared)
    b = load_corpus_resource(readiness_dir=readiness, prepared_root=prepared)
    assert a == b
    assert a.provenance == b.provenance


def test_tampered_manifest_hash_fails(tmp_path: Path) -> None:
    readiness, prepared = _make_package(tmp_path, tamper=True)
    with pytest.raises(CorpusResourceError, match="manifest hash mismatch"):
        load_corpus_resource(readiness_dir=readiness, prepared_root=prepared)


def test_unknown_package_id_fails(tmp_path: Path) -> None:
    readiness, prepared = _make_package(tmp_path)
    with pytest.raises(CorpusResourceError, match="unknown corpus package"):
        load_corpus_resource("other-package", readiness_dir=readiness, prepared_root=prepared)


def test_missing_prepared_root_fails(tmp_path: Path) -> None:
    readiness, _ = _make_package(tmp_path)
    with pytest.raises(CorpusResourceError, match="prepared corpus root missing"):
        load_corpus_resource(readiness_dir=readiness, prepared_root=tmp_path / "nope")


def test_manifest_row_count_mismatch_fails(tmp_path: Path) -> None:
    readiness, prepared = _make_package(tmp_path, row_count=5)
    version = json.loads((readiness / "corpus_version.json").read_text(encoding="utf-8"))
    version["usable_logical_text_count"] = 4
    (readiness / "corpus_version.json").write_text(json.dumps(version), encoding="utf-8")
    with pytest.raises(CorpusResourceError, match="row count"):
        load_corpus_resource(readiness_dir=readiness, prepared_root=prepared)


def test_missing_manifest_file_fails(tmp_path: Path) -> None:
    readiness, prepared = _make_package(tmp_path)
    (readiness / "data" / "holdout_candidates.csv").unlink()
    with pytest.raises(CorpusResourceError, match="manifest file missing"):
        load_corpus_resource(readiness_dir=readiness, prepared_root=prepared)


def test_compute_manifest_hash_matches_registered(tmp_path: Path) -> None:
    readiness, prepared = _make_package(tmp_path)
    desc = load_corpus_resource(readiness_dir=readiness, prepared_root=prepared)
    assert compute_manifest_hash(readiness / "data") == desc.manifest_hash
