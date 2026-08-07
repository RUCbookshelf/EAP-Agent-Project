"""WU2/WU5 — feature contract and extraction tests."""

from __future__ import annotations

import pytest

from app.corpus.errors import CorpusIntelligenceError
from app.corpus.features import (
    ALL_FEATURE_IDS,
    FEATURE_DEFINITIONS,
    FEATURE_SET_VERSION,
    extract_features,
    extract_features_batch,
)

NORMAL_TEXT = (
    "I think they are both right. Many people go to the university, "
    "because it can be easy for you to find a work. However, in addition, "
    "the first reason is important."
)


def test_all_features_extracted() -> None:
    snaps = extract_features(NORMAL_TEXT)
    assert [s.feature_id for s in snaps] == ALL_FEATURE_IDS
    assert all(s.feature_set_version == FEATURE_SET_VERSION for s in snaps)
    assert all(s.analysis_status == "available" for s in snaps)


def test_text_length_positive() -> None:
    (snap,) = extract_features(NORMAL_TEXT, ["text_length_tokens"])
    assert snap.value and snap.value > 10
    assert snap.unit == "tokens"


def test_empty_text_unavailable() -> None:
    snaps = extract_features("", ["text_length_tokens", "sentence_length_mean", "t_unit_proxy"])
    assert snaps[0].value == 0
    assert snaps[1].analysis_status == "unavailable"
    assert snaps[2].analysis_status == "unavailable"


def test_short_text() -> None:
    snaps = extract_features("Hello world.", ["text_length_tokens", "sentence_length_mean"])
    assert snaps[0].value == 3
    assert snaps[1].analysis_status == "available"


def test_non_ascii_text() -> None:
    text = "I live in 许巷 and I like it. It is very nice."
    snaps = extract_features(text, ["text_length_tokens", "pos_share_noun"])
    assert snaps[0].value and snaps[0].value > 5
    assert snaps[1].value is not None and 0.0 <= snaps[1].value <= 1.0


def test_malformed_text() -> None:
    text = "!!!!!!! ... ???"
    snaps = extract_features(text, ["text_length_tokens", "pos_share_other"])
    assert snaps[0].value and snaps[0].value > 0
    assert snaps[1].value == 1.0


def test_pos_shares_sum_to_one() -> None:
    snaps = extract_features(NORMAL_TEXT)
    shares = [s for s in snaps if s.feature_id.startswith("pos_share_")]
    total = sum(s.value for s in shares)
    assert abs(total - 1.0) < 1e-5


def test_connective_density_deterministic_and_positive() -> None:
    a = extract_features(NORMAL_TEXT, ["connective_density"])[0]
    b = extract_features(NORMAL_TEXT, ["connective_density"])[0]
    assert a == b
    assert a.value and a.value > 0
    assert a.unit == "per_1000_tokens"


def test_determinism_repeatability() -> None:
    a = extract_features(NORMAL_TEXT)
    b = extract_features(NORMAL_TEXT)
    assert a == b


def test_batch_matches_single() -> None:
    texts = [NORMAL_TEXT, "Short text here.", ""]
    batch = extract_features_batch(texts)
    for text, snaps in zip(texts, batch):
        single = extract_features(text)
        assert snaps == single


def test_unknown_feature_rejected() -> None:
    with pytest.raises(CorpusIntelligenceError, match="unknown feature_id"):
        extract_features(NORMAL_TEXT, ["not_a_feature"])


def test_definitions_complete() -> None:
    assert set(FEATURE_DEFINITIONS) == set(ALL_FEATURE_IDS)
    for fid, definition in FEATURE_DEFINITIONS.items():
        assert definition.feature_id == fid
        assert definition.feature_version
        assert definition.unit
        assert definition.algorithm
        assert definition.missing_behavior


def test_warg2081_style_corrupt_input() -> None:
    # A NUL-only text would be rejected by the corpus adapter before extraction;
    # the extractor itself must not crash on degenerate input.
    snaps = extract_features("\x00\x00\x00")
    assert all(s.analysis_status in ("available", "unavailable") for s in snaps)
