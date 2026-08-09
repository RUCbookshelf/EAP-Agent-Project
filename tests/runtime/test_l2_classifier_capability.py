"""L2 task-type classification capability: real Domain Pack v1 classifier."""

from __future__ import annotations

from app.runtime.capabilities import L2TaskTypeClassifierCapability
from app.runtime.executor import STATUS_ERROR, STATUS_INELIGIBLE, STATUS_SUCCESS, CapabilityExecutor
from app.runtime.registry import CapabilityRegistry


def _classifier_executor() -> CapabilityExecutor:
    capability = L2TaskTypeClassifierCapability()
    registry = CapabilityRegistry()
    registry.register(capability.manifest, capability)
    return CapabilityExecutor(registry)


def test_typed_discussion_classification() -> None:
    result = _classifier_executor().execute(
        "l2.task_type_classifier",
        request={
            "prompt": (
                "Some people think university students should study abroad, while others "
                "believe they should study in their own country. Discuss both views and "
                "give your own opinion."
            )
        },
        caller_domain="l2",
    )
    assert result.status == STATUS_SUCCESS
    assert result.result["outcome"] == "typed"
    assert result.result["task_type"] == "discussion"
    assert result.result["reason_code"] is None
    assert result.result["taxonomy_version"] == "l2-task-type-taxonomy-v1.0.0"


def test_typed_opinion_classification() -> None:
    result = _classifier_executor().execute(
        "l2.task_type_classifier",
        request={"prompt": "Do you agree or disagree with this statement? What is your opinion?"},
        caller_domain="l2",
    )
    assert result.status == STATUS_SUCCESS
    assert result.result["task_type"] == "opinion"


def test_honest_unclassified_not_eap() -> None:
    result = _classifier_executor().execute(
        "l2.task_type_classifier", request={"prompt": "Hello world."}, caller_domain="l2"
    )
    assert result.status == STATUS_SUCCESS
    assert result.result["outcome"] == "unclassified"
    assert result.result["task_type"] is None
    assert result.result["reason_code"] == "not_eap"


def test_honest_unclassified_conflict() -> None:
    result = _classifier_executor().execute(
        "l2.task_type_classifier",
        request={"prompt": "Discuss both views and take a position, arguing with evidence."},
        caller_domain="l2",
    )
    assert result.status == STATUS_SUCCESS
    assert result.result["outcome"] == "unclassified"
    assert result.result["reason_code"] == "ambiguous_precedence_conflict"


def test_invalid_declared_type_is_isolated_error_not_crash() -> None:
    result = _classifier_executor().execute(
        "l2.task_type_classifier",
        request={"prompt": "What is your opinion?", "declared_task_type": "bogus_type"},
        caller_domain="l2",
    )
    assert result.status == STATUS_ERROR
    assert result.error["type"] == "TaskTypeClassificationError"


def test_provenance_passthrough() -> None:
    result = _classifier_executor().execute(
        "l2.task_type_classifier",
        request={"prompt": "Do you agree or disagree? Give your reasons."},
        caller_domain="l2",
    )
    provenance = result.result["provenance"]
    assert provenance["rule_version"] == "l2-domain-pack-v1.0.0"
    assert provenance["classification_scope"] == "task_definition_only"
    assert provenance["legacy_sentinel_unreachable"] == "legacy_unclassified"


def test_list_task_types_operation() -> None:
    result = _classifier_executor().execute(
        "l2.task_type_classifier",
        request={"operation": "list_task_types"},
        caller_domain="l2",
    )
    assert result.status == STATUS_SUCCESS
    assert result.result["display_order"][0] == "opinion"


def test_capability_is_ineligible_for_non_l2_caller() -> None:
    result = _classifier_executor().execute(
        "l2.task_type_classifier",
        request={"prompt": "What is your opinion?"},
        caller_domain="ux",
    )
    assert result.status == STATUS_INELIGIBLE
    assert result.reason == "domain_not_eligible"
