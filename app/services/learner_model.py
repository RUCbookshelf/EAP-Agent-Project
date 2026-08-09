from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from statistics import mean, pstdev
from typing import Any

from app.configuration import ConfigurationPayload
from app.core import (
    DataSufficiency, DiagnosticEvidenceCount, DiagnosticTrajectoryV2,
    HistoryEvidenceRecord, LearningTarget, MetricTrajectory, MetricTrajectoryPoint,
    StrengthPattern, TaskCluster,
)
from app.services.legacy_genre_mapping import map_legacy_genre


class LearnerModelEngine:
    """Transparent v0.7 task-aware learner-model calculations.

    The engine reports observed, version-compatible text signals. It never reports
    proficiency, mastery, causal improvement, or a learner score.
    """

    profile_version = "learner-profile-v0.7.0"
    task_cluster_version = "task-cluster-v0.8.0"
    metric_version = "metric-trajectory-v0.7.0"
    diagnostic_version = "diagnostic-trajectory-v0.7.0"

    def __init__(self, configuration: ConfigurationPayload | None = None) -> None:
        self.configuration = configuration or ConfigurationPayload()

    @staticmethod
    def submission_id(record: dict[str, Any]) -> str:
        return f"E{int(record['essay_id']):06d}"

    @staticmethod
    def observed_at(record: dict[str, Any]) -> datetime:
        value = record["submitted_at"]
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    def choose_representatives(
        self, records: list[dict[str, Any]], strategy: str | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        strategy = strategy or self.configuration.representative_draft_strategy
        independent = [item for item in records if not item.get("revision_group_id")]
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in records:
            if item.get("revision_group_id"):
                groups[str(item["revision_group_id"])].append(item)
        selected = list(independent)
        excluded: list[dict[str, Any]] = []
        for members in groups.values():
            ordered = sorted(
                members,
                key=lambda item: (int(item.get("revision_sequence") or 0), int(item["essay_id"])),
            )
            if strategy == "all_drafts_research_mode":
                chosen = ordered
            elif strategy == "first_draft_only":
                chosen = ordered[:1]
            elif strategy == "latest_draft_only":
                chosen = ordered[-1:]
            else:
                finals = [item for item in ordered if self._stage(item) == "final_draft"]
                chosen = (finals[-1:] or ordered[-1:])
            selected.extend(chosen)
            chosen_ids = {int(item["essay_id"]) for item in chosen}
            excluded.extend(item for item in ordered if int(item["essay_id"]) not in chosen_ids)
        return sorted(selected, key=self.observed_at), sorted(excluded, key=self.observed_at)

    def task_clusters(self, student_id: str, records: list[dict[str, Any]]) -> list[TaskCluster]:
        buckets: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            key = self._cluster_key(record)
            buckets[key].append(record)
        clusters: list[TaskCluster] = []
        for index, (key, members) in enumerate(sorted(buckets.items()), 1):
            genre, purpose, timed, time_band, tool, mode, prompt_family, analyzer, metric_signature = key
            clusters.append(TaskCluster(
                task_cluster_id=f"TC{index:03d}", student_id=student_id,
                cluster_type="task_condition_cluster", genre=genre, writing_purpose=purpose,
                timed=timed == "timed", time_limit_band=time_band, tool_use=tool,
                task_mode=mode, prompt_family=prompt_family, analyzer_family=analyzer,
                metric_version_signature=metric_signature,
                submission_ids=[self.submission_id(item) for item in members],
                representative_submission_ids=[self.submission_id(item) for item in members],
                comparability_status="comparable" if len(members) >= 2 else "limited",
                confidence="medium" if len(members) >= 3 else "low" if len(members) >= 2 else "insufficient",
                limitations=[
                    "Task clustering uses transparent metadata rules, not semantic equivalence.",
                    "A shared cluster does not make tasks psychometrically equivalent.",
                ],
            ))
        return clusters

    def data_sufficiency(
        self, records: list[dict[str, Any]], representatives: list[dict[str, Any]],
        excluded: list[dict[str, Any]], clusters: list[TaskCluster],
    ) -> DataSufficiency:
        count = len(representatives)
        if count < self.configuration.learner_model_min_pairwise_tasks:
            status = "insufficient"
            explanation = "Fewer than two representative tasks; no longitudinal comparison is admitted."
        elif count < self.configuration.learner_model_min_direction_tasks:
            status = "limited"
            explanation = "Two representative tasks permit only a pairwise descriptive comparison."
        elif count < self.configuration.learner_model_adequate_tasks:
            status = "provisional"
            explanation = "Three or four representative tasks permit provisional within-cluster patterns."
        else:
            status = "adequate_for_descriptive_trend"
            explanation = "At least five representative tasks support descriptive trends, not ability claims."
        versions = {str(item.get("analyzer_version") or item.get("analysis_version")) for item in representatives}
        metric_signatures = {self._metric_signature(item) for item in representatives}
        valid_metrics = sum(
            1 for item in representatives for value in self._versioned_metrics(item).values()
            if value.get("status", "available") == "available"
            and value.get("eligible_for_longitudinal_comparison", True)
        )
        quality_exclusions = sum(1 for item in records if self._quality_excluded(item))
        quality_issues = sum(1 for item in records if (item.get("input_quality") or {}).get("quality_flags"))
        metadata_missing = sum(
            1 for item in records if not item.get("genre") or item.get("timed") is None
        )
        span = (
            max((self.observed_at(item) for item in records), default=datetime.now(timezone.utc))
            - min((self.observed_at(item) for item in records), default=datetime.now(timezone.utc))
        ).total_seconds() / 86400
        return DataSufficiency(
            status=status, historical_submission_count=len(records), independent_task_count=count,
            current_task_cluster_count=len(clusters), valid_metric_result_count=valid_metrics,
            selected_diagnosis_count=sum(len(self._signals(item, "selected")) for item in representatives),
            time_span_days=max(0.0, round(span, 3)), analyzer_compatible=len(versions) <= 1,
            metric_versions_compatible=len(metric_signatures) <= 1,
            metadata_missing_count=metadata_missing, revision_duplicate_count=len(excluded),
            input_quality_exclusion_count=quality_exclusions,
            input_quality_issue_count=quality_issues,
            thresholds={
                "minimum_pairwise_tasks": self.configuration.learner_model_min_pairwise_tasks,
                "minimum_direction_tasks": self.configuration.learner_model_min_direction_tasks,
                "adequate_descriptive_tasks": self.configuration.learner_model_adequate_tasks,
            }, explanation=explanation,
            limitations=["Thresholds are conservative prototype defaults without educational validation."],
        )

    def metric_trajectories(
        self, clusters: list[TaskCluster], records: list[dict[str, Any]],
    ) -> list[MetricTrajectory]:
        by_id = {self.submission_id(item): item for item in records}
        results: list[MetricTrajectory] = []
        counter = 0
        for cluster in clusters:
            groups: dict[tuple[str, str, str], list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
            for sid in cluster.representative_submission_ids:
                record = by_id[sid]
                for metric_id, result in self._versioned_metrics(record).items():
                    if result.get("status", "available") != "available":
                        continue
                    version = str(result.get("metric_version", "legacy-v0.1"))
                    analyzer = str(record.get("analyzer_version") or record.get("analysis_version") or "unknown")
                    groups[(metric_id, version, analyzer)].append((record, result))
            for (metric_id, metric_version, analyzer), items in sorted(groups.items()):
                values: list[float] = []
                points: list[MetricTrajectoryPoint] = []
                for record, result in sorted(items, key=lambda pair: self.observed_at(pair[0])):
                    try:
                        value = float(result["value"])
                    except (TypeError, ValueError):
                        continue
                    values.append(value)
                    points.append(MetricTrajectoryPoint(
                        submission_id=self.submission_id(record),
                        analysis_run_id=record.get("analysis_run_id"),
                        submitted_at=self.observed_at(record), value=value,
                        metric_confidence=str(result.get("confidence", "low")),
                    ))
                if not points:
                    continue
                counter += 1
                direction, status, slope, relative, pairwise, variability, confidence = self._metric_pattern(values)
                results.append(MetricTrajectory(
                    trajectory_id=f"MT{counter:03d}", metric_id=metric_id,
                    metric_version=metric_version, analyzer_version=analyzer,
                    task_cluster_id=cluster.task_cluster_id, data_points=points,
                    included_submission_ids=[point.submission_id for point in points],
                    excluded_submission_ids=[], direction=direction, variability=variability,
                    confidence=confidence, trend_status=status, slope=slope,
                    relative_change=relative, pairwise_difference=pairwise,
                    limitations=[
                        "Observed metric direction is task- and version-specific, not proficiency growth.",
                        "Two points are reported only as a pairwise difference.",
                    ],
                ))
        return results

    def diagnostic_trajectories(
        self, clusters: list[TaskCluster], records: list[dict[str, Any]],
    ) -> list[DiagnosticTrajectoryV2]:
        by_id = {self.submission_id(item): item for item in records}
        results: list[DiagnosticTrajectoryV2] = []
        counter = 0
        for cluster in clusters:
            members = [by_id[sid] for sid in cluster.representative_submission_ids]
            categories = sorted({
                str(signal.get("category")) for item in members
                for kind in ("selected", "eligible", "monitored", "suppressed")
                for signal in self._signals(item, kind) if signal.get("category")
            })
            for category in categories:
                counter += 1
                selected = [item for item in members if self._has_category(item, "selected", category)]
                eligible = [item for item in members if self._has_category(item, "eligible", category)]
                monitored = [item for item in members if self._has_category(item, "monitored", category)]
                suppressed = [item for item in members if self._has_category(item, "suppressed", category)]
                current = members[-1]
                current_signal = next((s for s in self._signals(current, "selected") if s.get("category") == category), None)
                current_verified = bool(current_signal and current_signal.get("evidence_relevance_status") == "verified")
                status = self._diagnostic_status(
                    len(members), len(selected), len(eligible), bool(current_signal), current_verified,
                    [self._has_category(item, "selected", category) for item in members],
                )
                versions = sorted({
                    str((item.get("diagnostic_calibration") or {}).get("diagnosis_version")
                        or item.get("diagnosis_version") or "legacy") for item in members
                })
                if len(versions) > 1:
                    status = "not_comparable"
                results.append(DiagnosticTrajectoryV2(
                    trajectory_id=f"DTL{counter:03d}", diagnosis_category=category,
                    task_cluster_id=cluster.task_cluster_id, status=status,
                    comparable_task_count=len(members),
                    evidence_counts=DiagnosticEvidenceCount(
                        selected_priority=len(selected), eligible_diagnosis=len(eligible),
                        monitored_signal=len(monitored), suppressed=len(suppressed),
                    ),
                    selected_submission_ids=[self.submission_id(item) for item in selected],
                    auxiliary_submission_ids=[self.submission_id(item) for item in eligible],
                    research_only_submission_ids=[self.submission_id(item) for item in [*monitored, *suppressed]],
                    diagnosis_versions=versions,
                    current_selection_status="selected_priority" if current_signal else "not_selected",
                    current_evidence_verified=current_verified,
                    confidence="medium" if status == "persistent_pattern" and len(versions) == 1 else
                               "low" if status not in {"insufficient_evidence", "not_comparable"} else "insufficient",
                    limitations=[
                        "Only calibrated selected priorities are primary evidence; monitored and suppressed signals are research-only.",
                        "A trajectory is not proof of mastery, persistence of ability, or causal change.",
                    ],
                ))
        return results

    def targets_and_evidence(
        self, trajectories: list[DiagnosticTrajectoryV2], records: list[dict[str, Any]],
    ) -> tuple[list[LearningTarget], list[HistoryEvidenceRecord]]:
        current = records[-1]
        current_id = self.submission_id(current)
        selected = {str(item.get("category")): item for item in self._signals(current, "selected")}
        candidates = [
            item for item in trajectories
            if item.diagnosis_category in selected and item.current_evidence_verified
            and item.status != "not_comparable"
        ]
        rank = {"persistent_pattern": 0, "recurring_pattern": 1, "emerging_pattern": 2,
                "variable_pattern": 3, "insufficient_evidence": 4}
        candidates.sort(key=lambda item: (rank.get(item.status, 5), item.diagnosis_category))
        targets: list[LearningTarget] = []
        evidence: list[HistoryEvidenceRecord] = []
        for index, trajectory in enumerate(candidates[:self.configuration.learner_model_max_targets], 1):
            signal = selected[trajectory.diagnosis_category]
            target_evidence_ids: list[str] = []
            if trajectory.comparable_task_count >= 2 and trajectory.status != "insufficient_evidence":
                evidence_index = len(evidence) + 1
                evidence.append(HistoryEvidenceRecord(
                    student_id=str(current["student_id"]), evidence_type="diagnostic_trajectory",
                    source_submission_ids=trajectory.selected_submission_ids,
                    source_diagnosis_ids=[str(signal.get("diagnosis_id", ""))],
                    task_cluster_id=trajectory.task_cluster_id,
                    evidence_text=(
                        f"{trajectory.diagnosis_category} is currently selected with verified evidence; "
                        f"its task-aware status is {trajectory.status}."
                    ),
                    evidence_status="verified", version_compatibility="compatible",
                    confidence=trajectory.confidence,
                    limitations=["This registry item supports formative prioritization, not an ability judgment."],
                ))
                target_evidence_ids = [f"PENDING-{evidence_index}"]
            targets.append(LearningTarget(
                target_id=f"LT{index:03d}", category=trajectory.diagnosis_category,
                status="active", source_trajectory_id=trajectory.trajectory_id,
                supporting_submission_ids=trajectory.selected_submission_ids,
                history_evidence_ids=target_evidence_ids,
                current_evidence_id=str(signal.get("diagnosis_id", "unknown")),
                selection_reason=(
                    f"Current Diagnostic Gate selected verified evidence; historical status is {trajectory.status}."
                ), confidence=trajectory.confidence if trajectory.confidence != "insufficient" else "low",
                priority=index,
                limitations=["Target selection cannot reactivate monitored or suppressed diagnostics."],
            ))
        return targets, evidence

    def strength_patterns(
        self, clusters: list[TaskCluster], records: list[dict[str, Any]],
    ) -> list[StrengthPattern]:
        by_id = {self.submission_id(item): item for item in records}
        observations: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for cluster in clusters:
            for sid in cluster.representative_submission_ids:
                record = by_id[sid]
                for signal in self._signals(record, "strength"):
                    quotes = signal.get("evidence_quote_candidates") or []
                    if signal.get("evidence_relevance_status") == "verified" and quotes:
                        observations[str(signal.get("category"))].append((sid, str(quotes[0])))
        results = []
        for index, (category, items) in enumerate(sorted(observations.items()), 1):
            count = len(items)
            results.append(StrengthPattern(
                strength_pattern_id=f"SP{index:03d}", category=category,
                status="stable_strength_signal" if count >= 3 else "recurring_strength" if count == 2 else "observed_once",
                supporting_submission_ids=[item[0] for item in items],
                evidence_quotes=[item[1] for item in items],
                confidence="medium" if count >= 3 else "low",
                limitations=["This is an observed text-feature pattern, not a general writing-strength claim."],
            ))
        return results

    @staticmethod
    def _stage(record: dict[str, Any]) -> str:
        value = str(record.get("revision_stage") or record.get("draft_stage") or "").casefold()
        return value.replace(" ", "_").replace("-", "_")

    def _cluster_key(self, record: dict[str, Any]) -> tuple[str, ...]:
        genre = str(record.get("genre") or "unknown").casefold().strip()
        # Domain Pack v1 / D-22: the cluster purpose is derived from the
        # deterministic task-type lane, never from genre substring inference.
        # A persisted task_type (future D-L2-02 additive column) wins; legacy
        # rows map through the qualified D-22 manifest (explicit-only).
        persisted = record.get("task_type")
        if persisted:
            purpose = str(persisted)
        else:
            purpose = map_legacy_genre(genre).mapping
        timed = "timed" if bool(record.get("timed")) else "untimed"
        minutes = int(record.get("time_limit_minutes") or 0)
        time_band = "not_applicable" if not record.get("timed") else "1-30" if minutes <= 30 else "31-60" if minutes <= 60 else "61+"
        tool = str(record.get("tool_use") or "none").casefold().strip()
        tool_class = "none" if tool in {"", "none", "no"} else "tool_assisted"
        mode = "revision_task" if record.get("revision_group_id") else "independent_task"
        prompt_family = f"{purpose}-general"
        analyzer = str(record.get("analyzer_version") or record.get("analysis_version") or "unknown")
        analyzer_family = analyzer.split("-v", 1)[0]
        return (genre, purpose, timed, time_band, tool_class, mode, prompt_family,
                analyzer_family, self._metric_signature(record))

    def _metric_signature(self, record: dict[str, Any]) -> str:
        return "|".join(sorted({
            f"{key}:{value.get('metric_version', 'legacy-v0.1')}"
            for key, value in self._versioned_metrics(record).items()
        })) or "no-versioned-metrics"

    @staticmethod
    def _versioned_metrics(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
        if record.get("versioned_metrics"):
            return record["versioned_metrics"]
        return {
            key: {"value": value, "metric_version": str(record.get("analysis_version", "legacy-v0.1")),
                  "status": "available", "confidence": "low",
                  "eligible_for_longitudinal_comparison": True}
            for key, value in record.get("metrics", {}).items()
            if isinstance(value, (int, float))
        }

    @staticmethod
    def _quality_excluded(record: dict[str, Any]) -> bool:
        quality = record.get("input_quality") or {}
        # v0.6 policy is preserved: automatic flags request confirmation and do
        # not exclude a whole essay by themselves. Explicit future adjudication
        # fields may mark a record unusable without changing that policy.
        return bool(quality.get("exclude_from_longitudinal") or quality.get("measurement_status") == "insufficient")

    @staticmethod
    def _signals(record: dict[str, Any], kind: str) -> list[dict[str, Any]]:
        calibration = record.get("diagnostic_calibration") or {}
        mapping = {"selected": "selected_priorities", "eligible": "eligible_diagnoses",
                   "monitored": "monitored_signals", "suppressed": "suppressed_diagnostics",
                   "strength": "verified_strengths"}
        if calibration:
            return list(calibration.get(mapping[kind], []))
        diagnosis = record.get("diagnosis") or {}
        legacy = {"selected": "improvement_priorities", "eligible": "improvement_priorities",
                  "monitored": "monitored_signals", "suppressed": "suppressed_signals",
                  "strength": "strengths"}
        return list(diagnosis.get(legacy[kind], []))

    def _has_category(self, record: dict[str, Any], kind: str, category: str) -> bool:
        return any(str(item.get("category")) == category for item in self._signals(record, kind))

    @staticmethod
    def _metric_pattern(values: list[float]) -> tuple[Any, Any, Any, Any, Any, Any, Any]:
        if len(values) == 1:
            return "insufficient_data", "insufficient", None, None, None, "insufficient_data", "insufficient"
        pairwise = round(values[-1] - values[0], 6)
        relative = round(pairwise / max(abs(values[0]), 1.0), 6)
        if len(values) == 2:
            return "insufficient_data", "limited_pairwise_comparison", None, relative, pairwise, "insufficient_data", "low"
        x_mean = (len(values) - 1) / 2
        y_mean = mean(values)
        denominator = sum((index - x_mean) ** 2 for index in range(len(values)))
        slope = sum((index - x_mean) * (value - y_mean) for index, value in enumerate(values)) / denominator
        cv = pstdev(values) / max(abs(y_mean), 1e-9)
        variability = "low" if cv <= 0.10 else "high" if cv > 0.30 else "moderate"
        direction = "variable" if variability == "high" else "increasing_signal" if relative >= 0.10 else "decreasing_signal" if relative <= -0.10 else "stable"
        status = "adequate_for_descriptive_trend" if len(values) >= 5 else "provisional_pattern"
        confidence = "medium" if len(values) >= 5 and variability != "high" else "low"
        return direction, status, round(slope, 6), relative, pairwise, variability, confidence

    def _diagnostic_status(
        self, task_count: int, selected_count: int, eligible_count: int,
        current_selected: bool, current_verified: bool, pattern: list[bool],
    ) -> str:
        if task_count < 2:
            return "insufficient_evidence"
        window = self.configuration.diagnostic_reduction_window
        if len(pattern) > window and sum(pattern[:-window]) >= 2 and not any(pattern[-window:]):
            return "recently_reduced_signal"
        if (
            task_count >= self.configuration.diagnostic_persistent_threshold
            and selected_count >= self.configuration.diagnostic_persistent_selected_threshold
            and current_selected and current_verified
        ):
            return "persistent_pattern"
        if selected_count >= self.configuration.diagnostic_recurring_threshold:
            return "recurring_pattern"
        if selected_count >= self.configuration.diagnostic_emerging_threshold:
            return "emerging_pattern"
        if selected_count or eligible_count:
            return "variable_pattern"
        return "not_currently_observed"
