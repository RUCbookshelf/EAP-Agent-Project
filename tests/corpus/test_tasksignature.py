"""WU-B - TaskSignature reference-group matching tests."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from app.corpus.errors import CorpusInvalidRequestError
from app.corpus.groups import ReferenceGroupIndex
from app.corpus.intelligence import CorpusIntelligence
from app.corpus.resource import load_corpus_resource
from app.corpus.tasksignature import ReferenceGroupMatcher, TaskSignature


def _make_matcher(tmp_path: Path, *, min_n: int = 5) -> ReferenceGroupMatcher:
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
    index = ReferenceGroupIndex(manifest=rows, min_n=min_n)
    ci = CorpusIntelligence(resource=resource, index=index, data_dir=tmp_path / "empty-data")
    return ReferenceGroupMatcher(ci)


def test_signature_validation() -> None:
    with pytest.raises(CorpusInvalidRequestError, match="prompt_id"):
        TaskSignature(prompt_id="XYZ99")
    with pytest.raises(CorpusInvalidRequestError, match="timed_status"):
        TaskSignature(prompt_id="ARG17", timed_status="sometimes")
    with pytest.raises(CorpusInvalidRequestError, match="genre"):
        TaskSignature(genre="persuasive")


def test_exact_prompt_match(tmp_path: Path) -> None:
    matcher = _make_matcher(tmp_path)
    result = matcher.match(TaskSignature(prompt_id="ARG17"))
    assert result.matched is True
    assert result.resolved_reference_group_id == "RG-prompt_id=ARG17"
    assert result.fallback_disclosure is None
    assert result.unmatched_reason is None


def test_prompt_timed_exact_match(tmp_path: Path) -> None:
    matcher = _make_matcher(tmp_path)
    result = matcher.match(TaskSignature(prompt_id="ARG17", timed_status="timed"))
    assert result.matched is True
    assert result.resolved_reference_group_id == "RG-prompt_id=ARG17-timed_status=timed"
    assert result.fallback_disclosure is None


def test_unknown_prompt_falls_back_to_genre_with_disclosure(tmp_path: Path) -> None:
    matcher = _make_matcher(tmp_path)
    result = matcher.match(TaskSignature(prompt_id="ARG99"))
    assert result.matched is True
    assert result.resolved_reference_group_id == "RG-genre=argumentative"
    assert result.fallback_disclosure == "RG-prompt_id=ARG99"


def test_incomplete_signature_explicit_unmatched(tmp_path: Path) -> None:
    matcher = _make_matcher(tmp_path)
    result = matcher.match(TaskSignature())
    assert result.matched is False
    assert result.resolved_reference_group_id is None
    assert "incomplete" in result.unmatched_reason


def test_too_small_groups_explicit_unmatched(tmp_path: Path) -> None:
    matcher = _make_matcher(tmp_path, min_n=100)
    result = matcher.match(TaskSignature(prompt_id="ARG17"))
    assert result.matched is False
    assert "no reference group available" in result.unmatched_reason


def test_result_provenance_and_exposure(tmp_path: Path) -> None:
    matcher = _make_matcher(tmp_path)
    result = matcher.match(TaskSignature(prompt_id="ARG17"))
    prov = result.provenance
    assert prov["feature_set_version"] == "corpus-features-v0.1.0"
    assert prov["reference_group_version"] == "reference-groups-v0.1.0"
    assert prov["corpus_package_id"] == "sweccl2-weccl20-v0.1.0"
    assert prov["manifest_hash"] == matcher.intelligence.resource.manifest_hash
    assert prov["learner_exposure"] == "research_only"


def test_genre_derived_from_prompt() -> None:
    sig = TaskSignature(prompt_id="ARG17")
    assert sig.derived_genre() == "argumentative"
    sig2 = TaskSignature(prompt_id="EXP01")
    assert sig2.derived_genre() == "expository"
    assert TaskSignature(genre="expository").derived_genre() == "expository"
    assert TaskSignature().derived_genre() is None
