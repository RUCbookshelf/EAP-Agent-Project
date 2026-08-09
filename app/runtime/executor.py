"""Synchronous capability executor (existing-runtime capability execution v1).

The executor is plain synchronous in-process code: no orchestrator, no event
bus, no second composition root, no runtime database (ADR-01).  It resolves a
capability from the additive registry, performs eligibility/scope checks at
dispatch time, invokes the bound handler inside an exception-isolation
boundary, and returns a structured ``CapabilityResult`` with provenance and
audit records.  Unknown/disabled capabilities are ``unavailable``; eligibility
and scope denials are ``ineligible``; handler failures are ``error`` — the
caller never receives a raised exception from capability execution.

Mechanism reference (read-only): DeepTutor dispatch-time resolution and
structured tool results in ``deeptutor/core/agentic/tool_dispatch.py``
(``execute_tool_call`` returns a structured outcome and isolates exceptions);
no code was copied.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import time
from typing import Any
from uuid import uuid4

from app.runtime.errors import (
    CapabilityDeniedError,
    CapabilityNotFoundError,
    CapabilityRequestError,
    CapabilityUnavailableError,
)
from app.runtime.registry import CapabilityRegistry

STATUS_SUCCESS = "success"
STATUS_UNAVAILABLE = "unavailable"
STATUS_INELIGIBLE = "ineligible"
STATUS_ERROR = "error"

RUNTIME_PROVENANCE_ID = "existing-runtime-capability-execution-v1"


@dataclass(frozen=True)
class CapabilityResult:
    """Structured result of one capability dispatch (never a raised exception)."""

    status: str
    capability_id: str
    capability_version: str
    owner: str
    request_id: str
    operation: str
    caller_domain: str | None
    started_at: str
    duration_ms: float
    result: Any = None
    reason: str | None = None
    error: dict[str, Any] | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "capability_id": self.capability_id,
            "capability_version": self.capability_version,
            "owner": self.owner,
            "request_id": self.request_id,
            "operation": self.operation,
            "caller_domain": self.caller_domain,
            "started_at": self.started_at,
            "duration_ms": self.duration_ms,
            "result": self.result,
            "reason": self.reason,
            "error": self.error,
            "provenance": self.provenance,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CapabilityExecutor:
    """Resolves, checks, invokes, and audits one capability synchronously."""

    def __init__(self, registry: CapabilityRegistry) -> None:
        self._registry = registry
        self._audit: list[dict[str, Any]] = []

    def execute(
        self,
        capability_id: str,
        *,
        request: dict[str, Any] | None = None,
        caller_domain: str | None = None,
        request_id: str | None = None,
    ) -> CapabilityResult:
        """Execute one capability and return a structured result.

        Never raises for capability execution failures: every outcome is an
        explicit ``success`` / ``unavailable`` / ``ineligible`` / ``error``
        state with a provenance/audit record.
        """
        request = request or {}
        request_id = request_id or uuid4().hex
        started_at = _now_iso()
        started_perf = time.perf_counter()
        operation = str(request.get("operation") or "")
        status: str = STATUS_SUCCESS
        reason: str | None = None
        error: dict[str, Any] | None = None
        payload: Any = None

        try:
            registered = self._registry.get(capability_id)
        except CapabilityNotFoundError as exc:
            status = STATUS_UNAVAILABLE
            reason = "capability_unregistered"
            error = {"kind": "unavailable", "type": "CapabilityNotFoundError", "message": str(exc)}
            operation = operation or "unknown"
            return self._finish(
                status=status,
                capability_id=capability_id,
                capability_version="unknown",
                owner="unknown",
                operation=operation,
                caller_domain=caller_domain,
                request_id=request_id,
                started_at=started_at,
                started_perf=started_perf,
                result=payload,
                reason=reason,
                error=error,
            )

        manifest = registered.manifest
        if not manifest.enabled:
            status = STATUS_UNAVAILABLE
            reason = "capability_disabled"
            error = {"kind": "unavailable", "type": "capability_disabled", "message": reason}
        elif caller_domain is None:
            status = STATUS_INELIGIBLE
            reason = "caller_domain_required"
            error = {
                "kind": "ineligible",
                "type": "caller_domain_required",
                "message": "a caller domain must be declared (deny-by-default, ADR-08)",
            }
        elif (
            "*" not in manifest.domain_eligibility
            and caller_domain not in manifest.domain_eligibility
        ):
            status = STATUS_INELIGIBLE
            reason = "domain_not_eligible"
            error = {
                "kind": "ineligible",
                "type": "domain_not_eligible",
                "message": (
                    f"caller domain {caller_domain!r} is not eligible for "
                    f"{capability_id!r}; eligible domains: "
                    f"{list(manifest.domain_eligibility)}"
                ),
            }

        if status == STATUS_SUCCESS:
            operation = operation or manifest.scope[0]
            if operation not in manifest.scope:
                status = STATUS_INELIGIBLE
                reason = "operation_not_in_scope"
                error = {
                    "kind": "ineligible",
                    "type": "operation_not_in_scope",
                    "message": (
                        f"operation {operation!r} is not in the declared scope of "
                        f"{capability_id!r}: {list(manifest.scope)}"
                    ),
                }

        if status == STATUS_SUCCESS:
            try:
                payload = registered.handler(request)
            except CapabilityDeniedError as exc:
                status = STATUS_INELIGIBLE
                reason = str(exc)
                error = {
                    "kind": "ineligible",
                    "type": "CapabilityDeniedError",
                    "message": str(exc),
                }
            except CapabilityUnavailableError as exc:
                status = STATUS_UNAVAILABLE
                reason = str(exc)
                error = {
                    "kind": "unavailable",
                    "type": "CapabilityUnavailableError",
                    "message": str(exc),
                }
            except CapabilityRequestError as exc:
                status = STATUS_ERROR
                reason = "request_error"
                error = {
                    "kind": "request_error",
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            except Exception as exc:  # exception isolation: never crash the caller
                status = STATUS_ERROR
                reason = "unexpected_exception"
                error = {
                    "kind": "unexpected_exception",
                    "type": type(exc).__name__,
                    "message": str(exc),
                }

        return self._finish(
            status=status,
            capability_id=manifest.identity,
            capability_version=manifest.version,
            owner=manifest.owner,
            operation=operation,
            caller_domain=caller_domain,
            request_id=request_id,
            started_at=started_at,
            started_perf=started_perf,
            result=payload,
            reason=reason,
            error=error,
        )

    def _finish(
        self,
        *,
        status: str,
        capability_id: str,
        capability_version: str,
        owner: str,
        operation: str,
        caller_domain: str | None,
        request_id: str,
        started_at: str,
        started_perf: float,
        result: Any,
        reason: str | None,
        error: dict[str, Any] | None,
    ) -> CapabilityResult:
        duration_ms = (time.perf_counter() - started_perf) * 1000.0
        audit_index = len(self._audit)
        self._audit.append(
            {
                "index": audit_index,
                "request_id": request_id,
                "capability_id": capability_id,
                "capability_version": capability_version,
                "owner": owner,
                "caller_domain": caller_domain,
                "operation": operation,
                "status": status,
                "started_at": started_at,
                "ended_at": _now_iso(),
                "duration_ms": duration_ms,
                "error": error,
            }
        )
        provenance = {
            "request_id": request_id,
            "capability_id": capability_id,
            "capability_version": capability_version,
            "owner": owner,
            "caller_domain": caller_domain,
            "operation": operation,
            "status": status,
            "started_at": started_at,
            "duration_ms": duration_ms,
            "audit_index": audit_index,
            "runtime": RUNTIME_PROVENANCE_ID,
        }
        return CapabilityResult(
            status=status,
            capability_id=capability_id,
            capability_version=capability_version,
            owner=owner,
            request_id=request_id,
            operation=operation,
            caller_domain=caller_domain,
            started_at=started_at,
            duration_ms=duration_ms,
            result=result,
            reason=reason,
            error=error,
            provenance=provenance,
        )

    def audit_log(self) -> list[dict[str, Any]]:
        """In-process audit records for every dispatch (append-only)."""
        return list(self._audit)


__all__ = [
    "CapabilityExecutor",
    "CapabilityResult",
    "RUNTIME_PROVENANCE_ID",
    "STATUS_ERROR",
    "STATUS_INELIGIBLE",
    "STATUS_SUCCESS",
    "STATUS_UNAVAILABLE",
]
