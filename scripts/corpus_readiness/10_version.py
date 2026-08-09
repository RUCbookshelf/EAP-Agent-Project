"""Corpus version record (Goal section 25).

Computes corpus_version.json with a deterministic manifest hash over the key
machine-readable artifacts.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from scripts.corpus_paths import get_repo_root, get_corpus_root

REPO_ROOT = get_repo_root()
OUT_DIR = REPO_ROOT / "docs" / "corpus-readiness" / "sweccl2"
DATA = OUT_DIR / "data"

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


def manifest_hash() -> str:
    h = hashlib.sha256()
    for name in MANIFEST_FILES:
        data = (DATA / name).read_bytes()
        h.update(name.encode("utf-8"))
        h.update(b"\x00")
        h.update(data)
        h.update(b"\x00")
    return h.hexdigest()


def main() -> None:
    version = {
        "corpus_package_id": "sweccl2-weccl20-v0.1.0",
        "source_corpus": "SWECCL 2.0 (Spoken and Written English Corpus of Chinese Learners 2.0)",
        "source_version": "2.0 (ISBN 978-7-5600-8015-4; FLTRP 2008-12)",
        "preparation_version": "0.1.0",
        "physical_source_identity": {
            "physical_root": str(get_corpus_root()),
            "inventory_snapshot": "docs/corpus-readiness/sweccl2/data/physical_inventory_discovery_snapshot.csv",
            "source_file_count_at_discovery": 19858,
            "note": "manual PDF was present at discovery (recorded in snapshot); relocated out of the root afterwards",
        },
        "source_file_count": 19858,
        "usable_logical_text_count": 4950,
        "usable_variants": {"raw": 4949, "lemma": 4949, "tagged": 4950},
        "manifest_hash": manifest_hash(),
        "processing_tool_version": "corpus_readiness pipeline 0.1.0 (python 3.12.13, charset_normalizer)",
        "creation_timestamp": datetime.now(timezone.utc).isoformat(),
        "known_limitations": [
            "WARG2081 RAW/LEMMA variants are all-NUL corrupt; TAGGED variant usable",
            "TEM8 (TEM8 folder, documented 916 files) not present in this physical copy",
            "manual PDF relocated out of corpus root after discovery; hash preserved in discovery snapshot",
            "token totals differ from manual by <=0.1% due to counting tool differences",
            "240 documents appear in duplicate groups (exact/normalized text level)",
            "2 LEMMA files contain TreeTagger tab artifacts from Chinese characters",
        ],
        "license_status": "PARTIALLY_DOCUMENTED; external use REQUIRES_REVIEW",
    }
    (OUT_DIR / "corpus_version.json").write_text(json.dumps(version, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(version, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
