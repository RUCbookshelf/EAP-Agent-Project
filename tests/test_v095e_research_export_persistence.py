from __future__ import annotations

from app.database import Database


def test_export_job_repository_surface_round_trips_without_creating_export_files(tmp_path):
    database = Database(tmp_path / "export-job.db")
    database.initialize()
    job = {
        "export_id": "EXP-V095E-001",
        "filter_spec": {"student_ids": ["S001"]},
        "privacy_mode": "pseudonymized",
        "formats": ["jsonl"],
        "status": "preview",
        "created_at": "2026-08-02T00:00:00+00:00",
        "completed_at": None,
        "export_directory": None,
        "file_count": 0,
        "record_counts": {},
        "excluded_counts": {},
        "manifest_path": None,
    }
    assert database._research_repository.save_export_job(job) is job
    assert database._research_repository.get_export_job(job["export_id"]) == job
    listed = database._research_repository.list_export_jobs()
    assert len(listed) == 1
    assert listed[0]["filter"] == job["filter_spec"]
    assert "filter_spec" not in listed[0]
    assert {key: value for key, value in listed[0].items() if key != "filter"} == {
        key: value for key, value in job.items() if key != "filter_spec"
    }
    assert list(tmp_path.iterdir()) == [tmp_path / "export-job.db"]
