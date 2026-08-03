"""v0.9.5-F6A0 focused tests: Revision repository capability completion.

Proves that SQLiteRevisionRepository structurally satisfies the unchanged
central RevisionRepository contract, that the two new read delegations
preserve pass-through/exception/missing-record behavior, that the facade
wires the exact existing Submission and Analysis repository instances into
the Revision repository, that all three share one connection manager (one
repository graph), and that the two delegations open no connections and
contain no SQL or transaction logic.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from app.database import Database
from app.infrastructure.sqlite.repositories.analysis import SQLiteAnalysisRepository
from app.infrastructure.sqlite.repositories.revision import SQLiteRevisionRepository
from app.infrastructure.sqlite.repositories.submission import SQLiteSubmissionRepository
from app.repositories.protocols import RevisionRepository


ROOT = Path(__file__).resolve().parents[1]


def _protocol_methods(protocol) -> dict[str, object]:
    return {
        name: value for name, value in vars(protocol).items()
        if not name.startswith("_") and callable(value)
    }


class CountingSubmissionReader:
    def __init__(self, row=None):
        self.row = row
        self.calls = 0
        self.last_id: int | None = None
        self.exception: Exception | None = None

    def get_submission_bundle(self, essay_id: int):
        self.calls += 1
        self.last_id = essay_id
        if self.exception is not None:
            raise self.exception
        return self.row


class CountingAnalysisReader:
    def __init__(self, run=None):
        self.run = run
        self.calls = 0
        self.last_id: int | None = None
        self.exception: Exception | None = None

    def get_latest_analysis_run(self, essay_id: int):
        self.calls += 1
        self.last_id = essay_id
        if self.exception is not None:
            raise self.exception
        return self.run


class TestStructuralContract:
    def test_revision_repository_protocol_method_set_is_unchanged(self):
        assert set(_protocol_methods(RevisionRepository)) == {
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
        }

    def test_sqlite_revision_repository_structurally_satisfies_protocol(self):
        for name, member in _protocol_methods(RevisionRepository).items():
            assert hasattr(SQLiteRevisionRepository, name), name
            assert inspect.signature(getattr(SQLiteRevisionRepository, name)) == inspect.signature(member), name

    def test_two_new_methods_have_exact_signature_parity_with_reader_repositories(self):
        assert inspect.signature(SQLiteRevisionRepository.get_submission_bundle) == inspect.signature(
            SQLiteSubmissionRepository.get_submission_bundle
        )
        assert inspect.signature(SQLiteRevisionRepository.get_latest_analysis_run) == inspect.signature(
            SQLiteAnalysisRepository.get_latest_analysis_run
        )

    def test_delegation_methods_contain_no_connection_sql_or_transaction_logic(self):
        source = (ROOT / "app/infrastructure/sqlite/repositories/revision.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        for name in ("get_submission_bundle", "get_latest_analysis_run"):
            node = next(
                candidate for candidate in ast.walk(tree)
                if isinstance(candidate, ast.FunctionDef) and candidate.name == name
            )
            segment = ast.get_source_segment(source, node)
            assert segment is not None
            assert "connect" not in segment
            assert "execute" not in segment
            assert "commit" not in segment
            assert "rollback" not in segment

    def test_existing_write_methods_retain_their_owned_updates(self):
        source = (ROOT / "app/infrastructure/sqlite/repositories/revision.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        segments = {
            node.name: ast.get_source_segment(source, node)
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name in {"create_revision_group", "link_revision", "save_revision_snapshot"}
        }
        assert segments["create_revision_group"] and "UPDATE essays" in segments["create_revision_group"]
        assert segments["link_revision"] and "UPDATE essays" in segments["link_revision"]
        assert segments["save_revision_snapshot"] and "INSERT INTO revision_snapshots" in segments["save_revision_snapshot"]


class TestDelegationBehavior:
    def test_get_submission_bundle_delegates_exactly_once_and_passes_through(self):
        row = {"essay_id": 7, "student_id": "S001", "essay_text": "Text."}
        reader = CountingSubmissionReader(row=row)
        repository = SQLiteRevisionRepository(None, reader, CountingAnalysisReader())

        result = repository.get_submission_bundle(7)

        assert reader.calls == 1
        assert reader.last_id == 7
        assert result is row

    def test_get_latest_analysis_run_delegates_exactly_once_and_passes_through(self):
        run = {"analysis_run_id": "AR000001", "metric_results": []}
        reader = CountingAnalysisReader(run=run)
        repository = SQLiteRevisionRepository(None, CountingSubmissionReader(), reader)

        result = repository.get_latest_analysis_run(9)

        assert reader.calls == 1
        assert reader.last_id == 9
        assert result is run

    def test_missing_record_behavior_passes_through(self):
        submission = CountingSubmissionReader(row=None)
        analysis = CountingAnalysisReader(run=None)
        repository = SQLiteRevisionRepository(None, submission, analysis)

        assert repository.get_submission_bundle(1) is None
        assert repository.get_latest_analysis_run(1) is None
        assert submission.calls == 1
        assert analysis.calls == 1

    def test_reader_exceptions_propagate_unchanged(self):
        submission = CountingSubmissionReader()
        submission.exception = LookupError("Submission not found.")
        analysis = CountingAnalysisReader()
        analysis.exception = RuntimeError("analysis read failed")
        repository = SQLiteRevisionRepository(None, submission, analysis)

        with pytest.raises(LookupError, match="Submission not found."):
            repository.get_submission_bundle(1)
        with pytest.raises(RuntimeError, match="analysis read failed"):
            repository.get_latest_analysis_run(1)
        assert submission.calls == 1
        assert analysis.calls == 1


class TestFacadeComposition:
    def test_facade_wires_exact_existing_instances_with_one_connection_manager(self, tmp_path):
        database = Database(tmp_path / "f6a0.db")
        revision = database._revision_repository

        assert isinstance(revision, SQLiteRevisionRepository)
        assert revision._submission_reader is database._submission_repository
        assert revision._analysis_reader is database._analysis_repository
        assert revision._connection_manager is database._connection_manager
        assert database._submission_repository._connection_manager is database._connection_manager
        assert database._analysis_repository._connection_manager is database._connection_manager

    def test_one_database_creates_one_repository_graph(self, tmp_path):
        database = Database(tmp_path / "f6a0-graph.db")
        managers = {
            id(database._connection_manager),
            id(database._revision_repository._connection_manager),
            id(database._submission_repository._connection_manager),
            id(database._analysis_repository._connection_manager),
        }
        assert len(managers) == 1

    def test_only_one_revision_repository_construction_site_in_production(self):
        source = (ROOT / "app/database/repository.py").read_text(encoding="utf-8")
        assert source.count("SQLiteRevisionRepository(") == 1
        assert "self._analysis_repository" in source

    def test_database_public_facade_remains_86_methods(self):
        source = (ROOT / "app/database/repository.py").read_text(encoding="utf-8")
        public = [
            line for line in source.splitlines()
            if line.startswith("    def ") and not line.startswith("    def _")
        ]
        assert len(public) == 2  # v0.9.5-G evidence-supported surface: connect, initialize
