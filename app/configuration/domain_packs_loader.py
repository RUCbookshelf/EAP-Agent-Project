"""Domain pack loader (D-26, mechanism only).

Loads versioned JSON data files under per-domain namespaces.
Content decisions belong to domain departments; Shared Core owns the mechanism.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_DOMAIN_PACKS_ROOT = Path(__file__).resolve().parent / "domain_packs"
_VERSION_RE = re.compile(r"^v\d+\.\d+\.\d+$")


class DomainPackError(Exception):
    """Base error for domain pack loading."""


class DomainPackNotFoundError(DomainPackError):
    """Requested domain or version does not exist."""


class DomainPackValidationError(DomainPackError):
    """Manifest schema or content validation failed."""


class DomainPackNotRegisteredError(DomainPackError):
    """Domain exists but has no registered pack (e.g. academic in H1)."""


def _validate_manifest(manifest: dict[str, Any], domain: str, version: str) -> None:
    """Validate manifest schema and identity fields."""
    required_keys = [
        "pack_id", "domain", "version", "supported_task_types",
        "dimensions", "resource_requirements", "availability",
        "content_status",
    ]
    missing = [k for k in required_keys if k not in manifest]
    if missing:
        raise DomainPackValidationError(
            f"Manifest missing required keys: {missing}"
        )

    if manifest["domain"] != domain:
        raise DomainPackValidationError(
            f"Manifest domain '{manifest['domain']}' does not match namespace '{domain}'"
        )

    if manifest["version"] != version:
        raise DomainPackValidationError(
            f"Manifest version '{manifest['version']}' does not match path version '{version}'"
        )

    if not _VERSION_RE.match(manifest["version"]):
        raise DomainPackValidationError(
            f"Version format invalid: '{manifest['version']}' (expected vX.Y.Z)"
        )

    for list_key in ("supported_task_types", "dimensions", "resource_requirements"):
        if not isinstance(manifest[list_key], list):
            raise DomainPackValidationError(
                f"'{list_key}' must be a list, got {type(manifest[list_key]).__name__}"
            )

    if not isinstance(manifest["content_status"], dict):
        raise DomainPackValidationError(
            "'content_status' must be a dict"
        )


def load_pack(domain: str, version: str) -> dict[str, Any]:
    """Load a domain pack manifest by domain and version.

    Returns the validated manifest dict. Does NOT wire into product runtime.
    """
    domain_dir = _DOMAIN_PACKS_ROOT / domain
    if not domain_dir.is_dir():
        raise DomainPackNotFoundError(
            f"Domain '{domain}' not found under {_DOMAIN_PACKS_ROOT}"
        )

    if not _VERSION_RE.match(version):
        raise DomainPackValidationError(
            f"Version format invalid: '{version}' (expected vX.Y.Z)"
        )

    pack_dir = domain_dir / version
    if not pack_dir.is_dir():
        raise DomainPackNotFoundError(
            f"Version '{version}' not found for domain '{domain}'"
        )

    manifest_path = pack_dir / "manifest.json"
    if not manifest_path.is_file():
        raise DomainPackValidationError(
            f"manifest.json not found in {pack_dir}"
        )

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DomainPackValidationError(
            f"manifest.json is not valid JSON: {exc}"
        ) from exc

    _validate_manifest(manifest, domain, version)
    return manifest


def domain_exists(domain: str) -> bool:
    """Check whether a domain namespace directory exists."""
    domain_dir = _DOMAIN_PACKS_ROOT / domain
    return domain_dir.is_dir()


def list_available_packs() -> list[dict[str, str]]:
    """List all available domain packs as [{domain, version}]."""
    packs: list[dict[str, str]] = []
    if not _DOMAIN_PACKS_ROOT.is_dir():
        return packs
    for domain_dir in sorted(_DOMAIN_PACKS_ROOT.iterdir()):
        if not domain_dir.is_dir():
            continue
        for version_dir in sorted(domain_dir.iterdir()):
            if not version_dir.is_dir():
                continue
            manifest_path = version_dir / "manifest.json"
            if manifest_path.is_file():
                packs.append({
                    "domain": domain_dir.name,
                    "version": version_dir.name,
                })
    return packs
