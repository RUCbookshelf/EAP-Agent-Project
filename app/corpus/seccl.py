"""SECCL20 spoken-corpus throughput extension (PDW1 CORPUS).

Deterministic, resumable, governed processing of the SECCL20 spoken
transcript layer of SWECCL 2.0 under the same v0.1 feature contract used
for the written WECCL20 corpus. Numeric per-document snapshots stay outside
git; governed aggregates and provenance records are NON-RECONSTRUCTIVE
AGGREGATE ARTIFACTS with learner_exposure=research_only.

Duplicate policy: ``effective_sample_excludes_merged_task123_members``.
TASK123 files are merged reproductions of the same speakers' TASK1/TASK2/
TASK3 transcripts; they are still processed into per-document snapshots
(throughput) but are excluded from every reference-group effective sample.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.corpus.errors import CorpusInvalidRequestError

SECCL_PACKAGE_ID = "sweccl2-seccl20-v0.1.0"
SECCL_REFERENCE_GROUP_VERSION = "seccl-reference-groups-v0.1.0"
SECCL_DISTRIBUTION_VERSION = "seccl-reference-distributions-v0.1.0"
SECCL_MIN_N = 30
DUPLICATE_POLICY = "effective_sample_excludes_merged_task123_members"

_TASK_MARKER = re.compile(r"^TASK\s+\d+$")


def compute_seccl_manifest_hash(manifest_path: Path) -> str:
    """SHA-256 over the SECCL manifest CSV bytes (documented hash)."""
    return hashlib.sha256(manifest_path.read_bytes()).hexdigest()


def load_seccl_manifest(manifest_path: Path) -> list[dict]:
    """Read the canonical SECCL manifest (utf-8-sig, CSV)."""
    with open(manifest_path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def strip_seccl_header(text: str) -> str:
    """Remove the <SPOKEN> header line and standalone TASK n marker lines.

    The first line of every SECCL transcript is the ``<SPOKEN>...`` header
    (structural metadata).  Single-task files carry one ``TASK n`` marker
    line; merged TASK123 files carry three.  These markers are structural,
    not learner speech, and are removed before feature extraction so the
    same FeatureSetVersion contract applies deterministically.
    """
    lines = text.splitlines()
    out: list[str] = []
    for i, line in enumerate(lines):
        if i == 0 and line.startswith("<SPOKEN"):
            continue
        if _TASK_MARKER.match(line):
            continue
        out.append(line)
    return "\n".join(out)


def classify_eligibility(row: dict, prepared_root: Path) -> tuple[str, str]:
    """Classify one manifest row against the prepared UTF-8 layer.

    Returns (status, reason) with status in
    {"eligible", "blocked", "excluded"}.
    """
    path = prepared_root / row["source_relative_path"]
    if not path.is_file():
        return "blocked", "prepared file missing"
    data = path.read_bytes()
    if data and data.count(b"\x00") == len(data):
        return "excluded", "corrupt (all NUL bytes)"
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return "excluded", "UTF-8 decode failure"
    return "eligible", ""


@dataclass(frozen=True)
class SecclReferenceGroup:
    reference_group_id: str
    corpus_package_id: str
    selection_criteria: dict
    n_raw: int
    n_effective: int
    supported_features: tuple[str, ...]
    metadata_coverage: float
    limitations: tuple[str, ...]
    availability: str
    fallback_parent: str | None
    exposure_class: str = "research_only"
    learner_exposure: str = "research_only"
    version: str = SECCL_REFERENCE_GROUP_VERSION


class SecclReferenceGroupIndex:
    """Versioned index over approved SECCL reference groups.

    Dimensions: exam, task_folder (TASK1/2/3 only), year_folder, grade, and
    task_folder x year_folder.  TASK123 merged members are excluded from all
    effective samples (documented duplicate policy).  min-N = 30.
    """

    def __init__(
        self,
        *,
        manifest: list[dict],
        min_n: int = SECCL_MIN_N,
        version: str = SECCL_REFERENCE_GROUP_VERSION,
    ) -> None:
        self.min_n = min_n
        self.version = version
        self.manifest = manifest
        self._build_groups()

    def _members(self, criteria: dict[str, str]) -> list[dict]:
        return [
            r for r in self.manifest
            if all(r.get(k) == v for k, v in criteria.items())
        ]

    def _effective(self, members: list[dict]) -> tuple[int, list[str]]:
        keep: list[str] = []
        for r in members:
            if r["task_folder"] == "TASK123":
                continue
            keep.append(f"{r['task_folder']}/{r['transcript_id']}")
        return len(keep), keep

    def _add_group(self, criteria: dict[str, str], seen: set) -> None:
        key = tuple(sorted(criteria.items()))
        if key in seen:
            return
        seen.add(key)
        members = self._members(criteria)
        n_raw = len(members)
        n_eff, _ = self._effective(members)
        gid = "RG-seccl-" + "-".join(f"{k}={v}" for k, v in sorted(criteria.items()))
        limitations: list[str] = []
        if n_raw < self.min_n:
            limitations.append(f"n_raw {n_raw} below min-N {self.min_n}")
        excluded = n_raw - n_eff
        if excluded:
            limitations.append(
                f"duplicate policy excluded {excluded} merged TASK123 member(s)"
            )
        availability = "available" if n_eff >= self.min_n else "unavailable"
        self.groups[gid] = SecclReferenceGroup(
            reference_group_id=gid,
            corpus_package_id=SECCL_PACKAGE_ID,
            selection_criteria=dict(sorted(criteria.items())),
            n_raw=n_raw,
            n_effective=n_eff,
            supported_features=(
                "text_length_tokens", "sentence_length_mean", "t_unit_proxy",
                "connective_density",
                *[f"pos_share_{c}" for c in (
                    "noun", "verb", "adjective", "adverb", "pronoun",
                    "determiner", "preposition", "conjunction", "numeral",
                    "other")],
            ),
            metadata_coverage=round(n_raw / len(self.manifest), 4) if self.manifest else 0.0,
            limitations=tuple(limitations),
            availability=availability,
            fallback_parent=None,
        )

    def _build_groups(self) -> None:
        self.groups: dict[str, SecclReferenceGroup] = {}
        seen: set = set()
        self._add_group({"exam": "TEM4"}, seen)
        for task in ("TASK1", "TASK2", "TASK3"):
            self._add_group({"task_folder": task}, seen)
        for year in sorted({r["year_folder"] for r in self.manifest}):
            self._add_group({"year_folder": year}, seen)
        for task in ("TASK1", "TASK2", "TASK3"):
            for year in sorted({r["year_folder"] for r in self.manifest}):
                self._add_group({"task_folder": task, "year_folder": year}, seen)
        for grade in sorted({r["grade"] for r in self.manifest}):
            self._add_group({"grade": grade}, seen)

    def get(self, group_id: str) -> SecclReferenceGroup:
        if group_id not in self.groups:
            raise CorpusInvalidRequestError(f"unknown reference group: {group_id}")
        return self.groups[group_id]

    def membership(self, group_id: str) -> list[str]:
        group = self.get(group_id)
        members = self._members(group.selection_criteria)
        _, keep = self._effective(members)
        return keep

    def approved_group_ids(self) -> list[str]:
        return sorted(
            gid for gid, g in self.groups.items()
            if g.availability in ("available", "limited")
        )


class SecclBatchPlan:
    """Deterministic, resumable batch plan over the SECCL manifest.

    Partition assignment is deterministic by sorted row order
    (index % n == i), so fan-out writes are disjoint and parent-integrated.
    """

    def __init__(
        self,
        *,
        rows: list[dict],
        prepared_root: Path,
        already_processed: dict[tuple[str, str], str] | None = None,
        partition: tuple[int, int] | None = None,
    ) -> None:
        self.rows = sorted(rows, key=lambda r: (r["task_folder"], r["transcript_id"], r["source_relative_path"]))
        self.prepared_root = prepared_root
        self.already_processed = already_processed or {}
        self.partition = partition
        self._classify()

    def _classify(self) -> None:
        self.counts = {
            "total": len(self.rows),
            "eligible": 0,
            "blocked": 0,
            "excluded": 0,
            "already_processed": 0,
            "pending": 0,
        }
        eligible: list[dict] = []
        self.assigned_rows: list[dict] = []
        for i, row in enumerate(self.rows):
            if self.partition is not None and i % self.partition[1] != self.partition[0]:
                continue
            self.assigned_rows.append(row)
            status, _ = classify_eligibility(row, self.prepared_root)
            if status == "blocked":
                self.counts["blocked"] += 1
                continue
            if status == "excluded":
                self.counts["excluded"] += 1
                continue
            self.counts["eligible"] += 1
            key = (row["transcript_id"], row["task_folder"])
            if key in self.already_processed:
                self.counts["already_processed"] += 1
                continue
            eligible.append(row)
        self.pending_rows = eligible
        self.counts["pending"] = len(eligible)

    @staticmethod
    def _snapshot_csv(
        rows: list[dict],
        extractor,
        manifest_hash: str,
        texts: list[str],
    ) -> str:
        """Render per-document numeric snapshot rows as deterministic CSV."""
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=[
            "document_id", "feature_id", "value", "unit", "analysis_status",
            "evidence_count", "feature_set_version", "source_variant",
            "manifest_hash", "reason",
        ])
        writer.writeheader()
        snapshots_batch = extractor(texts)
        for row, snaps in zip(rows, snapshots_batch):
            doc_id = f"{row['task_folder']}/{row['transcript_id']}"
            for s in snaps:
                writer.writerow({
                    "document_id": doc_id,
                    "feature_id": s["feature_id"],
                    "value": "" if s["value"] is None else s["value"],
                    "unit": s["unit"],
                    "analysis_status": s["analysis_status"],
                    "evidence_count": s["evidence_count"],
                    "feature_set_version": s["feature_set_version"],
                    "source_variant": "raw",
                    "manifest_hash": manifest_hash,
                    "reason": "" if s["analysis_status"] == "available"
                    else "; ".join(s.get("limitations") or ()),
                })
        return buf.getvalue()
