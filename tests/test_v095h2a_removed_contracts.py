"""v0.9.5-H2A focused tests: removed legacy contracts and preserved active contracts.

Proves the 13 H1-approved unused persistence contracts are gone (definitions,
re-exports, imports) and that every H1-active contract (A/B/C), its method
set, and its intended concrete Repository satisfier are unchanged. Source
structure is read via AST; no unstable line numbers are hard-coded.

v0.9.5-H2C canonicalized the exact duplicate infrastructure reader pair
(_AnalysisRunReader in revision.py and learner.py) into one shared
AnalysisRunReader contract in app/infrastructure/sqlite/repositories/
contracts.py; the two historical inventory entries map to that single
canonical definition while the H1 inventory remains historical evidence.
"""

from __future__ import annotations

import ast
import importlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
H1_INVENTORY = ROOT / "verification" / "v0.9.5-h1" / "protocol_inventory.json"

# H1-inventory name -> post-H2B active name (v0.9.5-H2B renamed the active
# local configuration contract; the H1 inventory remains historical evidence).
H1_RENAMED = {"ConfigurationRepository": "ConfigurationPort"}

# H1-inventory duplicate reader pair -> post-H2C canonical definition
# (v0.9.5-H2C; the H1 inventory remains historical evidence).
H2C_REPLACED = {
    "_AnalysisRunReader": ("AnalysisRunReader", "app.infrastructure.sqlite.repositories.contracts"),
}

REMOVED_NAMES = {
    "StudentRepository",
    "EssayRepository",
    "MetricRepository",
    "ErrorAnnotationRepository",
    "DiagnosisRepository",
    "FeedbackRepository",
    "ExerciseRepository",
    "LearnerHistoryRepository",
    "LearnerProfileRepository",
    "ConfigurationRepository",
    "SystemVersionRepository",
    "SubmissionRepositories",
    "SubmissionRepository",
}

REPOSITORIES_INIT = ROOT / "app/repositories/__init__.py"
PROTOCOLS_MODULE = ROOT / "app/repositories/protocols.py"
SUBMISSION_MODULE = ROOT / "app/services/submission.py"


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))


def _classdefs(path: Path) -> dict[str, ast.ClassDef]:
    tree = _parse(path)
    return {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
    }


def _assign_names(path: Path) -> set[str]:
    tree = _parse(path)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def _method_names(classdef: ast.ClassDef) -> list[str]:
    return [
        node.name
        for node in classdef.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def _inventory() -> dict:
    return json.loads(H1_INVENTORY.read_text(encoding="utf-8"))


def _active_contracts(inv: dict) -> list[dict]:
    return [c for c in inv["contracts"] if c["classification"] in ("A", "B", "C")]


def _module_file(module: str) -> Path:
    return ROOT / (module.replace(".", "/") + ".py")


def _import_class(module: str, name: str):
    mod = importlib.import_module(module)
    return getattr(mod, name)


def _current_contract_target(contract: dict) -> tuple[str, str]:
    """Map an H1-inventory contract entry to its current definition target."""
    name = H1_RENAMED.get(contract["contract_name"], contract["contract_name"])
    module = contract["module"]
    if contract["contract_name"] in H2C_REPLACED:
        name, module = H2C_REPLACED[contract["contract_name"]]
    return name, module


# ---------------------------------------------------------------------------
# 1. Removed definitions and re-exports are absent
# ---------------------------------------------------------------------------

def test_thirteen_removed_names_absent_from_former_modules():
    # central definition module: no removed Protocol class and no alias assignment
    central_classes = _classdefs(PROTOCOLS_MODULE)
    central_assigns = _assign_names(PROTOCOLS_MODULE)
    assert REMOVED_NAMES.isdisjoint(central_classes)
    assert "SubmissionRepositories" not in central_assigns

    # legacy combined class absent from the SubmissionService module
    submission_classes = _classdefs(SUBMISSION_MODULE)
    assert "SubmissionRepository" not in submission_classes

    # package re-export module no longer references any removed name
    init_source = REPOSITORIES_INIT.read_text(encoding="utf-8")
    tree = ast.parse(init_source, filename=str(REPOSITORIES_INIT))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported.add(alias.name)
    assert REMOVED_NAMES.isdisjoint(imported)
    assert "RevisionRepository" in imported


def test_repositories_package_reexports_only_active_central_contract():
    import app.repositories as repositories

    assert repositories.__all__ == ["RevisionRepository"]
    assert set(dir(repositories)).isdisjoint(REMOVED_NAMES)
    assert repositories.RevisionRepository is not None


# ---------------------------------------------------------------------------
# 2. No active source import references a removed name
# ---------------------------------------------------------------------------

def test_no_source_import_references_any_removed_name():
    scanned = []
    for base in ("app", "scripts", "tests"):
        for path in (ROOT / base).rglob("*.py"):
            rel = path.relative_to(ROOT).as_posix()
            if "__pycache__" in rel or "-冲突-" in rel:
                continue
            if rel.startswith("verification/"):
                continue
            scanned.append(path)
    for path in scanned:
        tree = _parse(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    tail = alias.name.split(".")[-1]
                    assert tail not in REMOVED_NAMES, (path, alias.name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    assert alias.name not in REMOVED_NAMES, (path, alias.name)


# ---------------------------------------------------------------------------
# 3. All 42 H1-active contracts remain defined with exact method sets
# ---------------------------------------------------------------------------

def test_all_h1_active_contracts_remain_defined_with_exact_method_sets():
    inv = _inventory()
    active = _active_contracts(inv)
    assert len(active) == 42
    for contract in active:
        name, module = _current_contract_target(contract)
        expected = {m["name"] for m in contract["declared_methods"]}
        if contract["contract_kind"] == "alias":
            continue
        classes = _classdefs(_module_file(module))
        assert name in classes, (module, name)
        actual = set(_method_names(classes[name]))
        assert actual == expected, (module, name, sorted(actual), sorted(expected))


# ---------------------------------------------------------------------------
# 4. Intended concrete Repositories still satisfy active contracts
# ---------------------------------------------------------------------------

def test_intended_concrete_repositories_satisfy_active_contracts():
    inv = _inventory()
    for contract in _active_contracts(inv):
        port_class = None
        if contract["contract_kind"] == "protocol":
            name, module = _current_contract_target(contract)
            port_class = _import_class(module, name)
        expected = {m["name"] for m in contract["declared_methods"]}
        assert contract["concrete_structural_implementations"], contract["contract_name"]
        for impl_ref in contract["concrete_structural_implementations"]:
            impl_module, impl_name = impl_ref.split("::")
            impl_class = _import_class(impl_module, impl_name)
            if port_class is not None and contract["runtime_checkable"]:
                assert issubclass(impl_class, port_class), (contract["contract_name"], impl_name)
            for method in expected:
                assert hasattr(impl_class, method), (contract["contract_name"], impl_name, method)


# ---------------------------------------------------------------------------
# 5. SubmissionService still uses exactly its four F6C Ports
# ---------------------------------------------------------------------------

def test_submission_service_uses_exactly_four_f6c_ports():
    tree = _parse(SUBMISSION_MODULE)
    init = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    annotations = {
        ast.unparse(argument.annotation)
        for argument in [*init.args.args, *init.args.kwonlyargs]
        if argument.annotation is not None
    }
    assert {
        "SubmissionSystemPort", "SubmissionDataPort",
        "SubmissionAnalysisPort", "SubmissionCalibrationPort",
    } <= annotations
    assert "SubmissionRepository" not in annotations


# ---------------------------------------------------------------------------
# 6. Active local configuration contract unchanged (renamed to ConfigurationPort
#    by v0.9.5-H2B; the old active-contract name must be gone)
# ---------------------------------------------------------------------------

def test_local_configuration_contract_unchanged_after_h2b_rename():
    source = (ROOT / "app/services/configuration.py").read_text(encoding="utf-8")
    assert "from app.repositories" not in source  # annotation resolves locally
    assert "ConfigurationRepository" not in source  # old active-contract name gone
    classes = _classdefs(ROOT / "app/services/configuration.py")
    assert "ConfigurationPort" in classes
    assert _method_names(classes["ConfigurationPort"]) == [
        "list_configurations",
        "get_configuration",
        "get_active_configuration",
        "create_configuration",
        "set_configuration_validation",
        "activate_configuration",
        "list_configuration_audit",
    ]


# ---------------------------------------------------------------------------
# 7. Practice read/write Port separation unchanged
# ---------------------------------------------------------------------------

def test_practice_read_write_port_separation_unchanged():
    inv = _inventory()
    practice = [c for c in inv["contracts"] if c["module"] == "app.practice.ports"]
    assert {c["contract_name"] for c in practice} == {
        "PracticeSubmissionReadPort", "PracticeReadPort", "PracticeWritePort",
    }
    classes = _classdefs(ROOT / "app/practice/ports.py")
    for contract in practice:
        assert _method_names(classes[contract["contract_name"]]) == [
            m["name"] for m in contract["declared_methods"]
        ]


# ---------------------------------------------------------------------------
# 8. API-owned Ports unchanged
# ---------------------------------------------------------------------------

def test_api_owned_ports_unchanged():
    inv = _inventory()
    api = [c for c in inv["contracts"] if c["module"] == "app.api.ports"]
    assert len(api) == 10
    classes = _classdefs(ROOT / "app/api/ports.py")
    for contract in api:
        assert contract["contract_name"] in classes
        assert _method_names(classes[contract["contract_name"]]) == [
            m["name"] for m in contract["declared_methods"]
        ]


# ---------------------------------------------------------------------------
# 9. RevisionRepository remains the only central contract and is importable
# ---------------------------------------------------------------------------

def test_revision_repository_still_importable_and_exact():
    from app.repositories import RevisionRepository
    from app.repositories.protocols import RevisionRepository as Direct

    assert RevisionRepository is Direct
    classes = _classdefs(PROTOCOLS_MODULE)
    assert set(classes) == {"RevisionRepository"}
    assert _method_names(classes["RevisionRepository"]) == [
        "get_submission_bundle",
        "get_latest_analysis_run",
        "create_revision_group",
        "link_revision",
        "get_revision_group",
        "get_revision_group_for_submission",
        "list_revision_candidates",
        "save_revision_snapshot",
        "list_revision_snapshots",
        "get_latest_revision_snapshot",
    ]
