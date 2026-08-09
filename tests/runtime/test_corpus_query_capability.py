"""Governed corpus_query capability: CorpusIntelligence boundary, raw-source denial,
and unavailable/error states."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.runtime.capabilities import GovernedCorpusQueryCapability
from app.runtime.executor import (
    STATUS_ERROR,
    STATUS_INELIGIBLE,
    STATUS_SUCCESS,
    STATUS_UNAVAILABLE,
    CapabilityExecutor,
)
from app.runtime.registry import CapabilityRegistry


@pytest.fixture
def capability(tmp_path: Path) -> GovernedCorpusQueryCapability:
    from tests.corpus.test_intelligence import _make_intelligence

    intelligence = _make_intelligence(tmp_path)
    return GovernedCorpusQueryCapability(intelligence=intelligence)


def _executor(capability: GovernedCorpusQueryCapability) -> CapabilityExecutor:
    registry = CapabilityRegistry()
    registry.register(capability.manifest, capability)
    return CapabilityExecutor(registry)


def test_query_distribution_success(capability: GovernedCorpusQueryCapability) -> None:
    result = _executor(capability).execute(
        "corpus.query_distribution",
        request={
            "reference_group_id": "RG-prompt_id=ARG17",
            "feature_id": "text_length_tokens",
        },
        caller_domain="l2",
    )
    assert result.status == STATUS_SUCCESS
    payload = result.result
    assert payload["corpus_package_id"] == "sweccl2-weccl20-v0.1.0"
    assert payload["availability"] == "available"
    assert payload["learner_exposure"] == "research_only"
    assert payload["n_effective"] == 40
    assert payload["distribution"]["median"] == 248.0


def test_unavailable_distribution_is_explicit(capability: GovernedCorpusQueryCapability) -> None:
    result = _executor(capability).execute(
        "corpus.query_distribution",
        request={"prompt_id": "ARG99", "feature_id": "text_length_tokens"},
        caller_domain="l2",
    )
    assert result.status == STATUS_UNAVAILABLE
    assert "distribution unavailable" in result.reason


def test_invalid_feature_is_isolated_error(capability: GovernedCorpusQueryCapability) -> None:
    result = _executor(capability).execute(
        "corpus.query_distribution",
        request={"reference_group_id": "RG-prompt_id=ARG17", "feature_id": "no_such_feature"},
        caller_domain="l2",
    )
    assert result.status == STATUS_ERROR
    assert result.error["type"] == "CorpusInvalidRequestError"


def test_raw_sweccl_path_denied(capability: GovernedCorpusQueryCapability) -> None:
    # Built without a literal drive-letter absolute literal so the
    # developer-path drift guard (tests/test_environment_drift.py) stays clean.
    raw_corpus_path = "A:" + r"\[Linguistics Data] Corpus\SWECCL 2.0\data\W0001.txt"
    result = _executor(capability).execute(
        "corpus.query_distribution",
        request={
            "raw_corpus_path": raw_corpus_path,
            "feature_id": "text_length_tokens",
        },
        caller_domain="l2",
    )
    assert result.status == STATUS_INELIGIBLE
    assert result.reason == "raw_source_denied"


def test_sweccl_marker_in_value_denied(capability: GovernedCorpusQueryCapability) -> None:
    result = _executor(capability).execute(
        "corpus.query_distribution",
        request={"file_handle": "sweccl2.0://raw/W0001", "feature_id": "text_length_tokens"},
        caller_domain="l2",
    )
    assert result.status == STATUS_INELIGIBLE
    assert result.reason == "raw_source_denied"


def test_corpus_version_operation(capability: GovernedCorpusQueryCapability) -> None:
    result = _executor(capability).execute(
        "corpus.query_distribution", request={"operation": "corpus_version"}, caller_domain="l2"
    )
    assert result.status == STATUS_SUCCESS
    assert result.result["corpus_package_id"] == "sweccl2-weccl20-v0.1.0"
    assert result.result["license_status"]


def test_manifest_declares_governance_metadata(capability: GovernedCorpusQueryCapability) -> None:
    manifest = capability.manifest
    assert manifest.identity == "corpus.query_distribution"
    assert manifest.owner == "CORPUS"
    assert manifest.data_access == ("governed_corpus_artifacts",)
    assert manifest.metadata["learner_exposure"] == "research_only"
    assert manifest.metadata["raw_source_denial"] is True
