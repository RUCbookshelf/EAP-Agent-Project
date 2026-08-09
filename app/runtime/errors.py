"""Runtime error taxonomy for existing-runtime capability execution v1.

The executor maps these exceptions to explicit structured states so a
capability failure can never crash the caller (ADR-01 lifecycle
requirement 3; DeepTutor ``tool_dispatch.execute_tool_call`` exception
isolation pattern, read-only reference).
"""

from __future__ import annotations


class ManifestValidationError(ValueError):
    """A capability manifest failed schema validation (ADR-08 deny-by-default)."""


class CapabilityRegistrationError(ValueError):
    """Duplicate registration (same identity + version) is rejected (ADR-02)."""


class CapabilityNotFoundError(KeyError):
    """No capability with the requested identity is registered."""


class CapabilityUnavailableError(RuntimeError):
    """The capability (or the domain resource it needs) is genuinely unavailable.

    Mapped by the executor to the explicit ``unavailable`` state; never
    fabricated and never coerced into a success.
    """


class CapabilityDeniedError(RuntimeError):
    """Dispatch-time authorization/scope denial (ADR-08 deny-by-default).

    Mapped by the executor to the explicit ``ineligible`` state.
    """


class CapabilityRequestError(ValueError):
    """The request is invalid for this capability (rejection path)."""
