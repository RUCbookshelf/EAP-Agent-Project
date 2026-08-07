"""WU6 — descriptive reference distributions with validity flags."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from app.corpus.groups import MIN_N, ReferenceGroupIndex

DISTRIBUTION_ALGORITHM_VERSION = "distribution-algorithm-v0.1.0"


@dataclass(frozen=True)
class ReferenceDistribution:
    reference_group_id: str
    feature_id: str
    feature_set_version: str
    reference_group_version: str
    distribution_version: str
    corpus_package_id: str
    manifest_hash: str
    n_effective: int
    n_missing: int
    n_raw: int
    mean: float | None
    median: float | None
    std: float | None
    iqr: float | None
    quantiles: dict[str, float]
    minimum: float | None
    maximum: float | None
    availability: str
    validity_flags: tuple[str, ...]
    duplicate_policy: str


def _quantiles(values: list[float]) -> dict[str, float]:
    arr = np.asarray(sorted(values), dtype=float)
    return {str(p): float(np.percentile(arr, p)) for p in (5, 25, 50, 75, 95)}


def _stats(values: list[float]) -> dict:
    arr = np.asarray(values, dtype=float)
    q = _quantiles(values)
    return {
        "mean": float(arr.mean()),
        "median": q["50"],
        "std": float(arr.std(ddof=1)) if len(arr) > 1 else 0.0,
        "iqr": q["75"] - q["25"],
        "quantiles": q,
        "minimum": float(arr.min()),
        "maximum": float(arr.max()),
    }


def build_distribution(
    group_id: str,
    feature_id: str,
    values: list[float | int | None],
    *,
    index: ReferenceGroupIndex,
    feature_set_version: str,
    distribution_version: str,
    manifest_hash: str,
    corpus_package_id: str,
    duplicate_policy: str,
    n_raw: int,
) -> ReferenceDistribution:
    group = index.get(group_id)
    present = [float(v) for v in values if v is not None]
    n_missing = len(values) - len(present)
    flags: list[str] = []
    if len(present) < group.n_effective:
        flags.append(f"missing values: {n_missing} of {len(values)}")
    if group.n_effective < MIN_N:
        flags.append(f"effective N {group.n_effective} below min-N {MIN_N}")
    if present:
        s = _stats(present)
        if s["std"] == 0.0 and len(present) > 1:
            flags.append("degenerate distribution (zero variance)")
        if s["iqr"] == 0.0 and len(present) > 5:
            flags.append("degenerate distribution (zero IQR)")
    else:
        s = None
    if len(present) >= MIN_N and group.n_effective >= MIN_N and s is not None:
        availability = "available"
    elif len(present) > 0 and group.n_effective >= MIN_N:
        availability = "limited"
    else:
        availability = "unavailable"
    return ReferenceDistribution(
        reference_group_id=group_id,
        feature_id=feature_id,
        feature_set_version=feature_set_version,
        reference_group_version=group.version,
        distribution_version=distribution_version,
        corpus_package_id=corpus_package_id,
        manifest_hash=manifest_hash,
        n_effective=group.n_effective,
        n_missing=n_missing,
        n_raw=n_raw,
        mean=s["mean"] if s else None,
        median=s["median"] if s else None,
        std=s["std"] if s else None,
        iqr=s["iqr"] if s else None,
        quantiles=s["quantiles"] if s else {},
        minimum=s["minimum"] if s else None,
        maximum=s["maximum"] if s else None,
        availability=availability,
        validity_flags=tuple(flags),
        duplicate_policy=duplicate_policy,
    )
