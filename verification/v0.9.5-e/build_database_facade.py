from __future__ import annotations

import ast
import json
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "app" / "database" / "repository.py"
INVENTORY = Path(__file__).with_name("prechange_repository_inventory.json")

OWNER_ATTRIBUTE = {
    "SystemRepository": "_system_repository",
    "SubmissionRepository": "_submission_repository",
    "AnalysisRepository": "_analysis_repository",
    "CalfRepository": "_calf_repository",
    "RevisionRepository": "_revision_repository",
    "LearnerRepository": "_learner_repository",
    "PracticeRepository": "_practice_repository",
    "ResearchRepository": "_research_repository",
    "ConfigurationRepository": "_configuration_repository",
}

IMPORTS = """from app.infrastructure.sqlite.repositories import (
    SQLiteAnalysisRepository,
    SQLiteCalfRepository,
    SQLiteConfigurationRepository,
    SQLiteLearnerRepository,
    SQLitePracticeRepository,
    SQLiteResearchRepository,
    SQLiteRevisionRepository,
    SQLiteSubmissionRepository,
    SQLiteSystemRepository,
)
"""


def method_signature(node: ast.FunctionDef) -> str:
    result = f"def {node.name}({ast.unparse(node.args)})"
    if node.returns:
        result += f" -> {ast.unparse(node.returns)}"
    return result + ":"


def forwarded_arguments(node: ast.FunctionDef) -> str:
    arguments = [*node.args.posonlyargs, *node.args.args]
    if arguments and arguments[0].arg == "self":
        arguments = arguments[1:]
    values = [argument.arg for argument in arguments]
    if node.args.vararg:
        values.append(f"*{node.args.vararg.arg}")
    values.extend(f"{argument.arg}={argument.arg}" for argument in node.args.kwonlyargs)
    if node.args.kwarg:
        values.append(f"**{node.args.kwarg.arg}")
    return ", ".join(values)


def public_contract(database: ast.ClassDef) -> dict[str, str]:
    return {
        node.name: ast.dump(ast.Module(body=[node], type_ignores=[]), include_attributes=False)
        for node in database.body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    }


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    database = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Database")
    baseline_methods = {
        node.name: node for node in database.body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    }
    owner_by_method = {
        row["name"]: row["owner"]
        for row in json.loads(INVENTORY.read_text(encoding="utf-8"))["methods"]
    }
    if set(baseline_methods) != set(owner_by_method):
        raise AssertionError("Facade inventory no longer matches the pre-change public method set")

    prefix = source[: database.lineno - 1 and source.rfind("class Database:")]
    marker = "from app.infrastructure.sqlite import ClosingConnection, SQLiteConnectionManager\n"
    if IMPORTS not in prefix:
        prefix = prefix.replace(marker, marker + IMPORTS)

    private_ddl = {}
    for node in database.body:
        if not isinstance(node, ast.FunctionDef) or node.name not in {
            "_add_column_if_missing", "_migrate_v0_1_to_v0_1_1"
        }:
            continue
        block = textwrap.indent(ast.get_source_segment(source, node), "    ")
        if node.name == "_add_column_if_missing":
            block = "    @staticmethod\n" + block
        private_ddl[node.name] = block

    blocks = ["class Database:", "    def __init__(self, path: str | Path):", "        self.path = Path(path)",
              "        self._connection_manager = SQLiteConnectionManager(self.path)",
              "        self._system_repository = SQLiteSystemRepository(self._connection_manager)",
              "        self._configuration_repository = SQLiteConfigurationRepository(self._connection_manager)",
              "        self._analysis_repository = SQLiteAnalysisRepository(self._connection_manager)",
              "        self._calf_repository = SQLiteCalfRepository(self._connection_manager)",
              "        self._submission_repository = SQLiteSubmissionRepository(",
              "            self._connection_manager, SQLiteRevisionRepository.normalize_revision_stage",
              "        )",
              "        self._revision_repository = SQLiteRevisionRepository(",
              "            self._connection_manager, self._submission_repository",
              "        )",
              "        self._learner_repository = SQLiteLearnerRepository(",
              "            self._connection_manager, self._analysis_repository, self._calf_repository,",
              "            SQLiteRevisionRepository.normalize_revision_stage,",
              "        )",
              "        self._practice_repository = SQLitePracticeRepository(self._connection_manager)",
              "        self._research_repository = SQLiteResearchRepository(self._connection_manager)"]

    for node in database.body:
        if not isinstance(node, ast.FunctionDef) or node.name == "__init__":
            continue
        if node.name in private_ddl:
            blocks.extend(["", private_ddl[node.name]])
            continue
        if node.name.startswith("_"):
            continue
        blocks.append("")
        if node.name == "transaction":
            blocks.extend([
                "    @contextmanager",
                f"    {method_signature(node)}",
                "        with self._system_repository.transaction() as connection:",
                "            yield connection",
            ])
            continue
        if node.name == "normalize_revision_stage":
            blocks.extend([
                "    @staticmethod",
                f"    {method_signature(node)}",
                "        return SQLiteRevisionRepository.normalize_revision_stage(value)",
            ])
            continue
        attribute = OWNER_ATTRIBUTE[owner_by_method[node.name]]
        blocks.extend([
            f"    {method_signature(node)}",
            f"        return self.{attribute}.{node.name}({forwarded_arguments(node)})",
        ])

    result = prefix.rstrip() + "\n\n\n" + "\n".join(blocks) + "\n\n\nSQLiteRepository = Database\n"
    generated_tree = ast.parse(result)
    generated_database = next(
        node for node in generated_tree.body if isinstance(node, ast.ClassDef) and node.name == "Database"
    )
    generated_methods = {
        node.name: node for node in generated_database.body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    }
    if set(generated_methods) != set(baseline_methods):
        raise AssertionError("Generated public facade method set drifted")
    for name, before in baseline_methods.items():
        after = generated_methods[name]
        before_contract = (
            ast.dump(before.args, include_attributes=False),
            ast.dump(before.returns, include_attributes=False) if before.returns else None,
        )
        after_contract = (
            ast.dump(after.args, include_attributes=False),
            ast.dump(after.returns, include_attributes=False) if after.returns else None,
        )
        if before_contract != after_contract:
            raise AssertionError(f"Generated signature drift: {name}")
    SOURCE.write_text(result, encoding="utf-8")
    print(f"rewrote {SOURCE.relative_to(ROOT)} as explicit 86-method facade")


if __name__ == "__main__":
    main()
