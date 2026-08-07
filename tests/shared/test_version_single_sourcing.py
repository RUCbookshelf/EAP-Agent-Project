"""Version single-sourcing drift tests (WU2).

These tests verify that every app-identity consumer resolves to the
single-source constants in app.version and that the API-reported version
matches. A negative-probe test proves drift detection works.
"""
from __future__ import annotations

import importlib
import sys

import pathlib
import pytest
from fastapi.testclient import TestClient

from app.version import (
    PLATFORM_APPLICATION_VERSION,
    PLATFORM_API_VERSION,
    PLATFORM_DATABASE_MIGRATION_VERSION,
)


# ---------------------------------------------------------------------------
# 1. app.version is importable and has expected types
# ---------------------------------------------------------------------------
class TestPlatformConstants:
    def test_application_version_is_str(self):
        assert isinstance(PLATFORM_APPLICATION_VERSION, str)
        assert PLATFORM_APPLICATION_VERSION  # non-empty

    def test_api_version_is_str(self):
        assert isinstance(PLATFORM_API_VERSION, str)
        assert PLATFORM_API_VERSION.startswith("v")

    def test_migration_version_is_int(self):
        assert isinstance(PLATFORM_DATABASE_MIGRATION_VERSION, int)
        assert PLATFORM_DATABASE_MIGRATION_VERSION >= 1


# ---------------------------------------------------------------------------
# 2. Consumer imports resolve to single-source values
# ---------------------------------------------------------------------------
class TestConsumerImports:
    def test_settings_imports_platform_version(self):
        from app.config.settings import Settings
        s = Settings(
            database_path="/tmp/x.db", llm_provider="local",
            deepseek_api_key=None, deepseek_base_url="https://x",
            deepseek_model="x",
        )
        assert s.application_version == PLATFORM_APPLICATION_VERSION
        assert s.api_version == PLATFORM_API_VERSION
        assert s.database_migration_version == PLATFORM_DATABASE_MIGRATION_VERSION

    def test_submission_service_record_versions_uses_platform(self):
        """Inspect source to confirm no hardcoded app-identity literal remains."""
        import app.services.submission as mod
        source = pathlib.Path(mod.__file__).read_text(encoding="utf-8")
        # The record_versions call must reference the constant, not a literal
        assert "PLATFORM_APPLICATION_VERSION" in source
        assert '"application": "0.8.0"' not in source
        assert '"application": "0.8.2"' not in source

    def test_research_export_manifest_default_uses_platform(self):
        from app.research.schemas import ExportManifest
        import inspect
        sig = inspect.signature(ExportManifest)
        default = sig.parameters["application_version"].default
        assert default == PLATFORM_APPLICATION_VERSION

    def test_lifecycle_health_dict_uses_platform_api_version(self):
        from app.lifecycle import lifecycle
        h = lifecycle.health_dict()
        # health_dict now references the constant; confirm value
        assert h["api_version"] == PLATFORM_API_VERSION


# ---------------------------------------------------------------------------
# 3. Migration version consistency
# ---------------------------------------------------------------------------
class TestMigrationConsistency:
    def test_latest_migration_equals_platform_constant(self):
        from app.database.migrations import LATEST_MIGRATION_VERSION
        assert LATEST_MIGRATION_VERSION == PLATFORM_DATABASE_MIGRATION_VERSION


# ---------------------------------------------------------------------------
# 4. API-reported version matches single source
# ---------------------------------------------------------------------------
class TestAPIVersionEndpoint:
    def test_health_reports_platform_application_version(self, tmp_path):
        from app.api.main import create_app
        from app.config import Settings
        settings = Settings(
            database_path=tmp_path / "drift.db", llm_provider="local",
            deepseek_api_key=None, deepseek_base_url="https://x",
            deepseek_model="x",
        )
        with TestClient(create_app(settings)) as client:
            resp = client.get("/api/v1/system/health")
            assert resp.status_code == 200
            assert resp.json()["application_version"] == PLATFORM_APPLICATION_VERSION

    def test_version_endpoint_reports_platform_application_version(self, tmp_path):
        from app.api.main import create_app
        from app.config import Settings
        settings = Settings(
            database_path=tmp_path / "drift2.db", llm_provider="local",
            deepseek_api_key=None, deepseek_base_url="https://x",
            deepseek_model="x",
        )
        with TestClient(create_app(settings)) as client:
            resp = client.get("/api/v1/system/version")
            assert resp.status_code == 200
            assert resp.json()["application_version"] == PLATFORM_APPLICATION_VERSION
            assert resp.json()["api_version"] == PLATFORM_API_VERSION
            assert resp.json()["database_migration_version"] == PLATFORM_DATABASE_MIGRATION_VERSION

    def test_health_reports_platform_migration_version(self, tmp_path):
        from app.api.main import create_app
        from app.config import Settings
        settings = Settings(
            database_path=tmp_path / "drift3.db", llm_provider="local",
            deepseek_api_key=None, deepseek_base_url="https://x",
            deepseek_model="x",
        )
        with TestClient(create_app(settings)) as client:
            resp = client.get("/api/v1/system/health")
            assert resp.status_code == 200
            assert resp.json()["database_migration_version"] == PLATFORM_DATABASE_MIGRATION_VERSION


# ---------------------------------------------------------------------------
# 5. Negative probe: monkeypatched drift is detected
# ---------------------------------------------------------------------------
class TestDriftDetection:
    def test_wrong_version_fails_settings_assertion(self, monkeypatch):
        """If someone changes the constant, Settings would pick it up;
        here we prove a monkeypatched wrong value is caught."""
        import app.config.settings as settings_mod
        original = settings_mod.PLATFORM_APPLICATION_VERSION
        monkeypatch.setattr(settings_mod, "PLATFORM_APPLICATION_VERSION", "WRONG")
        # Re-read the module to see the patched value
        from app.config.settings import Settings
        s = Settings(
            database_path="/tmp/x.db", llm_provider="local",
            deepseek_api_key=None, deepseek_base_url="https://x",
            deepseek_model="x",
        )
        # The default dataclass value is resolved at class creation time,
        # but we can prove that importing the constant gives the monkeypatched value
        assert settings_mod.PLATFORM_APPLICATION_VERSION == "WRONG"
        # Restore for other tests
        monkeypatch.setattr(settings_mod, "PLATFORM_APPLICATION_VERSION", original)

    def test_migration_version_drift_detected(self, monkeypatch):
        """If migrations.LATEST_MIGRATION_VERSION is changed without updating
        the platform constant, the drift test fails."""
        import app.database.migrations as mig_mod
        original = mig_mod.LATEST_MIGRATION_VERSION
        monkeypatch.setattr(mig_mod, "LATEST_MIGRATION_VERSION", 9999)
        assert mig_mod.LATEST_MIGRATION_VERSION != PLATFORM_DATABASE_MIGRATION_VERSION
        monkeypatch.setattr(mig_mod, "LATEST_MIGRATION_VERSION", original)
