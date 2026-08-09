"""CapabilityExecutor tests: eligibility checks, unavailable/ineligible states,
exception isolation, and provenance/audit records."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.runtime.errors import (
    CapabilityDeniedError,
    CapabilityUnavailableError,
)
from app.runtime.executor import (
    STATUS_ERROR,
    STATUS_INELIGIBLE,
    STATUS_SUCCESS,
    STATUS_UNAVAILABLE,
    CapabilityExecutor,
    CapabilityResult,
)
from app.runtime.manifest import CapabilityManifest
from app.runtime.registry import CapabilityRegistry


def _manifest(
    *,
    identity: str = "demo.echo",
    version: str = "1.0.0",
    owner: str = "CORE",
    domain_eligibility: tuple[str, ...] = ("l2",),
    scope: tuple[str, ...] = ("echo",),
    enabled: bool = True,
) -> CapabilityManifest:
    return CapabilityManifest(
        identity=identity,
        version=version,
        owner=owner,
        description="Demo capability.",
        domain_eligibility=domain_eligibility,
        scope=scope,
        enabled=enabled,
    )


def _executor_with(manifest: CapabilityManifest, handler) -> CapabilityExecutor:
    registry = CapabilityRegistry()
    registry.register(manifest, handler)
    return CapabilityExecutor(registry)


def test_successful_invocation_returns_structured_result() -> None:
    executor = _executor_with(_manifest(), lambda request: {"echo": request.get("text")})
    result = executor.execute(
        "demo.echo", request={"text": "hello"}, caller_domain="l2", request_id="req-1"
    )
    assert isinstance(result, CapabilityResult)
    assert result.status == STATUS_SUCCESS
    assert result.result == {"echo": "hello"}
    assert result.error is None
    assert result.reason is None
    assert result.capability_id == "demo.echo"
    assert result.capability_version == "1.0.0"
    assert result.owner == "CORE"
    assert result.request_id == "req-1"


def test_unavailable_when_capability_not_registered() -> None:
    executor = CapabilityExecutor(CapabilityRegistry())
    result = executor.execute("no.such.capability", request={}, caller_domain="l2")
    assert result.status == STATUS_UNAVAILABLE
    assert result.reason == "capability_unregistered"
    assert result.result is None
    assert result.error is not None


def test_unavailable_when_capability_disabled() -> None:
    executor = _executor_with(_manifest(enabled=False), lambda request: {"ok": True})
    result = executor.execute("demo.echo", request={}, caller_domain="l2")
    assert result.status == STATUS_UNAVAILABLE
    assert result.reason == "capability_disabled"
    assert result.result is None


def test_ineligible_when_caller_domain_missing() -> None:
    executor = _executor_with(_manifest(), lambda request: {"ok": True})
    result = executor.execute("demo.echo", request={}, caller_domain=None)
    assert result.status == STATUS_INELIGIBLE
    assert result.reason == "caller_domain_required"


def test_ineligible_when_domain_not_eligible() -> None:
    executor = _executor_with(_manifest(domain_eligibility=("l2",)), lambda request: {"ok": True})
    result = executor.execute("demo.echo", request={}, caller_domain="ux")
    assert result.status == STATUS_INELIGIBLE
    assert result.reason == "domain_not_eligible"
    assert result.result is None


def test_ineligible_when_operation_not_in_scope() -> None:
    executor = _executor_with(_manifest(scope=("echo",)), lambda request: {"ok": True})
    result = executor.execute(
        "demo.echo", request={"operation": "delete_everything"}, caller_domain="l2"
    )
    assert result.status == STATUS_INELIGIBLE
    assert result.reason == "operation_not_in_scope"
    assert result.result is None


def test_exception_isolation_never_crashes_caller() -> None:
    def boom(_request: dict) -> dict:
        raise RuntimeError("handler exploded")

    executor = _executor_with(_manifest(), boom)
    result = executor.execute("demo.echo", request={}, caller_domain="l2")
    assert result.status == STATUS_ERROR
    assert result.result is None
    assert result.error is not None
    assert result.error["type"] == "RuntimeError"
    assert "handler exploded" in result.error["message"]
    # Executor remains usable after a failure.
    second = _executor_with(_manifest(), lambda request: {"ok": True}).execute(
        "demo.echo", request={}, caller_domain="l2"
    )
    assert second.status == STATUS_SUCCESS


def test_denied_error_maps_to_ineligible() -> None:
    def deny(_request: dict) -> dict:
        raise CapabilityDeniedError("raw source access denied")

    executor = _executor_with(_manifest(), deny)
    result = executor.execute("demo.echo", request={}, caller_domain="l2")
    assert result.status == STATUS_INELIGIBLE
    assert result.reason == "raw source access denied"


def test_unavailable_error_maps_to_unavailable() -> None:
    def unavailable(_request: dict) -> dict:
        raise CapabilityUnavailableError("distribution artifact missing")

    executor = _executor_with(_manifest(), unavailable)
    result = executor.execute("demo.echo", request={}, caller_domain="l2")
    assert result.status == STATUS_UNAVAILABLE
    assert result.reason == "distribution artifact missing"


def test_provenance_and_audit_fields_recorded() -> None:
    executor = _executor_with(_manifest(), lambda request: {"ok": True})
    result = executor.execute(
        "demo.echo", request={"operation": "echo", "text": "x"}, caller_domain="l2"
    )
    provenance = result.provenance
    assert provenance["request_id"] == result.request_id
    assert provenance["capability_id"] == "demo.echo"
    assert provenance["capability_version"] == "1.0.0"
    assert provenance["owner"] == "CORE"
    assert provenance["caller_domain"] == "l2"
    assert provenance["operation"] == "echo"
    assert provenance["status"] == STATUS_SUCCESS
    assert provenance["runtime"] == "existing-runtime-capability-execution-v1"
    assert provenance["audit_index"] == 0
    assert result.duration_ms >= 0
    started = datetime.fromisoformat(result.started_at)
    assert started.tzinfo is not None

    audit = executor.audit_log()
    assert len(audit) == 1
    entry = audit[0]
    assert entry["request_id"] == result.request_id
    assert entry["capability_id"] == "demo.echo"
    assert entry["capability_version"] == "1.0.0"
    assert entry["owner"] == "CORE"
    assert entry["caller_domain"] == "l2"
    assert entry["operation"] == "echo"
    assert entry["status"] == STATUS_SUCCESS
    assert entry["duration_ms"] == result.duration_ms


def test_audit_records_failures_and_unavailable_calls() -> None:
    executor = _executor_with(_manifest(), lambda request: {"ok": True})
    executor.execute("demo.missing", request={}, caller_domain="l2")
    executor.execute("demo.echo", request={}, caller_domain="ux")
    audit = executor.audit_log()
    assert [entry["status"] for entry in audit] == [STATUS_UNAVAILABLE, STATUS_INELIGIBLE]
    assert all(entry["request_id"] for entry in audit)


def test_result_to_dict_serializes() -> None:
    executor = _executor_with(_manifest(), lambda request: {"ok": True})
    result = executor.execute("demo.echo", request={}, caller_domain="l2")
    payload = result.to_dict()
    assert payload["status"] == STATUS_SUCCESS
    assert payload["capability_id"] == "demo.echo"
    assert set(payload) >= {
        "status",
        "capability_id",
        "capability_version",
        "owner",
        "request_id",
        "operation",
        "caller_domain",
        "started_at",
        "duration_ms",
        "result",
        "reason",
        "error",
        "provenance",
    }
