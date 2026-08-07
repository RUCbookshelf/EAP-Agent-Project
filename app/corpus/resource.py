"""WU1 — corpus resource registration.

Consumes the preparation-phase artifacts (corpus_version.json and the
machine-readable manifest files) without introducing a second corpus
manifest. Registration verifies package identity and the canonical manifest
hash; failures are explicit and safe.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from app.corpus.errors import CorpusResourceError

REPO_ROOT = Path(r"A:\EAP Agent Project\writing-feedback-mvp")
DEFAULT_READINESS_DIR = REPO_ROOT / "docs" / "corpus-readiness" / "sweccl2"
DEFAULT_PREPARED_ROOT = Path(r"A:\[Linguistics Data] Corpus\SWECCL 2.0\PREPARED\utf8")

MANIFEST_FILES = [
    "physical_inventory.csv",
    "corpus_manifest.csv",
    "derived_manifest.csv",
    "variant_pairing.csv",
    "quality_issues.csv",
    "duplicate_report.csv",
    "documentation_vs_physical.csv",
    "metadata_coverage.csv",
    "reference_group_candidates.csv",
    "feature_candidate_registry.csv",
    "holdout_candidates.csv",
]


def compute_manifest_hash(data_dir: Path) -> str:
    """Recompute the canonical composite hash over the 11 manifest files.

    Algorithm must match scripts/corpus_readiness/10_version.py exactly:
    for each file in fixed order, hash(name + NUL + content + NUL).
    """
    h = hashlib.sha256()
    for name in MANIFEST_FILES:
        path = data_dir / name
        if not path.is_file():
            raise CorpusResourceError(f"manifest file missing: {name}")
        data = path.read_bytes()
        h.update(name.encode("utf-8"))
        h.update(b"\x00")
        h.update(data)
        h.update(b"\x00")
    return h.hexdigest()


@dataclass(frozen=True)
class CorpusResourceDescriptor:
    """Immutable identity of one registered corpus package."""

    corpus_package_id: str
    source_corpus: str
    source_version: str
    preparation_version: str
    manifest_hash: str
    prepared_root: Path
    readiness_dir: Path
    usable_logical_text_count: int
    usable_variants: dict[str, int]
    license_status: str
    known_limitations: tuple[str, ...]
    loaded_from: Path
    manifest_row_count: int = field(compare=False)

    @property
    def provenance(self) -> dict:
        return {
            "corpus_package_id": self.corpus_package_id,
            "source_corpus": self.source_corpus,
            "source_version": self.source_version,
            "preparation_version": self.preparation_version,
            "manifest_hash": self.manifest_hash,
            "prepared_root": str(self.prepared_root),
        }


def _read_version_record(readiness_dir: Path) -> dict:
    path = readiness_dir / "corpus_version.json"
    if not path.is_file():
        raise CorpusResourceError(f"corpus_version.json not found: {path}")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise CorpusResourceError(f"corpus_version.json unreadable: {exc}") from exc
    if not isinstance(record, dict):
        raise CorpusResourceError("corpus_version.json is not an object")
    return record


def _manifest_row_count(data_dir: Path) -> int:
    path = data_dir / "corpus_manifest.csv"
    if not path.is_file():
        raise CorpusResourceError(f"corpus_manifest.csv not found: {path}")
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            return sum(1 for _ in csv.DictReader(f))
    except (OSError, csv.Error) as exc:
        raise CorpusResourceError(f"corpus_manifest.csv unreadable: {exc}") from exc


def _verify_prepared_root(prepared_root: Path, usable_variants: dict[str, int]) -> None:
    if not prepared_root.is_dir():
        raise CorpusResourceError(f"prepared corpus root missing: {prepared_root}")
    for variant, count in usable_variants.items():
        variant_dir = prepared_root / "WECCL20" / variant.upper()
        if not variant_dir.is_dir():
            raise CorpusResourceError(f"prepared variant directory missing: {variant_dir}")
        try:
            actual = len([p for p in variant_dir.iterdir() if p.is_file()])
        except OSError as exc:
            raise CorpusResourceError(f"prepared variant directory unreadable: {variant_dir} ({exc})") from exc
        if actual < count:
            raise CorpusResourceError(
                f"prepared variant count below usable expectation for {variant}: usable {count}, found {actual} (layer may include flagged-unusable files)"
            )


def load_corpus_resource(
    corpus_package_id: str = "sweccl2-weccl20-v0.1.0",
    *,
    readiness_dir: Path = DEFAULT_READINESS_DIR,
    prepared_root: Path = DEFAULT_PREPARED_ROOT,
) -> CorpusResourceDescriptor:
    """Load and verify one corpus package.

    Raises CorpusResourceError for unknown packages, missing artifacts,
    manifest-hash mismatch, or prepared-layer inconsistency.
    """
    record = _read_version_record(readiness_dir)
    recorded_id = record.get("corpus_package_id")
    if recorded_id != corpus_package_id:
        raise CorpusResourceError(
            f"unknown corpus package {corpus_package_id!r} (recorded: {recorded_id!r})"
        )
    data_dir = readiness_dir / "data"
    expected_hash = record.get("manifest_hash")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise CorpusResourceError("corpus_version.json manifest_hash invalid")
    actual_hash = compute_manifest_hash(data_dir)
    if actual_hash != expected_hash:
        raise CorpusResourceError(
            f"manifest hash mismatch: expected {expected_hash}, computed {actual_hash}"
        )
    usable = record.get("usable_variants")
    if not isinstance(usable, dict):
        raise CorpusResourceError("corpus_version.json usable_variants invalid")
    _verify_prepared_root(prepared_root, {k: int(v) for k, v in usable.items()})
    manifest_rows = _manifest_row_count(data_dir)
    expected_rows = int(record.get("usable_logical_text_count", 0))
    if manifest_rows != expected_rows:
        raise CorpusResourceError(
            f"corpus_manifest.csv row count {manifest_rows} != usable_logical_text_count {expected_rows}"
        )
    limitations = record.get("known_limitations", [])
    if not isinstance(limitations, list):
        limitations = []
    return CorpusResourceDescriptor(
        corpus_package_id=corpus_package_id,
        source_corpus=str(record.get("source_corpus", "")),
        source_version=str(record.get("source_version", "")),
        preparation_version=str(record.get("preparation_version", "")),
        manifest_hash=actual_hash,
        prepared_root=prepared_root,
        readiness_dir=readiness_dir,
        usable_logical_text_count=int(record.get("usable_logical_text_count", 0)),
        usable_variants={k: int(v) for k, v in usable.items()},
        license_status=str(record.get("license_status", "")),
        known_limitations=tuple(str(x) for x in limitations),
        loaded_from=readiness_dir / "corpus_version.json",
        manifest_row_count=manifest_rows,
    )


_CACHE: dict[str, CorpusResourceDescriptor] = {}


def get_corpus_resource(
    corpus_package_id: str = "sweccl2-weccl20-v0.1.0",
    *,
    readiness_dir: Path = DEFAULT_READINESS_DIR,
    prepared_root: Path = DEFAULT_PREPARED_ROOT,
) -> CorpusResourceDescriptor:
    """Cached, deterministic resource accessor for the internal boundary."""
    if corpus_package_id not in _CACHE:
        _CACHE[corpus_package_id] = load_corpus_resource(
            corpus_package_id, readiness_dir=readiness_dir, prepared_root=prepared_root
        )
    return _CACHE[corpus_package_id]
