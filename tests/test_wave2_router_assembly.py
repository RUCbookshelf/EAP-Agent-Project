"""Wave-2 Goal A router-assembly tests.

The ``app/api/routers/wave2.py`` assembly statically imports the future
sub-routers (learner_api, revision_api, personalized_api) from
``app/api/routers/wave2_modules/`` with graceful ImportError tolerance, and
``app/api/main.py`` registers the wave2 router with exactly one additive
registration line.
"""

from __future__ import annotations

import importlib
import sys
import types

from fastapi import APIRouter

from app.api.main import _BUSINESS_ROUTERS
from app.api.routers import wave2 as wave2_module
from app.api.routers import wave2_modules

SUBROUTER_NAMES = ("learner_api", "revision_api", "personalized_api")


def _fake_subrouter(name: str) -> types.ModuleType:
    module = types.ModuleType(f"app.api.routers.wave2_modules.{name}")
    router = APIRouter()

    def _endpoint():
        return {"module": name}

    router.add_api_route(f"/api/v1/wave2/{name}/probe", _endpoint, methods=["GET"])
    module.router = router
    return module


def _mounted_paths() -> set[str]:
    return {
        getattr(route, "path", None)
        for route in wave2_module.router.routes
        if getattr(route, "path", None)
    }


def _inject(fakes: dict[str, types.ModuleType]) -> None:
    for name, module in fakes.items():
        sys.modules[f"app.api.routers.wave2_modules.{name}"] = module
        setattr(wave2_modules, name, module)
    importlib.reload(wave2_module)


def _restore(fakes: dict[str, types.ModuleType]) -> None:
    for name in fakes:
        sys.modules.pop(f"app.api.routers.wave2_modules.{name}", None)
        delattr(wave2_modules, name)
    importlib.reload(wave2_module)
    assert _mounted_paths() == set()


def test_assembly_imports_without_submodules_and_mounts_nothing():
    # Absent sub-router modules must be tolerated: no ImportError, empty mount.
    assert wave2_module.router is not None
    assert _mounted_paths() == set()


def test_assembly_mounts_each_present_subrouter():
    fakes = {name: _fake_subrouter(name) for name in SUBROUTER_NAMES}
    try:
        _inject(fakes)
        assert _mounted_paths() == {
            f"/api/v1/wave2/{name}/probe" for name in SUBROUTER_NAMES
        }
    finally:
        _restore(fakes)


def test_assembly_tolerates_partial_submodule_presence():
    fakes = {"revision_api": _fake_subrouter("revision_api")}
    try:
        _inject(fakes)
        assert _mounted_paths() == {"/api/v1/wave2/revision_api/probe"}
    finally:
        _restore(fakes)


def test_main_registers_wave2_router_exactly_once():
    registrations = [
        module for module in _BUSINESS_ROUTERS if module is wave2_module
    ]
    assert registrations == [wave2_module]


def test_full_app_builds_and_mounts_wave2_routes_when_submodules_present(tmp_path):
    from app.api.main import create_app
    from app.config import Settings

    fakes = {name: _fake_subrouter(name) for name in SUBROUTER_NAMES}
    try:
        _inject(fakes)
        settings = Settings(
            database_path=tmp_path / "wave2-api.db",
            llm_provider="local",
            deepseek_api_key=None,
            deepseek_base_url="https://example.invalid",
            deepseek_model="deepseek-test",
        )
        app = create_app(settings)
        paths = {getattr(route, "path", None) for route in app.routes}
        assert {
            f"/api/v1/wave2/{name}/probe" for name in SUBROUTER_NAMES
        } <= paths
    finally:
        _restore(fakes)

