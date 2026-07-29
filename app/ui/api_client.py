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
