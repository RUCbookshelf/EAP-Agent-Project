"""WU-C - observed-descriptive comparison math (Stage 6, research-only).

Stage-6 WU-C computes within-group comparison statistics (estimated
percentile, standardized distance) for a student feature snapshot against an
approved reference-group distribution. Per D-07 the output is
observed-descriptive evidence only:

- No normative labels (no above/below average, no good/poor, no ranking
  language) - the result objects structurally carry no label fields.
- No proficiency/mastery/learning-gain interpretation vocabulary.
- No LLM computation (I5): all math is deterministic local code.
- Same FeatureSetVersion enforcement: snapshot and distribution versions
  must match the registered contract or the comparison fails closed.
- Unavailable inputs (student feature unavailable, missing/degenerate
  distribution) produce explicit unavailable results - never imputed.
- learner_exposure is always "research_only"; NON-RECONSTRUCTIVE aggregate.

Percentile method: the distribution record stores min/max and the 5/25/50/
75/95 quantiles. The estimated percentile is a piecewise-linear
interpolation over those points (value clamped to [min, max]). It is an
approximation based on recorded quantiles, not an exact rank; the method is
disclosed on every result.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.corpus.distributions import ReferenceDistribution
from app.corpus.errors import CorpusInvalidRequestError, CorpusUnavailableError
from app.corpus.features import FEATURE_SET_VERSION, FeatureSnapshot
from app.corpus.intelligence import CorpusIntelligence
from app.corpus.student import StudentFeatureSnapshot
from app.corpus.tasksignature import TaskMatchResult

COMPARISON_PROCESSING_VERSION = "comparison-engine-v0.1.0"
COMPARISON_ARTIFACT_VERSION = "feature-comparison-v0.1.0"
COMPARISON_ALGORITHM_VERSION = "comparison-algorithm-v0.1.0"
ARTIFACT_CLASS = "NON-RECONSTRUCTIVE AGGREGATE ARTIFACT"
EVIDENCE_CLASS = "observed_descriptive"  # D-07

PERCENTILE_METHOD = (
    "piecewise-linear interpolation over recorded min/max and quantiles "
    "(5/25/50/75/95); value clamped to [min, max]; approximation, not an exact rank"
)


def _percentile_points(dist: ReferenceDistribution) -> list[tuple[float, float]]:
    q = dist.quantiles
    points = []
    for p, key in ((0.0, "min"), (5.0, "5"), (25.0, "25"), (50.0, "50"),
                   (75.0, "75"), (95.0, "95"), (100.0, "max")):
        if key == "min":
            value = dist.minimum
        elif key == "max":
            value = dist.maximum
        else:
            value = q.get(key)
        if value is None:
            return []
        points.append((p, float(value)))
    return points


def estimated_percentile(value: float, dist: ReferenceDistribution) -> float | None:
    """Estimated percentile of value within the recorded distribution."""
    points = _percentile_points(dist)
    if not points:
        return None
    points.sort(key=lambda item: item[1])
    values = [v for _, v in points]
    v = min(max(value, values[0]), values[-1])
    for (p0, v0), (p1, v1) in zip(points, points[1:]):
        if v1 >= v0 and v0 <= v <= v1:
            if v1 == v0:
                return round(p1, 4)
            return round(p0 + (p1 - p0) * (v - v0) / (v1 - v0), 4)
    return round(points[-1][0], 4)


def z_distance(value: float, dist: ReferenceDistribution) -> float | None:
    """Standardized distance (value - mean) / std; None when undefined."""
    if dist.mean is None or dist.std is None or dist.std == 0.0:
        return None
    return round((value - dist.mean) / dist.std, 4)


@dataclass(frozen=True)
class FeatureComparisonResult:
    """Observed-descriptive comparison for one feature.

    Deliberately contains no normative label field.
    """

    artifact_version: str
    processing_version: str
    algorithm_version: str
    feature_id: str
    feature_set_version: str
    student_value: float | int | None
    student_analysis_status: str
    reference_group_id: str
    reference_group_version: str
    distribution_version: str
    corpus_package_id: str
    manifest_hash: str
    n_effective: int
    estimated_percentile: float | None
    percentile_method: str
    z_distance: float | None
    distance_limitations: tuple[str, ...]
    availability: str
    unavailable_reason: str | None
    evidence_class: str = EVIDENCE_CLASS
    learner_exposure: str = "research_only"
    artifact_class: str = ARTIFACT_CLASS


@dataclass(frozen=True)
class SnapshotComparisonResult:
    """All per-feature comparisons for one snapshot against one group."""

    artifact_version: str
    processing_version: str
    feature_set_version: str
    corpus_package_id: str
    manifest_hash: str
    reference_group_id: str
    reference_group_version: str
    comparisons: tuple[FeatureComparisonResult, ...]
    n_available: int
    n_unavailable: int
    learner_exposure: str = "research_only"
    artifact_class: str = ARTIFACT_CLASS

    @property
    def provenance(self) -> dict:
        return {
            "artifact_version": self.artifact_version,
            "processing_version": self.processing_version,
            "feature_set_version": self.feature_set_version,
            "reference_group_id": self.reference_group_id,
            "reference_group_version": self.reference_group_version,
            "corpus_package_id": self.corpus_package_id,
            "manifest_hash": self.manifest_hash,
            "learner_exposure": self.learner_exposure,
            "artifact_class": self.artifact_class,
        }


def _enforce_feature_set_version(
    snapshot_version: str,
    distribution_version: str,
    required: str,
) -> None:
    versions = {snapshot_version, distribution_version, required}
    if len(versions) != 1:
        raise CorpusInvalidRequestError(
            "FeatureSetVersion mismatch: snapshot "
            f"{snapshot_version!r}, distribution {distribution_version!r}, "
            f"required {required!r} - comparison prohibited without the same "
            "feature contract (Stage-6 I3)"
        )


class ComparisonEngine:
    """Observed-descriptive comparisons through the Stage-5 query boundary."""

    def __init__(
        self,
        intelligence: CorpusIntelligence | None = None,
        *,
        required_feature_set_version: str = FEATURE_SET_VERSION,
    ) -> None:
        self.intelligence = intelligence if intelligence is not None else CorpusIntelligence()
        self.required_feature_set_version = required_feature_set_version

    def _compare_one(
        self,
        feature: FeatureSnapshot,
        group_id: str,
        distribution: ReferenceDistribution,
    ) -> FeatureComparisonResult:
        resource = self.intelligence.resource
        if feature.value is None:
            return FeatureComparisonResult(
                artifact_version=COMPARISON_ARTIFACT_VERSION,
                processing_version=COMPARISON_PROCESSING_VERSION,
                algorithm_version=COMPARISON_ALGORITHM_VERSION,
                feature_id=feature.feature_id,
                feature_set_version=feature.feature_set_version,
                student_value=None,
                student_analysis_status=feature.analysis_status,
                reference_group_id=group_id,
                reference_group_version=distribution.reference_group_version,
                distribution_version=distribution.distribution_version,
                corpus_package_id=resource.corpus_package_id,
                manifest_hash=resource.manifest_hash,
                n_effective=distribution.n_effective,
                estimated_percentile=None,
                percentile_method=PERCENTILE_METHOD,
                z_distance=None,
                distance_limitations=(),
                availability="unavailable",
                unavailable_reason=(
                    f"student feature unavailable (analysis_status={feature.analysis_status})"
                ),
            )
        if distribution.availability != "available":
            return FeatureComparisonResult(
                artifact_version=COMPARISON_ARTIFACT_VERSION,
                processing_version=COMPARISON_PROCESSING_VERSION,
                algorithm_version=COMPARISON_ALGORITHM_VERSION,
                feature_id=feature.feature_id,
                feature_set_version=feature.feature_set_version,
                student_value=feature.value,
                student_analysis_status=feature.analysis_status,
                reference_group_id=group_id,
                reference_group_version=distribution.reference_group_version,
                distribution_version=distribution.distribution_version,
                corpus_package_id=resource.corpus_package_id,
                manifest_hash=resource.manifest_hash,
                n_effective=distribution.n_effective,
                estimated_percentile=None,
                percentile_method=PERCENTILE_METHOD,
                z_distance=None,
                distance_limitations=tuple(distribution.validity_flags),
                availability="unavailable",
                unavailable_reason=(
                    f"distribution unavailable (availability={distribution.availability})"
                ),
            )
        percentile = estimated_percentile(float(feature.value), distribution)
        dist = z_distance(float(feature.value), distribution)
        limitations: list[str] = []
        if percentile is None:
            limitations.append("percentile undefined: distribution lacks min/max or quantiles")
        if dist is None:
            limitations.append(
                "z_distance undefined: distribution lacks mean/std or has zero variance"
            )
        return FeatureComparisonResult(
            artifact_version=COMPARISON_ARTIFACT_VERSION,
            processing_version=COMPARISON_PROCESSING_VERSION,
            algorithm_version=COMPARISON_ALGORITHM_VERSION,
            feature_id=feature.feature_id,
            feature_set_version=feature.feature_set_version,
            student_value=feature.value,
            student_analysis_status=feature.analysis_status,
            reference_group_id=group_id,
            reference_group_version=distribution.reference_group_version,
            distribution_version=distribution.distribution_version,
            corpus_package_id=resource.corpus_package_id,
            manifest_hash=resource.manifest_hash,
            n_effective=distribution.n_effective,
            estimated_percentile=percentile,
            percentile_method=PERCENTILE_METHOD,
            z_distance=dist,
            distance_limitations=tuple(limitations) + tuple(distribution.validity_flags),
            availability="available",
            unavailable_reason=None,
        )

    def compare(
        self,
        snapshot: StudentFeatureSnapshot,
        match: TaskMatchResult,
        feature_ids: list[str] | None = None,
    ) -> SnapshotComparisonResult:
        """Compare a snapshot against the matched group (research-only)."""
        _enforce_feature_set_version(
            snapshot.feature_set_version,
            match.feature_set_version,
            self.required_feature_set_version,
        )
        if not match.matched or match.resolved_reference_group_id is None:
            raise CorpusInvalidRequestError(
                f"cannot compare: reference group not matched ({match.unmatched_reason})"
            )
        group_id = match.resolved_reference_group_id
        by_id = {f.feature_id: f for f in snapshot.features}
        selected = feature_ids or list(by_id)
        unknown = [fid for fid in selected if fid not in by_id]
        if unknown:
            raise CorpusInvalidRequestError(
                f"snapshot does not contain requested feature(s): {unknown}"
            )
        results: list[FeatureComparisonResult] = []
        for feature_id in selected:
            feature = by_id[feature_id]
            try:
                query = self.intelligence.get_feature_distribution(
                    reference_group_id=group_id, feature_id=feature_id
                )
                distribution = query.distribution
                if distribution is None:
                    raise CorpusUnavailableError("distribution missing")
            except CorpusUnavailableError as exc:
                results.append(FeatureComparisonResult(
                    artifact_version=COMPARISON_ARTIFACT_VERSION,
                    processing_version=COMPARISON_PROCESSING_VERSION,
                    algorithm_version=COMPARISON_ALGORITHM_VERSION,
                    feature_id=feature_id,
                    feature_set_version=feature.feature_set_version,
                    student_value=feature.value,
                    student_analysis_status=feature.analysis_status,
                    reference_group_id=group_id,
                    reference_group_version=match.reference_group_version,
                    distribution_version="",
                    corpus_package_id=match.corpus_package_id,
                    manifest_hash=match.manifest_hash,
                    n_effective=0,
                    estimated_percentile=None,
                    percentile_method=PERCENTILE_METHOD,
                    z_distance=None,
                    distance_limitations=(),
                    availability="unavailable",
                    unavailable_reason=f"distribution unavailable: {exc}",
                ))
                continue
            _enforce_feature_set_version(
                feature.feature_set_version,
                distribution.feature_set_version,
                self.required_feature_set_version,
            )
            results.append(self._compare_one(feature, group_id, distribution))
        n_available = sum(1 for r in results if r.availability == "available")
        return SnapshotComparisonResult(
            artifact_version=COMPARISON_ARTIFACT_VERSION,
            processing_version=COMPARISON_PROCESSING_VERSION,
            feature_set_version=snapshot.feature_set_version,
            corpus_package_id=match.corpus_package_id,
            manifest_hash=match.manifest_hash,
            reference_group_id=group_id,
            reference_group_version=match.reference_group_version,
            comparisons=tuple(results),
            n_available=n_available,
            n_unavailable=len(results) - n_available,
        )
