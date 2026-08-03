"""v0.9.5-H2B focused tests: active configuration contract renamed
ConfigurationRepository -> ConfigurationPort.

Proves: the old active-contract name is absent from production source; the new
consumer-owned ConfigurationPort exists with exactly the seven preserved
methods; ConfigurationService is annotated against it; the concrete
SQLiteConfigurationRepository still satisfies it (method + parameter parity);
no duplicate contract name or compatibility alias exists; and the
create/validate/activate runtime flow is unchanged on an isolated database.
"""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

from app.analysis import AnalyzerRegistry, default_metric_registry
from app.analyzer import BasicAnalyzer
from app.configuration import ConfigurationCreate, ConfigurationPayload
from app.database import Database
from app.infrastructure.sqlite.repositories.configuration import SQLiteConfigurationRepository
from app.services.configuration import ConfigurationPort, ConfigurationService

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_METHODS = [
    "list_configurations",
    "get_configuration",
    "get_active_configuration",
    "create_configuration",
    "set_configuration_validation",
    "activate_configuration",
    "list_configuration_audit",
]


def _classdefs(path: Path) -> dict[str, ast.ClassDef]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    return {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
    }


def _method_names(classdef: ast.ClassDef) -> list[str]:
    return [
        node.name
        for node in classdef.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def test_old_name_absent_from_production_source():
    for path in (ROOT / "app").rglob("*.py"):
        rel = path.relative_to(ROOT).as_posix()
        if "__pycache__" in rel or "-冲突-" in rel:
            continue
        source = path.read_text(encoding="utf-8-sig")
        assert not re.search(r"\bConfigurationRepository\b", source), path


def test_new_contract_exists_with_exact_seven_methods():
    classes = _classdefs(ROOT / "app/services/configuration.py")
    assert "ConfigurationPort" in classes
    assert _method_names(classes["ConfigurationPort"]) == EXPECTED_METHODS


def test_service_constructor_annotated_against_new_contract_only():
    signature = inspect.signature(ConfigurationService.__init__)
    annotation = str(signature.parameters["repository"].annotation)
    assert "ConfigurationPort" in annotation
    assert "ConfigurationRepository" not in annotation


def test_no_duplicate_contract_name_or_compatibility_alias():
    for path in (ROOT / "app").rglob("*.py"):
        rel = path.relative_to(ROOT).as_posix()
        if "__pycache__" in rel or "-冲突-" in rel:
            continue
        rel = path.relative_to(ROOT).as_posix()
        classes = _classdefs(path)
        if rel == "app/services/configuration.py":
            assert classes.get("ConfigurationPort") is not None
        else:
            assert "ConfigurationPort" not in classes, path
        assert "ConfigurationRepository" not in classes, path
    assert ConfigurationPort.__name__ == "ConfigurationPort"


def test_concrete_repository_satisfies_renamed_contract():
    assert set(EXPECTED_METHODS) <= set(dir(SQLiteConfigurationRepository))
    for method in EXPECTED_METHODS:
        stub_params = list(inspect.signature(getattr(ConfigurationPort, method)).parameters)
        impl_params = list(inspect.signature(getattr(SQLiteConfigurationRepository, method)).parameters)
        assert stub_params == impl_params, (method, stub_params, impl_params)


def test_configuration_service_runtime_flows_unchanged(tmp_path):
    repository = Database(tmp_path / "h2b-cfg.db")
    repository.initialize()
    extracted = repository._configuration_repository
    service = ConfigurationService(
        extracted, AnalyzerRegistry([BasicAnalyzer()]), default_metric_registry(),
    )
    assert isinstance(extracted, SQLiteConfigurationRepository)
    assert service.list()
    assert service.active().version == "config-v0.9.0"

    created = service.create(ConfigurationCreate(
        payload=ConfigurationPayload(active_analyzer="basic", mattr_window=65),
        change_note="H2B contract test.",
    ))
    assert created.status == "draft" and created.parent_version == "config-v0.9.0"

    validated = service.validate(created.configuration_id, actor="local_researcher")
    assert validated.validation_status == "passed" and validated.status == "validated"

    activated = service.activate(created.configuration_id, actor="local_researcher", reason="H2B test.")
    assert activated.status == "active"
    assert sum(item.status == "active" for item in service.list()) == 1
    assert service.active().configuration_id == created.configuration_id

    actions = [item["action"] for item in service.audit()]
    assert {"create", "validate", "activate"} <= set(actions)
