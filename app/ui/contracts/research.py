"""UI-safe Research Data export payload contract (v0.9.5-C).

Builds the exact request JSON previously produced by constructing backend
Pydantic models (ExportJob/ExportFilter/PrivacyMode/ExportFormat) in the UI.
The shape, defaults, enum string values, and UTC timestamp format mirror the
backend serialization; a payload-parity test pins the equivalence. No backend
imports.
"""

from __future__ import annotations

from datetime import datetime, timezone


# Values exposed to the Research Data page (identical strings to the backend
# PrivacyMode / ExportFormat enums).
PRIVACY_MODES: tuple[str, ...] = ("pseudonymized", "internal_research", "minimal_anonymous")
EXPORT_FORMATS: tuple[str, ...] = ("jsonl", "csv")


# Serialized ExportFilter() with all backend defaults (model_dump shape).
_DEFAULT_EXPORT_FILTER: dict = {
    "student_ids": None,
    "pseudonyms": None,
    "date_from": None,
    "date_to": None,
    "genres": None,
    "draft_stages": None,
    "revision_group_ids": None,
    "independent_tasks_only": None,
    "task_cluster_ids": None,
    "timed_only": None,
    "tool_use": None,
    "analyzer_versions": None,
    "metric_versions": None,
    "diagnostic_statuses": None,
    "providers": None,
    "fallback_status": None,
    "human_review_status": None,
    "data_sufficiency_status": None,
    "privacy_mode": "pseudonymized",
    "formats": ["jsonl"],
}


def build_export_job_payload(privacy_mode: str, formats: list[str]) -> dict:
    """Build the exact export-job JSON previously sent by the Research Data page."""
    return {
        "export_id": None,
        "export_schema_version": "research-export-v0.1",
        "filter_spec": dict(_DEFAULT_EXPORT_FILTER),
        "privacy_mode": privacy_mode,
        "formats": list(formats),
        "status": "preview",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "export_directory": None,
        "file_count": 0,
        "record_counts": {},
        "excluded_counts": {},
        "manifest_path": None,
    }
