"""INT-owned wave2 sub-router surface pin (PDW3-WU5 re-gate 20260812).

This pin is maintained by INT and reflects the COMPOSED Wave-3 surface:
the Wave-2 sub-router assembly now mounts 27 (method, path) pairs across
26 unique paths (19 pairs / 18 paths at the promoted Wave-2 master plus
the EXACT +8 authorized L2 WU3 delta). The delta was proven route-by-route
by the re-gate ENUMERATE -> COMPARE -> CLASSIFY -> QUALIFY audit
(verification/pdw3-wu5-int-consolidated-wave3-integration-gate/
re-gate-20260812/wave2_assembly_pin_delta_facts_RE-GATE.json): the eight
added pairs are precisely the adaptive-practice (evaluate/recommend/
select), mini-writing, and tutor (accept/decline/observation/recommend)
POST routes; zero unexpected additions and zero removals.

The ``app/api/routers/wave2.py`` assembly statically imports the
sub-routers (learner_api, revision_api, personalized_api) from
``app/api/routers/wave2_modules/`` with graceful ImportError tolerance, and
``app/api/main.py`` registers the wave2 router with exactly one additive
registration line.

Integration-aware expectations: when the real sub-router modules exist, the
product mounts exactly the intended Wave-2 + Wave-3 route surface (27
method+path pairs / 26 unique paths, verified on the composed re-gate
preview). Absent modules are tolerated, but the empty-mount state is an
implementation detail, not a contract -- stale empty-mount assertions are
deliberately removed.
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

# Exact composed Wave-2 + Wave-3 route surface as mounted by the composed
# product (verified from the real learner/revision/personalized sub-routers
# in the re-gate preview): 26 unique paths, 27 (method, path) pairs.
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
        ("POST", "/api/v1/wave2/personalized/adaptive-practice/evaluate"),
        ("POST", "/api/v1/wave2/personalized/adaptive-practice/recommend"),
        ("POST", "/api/v1/wave2/personalized/adaptive-practice/select"),
        ("POST", "/api/v1/wave2/personalized/mini-writing"),
        ("POST", "/api/v1/wave2/personalized/tutor/accept"),
        ("POST", "/api/v1/wave2/personalized/tutor/decline"),
        ("POST", "/api/v1/wave2/personalized/tutor/observation"),
        ("POST", "/api/v1/wave2/personalized/tutor/recommend"),
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

assert len(REAL_WAVE2_PAIRS) == 27, "composed Wave-2/Wave-3 surface changed"
assert len(REAL_WAVE2_PATHS) == 26, "composed Wave-2/Wave-3 surface changed"


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
    # currently mounts must stay inside the intended composed surface.
    assert _mounted_pairs() <= REAL_WAVE2_PAIRS


def _expected_pairs(fakes: dict[str, types.ModuleType]) -> frozenset[tuple[str, str]]:
    """Surface the assembly must mount after ``_inject(fakes)``: the fakes'
    routes plus any real sub-router modules that are importable on this tree
    (in the composed product the real modules exist alongside fakes)."""
    expected = set()
    for name in SUBROUTER_NAMES:
        if name in fakes or importlib.util.find_spec(
            f"app.api.routers.wave2_modules.{name}"
        ) is not None:
            expected.update(REAL_WAVE2_ROUTE_TABLE[name])
    return frozenset(expected)


def test_assembly_mounts_only_the_intended_wave2_route_surface():
    # Absent sub-router modules are tolerated (no ImportError), and anything
    # mounted stays within the intended composed Wave-2/Wave-3 surface.
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
    mounts exactly the intended composed Wave-2/Wave-3 route surface."""
    assert _mounted_pairs() == REAL_WAVE2_PAIRS
    assert _mounted_paths() == REAL_WAVE2_PATHS
