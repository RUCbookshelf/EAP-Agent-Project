"""PDW1 CORPUS throughput expansion: deterministic SECCL20 batch build.

Processes the eligible unprocessed SECCL20 spoken-transcript layer of
SWECCL 2.0 through the frozen v0.1 feature contract, with:

  - deterministic row order (task_folder, transcript_id, source path)
  - resumable/idempotent run ledger (outside git, under PREPARED/)
  - per-document numeric snapshots outside git
  - optional disjoint partition fan-out (--partition i/n) with a
    parent-integrated --merge step
  - governed NON-RECONSTRUCTIVE AGGREGATE artifacts under
    docs/corpus-intelligence/l2/data/seccl/ with provenance and
    learner_exposure=research_only

Usage:
  $env:CORPUS_ROOT = "A:\\[Linguistics Data] Corpus\\SWECCL 2.0"
  python scripts/corpus_intelligence/build_seccl.py            # full run
  python scripts/corpus_intelligence/build_seccl.py --dry-run  # inventory only
  python scripts/corpus_intelligence/build_seccl.py --partition 0 4
  python scripts/corpus_intelligence/build_seccl.py --merge
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from scripts.corpus_paths import get_corpus_root, get_repo_root

sys.path.insert(0, str(get_repo_root()))

from app.corpus.distributions import DISTRIBUTION_ALGORITHM_VERSION, build_distribution
from app.corpus.features import FEATURE_SET_VERSION, extract_features_batch
from app.corpus.seccl import (
    SECCL_DISTRIBUTION_VERSION,
    SECCL_PACKAGE_ID,
    SECCL_REFERENCE_GROUP_VERSION,
    SecclBatchPlan,
    SecclReferenceGroupIndex,
    classify_eligibility,
    compute_seccl_manifest_hash,
    load_seccl_manifest,
    strip_seccl_header,
)

REPO = get_repo_root()
READINESS_DATA = REPO / "docs" / "corpus-readiness" / "sweccl2" / "data"
MANIFEST_PATH = READINESS_DATA / "seccl_manifest.csv"
PREPARED_UTF8 = get_corpus_root() / "PREPARED" / "utf8"
INTEL_OUT = REPO / "docs" / "corpus-intelligence" / "l2" / "data" / "seccl"
SNAPSHOT_DIR = get_corpus_root() / "PREPARED" / "corpus-intelligence"
SNAPSHOT_CSV = SNAPSHOT_DIR / "seccl_feature_snapshots.csv"
LEDGER_PATH = SNAPSHOT_DIR / "seccl_run_ledger.jsonl"


@dataclass
class SecclPaths:
    manifest: Path = MANIFEST_PATH
    prepared_root: Path = PREPARED_UTF8
    snapshot_dir: Path = SNAPSHOT_DIR
    snapshot_csv: Path = SNAPSHOT_CSV
    ledger: Path = LEDGER_PATH
    intel_out: Path = INTEL_OUT

SNAPSHOT_FIELDS = [
    "document_id", "feature_id", "value", "unit", "analysis_status",
    "evidence_count", "feature_set_version", "source_variant", "manifest_hash",
    "reason",
]
ALL_FEATURE_IDS = [
    "text_length_tokens", "sentence_length_mean", "t_unit_proxy",
    "connective_density",
    *[f"pos_share_{cat}" for cat in (
        "noun", "verb", "adjective", "adverb", "pronoun", "determiner",
        "preposition", "conjunction", "numeral", "other")],
]


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_ledger(path: Path) -> dict[tuple[str, str], dict]:
    result: dict[tuple[str, str], dict] = {}
    if not path.is_file():
        return result
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            result[(item["transcript_id"], item["task_folder"])] = item
    return result


def _append_ledger(path: Path, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _read_snapshot_rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _write_snapshot(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SNAPSHOT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _render_rows(
    rows: list[dict],
    texts: list[str],
    manifest_hash: str,
    paths: SecclPaths,
) -> list[dict]:
    out: list[dict] = []
    snapshots_batch = extract_features_batch(texts)
    for row, snaps in zip(rows, snapshots_batch):
        doc_id = f"{row['task_folder']}/{row['transcript_id']}"
        for s in snaps:
            out.append({
                "document_id": doc_id,
                "feature_id": s.feature_id,
                "value": "" if s.value is None else s.value,
                "unit": s.unit,
                "analysis_status": s.analysis_status,
                "evidence_count": s.evidence_count,
                "feature_set_version": s.feature_set_version,
                "source_variant": "raw",
                "manifest_hash": manifest_hash,
                "reason": "" if s.analysis_status == "available"
                else "; ".join(s.limitations),
            })
        _append_ledger(paths.ledger, {
            "transcript_id": row["transcript_id"],
            "task_folder": row["task_folder"],
            "file_sha256": _file_sha256(paths.prepared_root / row["source_relative_path"]),
            "status": "processed",
            "feature_set_version": FEATURE_SET_VERSION,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        })
    return out


def _build_aggregates(
    manifest_hash: str,
    package_manifest_rows: int,
    paths: SecclPaths,
) -> dict:
    """Build governed membership, distributions, and version records."""
    paths.intel_out.mkdir(parents=True, exist_ok=True)
    rows = _read_snapshot_rows(paths.snapshot_csv)
    values_by_doc: dict[str, dict[str, float | None]] = defaultdict(dict)
    for r in rows:
        values_by_doc[r["document_id"]][r["feature_id"]] = (
            float(r["value"]) if r["value"] != "" else None
        )

    manifest = load_seccl_manifest(paths.manifest)
    index = SecclReferenceGroupIndex(manifest=manifest)
    group_ids = index.approved_group_ids()

    membership_rows = [
        {"reference_group_id": gid, "document_id": doc, "role": "member"}
        for gid in group_ids
        for doc in index.membership(gid)
    ]
    with open(paths.intel_out / "seccl_reference_group_membership.csv", "w",
              encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["reference_group_id", "document_id", "role"]
        )
        writer.writeheader()
        writer.writerows(sorted(
            membership_rows,
            key=lambda r: (r["reference_group_id"], r["document_id"]),
        ))

    dist_lines: list[dict] = []
    for gid in group_ids:
        group = index.get(gid)
        members = index.membership(gid)
        for fid in ALL_FEATURE_IDS:
            vals = [values_by_doc.get(d, {}).get(fid) for d in members]
            dist = build_distribution(
                gid, fid, vals,
                index=index,
                feature_set_version=FEATURE_SET_VERSION,
                distribution_version=SECCL_DISTRIBUTION_VERSION,
                manifest_hash=manifest_hash,
                corpus_package_id=SECCL_PACKAGE_ID,
                duplicate_policy="effective_sample_excludes_merged_task123_members",
                n_raw=group.n_raw,
            )
            record = dist.__dict__
            record["learner_exposure"] = "research_only"
            record["exposure_class"] = "research_only"
            dist_lines.append(record)
    with open(paths.intel_out / "seccl_reference_distributions.jsonl", "w",
              encoding="utf-8") as f:
        for line in sorted(
            dist_lines,
            key=lambda d: (d["reference_group_id"], d["feature_id"]),
        ):
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    feature_version = {
        "feature_set_version": FEATURE_SET_VERSION,
        "spacy_model": "en_core_web_sm",
        "spacy_model_version": "3.8.0",
        "features": ALL_FEATURE_IDS,
        "connective_resource": "connectives_v0_6_1.json",
        "corpus_package_id": SECCL_PACKAGE_ID,
        "note": "same frozen v0.1 feature contract applied to SECCL20 spoken transcripts",
    }
    group_version = {
        "reference_group_version": SECCL_REFERENCE_GROUP_VERSION,
        "corpus_package_id": SECCL_PACKAGE_ID,
        "min_n": index.min_n,
        "duplicate_policy": "effective_sample_excludes_merged_task123_members",
        "approved_group_count": len(group_ids),
        "dimensions": ["exam", "task_folder", "year_folder", "grade",
                       "task_folder x year_folder"],
    }
    distribution_version = {
        "distribution_version": SECCL_DISTRIBUTION_VERSION,
        "algorithm_version": DISTRIBUTION_ALGORITHM_VERSION,
        "statistics": ["n_effective", "n_missing", "mean", "median", "std", "iqr",
                       "quantiles_5_25_50_75_95", "min", "max"],
        "quantile_method": "numpy linear interpolation",
        "manifest_hash": manifest_hash,
        "corpus_package_id": SECCL_PACKAGE_ID,
        "creation_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    descriptor = {
        "artifact_type": "corpus_package_descriptor",
        "version": "seccl-v0.1.0",
        "corpus_package_id": SECCL_PACKAGE_ID,
        "source_corpus": "SWECCL 2.0 (Spoken English Corpus of Chinese Learners 2.0)",
        "component": "SECCL20 spoken transcripts (TEM4)",
        "manifest": "seccl_manifest.csv",
        "manifest_hash": manifest_hash,
        "manifest_row_count": package_manifest_rows,
        "component": "SECCL20 spoken transcripts (TEM4)",
        "prepared_layer_status": "verified_present",
        "owner": "CORPUS",
        "generator": "scripts/corpus_intelligence/build_seccl.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "learner_exposure": "research_only",
        "exposure_class": "research_only",
        "license_status": "PARTIALLY_DOCUMENTED; internal research pipeline only",
        "duplicate_policy": "effective_sample_excludes_merged_task123_members",
    }
    for name, payload in [
        ("seccl_feature_set_version.json", feature_version),
        ("seccl_reference_group_version.json", group_version),
        ("seccl_distribution_version.json", distribution_version),
        ("seccl_package_descriptor.json", descriptor),
    ]:
        (paths.intel_out / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    available = sum(1 for d in dist_lines if d["availability"] == "available")
    return {
        "groups": len(group_ids),
        "distributions": len(dist_lines),
        "available": available,
        "membership_rows": len(membership_rows),
    }


def _merge_snapshots(paths: SecclPaths) -> None:
    """Parent-integrated merge of disjoint partition snapshot files."""
    merged: dict[tuple[str, str], dict] = {}
    partition_files = sorted(paths.snapshot_dir.glob("seccl_feature_snapshots.p*.csv"))
    if not partition_files:
        raise SystemExit("merge: no partition snapshot files found; nothing to merge")
    for p in partition_files:
        for r in _read_snapshot_rows(p):
            merged[(r["document_id"], r["feature_id"])] = r
    rows = sorted(
        merged.values(),
        key=lambda r: (r["document_id"], r["feature_id"]),
    )
    _write_snapshot(paths.snapshot_csv, rows)
    print(f"merge: {len(rows)} rows -> {paths.snapshot_csv}")


def _inventory_counts(paths: SecclPaths) -> dict:
    rows = load_seccl_manifest(paths.manifest)
    counts = {"total": len(rows), "eligible": 0, "blocked": 0, "excluded": 0}
    for r in rows:
        status, _ = classify_eligibility(r, paths.prepared_root)
        counts[status] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="inventory only")
    parser.add_argument("--partition", nargs=2, type=int, metavar=("I", "N"),
                        help="disjoint partition I of N")
    parser.add_argument("--merge", action="store_true",
                        help="merge partition snapshots and rebuild aggregates")
    parser.add_argument("--limit", type=int, default=None,
                        help="process at most N pending rows (resumable smoke)")
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH,
                        help="override SECCL manifest path (test isolation)")
    parser.add_argument("--prepared-root", type=Path, default=PREPARED_UTF8,
                        help="override prepared UTF-8 root (test isolation)")
    parser.add_argument("--snapshot-dir", type=Path, default=SNAPSHOT_DIR,
                        help="override snapshot/ledger directory (test isolation)")
    parser.add_argument("--out-dir", type=Path, default=INTEL_OUT,
                        help="override governed-aggregate output directory")
    args = parser.parse_args()

    paths = SecclPaths(
        manifest=args.manifest,
        prepared_root=args.prepared_root,
        snapshot_dir=args.snapshot_dir,
        snapshot_csv=args.snapshot_dir / "seccl_feature_snapshots.csv",
        ledger=args.snapshot_dir / "seccl_run_ledger.jsonl",
        intel_out=args.out_dir,
    )

    rows = load_seccl_manifest(paths.manifest)
    manifest_hash = compute_seccl_manifest_hash(paths.manifest)
    print(f"seccl package {SECCL_PACKAGE_ID} manifest_hash={manifest_hash[:16]}...")

    if args.dry_run:
        counts = _inventory_counts(paths)
        print(json.dumps(counts, indent=2))
        return 0

    ledger = _load_ledger(paths.ledger)
    already_processed: dict[tuple[str, str], str] = {}
    for key, item in ledger.items():
        if item.get("status") == "processed":
            already_processed[key] = item.get("file_sha256", "")
    partition = None if args.partition is None else tuple(args.partition)
    plan = SecclBatchPlan(
        rows=rows,
        prepared_root=paths.prepared_root,
        already_processed=already_processed,
        partition=partition,
    )
    print(json.dumps(plan.counts, indent=2))

    pending = plan.pending_rows
    if args.limit is not None:
        pending = pending[: args.limit]

    if pending:
        texts = []
        usable: list[dict] = []
        for r in pending:
            path = paths.prepared_root / r["source_relative_path"]
            text = strip_seccl_header(path.read_text(encoding="utf-8"))
            texts.append(text)
            usable.append(r)
        new_rows = _render_rows(usable, texts, manifest_hash, paths)
        if partition is not None:
            out_path = paths.snapshot_dir / f"seccl_feature_snapshots.p{partition[0]}.csv"
            existing = _read_snapshot_rows(out_path)
            existing.extend(new_rows)
            existing.sort(key=lambda r: (r["document_id"], r["feature_id"]))
            _write_snapshot(out_path, existing)
            print(f"partition {partition[0]}/{partition[1]}: {len(new_rows)} rows -> {out_path}")
        else:
            existing = _read_snapshot_rows(paths.snapshot_csv)
            existing.extend(new_rows)
            existing.sort(key=lambda r: (r["document_id"], r["feature_id"]))
            _write_snapshot(paths.snapshot_csv, existing)
            print(f"snapshots: {len(existing)} rows -> {paths.snapshot_csv}")
        print(f"newly processed: {len(usable)}")

    if args.merge:
        _merge_snapshots(paths)

    if partition is None and not args.dry_run:
        summary = _build_aggregates(manifest_hash, len(rows), paths)
        print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
