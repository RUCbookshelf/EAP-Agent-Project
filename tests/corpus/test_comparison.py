"""WU-C - observed-descriptive comparison math tests."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from app.corpus.comparison import (
    COMPARISON_ALGORITHM_VERSION,
    COMPARISON_ARTIFACT_VERSION,
    ComparisonEngine,
    estimated_percentile,
    z_distance,
)
from app.corpus.distributions import ReferenceDistribution
from app.corpus.errors import CorpusInvalidRequestError
from app.corpus.groups import ReferenceGroupIndex
from app.corpus.intelligence import CorpusIntelligence
from app.corpus.resource import load_corpus_resource
from app.corpus.student import StudentFeatureSnapshot, extract_student_features
from app.corpus.tasksignature import ReferenceGroupMatcher, TaskSignature

STUDENT_TEXT = (
    "I think they are both right. Many people go to the university, "
    "because it can be easy for you to find a work. However, in addition, "
    "the first reason is important."
)


def _dist(feature_id: str = "text_length_tokens", **overrides) -> ReferenceDistribution:
    base = dict(
        reference_group_id="RG-prompt_id=ARG17",
        feature_id=feature_id,
        feature_set_version="corpus-features-v0.1.0",
        reference_group_version="reference-groups-v0.1.0",
        distribution_version="reference-distributions-v0.1.0",
        corpus_package_id="sweccl2-weccl20-v0.1.0",
        manifest_hash="x" * 64,
        n_effective=40,
        n_missing=0,
        n_raw=40,
        mean=250.0,
        median=248.0,
        std=30.0,
        iqr=40.0,
        quantiles={"5": 200.0, "25": 230.0, "50": 248.0, "75": 270.0, "95": 300.0},
        minimum=180.0,
        maximum=340.0,
        availability="available",
        validity_flags=(),
        duplicate_policy="effective_sample_excludes_non_canonical_duplicate_members",
    )
    base.update(overrides)
    return ReferenceDistribution(**base)


def _make_intelligence(tmp_path: Path, distributions: list[ReferenceDistribution]) -> CorpusIntelligence:
    from tests.corpus.test_resource import _make_package

    readiness, prepared = _make_package(tmp_path, row_count=40)
    resource = load_corpus_resource(readiness_dir=readiness, prepared_root=prepared)
    rows = []
    with open(readiness / "data" / "corpus_manifest.csv", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for i, row in enumerate(rows):
        row["document_id"] = f"W{i:04d}"
        row["prompt_id"] = "ARG17"
        row["genre"] = "argumentative"
        row["timed_status"] = "timed"
        row["grade"] = "1"
        row["major_type"] = "english_major"
        row["entry_year"] = "2006"
    index = ReferenceGroupIndex(manifest=rows, min_n=5)
    data_dir = tmp_path / "intel-data"
    data_dir.mkdir()
    with open(data_dir / "reference_distributions.jsonl", "w", encoding="utf-8") as f:
        for dist in distributions:
            f.write(json.dumps(dist.__dict__) + "\n")
    return CorpusIntelligence(resource=resource, index=index, data_dir=data_dir)


def _snapshot() -> StudentFeatureSnapshot:
    return extract_student_features(STUDENT_TEXT, submission_id="research-sub-001")


def _match_and_compare(tmp_path: Path, snapshot: StudentFeatureSnapshot,
                       distributions: list[ReferenceDistribution],
                       feature_ids: list[str] | None = None):
    ci = _make_intelligence(tmp_path, distributions)
    match = ReferenceGroupMatcher(ci).match(TaskSignature(prompt_id="ARG17"))
    engine = ComparisonEngine(ci)
    return engine.compare(snapshot, match, feature_ids=feature_ids)


def test_available_comparison_full_provenance(tmp_path: Path) -> None:
    result = _match_and_compare(
        tmp_path, _snapshot(), [_dist(), _dist("connective_density")],
        feature_ids=["text_length_tokens", "connective_density"],
    )
    assert result.n_available == 2
    assert result.n_unavailable == 0
    prov = result.provenance
    assert prov["artifact_version"] == COMPARISON_ARTIFACT_VERSION
    assert prov["feature_set_version"] == "corpus-features-v0.1.0"
    assert prov["reference_group_id"] == "RG-prompt_id=ARG17"
    assert prov["corpus_package_id"] == "sweccl2-weccl20-v0.1.0"
    assert prov["manifest_hash"]
    assert prov["learner_exposure"] == "research_only"
    comp = result.comparisons[0]
    assert comp.evidence_class == "observed_descriptive"
    assert comp.algorithm_version == COMPARISON_ALGORITHM_VERSION
    assert comp.student_value is not None
    assert 0.0 <= comp.estimated_percentile <= 100.0
    assert comp.z_distance is not None
    assert "piecewise-linear" in comp.percentile_method


def test_no_normative_label_fields(tmp_path: Path) -> None:
    result = _match_and_compare(
        tmp_path, _snapshot(), [_dist(), _dist("connective_density")],
        feature_ids=["text_length_tokens", "connective_density"],
    )
    for comp in result.comparisons:
        for forbidden in ("label", "proficiency", "mastery", "learning_gain", "rank", "band"):
            assert not hasattr(comp, forbidden)
    for forbidden in ("label", "proficiency", "mastery", "learning_gain"):
        assert not hasattr(result, forbidden)


def test_percentile_known_points(tmp_path: Path) -> None:
    dist = _dist()
    assert estimated_percentile(dist.minimum, dist) == 0.0
    assert estimated_percentile(dist.quantiles["50"], dist) == 50.0
    assert estimated_percentile(dist.quantiles["95"], dist) == 95.0
    assert estimated_percentile(dist.maximum, dist) == 100.0


def test_percentile_clamps_outside_range(tmp_path: Path) -> None:
    dist = _dist()
    assert estimated_percentile(10.0, dist) == 0.0
    assert estimated_percentile(9999.0, dist) == 100.0


def test_z_distance_undefined_on_degenerate(tmp_path: Path) -> None:
    dist = _dist(std=0.0, validity_flags=("degenerate distribution (zero variance)",))
    assert z_distance(250.0, dist) is None


def test_feature_version_mismatch_fails_closed(tmp_path: Path) -> None:
    snapshot = _snapshot()
    wrong = StudentFeatureSnapshot(
        artifact_version=snapshot.artifact_version,
        submission_id=snapshot.submission_id,
        feature_set_version="corpus-features-v9.9.9",
        processing_version=snapshot.processing_version,
        extractor=snapshot.extractor,
        extractor_version=snapshot.extractor_version,
        features=snapshot.features,
        eligibility=snapshot.eligibility,
    )
    with pytest.raises(CorpusInvalidRequestError, match="FeatureSetVersion mismatch"):
        _match_and_compare(tmp_path, wrong, [_dist()])


def test_unavailable_student_feature_reported(tmp_path: Path) -> None:
    snapshot = extract_student_features("Hello world.", submission_id="short")
    ci = _make_intelligence(tmp_path, [_dist("t_unit_proxy")])
    match = ReferenceGroupMatcher(ci).match(TaskSignature(prompt_id="ARG17"))
    engine = ComparisonEngine(ci)
    result = engine.compare(snapshot, match, feature_ids=["t_unit_proxy"])
    (comp,) = result.comparisons
    assert comp.availability == "unavailable"
    assert "student feature unavailable" in comp.unavailable_reason


def test_missing_distribution_reported_unavailable(tmp_path: Path) -> None:
    snapshot = _snapshot()
    ci = _make_intelligence(tmp_path, [_dist()])
    match = ReferenceGroupMatcher(ci).match(TaskSignature(prompt_id="ARG17"))
    engine = ComparisonEngine(ci)
    result = engine.compare(snapshot, match, feature_ids=["text_length_tokens", "connective_density"])
    by_id = {c.feature_id: c for c in result.comparisons}
    assert by_id["text_length_tokens"].availability == "available"
    assert by_id["connective_density"].availability == "unavailable"
    assert "distribution unavailable" in by_id["connective_density"].unavailable_reason


def test_compare_unmatched_group_fails_closed(tmp_path: Path) -> None:
    ci = _make_intelligence(tmp_path, [_dist()])
    matcher = ReferenceGroupMatcher(ci)
    unmatched = matcher.match(TaskSignature())
    assert unmatched.matched is False
    with pytest.raises(CorpusInvalidRequestError, match="not matched"):
        ComparisonEngine(ci).compare(_snapshot(), unmatched)


def test_unknown_requested_feature_rejected(tmp_path: Path) -> None:
    ci = _make_intelligence(tmp_path, [_dist()])
    match = ReferenceGroupMatcher(ci).match(TaskSignature(prompt_id="ARG17"))
    with pytest.raises(CorpusInvalidRequestError, match="does not contain"):
        ComparisonEngine(ci).compare(_snapshot(), match, feature_ids=["not_a_feature"])
