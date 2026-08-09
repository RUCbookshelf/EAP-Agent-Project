"""v0.9.5-H2D2 focused tests: API-owned Ports bound to dependency accessors.

Proves that exactly the ten API-owned persistence Ports from v0.9.5-G are now
bound as exact production return annotations on the ten matching
app/api/deps.py accessors, with no broad/concrete/union annotations, no Port
definition change, no accessor body change, no Router or composition change,
structural satisfaction of the assigned facade-owned repositories, unchanged
object identity through both application-construction paths, and exact
OpenAPI/dependency-graph parity.
"""

from __future__ import annotations

import ast
import inspect
import json
import typing
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI

from app.api.deps import (
    get_analysis_runs_reader,
    get_calf_reader,
    get_research_export_writer,
    get_revision_group_lookup,
    get_student_learner_reader,
    get_student_lookup,
    get_student_submission_list,
    get_submission_bundle_reader,
    get_submission_calibration_reader,
    get_system_migration_reader,
)
from app.api.main import _build_full_app, _run_startup
from app.api.ports import (
    AnalysisRunReadPort,
    CalfReadPort,
    ResearchExportWritePort,
    RevisionGroupLookupPort,
    StudentLearnerReadPort,
    StudentLookupPort,
    StudentSubmissionListPort,
    SubmissionBundleReadPort,
    SubmissionCalibrationReadPort,
    SystemMigrationPort,
)
from app.config import Settings
from app.infrastructure.sqlite.repositories.analysis import SQLiteAnalysisRepository
from app.infrastructure.sqlite.repositories.calf import SQLiteCalfRepository
from app.infrastructure.sqlite.repositories.learner import SQLiteLearnerRepository
from app.infrastructure.sqlite.repositories.research import SQLiteResearchRepository
from app.infrastructure.sqlite.repositories.revision import SQLiteRevisionRepository
from app.infrastructure.sqlite.repositories.submission import SQLiteSubmissionRepository
from app.infrastructure.sqlite.repositories.system import SQLiteSystemRepository
from tests.test_v095f2_service_narrowing import _restore_lifecycle, _snapshot_lifecycle


ROOT = Path(__file__).resolve().parents[1]
H2D2 = ROOT / "verification" / "v0.9.5-h2d2"

PORT_ACCESSOR_MAP = {
    "SubmissionBundleReadPort": "get_submission_bundle_reader",
    "StudentLookupPort": "get_student_lookup",
    "AnalysisRunReadPort": "get_analysis_runs_reader",
    "CalfReadPort": "get_calf_reader",
    "ResearchExportWritePort": "get_research_export_writer",
    "StudentSubmissionListPort": "get_student_submission_list",
    "RevisionGroupLookupPort": "get_revision_group_lookup",
    "StudentLearnerReadPort": "get_student_learner_reader",
    "SubmissionCalibrationReadPort": "get_submission_calibration_reader",
    "SystemMigrationPort": "get_system_migration_reader",
}

STATE_ATTRS = {
    "SubmissionBundleReadPort": "submission_bundle_reader",
    "StudentLookupPort": "student_lookup",
    "AnalysisRunReadPort": "analysis_runs_reader",
    "CalfReadPort": "calf_reader",
    "ResearchExportWritePort": "research_export_writer",
    "StudentSubmissionListPort": "student_submission_list",
    "RevisionGroupLookupPort": "revision_group_lookup",
    "StudentLearnerReadPort": "student_learner_reader",
    "SubmissionCalibrationReadPort": "submission_calibration_reader",
    "SystemMigrationPort": "system_migration_reader",
}

CONCRETE_SATISFIER = {
    "SubmissionBundleReadPort": SQLiteSubmissionRepository,
    "StudentLookupPort": SQLiteLearnerRepository,
    "AnalysisRunReadPort": SQLiteAnalysisRepository,
    "CalfReadPort": SQLiteCalfRepository,
    "ResearchExportWritePort": SQLiteResearchRepository,
    "StudentSubmissionListPort": SQLiteSubmissionRepository,
    "RevisionGroupLookupPort": SQLiteRevisionRepository,
    "StudentLearnerReadPort": SQLiteLearnerRepository,
    "SubmissionCalibrationReadPort": SQLiteCalfRepository,
    "SystemMigrationPort": SQLiteSystemRepository,
}

PORT_OBJECTS = {
    "SubmissionBundleReadPort": SubmissionBundleReadPort,
    "StudentLookupPort": StudentLookupPort,
    "AnalysisRunReadPort": AnalysisRunReadPort,
    "CalfReadPort": CalfReadPort,
    "ResearchExportWritePort": ResearchExportWritePort,
    "StudentSubmissionListPort": StudentSubmissionListPort,
    "RevisionGroupLookupPort": RevisionGroupLookupPort,
    "StudentLearnerReadPort": StudentLearnerReadPort,
    "SubmissionCalibrationReadPort": SubmissionCalibrationReadPort,
    "SystemMigrationPort": SystemMigrationPort,
}

ACCESSOR_OBJECTS = {
    "get_submission_bundle_reader": get_submission_bundle_reader,
    "get_student_lookup": get_student_lookup,
    "get_analysis_runs_reader": get_analysis_runs_reader,
    "get_calf_reader": get_calf_reader,
    "get_research_export_writer": get_research_export_writer,
    "get_student_submission_list": get_student_submission_list,
    "get_revision_group_lookup": get_revision_group_lookup,
    "get_student_learner_reader": get_student_learner_reader,
    "get_submission_calibration_reader": get_submission_calibration_reader,
    "get_system_migration_reader": get_system_migration_reader,
}


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))


def _classdefs(path: Path) -> dict[str, ast.ClassDef]:
    return {
        node.name: node
        for node in ast.walk(_parse(path))
        if isinstance(node, ast.ClassDef)
    }


def _funcdefs(path: Path) -> dict[str, ast.FunctionDef]:
    return {
        node.name: node
        for node in ast.walk(_parse(path))
        if isinstance(node, ast.FunctionDef)
    }


def _method_names(cls: ast.ClassDef) -> list[str]:
    return [
        node.name
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def _params(signature: inspect.Signature) -> list[tuple[str, str, object]]:
    return [
        (name, str(parameter.kind), parameter.default)
        for name, parameter in signature.parameters.items()
        if name != "self"
    ]


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "h2d2.db",
        llm_provider="local",
        deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com",
        deepseek_model="deepseek-chat",
    )


def _before_bindings() -> dict:
    return json.loads((H2D2 / "api_port_bindings_before.json").read_text(encoding="utf-8"))


class TestExactBindings:
    def test_exactly_ten_api_owned_ports_in_scope(self):
        classes = _classdefs(ROOT / "app/api/ports.py")
        protocols = {
            name: node for name, node in classes.items()
            if any("Protocol" in ast.unparse(base) for base in node.bases)
        }
        assert set(protocols) == set(PORT_ACCESSOR_MAP)
        assert len(protocols) == 10
        for node in protocols.values():
            assert any("runtime_checkable" in ast.unparse(d) for d in node.decorator_list)

    def test_exactly_ten_accessors_bound_with_exact_annotations(self):
        funcs = _funcdefs(ROOT / "app/api/deps.py")
        bound = {
            name: func for name, func in funcs.items()
            if name in ACCESSOR_OBJECTS
        }
        assert set(bound) == set(ACCESSOR_OBJECTS)
        for port_name, accessor_name in PORT_ACCESSOR_MAP.items():
            annotation = bound[accessor_name].returns
            assert annotation is not None, accessor_name
            assert ast.unparse(annotation) == port_name, accessor_name

    def test_each_port_maps_to_exactly_one_accessor(self):
        assert len(set(PORT_ACCESSOR_MAP)) == 10
        assert len(set(PORT_ACCESSOR_MAP.values())) == 10

    def test_no_broad_or_concrete_annotations(self):
        funcs = _funcdefs(ROOT / "app/api/deps.py")
        for port_name, accessor_name in PORT_ACCESSOR_MAP.items():
            returns = funcs[accessor_name].returns
            assert isinstance(returns, ast.Name), accessor_name
            assert returns.id == port_name, accessor_name

    def test_all_annotations_resolve_at_runtime(self):
        for port_name, accessor_name in PORT_ACCESSOR_MAP.items():
            hints = typing.get_type_hints(ACCESSOR_OBJECTS[accessor_name])
            assert hints["return"] is PORT_OBJECTS[port_name], accessor_name

    def test_every_port_has_a_production_reference(self):
        deps_source = (ROOT / "app/api/deps.py").read_text(encoding="utf-8")
        after = json.loads((H2D2 / "api_port_bindings_after.json").read_text(encoding="utf-8"))
        after_rows = {b["port_name"]: b for b in after["bindings"]}
        for port_name in PORT_ACCESSOR_MAP:
            assert port_name in deps_source, port_name
            assert after_rows[port_name]["current_production_reference_count"] == 2, port_name

    def test_no_port_definition_changed(self):
        before = _before_bindings()
        classes = _classdefs(ROOT / "app/api/ports.py")
        for row in before["bindings"]:
            node = classes[row["port_name"]]
            assert _method_names(node) == [m["name"] for m in row["declared_methods"]], row["port_name"]
            assert node.lineno == row["definition_line"], row["port_name"]

    def test_runtime_checkable_statuses_unchanged(self):
        classes = _classdefs(ROOT / "app/api/ports.py")
        for port_name in PORT_ACCESSOR_MAP:
            assert any(
                "runtime_checkable" in ast.unparse(d)
                for d in classes[port_name].decorator_list
            ), port_name
        runtime_count = 0
        for path in (ROOT / "app").rglob("*.py"):
            rel = path.relative_to(ROOT).as_posix()
            if "__pycache__" in rel or "-冲突-" in rel:
                continue
            for node in ast.walk(_parse(path)):
                if isinstance(node, ast.ClassDef) and any(
                    "runtime_checkable" in ast.unparse(d) for d in node.decorator_list
                ):
                    runtime_count += 1
        # H1 shared-core additions: AncestryFetchProtocol (D-23 resolver),\n        # _DomainTagged, _DictEntry (D-26 registry selection policy).\n        assert runtime_count == 39


class TestFunctionParity:
    def test_accessor_names_params_and_bodies_unchanged(self):
        before = _before_bindings()
        funcs = _funcdefs(ROOT / "app/api/deps.py")
        for row in before["bindings"]:
            node = funcs[row["target_accessor"]]
            params = [a.arg for a in [*node.args.posonlyargs, *node.args.args]]
            assert params == ["request"], row["target_accessor"]
            before_params = [p["name"] for p in row["accessor_parameters"]]
            assert params == before_params, row["target_accessor"]
            wrapper = ast.Module(body=node.body, type_ignores=[])
            import hashlib
            fingerprint = hashlib.sha256(
                ast.dump(wrapper, include_attributes=False).encode("utf-8")
            ).hexdigest()
            assert fingerprint == row["accessor_body_fingerprint"], row["target_accessor"]


class TestStructuralSatisfaction:
    def test_assigned_objects_structurally_satisfy_ports(self):
        for port_name, concrete in CONCRETE_SATISFIER.items():
            port = PORT_OBJECTS[port_name]
            for method in _method_names(_classdefs(ROOT / "app/api/ports.py")[port_name]):
                assert hasattr(concrete, method), (port_name, method)
                assert _params(inspect.signature(getattr(port, method))) == _params(
                    inspect.signature(getattr(concrete, method))
                ), (port_name, method)


class TestObjectIdentity:
    def _assert_binding(self, api: FastAPI) -> None:
        for port_name, accessor_name in PORT_ACCESSOR_MAP.items():
            attribute = STATE_ATTRS[port_name]
            request = SimpleNamespace(app=SimpleNamespace(state=api.state))
            assert ACCESSOR_OBJECTS[accessor_name](request) is getattr(api.state, attribute), (
                port_name, accessor_name,
            )

    def test_build_full_app_identity(self, tmp_path):
        api = _build_full_app(_settings(tmp_path))
        self._assert_binding(api)

    def test_run_startup_identity(self, tmp_path, monkeypatch):
        saved = _snapshot_lifecycle()
        try:
            monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
            monkeypatch.delenv("DATABASE_URL", raising=False)
            monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "startup.db"))
            monkeypatch.setenv("LLM_PROVIDER", "local")
            api = FastAPI()
            _run_startup(api)
            self._assert_binding(api)
        finally:
            _restore_lifecycle(saved)


class TestFastAPIParity:
    def test_openapi_and_dependency_graph_unchanged(self, tmp_path):
        from app.api.main import create_app

        api = create_app(_settings(tmp_path))
        openapi = api.openapi()
        before_openapi = json.loads(
            (H2D2 / "openapi_before.json").read_text(encoding="utf-8")
        )["normalized_openapi"]
        assert openapi == before_openapi

        before_graph = json.loads(
            (H2D2 / "dependency_graph_before.json").read_text(encoding="utf-8")
        )
        routes = []
        for route in api.routes:
            methods = sorted(getattr(route, "methods", []) or [])
            path = getattr(route, "path", None)
            if path and methods:
                for method in methods:
                    routes.append({"method": method, "path": path, "name": getattr(route, "name", None)})
        routes = sorted(routes, key=lambda r: (r["path"], r["method"]))
        assert routes == before_graph["routes"]
        assert len([r for r in routes if r["method"] in ("GET", "POST")]) == 81

        depends_calls = []
        for rpath in sorted((ROOT / "app/api/routers").glob("*.py")):
            tree = _parse(rpath)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Depends":
                    args = [ast.unparse(a) for a in node.args]
                    keywords = {k.arg: ast.unparse(k.value) for k in node.keywords}
                    depends_calls.append({
                        "router": rpath.name,
                        "line": node.lineno,
                        "dependency_function": args[0] if args else None,
                        "use_cache": keywords.get("use_cache"),
                    })
        assert depends_calls == before_graph["depends_calls"]
