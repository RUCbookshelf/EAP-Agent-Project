from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from app.errors import (
    CATEGORY_HTTP_STATUS,
    CATEGORY_MESSAGE_KEY,
    ApiError,
    ErrorCategory,
)


# ---------------------------------------------------------------------------
# Timeout policy (centralized). Local healthy endpoints were observed well
# under 100 ms; these profiles are about prompt failure detection, not server
# performance tuning.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TimeoutProfile:
    connect: float = 2.0
    read: float = 10.0
    write: float = 30.0


# Long-read profile for operations that legitimately reconstruct a large
# learner model or run an export.
LONG_READ_TIMEOUTS = TimeoutProfile(connect=2.0, read=60.0, write=30.0)
# Long-submit profile for the linked-revision submit path only: the backend
# runs the full analysis + provider feedback pipeline (measured provider calls
# of 30-38 s in the v0.9.6-A incident), so this path uses a dedicated bounded
# 180 s wait instead of the generic 30 s write timeout. Ordinary requests and
# every other submit path keep DEFAULT_TIMEOUTS.
LONG_SUBMIT_TIMEOUTS = TimeoutProfile(connect=2.0, read=180.0, write=180.0)
LIFECYCLE_TIMEOUTS = TimeoutProfile(connect=2.0, read=5.0, write=10.0)
DEFAULT_TIMEOUTS = TimeoutProfile()


class ApiClientError(RuntimeError):
    """Classified API client error with a canonical category."""

    def __init__(
        self,
        category: ErrorCategory,
        message: str,
        *,
        operation: str = "",
        request_id: str | None = None,
        http_status: int | None = None,
        detail: str | None = None,
        field_errors: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.message_key = CATEGORY_MESSAGE_KEY[category]
        self.operation = operation
        self.request_id = request_id
        self.http_status = http_status
        self.detail = detail
        self.field_errors = field_errors or []
        self.retryable = category in (
            ErrorCategory.SERVICE_STARTING,
            ErrorCategory.CONNECTION_INTERRUPTED,
            ErrorCategory.REQUEST_TIMEOUT,
        )

    @property
    def user_message(self) -> str:
        return str(self)

    def to_public(self, *, include_detail: bool = False) -> dict[str, Any]:
        err = ApiError.from_category(
            self.category, self.operation,
            request_id=self.request_id, http_status=self.http_status,
            detail=self.detail, field_errors=self.field_errors,
        )
        return err.to_public_dict(include_detail=include_detail)


def classify_exception(exc: requests.RequestException, operation: str) -> ApiClientError:
    """Map a requests exception to a canonical client error."""
    if isinstance(exc, requests.exceptions.ConnectTimeout):
        return ApiClientError(ErrorCategory.REQUEST_TIMEOUT, "connect timed out", operation=operation)
    if isinstance(exc, requests.exceptions.ReadTimeout):
        return ApiClientError(ErrorCategory.REQUEST_TIMEOUT, "read timed out", operation=operation)
    if isinstance(exc, requests.exceptions.ConnectionError):
        return ApiClientError(ErrorCategory.SERVICE_NOT_RUNNING, "connection refused", operation=operation)
    if isinstance(exc, requests.exceptions.ChunkedEncodingError):
        return ApiClientError(ErrorCategory.CONNECTION_INTERRUPTED, "connection interrupted", operation=operation)
    return ApiClientError(ErrorCategory.UNKNOWN_ERROR, str(exc)[:200], operation=operation)


class WritingFeedbackApiClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 15.0,
        session=None,
        timeouts: TimeoutProfile | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout  # kept for backward compatibility
        self.timeouts = timeouts or DEFAULT_TIMEOUTS
        self.session = session or requests.Session()

    # -- request core ------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        operation: str = "",
        profile: TimeoutProfile | None = None,
        retry: bool = False,
        **kwargs,
    ) -> dict[str, Any]:
        """Perform a classified request with bounded safe retry.

        Automatic retry is permitted ONLY for read-only GET requests and only
        for connection-interrupted/timeout categories. State-changing methods
        are never automatically retried.
        """
        profile = profile or self.timeouts
        timeout_tuple = (profile.connect, profile.read) if method == "GET" else (profile.connect, profile.write)
        if "timeout" in kwargs:
            kwargs.pop("timeout")

        attempts = 2 if (retry and method == "GET") else 1
        last_error: ApiClientError | None = None
        for attempt in range(attempts):
            try:
                response = self.session.request(
                    method, f"{self.base_url}{path}", timeout=timeout_tuple, **kwargs
                )
            except requests.RequestException as exc:
                last_error = classify_exception(exc, operation)
                if attempt + 1 < attempts and last_error.retryable:
                    continue
                raise last_error from exc
            try:
                payload = response.json()
            except ValueError as exc:
                raise ApiClientError(
                    ErrorCategory.INVALID_RESPONSE,
                    "The local feedback API returned an unreadable response.",
                    operation=operation,
                    request_id=getattr(response, "headers", {}).get("X-Request-ID"),
                    http_status=response.status_code,
                ) from exc
            if response.status_code >= 400:
                raise self._classify_http(response, payload, operation)
            return payload
        raise last_error  # pragma: no cover

    def _classify_http(self, response, payload: Any, operation: str) -> ApiClientError:
        request_id = getattr(response, "headers", {}).get("X-Request-ID")
        err = payload.get("error", {}) if isinstance(payload, dict) else {}
        category_raw = err.get("category")
        try:
            category = ErrorCategory(category_raw) if category_raw else self._infer_category(response.status_code)
        except ValueError:
            category = self._infer_category(response.status_code)
        message = err.get("detail") or err.get("message") or f"Request failed with status {response.status_code}."
        return ApiClientError(
            category, message, operation=operation, request_id=request_id,
            http_status=response.status_code,
            detail=err.get("detail") if isinstance(err.get("detail"), str) else None,
            field_errors=err.get("field_errors") if isinstance(err.get("field_errors"), list) else None,
        )

    @staticmethod
    def _infer_category(status: int) -> ErrorCategory:
        for category, http in CATEGORY_HTTP_STATUS.items():
            if http == status:
                return category
        return ErrorCategory.BACKEND_PROCESSING_ERROR

    # -- lifecycle ---------------------------------------------------------

    def live(self) -> dict[str, Any]:
        try:
            return self._request("GET", "/api/v1/system/live", operation="live", profile=LIFECYCLE_TIMEOUTS, retry=True)
        except ApiClientError as exc:
            if exc.category == ErrorCategory.SERVICE_NOT_RUNNING:
                return {"status": "process_not_running", "lifecycle_state": "unknown"}
            return {"status": "unknown", "lifecycle_state": "unknown", "error": str(exc)}

    def ready(self) -> dict[str, Any]:
        try:
            return self._request("GET", "/api/v1/system/ready", operation="ready", profile=LIFECYCLE_TIMEOUTS, retry=True)
        except ApiClientError as exc:
            return {"status": "not_reachable", "ready": False, "error": str(exc)}

    def lifecycle_state(self) -> str:
        try:
            data = self.live()
            return data.get("lifecycle_state", "unknown")
        except Exception:
            return "unknown"

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/system/health", operation="health", profile=LIFECYCLE_TIMEOUTS, retry=True)

    # -- submissions / learner model (read-only GETs retryable) ------------

    def _submit_long_running(self, submission: dict[str, Any]) -> dict[str, Any]:
        """Private shared long-running essay-submission transport.

        One POST to /api/v1/submissions with the dedicated long-operation
        timeout (LONG_SUBMIT_TIMEOUTS) covering the full analysis + provider
        feedback pipeline. Never automatically retried (retry applies only
        to GET requests). Used by both the first-draft submission entry and
        the linked-revision submission entry.
        """
        return self._request(
            "POST", "/api/v1/submissions", operation="submit",
            json=submission, profile=LONG_SUBMIT_TIMEOUTS,
        )

    def submit(self, submission: dict[str, Any]) -> dict[str, Any]:
        """Submit a first draft (or writing-page revision) reliably."""
        return self._submit_long_running(submission)

    def submit_linked_revision(self, submission: dict[str, Any]) -> dict[str, Any]:
        """Submit a linked revision with the shared reliable transport."""
        return self._submit_long_running(submission)

    def get_submission(self, submission_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/submissions/{submission_id}", operation="get_submission", retry=True)

    def get_analyses(self, submission_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/submissions/{submission_id}/analyses", operation="get_analyses", retry=True)

    def get_diagnostic_audit(self, submission_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/submissions/{submission_id}/diagnostic-audit", operation="diagnostic_audit", retry=True)

    def reanalyze(self, submission_id: int) -> dict[str, Any]:
        return self._request("POST", f"/api/v1/submissions/{submission_id}/analyses", operation="reanalyze")

    def get_calf(self, submission_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/submissions/{submission_id}/calf", operation="get_calf", retry=True)

    def get_calf_constructs(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/calf/constructs", operation="calf_constructs", retry=True)

    def get_calf_metrics(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/calf/metrics", operation="calf_metrics", retry=True)

    def get_student_revision_candidates(self, student_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/students/{student_id}/revision-candidates", operation="revision_candidates", retry=True)

    def create_revision(self, source_submission_id: int, target_submission_id: int) -> dict[str, Any]:
        return self._request("POST", "/api/v1/revisions", operation="create_revision", json={
            "source_submission_id": source_submission_id, "target_submission_id": target_submission_id,
        })

    def get_revision_group(self, revision_group_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/revisions/{revision_group_id}", operation="revision_group", retry=True)

    def get_revision_comparison(self, revision_group_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/revisions/{revision_group_id}/comparison", operation="revision_comparison", retry=True)

    def get_revision_trajectory(self, revision_group_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/revisions/{revision_group_id}/trajectory", operation="revision_trajectory", retry=True)

    def get_revision_candidates(self, submission_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/submissions/{submission_id}/revision-candidates", operation="revision_candidates", retry=True)

    def get_revision_analysis(self, submission_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/submissions/{submission_id}/revision-analysis", operation="revision_analysis", retry=True)

    def get_dashboard(self, student_id: str, metric_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/students/{student_id}/dashboard", operation="dashboard", params={"metric_id": metric_id}, retry=True)

    def get_learner_model(self, student_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/students/{student_id}/learner-model", operation="learner_model", profile=LONG_READ_TIMEOUTS, retry=True)

    def get_learner_model_snapshots(self, student_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/students/{student_id}/learner-model/snapshots", operation="learner_snapshots", profile=LONG_READ_TIMEOUTS, retry=True)

    def get_learner_model_snapshot(self, student_id: str, snapshot_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/students/{student_id}/learner-model/snapshots/{snapshot_id}", operation="learner_snapshot", profile=LONG_READ_TIMEOUTS, retry=True)

    def preview_learner_model(self, student_id: str, strategy: str) -> dict[str, Any]:
        return self._request("POST", f"/api/v1/students/{student_id}/learner-model/preview", operation="learner_preview",
                             json={"representative_draft_strategy": strategy, "max_submissions": 200})

    def rebuild_learner_model(self, student_id: str, strategy: str) -> dict[str, Any]:
        return self._request("POST", f"/api/v1/students/{student_id}/learner-model/rebuild", operation="learner_rebuild",
                             json={"representative_draft_strategy": strategy, "max_submissions": 200})

    def get_configurations(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/admin/configurations", operation="configurations", retry=True)

    def create_configuration(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/admin/configurations", operation="create_configuration", json=payload)

    def validate_configuration(self, configuration_id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/v1/admin/configurations/{configuration_id}/validate", operation="validate_configuration")

    def activate_configuration(self, configuration_id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/v1/admin/configurations/{configuration_id}/activate", operation="activate_configuration")

    def rollback_configuration(self, configuration_id: str, reason: str) -> dict[str, Any]:
        return self._request(
            "POST", f"/api/v1/admin/configurations/{configuration_id}/rollback", operation="rollback_configuration",
            json={"reason": reason, "actor": "local_researcher"},
        )

    def get_registries(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/admin/registries", operation="registries", retry=True)

    def preview_reanalysis(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/admin/reanalysis/preview", operation="reanalysis_preview", json=payload)

    def run_reanalysis(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/admin/reanalysis/run", operation="reanalysis_run", json=payload)

    # -- research ----------------------------------------------------------

    def research_export_preview(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/research/export/preview", operation="export_preview", json=payload)

    def research_export_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/research/export/run", operation="export_run", profile=LONG_READ_TIMEOUTS, json=payload)

    def research_export_schema(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/research/export/schema", operation="export_schema", retry=True)

    def research_data_quality(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/research/data-quality", operation="data_quality", retry=True)

    def get_pii_candidates(self, submission_id: int) -> list[dict[str, Any]]:
        return self._request("GET", f"/api/v1/submissions/{submission_id}/pii-candidates", operation="pii_candidates", retry=True)

    def create_human_review(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/research/reviews", operation="create_human_review", json=payload)

    def list_human_reviews(self, target_type: str | None = None, target_id: str | None = None) -> list[dict[str, Any]]:
        params = "?" + "&".join(f"{k}={v}" for k, v in [("target_type", target_type), ("target_id", target_id)] if v)
        return self._request("GET", f"/api/v1/research/reviews{params}" if params else "/api/v1/research/reviews", operation="list_human_reviews", retry=True)

    def research_export_history(self) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/research/export/history", operation="export_history", retry=True)

    def research_export_manifest(self, export_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/research/export/{export_id}/manifest", operation="export_manifest", retry=True)

    def create_dataset_split(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/research/dataset-split", operation="dataset_split", json=payload)

    # -- practice ----------------------------------------------------------

    def get_practice_targets(self, student_id: str) -> list[dict[str, Any]]:
        return self._request("GET", f"/api/v1/students/{student_id}/practice-targets", operation="practice_targets", retry=True)

    def create_practice_target(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/practice-targets", operation="create_practice_target", json=payload)

    def create_exercise(self, practice_target_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", f"/api/v1/practice-targets/{practice_target_id}/exercises", operation="create_exercise", json=payload)

    def submit_exercise_attempt(self, exercise_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", f"/api/v1/exercises/{exercise_id}/attempts", operation="submit_exercise_attempt", json=payload)

    def get_engagement_traces(self, student_id: str) -> list[dict[str, Any]]:
        return self._request("GET", f"/api/v1/students/{student_id}/engagement-traces", operation="engagement_traces", retry=True)

    def get_transfer_evidence(self, student_id: str) -> list[dict[str, Any]]:
        return self._request("GET", f"/api/v1/students/{student_id}/transfer-evidence", operation="transfer_evidence", retry=True)

    def get_journey(self, student_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/students/{student_id}/journey", operation="learning_journey", retry=True)

    def get_exercise_instances(self, practice_target_id: str) -> list[dict[str, Any]]:
        return self._request("GET", f"/api/v1/practice-targets/{practice_target_id}/exercises", operation="practice_exercises", retry=True)

    def get_exercise_attempts(self, exercise_id: str) -> list[dict[str, Any]]:
        return self._request("GET", f"/api/v1/exercises/{exercise_id}/attempts", operation="exercise_attempts", retry=True)
