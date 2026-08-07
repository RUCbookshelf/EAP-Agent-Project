"""WU4 — reference group definitions, duplicate policy, fallback resolution."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from app.corpus.errors import CorpusInvalidRequestError, CorpusUnavailableError

REFERENCE_GROUP_VERSION = "reference-groups-v0.1.0"
MIN_N = 30

REPO_ROOT = Path(r"A:\EAP Agent Project\writing-feedback-mvp")
READINESS_DATA = REPO_ROOT / "docs" / "corpus-readiness" / "sweccl2" / "data"


@dataclass(frozen=True)
class ReferenceGroup:
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
    version: str = REFERENCE_GROUP_VERSION


def _load_manifest() -> list[dict]:
    rows = []
    with open(READINESS_DATA / "corpus_manifest.csv", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def _load_duplicate_members() -> dict[str, str]:
    """Stable duplicate provenance: document_id -> duplicate_group_id.

    Canonical representative per group = lexicographically smallest
    document_id; remaining members are excluded from effective reference
    samples (policy recorded in WU3/WU4 docs).
    """
    members: dict[str, str] = {}
    with open(READINESS_DATA / "duplicate_report.csv", encoding="utf-8-sig", newline="") as f:
        for i, row in enumerate(csv.DictReader(f), start=1):
            group_id = f"DUP-{i:03d}"
            for member in row["members"].split(","):
                stem = Path(member).stem
                members[stem] = group_id
    return members


def _criteria_key(criteria: dict) -> tuple:
    return tuple(sorted((k, str(v)) for k, v in criteria.items()))


class ReferenceGroupIndex:
    """Versioned index over approved reference groups."""

    def __init__(
        self,
        *,
        manifest: list[dict] | None = None,
        duplicates: dict[str, str] | None = None,
        min_n: int = MIN_N,
        version: str = REFERENCE_GROUP_VERSION,
    ) -> None:
        self.min_n = min_n
        self.version = version
        self.manifest = manifest if manifest is not None else _load_manifest()
        self.duplicates = duplicates if duplicates is not None else _load_duplicate_members()
        self._canonical: dict[str, str] = {}
        for doc, group in self.duplicates.items():
            if group not in self._canonical or doc < self._canonical[group]:
                self._canonical[group] = doc
        self._build_groups()

    def _members(self, criteria: dict[str, str]) -> list[dict]:
        out = []
        for row in self.manifest:
            if all(row.get(k) == v for k, v in criteria.items()):
                out.append(row)
        return out

    def _effective(self, members: list[dict]) -> tuple[int, list[str]]:
        keep: list[str] = []
        for row in members:
            doc = row["document_id"]
            group = self.duplicates.get(doc)
            if group is None or doc == self._canonical[group]:
                keep.append(doc)
        return len(keep), keep

    def _build_groups(self) -> None:
        self.groups: dict[str, ReferenceGroup] = {}
        seen: set[tuple] = set()
        # prompt groups
        prompts = sorted({r["prompt_id"] for r in self.manifest})
        for prompt in prompts:
            criteria = {"prompt_id": prompt}
            self._add_group(criteria, seen)
        # genre groups
        for genre in ("argumentative", "expository"):
            self._add_group({"genre": genre}, seen)
        # timed/untimed
        for timed in ("timed", "untimed"):
            self._add_group({"timed_status": timed}, seen)
        # major type
        for major in ("english_major", "non_english_major"):
            self._add_group({"major_type": major}, seen)
        # grade
        for grade in ("1", "2", "3", "4"):
            self._add_group({"grade": grade}, seen)
        # entry year
        for year in ("2003", "2004", "2005", "2006", "2007"):
            self._add_group({"entry_year": year}, seen)
        # prompt x timed combos
        for prompt in prompts:
            for timed in ("timed", "untimed"):
                self._add_group({"prompt_id": prompt, "timed_status": timed}, seen)

    def _add_group(self, criteria: dict[str, str], seen: set) -> None:
        key = _criteria_key(criteria)
        if key in seen:
            return
        seen.add(key)
        members = self._members(criteria)
        n_raw = len(members)
        n_eff, _ = self._effective(members)
        gid = "RG-" + "-".join(f"{k}={v}" for k, v in sorted(criteria.items()))
        limitations = []
        if n_raw < self.min_n:
            limitations.append(f"n_raw {n_raw} below min-N {self.min_n}; standalone distribution unavailable")
        excluded = n_raw - n_eff
        if excluded:
            limitations.append(f"duplicate policy excluded {excluded} document(s) from effective sample")
        availability = "available" if n_eff >= self.min_n else "unavailable"
        if n_raw >= self.min_n and n_eff < self.min_n:
            availability = "limited"
        self.groups[gid] = ReferenceGroup(
            reference_group_id=gid,
            corpus_package_id="sweccl2-weccl20-v0.1.0",
            selection_criteria=dict(sorted(criteria.items())),
            n_raw=n_raw,
            n_effective=n_eff,
            supported_features=("text_length_tokens", "sentence_length_mean", "t_unit_proxy",
                                "connective_density", *[f"pos_share_{c}" for c in (
                                    "noun", "verb", "adjective", "adverb", "pronoun",
                                    "determiner", "preposition", "conjunction", "numeral", "other")]),
            metadata_coverage=round(n_raw / len(self.manifest), 4) if self.manifest else 0.0,
            limitations=tuple(limitations),
            availability=availability,
            fallback_parent=None,
        )

    def get(self, group_id: str) -> ReferenceGroup:
        if group_id not in self.groups:
            raise CorpusInvalidRequestError(f"unknown reference group: {group_id}")
        return self.groups[group_id]

    def resolve(self, *, prompt_id: str | None = None, timed_status: str | None = None,
                genre: str | None = None) -> tuple[ReferenceGroup, str | None]:
        """Deterministic fallback resolution with disclosure.

        Hierarchy: prompt+timed -> prompt -> genre+timed -> genre -> UNAVAILABLE.
        """
        candidates = []
        if prompt_id and timed_status:
            candidates.append(f"RG-prompt_id={prompt_id}-timed_status={timed_status}")
        if prompt_id:
            candidates.append(f"RG-prompt_id={prompt_id}")
        if genre is None and prompt_id:
            genre = "argumentative" if prompt_id.startswith("ARG") else "expository"
        if genre and timed_status:
            candidates.append(f"RG-genre={genre}-timed_status={timed_status}")
        if genre:
            candidates.append(f"RG-genre={genre}")
        for gid in candidates:
            group = self.groups.get(gid)
            if group is not None and group.n_effective >= self.min_n:
                fallback = None if gid == candidates[0] else candidates[0]
                return group, fallback
        raise CorpusUnavailableError(
            f"no reference group available for prompt={prompt_id} timed={timed_status} genre={genre}"
        )

    def membership(self, group_id: str) -> list[str]:
        group = self.get(group_id)
        criteria = group.selection_criteria
        members = self._members(criteria)
        n_eff, keep = self._effective(members)
        return keep

    def approved_group_ids(self) -> list[str]:
        return sorted(gid for gid, g in self.groups.items() if g.availability in ("available", "limited"))
