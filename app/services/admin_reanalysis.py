from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.config import Settings
from app.services.configuration import ConfigurationService, settings_from_configuration
from app.services.factory import build_analyzer
from app.services.revision import RevisionService
from app.services.submission import SubmissionService


class ReanalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scope_type: Literal["submission", "revision_group", "student", "analysis_run"]
    scope_id: str = Field(min_length=1, max_length=100)
    analyzer_id: str | None = Field(default=None, max_length=100)
    configuration_version: str | None = Field(default=None, max_length=100)
    call_llm: bool = False
    confirm_llm_cost: bool = False

    @model_validator(mode="after")
    def confirm_paid_path(self) -> "ReanalysisRequest":
        if self.call_llm and not self.confirm_llm_cost:
            raise ValueError("confirm_llm_cost must be true when call_llm is requested")
        return self


class AdminReanalysisService:
    def __init__(self, repository, settings: Settings, configurations: ConfigurationService,
                 submission_service: SubmissionService) -> None:
        self.repository = repository
        self.settings = settings
        self.configurations = configurations
        self.submission_service = submission_service
        self.revisions = RevisionService(repository)

    def preview(self, request: ReanalysisRequest) -> dict[str, Any]:
        ids = self._scope(request)
        configuration = (
            self.configurations.active() if request.configuration_version is None
            else self.repository.get_configuration(request.configuration_version)
        )
        if configuration is None:
            raise LookupError("Configuration not found.")
        analyzer_id = request.analyzer_id or configuration.payload.active_analyzer
        analyzer = build_analyzer(settings_from_configuration(self.settings, configuration))
        analyzer.registry.get(analyzer_id)
        return {
            "scope_type": request.scope_type, "scope_id": request.scope_id,
            "submission_ids": ids, "submission_count": len(ids),
            "analyzer_id": analyzer_id,
            "analyzer_version": analyzer.registry.get(analyzer_id).version,
            "configuration_id": configuration.configuration_id,
            "configuration_version": configuration.version,
            "configuration_status": configuration.status,
            "configuration_validation_status": configuration.validation_status,
            "llm_requested": request.call_llm,
            "llm_cost_warning": (
                "Explicit LLM regeneration may incur provider charges."
                if request.call_llm else
                "Local Analyzer only; no LLM call will be made."
            ),
            "append_only": True,
            "limitations": ["Reanalysis creates new runs and does not retroactively validate earlier outputs."],
        }

    def run(self, request: ReanalysisRequest) -> dict[str, Any]:
        preview = self.preview(request)
        configuration = self.repository.get_configuration(preview["configuration_id"])
        if configuration.validation_status != "passed":
            raise ValueError("Reanalysis requires a validated configuration.")
        analyzer = build_analyzer(settings_from_configuration(self.settings, configuration)).registry.get(
            preview["analyzer_id"]
        )
        runs = []
        feedback = []
        for essay_id in preview["submission_ids"]:
            row = self.repository.get_submission_bundle(essay_id)
            analysis = analyzer.analyze(
                row["essay_text"], writing_prompt=row["writing_prompt"],
                draft_stage=row["draft_stage"], tool_use=row["tool_use"],
            )
            analysis = analysis.model_copy(update={"configuration_version": configuration.version})
            saved = self.repository.save_analysis_run(essay_id, analysis)
            runs.append({"submission_id": essay_id, "analysis_run_id": saved.analysis_run_id})
            if request.call_llm:
                generated = self.submission_service.regenerate_feedback(essay_id, saved)
                feedback.append({
                    "submission_id": essay_id, "provider": generated.provider_name,
                    "success_status": generated.success_status, "prompt_version": generated.prompt_version,
                })
        snapshots = []
        group_ids = {
            self.repository.get_submission_bundle(essay_id).get("revision_group_id")
            for essay_id in preview["submission_ids"]
        } - {None}
        for group_id in sorted(group_ids):
            group = self.revisions.group(group_id)
            for source_id, target_id in zip(group.member_submission_ids, group.member_submission_ids[1:]):
                snapshot = self.revisions.recalculate(group_id, source_id, target_id)
                snapshots.append(snapshot.revision_snapshot_id)
        return {
            **preview, "analysis_runs": runs, "revision_snapshot_ids": snapshots,
            "llm_called": request.call_llm, "feedback_records": feedback,
        }

    def _scope(self, request: ReanalysisRequest) -> list[int]:
        if request.scope_type == "submission":
            try:
                essay_id = int(request.scope_id)
            except ValueError as exc:
                raise ValueError("submission scope_id must be an integer") from exc
            if self.repository.get_submission_bundle(essay_id) is None:
                raise LookupError("Submission not found.")
            return [essay_id]
        if request.scope_type == "student":
            items = self.repository.list_student_submissions(request.scope_id)
            if not items:
                raise LookupError("Student has no submissions.")
            return [int(item["essay_id"]) for item in items]
        if request.scope_type == "revision_group":
            group = self.repository.get_revision_group(request.scope_id)
            if group is None:
                raise LookupError("Revision group not found.")
            return group.member_submission_ids
        run = self.repository.get_analysis_run(request.scope_id)
        if run is None:
            raise LookupError("AnalysisRun not found.")
        return [int(run["essay_id"])]
