"""Wave-2 Context-Aware Revision Loop API (Goal PDW2-C-L2-REVISION-SCAFFOLD).

Router module under ``/api/v1/wave2/revision/``. The CORE Wave-2 assembly
(``app.api.routers.wave2``) mounts this module's ``router`` at integration;
``wave2_modules/__init__.py`` is contributed by CORE, so this module stays
importable as a namespace package on the L2 branch.

The branch-local default dependency builds the service over the EXISTING
composition-root services (``app.state.submission_service`` /
``app.state.reanalysis``) with an in-memory repository; integration wiring
replaces the repository. Test clients override the dependency.

All responses use bounded non-normative language; composed outputs are
scanned with the shared NormativeClaimsScanner (strict) and rejected
structurally (HTTP 500) on any violation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.learner.normative import NormativeClaimsScanner
from app.l2.wave2.corpus_routing import LocalWrittenCorpusRouter
from app.l2.wave2.pipeline import ExistingWritingPipeline
from app.l2.wave2.repository import InMemoryRevisionLoopRepository
from app.l2.wave2.revision_loop import RevisionLoopService
from app.l2.wave2.models import WritingTaskMetadata


router = APIRouter()

_SCANNER = NormativeClaimsScanner()
_DEFAULT_REPOSITORY = InMemoryRevisionLoopRepository()

NORMATIVE_REJECTION_DETAIL = (
    "An output candidate failed the no-normative-claims scan; nothing was "
    "returned (structural rejection)."
)


def get_revision_loop_service(request: Request) -> RevisionLoopService:
    """Branch-local default: existing composition-root services + in-memory
    repository until the Wave-2 composition wiring lands at integration."""

    submission_service = getattr(request.app.state, "submission_service", None)
    reanalysis_service = getattr(request.app.state, "reanalysis", None)
    if submission_service is None or reanalysis_service is None:
        raise HTTPException(
            status_code=503,
            detail="Wave-2 revision router requires the composition-root services.",
        )
    return RevisionLoopService(
        repository=_DEFAULT_REPOSITORY,
        pipeline=ExistingWritingPipeline(submission_service, reanalysis_service),
        routing=LocalWrittenCorpusRouter(),
    )


def reject_normative_output(payload) -> None:
    """Strict no-normative-claims guard over a composed response payload."""
    violations = _SCANNER.scan_mapping(payload)
    if violations:
        raise HTTPException(status_code=500, detail=NORMATIVE_REJECTION_DETAIL)


class CreateTaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str = Field(min_length=1, max_length=100)
    task_type: str = Field(min_length=1, max_length=64)
    writing_context: str = Field(min_length=1, max_length=64)
    writing_prompt: str = Field(min_length=1, max_length=4000)
    metadata: WritingTaskMetadata | None = None
    declared_task_type: str | None = Field(default=None, max_length=64)


class SubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    essay_text: str = Field(min_length=1)
    draft_stage: str = Field(default="first draft", min_length=1, max_length=100)
    tool_use: str = Field(default="none", max_length=300)


class ReviseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    essay_text: str = Field(min_length=1)
    draft_stage: str = Field(default="revised draft", min_length=1, max_length=100)
    tool_use: str = Field(default="none", max_length=300)


@router.post("/api/v1/wave2/revision/tasks", status_code=201)
def create_task(
    request: CreateTaskRequest,
    service: RevisionLoopService = Depends(get_revision_loop_service),
) -> dict:
    """Register a two-level writing task (task_type + writing_context)."""
    task = service.create_task(
        student_id=request.student_id,
        task_type=request.task_type,
        writing_context=request.writing_context,
        writing_prompt=request.writing_prompt,
        metadata=request.metadata,
        declared_task_type=request.declared_task_type,
    )
    payload = task.model_dump(mode="json")
    reject_normative_output(payload)
    return payload


@router.get("/api/v1/wave2/revision/tasks/{task_id}")
def get_task(
    task_id: str,
    service: RevisionLoopService = Depends(get_revision_loop_service),
) -> dict:
    """Task detail with preserved prompt + context."""
    try:
        task = service.get_task(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    payload = task.model_dump(mode="json")
    reject_normative_output(payload)
    return payload


@router.post(
    "/api/v1/wave2/revision/tasks/{task_id}/submissions", status_code=201,
)
def submit_v1(
    task_id: str,
    request: SubmitRequest,
    service: RevisionLoopService = Depends(get_revision_loop_service),
) -> dict:
    """Submit V1 through the existing Writing Intelligence pipeline."""
    try:
        version = service.submit_v1(
            task_id, request.essay_text,
            draft_stage=request.draft_stage, tool_use=request.tool_use,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    payload = version.model_dump(mode="json")
    reject_normative_output(payload)
    return payload


@router.post(
    "/api/v1/wave2/revision/tasks/{task_id}/submissions/"
    "{submission_id}/revisions",
    status_code=201,
)
def revise(
    task_id: str,
    submission_id: int,
    request: ReviseRequest,
    service: RevisionLoopService = Depends(get_revision_loop_service),
) -> dict:
    """Revise an existing version; a NEW version is persisted (append-only)."""
    try:
        version = service.revise(
            task_id, submission_id, request.essay_text,
            draft_stage=request.draft_stage, tool_use=request.tool_use,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    payload = version.model_dump(mode="json")
    reject_normative_output(payload)
    return payload


@router.get("/api/v1/wave2/revision/tasks/{task_id}/versions")
def version_history(
    task_id: str,
    service: RevisionLoopService = Depends(get_revision_loop_service),
) -> dict:
    """Version history with ancestry/timestamps/analysis/feedback links."""
    try:
        versions = service.version_history(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    payload = {
        "task_id": task_id,
        "versions": [version.model_dump(mode="json") for version in versions],
    }
    reject_normative_output(payload)
    return payload


@router.get(
    "/api/v1/wave2/revision/tasks/{task_id}/versions/"
    "{submission_id}/observation",
)
def revision_observation(
    task_id: str,
    submission_id: int,
    service: RevisionLoopService = Depends(get_revision_loop_service),
) -> dict:
    """Bounded observational comparison between the version and its parent."""
    try:
        observation = service.observe(task_id, submission_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    payload = observation.model_dump(mode="json")
    reject_normative_output(payload)
    return payload


@router.post("/api/v1/wave2/revision/submissions/{submission_id}/reanalysis")
def reanalysis(
    submission_id: int,
    service: RevisionLoopService = Depends(get_revision_loop_service),
) -> dict:
    """Re-enter the existing pipeline: real analyzer run + real feedback path."""
    try:
        result = service.reanalyze_submission(submission_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    payload = result.model_dump(mode="json")
    reject_normative_output(payload)
    return payload


__all__ = ["get_revision_loop_service", "reject_normative_output", "router"]
