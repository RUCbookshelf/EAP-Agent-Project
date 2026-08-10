"""Personalized feedback bridge v1 (Wave-2 Goal C).

Combines LOCAL observations (current submission), GLOBAL bounded whole-text
observations (basic organization observation only; discourse_organization
validated measurement NOT established) and HISTORICAL feedback grounded in
stored submissions (recurring / stable / reappeared / first_observed /
insufficient-history -- never fabricated for learners without stored
history) into a small actionable priority revision plan, plus a 7-level
progressive scaffold engine (default SCAFFOLD FIRST; helps the learner
revise, never replaces writing; scaffold history recorded) and LearningItem
v1 (durable learning target with full linkage; no FSRS; no practice/tutor).

All outputs are bounded and observation-only; nothing here states mastery,
proficiency, ability change, or learning outcomes as fact.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from app.l2.wave2.corpus_routing import CorpusRoutingProtocol
from app.l2.wave2.models import (
    GlobalObservationItem,
    HistoricalFeedbackItem,
    HistoricalFeedbackView,
    LearningItem,
    LearningItemStatus,
    LocalObservationItem,
    PriorityPlanItem,
    PriorityRevisionPlan,
    ScaffoldContent,
    ScaffoldEvent,
    ScaffoldResponse,
)
from app.l2.wave2.pipeline import WritingPipelinePort
from app.l2.wave2.repository import RevisionLoopRepository
from app.models.schemas import utc_now


OBSERVATION_ONLY_LIMITATION = (
    "Observations and plan items are descriptive; they do not establish "
    "ability change or learning outcomes."
)

HISTORY_LIMITATION = (
    "Historical feedback is derived from stored submissions and diagnoses; "
    "it is descriptive and never a validated measurement."
)

MIN_STABLE_ABSENT_SAMPLES = 2


def _sort_key(bundle: dict[str, Any]) -> tuple[str, int]:
    return (str(bundle.get("submitted_at") or ""), int(bundle["essay_id"]))


def _evidence_ref(submission_id: int) -> str:
    return f"E{submission_id:06d}"


class PersonalizedBridgeService:
    """Personalized feedback bridge over the revision-loop repository."""

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
        self.routing = routing
        self._now = now or utc_now

    # ------------------------------------------------------------------
    # Historical feedback (grounded in stored submissions)
    # ------------------------------------------------------------------

    def historical_feedback(self, learner_id: str) -> HistoricalFeedbackView:
        submissions = sorted(
            self.pipeline.list_student_submissions(learner_id), key=_sort_key,
        )
        if not submissions:
            return HistoricalFeedbackView(
                learner_id=learner_id,
                history_state="insufficient_history",
                items=[],
                history_reasons=["no stored submissions for this learner"],
                limitations=[
                    "No historical feedback can be derived; nothing was "
                    "fabricated or substituted.",
                    HISTORY_LIMITATION,
                ],
            )
        if len(submissions) < 2:
            insufficient = True
            history_reasons = [
                "no stored history beyond the current submission; fewer "
                "than 2 stored submissions, so recurrence cannot be "
                "established",
            ]
        else:
            insufficient = False
            history_reasons = []
        occurrences: dict[str, list[dict[str, Any]]] = {}
        for submission in submissions:
            submission_id = int(submission["essay_id"])
            for item in _diagnosis_items(submission):
                category = item["category"]
                occurrences.setdefault(category, []).append({
                    "submission_id": submission_id,
                    "evidence": item.get("evidence", ""),
                    "submitted_at": str(submission.get("submitted_at") or ""),
                    "context": str(submission.get("genre") or ""),
                    "revision_of": submission.get("revision_of_submission_id"),
                })
        items: list[HistoricalFeedbackItem] = []
        for category, records in sorted(occurrences.items()):
            items.append(self._historical_item(
                learner_id, category, records, submissions,
            ))
        if not items:
            return HistoricalFeedbackView(
                learner_id=learner_id,
                history_state="insufficient_history",
                items=[],
                history_reasons=[
                    "stored submissions exist but no improvement-priority "
                    "category is available to report",
                ],
                limitations=[HISTORY_LIMITATION],
            )
        return HistoricalFeedbackView(
            learner_id=learner_id,
            history_state=(
                "insufficient_history" if insufficient else "sufficient"
            ),
            items=items,
            history_reasons=history_reasons,
            limitations=[HISTORY_LIMITATION],
        )

    def _historical_item(
        self,
        learner_id: str,
        category: str,
        records: list[dict[str, Any]],
        submissions: list[dict[str, Any]],
    ) -> HistoricalFeedbackItem:
        records = sorted(records, key=lambda record: record["submitted_at"])
        submission_ids = [record["submission_id"] for record in records]
        contexts = list(dict.fromkeys(record["context"] for record in records))
        first_observed_at = records[0]["submitted_at"]
        last_observed_at = records[-1]["submitted_at"]
        count = len(records)
        category_ids = {record["submission_id"] for record in records}

        later_absent = [
            submission for submission in submissions
            if int(submission["essay_id"]) > submission_ids[-1]
            and category not in _diagnosis_categories_of(submission)
        ]
        absent_after_last = len(later_absent)

        gap_detected = False
        for left, right in zip(records, records[1:]):
            between = [
                submission for submission in submissions
                if left["submission_id"] < int(submission["essay_id"]) < right["submission_id"]
            ]
            if between and all(
                category not in _diagnosis_categories_of(submission)
                for submission in between
            ):
                gap_detected = True
                break

        if count >= 2 and gap_detected:
            status = "reappeared"
            state, reasons = "sufficient", []
        elif count >= 2:
            status = "recurring"
            state, reasons = "sufficient", []
        elif absent_after_last >= MIN_STABLE_ABSENT_SAMPLES:
            status = "stable"
            state, reasons = "sufficient", []
        else:
            status = "first_observed"
            state, reasons = "sufficient", [
                "single occurrence; recurring or stable status cannot be "
                "established from stored evidence",
            ]

        revision_success_note = self._revision_success_note(
            category, records, submissions, category_ids,
        )
        limitations = [HISTORY_LIMITATION]
        if len(contexts) > 1:
            limitations.append(
                "occurrences span different task contexts; recurrence is "
                "descriptive only"
            )
        if status == "first_observed" and absent_after_last == 1:
            limitations.append(
                "only one later sample is stored; stability cannot be "
                "established"
            )
        return HistoricalFeedbackItem(
            learner_id=learner_id,
            category=category,
            status=status,
            occurrence_count=count,
            first_observed_at=first_observed_at,
            last_observed_at=last_observed_at,
            supporting_submission_ids=submission_ids,
            evidence_refs=[_evidence_ref(submission_id) for submission_id in submission_ids],
            contexts=contexts,
            revision_success_note=revision_success_note,
            history_state=state,
            history_reasons=reasons,
            limitations=limitations,
            claims_status="observation_only",
        )

    @staticmethod
    def _revision_success_note(
        category: str,
        records: list[dict[str, Any]],
        submissions: list[dict[str, Any]],
        category_submission_ids: set[int],
    ) -> str | None:
        revision_targets = {
            int(submission["revision_of_submission_id"])
            for submission in submissions
            if submission.get("revision_of_submission_id") is not None
        }
        if not (category_submission_ids & revision_targets):
            return None
        latest_submission = submissions[-1]
        latest_has = category in _diagnosis_categories_of(latest_submission)
        if latest_has:
            return (
                "previously addressed in a revision; observed again in the "
                "latest submission"
            )
        return (
            "previously addressed in a revision; not observed in the latest "
            "submission"
        )

    # ------------------------------------------------------------------
    # Priority revision plan
    # ------------------------------------------------------------------

    def build_priority_plan(
        self, learner_id: str, task_id: str, submission_id: int,
    ) -> PriorityRevisionPlan:
        task = self.repository.get_writing_task(task_id)
        if task is None:
            raise LookupError(f"Writing task not found: {task_id}")
        bundle = self.pipeline.get_submission_bundle(submission_id)
        if bundle is None:
            raise LookupError(f"Submission not found: {submission_id}")
        if bundle.get("student_id") != learner_id:
            raise ValueError(
                "The submission does not belong to the requested learner."
            )

        local_observations = self._local_observations(bundle)
        global_observations = self._global_observations(learner_id, bundle)
        historical = self.historical_feedback(learner_id)
        historical_by_category = {
            item.category: item for item in historical.items
        }

        current_priorities = _diagnosis_items(bundle)
        plan_items: list[PriorityPlanItem] = []
        for index, priority in enumerate(current_priorities):
            category = priority["category"]
            history_item = historical_by_category.get(category)
            if history_item is not None:
                recurrence_status = history_item.status
                evidence_refs = [
                    *_evidence_refs_for(history_item),
                    _evidence_ref(submission_id),
                ]
                limitations = list(history_item.limitations)
                if history_item.revision_success_note:
                    limitations.append(
                        f"revision evidence: {history_item.revision_success_note}"
                    )
            else:
                recurrence_status = "first_observed"
                evidence_refs = [_evidence_ref(submission_id)]
                limitations = [
                    "no stored history for this area; the plan item is based "
                    "on the current submission only",
                ]
            plan_items.append(PriorityPlanItem(
                plan_item_id=f"PI{index + 1:02d}",
                category=category,
                diagnosis_id=priority.get("diagnosis_id"),
                recurrence_status=recurrence_status,
                context={
                    "task_type": task.task_type,
                    "writing_context": task.writing_context,
                },
                action_statement=self._action_statement(bundle, category),
                evidence_refs=list(dict.fromkeys(evidence_refs)),
                confidence=priority.get("confidence", "low"),
                limitations=limitations,
            ))

        priority_order = {"reappeared": 0, "recurring": 1, "first_observed": 2}
        plan_items.sort(key=lambda item: priority_order.get(item.recurrence_status, 3))
        plan_items = plan_items[:3]

        if historical.history_state == "sufficient" and historical.items:
            history_state = "sufficient"
            history_reasons: list[str] = []
            limitations = [OBSERVATION_ONLY_LIMITATION]
            historical_feedback = historical.items
        else:
            history_state = "insufficient_history"
            history_reasons = list(historical.history_reasons)
            historical_feedback: list[HistoricalFeedbackItem] = []
            limitations = [
                OBSERVATION_ONLY_LIMITATION,
                "No sufficient stored history exists for this learner; the plan is based "
                "on the current submission only and nothing was fabricated.",
            ]
        if not current_priorities:
            limitations.append(
                "No improvement-priority area was selected for the current "
                "submission; the plan contains no actionable item."
            )

        plan = PriorityRevisionPlan(
            plan_id="PP-PENDING",
            learner_id=learner_id,
            task_id=task_id,
            submission_id=submission_id,
            generated_at=self._now(),
            items=plan_items,
            history_state=history_state,
            history_reasons=history_reasons,
            local_observations=local_observations,
            global_observations=global_observations,
            historical_feedback=historical_feedback,
            limitations=limitations,
            claims_status="observation_only",
        )
        self.repository.save_priority_plan(plan)
        return plan

    @staticmethod
    def _local_observations(bundle: dict[str, Any]) -> list[LocalObservationItem]:
        metrics = bundle.get("metrics") or {}
        items: list[LocalObservationItem] = []
        for feature_id, label in (
            ("word_count", "word count"),
            ("average_sentence_length", "average sentence length"),
            ("type_token_ratio", "type-token ratio"),
            ("connective_count", "listed connective count"),
            ("paragraph_count", "paragraph count"),
        ):
            value = metrics.get(feature_id)
            if value is None:
                items.append(LocalObservationItem(
                    feature_id=feature_id,
                    value=None,
                    available=False,
                    statement=f"The {label} of the current draft is unavailable.",
                    limitation="Metric was not produced for the current draft.",
                ))
                continue
            if feature_id == "paragraph_count":
                statement = (
                    f"The current draft contains {value} paragraph(s). This is "
                    "a basic organization observation only."
                )
                limitation = (
                    "basic organization observation only; discourse_organization "
                    "validated measurement NOT established"
                )
            else:
                statement = f"The current draft {label} is {value}."
                limitation = (
                    "Surface-form observation from the stored analysis; not a "
                    "quality or ability judgment."
                )
            items.append(LocalObservationItem(
                feature_id=feature_id, value=value, available=True,
                statement=statement, limitation=limitation,
            ))
        return items

    def _global_observations(
        self, learner_id: str, bundle: dict[str, Any],
    ) -> list[GlobalObservationItem]:
        submissions = sorted(
            self.pipeline.list_student_submissions(learner_id), key=_sort_key,
        )
        samples = submissions or [bundle]
        word_counts = [
            (item.get("metrics") or {}).get("word_count")
            for item in samples
        ]
        ttrs = [
            (item.get("metrics") or {}).get("type_token_ratio")
            for item in samples
        ]
        connectives = [
            (item.get("metrics") or {}).get("connective_count")
            for item in samples
        ]
        numeric = [value for value in word_counts if isinstance(value, (int, float))]
        numeric_ttr = [value for value in ttrs if isinstance(value, (int, float))]
        numeric_conn = [value for value in connectives if isinstance(value, (int, float))]
        sample_count = len(samples)
        observations: list[GlobalObservationItem] = [
            GlobalObservationItem(
                observation_id="GO-001",
                scope="whole_text",
                kind="text_length",
                value=round(sum(numeric) / len(numeric), 1) if numeric else None,
                descriptive_statement=(
                    f"Mean word count across {sample_count} stored submission(s) "
                    f"is {round(sum(numeric) / len(numeric), 1) if numeric else 'unavailable'}."
                ),
                limitation="Descriptive whole-text length observation; not a "
                           "quality or ability judgment.",
            ),
            GlobalObservationItem(
                observation_id="GO-002",
                scope="whole_text",
                kind="lexical_diversity",
                value=round(sum(numeric_ttr) / len(numeric_ttr), 3) if numeric_ttr else None,
                descriptive_statement=(
                    f"Mean surface type-token ratio across {sample_count} stored "
                    "submission(s); descriptive only."
                ),
                limitation="Surface-form diversity observation; not a validated "
                           "measurement.",
            ),
            GlobalObservationItem(
                observation_id="GO-003",
                scope="whole_text",
                kind="connective_density",
                value=round(sum(numeric_conn) / len(numeric_conn), 2) if numeric_conn else None,
                descriptive_statement=(
                    f"Mean listed-connective count across {sample_count} stored "
                    "submission(s); descriptive only."
                ),
                limitation="Dictionary-listed connectives only; cohesion is not "
                           "measured.",
            ),
            GlobalObservationItem(
                observation_id="GO-004",
                scope="whole_text",
                kind="basic_organization",
                value=(bundle.get("metrics") or {}).get("paragraph_count"),
                descriptive_statement=(
                    "The current draft's paragraph structure is observable; "
                    "organization is described at a basic level only."
                ),
                limitation=(
                    "basic organization observation only; discourse_organization "
                    "validated measurement NOT established"
                ),
            ),
        ]
        return observations

    @staticmethod
    def _action_statement(bundle: dict[str, Any], category: str) -> str:
        for item in (bundle.get("feedback") or {}).get("priority_feedback", []):
            if item.get("category") == category and item.get("revision_guidance"):
                return item["revision_guidance"]
        return (
            f"Review the '{category}' area in the current draft and try one "
            "focused revision of a single passage."
        )

    # ------------------------------------------------------------------
    # Progressive scaffold (7 levels, SCAFFOLD FIRST)
    # ------------------------------------------------------------------

    def request_scaffold(
        self,
        learner_id: str,
        *,
        plan_item_id: str | None = None,
        learning_item_id: str | None = None,
        category: str | None = None,
        evidence: str | None = None,
        level: int | None = None,
    ) -> ScaffoldResponse:
        resolved_category: str
        resolved_evidence = evidence or ""
        plan_item: PriorityPlanItem | None = None
        if plan_item_id is not None:
            plan_item, resolved_category, resolved_evidence = (
                self._resolve_plan_item(learner_id, plan_item_id)
            )
        elif learning_item_id is not None:
            item = self.repository.get_learning_item(learning_item_id)
            if item is None:
                raise LookupError(f"Learning item not found: {learning_item_id}")
            resolved_category = item.category
            resolved_evidence = evidence or ""
        elif category is not None:
            resolved_category = category
        else:
            raise ValueError(
                "One of plan_item_id, learning_item_id, or category is required."
            )

        requested_level = level if level is not None else 1
        if not 1 <= requested_level <= 7:
            raise ValueError("Scaffold level must be between 1 and 7.")
        content = scaffold_content(resolved_category, resolved_evidence, requested_level)
        learner_action = (
            "The learner writes the revised text; the scaffold only guides "
            "the revision."
        )
        never_writes = (
            "The scaffold helps you revise; it never writes your essay for you."
        )
        event = ScaffoldEvent(
            scaffold_event_id="SE-PENDING",
            learner_id=learner_id,
            learning_item_id=learning_item_id,
            plan_item_id=plan_item_id,
            category=resolved_category,
            level=requested_level,
            requested_at=self._now(),
            default_first=requested_level == 1,
            limitations=[],
        )
        self.repository.save_scaffold_event(event)
        return ScaffoldResponse(
            learner_id=learner_id,
            category=resolved_category,
            level=requested_level,
            default_first=requested_level == 1,
            available_levels=list(range(1, 8)),
            content=content,
            learner_action=learner_action,
            never_writes_statement=never_writes,
            limitations=[
                "Scaffolds are deterministic revision prompts; they do not "
                "measure the learner or predict outcomes.",
            ],
        )

    def _resolve_plan_item(
        self, learner_id: str, plan_item_id: str,
    ) -> tuple[PriorityPlanItem, str, str]:
        for plan in self.repository.list_priority_plans(learner_id):
            for item in plan.items:
                if item.plan_item_id == plan_item_id:
                    evidence = (
                        "; ".join(item.evidence_refs)
                    )
                    return item, item.category, evidence
        raise LookupError(f"Priority plan item not found: {plan_item_id}")

    # ------------------------------------------------------------------
    # LearningItem v1
    # ------------------------------------------------------------------

    def create_learning_item(
        self, learner_id: str, plan_item_id: str,
    ) -> LearningItem:
        plan_item, category, _ = self._resolve_plan_item(learner_id, plan_item_id)
        plans = [
            plan for plan in self.repository.list_priority_plans(learner_id)
            if any(item.plan_item_id == plan_item_id for item in plan.items)
        ]
        plan = plans[0]
        bundle = self.pipeline.get_submission_bundle(plan.submission_id)
        revision_history = [
            {
                "version_number": version.version_number,
                "submission_id": version.submission_id,
                "revision_of_submission_id": version.revision_of_submission_id,
            }
            for version in self.repository.list_submission_versions(plan.task_id)
        ]
        item = LearningItem(
            learning_item_id="LI-PENDING",
            student_id=learner_id,
            category=category,
            originating_evidence={
                "submission_ids": [plan.submission_id],
                "diagnosis_ids": (
                    [plan_item.diagnosis_id] if plan_item.diagnosis_id else []
                ),
                "categories": [category],
                "evidence_refs": plan_item.evidence_refs,
            },
            feedback_reference=(
                f"feedback:{bundle.get('feedback_id')}" if bundle is not None else None
            ),
            revision_history=revision_history,
            task_id=plan.task_id,
            task_context=plan_item.context,
            status="proposed",
            created_at=self._now(),
            updated_at=self._now(),
            limitations=[
                "LearningItem v1 is a durable learning target with provenance "
                "links; it does not measure the learner or predict outcomes.",
            ],
        )
        return self.repository.save_learning_item(item)

    def list_learning_items(
        self, student_id: str, status: LearningItemStatus | None = None,
    ) -> list[LearningItem]:
        return self.repository.list_learning_items(student_id, status=status)

    def update_learning_item_status(
        self, learning_item_id: str, status: LearningItemStatus,
    ) -> LearningItem:
        updated = self.repository.update_learning_item_status(
            learning_item_id, status, self._now(),
        )
        if updated is None:
            raise LookupError(f"Learning item not found: {learning_item_id}")
        return updated


# ---------------------------------------------------------------------------
# Deterministic scaffold templates (7 levels; SCAFFOLD FIRST)
# ---------------------------------------------------------------------------

_STARTERS = {
    "essay_length": ("One important reason is that ...", "Another example is ..."),
    "lexical_repetition": (
        "Instead of repeating this word, try ...",
        "A more specific alternative here is ...",
    ),
    "connective_use": ("However, ...", "Therefore, ...", "For example, ..."),
    "sentence_length_pattern": (
        "The long part could become: ...",
        "Combine the two short parts with: ...",
    ),
    "sentence_structure_candidate": (
        "One clearer frame is: ...",
        "The main point could come first: ...",
    ),
}

_FRAMES = {
    "essay_length": (
        "The draft would become more complete if one ______ directly "
        "answered the prompt."
    ),
    "lexical_repetition": (
        "The repeated word appears ______ times; replace one occurrence "
        "with ______."
    ),
    "connective_use": (
        "Between these two ideas, the missing logical link is ______."
    ),
    "sentence_length_pattern": (
        "The sentence could be split after ______ so the reader can pause."
    ),
}

_DEFAULT_STARTERS = ("One way to revise this is ...", "Try writing: ...")
_DEFAULT_FRAME = "A clearer version of this passage would add ______."


def scaffold_content(
    category: str, evidence: str, level: int,
) -> ScaffoldContent:
    """Deterministic scaffold content for one level (bounded, non-normative)."""
    quote = (evidence or "").strip()[:180]
    kinds: dict[int, str] = {
        1: "focus",
        2: "guiding_question",
        3: "sentence_starter",
        4: "fill_in_blank",
        5: "model_fragment",
        6: "self_check",
        7: "worked_example",
    }
    if level == 1:
        text = (
            f"The flagged area is '{category}'. Look at your draft and "
            "choose one sentence to revise first. You write the revision."
        )
    elif level == 2:
        text = (
            f"Look at the flagged passage: '{quote}'. What is this passage "
            "trying to say, and what does the reader need that is missing?"
        )
    elif level == 3:
        starters = _STARTERS.get(category, _DEFAULT_STARTERS)
        text = (
            "Try starting the revised sentence with one of these frames: "
            + " ".join(starters)
            + " You finish the sentence yourself."
        )
    elif level == 4:
        frame = _FRAMES.get(category, _DEFAULT_FRAME)
        text = f"Complete this frame in your own words: {frame}"
    elif level == 5:
        text = (
            f"Here is a short phrase you can adapt (not your final sentence): "
            f"'{quote[:90]}' -- rewrite it in your own words."
        )
    elif level == 6:
        text = (
            "Self-check before you finish: (1) Does the revised passage "
            "answer the prompt? (2) Is the meaning clearer than before? "
            "(3) Did you keep your own voice? (4) Read it aloud once."
        )
    else:
        text = (
            f"Example: '{quote}' could be revised to: '{_example_revision(category, quote)}'. "
            "Use this only as a model, then write your own version."
        )
    return ScaffoldContent(level=level, kind=kinds[level], text=text)


def _example_revision(category: str, quote: str) -> str:
    if category == "connective_use":
        return "However, the same benefit can also bring new costs."
    if category == "essay_length":
        return "One clear reason is that green spaces improve daily health."
    if category == "lexical_repetition":
        return "The same idea appears again, but with a different expression."
    if category == "sentence_length_pattern":
        return "The long sentence was split. Each part is now easier to follow."
    return "The revised sentence states the main point more directly."


def _diagnosis_items(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item for item in
        (bundle.get("diagnosis") or {}).get("improvement_priorities", [])
        if item.get("category")
    ]


def _diagnosis_categories_of(bundle: dict[str, Any]) -> set[str]:
    return {item["category"] for item in _diagnosis_items(bundle)}


def _evidence_refs_for(item: HistoricalFeedbackItem) -> list[str]:
    return list(item.evidence_refs)


__all__ = [
    "HISTORY_LIMITATION",
    "MIN_STABLE_ABSENT_SAMPLES",
    "OBSERVATION_ONLY_LIMITATION",
    "PersonalizedBridgeService",
    "scaffold_content",
]
