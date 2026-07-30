from __future__ import annotations

from typing import Any

from app.repositories import RevisionRepository
from app.revision import (
    DiagnosisTrajectory, FeedbackUptakeCandidate, LocalRevisionAligner, MetricChange,
    RevisionComparabilityService, RevisionDraftChainItem, RevisionGroup, RevisionGroupSummary,
    RevisionSnapshot, RevisionTrajectoryComparison, WithinTaskRevisionTrajectory,
)


class RevisionService:
    alignment_version = "local-sequence-alignment-v0.5.0"
    uptake_version = "feedback-uptake-v0.5.0"

    def __init__(self, repository: RevisionRepository) -> None:
        self.repository = repository
        self.aligner = LocalRevisionAligner()
        self.comparability = RevisionComparabilityService()

    def validate_relationship(self, source_submission_id: int, target_submission_id: int | None,
                              *, target_student_id: str | None = None) -> None:
        source = self.repository.get_submission_bundle(source_submission_id)
        if source is None:
            raise LookupError("Source submission not found.")
        if target_submission_id is not None:
            if source_submission_id == target_submission_id:
                raise ValueError("A submission cannot revise itself.")
            target = self.repository.get_submission_bundle(target_submission_id)
            if target is None:
                raise LookupError("Target submission not found.")
            target_student_id = target["student_id"]
        if target_student_id is not None and source["student_id"] != target_student_id:
            raise ValueError("Cross-student revision relationships are forbidden.")
        cursor = source
        seen: set[int] = set()
        while cursor and cursor.get("revision_of_submission_id") is not None:
            current_id = int(cursor["essay_id"])
            if current_id in seen:
                raise ValueError("A cyclic revision relationship already exists.")
            seen.add(current_id)
            parent_id = int(cursor["revision_of_submission_id"])
            if target_submission_id is not None and parent_id == target_submission_id:
                raise ValueError("The requested relationship would create a cycle.")
            cursor = self.repository.get_submission_bundle(parent_id)
        if target_submission_id is not None:
            target = self.repository.get_submission_bundle(target_submission_id)
            if target and (target.get("revision_of_submission_id") is not None or target.get("revision_group_id") is not None):
                raise ValueError("The target submission already belongs to a revision relationship.")

    def create_relationship(self, source_submission_id: int, target_submission_id: int) -> RevisionSnapshot:
        self.validate_relationship(source_submission_id, target_submission_id)
        group = self.repository.create_revision_group(source_submission_id)
        self.repository.link_revision(source_submission_id, target_submission_id, group.revision_group_id)
        return self.recalculate(group.revision_group_id, source_submission_id, target_submission_id)

    def recalculate(self, revision_group_id: str, source_submission_id: int, target_submission_id: int) -> RevisionSnapshot:
        return self.repository.save_revision_snapshot(
            self._calculate(revision_group_id, source_submission_id, target_submission_id)
        )

    def _calculate(self, revision_group_id: str, source_submission_id: int, target_submission_id: int) -> RevisionSnapshot:
        source = self.repository.get_submission_bundle(source_submission_id)
        target = self.repository.get_submission_bundle(target_submission_id)
        if source is None or target is None:
            raise LookupError("Source or target submission not found.")
        paragraphs, sentences, token_changes = self.aligner.align(source["essay_text"], target["essay_text"])
        full_similarity = self.aligner.similarity(source["essay_text"], target["essay_text"])
        comparability = self.comparability.compare(source, target, full_text_similarity=full_similarity)
        major = comparability.status == "major_rewrite" or (
            token_changes["inserted_ratio"] + token_changes["deleted_ratio"] + token_changes["modified_ratio"] > 0.75
        )
        if major and comparability.status != "major_rewrite":
            comparability = comparability.model_copy(update={
                "status": "major_rewrite", "confidence": "low",
                "reasons": [*comparability.reasons, "Combined local edit ratios exceed the prototype major-rewrite boundary."],
            })
        source_run = self.repository.get_latest_analysis_run(source_submission_id)
        target_run = self.repository.get_latest_analysis_run(target_submission_id)
        analyzer_versions = {
            "source": source_run["analyzer_version"] if source_run else source.get("analysis_version", "unknown"),
            "target": target_run["analyzer_version"] if target_run else target.get("analysis_version", "unknown"),
        }
        metric_changes = self._metric_changes(source, target, analyzer_versions)
        trajectories = self._diagnosis_trajectories(source, target, analyzer_versions)
        uptake = self._uptake_candidates(source, target, trajectories, sentences, major)
        evidence = self._revision_evidence(comparability, token_changes, metric_changes, trajectories, uptake)
        limitations = [
            "Revision outputs describe observed text changes, not proficiency growth or learning effects.",
            "Local alignment and uptake rules are prototype candidates requiring human confirmation.",
        ]
        if major:
            limitations.append("Major rewrite limits attribution of changes to prior feedback.")
        if analyzer_versions["source"] != analyzer_versions["target"]:
            limitations.append("Analyzer versions differ; metric and diagnosis comparisons are limited.")
        snapshot = RevisionSnapshot(
            revision_group_id=revision_group_id, source_submission_id=source_submission_id,
            target_submission_id=target_submission_id, comparability=comparability,
            paragraph_alignments=paragraphs, sentence_alignments=sentences, token_changes=token_changes,
            metric_changes=metric_changes, diagnosis_trajectories=trajectories, uptake_candidates=uptake,
            revision_evidence=evidence, major_rewrite=major, analyzer_versions=analyzer_versions,
            algorithm_versions={"alignment": self.alignment_version, "comparability": self.comparability.version,
                                "uptake": self.uptake_version, "diagnosis_trajectory": "revision-diagnosis-trajectory-v0.5.0"},
            resource_versions={}, limitations=limitations,
        )
        return snapshot

    def candidates(self, submission_id: int) -> list[dict[str, Any]]:
        return self.repository.list_revision_candidates(submission_id)

    def group(self, revision_group_id: str) -> RevisionGroup:
        group = self.repository.get_revision_group(revision_group_id)
        if group is None:
            raise LookupError("Revision group not found.")
        return group

    def latest(self, revision_group_id: str) -> RevisionSnapshot:
        value = self.repository.get_latest_revision_snapshot(revision_group_id)
        if value is None:
            raise LookupError("Revision snapshot not found.")
        return RevisionSnapshot.model_validate(value)

    def history(self, revision_group_id: str) -> list[RevisionSnapshot]:
        return [RevisionSnapshot.model_validate(item) for item in self.repository.list_revision_snapshots(revision_group_id)]

    def group_summary(self, revision_group_id: str) -> RevisionGroupSummary:
        group = self.group(revision_group_id)
        return RevisionGroupSummary(
            revision_group_id=revision_group_id,
            draft_submission_count=len(group.member_submission_ids),
        )

    def trajectory(self, revision_group_id: str) -> WithinTaskRevisionTrajectory:
        group = self.group(revision_group_id)
        members = [
            self.repository.get_submission_bundle(submission_id)
            for submission_id in group.member_submission_ids
        ]
        if any(item is None for item in members):
            raise LookupError("A Revision Group member is unavailable.")
        records = [item for item in members if item is not None]
        draft_chain = [
            RevisionDraftChainItem(
                submission_id=int(item["essay_id"]), draft_stage=str(item.get("draft_stage") or "unknown"),
                revision_sequence=int(item.get("revision_sequence") or index),
                submitted_at=item["submitted_at"], writing_prompt=str(item.get("writing_prompt") or ""),
                revision_group_id=revision_group_id,
            )
            for index, item in enumerate(records, 1)
        ]
        latest_by_pair: dict[tuple[int, int], RevisionSnapshot] = {}
        for snapshot in self.history(revision_group_id):
            latest_by_pair[(snapshot.source_submission_id, snapshot.target_submission_id)] = snapshot
        pairwise_snapshots: list[RevisionSnapshot] = []
        for source, target in zip(records, records[1:]):
            key = (int(source["essay_id"]), int(target["essay_id"]))
            snapshot = latest_by_pair.get(key)
            if snapshot is not None:
                pairwise_snapshots.append(snapshot)
        first_to_latest_snapshot = None
        if len(records) >= 2:
            key = (int(records[0]["essay_id"]), int(records[-1]["essay_id"]))
            first_to_latest_snapshot = latest_by_pair.get(key) or self._calculate(
                revision_group_id, key[0], key[1]
            )
        pairwise = [self._trajectory_comparison(item) for item in pairwise_snapshots]
        first_to_latest = (
            self._trajectory_comparison(first_to_latest_snapshot)
            if first_to_latest_snapshot is not None else None
        )
        previous = records[-2] if len(records) >= 2 else None
        current = records[-1]
        previous_priorities = list((previous.get("feedback") or {}).get("priority_feedback", [])) if previous else []
        current_priorities = [
            {
                "diagnosis_id": item.get("diagnosis_id"), "category": item.get("category"),
                "selection_status": item.get("selection_status", "selected_priority"),
            }
            for item in (current.get("diagnosis") or {}).get("improvement_priorities", [])
        ]
        major = any(item.major_rewrite for item in pairwise_snapshots) or bool(
            first_to_latest_snapshot and first_to_latest_snapshot.major_rewrite
        )
        latest_snapshot = pairwise_snapshots[-1] if pairwise_snapshots else first_to_latest_snapshot
        attribution = "insufficient" if major else "low"
        limitations = [
            "Within-task changes are observable text differences, not cross-task development or ability growth.",
            "Feedback-uptake candidates do not establish that feedback caused a revision.",
        ]
        if major:
            limitations.append("Major rewriting prevents reliable attribution of changes to prior feedback.")
        if not previous_priorities:
            limitations.append("No previous selected priority is available for uptake tracking.")
        return WithinTaskRevisionTrajectory(
            revision_group_id=revision_group_id, draft_chain=draft_chain,
            pairwise_comparisons=pairwise, first_to_latest_comparison=first_to_latest,
            diagnosis_changes=first_to_latest.diagnosis_changes if first_to_latest else [],
            metric_changes=first_to_latest.metric_changes if first_to_latest else [],
            previous_selected_priorities=previous_priorities,
            current_priority_status=current_priorities,
            feedback_uptake_candidates=(latest_snapshot.uptake_candidates if latest_snapshot else []),
            attribution_confidence=attribution, major_rewrite_detected=major,
            limitations=limitations,
        )

    @staticmethod
    def _trajectory_comparison(snapshot: RevisionSnapshot) -> RevisionTrajectoryComparison:
        return RevisionTrajectoryComparison(
            source_submission_id=snapshot.source_submission_id,
            target_submission_id=snapshot.target_submission_id,
            token_changes=snapshot.token_changes, metric_changes=snapshot.metric_changes,
            diagnosis_changes=snapshot.diagnosis_trajectories,
            major_rewrite=snapshot.major_rewrite,
            attribution_confidence="insufficient" if snapshot.major_rewrite else "low",
            limitations=snapshot.limitations,
        )

    @staticmethod
    def _metric_changes(source: dict, target: dict, versions: dict[str, str]) -> list[MetricChange]:
        names = sorted(set((source.get("metrics") or {}).keys()) | set((target.get("metrics") or {}).keys()))
        same = versions["source"] == versions["target"]
        results = []
        for name in names:
            left = (source.get("metrics") or {}).get(name)
            right = (target.get("metrics") or {}).get(name)
            status = "compatible" if same and left is not None and right is not None else "incompatible_version" if not same else "insufficient_data"
            change = round(float(right) - float(left), 4) if status == "compatible" and isinstance(left, (int, float)) and isinstance(right, (int, float)) else None
            limitations = ["Observed metric difference is not evidence of ability improvement."]
            if not same:
                limitations.append("Analyzer versions differ; values are not directly compared.")
            results.append(MetricChange(
                metric_id=name, source_value=left, target_value=right, change=change,
                comparison_status=status, source_analyzer_version=versions["source"],
                target_analyzer_version=versions["target"], limitations=limitations,
            ))
        return results

    @staticmethod
    def _diagnosis_trajectories(source: dict, target: dict, versions: dict[str, str]) -> list[DiagnosisTrajectory]:
        source_items = (source.get("diagnosis") or {}).get("improvement_priorities", [])
        target_items = (target.get("diagnosis") or {}).get("improvement_priorities", [])
        categories = sorted({item.get("category") for item in [*source_items, *target_items] if item.get("category")})
        compatible = versions["source"] == versions["target"] and source.get("diagnosis_version") == target.get("diagnosis_version")
        results = []
        for index, category in enumerate(categories, 1):
            left = [item for item in source_items if item.get("category") == category]
            right = [item for item in target_items if item.get("category") == category]
            if not compatible:
                status, confidence = "not_comparable", "insufficient"
            elif left and right:
                left_evidence = {(item.get("evidence"), str(item.get("source_metrics"))) for item in left}
                right_evidence = {(item.get("evidence"), str(item.get("source_metrics"))) for item in right}
                status = "still_observed" if left_evidence == right_evidence else "changed_evidence"
                confidence = "medium" if status == "still_observed" else "low"
            elif left:
                status, confidence = "not_currently_observed", "low"
            elif right:
                status, confidence = "newly_observed", "low"
            else:
                status, confidence = "insufficient_evidence", "insufficient"
            limitations = ["A single absence is not solved or mastered; diagnoses are prototype signals."]
            if not compatible:
                limitations.append("Analyzer or diagnosis versions differ.")
            results.append(DiagnosisTrajectory(
                trajectory_id=f"DT{index:03d}", diagnosis_category=category, status=status,
                source_diagnosis_ids=[item["diagnosis_id"] for item in left],
                target_diagnosis_ids=[item["diagnosis_id"] for item in right],
                supporting_submission_ids=[source["essay_id"], target["essay_id"]],
                confidence=confidence, limitations=limitations,
            ))
        return results

    @staticmethod
    def _uptake_candidates(source: dict, target: dict, trajectories: list[DiagnosisTrajectory], alignments, major: bool) -> list[FeedbackUptakeCandidate]:
        feedback = source.get("feedback") or {}
        items = feedback.get("priority_feedback", [])
        by_category = {item.diagnosis_category: item for item in trajectories}
        alignment_ids = [item.alignment_id for item in alignments if item.alignment_type not in {"unchanged", "unaligned"}]
        results = []
        for index, item in enumerate(items, 1):
            trajectory = by_category.get(item.get("category"))
            if major or trajectory is None or trajectory.status == "not_comparable":
                status, confidence, observed = "not_assessable", "insufficient", "The revision evidence is not sufficiently comparable."
            elif trajectory.status == "not_currently_observed":
                status, confidence, observed = "supported", "low", "The prior signal is not currently observed in the linked draft."
            elif trajectory.status in {"reduced_signal", "changed_evidence"}:
                status, confidence, observed = "partially_supported", "low", "The signal or its evidence changed in the linked draft."
            elif trajectory.status == "still_observed":
                status, confidence, observed = "not_observed", "low", "The prior diagnosis category is still observed."
            else:
                status, confidence, observed = "not_assessable", "insufficient", "No comparable trajectory is available."
            results.append(FeedbackUptakeCandidate(
                uptake_id=f"UP{index:03d}", previous_feedback_id=int(source.get("feedback_id") or 0),
                previous_diagnosis_id=item.get("diagnosis_id", "D000"),
                source_submission_id=source["essay_id"], target_submission_id=target["essay_id"],
                previous_guidance_summary=item.get("revision_guidance", ""), observed_change=observed,
                supporting_alignment_ids=alignment_ids[:5], status=status, confidence=confidence,
                limitations=["Observable consistency does not prove the feedback caused the revision.",
                             "Major rewrites weaken interpretation." if major else "Human review is required."],
            ))
        return results

    @staticmethod
    def _revision_evidence(comparability, token_changes, metrics, trajectories, uptake) -> list[dict[str, Any]]:
        evidence = [{
            "revision_evidence_id": "R001", "evidence_type": "revision_comparability",
            "description": f"Local rules classified the linked drafts as {comparability.status}.",
            "confidence": comparability.confidence, "limitations": comparability.reasons,
        }]
        evidence.append({
            "revision_evidence_id": "R002", "evidence_type": "token_change_summary",
            "description": (f"Observed inserted ratio {token_changes['inserted_ratio']}, deleted ratio "
                            f"{token_changes['deleted_ratio']}, modified ratio {token_changes['modified_ratio']}."),
            "confidence": "low", "limitations": ["Token changes do not indicate proficiency growth."],
        })
        for trajectory in trajectories[:2]:
            evidence.append({
                "revision_evidence_id": f"R{len(evidence)+1:03d}", "evidence_type": "diagnosis_trajectory",
                "description": f"{trajectory.diagnosis_category}: {trajectory.status}.",
                "confidence": trajectory.confidence, "limitations": trajectory.limitations,
            })
        for candidate in uptake[:1]:
            evidence.append({
                "revision_evidence_id": f"R{len(evidence)+1:03d}", "evidence_type": "feedback_uptake_candidate",
                "description": f"{candidate.previous_diagnosis_id}: {candidate.status}; {candidate.observed_change}",
                "confidence": candidate.confidence, "limitations": candidate.limitations,
            })
        return evidence
