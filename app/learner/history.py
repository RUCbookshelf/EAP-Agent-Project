from __future__ import annotations

from collections import Counter
from typing import Any, Protocol, runtime_checkable

from app.models import (
    AnalysisResult,
    DiagnosisResult,
    EssaySubmission,
    HistoryEvidence,
    HistoryResult,
)


HISTORY_LIMITATION = (
    "This evidence is produced by prototype heuristic metrics and diagnoses; it does not establish "
    "language-ability improvement, decline, mastery, or regression."
)


@runtime_checkable
class PriorRecordsPort(Protocol):
    """Consumer-owned one-method read port for earlier-submission records."""

    def prior_records(self, submission: EssaySubmission) -> list[dict[str, Any]]: ...


class LearnerHistoryService:
    """Build human-readable and ID-addressable longitudinal evidence."""

    def __init__(self, database: PriorRecordsPort):
        self.database = database

    def summarize(self, essay_id: int, submission: EssaySubmission, current_analysis: AnalysisResult,
                  current_diagnosis: DiagnosisResult) -> HistoryResult:
        prior = self.database.prior_records(submission)
        if not prior:
            return HistoryResult(
                comparability_status="insufficient_history", comparable_submission_count=0,
                history_evidence=[], summary="数据不足，无法判断趋势。",
                limitations=[HISTORY_LIMITATION],
                comparability_reasons=["No earlier submission exists for this student_id."],
            )

        comparable: list[dict[str, Any]] = []
        partial: list[dict[str, Any]] = []
        excluded: list[str] = []
        reasons: list[str] = []
        for record in prior:
            status, reason = self._classify(record, submission)
            submission_id = self._submission_id(record["essay_id"])
            reasons.append(f"{submission_id}: {reason}")
            if status == "comparable":
                comparable.append(record)
            elif status == "partially_comparable":
                partial.append(record)
            else:
                excluded.append(submission_id)

        if comparable:
            status = "comparable"
            eligible = comparable + partial
        elif partial:
            status = "partially_comparable"
            eligible = partial
        else:
            return HistoryResult(
                comparability_status="not_comparable", comparable_submission_count=0,
                history_evidence=[],
                summary="数据不足，无法判断趋势。已发现更早作文，但记录的任务条件不可比。",
                limitations=[HISTORY_LIMITATION], comparability_reasons=reasons,
                excluded_submission_ids=excluded,
            )

        evidence = self._build_evidence(
            essay_id, eligible, current_analysis, current_diagnosis
        )
        summary = self._human_summary(status, len(eligible), evidence)
        return HistoryResult(
            comparability_status=status,
            comparable_submission_count=len(eligible),
            history_evidence=evidence,
            summary=summary,
            limitations=[HISTORY_LIMITATION],
            comparability_reasons=reasons,
            excluded_submission_ids=excluded,
        )

    @staticmethod
    def _classify(record: dict[str, Any], submission: EssaySubmission) -> tuple[str, str]:
        checks = {
            "student_id": record["student_id"] == submission.student_id,
            "genre": record["genre"] == submission.genre,
            "draft_stage": record["draft_stage"] == submission.draft_stage,
            "timed": bool(record["timed"]) == submission.timed,
            "time_limit_minutes": record.get("time_limit_minutes") == submission.time_limit_minutes,
            "tool_use": record["tool_use"] == submission.tool_use,
            "writing_prompt": LearnerHistoryService._normalize(record["writing_prompt"])
            == LearnerHistoryService._normalize(submission.writing_prompt),
        }
        mismatches = [name for name, passed in checks.items() if not passed]
        if not mismatches:
            return "comparable", "All recorded task conditions match."
        if mismatches == ["draft_stage"]:
            return (
                "partially_comparable",
                "Only draft_stage differs; v0.1.1 explicitly allows this limited revision comparison.",
            )
        return "not_comparable", "Excluded because these conditions differ: " + ", ".join(mismatches) + "."

    def _build_evidence(self, essay_id: int, eligible: list[dict[str, Any]],
                        current_analysis: AnalysisResult,
                        current_diagnosis: DiagnosisResult) -> list[HistoryEvidence]:
        evidence: list[HistoryEvidence] = []
        latest = eligible[-1]
        old_metrics = latest.get("metrics", {})
        changes: list[str] = []
        for key in ("word_count", "connective_count", "type_token_ratio"):
            if key in old_metrics and key in current_analysis.metrics:
                old = old_metrics[key]
                current = current_analysis.metrics[key]
                changes.append(f"{key}: {old} -> {current}")
        if changes:
            evidence.append(HistoryEvidence(
                history_evidence_id="H001", evidence_type="metric_change",
                description="Descriptive surface-metric comparison with the latest eligible submission: "
                + "; ".join(changes) + ".",
                supporting_submission_ids=[
                    self._submission_id(latest["essay_id"]), self._submission_id(essay_id)
                ],
                comparable_submission_count=len(eligible), confidence="low",
                limitation=HISTORY_LIMITATION,
            ))

        previous_categories: list[tuple[str, int]] = []
        for record in eligible:
            for item in record.get("diagnosis", {}).get("improvement_priorities", []):
                if item.get("category"):
                    previous_categories.append((item["category"], record["essay_id"]))
        current_categories = [item.category for item in current_diagnosis.improvement_priorities]
        category_counts = Counter([category for category, _ in previous_categories] + current_categories)
        for category, count in sorted(category_counts.items()):
            if count < 2 or category not in current_categories:
                continue
            supporting = [
                self._submission_id(record_id)
                for old_category, record_id in previous_categories if old_category == category
            ] + [self._submission_id(essay_id)]
            evidence.append(HistoryEvidence(
                history_evidence_id=f"H{len(evidence) + 1:03d}",
                evidence_type="repeated_diagnosis",
                description=(
                    f"The prototype diagnosis '{category}' appears {count} times across the current "
                    f"submission and {len(eligible)} eligible earlier submission(s)."
                ),
                supporting_submission_ids=supporting,
                comparable_submission_count=len(eligible), confidence="low",
                limitation=HISTORY_LIMITATION,
            ))

        current_set = set(current_categories)
        for category in sorted({category for category, _ in previous_categories} - current_set):
            supporting = [
                self._submission_id(record_id)
                for old_category, record_id in previous_categories if old_category == category
            ] + [self._submission_id(essay_id)]
            evidence.append(HistoryEvidence(
                history_evidence_id=f"H{len(evidence) + 1:03d}",
                evidence_type="previous_flag_not_current",
                description=(
                    f"The prototype diagnosis '{category}' appeared in eligible earlier submission(s) "
                    "but was not selected for the current submission."
                ),
                supporting_submission_ids=supporting,
                comparable_submission_count=len(eligible), confidence="low",
                limitation=HISTORY_LIMITATION,
            ))
        return evidence

    @staticmethod
    def _human_summary(status: str, count: int, evidence: list[HistoryEvidence]) -> str:
        evidence_types = ", ".join(item.evidence_type for item in evidence) or "none"
        return (
            f"History status is {status}. {count} earlier submission(s) were eligible. "
            f"Available prototype evidence types: {evidence_types}. "
            "These descriptive signals do not establish genuine ability change."
        )

    @staticmethod
    def _submission_id(essay_id: int) -> str:
        return f"E{essay_id:06d}"

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.casefold().split())
