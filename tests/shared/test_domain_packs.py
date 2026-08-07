"""Tests for domain pack loader (WU6-DOMAIN-PACKS, D-26).

Covers:
- L2 pack loads under its own namespace
- Unknown domain rejected
- Unknown version rejected
- Malformed manifest rejected
- No academic pack exists; academic namespace returns explicit not-registered
- Pack identity fields valid
- Content lists empty with explicit status (H1)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.configuration.domain_packs_loader import (
    DomainPackNotRegisteredError,
    DomainPackNotFoundError,
    DomainPackValidationError,
    domain_exists,
    list_available_packs,
    load_pack,
)

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "domain_packs"


class TestL2PackLoads:
    """L2 pack loads under its own namespace."""

    def test_l2_v010_loads(self):
        manifest = load_pack("l2", "v0.1.0")
        assert manifest["domain"] == "l2"
        assert manifest["version"] == "v0.1.0"

    def test_l2_pack_id_format(self):
        manifest = load_pack("l2", "v0.1.0")
        assert manifest["pack_id"] == "l2-core-v0.1.0"


class TestPackIdentityFields:
    """Pack identity fields are valid."""

    def test_all_identity_fields_present(self):
        manifest = load_pack("l2", "v0.1.0")
        assert "pack_id" in manifest
        assert "domain" in manifest
        assert "version" in manifest
        assert "supported_task_types" in manifest
        assert "dimensions" in manifest
        assert "resource_requirements" in manifest
        assert "availability" in manifest
        assert "content_status" in manifest

    def test_domain_matches_namespace(self):
        manifest = load_pack("l2", "v0.1.0")
        assert manifest["domain"] == "l2"

    def test_version_matches_path(self):
        manifest = load_pack("l2", "v0.1.0")
        assert manifest["version"] == "v0.1.0"

    def test_content_lists_are_lists(self):
        manifest = load_pack("l2", "v0.1.0")
        assert isinstance(manifest["supported_task_types"], list)
        assert isinstance(manifest["dimensions"], list)
        assert isinstance(manifest["resource_requirements"], list)


class TestContentListsEmpty:
    """Content lists empty with explicit status (H1)."""

    def test_task_types_empty(self):
        manifest = load_pack("l2", "v0.1.0")
        assert manifest["supported_task_types"] == []

    def test_dimensions_empty(self):
        manifest = load_pack("l2", "v0.1.0")
        assert manifest["dimensions"] == []

    def test_resource_requirements_empty(self):
        manifest = load_pack("l2", "v0.1.0")
        assert manifest["resource_requirements"] == []

    def test_content_status_has_nr_blocked_notes(self):
        manifest = load_pack("l2", "v0.1.0")
        cs = manifest["content_status"]
        assert "NR" in cs.get("task_types", "") or "blocked" in cs.get("task_types", "")
        assert "NR" in cs.get("dimensions", "") or "blocked" in cs.get("dimensions", "")

    def test_content_status_references_d_l2_01(self):
        manifest = load_pack("l2", "v0.1.0")
        cs = manifest["content_status"]
        assert "D-L2-01" in cs.get("task_types", "") or "D-L2-01" in cs.get("note", "")


class TestUnknownDomainRejected:
    """Unknown domain is rejected."""

    def test_unknown_domain_raises(self):
        with pytest.raises(DomainPackNotFoundError, match="Domain 'nonexistent' not found"):
            load_pack("nonexistent", "v0.1.0")

    def test_domain_exists_false(self):
        assert domain_exists("nonexistent") is False

    def test_domain_exists_true(self):
        assert domain_exists("l2") is True


class TestUnknownVersionRejected:
    """Unknown version is rejected."""

    def test_unknown_version_raises(self):
        with pytest.raises(DomainPackNotFoundError, match="Version 'v9.9.9' not found"):
            load_pack("l2", "v9.9.9")

    def test_invalid_version_format_raises(self):
        with pytest.raises(DomainPackValidationError, match="Version format invalid"):
            load_pack("l2", "bad-format")


class TestMalformedManifestRejected:
    """Malformed manifest is rejected."""

    def test_missing_required_key(self, tmp_path: Path):
        domain_dir = tmp_path / "broken" / "v0.1.0"
        domain_dir.mkdir(parents=True)
        manifest_path = domain_dir / "manifest.json"
        manifest_path.write_text(json.dumps({
            "pack_id": "broken-v0.1.0",
            # missing domain, version, etc.
        }), encoding="utf-8")

        # Monkey-patch the root for this test
        import app.configuration.domain_packs_loader as loader
        original_root = loader._DOMAIN_PACKS_ROOT
        loader._DOMAIN_PACKS_ROOT = tmp_path
        try:
            with pytest.raises(DomainPackValidationError, match="Manifest missing required keys"):
                load_pack("broken", "v0.1.0")
        finally:
            loader._DOMAIN_PACKS_ROOT = original_root

    def test_domain_mismatch(self, tmp_path: Path):
        domain_dir = tmp_path / "mismatch" / "v0.1.0"
        domain_dir.mkdir(parents=True)
        manifest_path = domain_dir / "manifest.json"
        manifest_path.write_text(json.dumps({
            "pack_id": "mismatch-v0.1.0",
            "domain": "wrong",
            "version": "v0.1.0",
            "supported_task_types": [],
            "dimensions": [],
            "resource_requirements": [],
            "availability": "not_available",
            "content_status": {"note": "test"},
        }), encoding="utf-8")

        import app.configuration.domain_packs_loader as loader
        original_root = loader._DOMAIN_PACKS_ROOT
        loader._DOMAIN_PACKS_ROOT = tmp_path
        try:
            with pytest.raises(DomainPackValidationError, match="does not match namespace"):
                load_pack("mismatch", "v0.1.0")
        finally:
            loader._DOMAIN_PACKS_ROOT = original_root

    def test_invalid_json(self, tmp_path: Path):
        domain_dir = tmp_path / "badjson" / "v0.1.0"
        domain_dir.mkdir(parents=True)
        manifest_path = domain_dir / "manifest.json"
        manifest_path.write_text("not json {{{", encoding="utf-8")

        import app.configuration.domain_packs_loader as loader
        original_root = loader._DOMAIN_PACKS_ROOT
        loader._DOMAIN_PACKS_ROOT = tmp_path
        try:
            with pytest.raises(DomainPackValidationError, match="not valid JSON"):
                load_pack("badjson", "v0.1.0")
        finally:
            loader._DOMAIN_PACKS_ROOT = original_root


class TestAcademicNamespace:
    """Academic namespace returns explicit empty/not-registered state."""

    def test_academic_domain_not_registered(self):
        assert domain_exists("academic") is False

    def test_academic_load_raises(self):
        with pytest.raises(DomainPackNotFoundError, match="Domain 'academic' not found"):
            load_pack("academic", "v0.1.0")

    def test_no_academic_pack_exists(self):
        packs = list_available_packs()
        academic_packs = [p for p in packs if p["domain"] == "academic"]
        assert academic_packs == []


class TestListAvailablePacks:
    """list_available_packs returns expected packs."""

    def test_lists_l2_pack(self):
        packs = list_available_packs()
        l2_versions = [p["version"] for p in packs if p["domain"] == "l2"]
        assert "v0.1.0" in l2_versions

    def test_returns_list_of_dicts(self):
        packs = list_available_packs()
        assert isinstance(packs, list)
        for p in packs:
            assert "domain" in p
            assert "version" in p
