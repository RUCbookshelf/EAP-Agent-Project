from __future__ import annotations

from app.analysis import AnalyzerProtocol
from app.models import AnalysisResult
from app.repositories import EssayRepository, MetricRepository


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
        return self.repository.save_analysis_run(submission_id, analysis)
