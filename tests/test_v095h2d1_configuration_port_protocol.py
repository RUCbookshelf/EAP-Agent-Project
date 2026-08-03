"""v0.9.5-H2D1 focused tests: ConfigurationPort formalized as typing.Protocol.

Proves the active ConfigurationPort contract in app/services/configuration.py
was converted from a plain structural class to a structural typing.Protocol
with its exact seven-method contract preserved, that it is not
@runtime_checkable, that no alias/instantiation/subclass/runtime-check path
depends on the ordinary-class identity, that ConfigurationService still
resolves its collaborator annotation to ConfigurationPort, that
SQLiteConfigurationRepository structurally satisfies the Protocol without
explicit inheritance, that no other contract changed representation, and
that configuration runtime behavior and application composition are
unchanged (same facade-owned Repository instance).
"""

from __future__ import annotations

import ast
import inspect
import json
import re
import typing
from pathlib import Path

import pytest

from app.analysis import AnalyzerRegistry, default_metric_registry
from app.analyzer import BasicAnalyzer
from app.api.main import _build_full_app
from app.config import Settings
from app.configuration import ConfigurationCreate, ConfigurationPayload
from app.database import Database
from app.infrastructure.sqlite.repositories.configuration import SQLiteConfigurationRepository
from app.services.configuration import ConfigurationPort, ConfigurationService


ROOT = Path(__file__).resolve().parents[1]
BEFORE = ROOT / "verification" / "v0.9.5-h2d1" / "configuration_port_before.json"
H1_INVENTORY = ROOT / "verification" / "v0.9.5-h1" / "protocol_inventory.json"

CONFIG_REL = "app/services/configuration.py"
EXPECTED_METHODS = [
    "list_configurations",
    "get_configuration",
    "get_active_configuration",
    "create_configuration",
    "set_configuration_validation",
    "activate_configuration",
    "list_configuration_audit",
]


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))


def _classdefs(path: Path) -> dict[str, ast.ClassDef]:
    return {
        node.name: node
        for node in ast.walk(_parse(path))
        if isinstance(node, ast.ClassDef)
    }


def _method_names(classdef: ast.ClassDef) -> list[str]:
    return [
        node.name
        for node in classdef.body
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
        database_path=tmp_path / "h2d1.db",
        llm_provider="local",
        deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com",
        deepseek_model="deepseek-chat",
    )


# ---------------------------------------------------------------------------
# Layer 2 - Contract representation
# ---------------------------------------------------------------------------

class TestProtocolRepresentation:
    def test_configuration_port_is_a_structural_protocol(self):
        assert isinstance(ConfigurationPort, type)
        assert issubclass(ConfigurationPort, typing.Protocol)
        assert ConfigurationPort.__module__ == "app.services.configuration"

    def test_configuration_port_is_not_runtime_checkable(self):
        assert getattr(ConfigurationPort, "_is_runtime_protocol", False) is False
        with pytest.raises(TypeError):
            ConfigurationPort()

    def test_exactly_one_definition_in_the_same_module(self):
        definitions = []
        for path in (ROOT / "app").rglob("*.py"):
            rel = path.relative_to(ROOT).as_posix()
            if "__pycache__" in rel or "-冲突-" in rel:
                continue
            for name, node in _classdefs(path).items():
                if name == "ConfigurationPort":
                    definitions.append((rel, node.lineno))
        assert len(definitions) == 1
        assert definitions[0][0] == CONFIG_REL

    def test_no_compatibility_alias(self):
        for path in (ROOT / "app").rglob("*.py"):
            rel = path.relative_to(ROOT).as_posix()
            if "__pycache__" in rel or "-冲突-" in rel:
                continue
            for i, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
                assert not re.search(r"^\s*_?ConfigurationPort\s*=\s*", line), (rel, i, line)

    def test_no_instantiation_subclass_or_runtime_check_in_production(self):
        for path in (ROOT / "app").rglob("*.py"):
            rel = path.relative_to(ROOT).as_posix()
            if "__pycache__" in rel or "-冲突-" in rel:
                continue
            tree = _parse(path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "ConfigurationPort":
                    pytest.fail(f"instantiation at {rel}:{node.lineno}")
                if isinstance(node, ast.ClassDef) and any(
                    isinstance(base, ast.Name) and base.id == "ConfigurationPort"
                    for base in node.bases
                ):
                    pytest.fail(f"subclass at {rel}:{node.lineno}")
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("isinstance", "issubclass"):
                    if any(re.search(r"\bConfigurationPort\b", ast.unparse(arg)) for arg in node.args):
                        pytest.fail(f"runtime check at {rel}:{node.lineno}")

    def test_no_other_contract_changed_representation(self):
        inv = json.loads(H1_INVENTORY.read_text(encoding="utf-8"))
        for contract in [c for c in inv["contracts"] if c["classification"] in ("A", "B", "C")]:
            name = contract["contract_name"]
            module = contract["module"]
            if name == "_AnalysisRunReader":
                continue  # canonicalized by H2C; checked by its own test
            if name == "ConfigurationRepository":
                # H2D1's approved change: plain class -> Protocol (same module/name).
                classes = _classdefs(ROOT / CONFIG_REL)
                assert "ConfigurationPort" in classes
                assert [ast.unparse(b) for b in classes["ConfigurationPort"].bases] == ["Protocol"]
                assert [ast.unparse(d) for d in classes["ConfigurationPort"].decorator_list] == []
                continue
            if contract["contract_kind"] == "alias":
                continue
            classes = _classdefs(ROOT / (module.replace(".", "/") + ".py"))
            node = classes[name]
            assert [ast.unparse(b) for b in node.bases] == contract["base_classes"], name
            assert (
                any("runtime_checkable" in ast.unparse(d) for d in node.decorator_list)
                == contract["runtime_checkable"]
            ), name


# ---------------------------------------------------------------------------
# Layer 3 - Signature parity
# ---------------------------------------------------------------------------

class TestSignatureParity:
    def test_seven_methods_and_signatures_match_before_state(self):
        before = json.loads(BEFORE.read_text(encoding="utf-8"))
        before_methods = before["definition"]["methods"]
        assert [m["name"] for m in before_methods] == EXPECTED_METHODS
        classes = _classdefs(ROOT / CONFIG_REL)
        current = _method_names(classes["ConfigurationPort"])
        assert current == EXPECTED_METHODS
        for expected in before_methods:
            signature = inspect.signature(getattr(ConfigurationPort, expected["name"]))
            actual_params = _params(signature)
            expected_params = []
            for p in expected["params"]:
                if p["name"] == "self":
                    continue
                kind = "KEYWORD_ONLY" if p["kind"] == "kwonly" else "POSITIONAL_OR_KEYWORD"
                if p["has_default"]:
                    default = ast.literal_eval(p["default"])
                else:
                    default = inspect.Parameter.empty
                expected_params.append((p["name"], kind, default))
            assert actual_params == expected_params, expected["name"]

    def test_configuration_service_annotation_resolves_to_configuration_port(self):
        init = ConfigurationService.__init__
        assert init.__annotations__["repository"] == "ConfigurationPort"
        resolved = typing.get_type_hints(init)
        assert resolved["repository"] is ConfigurationPort
        assert list(inspect.signature(init).parameters) == [
            "self", "repository", "analyzers", "metrics",
        ]
        assert inspect.signature(init).parameters["repository"].default is inspect.Parameter.empty

    def test_no_service_executable_statement_changed(self):
        init = inspect.signature(ConfigurationService.__init__)
        assert init.parameters["repository"].default is inspect.Parameter.empty
        service_methods = [
            name for name in _method_names(_classdefs(ROOT / CONFIG_REL)["ConfigurationService"])
            if not name.startswith("_")
        ]
        assert service_methods == [
            "list", "active", "create", "validate", "activate", "rollback", "audit", "registries",
        ]


# ---------------------------------------------------------------------------
# Layer 4 - Structural satisfaction
# ---------------------------------------------------------------------------

class TestStructuralSatisfaction:
    def test_sqlite_configuration_repository_structurally_satisfies_protocol(self):
        for method in EXPECTED_METHODS:
            stub = inspect.signature(getattr(ConfigurationPort, method))
            impl = inspect.signature(getattr(SQLiteConfigurationRepository, method))
            assert _params(stub) == _params(impl), method

    def test_concrete_repository_does_not_explicitly_inherit_protocol(self):
        assert ConfigurationPort not in SQLiteConfigurationRepository.__bases__
        repo_path = ROOT / "app/infrastructure/sqlite/repositories/configuration.py"
        node = _classdefs(repo_path)["SQLiteConfigurationRepository"]
        assert not any(
            isinstance(base, ast.Name) and base.id == "ConfigurationPort"
            for base in node.bases
        )


# ---------------------------------------------------------------------------
# Layer 5 - Runtime behavior (isolated database)
# ---------------------------------------------------------------------------

class TestRuntimeBehavior:
    def test_configuration_service_runtime_flows_unchanged(self, tmp_path):
        database = Database(tmp_path / "h2d1-cfg.db")
        database.initialize()
        extracted = database._configuration_repository
        service = ConfigurationService(
            extracted, AnalyzerRegistry([BasicAnalyzer()]), default_metric_registry(),
        )
        assert service.repository is database._configuration_repository
        assert isinstance(extracted, SQLiteConfigurationRepository)
        assert service.list()
        assert service.active().version == "config-v0.9.0"

        created = service.create(ConfigurationCreate(
            payload=ConfigurationPayload(active_analyzer="basic", mattr_window=65),
            change_note="H2D1 contract test.",
        ))
        assert created.status == "draft" and created.parent_version == "config-v0.9.0"

        validated = service.validate(created.configuration_id, actor="local_researcher")
        assert validated.validation_status == "passed" and validated.status == "validated"

        activated = service.activate(created.configuration_id, actor="local_researcher", reason="H2D1 test.")
        assert activated.status == "active"
        assert sum(item.status == "active" for item in service.list()) == 1
        assert service.active().configuration_id == created.configuration_id

        actions = [item["action"] for item in service.audit()]
        assert {"create", "validate", "activate"} <= set(actions)

    def test_application_construction_passes_the_same_facade_owned_repository(self, tmp_path):
        app = _build_full_app(_settings(tmp_path))
        repository = app.state.repository
        assert isinstance(repository, Database)
        assert app.state.configurations.repository is repository._configuration_repository
        assert isinstance(app.state.configurations.repository, SQLiteConfigurationRepository)
