"""MiniWritingService: bounded mini-writing through the EXISTING pipeline.

Mini-writing is learner-supplied short text submitted through the existing
Writing Intelligence pipeline (``RevisionLoopService`` + the wave2
``WritingPipelinePort``); no disconnected analysis or essay-generation
service exists here. The pipeline analyzes the learner text; the service
never generates an essay. Bounded length is enforced before any submission.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from app.l2.wave2.revision_loop import RevisionLoopService
from app.l2.wave3.models import MiniWritingResult, OBSERVATION_ONLY
from app.models.schemas import utc_now


PIPELINE_ADAPTER = "writing-intelligence-pipeline-v0.9.7"
MAX_MINI_WRITING_LENGTH = 600


class MiniWritingService:
    """Bounded mini-writing re-entering the existing pipeline."""

    def __init__(
        self,
        *,
        revision_loop: RevisionLoopService,
        now: Callable[[], datetime] | None = None,
        max_length: int = MAX_MINI_WRITING_LENGTH,
    ) -> None:
        self.revision_loop = revision_loop
        self._now = now or utc_now
        self.max_length = max_length

    def submit(
        self, learner_id: str, task_id: str, text: str,
    ) -> MiniWritingResult:
        task = self.revision_loop.get_task(task_id)
        if task.student_id != learner_id:
            raise LookupError(
                f"Task {task_id} does not belong to learner {learner_id}."
            )
        stripped = text.strip()
        if not stripped:
            raise ValueError("Mini-writing text must not be blank.")
        if len(stripped) > self.max_length:
            raise ValueError(
                f"Mini-writing exceeds the bounded length of {self.max_length} "
                "characters."
            )
        version = self.revision_loop.submit_v1(
            task_id, stripped, draft_stage="mini-writing",
        )
        return MiniWritingResult(
            result_id=self._result_id(learner_id, version.submission_id),
            learner_id=learner_id,
            task_id=task_id,
            submission_id=version.submission_id,
            analysis_run_id=version.analysis_run_id or "",
            analysis_version=version.analysis_version or "",
            feedback_record_id=version.feedback_record_id,
            essay_text_hash=version.essay_text_hash,
            word_count=len(stripped.split()),
            pipeline_adapter=PIPELINE_ADAPTER,
            bounded=True,
            limitations=[
                "Mini-writing is learner text analyzed by the existing "
                "pipeline; it is descriptive only and does not establish "
                "outcomes.",
            ],
            claims_status=OBSERVATION_ONLY,
        )

    @staticmethod
    def _result_id(learner_id: str, submission_id: int) -> str:
        return f"MW-{learner_id}-{submission_id:06d}"


__all__ = ["MAX_MINI_WRITING_LENGTH", "MiniWritingService", "PIPELINE_ADAPTER"]
