"""HTTP client for the Wave-2 API contracts (revision/personalized/learner).

Fail-closed availability classification:

- connection failures, timeouts, and HTTP 404/405/503 on a Wave-2 route
  mean the endpoint is not wired up yet -> ``Wave2ApiUnavailable`` (the UI
  degrades to the existing writing/feedback flow).
- every other 4xx/5xx is a real service error -> ``Wave2ApiClientError``.
- GET requests are safe to retry once on interrupt/timeout; state-changing
  methods are never retried automatically.
"""

from __future__ import annotations

from typing import Any

import requests

from app.ui.api_client import TimeoutProfile
from app.ui.wave2.contracts import (
    LEARNER_DIFFICULTIES,
    LEARNER_EVIDENCE,
    LEARNER_OBSERVATION,
    LEARNER_OBSERVATIONS,
    LEARNER_PROFICIENCY_CONTEXT,
    LEARNER_STABLE,
    LEARNER_STRENGTHS,
    PERSONALIZED_LEARNING_ITEM,
    PERSONALIZED_LEARNING_ITEMS,
    PERSONALIZED_PRIORITY_PLAN,
    PERSONALIZED_SCAFFOLD,
    PROBE_PATH,
    REVISION_OBSERVATION,
    REVISION_REVISIONS,
    REVISION_SUBMISSIONS,
    REVISION_TASK,
    REVISION_TASKS,
    REVISION_VERSIONS,
    UNAVAILABLE_STATUSES,
)


class Wave2ApiUnavailable(RuntimeError):
    """The Wave-2 endpoint is not reachable/wired up; use the legacy flow."""

    def __init__(self, message: str = "Wave-2 endpoint unavailable.", *, operation: str = "") -> None:
        super().__init__(message)
        self.operation = operation


class Wave2ApiClientError(RuntimeError):
    """A classified Wave-2 service error (4xx/5xx other than 404/405/503)."""

    def __init__(self, message: str, *, http_status: int | None = None, operation: str = "") -> None:
        super().__init__(message)
        self.http_status = http_status
        self.operation = operation


def _classify_request_exception(exc: requests.RequestException, operation: str) -> Wave2ApiUnavailable:
    if isinstance(exc, (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout)):
        return Wave2ApiUnavailable("Wave-2 endpoint timed out.", operation=operation)
    if isinstance(exc, requests.exceptions.ConnectionError):
        return Wave2ApiUnavailable("Wave-2 endpoint is not running.", operation=operation)
    return Wave2ApiUnavailable(f"Wave-2 request failed: {exc}", operation=operation)


class Wave2ApiClient:
    """HTTP client for the Wave-2 contracts (used at integration)."""

    def __init__(self, base_url: str, *, session: requests.Session | None = None,
                 timeouts: TimeoutProfile | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeouts = timeouts or TimeoutProfile()
        self._probe_cache: bool | None = None

    # -- request core --------------------------------------------------------

    def _request(self, method: str, path: str, *, operation: str,
                 params: dict[str, Any] | None = None,
                 json: dict[str, Any] | None = None,
                 profile: TimeoutProfile | None = None,
                 retry: bool = False) -> dict[str, Any]:
        profile = profile or self.timeouts
        timeout_tuple = (profile.connect, profile.read) if method == "GET" else (profile.connect, profile.write)
        attempts = 2 if (retry and method == "GET") else 1
        last_error: Wave2ApiUnavailable | None = None
        url = f"{self.base_url}{path}"
        if params:
            from urllib.parse import urlencode
            url = f"{url}?{urlencode(sorted(params.items()))}"
        for attempt in range(attempts):
            try:
                response = self.session.request(
                    method, url, timeout=timeout_tuple,
                    json=json,
                )
            except requests.RequestException as exc:
                last_error = _classify_request_exception(exc, operation)
                if attempt + 1 < attempts:
                    continue
                raise last_error from exc
            if response.status_code in UNAVAILABLE_STATUSES:
                raise Wave2ApiUnavailable(
                    f"Wave-2 endpoint returned HTTP {response.status_code}.",
                    operation=operation,
                )
            if response.status_code >= 400:
                raise Wave2ApiClientError(
                    f"Wave-2 request failed with status {response.status_code}.",
                    http_status=response.status_code, operation=operation,
                )
            try:
                return response.json()
            except ValueError as exc:
                raise Wave2ApiClientError(
                    "Wave-2 endpoint returned an unreadable response.",
                    http_status=response.status_code, operation=operation,
                ) from exc
        raise last_error  # pragma: no cover

    # -- availability --------------------------------------------------------

    def probe(self) -> bool:
        """True when the Wave-2 namespace answers a bounded GET (cached)."""
        if self._probe_cache is not None:
            return self._probe_cache
        try:
            self._request("GET", PROBE_PATH, operation="probe",
                          params={"learner_id": "__probe__"}, retry=True)
            self._probe_cache = True
        except (Wave2ApiUnavailable, Wave2ApiClientError):
            self._probe_cache = False  # fail closed
        return self._probe_cache

    # -- revision API --------------------------------------------------------

    def create_task(self, student_id: str, task_type: str, writing_context: str,
                    writing_prompt: str, *, metadata: dict[str, Any] | None = None,
                    declared_task_type: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "student_id": student_id, "task_type": task_type,
            "writing_context": writing_context, "writing_prompt": writing_prompt,
        }
        if metadata is not None:
            body["metadata"] = metadata
        if declared_task_type is not None:
            body["declared_task_type"] = declared_task_type
        return self._request("POST", REVISION_TASKS, operation="create_task", json=body)

    def get_task(self, task_id: str) -> dict[str, Any]:
        return self._request("GET", REVISION_TASK.format(task_id=task_id),
                             operation="get_task", retry=True)

    def submit_v1(self, task_id: str, essay_text: str, *,
                  draft_stage: str = "first draft", tool_use: str = "none") -> dict[str, Any]:
        return self._request(
            "POST", REVISION_SUBMISSIONS.format(task_id=task_id),
            operation="submit_v1",
            json={"essay_text": essay_text, "draft_stage": draft_stage, "tool_use": tool_use},
        )

    def revise(self, task_id: str, submission_id: int, essay_text: str, *,
               draft_stage: str = "revised draft", tool_use: str = "none") -> dict[str, Any]:
        return self._request(
            "POST", REVISION_REVISIONS.format(task_id=task_id, submission_id=submission_id),
            operation="revise",
            json={"essay_text": essay_text, "draft_stage": draft_stage, "tool_use": tool_use},
        )

    def version_history(self, task_id: str) -> dict[str, Any]:
        return self._request("GET", REVISION_VERSIONS.format(task_id=task_id),
                             operation="version_history", retry=True)

    def revision_observation(self, task_id: str, submission_id: int) -> dict[str, Any]:
        return self._request(
            "GET", REVISION_OBSERVATION.format(task_id=task_id, submission_id=submission_id),
            operation="revision_observation", retry=True,
        )

    # -- personalized API ----------------------------------------------------

    def priority_plan(self, learner_id: str, task_id: str, submission_id: int) -> dict[str, Any]:
        return self._request(
            "POST", PERSONALIZED_PRIORITY_PLAN, operation="priority_plan",
            json={"learner_id": learner_id, "task_id": task_id, "submission_id": submission_id},
        )

    def scaffold(self, learner_id: str, category: str, *, level: int | None = None,
                 plan_item_id: str | None = None, learning_item_id: str | None = None,
                 evidence: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"learner_id": learner_id, "category": category}
        if level is not None:
            body["level"] = level
        if plan_item_id is not None:
            body["plan_item_id"] = plan_item_id
        if learning_item_id is not None:
            body["learning_item_id"] = learning_item_id
        if evidence is not None:
            body["evidence"] = evidence
        return self._request("POST", PERSONALIZED_SCAFFOLD, operation="scaffold", json=body)

    def list_learning_items(self, student_id: str, *, status: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"student_id": student_id}
        if status is not None:
            params["status"] = status
        return self._request("GET", PERSONALIZED_LEARNING_ITEMS, operation="list_learning_items",
                             params=params, retry=True)

    def create_learning_item(self, learner_id: str, plan_item_id: str) -> dict[str, Any]:
        return self._request(
            "POST", PERSONALIZED_LEARNING_ITEMS, operation="create_learning_item",
            json={"learner_id": learner_id, "plan_item_id": plan_item_id},
        )

    def update_learning_item_status(self, learning_item_id: str, status: str) -> dict[str, Any]:
        return self._request(
            "PATCH", PERSONALIZED_LEARNING_ITEM.format(learning_item_id=learning_item_id),
            operation="update_learning_item_status",
            json={"status": status},
        )

    # -- learner API ---------------------------------------------------------

    def list_observations(self, learner_id: str) -> dict[str, Any]:
        return self._request("GET", LEARNER_OBSERVATIONS, operation="list_observations",
                             params={"learner_id": learner_id}, retry=True)

    def observation_status(self, learner_id: str, observation_id: str) -> dict[str, Any]:
        return self._request(
            "GET", LEARNER_OBSERVATION.format(observation_id=observation_id),
            operation="observation_status",
            params={"learner_id": learner_id}, retry=True,
        )

    def difficulties(self, learner_id: str) -> dict[str, Any]:
        return self._request("GET", LEARNER_DIFFICULTIES, operation="difficulties",
                             params={"learner_id": learner_id}, retry=True)

    def strengths(self, learner_id: str) -> dict[str, Any]:
        return self._request("GET", LEARNER_STRENGTHS, operation="strengths",
                             params={"learner_id": learner_id}, retry=True)

    def stable(self, learner_id: str) -> dict[str, Any]:
        return self._request("GET", LEARNER_STABLE, operation="stable",
                             params={"learner_id": learner_id}, retry=True)

    def proficiency_context(self, learner_id: str) -> dict[str, Any]:
        return self._request("GET", LEARNER_PROFICIENCY_CONTEXT, operation="proficiency_context",
                             params={"learner_id": learner_id}, retry=True)

    def current_evidence(self, learner_id: str) -> dict[str, Any]:
        return self._request("GET", LEARNER_EVIDENCE, operation="current_evidence",
                             params={"learner_id": learner_id}, retry=True)


__all__ = [
    "Wave2ApiClient",
    "Wave2ApiClientError",
    "Wave2ApiUnavailable",
]