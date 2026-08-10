"""Wave-2 Goal A router-assembly tests (F-2 integration-aware refresh).

The ``app/api/routers/wave2.py`` assembly statically imports the sub-routers
(learner_api, revision_api, personalized_api) from
``app/api/routers/wave2_modules/`` with graceful ImportError tolerance, and
``app/api/main.py`` registers the wave2 router with exactly one additive
registration line.

Integration-aware expectations: when the real sub-router modules exist, the
product mounts exactly the intended Wave-2 route surface (18 unique paths /
19 method+path pairs, verified on the merged Wave-2 composition). Absent
modules are tolerated, but the empty-mount state is an implementation detail,
not a contract -- stale empty-mount assertions are deliberately removed.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
import types

import pytest
from fastapi import APIRouter

from app.api.main import _BUSINESS_ROUTERS
from app.api.routers import wave2 as wave2_module
from app.api.routers import wave2_modules

SUBROUTER_NAMES = ("learner_api", "revision_api", "personalized_api")

# Exact Wave-2 route surface as mounted by the merged composition
# (verified from the real learner/revision/personalized sub-routers):
# 18 unique paths, 19 (method, path) pairs.
REAL_WAVE2_ROUTE_TABLE: dict[str, list[tuple[str, str]]] = {
    "revision_api": [
        ("POST", "/api/v1/wave2/revision/tasks"),
        ("GET", "/api/v1/wave2/revision/tasks/{task_id}"),
        ("POST", "/api/v1/wave2/revision/tasks/{task_id}/submissions"),
        (
            "POST",
            "/api/v1/wave2/revision/tasks/{task_id}/submissions/"
            "{submission_id}/revisions",
        ),
        ("GET", "/api/v1/wave2/revision/tasks/{task_id}/versions"),
        (
            "GET",
            "/api/v1/wave2/revision/tasks/{task_id}/versions/"
            "{submission_id}/observation",
        ),
        ("POST", "/api/v1/wave2/revision/submissions/{submission_id}/reanalysis"),
    ],
    "personalized_api": [
        ("POST", "/api/v1/wave2/personalized/priority-plan"),
        ("POST", "/api/v1/wave2/personalized/scaffold"),
        ("GET", "/api/v1/wave2/personalized/learning-items"),
        ("POST", "/api/v1/wave2/personalized/learning-items"),
        ("PATCH", "/api/v1/wave2/personalized/learning-items/{learning_item_id}"),
    ],
    "learner_api": [
        ("GET", "/api/v1/wave2/learner/observations"),
        ("GET", "/api/v1/wave2/learner/observations/{observation_id}"),
        ("GET", "/api/v1/wave2/learner/difficulties"),
        ("GET", "/api/v1/wave2/learner/strengths"),
        ("GET", "/api/v1/wave2/learner/stable"),
        ("GET", "/api/v1/wave2/learner/proficiency-context"),
        ("GET", "/api/v1/wave2/learner/evidence"),
    ],
}

REAL_WAVE2_PAIRS = frozenset(
    pair for pairs in REAL_WAVE2_ROUTE_TABLE.values() for pair in pairs
)
REAL_WAVE2_PATHS = frozenset(path for _, path in REAL_WAVE2_PAIRS)

assert len(REAL_WAVE2_PAIRS) == 19, "merged Wave-2 route surface changed"
assert len(REAL_WAVE2_PATHS) == 18, "merged Wave-2 route surface changed"


def _real_modules_present() -> bool:
    return all(
        importlib.util.find_spec(
            f"app.api.routers.wave2_modules.{name}"
        ) is not None
        for name in SUBROUTER_NAMES
    )


def _fake_subrouter(name: str) -> types.ModuleType:
    """Fake module mirroring the real sub-router's exact route table."""
    module = types.ModuleType(f"app.api.routers.wave2_modules.{name}")
    router = APIRouter()

    def _endpoint():
        return {"module": name}

    for method, path in REAL_WAVE2_ROUTE_TABLE[name]:
        router.add_api_route(path, _endpoint, methods=[method])
    module.router = router
    return module


def _mounted_pairs() -> set[tuple[str, str]]:
    pairs = set()
    for route in wave2_module.router.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if path is None or methods is None:
            continue
        for method in methods:
            if method not in {"HEAD", "OPTIONS"}:
                pairs.add((method, path))
    return pairs


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
    # Self-consistency, not an empty-mount contract: whatever the assembly
    # currently mounts must stay inside the intended Wave-2 route surface.
    assert _mounted_pairs() <= REAL_WAVE2_PAIRS


def _expected_pairs(fakes: dict[str, types.ModuleType]) -> frozenset[tuple[str, str]]:
    """Surface the assembly must mount after ``_inject(fakes)``: the fakes'
    routes plus any real sub-router modules that are importable on this tree
    (in the merged composition the real modules exist alongside fakes)."""
    expected = set()
    for name in SUBROUTER_NAMES:
        if name in fakes or importlib.util.find_spec(
            f"app.api.routers.wave2_modules.{name}"
        ) is not None:
            expected.update(REAL_WAVE2_ROUTE_TABLE[name])
    return frozenset(expected)


def test_assembly_mounts_only_the_intended_wave2_route_surface():
    # Replaces the stale empty-mount assertion: absent sub-router modules are
    # tolerated (no ImportError), and anything mounted stays within the
    # intended Wave-2 route surface (in this branch that is the empty set).
    assert wave2_module.router is not None
    assert _mounted_pairs() <= REAL_WAVE2_PAIRS


def test_assembly_mounts_each_present_subrouter_with_real_route_surface():
    fakes = {name: _fake_subrouter(name) for name in SUBROUTER_NAMES}
    try:
        _inject(fakes)
        assert _mounted_pairs() == REAL_WAVE2_PAIRS
        assert _mounted_paths() == REAL_WAVE2_PATHS
    finally:
        _restore(fakes)


def test_assembly_tolerates_partial_submodule_presence():
    fakes = {"revision_api": _fake_subrouter("revision_api")}
    try:
        _inject(fakes)
        assert _mounted_pairs() == _expected_pairs(fakes)
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
        assert REAL_WAVE2_PATHS <= paths
    finally:
        _restore(fakes)


@pytest.mark.skipif(
    not _real_modules_present(),
    reason="real wave2 sub-router modules are not contributed on this branch",
)
def test_real_subrouter_modules_mount_the_full_wave2_surface():
    """Integration contract: with the real sub-routers present, the product
    mounts exactly the intended Wave-2 route surface."""
    assert _mounted_pairs() == REAL_WAVE2_PAIRS
    assert _mounted_paths() == REAL_WAVE2_PATHS
