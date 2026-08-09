"""Capability manifest schema (ADR-01/02/08).

A manifest is the additive metadata record for one capability: globally
unique identity, semantic version, owning department, domain eligibility,
operation scope, data-access scope, source, enablement, and audit
requirement.  The registry never replaces an authoritative domain registry:
it federates real domain entry points declared by these manifests
(ADR-02 federation-as-read-only-adapter; DeepTutor
``CapabilityManifest`` in ``deeptutor/core/capability_protocol.py`` is the
read-only mechanism reference).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.runtime.errors import ManifestValidationError

_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def validate_manifest(manifest: "CapabilityManifest") -> None:
    """Validate manifest fields; raise ``ManifestValidationError`` on failure."""
    if not isinstance(manifest.identity, str) or not manifest.identity.strip():
        raise ManifestValidationError("manifest identity must be a non-empty string")
    if any(ch.isspace() for ch in manifest.identity):
        raise ManifestValidationError(
            f"manifest identity must not contain whitespace: {manifest.identity!r}"
        )
    if not _SEMVER.match(manifest.version):
        raise ManifestValidationError(
            f"manifest version must be semantic x.y.z: {manifest.version!r}"
        )
    if not isinstance(manifest.owner, str) or not manifest.owner.strip():
        raise ManifestValidationError("manifest owner must be a non-empty string")
    if not manifest.domain_eligibility:
        raise ManifestValidationError("manifest domain_eligibility must not be empty")
    if not manifest.scope:
        raise ManifestValidationError("manifest scope must not be empty")


@dataclass(frozen=True)
class CapabilityManifest:
    """Static metadata for one capability (ADR-01/02/08 fields)."""

    identity: str
    version: str
    owner: str
    description: str
    domain_eligibility: tuple[str, ...]
    scope: tuple[str, ...]
    data_access: tuple[str, ...] = field(default_factory=tuple)
    source: str = "builtin"
    enabled: bool = True
    audit_required: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_manifest(self)


__all__ = ["CapabilityManifest", "validate_manifest"]
