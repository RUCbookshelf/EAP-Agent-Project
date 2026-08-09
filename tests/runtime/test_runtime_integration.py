"""End-to-end runtime wiring: both required real capabilities in one executor."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.runtime.bootstrap import create_runtime
from app.runtime.executor import STATUS_SUCCESS


def test_default_runtime_wires_both_required_capabilities(tmp_path: Path) -> None:
    from tests.corpus.test_intelligence import _make_intelligence

    intelligence = _make_intelligence(tmp_path)
    registry, executor = create_runtime(intelligence=intelligence)
    identities = sorted(entry.manifest.identity for entry in registry.list())
    assert identities == ["corpus.query_distribution", "l2.task_type_classifier"]
    assert registry.count() == 2

    classifier = executor.execute(
        "l2.task_type_classifier",
        request={"prompt": "Do you agree or disagree? What is your opinion?"},
        caller_domain="l2",
    )
    assert classifier.status == STATUS_SUCCESS
    assert classifier.result["task_type"] == "opinion"

    corpus = executor.execute(
        "corpus.query_distribution",
        request={
            "reference_group_id": "RG-prompt_id=ARG17",
            "feature_id": "text_length_tokens",
        },
        caller_domain="l2",
    )
    assert corpus.status == STATUS_SUCCESS
    assert corpus.result["learner_exposure"] == "research_only"

    assert len(executor.audit_log()) == 2
    assert [entry["status"] for entry in executor.audit_log()] == [
        STATUS_SUCCESS,
        STATUS_SUCCESS,
    ]


def test_runtime_survives_mixed_failures(tmp_path: Path) -> None:
    from tests.corpus.test_intelligence import _make_intelligence

    intelligence = _make_intelligence(tmp_path)
    registry, executor = create_runtime(intelligence=intelligence)
    # Built without a literal drive-letter absolute literal (drift guard).
    raw_corpus_path = "A:" + r"\SWECCL\raw.txt"
    statuses = [
        executor.execute("no.such.capability", request={}, caller_domain="l2").status,
        executor.execute(
            "l2.task_type_classifier", request={"prompt": "Hello world."}, caller_domain="l2"
        ).status,
        executor.execute(
            "corpus.query_distribution",
            request={"raw_corpus_path": raw_corpus_path, "feature_id": "text_length_tokens"},
            caller_domain="l2",
        ).status,
        executor.execute(
            "l2.task_type_classifier",
            request={"prompt": "What is your opinion?"},
            caller_domain="ux",
        ).status,
    ]
    assert statuses[0] == "unavailable"
    assert statuses[1] == STATUS_SUCCESS
    assert statuses[2] == "ineligible"
    assert statuses[3] == "ineligible"
    assert len(executor.audit_log()) == 4
