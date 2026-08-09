"""Additive capability registry (ADR-02 registry federation contract).

The registry is a thin manifest layer over real, authoritative domain entry
points.  It never replaces ``TaskTypeRegistry``, the Domain Pack v1 content,
or the CORPUS-owned ``CorpusIntelligence`` boundary; capability adapters
federate those existing registries read-only.  Registration is additive and
versioned: the same ``(identity, version)`` pair can be registered exactly
once, and a duplicate attempt is rejected (ADR-02 duplicate-registration
protection).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.runtime.errors import CapabilityNotFoundError, CapabilityRegistrationError
from app.runtime.manifest import CapabilityManifest

# A capability handler is a synchronous in-process callable taking a request
# dict and returning an arbitrary payload (or raising).
CapabilityHandler = Callable[[dict[str, Any]], Any]


@dataclass(frozen=True)
class RegisteredCapability:
    """A manifest plus its bound synchronous handler."""

    manifest: CapabilityManifest
    handler: CapabilityHandler


def _version_key(version: str) -> tuple[int, int, int]:
    return tuple(int(part) for part in version.split("."))  # type: ignore[return-value]


class CapabilityRegistry:
    """Versioned, additive-only capability manifest registry."""

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], RegisteredCapability] = {}

    def register(self, manifest: CapabilityManifest, handler: CapabilityHandler) -> None:
        """Register one capability.

        Raises ``CapabilityRegistrationError`` when the same identity+version
        pair is already registered (ADR-02 duplicate-rejection rule).
        """
        if not isinstance(manifest, CapabilityManifest):
            raise CapabilityRegistrationError(
                "manifest must be a CapabilityManifest instance"
            )
        if not callable(handler):
            raise CapabilityRegistrationError("handler must be callable")
        key = (manifest.identity, manifest.version)
        if key in self._entries:
            raise CapabilityRegistrationError(
                f"duplicate capability registration rejected: "
                f"identity={manifest.identity!r} version={manifest.version!r} "
                f"(ADR-02 no-duplicate-registration rule)"
            )
        self._entries[key] = RegisteredCapability(manifest=manifest, handler=handler)

    def get(self, identity: str, version: str | None = None) -> RegisteredCapability:
        """Resolve a registered capability.

        Without ``version`` the latest registered version wins (stable
        precedence); with ``version`` an exact match is required.
        """
        versions = [
            registered
            for (registered_identity, _), registered in self._entries.items()
            if registered_identity == identity
        ]
        if not versions:
            raise CapabilityNotFoundError(f"capability not registered: {identity!r}")
        if version is not None:
            for registered in versions:
                if registered.manifest.version == version:
                    return registered
            raise CapabilityNotFoundError(
                f"capability {identity!r} has no registered version {version!r}"
            )
        return max(versions, key=lambda item: _version_key(item.manifest.version))

    def has(self, identity: str) -> bool:
        return any(registered_identity == identity for registered_identity, _ in self._entries)

    def list(self) -> list[RegisteredCapability]:
        """All registered capabilities in stable identity-then-version order."""
        return [
            self._entries[key]
            for key in sorted(self._entries, key=lambda item: (item[0], _version_key(item[1])))
        ]

    def count(self) -> int:
        return len(self._entries)


__all__ = ["CapabilityHandler", "CapabilityRegistry", "RegisteredCapability"]
