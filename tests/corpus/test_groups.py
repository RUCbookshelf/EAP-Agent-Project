"""WU4 — reference group index and fallback tests."""

from __future__ import annotations

import pytest

from app.corpus.errors import CorpusInvalidRequestError, CorpusUnavailableError
from app.corpus.groups import MIN_N, ReferenceGroupIndex


def test_approved_groups_exist() -> None:
    index = ReferenceGroupIndex()
    ids = index.approved_group_ids()
    assert len(ids) >= 40
    assert "RG-prompt_id=ARG17" in ids
    assert "RG-genre=argumentative" in ids


def test_too_sparse_prompts_unavailable() -> None:
    index = ReferenceGroupIndex()
    group = index.get("RG-prompt_id=ARG13")
    assert group.n_raw < MIN_N
    assert group.availability == "unavailable"
    group19 = index.get("RG-prompt_id=ARG19")
    assert group19.availability == "unavailable"


def test_same_prompt_resolution() -> None:
    index = ReferenceGroupIndex()
    group, fallback = index.resolve(prompt_id="ARG17")
    assert group.reference_group_id == "RG-prompt_id=ARG17"
    assert group.n_effective >= MIN_N
    assert fallback is None


def test_prompt_timed_resolution() -> None:
    index = ReferenceGroupIndex()
    group, fallback = index.resolve(prompt_id="ARG17", timed_status="timed")
    assert group.reference_group_id == "RG-prompt_id=ARG17-timed_status=timed"
    assert fallback is None


def test_sparse_prompt_falls_back_to_genre() -> None:
    index = ReferenceGroupIndex()
    group, fallback = index.resolve(prompt_id="ARG13")
    assert group.reference_group_id == "RG-genre=argumentative"
    assert fallback == "RG-prompt_id=ARG13"


def test_unknown_group_rejected() -> None:
    index = ReferenceGroupIndex()
    with pytest.raises(CorpusInvalidRequestError, match="unknown reference group"):
        index.get("RG-prompt_id=ARG99")


def test_membership_consistent_with_counts() -> None:
    index = ReferenceGroupIndex()
    group = index.get("RG-prompt_id=ARG17")
    members = index.membership("RG-prompt_id=ARG17")
    assert len(members) == group.n_effective
    assert len(set(members)) == len(members)


def test_duplicate_policy_reduces_effective_n() -> None:
    index = ReferenceGroupIndex()
    group = index.get("RG-genre=argumentative")
    assert group.n_effective <= group.n_raw
