"""v0.9.5-H2C focused tests: shared AnalysisRunReader infrastructure contract.

Proves that the two duplicate infrastructure-local `_AnalysisRunReader`
definitions (revision.py and learner.py) were canonicalized into one shared
`AnalysisRunReader` contract in
`app/infrastructure/sqlite/repositories/contracts.py` with zero runtime
behavior change: both consumers reference the same canonical contract object,
both former local definitions are absent, no alias exists, the concrete
SQLiteAnalysisRepository still satisfies the contract, no Service/API Port
imports the infrastructure contract, no active consumer-owned contract
changed, and the active persistence contract count is reduced by exactly one
(42 -> 41). Constructor parameter parity, facade identity, and missing/
populated analysis-run behavior through both consumers are verified on an
isolated database.
"""

from __future__ import annotations

import ast
import inspect
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings
from app.database import Database
from app.infrastructure.sqlite.repositories.analysis import SQLiteAnalysisRepository
from app.infrastructure.sqlite.repositories.contracts import AnalysisRunReader
from app.infrastructure.sqlite.repositories.learner import SQLiteLearnerRepository
from app.infrastructure.sqlite.repositories.revision import SQLiteRevisionRepository
from app.models import EssaySubmission
from app.services import build_submission_service


ROOT = Path(__file__).resolve().parents[1]
H1_INVENTORY = ROOT / "verification" / "v0.9.5-h1" / "protocol_inventory.json"

CONTRACTS_REL = "app/infrastructure/sqlite/repositories/contracts.py"
REVISION_REL = "app/infrastructure/sqlite/repositories/revision.py"
LEARNER_REL = "app/infrastructure/sqlite/repositories/learner.py"


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


def _init_params(classdef: ast.ClassDef) -> list[tuple[str, str | None]]:
    init = next(
        node for node in classdef.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    params = []
    positional = [*init.args.posonlyargs, *init.args.args]
    defaults = [None] * (len(positional) - len(init.args.defaults)) + list(init.args.defaults)
    for arg, default in zip(positional, defaults):
        params.append((arg.arg, ast.unparse(arg.annotation) if arg.annotation else None))
    for arg, default in zip(init.args.kwonlyargs, init.args.kw_defaults):
        params.append((arg.arg, ast.unparse(arg.annotation) if arg.annotation else None))
    return params


def _stored_attributes(classdef: ast.ClassDef) -> set[str]:
    init = next(
        node for node in classdef.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    stored = set()
    for node in ast.walk(init):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    stored.add(target.attr)
    return stored


def _inventory() -> dict:
    return json.loads(H1_INVENTORY.read_text(encoding="utf-8"))


def _active_contracts(inv: dict) -> list[dict]:
    return [c for c in inv["contracts"] if c["classification"] in ("A", "B", "C")]


def _module_file(module: str) -> Path:
    return ROOT / (module.replace(".", "/") + ".py")


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "h2c.db",
        llm_provider="local",
        deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com",
        deepseek_model="deepseek-chat",
    )


def _submission() -> EssaySubmission:
    return EssaySubmission(
        student_id="H2C-S",
        writing_prompt="P",
        genre="argumentative essay",
        draft_stage="first draft",
        timed=False,
        tool_use="none",
        essay_text="Students should protect public parks because green space matters for communities.",
        submitted_at=datetime(2026, 8, 3, tzinfo=timezone.utc),
    )


def _seed_essay_with_run(tmp_path: Path, database: Database) -> int:
    """Submit one essay through the factory (real analysis run persisted)."""
    service = build_submission_service(
        _settings(tmp_path),
        system_repository=database._system_repository,
        submission_repository=database._submission_repository,
        analysis_repository=database._analysis_repository,
        calibration_repository=database._calf_repository,
        learner_repository=database._learner_repository,
        configuration_repository=database._configuration_repository,
        revision_repository=database._revision_repository,
    )
    return service.submit(_submission(), synthetic=True).essay_id


# ---------------------------------------------------------------------------
# Layer 2 - Contract identity
# ---------------------------------------------------------------------------

class TestCanonicalContract:
    def test_one_canonical_definition_and_no_local_duplicates(self):
        canonical = []
        local = []
        for path in (ROOT / "app").rglob("*.py"):
            rel = path.relative_to(ROOT).as_posix()
            if "__pycache__" in rel or "-冲突-" in rel:
                continue
            classes = _classdefs(path)
            canonical.extend(
                (rel, node.lineno) for name, node in classes.items()
                if name == "AnalysisRunReader"
            )
            local.extend(
                (rel, node.lineno) for name, node in classes.items()
                if name == "_AnalysisRunReader"
            )
        assert local == []
        assert len(canonical) == 1
        assert canonical[0][0] == CONTRACTS_REL

    def test_both_consumers_reference_the_same_canonical_contract(self):
        from app.infrastructure.sqlite.repositories import learner, revision

        assert learner.AnalysisRunReader is revision.AnalysisRunReader is AnalysisRunReader
        assert AnalysisRunReader.__module__ == "app.infrastructure.sqlite.repositories.contracts"
        revision_annotation = SQLiteRevisionRepository.__init__.__annotations__["analysis_reader"]
        learner_annotation = SQLiteLearnerRepository.__init__.__annotations__["analysis_reader"]
        assert revision_annotation == "AnalysisRunReader"
        assert learner_annotation == "AnalysisRunReader"

    def test_canonical_method_set_matches_the_two_before_state_definitions(self):
        classes = _classdefs(ROOT / CONTRACTS_REL)
        contract = classes["AnalysisRunReader"]
        assert _method_names(contract) == ["get_latest_analysis_run"]
        assert [ast.unparse(base) for base in contract.bases] == ["Protocol"]
        assert [ast.unparse(d) for d in contract.decorator_list] == []
        method = next(
            node for node in contract.body
            if isinstance(node, ast.FunctionDef) and node.name == "get_latest_analysis_run"
        )
        assert ast.unparse(method.args) == "self, essay_id: int"
        assert ast.unparse(method.returns) == "dict[str, Any] | None"
        # Signature parity with the intended concrete satisfier.
        assert inspect.signature(AnalysisRunReader.get_latest_analysis_run) == inspect.signature(
            SQLiteAnalysisRepository.get_latest_analysis_run
        )

    def test_no_alias_preserves_either_old_local_definition(self):
        for path in (ROOT / "app").rglob("*.py"):
            rel = path.relative_to(ROOT).as_posix()
            if "__pycache__" in rel or "-冲突-" in rel:
                continue
            source = path.read_text(encoding="utf-8-sig")
            assert not re.search(r"\b_AnalysisRunReader\b", source), path

    def test_concrete_repository_structurally_satisfies_canonical_contract(self):
        assert hasattr(SQLiteAnalysisRepository, "get_latest_analysis_run")
        assert inspect.signature(
            getattr(AnalysisRunReader, "get_latest_analysis_run")
        ) == inspect.signature(getattr(SQLiteAnalysisRepository, "get_latest_analysis_run"))

    def test_contract_module_has_no_service_api_or_fastapi_dependency(self):
        source = (ROOT / CONTRACTS_REL).read_text(encoding="utf-8-sig")
        for forbidden in ("fastapi", "streamlit", "app.api", "app.services", "app.ui", "sqlite"):
            assert forbidden not in source, forbidden

    def test_no_service_or_api_port_imports_the_canonical_infrastructure_contract(self):
        for base in ("app/services", "app/api", "app/journey", "app/practice", "app/research"):
            for path in (ROOT / base).rglob("*.py"):
                rel = path.relative_to(ROOT).as_posix()
                if "__pycache__" in rel or "-冲突-" in rel:
                    continue
                source = path.read_text(encoding="utf-8-sig")
                assert "AnalysisRunReader" not in source, path
                assert "repositories.contracts" not in source, path

    def test_no_active_consumer_owned_contract_changed(self):
        inv = _inventory()
        for contract in _active_contracts(inv):
            if contract["contract_name"] == "_AnalysisRunReader":
                continue
            name = "ConfigurationPort" if contract["contract_name"] == "ConfigurationRepository" else contract["contract_name"]
            expected = {m["name"] for m in contract["declared_methods"]}
            if contract["contract_kind"] == "alias":
                continue
            classes = _classdefs(_module_file(contract["module"]))
            assert name in classes, (contract["module"], name)
            assert set(_method_names(classes[name])) == expected, (contract["module"], name)

    def test_active_persistence_contracts_reduced_by_exactly_one(self):
        inv = _inventory()
        current_targets = set()
        for contract in _active_contracts(inv):
            if contract["contract_name"] == "_AnalysisRunReader":
                current_targets.add(("AnalysisRunReader", CONTRACTS_REL))
            else:
                name = "ConfigurationPort" if contract["contract_name"] == "ConfigurationRepository" else contract["contract_name"]
                current_targets.add((name, contract["rel"]))
        assert len(_active_contracts(inv)) == 42
        assert len(current_targets) == 41

    def test_h2a_h2b_invariants_remain_valid(self):
        import app.repositories as repositories

        assert repositories.__all__ == ["RevisionRepository"]
        from app.repositories.protocols import RevisionRepository as Central

        assert Central is repositories.RevisionRepository
        classes = _classdefs(ROOT / "app/repositories/protocols.py")
        assert set(classes) == {"RevisionRepository"}
        configuration_classes = _classdefs(ROOT / "app/services/configuration.py")
        assert "ConfigurationPort" in configuration_classes
        assert _method_names(configuration_classes["ConfigurationPort"]) == [
            "list_configurations",
            "get_configuration",
            "get_active_configuration",
            "create_configuration",
            "set_configuration_validation",
            "activate_configuration",
            "list_configuration_audit",
        ]
        revision_classes = _classdefs(ROOT / REVISION_REL)
        learner_classes = _classdefs(ROOT / LEARNER_REL)
        assert "_SubmissionBundleReader" in revision_classes
        assert "_DiagnosticCalibrationReader" in learner_classes


# ---------------------------------------------------------------------------
# Layer 3 - Constructor parity
# ---------------------------------------------------------------------------

class TestConstructorParity:
    def test_consumer_constructor_parameters_unchanged_except_annotation(self):
        revision_classes = _classdefs(ROOT / REVISION_REL)
        learner_classes = _classdefs(ROOT / LEARNER_REL)
        revision_params = _init_params(revision_classes["SQLiteRevisionRepository"])
        learner_params = _init_params(learner_classes["SQLiteLearnerRepository"])

        assert revision_params == [
            ("self", None),
            ("connection_manager", "SQLiteConnectionManager"),
            ("submission_reader", "_SubmissionBundleReader"),
            ("analysis_reader", "AnalysisRunReader"),
        ]
        assert learner_params == [
            ("self", None),
            ("connection_manager", "SQLiteConnectionManager"),
            ("analysis_reader", "AnalysisRunReader"),
            ("calf_reader", "_DiagnosticCalibrationReader"),
            ("revision_stage_normalizer", "Callable[[str], str]"),
        ]
        assert "_analysis_reader" in _stored_attributes(revision_classes["SQLiteRevisionRepository"])
        assert "_analysis_reader" in _stored_attributes(learner_classes["SQLiteLearnerRepository"])

    def test_facade_wires_the_same_concrete_analysis_instance_into_both_consumers(self, tmp_path):
        database = Database(tmp_path / "h2c-identity.db")
        revision = database._revision_repository
        learner = database._learner_repository

        assert isinstance(revision, SQLiteRevisionRepository)
        assert isinstance(learner, SQLiteLearnerRepository)
        assert revision._analysis_reader is database._analysis_repository
        assert learner._analysis_reader is database._analysis_repository
        assert revision._connection_manager is database._connection_manager
        assert learner._connection_manager is database._connection_manager
        assert len({
            id(database._connection_manager),
            id(revision._connection_manager),
            id(learner._connection_manager),
            id(database._analysis_repository._connection_manager),
        }) == 1

    def test_no_repository_construction_call_or_composition_change(self):
        source = (ROOT / "app/database/repository.py").read_text(encoding="utf-8")
        assert source.count("SQLiteRevisionRepository(") == 1
        assert source.count("SQLiteLearnerRepository(") == 1
        assert "self._analysis_repository," in source
        for path in (ROOT / "app").rglob("*.py"):
            rel = path.relative_to(ROOT).as_posix()
            if "__pycache__" in rel or "-冲突-" in rel or rel == "app/database/repository.py":
                continue
            text = path.read_text(encoding="utf-8-sig")
            assert "SQLiteRevisionRepository(" not in text, path
            assert "SQLiteLearnerRepository(" not in text, path


# ---------------------------------------------------------------------------
# Layer 4 - Behavior parity (isolated database)
# ---------------------------------------------------------------------------

class TestBehaviorParity:
    def test_missing_and_populated_analysis_run_reads_unchanged_through_both_consumers(self, tmp_path):
        database = Database(tmp_path / "h2c-behavior.db")
        database.initialize()
        essay_id = _seed_essay_with_run(tmp_path, database)
        # Legacy record: essay with metrics+diagnosis but no analysis run
        # (repository-level seeding for the learner missing-run path).
        legacy_essay_id = database._submission_repository.save_essay(_submission(), synthetic=True)
        with database.connect() as connection:
            connection.execute(
                "INSERT INTO metrics(essay_id, metrics_json, analysis_version, limitations) VALUES (?, ?, ?, ?)",
                (legacy_essay_id, '{"word_count": 100}', "basic-analyzer-v0.1", "[]"),
            )
            connection.execute(
                "INSERT INTO diagnoses(essay_id, diagnosis_json, diagnosis_version) VALUES (?, ?, ?)",
                (legacy_essay_id, '{"improvement_priorities": []}', "prototype-diagnosis-v0.1.1"),
            )

        through_revision = database._revision_repository.get_latest_analysis_run(essay_id)
        assert through_revision is not None
        assert through_revision["analysis_run_id"].startswith("AR")
        assert database._revision_repository.get_latest_analysis_run(999999) is None

        # The learner consumer's analysis-run read path (visualization records)
        # resolves the same populated run and the same missing (legacy) state.
        records = database._learner_repository.list_visualization_records("H2C-S")
        by_id = {int(item["essay_id"]): item for item in records}
        assert by_id[essay_id]["analysis_run_id"] == through_revision["analysis_run_id"]
        assert by_id[essay_id]["analyzer_id"] == through_revision["analyzer_id"]
        assert by_id[legacy_essay_id]["analysis_run_id"] is None
        assert by_id[legacy_essay_id]["analyzer_id"] == "legacy"
        assert by_id[legacy_essay_id]["analysis_version"] == "basic-analyzer-v0.1"
