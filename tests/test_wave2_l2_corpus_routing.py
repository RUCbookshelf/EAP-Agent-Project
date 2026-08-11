"""Wave-2 Goal C -- written-corpus routing protocol/fake tests (TDD red phase).

The L2 branch does not contain the CORPUS routing module (it lands at
integration). This module consumes the modality-aware routing contract
semantics through a LOCALLY DEFINED protocol/fake: written requests route to
the primary written resource (WECCL20) by default; SECCL20 is spoken +
secondary/research_only and is never a written candidate without an explicit
spoken opt-in. The local module must NOT import ``app.corpus.routing``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.l2.wave2.corpus_routing import (
    MODALITY_SPOKEN,
    MODALITY_WRITTEN,
    SECCL_PACKAGE_ID,
    WECCL_PACKAGE_ID,
    CorpusRoutingProtocol,
    LocalWrittenCorpusRouter,
    WrittenCorpusRoutingRequest,
)


def _request(**overrides) -> WrittenCorpusRoutingRequest:
    values = dict(
        task_type="argumentative",
        writing_context="ielts_task2",
        writing_prompt="Take a position on studying abroad.",
        modality=MODALITY_WRITTEN,
    )
    values.update(overrides)
    return WrittenCorpusRoutingRequest(**values)


class TestWrittenDefault:
    def test_written_request_routes_to_weccl20_by_default(self) -> None:
        router = LocalWrittenCorpusRouter()
        result = router.route(_request())
        assert result.routed is True
        assert result.resolved_resource_id == WECCL_PACKAGE_ID
        assert result.resolved_reference_group_id is not None
        assert result.learner_exposure == "research_only"
        assert result.descriptive_only is True
        assert result.secondary is False

    def test_written_request_never_routes_to_seccl(self) -> None:
        router = LocalWrittenCorpusRouter()
        result = router.route(_request())
        assert result.corpus_package_id == WECCL_PACKAGE_ID
        assert result.corpus_package_id != SECCL_PACKAGE_ID


class TestSecclExclusion:
    def test_spoken_request_without_opt_in_is_refused_with_disclosure(self) -> None:
        router = LocalWrittenCorpusRouter()
        result = router.route(_request(modality=MODALITY_SPOKEN))
        assert result.routed is False
        assert result.unmatched_reason is not None
        assert "spoken" in result.unmatched_reason.casefold()
        assert "secondary" in result.unmatched_reason.casefold()

    def test_spoken_opt_in_still_requires_research_only_and_spoken_domain(self) -> None:
        router = LocalWrittenCorpusRouter()
        result = router.route(
            _request(modality=MODALITY_SPOKEN),
            domain="l2_speaking",
            allow_secondary=True,
        )
        assert result.routed is True
        assert result.resolved_resource_id == SECCL_PACKAGE_ID
        assert result.secondary is True
        assert result.learner_exposure == "research_only"

    def test_spoken_opt_in_rejected_for_writing_domain(self) -> None:
        router = LocalWrittenCorpusRouter()
        result = router.route(_request(modality=MODALITY_SPOKEN), allow_secondary=True)
        assert result.routed is False


class TestEligibilityGating:
    def test_invalid_modality_rejected(self) -> None:
        router = LocalWrittenCorpusRouter()
        with pytest.raises(ValueError):
            router.route(_request(modality="braille"))

    def test_unknown_task_type_rejected(self) -> None:
        router = LocalWrittenCorpusRouter()
        with pytest.raises(ValueError):
            router.route(_request(task_type="persuasive_essay"))

    def test_resolved_reference_group_is_context_aware(self) -> None:
        router = LocalWrittenCorpusRouter()
        result = router.route(_request(task_type="discussion", writing_context="cet6"))
        assert result.routed is True
        assert result.resolved_reference_group_id is not None
        assert "discussion" in result.resolved_reference_group_id
        assert "cet6" in result.resolved_reference_group_id


class TestNoCorpusRoutingImport:
    def test_module_does_not_import_app_corpus_routing(self) -> None:
        source = Path(
            "app/l2/wave2/corpus_routing.py"
        ).read_text(encoding="utf-8")
        assert "app.corpus.routing" not in source

    def test_router_satisfies_protocol(self) -> None:
        assert isinstance(LocalWrittenCorpusRouter(), CorpusRoutingProtocol)
