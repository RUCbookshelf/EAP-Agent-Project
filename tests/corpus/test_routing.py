"""TDD tests for Wave-2 Goal E modality-aware corpus routing.

Covers: written-default routing for L2 Writing requests; SECCL20 spoken +
secondary/research_only classification; SECCL exclusion from default L2
Writing routing; five-factor eligibility gating (domain relevance, modality
relevance, exposure policy, artifact availability, reference-group
eligibility); the WECCL written fallback chain (same prompt -> task type +
context -> task type -> similar written context -> broader distribution);
descriptive-only semantics; and leak hygiene.

All fixtures are synthetic; no raw SWECCL data is touched.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from app.corpus.distributions import ReferenceDistribution
from app.corpus.errors import CorpusInvalidRequestError
from app.corpus.groups import ReferenceGroupIndex
from app.corpus.routing import (
    ALL_WRITTEN_GROUP_ID,
    L2_WRITING_DOMAIN,
    L2WritingRouter,
    MODALITY_SPOKEN,
    MODALITY_WRITTEN,
    ROLE_PRIMARY,
    ROLE_SECONDARY,
    RoutingResource,
    SECCL_PACKAGE_ID,
    WECCL_PACKAGE_ID,
    assess_eligibility,
    classify_resource,
)
from app.corpus.seccl import SecclReferenceGroupIndex
from app.corpus.tasksignature import TaskSignature

FEATURE = "text_length_tokens"


def _manifest_rows() -> list[dict]:
    """90 synthetic WECCL-like written rows across three prompts."""
    rows: list[dict] = []
    for i in range(30):
        rows.append({
            "document_id": f"WARG17{i:04d}", "prompt_id": "ARG17",
            "genre": "argumentative", "timed_status": "timed",
            "grade": "1", "major_type": "english_major", "entry_year": "2006",
        })
    for i in range(30):
        rows.append({
            "document_id": f"WARG02{i:04d}", "prompt_id": "ARG02",
            "genre": "argumentative", "timed_status": "untimed",
            "grade": "2", "major_type": "non_english_major", "entry_year": "2004",
        })
    for i in range(30):
        rows.append({
            "document_id": f"WEXP01{i:04d}", "prompt_id": "EXP01",
            "genre": "expository", "timed_status": "untimed",
            "grade": "3", "major_type": "english_major", "entry_year": "2005",
        })
    return rows


class _GenreTimedIndex(ReferenceGroupIndex):
    """ReferenceGroupIndex that also builds genre x timed_status groups.

    The routing chain's task_type_context level needs these groups; the
    production index does not currently build them, so the production chain
    discloses that level as unavailable. Fixtures add them to prove chain
    ordering when the governed groups/artifacts exist.
    """

    def _build_groups(self) -> None:
        super()._build_groups()
        genres = sorted({r["genre"] for r in self.manifest})
        timeds = sorted({r["timed_status"] for r in self.manifest})
        for genre in genres:
            for timed in timeds:
                self._add_group({"genre": genre, "timed_status": timed}, set())


def _rich_index() -> ReferenceGroupIndex:
    return _GenreTimedIndex(manifest=_manifest_rows(), min_n=5)


def _dist(group_id: str, availability: str = "available") -> ReferenceDistribution:
    return ReferenceDistribution(
        reference_group_id=group_id,
        feature_id=FEATURE,
        feature_set_version="corpus-features-v0.1.0",
        reference_group_version="reference-groups-v0.1.0",
        distribution_version="reference-distributions-v0.1.0",
        corpus_package_id=WECCL_PACKAGE_ID,
        manifest_hash="0" * 64,
        n_effective=30,
        n_missing=0,
        n_raw=30,
        mean=250.0,
        median=248.0,
        std=30.0,
        iqr=40.0,
        quantiles={"5": 200.0, "25": 230.0, "50": 248.0, "75": 270.0, "95": 300.0},
        minimum=180.0,
        maximum=340.0,
        availability=availability,
        validity_flags=(),
        duplicate_policy="fixture_policy",
    )


def _resource(package_id: str) -> RoutingResource:
    return RoutingResource(
        corpus_package_id=package_id,
        manifest_hash="0" * 64,
        provenance={"corpus_package_id": package_id, "source": "fixture"},
    )


def _resources() -> dict[str, RoutingResource]:
    return {
        WECCL_PACKAGE_ID: _resource(WECCL_PACKAGE_ID),
        SECCL_PACKAGE_ID: _resource(SECCL_PACKAGE_ID),
    }


def _seccl_rows() -> list[dict]:
    rows: list[dict] = []
    for i in range(35):
        rows.append({
            "transcript_id": f"03-{i:03d}-01A",
            "task_folder": "TASK1",
            "year_folder": "2003",
            "exam": "TEM4",
            "grade": "2",
            "source_relative_path": f"SECCL20/TEXTS/TASK1/2003/03-130/03-130-{i:02d}.txt",
        })
    return rows


def _router(
    *,
    index: ReferenceGroupIndex | None = None,
    distributions: dict[tuple[str, str], ReferenceDistribution] | None = None,
    include_seccl: bool = True,
) -> L2WritingRouter:
    seccl_index = SecclReferenceGroupIndex(manifest=_seccl_rows(), min_n=5)
    return L2WritingRouter(
        index=index if index is not None else _rich_index(),
        distributions=distributions or {},
        seccl_index=seccl_index if include_seccl else None,
        resources=_resources(),
        min_n=5,
    )


class TestClassification:
    def test_weccl_classified_written_primary(self) -> None:
        cls = classify_resource(WECCL_PACKAGE_ID)
        assert cls.modality == MODALITY_WRITTEN
        assert cls.role == ROLE_PRIMARY
        assert cls.secondary is False
        assert cls.exposure_class == "research_only"
        assert cls.learner_exposure == "research_only"
        assert L2_WRITING_DOMAIN in cls.domains
        assert cls.allowed_exposures == ("research_only",)

    def test_seccl_classified_spoken_secondary_research_only(self) -> None:
        cls = classify_resource(SECCL_PACKAGE_ID)
        assert cls.modality == MODALITY_SPOKEN
        assert cls.role == ROLE_SECONDARY
        assert cls.secondary is True
        assert cls.exposure_class == "research_only"
        assert cls.learner_exposure == "research_only"
        assert L2_WRITING_DOMAIN not in cls.domains
        assert cls.allowed_exposures == ("research_only",)

    def test_unknown_package_rejected(self) -> None:
        with pytest.raises(CorpusInvalidRequestError):
            classify_resource("not-a-package")


class TestWrittenDefaultRouting:
    def test_default_routes_to_written_resource(self) -> None:
        result = _router(distributions={
            ("RG-prompt_id=ARG17", FEATURE): _dist("RG-prompt_id=ARG17"),
        }).route(TaskSignature(prompt_id="ARG17", timed_status="timed", genre="argumentative"))
        assert result.routed is True
        assert result.corpus_package_id == WECCL_PACKAGE_ID
        assert result.resolved_resource_id == WECCL_PACKAGE_ID
        assert result.request["requested_modality"] == MODALITY_WRITTEN
        assert result.request["domain"] == L2_WRITING_DOMAIN

    def test_same_prompt_resolves_without_fallback(self) -> None:
        result = _router(distributions={
            ("RG-prompt_id=ARG17", FEATURE): _dist("RG-prompt_id=ARG17"),
        }).route(TaskSignature(prompt_id="ARG17", timed_status="timed", genre="argumentative"))
        assert result.resolved_reference_group_id == "RG-prompt_id=ARG17"
        assert result.resolved_level == "same_prompt"
        assert result.fallback_disclosure is None

    def test_never_routes_seccl_by_default_even_when_artifacts_exist(self) -> None:
        result = _router(distributions={
            ("RG-prompt_id=ARG17", FEATURE): _dist("RG-prompt_id=ARG17"),
            ("RG-seccl-exam=TEM4", FEATURE): _dist("RG-seccl-exam=TEM4"),
        }).route(TaskSignature(prompt_id="ARG17", timed_status="timed", genre="argumentative"))
        assert result.routed is True
        assert result.corpus_package_id == WECCL_PACKAGE_ID
        assert SECCL_PACKAGE_ID not in json.dumps(result.request)

    def test_seccl_not_eligible_for_l2_writing_domain(self) -> None:
        cls = classify_resource(SECCL_PACKAGE_ID)
        eligibility = assess_eligibility(
            cls,
            domain=L2_WRITING_DOMAIN,
            requested_modality=MODALITY_WRITTEN,
            requested_exposure="research_only",
            reference_group_availability="available",
            n_effective=35,
            min_n=5,
            artifact_available=True,
        )
        assert eligibility.eligible is False
        assert eligibility.domain_relevance is False
        assert eligibility.modality_relevance is False
        assert eligibility.artifact_availability is True
        assert any("domain" in r for r in eligibility.reasons)
        assert any("modality" in r for r in eligibility.reasons)


class TestSecclSpokenOptIn:
    def test_spoken_request_requires_allow_secondary(self) -> None:
        result = _router(distributions={
            ("RG-seccl-exam=TEM4", FEATURE): _dist("RG-seccl-exam=TEM4"),
        }).route(
            TaskSignature(prompt_id=None, genre=None),
            domain="l2_speaking",
            requested_modality=MODALITY_SPOKEN,
            allow_secondary=False,
        )
        assert result.routed is False
        assert "allow_secondary" in (result.unmatched_reason or "")

    def test_spoken_opt_in_routes_seccl_research_only_as_secondary(self) -> None:
        result = _router(distributions={
            ("RG-seccl-exam=TEM4", FEATURE): _dist("RG-seccl-exam=TEM4"),
        }).route(
            TaskSignature(prompt_id=None, genre=None),
            domain="l2_speaking",
            requested_modality=MODALITY_SPOKEN,
            allow_secondary=True,
        )
        assert result.routed is True
        assert result.corpus_package_id == SECCL_PACKAGE_ID
        assert result.secondary is True
        assert result.learner_exposure == "research_only"
        assert result.resolved_reference_group_id == "RG-seccl-exam=TEM4"

    def test_spoken_opt_in_diagnostic_exposure_refused(self) -> None:
        result = _router(distributions={
            ("RG-seccl-exam=TEM4", FEATURE): _dist("RG-seccl-exam=TEM4"),
        }).route(
            TaskSignature(prompt_id=None, genre=None),
            domain="l2_speaking",
            requested_modality=MODALITY_SPOKEN,
            requested_exposure="diagnostic_only",
            allow_secondary=True,
        )
        assert result.routed is False
        assert "exposure" in (result.unmatched_reason or "")

    def test_processed_seccl_artifacts_do_not_imply_eligibility(self) -> None:
        """Processed artifacts exist, but eligibility still fails for L2 Writing."""
        cls = classify_resource(SECCL_PACKAGE_ID)
        eligibility = assess_eligibility(
            cls,
            domain=L2_WRITING_DOMAIN,
            requested_modality=MODALITY_WRITTEN,
            requested_exposure="research_only",
            reference_group_availability="available",
            n_effective=35,
            min_n=5,
            artifact_available=True,
        )
        assert eligibility.artifact_availability is True
        assert eligibility.reference_group_eligibility is True
        assert eligibility.eligible is False  # domain + modality still gate


class TestEligibilityGating:
    def test_missing_distribution_artifact_blocks_routing(self) -> None:
        result = _router(distributions={}).route(
            TaskSignature(prompt_id="ARG17", timed_status="timed", genre="argumentative")
        )
        assert result.routed is False
        assert "artifact" in (result.unmatched_reason or "")

    def test_below_min_n_group_blocks_routing(self) -> None:
        sparse = [{
            "document_id": f"WARG99{i:04d}", "prompt_id": "ARG99",
            "genre": "argumentative", "timed_status": "timed",
            "grade": "1", "major_type": "english_major", "entry_year": "2006",
        } for i in range(2)]
        index = _GenreTimedIndex(manifest=sparse + _manifest_rows(), min_n=5)
        result = _router(index=index, distributions={
            ("RG-prompt_id=ARG99", FEATURE): _dist("RG-prompt_id=ARG99"),
        }).route(TaskSignature(prompt_id="ARG99", timed_status="timed", genre="argumentative"))
        assert result.routed is False
        assert "min_n" in (result.unmatched_reason or "")

    def test_diagnostic_exposure_refused_for_written_too(self) -> None:
        result = _router(distributions={
            ("RG-prompt_id=ARG17", FEATURE): _dist("RG-prompt_id=ARG17"),
        }).route(
            TaskSignature(prompt_id="ARG17", timed_status="timed", genre="argumentative"),
            requested_exposure="diagnostic_only",
        )
        assert result.routed is False
        assert "exposure" in (result.unmatched_reason or "")

    def test_group_absent_from_index_disclosed_unavailable(self) -> None:
        """The task_type_context level has no governed group today; it must be
        disclosed as unavailable, never silently skipped as resolved."""
        result = _router(distributions={
            ("RG-genre=argumentative", FEATURE): _dist("RG-genre=argumentative"),
        }).route(TaskSignature(prompt_id="ARG17", timed_status="timed", genre="argumentative"))
        assert result.resolved_level == "task_type"
        assert result.fallback_disclosure == "same_prompt"


class TestWrittenFallbackChain:
    def test_chain_levels_ordered_for_full_signature(self) -> None:
        result = _router(distributions={
            ("RG-prompt_id=ARG17", FEATURE): _dist("RG-prompt_id=ARG17"),
        }).route(TaskSignature(prompt_id="ARG17", timed_status="timed", genre="argumentative"))
        assert result.fallback_chain == (
            "same_prompt",
            "task_type_context",
            "task_type",
            "similar_written_context",
            "broader_distribution",
        )

    def test_falls_back_to_task_type_context(self) -> None:
        result = _router(distributions={
            ("RG-genre=argumentative-timed_status=timed", FEATURE): _dist(
                "RG-genre=argumentative-timed_status=timed"
            ),
        }).route(TaskSignature(prompt_id="ARG17", timed_status="timed", genre="argumentative"))
        assert result.resolved_level == "task_type_context"
        assert result.resolved_reference_group_id == "RG-genre=argumentative-timed_status=timed"
        assert result.fallback_disclosure == "same_prompt"

    def test_falls_back_to_task_type(self) -> None:
        result = _router(distributions={
            ("RG-genre=argumentative", FEATURE): _dist("RG-genre=argumentative"),
        }).route(TaskSignature(prompt_id="ARG17", timed_status="timed", genre="argumentative"))
        assert result.resolved_level == "task_type"
        assert result.resolved_reference_group_id == "RG-genre=argumentative"

    def test_falls_back_to_similar_written_context(self) -> None:
        result = _router(distributions={
            ("RG-timed_status=timed", FEATURE): _dist("RG-timed_status=timed"),
        }).route(TaskSignature(prompt_id="ARG17", timed_status="timed", genre="argumentative"))
        assert result.resolved_level == "similar_written_context"
        assert result.resolved_reference_group_id == "RG-timed_status=timed"

    def test_falls_back_to_broader_distribution(self) -> None:
        result = _router(distributions={
            (ALL_WRITTEN_GROUP_ID, FEATURE): _dist(ALL_WRITTEN_GROUP_ID),
        }).route(TaskSignature(prompt_id="ARG17", timed_status="timed", genre="argumentative"))
        assert result.resolved_level == "broader_distribution"
        assert result.resolved_reference_group_id == ALL_WRITTEN_GROUP_ID
        assert result.fallback_disclosure == "same_prompt"

    def test_chain_exhausted_explicit_unmatched(self) -> None:
        result = _router(distributions={}).route(
            TaskSignature(prompt_id="ARG17", timed_status="timed", genre="argumentative")
        )
        assert result.routed is False
        assert result.resolved_reference_group_id is None
        assert result.unmatched_reason is not None
        for level in ("same_prompt", "task_type_context", "task_type",
                      "similar_written_context", "broader_distribution"):
            assert level in (result.unmatched_reason or "")

    def test_incomplete_signature_explicit_unmatched(self) -> None:
        result = _router(distributions={
            ("RG-prompt_id=ARG17", FEATURE): _dist("RG-prompt_id=ARG17"),
        }).route(TaskSignature(prompt_id=None, genre=None))
        assert result.routed is False
        assert "incomplete" in (result.unmatched_reason or "")


class TestResultSemantics:
    def test_descriptive_context_only(self) -> None:
        result = _router(distributions={
            ("RG-prompt_id=ARG17", FEATURE): _dist("RG-prompt_id=ARG17"),
        }).route(TaskSignature(prompt_id="ARG17", timed_status="timed", genre="argumentative"))
        assert result.descriptive_only is True
        assert result.learner_exposure == "research_only"
        assert result.artifact_class == "NON-RECONSTRUCTIVE AGGREGATE ARTIFACT"
        assert result.secondary is False

    def test_banned_vocabulary_absent(self) -> None:
        result = _router(distributions={
            ("RG-prompt_id=ARG17", FEATURE): _dist("RG-prompt_id=ARG17"),
        }).route(TaskSignature(prompt_id="ARG17", timed_status="timed", genre="argumentative"))
        sample = json.dumps(result.__dict__, default=str)
        pattern = re.compile(r"\b(proficiency|mastery|CEFR|ability|learning\s+gain)\b", re.IGNORECASE)
        assert pattern.search(sample) is None

    def test_leak_hygiene_no_raw_paths(self) -> None:
        result = _router(distributions={
            ("RG-prompt_id=ARG17", FEATURE): _dist("RG-prompt_id=ARG17"),
        }).route(TaskSignature(prompt_id="ARG17", timed_status="timed", genre="argumentative"))
        sample = json.dumps(result.__dict__, default=str)
        # Negative denial: the routing result must never carry an absolute
        # drive-letter path (the raw SWECCL root lives on one). The prefix is
        # derived from os.path so the assertion stays platform-independent;
        # on POSIX there is no drive letter and the check is trivially true.
        drive, _ = os.path.splitdrive(os.path.abspath(__file__))
        drive_root = f"{drive}{os.sep}" if drive else ""
        assert drive_root not in sample
        assert "SWECCL 2.0" not in sample
        assert "PREPARED" not in sample

    def test_provenance_and_exposure(self) -> None:
        result = _router(distributions={
            ("RG-prompt_id=ARG17", FEATURE): _dist("RG-prompt_id=ARG17"),
        }).route(TaskSignature(prompt_id="ARG17", timed_status="timed", genre="argumentative"))
        provenance = result.provenance
        assert provenance["corpus_package_id"] == WECCL_PACKAGE_ID
        assert provenance["manifest_hash"] == "0" * 64
        assert provenance["learner_exposure"] == "research_only"
        assert provenance["descriptive_only"] is True
