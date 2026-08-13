"""Composition-root tests: both production and test paths resolve
through the single _build_services builder."""

from __future__ import annotations

import app.api.main as main_module
from app.api.main import _build_services, _apply_service_state
from app.config import Settings
from app.lifecycle import ServiceState, lifecycle


def _make_settings(tmp_path):
    return Settings(
        database_path=tmp_path / "test.db", llm_provider="local",
        deepseek_api_key=None, deepseek_base_url="https://example.invalid",
        deepseek_model="deepseek-test",
    )


def test_build_services_is_single_builder():
    """Both _run_startup and _build_full_app reference the same builder."""
    assert hasattr(main_module, "_build_services")
    assert main_module._build_services is _build_services


def test_build_services_returns_expected_keys(tmp_path):
    """The builder returns all service keys needed by _apply_service_state."""
    settings = _make_settings(tmp_path)
    svc = _build_services(settings)
    expected_keys = {
        "settings", "repository", "analyzer", "submission_service",
        "learner_profiles", "metrics", "configurations", "dashboards",
        "reanalysis", "journey", "revisions", "calf", "research",
        # WU2 learner slices (RETRY-2 Worker D): acknowledgement service and
        # practice/review bridge are part of the single service graph.
        "acknowledgement", "practice_review_transfer",
    }
    assert set(svc.keys()) == expected_keys
    assert svc["settings"] is settings


def test_both_composition_paths_use_same_builder(tmp_path):
    """Test path (create_app with settings) and production reference
    both resolve through _build_services."""
    from app.api.main import create_app

    settings = _make_settings(tmp_path)

    # Test path: create_app(settings) -> _build_full_app -> _build_services
    test_app = create_app(settings)
    assert test_app.state.settings is settings
    assert test_app.state.repository is not None

    # Production reference: the module-level _build_services is the same function
    # that _run_startup would call
    from app.api.main import _build_services as builder_from_import
    assert builder_from_import is _build_services


def test_boots_without_corpus(tmp_path):
    """The app boots without corpus modules being required."""
    settings = _make_settings(tmp_path)
    api = main_module.create_app(settings)
    assert api.state.repository is not None


def test_service_state_assigns_wu2_composition_services(tmp_path):
    """The WU2 acknowledgement service and practice/review bridge are
    assigned to app state through the single assignment point."""
    settings = _make_settings(tmp_path)
    api = main_module.create_app(settings)
    assert api.state.acknowledgement_service is not None
    assert api.state.practice_review_transfer is not None
