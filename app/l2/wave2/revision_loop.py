"""Context-aware revision loop v1 (Wave-2 Goal C).

WritingTask -> Submission V1 -> V2 -> V3 with ancestry, timestamps and
task-context/analysis/feedback links. Every submission and revision runs
through the EXISTING Writing Intelligence pipeline (``WritingPipelinePort``
backed by the composition-root services); a revision NEVER overwrites prior
submissions -- historical versions are evidence. Revision observations are
bounded and observational: what changed, which feedback areas appear
addressed/remaining, new observations, and apparent independent corrections
-- with NO intent inference.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Callable

from app.l2.wave2.corpus_routing import (
    CorpusRoutingProtocol,
    CorpusRoutingResult,
    LocalWrittenCorpusRouter,
    WrittenCorpusRoutingRequest,
)
from app.l2.wave2.models import (
    LEGACY_UNCLASSIFIED,
    RevisionObservation,
    SubmissionVersion,
    WritingTask,
    WritingTaskMetadata,
)
from app.l2.wave2.pipeline import (
    ReanalysisResult,
    WritingPipelinePort,
    essay_text_hash,
)
from app.l2.wave2.repository import RevisionLoopRepository
from app.models import EssaySubmission
from app.models.schemas import utc_now
from app.services.task_type_classifier import (
    TaskTypeClassificationError,
    classify_task_definition,
)


NO_INTENT_INFERENCE = (
    "Observations describe observed text changes; they do not infer the "
    "learner's intent, ability, or learning outcomes."
)


def _value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _diagnosis_categories(bundle: dict | None) -> list[dict[str, Any]]:
    if not bundle:
        return []
    return [
        item for item in
        (bundle.get("diagnosis") or {}).get("improvement_priorities", [])
        if item.get("category")
    ]


def _feedback_items(bundle: dict | None) -> list[dict[str, Any]]:
    if not bundle:
        return []
    return [
        item for item in
        (bundle.get("feedback") or {}).get("priority_feedback", [])
        if item.get("category")
    ]


def _token_diff(source_text: str, target_text: str) -> dict[str, Any]:
    source_tokens = [token for token in source_text.split() if token]
    target_tokens = [token for token in target_text.split() if token]
    source_counts = Counter(token.casefold() for token in source_tokens)
    target_counts = Counter(token.casefold() for token in target_tokens)
    inserted = sum((target_counts - source_counts).values())
    deleted = sum((source_counts - target_counts).values())
    return {
        "source_tokens": len(source_tokens),
        "target_tokens": len(target_tokens),
        "inserted_tokens": inserted,
        "deleted_tokens": deleted,
        "changed_ratio": round(
            (inserted + deleted) / max(1, len(source_tokens)), 4
        ),
    }


def build_revision_observation(
    source_bundle: dict[str, Any],
    target_bundle: dict[str, Any],
    source_version: Any,
    target_version: Any,
    *,
    now: Callable[[], datetime] | None = None,
) -> RevisionObservation:
    """Build one bounded, observational revision comparison."""
    now_fn = now or utc_now
    source_text = source_bundle.get("essay_text") or ""
    target_text = target_bundle.get("essay_text") or ""
    what_changed = _token_diff(source_text, target_text)
    source_categories = _diagnosis_categories(source_bundle)
    target_categories = _diagnosis_categories(target_bundle)
    source_category_ids = {item["category"] for item in source_categories}
    target_category_ids = {item["category"] for item in target_categories}

    feedback_areas: list[dict[str, Any]] = []
    for item in _feedback_items(source_bundle):
        category = item["category"]
        if category in target_category_ids:
            status = "appears_remaining"
            target_evidence = next(
                (candidate["evidence"] for candidate in target_categories
                 if candidate["category"] == category), "",
            )
            observed_note = f"The prior feedback area is still observed in the target version: {target_evidence}"
        else:
            status = "appears_addressed"
            observed_note = (
                "The prior feedback area is not currently observed in the "
                "target version's diagnosis; absence in one version is not "
                "evidence of being solved."
            )
        feedback_areas.append({
            "category": category,
            "diagnosis_id": item.get("diagnosis_id"),
            "prior_guidance": item.get("revision_guidance", ""),
            "status": status,
            "observed_note": observed_note,
        })

    new_observations: list[dict[str, Any]] = [
        {
            "category": item["category"],
            "evidence": item.get("evidence", ""),
            "note": "This area is newly observed in the target version and was "
                    "not present in the prior version's diagnosis.",
        }
        for item in target_categories
        if item["category"] not in source_category_ids
    ]

    feedback_category_ids = {item["category"] for item in _feedback_items(source_bundle)}
    apparent_independent_corrections: list[dict[str, Any]] = [
        {
            "category": category,
            "note": "This area changed and is no longer observed in the target "
                    "version, but it was not among the previously provided "
                    "feedback priorities; the change is observed, its cause "
                    "is not inferred.",
        }
        for category in sorted(source_category_ids - feedback_category_ids - target_category_ids)
    ]

    task_id = _value(target_version, "task_id", "")
    return RevisionObservation(
        observation_id=f"RO-{_value(source_version, 'submission_id')}-{_value(target_version, 'submission_id')}",
        task_id=task_id,
        source_submission_id=int(_value(source_version, "submission_id")),
        target_submission_id=int(_value(target_version, "submission_id")),
        observed_at=now_fn(),
        what_changed=what_changed,
        feedback_areas=feedback_areas,
        new_observations=new_observations,
        apparent_independent_corrections=apparent_independent_corrections,
        no_intent_inference=NO_INTENT_INFERENCE,
        limitations=[
            "Feedback-area statuses describe observable diagnosis presence "
            "across versions; they do not infer that the revision followed "
            "the feedback.",
            "A single-version absence is not evidence that an area was "
            "solved or that learning occurred.",
        ],
    )


class RevisionLoopService:
    """Application service for the context-aware revision loop."""

    def __init__(
        self,
        *,
        repository: RevisionLoopRepository,
        pipeline: WritingPipelinePort,
        routing: CorpusRoutingProtocol | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.pipeline = pipeline
        self.routing = routing or LocalWrittenCorpusRouter()
        self._now = now or utc_now

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    def create_task(
        self,
        *,
        student_id: str,
        task_type: str,
        writing_context: str,
        writing_prompt: str,
        metadata: WritingTaskMetadata | None = None,
        declared_task_type: str | None = None,
    ) -> WritingTask:
        classification: dict[str, Any] = {}
        if task_type != LEGACY_UNCLASSIFIED:
            try:
                result = classify_task_definition(
                    writing_prompt, declared_task_type=declared_task_type,
                )
            except TaskTypeClassificationError as exc:
                raise ValueError(str(exc)) from exc
            classification = {
                "outcome": result.outcome,
                "task_type": result.task_type,
                "reason_code": result.reason_code,
                "taxonomy_version": result.taxonomy_version,
                "dictionary_version": result.dictionary_version,
            }
        task = WritingTask(
            task_id="WT-PENDING",
            student_id=student_id,
            task_type=task_type,
            writing_context=writing_context,
            writing_prompt=writing_prompt,
            metadata=metadata or WritingTaskMetadata(),
            classification=classification,
            created_at=self._now(),
            limitations=[
                "Task metadata is routing/context metadata only; it never "
                "measures the learner.",
            ],
        )
        return self.repository.save_writing_task(task)

    def get_task(self, task_id: str) -> WritingTask:
        task = self.repository.get_writing_task(task_id)
        if task is None:
            raise LookupError(f"Writing task not found: {task_id}")
        return task

    # ------------------------------------------------------------------
    # Submissions and revisions (append-only; through the real pipeline)
    # ------------------------------------------------------------------

    def submit_v1(
        self,
        task_id: str,
        essay_text: str,
        *,
        draft_stage: str = "first draft",
        tool_use: str = "none",
    ) -> SubmissionVersion:
        task = self.get_task(task_id)
        submission = EssaySubmission(
            student_id=task.student_id,
            writing_prompt=task.writing_prompt,
            genre=task.writing_context,
            draft_stage=draft_stage,
            tool_use=tool_use,
            essay_text=essay_text,
        )
        result = self.pipeline.submit(submission)
        bundle = self.pipeline.get_submission_bundle(result["essay_id"])
        version = SubmissionVersion(
            task_id=task_id,
            submission_id=result["essay_id"],
            version_number=1,
            revision_of_submission_id=None,
            ancestry=[result["essay_id"]],
            submitted_at=self._now(),
            task_context=self._task_context(task),
            essay_text_hash=essay_text_hash(essay_text),
            draft_stage=draft_stage,
            analysis_run_id=result["analysis_run_id"],
            analysis_version=result["analysis_version"],
            feedback_record_id=(
                bundle.get("feedback_id") if bundle is not None else None
            ),
            corpus_routing=self._route(task).model_dump(mode="json"),
            limitations=[
                "Versions are append-only; prior submissions are preserved "
                "as evidence.",
            ],
        )
        return self.repository.save_submission_version(version)

    def revise(
        self,
        task_id: str,
        revision_of_submission_id: int,
        essay_text: str,
        *,
        draft_stage: str = "revised draft",
        tool_use: str = "none",
    ) -> SubmissionVersion:
        task = self.get_task(task_id)
        source = self.repository.get_submission_version(
            task_id, revision_of_submission_id,
        )
        if source is None:
            raise LookupError(
                f"Source submission {revision_of_submission_id} is not a "
                f"version of task {task_id}."
            )
        submission = EssaySubmission(
            student_id=task.student_id,
            writing_prompt=task.writing_prompt,
            genre=task.writing_context,
            draft_stage=draft_stage,
            tool_use=tool_use,
            essay_text=essay_text,
            revision_of_submission_id=revision_of_submission_id,
        )
        result = self.pipeline.submit(submission)
        bundle = self.pipeline.get_submission_bundle(result["essay_id"])
        versions = self.repository.list_submission_versions(task_id)
        version_number = max(
            (version.version_number for version in versions), default=0,
        ) + 1
        version = SubmissionVersion(
            task_id=task_id,
            submission_id=result["essay_id"],
            version_number=version_number,
            revision_of_submission_id=revision_of_submission_id,
            ancestry=[*source.ancestry, result["essay_id"]],
            submitted_at=self._now(),
            task_context=self._task_context(task),
            essay_text_hash=essay_text_hash(essay_text),
            draft_stage=draft_stage,
            analysis_run_id=result["analysis_run_id"],
            analysis_version=result["analysis_version"],
            feedback_record_id=(
                bundle.get("feedback_id") if bundle is not None else None
            ),
            revision_group_id=result["revision_group_id"],
            revision_snapshot_id=result["revision_snapshot_id"],
            corpus_routing=self._route(task).model_dump(mode="json"),
            limitations=[
                "Versions are append-only; prior submissions are preserved "
                "as evidence.",
            ],
        )
        return self.repository.save_submission_version(version)

    def version_history(self, task_id: str) -> list[SubmissionVersion]:
        self.get_task(task_id)
        return self.repository.list_submission_versions(task_id)

    def get_version(self, task_id: str, submission_id: int) -> SubmissionVersion:
        version = self.repository.get_submission_version(task_id, submission_id)
        if version is None:
            raise LookupError(
                f"Submission {submission_id} is not a version of task {task_id}."
            )
        return version

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    def observe(self, task_id: str, submission_id: int) -> RevisionObservation:
        target = self.get_version(task_id, submission_id)
        if target.revision_of_submission_id is None:
            raise ValueError("V1 has no prior version to observe against.")
        source = self.repository.get_submission_version(
            task_id, target.revision_of_submission_id,
        )
        if source is None:
            raise LookupError("Prior version not found for observation.")
        source_bundle = self.pipeline.get_submission_bundle(
            source.submission_id,
        )
        target_bundle = self.pipeline.get_submission_bundle(
            target.submission_id,
        )
        if source_bundle is None or target_bundle is None:
            raise LookupError("Stored submission evidence is unavailable.")
        observation = build_revision_observation(
            source_bundle, target_bundle, source, target, now=self._now,
        )
        self.repository.save_revision_observation(observation)
        return observation

    # ------------------------------------------------------------------
    # Reanalysis through the existing pipeline
    # ------------------------------------------------------------------

    def reanalyze(self, task_id: str, submission_id: int) -> ReanalysisResult:
        version = self.get_version(task_id, submission_id)
        result = self.pipeline.reanalyze(submission_id)
        events = [
            *version.reanalysis_events,
            {
                "analysis_run_id": result.analysis_run_id,
                "analysis_version": result.analysis_version,
                "feedback_record_id": result.feedback_record_id,
                "reanalyzed_at": result.reanalyzed_at.isoformat(),
            },
        ]
        updated = version.model_copy(update={
            "analysis_run_id": result.analysis_run_id,
            "analysis_version": result.analysis_version,
            "feedback_record_id": result.feedback_record_id,
            "reanalysis_events": events,
        })
        self.repository.save_submission_version(updated)
        return result

    def reanalyze_submission(self, submission_id: int) -> ReanalysisResult:
        """Reanalyze a submission without naming its task up front."""
        task_id = self.repository.find_task_id_for_submission(submission_id)
        if task_id is None:
            raise LookupError(
                f"Submission {submission_id} is not a version of any task."
            )
        return self.reanalyze(task_id, submission_id)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _task_context(self, task: WritingTask) -> dict[str, Any]:
        return {
            "task_type": task.task_type,
            "writing_context": task.writing_context,
            "writing_prompt": task.writing_prompt,
            "metadata": task.metadata.model_dump(mode="json"),
            "modality": task.modality,
        }

    def _route(self, task: WritingTask) -> CorpusRoutingResult:
        if task.task_type == LEGACY_UNCLASSIFIED:
            return CorpusRoutingResult(
                routed=False,
                modality=task.modality,
                corpus_package_id="",
                unmatched_reason=(
                    "legacy_unclassified task types carry no routing "
                    "semantics; no reference resource was selected"
                ),
            )
        return self.routing.route(WrittenCorpusRoutingRequest(
            task_type=task.task_type,
            writing_context=task.writing_context,
            writing_prompt=task.writing_prompt,
            modality=task.modality,
        ))


__all__ = [
    "NO_INTENT_INFERENCE",
    "RevisionLoopService",
    "build_revision_observation",
]
