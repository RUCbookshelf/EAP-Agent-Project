"""Research router: export, PII, human review, dataset split, and data quality."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.deps import get_repository, get_research
from app.research.schemas import ExportJob, HumanReviewCreate, PiiReview

router = APIRouter()


@router.get("/api/v1/research/export/schema")
def research_export_schema(research_service=Depends(get_research)) -> dict:
    return research_service.schema()


@router.post("/api/v1/research/export/preview")
def research_export_preview(payload: dict, research_service=Depends(get_research)) -> dict:
    try:
        job = ExportJob(**payload)
    except Exception as exc:
        raise HTTPException(422, f"Invalid export job: {str(exc)[:200]}") from None
    return research_service.preview(job)


@router.post("/api/v1/research/export/run")
def research_export_run(
    payload: dict,
    request: Request,
    research_service=Depends(get_research),
    repository=Depends(get_repository),
) -> dict:
    try:
        job = ExportJob(**payload)
    except Exception as exc:
        raise HTTPException(422, f"Invalid export job: {str(exc)[:200]}") from None
    result = research_service.run_export(
        job,
        git_commit=request.app.state.git_commit if hasattr(request.app.state, "git_commit") else None,
        migration_version=getattr(request.app.state, "migration_version", None),
        config_version=getattr(request.app.state, "config_version", None),
    )
    # Persist export-job metadata for history/status lookups (append-only; no schema change).
    if hasattr(repository, "save_export_job"):
        try:
            repository.save_export_job({
                "export_id": result.get("export_id"),
                "filter_spec": job.filter_spec.model_dump(mode="json"),
                "privacy_mode": job.privacy_mode.value,
                "formats": [f.value for f in job.formats],
                "status": result.get("status"),
                "created_at": (result.get("manifest") or {}).get("created_at"),
                "completed_at": (result.get("manifest") or {}).get("created_at"),
                "export_directory": result.get("export_directory"),
                "file_count": result.get("file_count", 0),
                "record_counts": result.get("record_counts", {}),
                "excluded_counts": {},
                "manifest_path": result.get("manifest_path"),
            })
        except Exception:
            pass  # History persistence is best-effort; export itself already succeeded.
    return result


# NOTE: /history must be registered BEFORE /{export_id} so it is not shadowed.
@router.get("/api/v1/research/export/history")
def research_export_history(research_service=Depends(get_research)) -> list[dict]:
    return research_service.export_history()


@router.get("/api/v1/research/export/{export_id}/manifest")
def research_export_manifest(export_id: str, research_service=Depends(get_research)) -> dict:
    status = research_service.export_status(export_id)
    if status.get("status") == "unknown":
        raise HTTPException(404, "Export job not found.")
    manifest_path = status.get("manifest_path")
    if manifest_path and Path(manifest_path).exists():
        import json as _json
        return _json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    raise HTTPException(404, "Export manifest not found.")


@router.get("/api/v1/research/export/{export_id}")
def research_export_status(export_id: str, research_service=Depends(get_research)) -> dict:
    return research_service.export_status(export_id)


@router.get("/api/v1/research/data-quality")
def research_data_quality(research_service=Depends(get_research)) -> dict:
    return research_service.data_quality_report().model_dump(mode="json")


@router.get("/api/v1/submissions/{submission_id}/pii-candidates")
def pii_candidates(submission_id: int, research_service=Depends(get_research)) -> list[dict]:
    try:
        return research_service.scan_pii(submission_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None


@router.post("/api/v1/submissions/{submission_id}/pii-review")
def pii_review(
    submission_id: int, payload: dict,
    research_service=Depends(get_research),
) -> dict:
    try:
        reviews = [PiiReview(**item) for item in payload.get("reviews", [])]
    except Exception as exc:
        raise HTTPException(422, f"Invalid PII review: {str(exc)[:200]}") from None
    return {"submission_id": submission_id, "updated_candidates": research_service.apply_pii_review(submission_id, reviews)}


@router.post("/api/v1/research/reviews")
def create_human_review(payload: dict, research_service=Depends(get_research)) -> dict:
    try:
        review = HumanReviewCreate(**payload)
    except Exception as exc:
        raise HTTPException(422, f"Invalid human review: {str(exc)[:200]}") from None
    result = research_service.create_human_review(review)
    return result.model_dump(mode="json")


@router.get("/api/v1/research/reviews")
def list_human_reviews(
    target_type: str | None = None, target_id: str | None = None,
    research_service=Depends(get_research),
) -> list[dict]:
    return research_service.get_human_reviews(target_type, target_id)


@router.post("/api/v1/research/dataset-split")
def create_dataset_split(payload: dict, research_service=Depends(get_research)) -> dict:
    try:
        return research_service.create_dataset_split(payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
