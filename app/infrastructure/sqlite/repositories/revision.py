from __future__ import annotations

import json
from typing import Any, Protocol

from app.infrastructure.sqlite import SQLiteConnectionManager
from app.infrastructure.sqlite.repositories.contracts import AnalysisRunReader
from app.revision import RevisionGroup, RevisionSnapshot


class _SubmissionBundleReader(Protocol):
    def get_submission_bundle(self, essay_id: int) -> dict[str, Any] | None: ...


class SQLiteRevisionRepository:
    def __init__(self, connection_manager: SQLiteConnectionManager,
                 submission_reader: _SubmissionBundleReader,
                 analysis_reader: AnalysisRunReader):
        self._connection_manager = connection_manager
        self._submission_reader = submission_reader
        self._analysis_reader = analysis_reader

    def get_submission_bundle(self, essay_id: int) -> dict[str, Any] | None:
        return self._submission_reader.get_submission_bundle(essay_id)

    def get_latest_analysis_run(self, essay_id: int) -> dict[str, Any] | None:
        return self._analysis_reader.get_latest_analysis_run(essay_id)

    @staticmethod
    def normalize_revision_stage(value: str) -> str:
        normalized = value.strip().casefold().replace("-", "_").replace(" ", "_")
        aliases = {
            "first": "first_draft", "first_draft": "first_draft",
            "revised": "revised_draft", "revision": "revised_draft", "revised_draft": "revised_draft",
            "final": "final_draft", "final_draft": "final_draft",
            "independent": "independent_submission", "independent_submission": "independent_submission",
        }
        return aliases.get(normalized, "independent_submission")

    def create_revision_group(self, source_submission_id: int) -> RevisionGroup:
        existing = self.get_revision_group_for_submission(source_submission_id)
        if existing:
            return existing
        source = self._submission_reader.get_submission_bundle(source_submission_id)
        if source is None:
            raise LookupError("Source submission not found.")
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        consistency = {"writing_prompt": True, "genre": True, "timed": True, "time_limit_minutes": True, "tool_use": True}
        limitations = ["Revision grouping is explicit metadata, not evidence of learning or proficiency change."]
        with self._connection_manager.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO revision_groups(
                    student_id, writing_prompt, genre, root_submission_id, created_at, updated_at,
                    metadata_consistency_json, limitations_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (source["student_id"], source["writing_prompt"], source["genre"], source_submission_id,
                 now, now, json.dumps(consistency), json.dumps(limitations)),
            )
            group_id = f"RG{int(cursor.lastrowid):06d}"
            connection.execute(
                "UPDATE revision_groups SET revision_group_id=? WHERE revision_group_row_id=?",
                (group_id, int(cursor.lastrowid)),
            )
            connection.execute(
                "UPDATE essays SET revision_group_id=?, revision_sequence=1, revision_stage=? WHERE essay_id=?",
                (group_id, self.normalize_revision_stage(source["draft_stage"]), source_submission_id),
            )
        group = self.get_revision_group(group_id)
        assert group is not None
        return group

    def link_revision(self, source_submission_id: int, target_submission_id: int, revision_group_id: str) -> None:
        source = self._submission_reader.get_submission_bundle(source_submission_id)
        target = self._submission_reader.get_submission_bundle(target_submission_id)
        if source is None or target is None:
            raise LookupError("Source or target submission not found.")
        sequence = int(source.get("revision_sequence") or 1) + 1
        consistency = {
            field: source.get(field) == target.get(field)
            for field in ("writing_prompt", "genre", "timed", "time_limit_minutes", "tool_use")
        }
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        with self._connection_manager.connect() as connection:
            connection.execute(
                """UPDATE essays SET revision_of_submission_id=?, revision_group_id=?,
                   revision_sequence=?, revision_stage=? WHERE essay_id=?""",
                (source_submission_id, revision_group_id, sequence,
                 self.normalize_revision_stage(target["draft_stage"]), target_submission_id),
            )
            connection.execute(
                "UPDATE revision_groups SET updated_at=?, metadata_consistency_json=? WHERE revision_group_id=?",
                (now, json.dumps(consistency), revision_group_id),
            )

    def get_revision_group(self, revision_group_id: str) -> RevisionGroup | None:
        with self._connection_manager.connect() as connection:
            row = connection.execute("SELECT * FROM revision_groups WHERE revision_group_id=?", (revision_group_id,)).fetchone()
            members = connection.execute(
                "SELECT essay_id FROM essays WHERE revision_group_id=? ORDER BY revision_sequence, essay_id", (revision_group_id,)
            ).fetchall() if row else []
        if not row:
            return None
        item = dict(row)
        member_ids = [int(member[0]) for member in members]
        return RevisionGroup(
            revision_group_id=item["revision_group_id"], student_id=item["student_id"],
            writing_prompt=item["writing_prompt"], genre=item["genre"], root_submission_id=item["root_submission_id"],
            member_submission_ids=member_ids, current_revision_id=member_ids[-1],
            created_at=item["created_at"], updated_at=item["updated_at"],
            metadata_consistency=json.loads(item["metadata_consistency_json"]),
            limitations=json.loads(item["limitations_json"]),
        )

    def get_revision_group_for_submission(self, submission_id: int) -> RevisionGroup | None:
        with self._connection_manager.connect() as connection:
            row = connection.execute("SELECT revision_group_id FROM essays WHERE essay_id=?", (submission_id,)).fetchone()
        return self.get_revision_group(row[0]) if row and row[0] else None

    def list_revision_candidates(self, submission_id: int) -> list[dict[str, Any]]:
        target = self._submission_reader.get_submission_bundle(submission_id)
        if target is None:
            raise LookupError("Submission not found.")
        with self._connection_manager.connect() as connection:
            rows = connection.execute(
                """SELECT essay_id, submitted_at, writing_prompt, genre, draft_stage, revision_group_id,
                   revision_sequence FROM essays WHERE student_id=? AND essay_id<>? AND submitted_at<=?
                   ORDER BY submitted_at DESC, essay_id DESC""",
                (target["student_id"], submission_id, target["submitted_at"]),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_revision_snapshot(self, snapshot: RevisionSnapshot) -> RevisionSnapshot:
        with self._connection_manager.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO revision_snapshots(
                    revision_group_id, source_submission_id, target_submission_id, snapshot_json,
                    alignment_version, uptake_version, configuration_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (snapshot.revision_group_id, snapshot.source_submission_id, snapshot.target_submission_id,
                 snapshot.model_dump_json(), snapshot.algorithm_versions["alignment"],
                 snapshot.algorithm_versions["uptake"], snapshot.configuration_version,
                 snapshot.generated_at.isoformat()),
            )
            snapshot_id = f"RS{int(cursor.lastrowid):06d}"
            stored = snapshot.model_copy(update={"revision_snapshot_id": snapshot_id})
            connection.execute(
                "UPDATE revision_snapshots SET revision_snapshot_id=?, snapshot_json=? WHERE revision_snapshot_row_id=?",
                (snapshot_id, stored.model_dump_json(), int(cursor.lastrowid)),
            )
        return stored

    def list_revision_snapshots(self, revision_group_id: str) -> list[dict[str, Any]]:
        with self._connection_manager.connect() as connection:
            rows = connection.execute(
                "SELECT snapshot_json FROM revision_snapshots WHERE revision_group_id=? ORDER BY revision_snapshot_row_id",
                (revision_group_id,),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def get_latest_revision_snapshot(self, revision_group_id: str) -> dict[str, Any] | None:
        items = self.list_revision_snapshots(revision_group_id)
        return items[-1] if items else None
