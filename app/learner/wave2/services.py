"""Longitudinal Learner Model v1 -- service (Goal PDW2-B-LEARNER-MODEL).

All outputs are bounded, observation-only, non-normative views. Where the
available history cannot support a statement, the output carries an explicit
``HistoryState.INSUFFICIENT_HISTORY`` with human-readable reasons. Revision
behavior states describe what was observed across revisions; they never
state ability change, mastery, proficiency, or learning gain.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from app.learner.evidence import (
    EvidenceAdmissionStatus,
    ObservedEvidence,
    check_provenance_completeness,
)
from app.learner.wave2.models import (
    DEFAULT_ANCHOR_STATEMENT,
    EvidenceList,
    HistoryState,
    LearnerEvidenceRecord,
    ObservationListView,
    ObservationRecord,
    ObservationStatusView,
    ObservationType,
    OccurrenceEntry,
    ProficiencyContext,
    ProficiencyContextView,
    QualifiedFrequency,
    RecurringDifficulty,
    RecurringDifficultyList,
    RevisionBehavior,
    RevisionResponseState,
    StabilityKind,
    StableList,
    StableObservation,
    StrengthList,
    StrengthView,
    SubmissionSample,
)
from app.learner.wave2.repository import ObservationRepository
from app.models.schemas import utc_now


OBSERVATION_ONLY_LIMITATION = (
    "Longitudinal observations are descriptive; they do not establish "
    "mastery, proficiency, ability, or learning gain (WU-D F11), and they "
    "are not attributed to any learning outcome."
)

FREQUENCY_LIMITATION = (
    "Descriptive proportion over qualified recent samples only; not a "
    "validated measurement, rate, or learner-performance label."
)

ANCHOR_LIMITATION = (
    "Declared external anchor; contextual only and never converted into a "
    "learner-performance label or corpus-derived statistic."
)

DEFAULT_RECENT_WINDOW = 3
MIN_RECENT_SAMPLES_FOR_FREQUENCY = 2


class LongitudinalLearnerService:
    """Observation services over the locally-defined repository protocol."""

    def __init__(
        self,
        repository: ObservationRepository,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._now = now or utc_now

    # ------------------------------------------------------------------
    # writes (records observed evidence and observations)
    # ------------------------------------------------------------------

    def record_observation(self, record: ObservationRecord) -> None:
        self._repository.save_observation(record)

    def record_submission_sample(self, sample: SubmissionSample) -> None:
        self._repository.save_submission_sample(sample)

    def admit_evidence(self, learner_id: str, evidence: ObservedEvidence) -> None:
        self._repository.save_evidence(learner_id, evidence)

    def record_revision_behavior(self, behavior: RevisionBehavior) -> None:
        self._repository.save_revision_behavior(behavior)

    def set_proficiency_context(self, context: ProficiencyContext) -> None:
        self._repository.save_proficiency_context(context)

    # ------------------------------------------------------------------
    # longitudinal queries
    # ------------------------------------------------------------------

    def list_observation_statuses(self, learner_id: str) -> ObservationListView:
        records = self._repository.list_observations(learner_id)
        items = [self._status_view(record) for record in records]
        items.sort(
            key=lambda view: view.last_observed_at
            or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        if items:
            state, reasons = HistoryState.SUFFICIENT, []
        else:
            state, reasons = (
                HistoryState.INSUFFICIENT_HISTORY,
                ["no observations recorded for this learner"],
            )
        return ObservationListView(
            learner_id=learner_id,
            history_state=state,
            items=items,
            limitations=[OBSERVATION_ONLY_LIMITATION],
        )

    def observation_status(
        self, learner_id: str, observation_id: str,
    ) -> ObservationStatusView | None:
        record = self._repository.get_observation(learner_id, observation_id)
        if record is None:
            return None
        return self._status_view(record)

    def recurring_difficulties(
        self, learner_id: str, *, min_occurrences: int = 2,
        recent_window: int = DEFAULT_RECENT_WINDOW,
    ) -> RecurringDifficultyList:
        candidates = [
            record
            for record in self._repository.list_observations(
                learner_id, observation_type=ObservationType.DIFFICULTY,
            )
            if len(record.occurrences) >= min_occurrences
        ]
        items: list[RecurringDifficulty] = []
        for record in candidates:
            view = self._status_view(record, recent_window=recent_window)
            items.append(RecurringDifficulty(
                **view.model_dump(),
                occurrence_history=sorted(
                    record.occurrences, key=lambda occurrence: occurrence.observed_at,
                ),
            ))
        items.sort(
            key=lambda item: item.last_observed_at
            or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        if items:
            state, reasons = HistoryState.SUFFICIENT, []
        else:
            state, reasons = (
                HistoryState.INSUFFICIENT_HISTORY,
                ["no difficulty observation has enough occurrences to "
                 "establish recurrence"],
            )
        return RecurringDifficultyList(
            learner_id=learner_id,
            history_state=state,
            items=items,
            limitations=[OBSERVATION_ONLY_LIMITATION],
        )

    def strengths(self, learner_id: str) -> StrengthList:
        records = self._repository.list_observations(
            learner_id, observation_type=ObservationType.STRENGTH,
        )
        items: list[StrengthView] = []
        for record in records:
            occurrences = sorted(
                record.occurrences, key=lambda occurrence: occurrence.observed_at,
            )
            count = len(occurrences)
            if count >= 2:
                state, reasons = HistoryState.SUFFICIENT, []
            else:
                state, reasons = (
                    HistoryState.INSUFFICIENT_HISTORY,
                    ["single positive observation; repeated positive history "
                     "is not yet available"],
                )
            last = occurrences[-1].observed_at if occurrences else None
            items.append(StrengthView(
                learner_id=learner_id,
                observation_id=record.observation_id,
                code=record.code,
                label=record.label,
                occurrence_count=count,
                qualified_occurrence_count=len(
                    [o for o in occurrences if o.qualified]
                ),
                first_observed_at=occurrences[0].observed_at if occurrences else None,
                last_observed_at=last,
                days_since_last_observed=self._days_since(last),
                history_state=state,
                history_reasons=reasons,
                limitations=[OBSERVATION_ONLY_LIMITATION],
            ))
        items.sort(
            key=lambda item: item.last_observed_at
            or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return StrengthList(
            learner_id=learner_id,
            items=items,
            limitations=[OBSERVATION_ONLY_LIMITATION],
        )

    def stable_recently(
        self, learner_id: str, *, recent_window: int = DEFAULT_RECENT_WINDOW,
        min_qualified_recent: int = 2,
    ) -> StableList:
        window = self._recent_qualified_samples(learner_id, recent_window)
        items: list[StableObservation] = []
        for record in self._repository.list_observations(learner_id):
            occurrences = sorted(
                record.occurrences, key=lambda occurrence: occurrence.observed_at,
            )
            if len(occurrences) < 2:
                continue
            last = occurrences[-1].observed_at
            in_window = self._window_occurrences(record, window)
            if (
                record.observation_type is ObservationType.STRENGTH
            ):
                items.append(StableObservation(
                    learner_id=learner_id,
                    observation_id=record.observation_id,
                    code=record.code,
                    label=record.label,
                    stability_kind=StabilityKind.STRENGTH_HISTORY,
                    occurrence_count=len(occurrences),
                    qualified_occurrence_count=len(
                        [o for o in occurrences if o.qualified]
                    ),
                    recent_window_occurrence_count=len(in_window),
                    recent_window_sample_count=len(window),
                    first_observed_at=occurrences[0].observed_at,
                    last_observed_at=last,
                    history_state=HistoryState.SUFFICIENT,
                    history_reasons=[],
                    limitations=[OBSERVATION_ONLY_LIMITATION],
                ))
            elif (
                record.observation_type is ObservationType.DIFFICULTY
                and not in_window
            ):
                if len(window) >= min_qualified_recent:
                    state, reasons = HistoryState.SUFFICIENT, []
                else:
                    state, reasons = (
                        HistoryState.INSUFFICIENT_HISTORY,
                        [f"fewer than {min_qualified_recent} qualified recent "
                         "samples; non-observation in the recent window cannot "
                         "be established"],
                    )
                items.append(StableObservation(
                    learner_id=learner_id,
                    observation_id=record.observation_id,
                    code=record.code,
                    label=record.label,
                    stability_kind=(
                        StabilityKind.PREVIOUSLY_RECURRING_NOT_RECENTLY_OBSERVED
                    ),
                    occurrence_count=len(occurrences),
                    qualified_occurrence_count=len(
                        [o for o in occurrences if o.qualified]
                    ),
                    recent_window_occurrence_count=0,
                    recent_window_sample_count=len(window),
                    first_observed_at=occurrences[0].observed_at,
                    last_observed_at=last,
                    history_state=state,
                    history_reasons=reasons,
                    limitations=[OBSERVATION_ONLY_LIMITATION],
                ))
        items.sort(
            key=lambda item: item.last_observed_at
            or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return StableList(
            learner_id=learner_id,
            items=items,
            limitations=[OBSERVATION_ONLY_LIMITATION],
        )

    def proficiency_context(self, learner_id: str) -> ProficiencyContextView:
        context = self._repository.get_proficiency_context(learner_id)
        if context is None:
            return ProficiencyContextView(
                learner_id=learner_id,
                anchors=[],
                derived_from_corpus=False,
                statement=DEFAULT_ANCHOR_STATEMENT,
                history_state=HistoryState.INSUFFICIENT_HISTORY,
                history_reasons=[
                    "no proficiency context record for this learner",
                ],
                limitations=[ANCHOR_LIMITATION, OBSERVATION_ONLY_LIMITATION],
            )
        if context.anchors:
            state, reasons = HistoryState.SUFFICIENT, []
        else:
            state, reasons = (
                HistoryState.INSUFFICIENT_HISTORY,
                ["proficiency context record exists but contains no external "
                 "anchors"],
            )
        return ProficiencyContextView(
            learner_id=learner_id,
            anchors=context.anchors,
            derived_from_corpus=context.derived_from_corpus,
            statement=context.statement,
            history_state=state,
            history_reasons=reasons,
            limitations=[ANCHOR_LIMITATION, *context.limitations],
        )

    def current_evidence(self, learner_id: str) -> EvidenceList:
        records = self._repository.list_evidence(learner_id)
        items: list[LearnerEvidenceRecord] = []
        excluded = 0
        for evidence in records:
            if evidence.admission_status is not EvidenceAdmissionStatus.ADMISSIBLE:
                excluded += 1
                continue
            if not check_provenance_completeness(evidence.provenance).complete:
                excluded += 1
                continue
            items.append(LearnerEvidenceRecord(
                learner_id=learner_id, evidence=evidence,
            ))
        return EvidenceList(
            learner_id=learner_id,
            items=items,
            excluded_count=excluded,
            limitations=[OBSERVATION_ONLY_LIMITATION],
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _status_view(
        self, record: ObservationRecord,
        recent_window: int = DEFAULT_RECENT_WINDOW,
    ) -> ObservationStatusView:
        occurrences = sorted(
            record.occurrences, key=lambda occurrence: occurrence.observed_at,
        )
        qualified = [o for o in occurrences if o.qualified]
        first = occurrences[0].observed_at if occurrences else None
        last = occurrences[-1].observed_at if occurrences else None
        contexts = list(dict.fromkeys(o.task_context for o in occurrences))
        behaviors = self._repository.list_revision_behavior(
            record.learner_id, observation_id=record.observation_id,
        )
        latest_behavior = behaviors[-1] if behaviors else None
        revision_response = (
            latest_behavior.state
            if latest_behavior is not None
            else RevisionResponseState.NO_REVISION_EVIDENCE
        )
        addressed_prior = bool(
            last is not None
            and any(behavior.occurred_at < last for behavior in behaviors)
        )
        count = len(occurrences)
        if count >= 2:
            state, reasons = HistoryState.SUFFICIENT, []
        else:
            state, reasons = (
                HistoryState.INSUFFICIENT_HISTORY,
                ["fewer than 2 occurrences; recurring or stable status cannot "
                 "be established"],
            )
        return ObservationStatusView(
            learner_id=record.learner_id,
            observation_id=record.observation_id,
            code=record.code,
            label=record.label,
            observation_type=record.observation_type,
            occurrence_count=count,
            qualified_occurrence_count=len(qualified),
            prior_occurrence_count=max(0, count - 1),
            appeared_before=count >= 2,
            first_observed_at=first,
            last_observed_at=last,
            days_since_last_observed=self._days_since(last),
            contexts=contexts,
            revision_response=revision_response,
            addressed_in_prior_revision=addressed_prior,
            frequency=self._frequency(record, recent_window=recent_window),
            history_state=state,
            history_reasons=reasons,
            limitations=[OBSERVATION_ONLY_LIMITATION, *record.limitations],
        )

    def _frequency(
        self, record: ObservationRecord, *, recent_window: int,
    ) -> QualifiedFrequency:
        window = self._recent_qualified_samples(record.learner_id, recent_window)
        if not window:
            return QualifiedFrequency(
                qualified_occurrence_count=0,
                qualified_sample_count=0,
                window_size=recent_window,
                descriptive_proportion=None,
                history_state=HistoryState.INSUFFICIENT_HISTORY,
                history_reasons=[
                    "no qualified recent samples; frequency cannot be "
                    "established",
                ],
                limitation=FREQUENCY_LIMITATION,
            )
        in_window = self._window_occurrences(record, window)
        sample_count = len(window)
        proportion = len(in_window) / sample_count
        if sample_count < MIN_RECENT_SAMPLES_FOR_FREQUENCY:
            state, reasons = (
                HistoryState.INSUFFICIENT_HISTORY,
                [f"fewer than {MIN_RECENT_SAMPLES_FOR_FREQUENCY} qualified "
                 "recent samples; frequency cannot be established"],
            )
        else:
            state, reasons = HistoryState.SUFFICIENT, []
        return QualifiedFrequency(
            qualified_occurrence_count=len(in_window),
            qualified_sample_count=sample_count,
            window_size=recent_window,
            descriptive_proportion=proportion,
            history_state=state,
            history_reasons=reasons,
            limitation=FREQUENCY_LIMITATION,
        )

    def _recent_qualified_samples(
        self, learner_id: str, window: int,
    ) -> list[SubmissionSample]:
        qualified = [
            sample
            for sample in self._repository.list_submission_samples(learner_id)
            if sample.qualified
        ]
        if window <= 0:
            return []
        return qualified[-window:]

    @staticmethod
    def _window_occurrences(
        record: ObservationRecord, window: list[SubmissionSample],
    ) -> list[OccurrenceEntry]:
        if not window:
            return []
        earliest = window[0].submitted_at
        return [
            occurrence
            for occurrence in record.occurrences
            if occurrence.qualified and occurrence.observed_at >= earliest
        ]

    def _days_since(self, moment: datetime | None) -> int | None:
        if moment is None:
            return None
        return max(0, (self._now() - moment).days)


__all__ = [
    "ANCHOR_LIMITATION",
    "DEFAULT_RECENT_WINDOW",
    "FREQUENCY_LIMITATION",
    "LongitudinalLearnerService",
    "MIN_RECENT_SAMPLES_FOR_FREQUENCY",
    "OBSERVATION_ONLY_LIMITATION",
]
