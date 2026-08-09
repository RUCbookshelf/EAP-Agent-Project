"""WU-A - Student FeatureSnapshot harness tests."""

from __future__ import annotations

import os

import pytest

from app.corpus.errors import CorpusInvalidRequestError
from app.corpus.features import ALL_FEATURE_IDS, FEATURE_SET_VERSION
from app.corpus.student import (
    ARTIFACT_CLASS,
    STUDENT_PROCESSING_VERSION,
    STUDENT_SNAPSHOT_ARTIFACT_VERSION,
    StudentFeatureSnapshot,
    extract_student_features,
    recheck_eligibility,
)

NORMAL_TEXT = (
    "I think they are both right. Many people go to the university, "
    "because it can be easy for you to find a work."
)


def test_snapshot_has_all_features_and_version() -> None:
    snap = extract_student_features(NORMAL_TEXT, submission_id="research-sub-001")
    assert [f.feature_id for f in snap.features] == ALL_FEATURE_IDS
    assert all(f.feature_set_version == FEATURE_SET_VERSION for f in snap.features)
    assert snap.feature_set_version == FEATURE_SET_VERSION


def test_snapshot_provenance_and_classification() -> None:
    snap = extract_student_features(NORMAL_TEXT, submission_id="research-sub-001")
    prov = snap.provenance
    assert prov["artifact_version"] == STUDENT_SNAPSHOT_ARTIFACT_VERSION
    assert prov["processing_version"] == STUDENT_PROCESSING_VERSION
    assert prov["extractor_version"] == "3.8.0"
    assert prov["extractor"].startswith("en_core_web_sm")
    assert prov["learner_exposure"] == "research_only"
    assert prov["artifact_class"] == ARTIFACT_CLASS
    assert prov["text_retained"] is False


def test_raw_text_never_retained() -> None:
    snap = extract_student_features(NORMAL_TEXT, submission_id="research-sub-001")
    assert not hasattr(snap, "text")
    assert snap.text_retained is False


def test_determinism_repeatability() -> None:
    a = extract_student_features(NORMAL_TEXT, submission_id="r1")
    b = extract_student_features(NORMAL_TEXT, submission_id="r1")
    assert a == b


def test_corpus_header_rejected() -> None:
    with pytest.raises(CorpusInvalidRequestError, match="corpus header"):
        extract_student_features("<STU1234>\n" + NORMAL_TEXT)
    with pytest.raises(CorpusInvalidRequestError, match="corpus header"):
        extract_student_features("  <STU1234> " + NORMAL_TEXT)


def test_path_shaped_submission_id_rejected() -> None:
    # Fixtures must stay byte-identical at runtime; os.sep keeps the source
    # free of machine-specific absolute-path literals for the drift guard.
    for bad in (f"A:{os.sep}raw{os.sep}path", "C:/corpus/file.txt", "..\\..\\escape"):
        with pytest.raises(CorpusInvalidRequestError, match="path separator"):
            extract_student_features(NORMAL_TEXT, submission_id=bad)


def test_empty_input_warns_and_stays_aggregate() -> None:
    snap = extract_student_features("   ", submission_id="empty")
    results = {c.check_id: c.result for c in snap.eligibility}
    assert results["minimum_evidence"] == "warning"
    assert results["feature_set_version"] == "pass"
    length = [f for f in snap.features if f.feature_id == "text_length_tokens"][0]
    assert length.value == 0


def test_eligibility_records_unavailable_features() -> None:
    snap = extract_student_features("Hello world.", submission_id="short")
    results = {c.check_id: c.result for c in snap.eligibility}
    assert results["feature_availability"] == "warning"  # t_unit_proxy unavailable


def test_recheck_eligibility_passes() -> None:
    snap = extract_student_features(NORMAL_TEXT)
    checks = recheck_eligibility(snap)
    assert all(c.result == "pass" for c in checks)


def test_recheck_eligibility_fails_on_version_mismatch() -> None:
    snap = extract_student_features(NORMAL_TEXT)
    wrong = StudentFeatureSnapshot(
        artifact_version=snap.artifact_version,
        submission_id=snap.submission_id,
        feature_set_version="corpus-features-v9.9.9",
        processing_version=snap.processing_version,
        extractor=snap.extractor,
        extractor_version=snap.extractor_version,
        features=snap.features,
        eligibility=snap.eligibility,
    )
    checks = recheck_eligibility(wrong)
    assert checks[0].result == "fail"


def test_selected_features_only() -> None:
    snap = extract_student_features(NORMAL_TEXT, feature_ids=["text_length_tokens"])
    assert [f.feature_id for f in snap.features] == ["text_length_tokens"]
