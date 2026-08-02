from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.analysis import AnalyzerProtocol
from app.calf import append_product_fluency_metric
from app.models import AnalysisResult, EssaySubmission


@runtime_checkable
class SubmissionBundleReadPort(Protocol):
    """Read contract for one Submission-owned bundle (ReanalysisService)."""

    def get_submission_bundle(self, essay_id: int) -> dict[str, Any] | None: ...


@runtime_checkable
class AnalysisRunWritePort(Protocol):
    """Append-only write contract for one Analysis-owned run (ReanalysisService)."""

    def save_analysis_run(self, essay_id: int, analysis: AnalysisResult) -> AnalysisResult: ...


class ReanalysisService:
    """Append a local AnalysisRun without changing compatibility metrics or invoking an LLM."""

    def __init__(
        self,
        submission_reader: SubmissionBundleReadPort,
        analysis_writer: AnalysisRunWritePort,
        analyzer: AnalyzerProtocol,
    ) -> None:
        self.submission_reader = submission_reader
        self.analysis_writer = analysis_writer
        self.analyzer = analyzer

    def run(self, submission_id: int) -> AnalysisResult:
        row = self.submission_reader.get_submission_bundle(submission_id)
        if row is None:
            raise LookupError("Submission not found.")
        analysis = self.analyzer.analyze(
            row["essay_text"], writing_prompt=row["writing_prompt"],
            draft_stage=row["draft_stage"], tool_use=row["tool_use"],
        )
        submission = EssaySubmission.model_validate({
            name: row[name] for name in EssaySubmission.model_fields if name in row
        })
        analysis = append_product_fluency_metric(analysis, submission)
        return self.analysis_writer.save_analysis_run(submission_id, analysis)
