"""Canonical request-error taxonomy for the writing-feedback-mvp.

Single model used by server-side exception mapping and client-side
classification. No secrets, essay text, or private paths may enter
the public payload fields.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ErrorCategory(str, Enum):
    SERVICE_NOT_RUNNING = "service_not_running"
    SERVICE_STARTING = "service_starting"
    SERVICE_DEGRADED = "service_degraded"
    SERVICE_FAILED = "service_failed"
    REQUEST_TIMEOUT = "request_timeout"
    CONNECTION_INTERRUPTED = "connection_interrupted"
    RESOURCE_NOT_FOUND = "resource_not_found"
    INVALID_REQUEST = "invalid_request"
    BACKEND_PROCESSING_ERROR = "backend_processing_error"
    INVALID_RESPONSE = "invalid_response"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PERMISSION_OR_PRIVACY_REJECTION = "permission_or_privacy_rejection"
    CONFLICT_OR_DUPLICATE_REQUEST = "conflict_or_duplicate_request"
    UNKNOWN_ERROR = "unknown_error"


# Message keys are stable locale keys (en.json / zh_CN.json).
CATEGORY_MESSAGE_KEY: dict[ErrorCategory, str] = {
    ErrorCategory.SERVICE_NOT_RUNNING: "error_service_not_running",
    ErrorCategory.SERVICE_STARTING: "error_service_starting",
    ErrorCategory.SERVICE_DEGRADED: "error_service_degraded",
    ErrorCategory.SERVICE_FAILED: "error_service_failed",
    ErrorCategory.REQUEST_TIMEOUT: "error_request_timeout",
    ErrorCategory.CONNECTION_INTERRUPTED: "error_connection_interrupted",
    ErrorCategory.RESOURCE_NOT_FOUND: "error_resource_not_found",
    ErrorCategory.INVALID_REQUEST: "error_invalid_request",
    ErrorCategory.BACKEND_PROCESSING_ERROR: "error_backend_processing_error",
    ErrorCategory.INVALID_RESPONSE: "error_invalid_response",
    ErrorCategory.PROVIDER_UNAVAILABLE: "error_provider_unavailable",
    ErrorCategory.PERMISSION_OR_PRIVACY_REJECTION: "error_permission_privacy",
    ErrorCategory.CONFLICT_OR_DUPLICATE_REQUEST: "error_conflict_duplicate",
    ErrorCategory.UNKNOWN_ERROR: "error_unknown",
}

# Retryability: automatic retry is allowed ONLY for these categories and
# only for idempotent (read-only) operations. State-changing operations are
# never automatically retried.
RETRYABLE_CATEGORIES: frozenset[ErrorCategory] = frozenset({
    ErrorCategory.SERVICE_STARTING,
    ErrorCategory.CONNECTION_INTERRUPTED,
    ErrorCategory.REQUEST_TIMEOUT,
})

# Default HTTP status per category when the server emits the error.
CATEGORY_HTTP_STATUS: dict[ErrorCategory, int] = {
    ErrorCategory.SERVICE_NOT_RUNNING: 503,
    ErrorCategory.SERVICE_STARTING: 503,
    ErrorCategory.SERVICE_DEGRADED: 503,
    ErrorCategory.SERVICE_FAILED: 503,
    ErrorCategory.REQUEST_TIMEOUT: 504,
    ErrorCategory.CONNECTION_INTERRUPTED: 502,
    ErrorCategory.RESOURCE_NOT_FOUND: 404,
    ErrorCategory.INVALID_REQUEST: 400,
    ErrorCategory.BACKEND_PROCESSING_ERROR: 500,
    ErrorCategory.INVALID_RESPONSE: 502,
    ErrorCategory.PROVIDER_UNAVAILABLE: 503,
    ErrorCategory.PERMISSION_OR_PRIVACY_REJECTION: 403,
    ErrorCategory.CONFLICT_OR_DUPLICATE_REQUEST: 409,
    ErrorCategory.UNKNOWN_ERROR: 500,
}


@dataclass
class ApiError:
    """Canonical error payload shared by server responses and client parsing."""

    category: ErrorCategory
    message_key: str
    operation: str
    request_id: str | None = None
    http_status: int | None = None
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    retryable: bool = False
    detail: str | None = None  # sanitized technical detail (Research/System Audit only)
    field_errors: list[dict[str, Any]] = field(default_factory=list)
    original_exception: str | None = None  # local logs only; never in public payload

    def to_public_dict(self, *, include_detail: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "error": {
                "category": self.category.value,
                "message_key": self.message_key,
                "operation": self.operation,
                "request_id": self.request_id,
                "http_status": self.http_status,
                "timestamp": self.timestamp,
                "retryable": self.retryable,
            }
        }
        if include_detail:
            payload["error"]["detail"] = self.detail
            payload["error"]["field_errors"] = self.field_errors
        return payload

    @classmethod
    def from_category(
        cls,
        category: ErrorCategory,
        operation: str,
        *,
        request_id: str | None = None,
        http_status: int | None = None,
        detail: str | None = None,
        field_errors: list[dict[str, Any]] | None = None,
    ) -> "ApiError":
        retryable = category in RETRYABLE_CATEGORIES
        return cls(
            category=category,
            message_key=CATEGORY_MESSAGE_KEY[category],
            operation=operation,
            request_id=request_id,
            http_status=http_status or CATEGORY_HTTP_STATUS[category],
            retryable=retryable,
            detail=detail,
            field_errors=field_errors or [],
        )
