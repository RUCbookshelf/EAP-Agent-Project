from __future__ import annotations

import json

from app.infrastructure.sqlite.connection import SQLiteConnectionManager


class SQLiteResearchRepository:
    def __init__(self, connection_manager: SQLiteConnectionManager):
        self._connection_manager = connection_manager

    def _next_research_id(self, table: str, id_column: str, prefix: str) -> str:
            with self._connection_manager.connect() as c:
                row = c.execute(
                    f"SELECT COALESCE(MAX(CAST(SUBSTR({id_column}, {len(prefix) + 1}) AS INTEGER)), 0) + 1 FROM {table}"
                ).fetchone()
            return f"{prefix}{int(row[0]):06d}"

    def save_human_review(self, review) -> dict:
            from app.research.schemas import HumanReview
            obj = review if isinstance(review, HumanReview) else HumanReview(**review)
            review_id = obj.review_id or self._next_research_id("human_reviews", "review_id", "HR")
            obj.review_id = review_id
            with self._connection_manager.connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO human_reviews VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        obj.review_id, obj.target_type.value if hasattr(obj.target_type, "value") else str(obj.target_type),
                        obj.target_id, obj.reviewer_id,
                        obj.decision.value if hasattr(obj.decision, "value") else str(obj.decision),
                        obj.confidence, obj.reason_code, obj.comment, obj.guideline_version,
                        obj.review_status.value if hasattr(obj.review_status, "value") else str(obj.review_status),
                        obj.created_at, obj.updated_at, obj.superseded_by,
                        json.dumps(obj.source_system_result_snapshot) if obj.source_system_result_snapshot else None,
                    ),
                )
            return obj.model_dump(mode="json")

    def list_human_reviews(self, target_type: str | None = None, target_id: str | None = None) -> list[dict]:
            from app.research.schemas import HumanReview
            with self._connection_manager.connect() as c:
                if target_type and target_id:
                    rows = c.execute(
                        "SELECT * FROM human_reviews WHERE target_type=? AND target_id=? ORDER BY created_at",
                        (target_type, target_id),
                    ).fetchall()
                elif target_type:
                    rows = c.execute(
                        "SELECT * FROM human_reviews WHERE target_type=? ORDER BY created_at", (target_type,)
                    ).fetchall()
                else:
                    rows = c.execute("SELECT * FROM human_reviews ORDER BY created_at").fetchall()
            result = []
            for row in rows:
                d = dict(row)
                d["source_system_result_snapshot"] = (
                    json.loads(d["source_system_result_snapshot"]) if d.get("source_system_result_snapshot") else None
                )
                try:
                    result.append(HumanReview(**d).model_dump(mode="json"))
                except Exception:
                    result.append(d)
            return result

    def apply_pii_review(self, submission_id: int, reviews: list) -> list[dict]:
            from app.research.schemas import PiiReview
            saved = []
            with self._connection_manager.connect() as c:
                for item in reviews:
                    obj = item if isinstance(item, PiiReview) else PiiReview(**item)
                    updated = c.execute(
                        """UPDATE pii_candidates SET review_status=?, action=?, reviewer_id=?, reviewed_at=?
                           WHERE pii_candidate_id=? AND submission_id=?""",
                        (
                            obj.action.value if hasattr(obj.action, "value") else str(obj.action),
                            obj.action.value if hasattr(obj.action, "value") else str(obj.action),
                            obj.reviewer_id, obj.reviewed_at, obj.pii_candidate_id, submission_id,
                        ),
                    ).rowcount
                    if updated:
                        row = c.execute(
                            "SELECT * FROM pii_candidates WHERE pii_candidate_id=?",
                            (obj.pii_candidate_id,),
                        ).fetchone()
                        if row:
                            saved.append(dict(row))
            return saved

    def save_export_job(self, job: dict) -> dict:
            with self._connection_manager.connect() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO export_jobs(
                        export_id, filter_json, privacy_mode, formats_json, status,
                        created_at, completed_at, export_directory, file_count,
                        record_counts_json, excluded_counts_json, manifest_path
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        job["export_id"], json.dumps(job.get("filter_spec", {})), job.get("privacy_mode"),
                        json.dumps(job.get("formats", [])), job.get("status"),
                        job.get("created_at"), job.get("completed_at"), job.get("export_directory"),
                        job.get("file_count", 0), json.dumps(job.get("record_counts", {})),
                        json.dumps(job.get("excluded_counts", {})), job.get("manifest_path"),
                    ),
                )
            return job

    def list_export_jobs(self) -> list[dict]:
            with self._connection_manager.connect() as c:
                rows = c.execute("SELECT * FROM export_jobs ORDER BY created_at DESC").fetchall()
            result = []
            for row in rows:
                d = dict(row)
                for key in ("filter_json", "formats_json", "record_counts_json", "excluded_counts_json"):
                    if d.get(key):
                        d[key.removesuffix("_json")] = json.loads(d.pop(key))
                if "filter_json" in d and d.get("filter_json") is not None:
                    d["filter_spec"] = json.loads(d.pop("filter_json"))
                result.append(d)
            return result

    def get_export_job(self, export_id: str) -> dict | None:
            with self._connection_manager.connect() as c:
                row = c.execute("SELECT * FROM export_jobs WHERE export_id=?", (export_id,)).fetchone()
            if row is None:
                return None
            d = dict(row)
            if d.get("filter_json"):
                d["filter_spec"] = json.loads(d.pop("filter_json"))
            if d.get("formats_json"):
                d["formats"] = json.loads(d.pop("formats_json"))
            if d.get("record_counts_json"):
                d["record_counts"] = json.loads(d.pop("record_counts_json"))
            if d.get("excluded_counts_json"):
                d["excluded_counts"] = json.loads(d.pop("excluded_counts_json"))
            return d
