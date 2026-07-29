from __future__ import annotations

from typing import Any

import requests


class ApiClientError(RuntimeError):
    pass


class WritingFeedbackApiClient:
    def __init__(self, base_url: str, *, timeout: float = 90.0, session=None) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        try:
            response = self.session.request(
                method, f"{self.base_url}{path}", timeout=self.timeout, **kwargs
            )
        except requests.RequestException as exc:
            raise ApiClientError(
                "The local feedback API is unavailable. Start run.bat and try again."
            ) from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise ApiClientError("The local feedback API returned an unreadable response.") from exc
        if response.status_code >= 400:
            message = payload.get("error", {}).get("message", "The request was rejected.")
            raise ApiClientError(message)
        return payload

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/system/health")

    def submit(self, submission: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/submissions", json=submission)

    def get_submission(self, submission_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/submissions/{submission_id}")

    def get_analyses(self, submission_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/submissions/{submission_id}/analyses")

    def get_diagnostic_audit(self, submission_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/submissions/{submission_id}/diagnostic-audit")

    def reanalyze(self, submission_id: int) -> dict[str, Any]:
        return self._request("POST", f"/api/v1/submissions/{submission_id}/analyses")

    def get_student_revision_candidates(self, student_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/students/{student_id}/revision-candidates")

    def create_revision(self, source_submission_id: int, target_submission_id: int) -> dict[str, Any]:
        return self._request("POST", "/api/v1/revisions", json={
            "source_submission_id": source_submission_id, "target_submission_id": target_submission_id,
        })

    def get_revision_group(self, revision_group_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/revisions/{revision_group_id}")

    def get_revision_comparison(self, revision_group_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/revisions/{revision_group_id}/comparison")

    def get_revision_candidates(self, submission_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/submissions/{submission_id}/revision-candidates")

    def get_revision_analysis(self, submission_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/submissions/{submission_id}/revision-analysis")

    def get_dashboard(self, student_id: str, metric_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/students/{student_id}/dashboard", params={"metric_id": metric_id})

    def get_learner_model(self, student_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/students/{student_id}/learner-model")

    def get_learner_model_snapshots(self, student_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/students/{student_id}/learner-model/snapshots")

    def get_learner_model_snapshot(self, student_id: str, snapshot_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/students/{student_id}/learner-model/snapshots/{snapshot_id}")

    def preview_learner_model(self, student_id: str, strategy: str) -> dict[str, Any]:
        return self._request("POST", f"/api/v1/students/{student_id}/learner-model/preview",
                             json={"representative_draft_strategy": strategy, "max_submissions": 200})

    def rebuild_learner_model(self, student_id: str, strategy: str) -> dict[str, Any]:
        return self._request("POST", f"/api/v1/students/{student_id}/learner-model/rebuild",
                             json={"representative_draft_strategy": strategy, "max_submissions": 200})

    def get_configurations(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/admin/configurations")

    def create_configuration(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/admin/configurations", json=payload)

    def validate_configuration(self, configuration_id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/v1/admin/configurations/{configuration_id}/validate")

    def activate_configuration(self, configuration_id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/v1/admin/configurations/{configuration_id}/activate")

    def rollback_configuration(self, configuration_id: str, reason: str) -> dict[str, Any]:
        return self._request(
            "POST", f"/api/v1/admin/configurations/{configuration_id}/rollback",
            json={"reason": reason, "actor": "local_researcher"},
        )

    def get_registries(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/admin/registries")

    def preview_reanalysis(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/admin/reanalysis/preview", json=payload)

    def run_reanalysis(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/admin/reanalysis/run", json=payload)
