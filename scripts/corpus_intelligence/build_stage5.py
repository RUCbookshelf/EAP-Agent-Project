"""Stage 5 reproducible build: snapshots, reference groups, distributions.

Usage:
  python scripts/corpus_intelligence/build_stage5.py

Requires the stage5 venv (spaCy en_core_web_sm 3.8.0, numpy).
Reads the prepared UTF-8 layer; writes:
  PREPARED/corpus-intelligence/feature_snapshots.csv   (per-document, outside git)
  docs/corpus-intelligence/l2/data/*                    (aggregates + versions)
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from scripts.corpus_paths import get_repo_root, get_corpus_root

sys.path.insert(0, str(get_repo_root()))

from app.corpus.distributions import DISTRIBUTION_ALGORITHM_VERSION, build_distribution
from app.corpus.features import FEATURE_SET_VERSION, extract_features_batch
from app.corpus.groups import REFERENCE_GROUP_VERSION, ReferenceGroupIndex
from app.corpus.resource import load_corpus_resource

REPO = get_repo_root()
READINESS = REPO / "docs" / "corpus-readiness" / "sweccl2"
PREPARED = get_corpus_root() / "PREPARED"
OUT = REPO / "docs" / "corpus-intelligence" / "l2" / "data"
SNAPSHOT_DIR = PREPARED / "corpus-intelligence"
DISTRIBUTION_VERSION = "reference-distributions-v0.1.0"
DUPLICATE_POLICY = "effective_sample_excludes_non_canonical_duplicate_members"

SNAPSHOT_FIELDS = [
    "document_id", "feature_id", "value", "unit", "analysis_status",
    "evidence_count", "feature_set_version", "source_variant", "manifest_hash", "reason",
]


def _strip_header(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].startswith("<STU"):
        return "\n".join(lines[1:])
    return text


def main() -> int:
    resource = load_corpus_resource()
    print(f"resource: {resource.corpus_package_id} hash={resource.manifest_hash[:16]}...")

    with open(READINESS / "data" / "corpus_manifest.csv", encoding="utf-8-sig", newline="") as f:
        manifest = list(csv.DictReader(f))
    index = ReferenceGroupIndex(manifest=manifest)

    raw_root = PREPARED / "utf8" / "WECCL20" / "RAW"
    texts: list[str] = []
    unusable: list[str] = []
    for row in manifest:
        path = raw_root / f"{row['document_id']}.txt"
        if not path.is_file():
            unusable.append(row["document_id"])
            continue
        data = path.read_bytes()
        if len(data) > 0 and data.count(b"\x00") == len(data):
            unusable.append(row["document_id"])
            continue
        texts.append(_strip_header(data.decode("utf-8")))

    print(f"extracting features from {len(texts)} usable RAW texts (unusable: {len(unusable)})")
    snapshots_batch = extract_features_batch(texts)

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for doc_id, snaps in zip((r["document_id"] for r in manifest if r["document_id"] not in unusable), snapshots_batch):
        for s in snaps:
            rows.append({
                "document_id": doc_id,
                "feature_id": s.feature_id,
                "value": "" if s.value is None else s.value,
                "unit": s.unit,
                "analysis_status": s.analysis_status,
                "evidence_count": s.evidence_count,
                "feature_set_version": s.feature_set_version,
                "source_variant": "raw",
                "manifest_hash": resource.manifest_hash,
                "reason": "" if s.analysis_status == "available" else "; ".join(s.limitations),
            })
    for doc_id in unusable:
        for fid in ["text_length_tokens", "sentence_length_mean", "t_unit_proxy", "connective_density"] + [
            f"pos_share_{cat}" for cat in ("noun", "verb", "adjective", "adverb", "pronoun",
                                           "determiner", "preposition", "conjunction", "numeral", "other")
        ]:
            rows.append({
                "document_id": doc_id,
                "feature_id": fid,
                "value": "",
                "unit": "",
                "analysis_status": "unavailable",
                "evidence_count": 0,
                "feature_set_version": FEATURE_SET_VERSION,
                "source_variant": "raw",
                "manifest_hash": resource.manifest_hash,
                "reason": "corrupt or missing RAW variant",
            })
    rows.sort(key=lambda r: (r["document_id"], r["feature_id"]))
    snapshot_path = SNAPSHOT_DIR / "feature_snapshots.csv"
    with open(snapshot_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SNAPSHOT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"snapshots: {len(rows)} rows -> {snapshot_path}")

    values_by_doc: dict[str, dict[str, float | None]] = defaultdict(dict)
    for r in rows:
        values_by_doc[r["document_id"]][r["feature_id"]] = float(r["value"]) if r["value"] != "" else None

    OUT.mkdir(parents=True, exist_ok=True)
    group_ids = index.approved_group_ids()
    membership_rows = [
        {"reference_group_id": gid, "document_id": doc, "role": "member"}
        for gid in group_ids
        for doc in index.membership(gid)
    ]
    with open(OUT / "reference_group_membership.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["reference_group_id", "document_id", "role"])
        writer.writeheader()
        writer.writerows(sorted(membership_rows, key=lambda r: (r["reference_group_id"], r["document_id"])))

    all_feature_ids = ["text_length_tokens", "sentence_length_mean", "t_unit_proxy", "connective_density"] + [
        f"pos_share_{cat}" for cat in ("noun", "verb", "adjective", "adverb", "pronoun",
                                       "determiner", "preposition", "conjunction", "numeral", "other")
    ]
    dist_lines: list[dict] = []
    for gid in group_ids:
        group = index.get(gid)
        members = index.membership(gid)
        for fid in all_feature_ids:
            vals = [values_by_doc.get(d, {}).get(fid) for d in members]
            dist = build_distribution(
                gid, fid, vals,
                index=index,
                feature_set_version=FEATURE_SET_VERSION,
                distribution_version=DISTRIBUTION_VERSION,
                manifest_hash=resource.manifest_hash,
                corpus_package_id=resource.corpus_package_id,
                duplicate_policy=DUPLICATE_POLICY,
                n_raw=group.n_raw,
            )
            dist_lines.append(dist.__dict__)
    with open(OUT / "reference_distributions.jsonl", "w", encoding="utf-8") as f:
        for line in sorted(dist_lines, key=lambda d: (d["reference_group_id"], d["feature_id"])):
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    feature_version = {
        "feature_set_version": FEATURE_SET_VERSION,
        "spacy_model": "en_core_web_sm",
        "spacy_model_version": "3.8.0",
        "features": all_feature_ids,
        "connective_resource": "connectives_v0_6_1.json",
    }
    group_version = {
        "reference_group_version": REFERENCE_GROUP_VERSION,
        "min_n": index.min_n,
        "fallback_hierarchy": ["prompt+timed", "prompt", "genre+timed", "genre", "UNAVAILABLE"],
        "duplicate_policy": DUPLICATE_POLICY,
        "approved_group_count": len(group_ids),
    }
    distribution_version = {
        "distribution_version": DISTRIBUTION_VERSION,
        "algorithm_version": DISTRIBUTION_ALGORITHM_VERSION,
        "statistics": ["n_effective", "n_missing", "mean", "median", "std", "iqr",
                       "quantiles_5_25_50_75_95", "min", "max"],
        "quantile_method": "numpy linear interpolation",
        "manifest_hash": resource.manifest_hash,
        "creation_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    for name, payload in [
        ("feature_set_version.json", feature_version),
        ("reference_group_version.json", group_version),
        ("distribution_version.json", distribution_version),
    ]:
        (OUT / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    available = sum(1 for d in dist_lines if d["availability"] == "available")
    limited = sum(1 for d in dist_lines if d["availability"] == "limited")
    print(f"distributions: {len(dist_lines)} records (available={available}, limited={limited})")
    print(f"approved groups: {len(group_ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())