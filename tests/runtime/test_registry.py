"""CapabilityRegistry tests: additive manifest registration and duplicate rejection."""

from __future__ import annotations

import pytest

from app.runtime.errors import (
    CapabilityNotFoundError,
    CapabilityRegistrationError,
    ManifestValidationError,
)
from app.runtime.manifest import CapabilityManifest
from app.runtime.registry import CapabilityRegistry


def _manifest(
    *,
    identity: str = "l2.task_type_classifier",
    version: str = "1.0.0",
    owner: str = "L2",
    domain_eligibility: tuple[str, ...] = ("l2",),
    scope: tuple[str, ...] = ("classify_task_definition",),
    enabled: bool = True,
) -> CapabilityManifest:
    return CapabilityManifest(
        identity=identity,
        version=version,
        owner=owner,
        description="Test capability.",
        domain_eligibility=domain_eligibility,
        scope=scope,
        enabled=enabled,
    )


def _handler(request: dict) -> dict:
    return {"echo": request}


def test_register_and_get_carries_manifest_metadata() -> None:
    registry = CapabilityRegistry()
    manifest = _manifest()
    registry.register(manifest, _handler)
    registered = registry.get("l2.task_type_classifier")
    assert registered.manifest.identity == "l2.task_type_classifier"
    assert registered.manifest.version == "1.0.0"
    assert registered.manifest.owner == "L2"
    assert registered.manifest.domain_eligibility == ("l2",)
    assert registered.manifest.scope == ("classify_task_definition",)
    assert registered.handler({"x": 1}) == {"echo": {"x": 1}}


def test_duplicate_registration_same_identity_version_rejected() -> None:
    registry = CapabilityRegistry()
    registry.register(_manifest(), _handler)
    with pytest.raises(CapabilityRegistrationError):
        registry.register(_manifest(), _handler)
    assert registry.count() == 1


def test_same_identity_different_version_is_allowed_and_latest_wins() -> None:
    registry = CapabilityRegistry()
    registry.register(_manifest(version="1.0.0"), _handler)
    registry.register(_manifest(version="1.1.0"), lambda request: {"v": "1.1.0"})
    assert registry.count() == 2
    latest = registry.get("l2.task_type_classifier")
    assert latest.manifest.version == "1.1.0"
    exact = registry.get("l2.task_type_classifier", version="1.0.0")
    assert exact.manifest.version == "1.0.0"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("identity", ""),
        ("identity", "has space"),
        ("version", "1.0"),
        ("version", "v1.0.0"),
        ("owner", ""),
        ("domain_eligibility", ()),
        ("scope", ()),
    ],
)
def test_invalid_manifest_fields_rejected(field: str, value: object) -> None:
    registry = CapabilityRegistry()
    kwargs = {
        "identity": "cap.x",
        "version": "1.0.0",
        "owner": "CORE",
        "description": "Test.",
        "domain_eligibility": ("l2",),
        "scope": ("run",),
    }
    kwargs[field] = value
    with pytest.raises(ManifestValidationError):
        registry.register(CapabilityManifest(**kwargs), _handler)


def test_get_unknown_capability_raises_not_found() -> None:
    registry = CapabilityRegistry()
    with pytest.raises(CapabilityNotFoundError):
        registry.get("no.such.capability")


def test_list_and_count() -> None:
    registry = CapabilityRegistry()
    registry.register(_manifest(identity="a.one"), _handler)
    registry.register(_manifest(identity="b.two"), _handler)
    assert registry.count() == 2
    identities = [entry.manifest.identity for entry in registry.list()]
    assert identities == ["a.one", "b.two"]
