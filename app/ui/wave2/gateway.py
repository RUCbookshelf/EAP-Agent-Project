"""UI facade for the Wave-2 Student Writing Experience.

``Wave2Gateway`` is the single entry point used by the student renderers:

- ``guided`` mode drives the Wave-2 journey through the documented
  contracts (revision / personalized / learner APIs).
- ``standard`` mode is the graceful degradation: while the Wave-2 endpoints
  are unavailable (they land at integration), the same journey runs over the
  existing writing/feedback flow (/api/v1/submissions, journey, revision
  candidates) without crashing and without fabricating Wave-2 features.

Mode selection: ``auto`` probes the Wave-2 namespace once and caches the
result; ``wave2`` and ``legacy`` force a mode (used by tests/demos).
"""

from __future__ import annotations

from typing import Any

from app.ui.wave2.client import Wave2ApiClientError, Wave2ApiUnavailable
from app.ui.wave2.contracts import LEGACY_GENRE_BY_CONTEXT
from app.ui.wave2.views import (
    build_feedback_view,
    build_history_view,
    build_learning_items_view,
    build_legacy_feedback_view,
    build_legacy_version_view,
    build_longitudinal_view,
    build_observation_view,
    build_task_view,
    build_version_view,
)


class Wave2Gateway:
    """Wave-2-first facade with graceful degradation to the legacy flow."""

    def __init__(self, wave2_client: Any, legacy_client: Any, mode: str = "auto") -> None:
        if mode not in {"auto", "wave2", "legacy"}:
            raise ValueError(f"Unknown gateway mode {mode!r}")
        self._wave2 = wave2_client
        self._legacy = legacy_client
        self._mode = mode
        self._available: bool | None = None

    # -- availability --------------------------------------------------------

    def available(self) -> bool:
        if self._mode == "legacy":
            return False
        if self._mode == "wave2":
            return True
        if self._available is None:
            try:
                self._available = bool(self._wave2.probe())
            except Exception:
                self._available = False
        return self._available

    def mode(self) -> str:
        return "guided" if self.available() else "standard"

    # -- task lifecycle ------------------------------------------------------

    def create_task(self, student_id: str, task_type: str, writing_context: str,
                    writing_prompt: str, *, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.available():
            return build_task_view(self._wave2.create_task(
                student_id, task_type, writing_context, writing_prompt,
                metadata=metadata,
            ))
        return build_task_view({
            "task_id": None,
            "student_id": student_id,
            "task_type": task_type,
            "writing_context": writing_context,
            "writing_prompt": writing_prompt,
            "metadata": metadata or {},
            "created_at": "",
        })

    # -- submission flow -----------------------------------------------------

    def submit_first(self, task: dict[str, Any], learner_id: str, essay_text: str,
                     draft_stage: str = "first draft") -> dict[str, Any]:
        if self.available():
            version = self._wave2.submit_v1(task["task_id"], essay_text, draft_stage=draft_stage)
            plan = self._wave2.priority_plan(learner_id, task["task_id"], version["submission_id"])
            return {
                "mode": "guided",
                "version": build_version_view(version),
                "feedback": build_feedback_view(plan),
                "submission_id": version["submission_id"],
            }
        result = self._legacy.submit({
            "student_id": learner_id,
            "writing_prompt": task.get("writing_prompt", ""),
            "genre": LEGACY_GENRE_BY_CONTEXT.get(task.get("writing_context", "other"), "argumentative essay"),
            "draft_stage": draft_stage,
            "timed": False,
            "time_limit_minutes": None,
            "tool_use": "none",
            "essay_text": essay_text,
            "revision_of_submission_id": None,
        })
        return {
            "mode": "standard",
            "version": build_legacy_version_view(result),
            "feedback": build_legacy_feedback_view(result),
            "submission_id": result.get("submission_id"),
        }

    def submit_revision(self, task: dict[str, Any], submission_id: int, essay_text: str,
                        learner_id: str, draft_stage: str = "revised draft") -> dict[str, Any]:
        if self.available():
            version = self._wave2.revise(
                task["task_id"], submission_id, essay_text, draft_stage=draft_stage,
            )
            observation = self._wave2.revision_observation(
                task["task_id"], version["submission_id"],
            )
            return {
                "mode": "guided",
                "version": build_version_view(version),
                "observation": build_observation_view(observation),
                "submission_id": version["submission_id"],
            }
        result = self._legacy.submit_linked_revision({
            "student_id": learner_id,
            "writing_prompt": task.get("writing_prompt", ""),
            "genre": LEGACY_GENRE_BY_CONTEXT.get(task.get("writing_context", "other"), "argumentative essay"),
            "draft_stage": draft_stage,
            "timed": False,
            "time_limit_minutes": None,
            "tool_use": "none",
            "essay_text": essay_text,
            "revision_of_submission_id": int(submission_id),
        })
        return {
            "mode": "standard",
            "version": build_legacy_version_view(result),
            "observation": None,
            "submission_id": result.get("submission_id"),
        }

    # -- personalized --------------------------------------------------------

    def scaffold(self, learner_id: str, category: str, *, level: int | None = None) -> dict[str, Any]:
        if not self.available():
            return {"available": False}
        payload = self._wave2.scaffold(learner_id, category, level=level)
        content = payload.get("content") or {}
        return {
            "available": True,
            "category": payload.get("category", category),
            "level": int(payload.get("level") or 1),
            "default_first": bool(payload.get("default_first", True)),
            "content": {
                "level": int(content.get("level") or payload.get("level") or 1),
                "kind": content.get("kind", ""),
                "text": content.get("text", ""),
            },
            "learner_action": payload.get("learner_action", ""),
            "never_writes_statement": payload.get("never_writes_statement", ""),
        }

    def revision_observation(self, task_id: str, submission_id: int) -> dict[str, Any]:
        if not self.available():
            return {"available": False}
        return build_observation_view(self._wave2.revision_observation(task_id, submission_id))

    # -- history / learning --------------------------------------------------

    def learning_items(self, learner_id: str) -> dict[str, Any]:
        if not self.available():
            return {"items": [], "available": False}
        return build_learning_items_view(self._wave2.list_learning_items(learner_id))

    def longitudinal(self, learner_id: str) -> dict[str, Any]:
        if not self.available():
            return build_longitudinal_view({})
        bundle: dict[str, Any] = {}
        for key, method in (
            ("observations", self._wave2.list_observations),
            ("difficulties", self._wave2.difficulties),
            ("strengths", self._wave2.strengths),
            ("stable", self._wave2.stable),
            ("proficiency", self._wave2.proficiency_context),
        ):
            try:
                bundle[key] = method(learner_id)
            except (Wave2ApiClientError, Wave2ApiUnavailable):
                bundle[key] = {}
        return build_longitudinal_view(bundle)

    def history(self, learner_id: str, *, session_tasks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        session_tasks = session_tasks or []
        if not self.available():
            return self._legacy_history(learner_id)
        items_raw = []
        try:
            items_raw = (self._wave2.list_learning_items(learner_id) or {}).get("items", [])
        except (Wave2ApiClientError, Wave2ApiUnavailable):
            items_raw = []
        tasks: list[dict[str, Any]] = []
        seen_task_ids: set[str] = set()
        for item in items_raw:
            task_id = item.get("task_id")
            if not task_id or task_id in seen_task_ids:
                continue
            seen_task_ids.add(task_id)
            try:
                task_payload = self._wave2.get_task(task_id)
                versions_payload = (self._wave2.version_history(task_id) or {}).get("versions", [])
            except (Wave2ApiClientError, Wave2ApiUnavailable):
                continue
            plan_items = []
            for entry in items_raw:
                if entry.get("task_id") != task_id:
                    continue
                for plan_item in ((entry.get("originating_evidence") or {}).get("plan_items") or []):
                    if plan_item.get("category"):
                        plan_items.append(plan_item)
            tasks.append({
                "task": task_payload,
                "versions": versions_payload,
                "plan": {"items": plan_items},
            })
        for task_view in session_tasks:
            task_id = task_view.get("task_id")
            if not task_id or task_id in seen_task_ids:
                continue
            seen_task_ids.add(task_id)
            versions_payload = []
            try:
                versions_payload = (self._wave2.version_history(task_id) or {}).get("versions", [])
            except (Wave2ApiClientError, Wave2ApiUnavailable):
                versions_payload = []
            tasks.append({
                "task": task_view,
                "versions": versions_payload,
                "plan": {"items": []},
            })
        bundle = {
            "learner_id": learner_id,
            "tasks": tasks,
            "learning_items": items_raw,
            "longitudinal": self._longitudinal_bundle(learner_id),
        }
        view = build_history_view(bundle)
        view["mode"] = "guided"
        view["events"] = []
        return view

    def _longitudinal_bundle(self, learner_id: str) -> dict[str, Any]:
        bundle: dict[str, Any] = {}
        for key, method in (
            ("observations", self._wave2.list_observations),
            ("difficulties", self._wave2.difficulties),
            ("strengths", self._wave2.strengths),
            ("stable", self._wave2.stable),
            ("proficiency", self._wave2.proficiency_context),
        ):
            try:
                bundle[key] = method(learner_id)
            except (Wave2ApiClientError, Wave2ApiUnavailable):
                bundle[key] = {}
        return bundle

    def _legacy_history(self, learner_id: str) -> dict[str, Any]:
        events: list[dict[str, Any]] = []
        candidates: list[dict[str, Any]] = []
        try:
            journey = self._legacy.get_journey(learner_id) or {}
            events = [
                {
                    "title_key": entry.get("title_key", ""),
                    "occurred_at": entry.get("occurred_at", ""),
                }
                for entry in (journey.get("events") or [])
                if entry.get("title_key")
            ]
        except Exception:
            events = []
        try:
            candidates = ((self._legacy.get_student_revision_candidates(learner_id) or {}).get("candidates") or [])
        except Exception:
            candidates = []
        tasks = []
        for candidate in candidates:
            priorities = ((candidate.get("feedback") or {}).get("priority_feedback")) or []
            tasks.append({
                "task": {
                    "task_id": None,
                    "task_type": "",
                    "writing_context": "",
                    "writing_prompt": candidate.get("writing_prompt", ""),
                    "created_at": candidate.get("submitted_at", ""),
                    "metadata": {},
                },
                "versions": [{
                    "version_number": 1,
                    "submission_id": int(candidate["essay_id"]) if candidate.get("essay_id") is not None else 0,
                    "draft_stage": candidate.get("draft_stage", "first draft"),
                    "submitted_at": candidate.get("submitted_at", ""),
                    "revision_of_submission_id": None,
                    "ancestry": [],
                }],
                "plan": {
                    "items": [
                        {
                            "category": priority.get("category", ""),
                            "recurrence_status": "insufficient_history",
                        }
                        for priority in priorities
                        if priority.get("category")
                    ]
                },
            })
        bundle = {
            "learner_id": learner_id,
            "tasks": tasks,
            "learning_items": [],
            "longitudinal": {},
        }
        view = build_history_view(bundle)
        view["mode"] = "standard"
        view["events"] = events
        return view


__all__ = ["Wave2Gateway"]