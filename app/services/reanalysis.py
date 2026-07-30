from __future__ import annotations

from app.analysis import AnalyzerProtocol
from app.models import AnalysisResult
from app.repositories import EssayRepository, MetricRepository
from app.calf import append_product_fluency_metric
from app.models import EssaySubmission


class ReanalysisRepository(EssayRepository, MetricRepository):
    pass


class ReanalysisService:
    """Append a local AnalysisRun without changing compatibility metrics or invoking an LLM."""

    def __init__(self, repository: ReanalysisRepository, analyzer: AnalyzerProtocol) -> None:
        self.repository = repository
        self.analyzer = analyzer

    def run(self, submission_id: int) -> AnalysisResult:
        row = self.repository.get_submission_bundle(submission_id)
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
        return self.repository.save_analysis_run(submission_id, analysis)
