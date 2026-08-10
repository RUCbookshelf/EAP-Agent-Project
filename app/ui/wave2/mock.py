"""Contract-shaped local mock of the Wave-2 backend for tests and demos.

The mock mirrors the documented response shapes of the Wave-2 contracts
(revision_api / personalized_api / learner_api) with deterministic,
bounded, non-normative content. Scenarios:

- ``new_learner``        no stored history; every longitudinal view is an
                          explicit insufficient-history state (nothing is
                          ever fabricated).
- ``returning_learner``  seeded history: prior task/versions, recurring
                          difficulty, stable observation, strengths,
                          LearningItems, an external proficiency anchor.

The mock implements a tiny deterministic text scan (repeated words, long
sentences, connectives, length) so plan items and revision observations are
grounded in the actual submitted text. It is a test double, not a backend
implementation.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Callable

from app.ui.wave2.client import Wave2ApiClientError, Wave2ApiUnavailable


def _now_iso(now: Callable[[], datetime]) -> str:
    return now().astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "of", "to", "on", "with",
    "at", "by", "from", "as", "is", "are", "was", "were", "be", "been", "being",
    "this", "that", "these", "those", "it", "its", "they", "them", "their",
    "there", "which", "who", "whom", "will", "would", "can", "could", "should",
    "may", "might", "must", "have", "has", "had", "do", "does", "did", "not",
    "no", "yes", "so", "if", "then", "than", "when", "while", "because",
    "also", "very", "just", "more", "most", "some", "any", "all", "each",
    "every", "both", "few", "such", "only", "own", "same", "other", "another",
    "how", "what", "where", "why", "whose", "into", "over", "under",
    "between", "through", "during", "about", "against", "after", "before",
    "first", "second", "last", "next",
})

_CONNECTIVES = frozenset({
    "however", "therefore", "moreover", "furthermore", "addition", "result",
    "example", "although", "while", "finally", "consequently",
    "meanwhile", "instead", "similarly",
})

_ACTION_BY_CATEGORY = {
    "lexical_repetition": (
        "Replace one repeated word with a synonym, or combine two sentences "
        "so the repetition is removed."
    ),
    "sentence_variety": (
        "Split the longest sentence into two shorter sentences at a natural pause."
    ),
    "connective_use": (
        "Add one linking word that shows how your ideas connect (for example: "
        "however, therefore, in addition)."
    ),
    "task_focus": (
        "Expand the draft: give one concrete reason or example that supports "
        "your position."
    ),
    "general_revision": (
        "Choose one place where your meaning is not clear yet and rephrase it "
        "in simpler words."
    ),
}

_RECURRENCE_BY_CATEGORY_RETURNING = {
    "lexical_repetition": "recurring",
    "sentence_variety": "stable",
    "connective_use": "reappeared",
}

_HISTORICAL_SEED = [
    {
        "category": "lexical_repetition", "status": "recurring",
        "occurrence_count": 3, "first": "2026-07-02T09:00:00Z",
        "last": "2026-07-28T11:30:00Z", "contexts": ["cet4", "course_essay", "cet4"],
        "note": "A prior revision reduced the repetition in one draft.",
    },
    {
        "category": "sentence_variety", "status": "stable",
        "occurrence_count": 2, "first": "2026-07-10T08:00:00Z",
        "last": "2026-07-25T10:00:00Z", "contexts": ["cet4", "cet6"],
        "note": None,
    },
    {
        "category": "connective_use", "status": "reappeared",
        "occurrence_count": 2, "first": "2026-07-05T09:00:00Z",
        "last": "2026-07-30T12:00:00Z", "contexts": ["cet4", "cet4"],
        "note": None,
    },
]

_NEVER_WRITES = (
    "Guidance only: the revision stays your own writing. Nothing here writes "
    "your draft for you."
)


def _scaffold_templates(category: str) -> list[dict[str, str]]:
    """Deterministic 7-level SCAFFOLD-FIRST template for one category."""
    name = category.replace("_", " ")
    return [
        {
            "kind": "notice",
            "text": (
                f"Look at the passage about this draft's {name} pattern. "
                "Find one exact spot where it appears. Which sentence stands "
                "out to you?"
            ),
            "learner_action": "Underline or copy one example sentence.",
        },
        {
            "kind": "name",
            "text": (
                f"Describe the {name} pattern in your own words: what does it "
                "look like in the spot you found?"
            ),
            "learner_action": "Write one sentence naming the pattern.",
        },
        {
            "kind": "example",
            "text": (
                f"Here is a generic example of the {name} pattern and one way "
                "to change it. Your draft is different, so use the idea, not "
                "the words."
            ),
            "learner_action": "Compare your sentence with the example.",
        },
        {
            "kind": "mini-practice",
            "text": (
                "Practice on one of your own sentences without changing your "
                f"draft yet: apply the {name} fix to a scratch copy."
            ),
            "learner_action": "Rewrite one sentence in a scratch area.",
        },
        {
            "kind": "apply",
            "text": (
                f"Choose one or two places in your draft where the {name} "
                "change fits naturally and edit only those places."
            ),
            "learner_action": "Edit those places in your draft.",
        },
        {
            "kind": "check",
            "text": (
                "Read the changed passage aloud. Does it still say what you "
                "meant, and does the change hold?"
            ),
            "learner_action": "Check your change against your meaning.",
        },
        {
            "kind": "decide",
            "text": (
                "Decide what is next: revise another target from your plan, "
                "or submit this revision for feedback."
            ),
            "learner_action": "Choose your next step.",
        },
    ]


def _detect_issues(essay_text: str) -> list[dict[str, Any]]:
    """Tiny deterministic scan; returns grounded, display-safe observations."""
    words = re.findall(r"[a-zA-Z']+", essay_text.lower())
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", essay_text.strip()) if s.strip()]
    content = Counter(w for w in words if w not in _STOPWORDS and len(w) > 2)
    issues: list[dict[str, Any]] = []

    if content:
        word, count = content.most_common(1)[0]
        if count >= 3:
            quote = next(
                (s for s in sentences if word in re.findall(r"[a-zA-Z']+", s.lower())),
                sentences[0] if sentences else "",
            )
            issues.append({
                "category": "lexical_repetition",
                "context": {
                    "explanation": (
                        f"The word '{word}' appears several times in this draft. "
                        "Repeating one word closely can make the writing feel "
                        "repetitive."
                    ),
                    "quote": quote,
                },
            })

    long_sentence = next((s for s in sentences if len(s.split()) > 32), None)
    if long_sentence:
        issues.append({
            "category": "sentence_variety",
            "context": {
                "explanation": (
                    "One sentence is much longer than the others, which can "
                    "make the idea harder to follow."
                ),
                "quote": long_sentence,
            },
        })

    if not (set(words) & _CONNECTIVES):
        issues.append({
            "category": "connective_use",
            "context": {
                "explanation": (
                    "The draft moves between ideas without linking words, so "
                    "the connection between them is not explicit."
                ),
                "quote": sentences[0] if sentences else "",
            },
        })

    if len(words) < 50:
        issues.append({
            "category": "task_focus",
            "context": {
                "explanation": (
                    "The draft is much shorter than a typical response to this "
                    "task, so the argument is not developed yet."
                ),
                "quote": essay_text[:90],
            },
        })

    if not issues:
        issues.append({
            "category": "general_revision",
            "context": {
                "explanation": (
                    "Re-read your draft against the task prompt and choose one "
                    "spot to strengthen."
                ),
                "quote": sentences[0] if sentences else "",
            },
        })
    return issues
class MockWave2Backend:
    """In-memory Wave-2 backend simulation with deterministic scenarios."""

    def __init__(self, scenario: str = "new_learner", now: Callable[[], datetime] | None = None) -> None:
        if scenario not in {"new_learner", "returning_learner"}:
            raise ValueError(f"Unknown scenario {scenario!r}")
        self.scenario = scenario
        self._now = now or _utc_now
        self._tasks: dict[str, dict[str, Any]] = {}
        self._versions: dict[str, list[dict[str, Any]]] = {}
        self._essays: dict[tuple[str, int], str] = {}
        self._plans_by_submission: dict[tuple[str, int], dict[str, Any]] = {}
        self._plans_by_learner: dict[str, list[dict[str, Any]]] = {}
        self._learning_items: dict[str, list[dict[str, Any]]] = {}
        self._task_seq = 0
        self._submission_seq = 0
        self._plan_seq = 0
        self._item_seq = 0
        self._observation_seq = 0
        if scenario == "returning_learner":
            self._seed_returning_learner()

    def _iso(self) -> str:
        return _now_iso(self._now)

    def _learner_history_map(self, learner_id: str) -> tuple[str, list[str]]:
        if self.scenario == "returning_learner" and learner_id == "L-RET-001":
            return "sufficient", []
        return "insufficient_history", [
            "No earlier stored writing for this learner is available yet."
        ]

    def _recurrence_for(self, learner_id: str, category: str) -> str:
        if self.scenario == "returning_learner" and learner_id == "L-RET-001":
            return _RECURRENCE_BY_CATEGORY_RETURNING.get(category, "first_observed")
        return "first_observed"

    # -- seeding -------------------------------------------------------------

    def _seed_returning_learner(self) -> None:
        task = self.create_task(
            student_id="L-RET-001", task_type="opinion", writing_context="cet4",
            writing_prompt="Should cities add more parks?",
        )
        task_id = task["task_id"]
        v1_text = (
            "Cities should add more parks because parks give residents space "
            "to exercise. Parks also support community events and provide "
            "shade. However, new parks require land and maintenance."
        )
        v2_text = (
            "Cities should add more parks because green spaces give residents "
            "room to exercise. Parks also support community events and provide "
            "shade. However, new parks require land and maintenance."
        )
        v1 = self.submit_v1(task_id, v1_text, draft_stage="first draft")
        self.revise(task_id, v1["submission_id"], v2_text, draft_stage="revised draft")
        self._learning_items["L-RET-001"] = [
            {
                "learning_item_id": "LI-0001",
                "student_id": "L-RET-001",
                "category": "lexical_repetition",
                "originating_evidence": {
                    "plan_items": [
                        {"category": "lexical_repetition", "recurrence_status": "recurring"}
                    ]
                },
                "feedback_reference": "PLAN-SEED-1",
                "revision_history": [],
                "task_id": task_id,
                "task_context": {
                    "writing_prompt": task["writing_prompt"],
                    "writing_context": task["writing_context"],
                },
                "status": "active",
                "created_at": "2026-07-28T11:30:00Z",
                "updated_at": "2026-07-30T12:00:00Z",
                "no_fsrs_note": "no FSRS scheduling or spaced-repetition state is stored in LearningItem v1",
                "no_practice_note": "no practice or tutor expansion is attached to LearningItem v1",
                "limitations": [],
            },
            {
                "learning_item_id": "LI-0002",
                "student_id": "L-RET-001",
                "category": "connective_use",
                "originating_evidence": {
                    "plan_items": [
                        {"category": "connective_use", "recurrence_status": "reappeared"}
                    ]
                },
                "feedback_reference": "PLAN-SEED-2",
                "revision_history": [],
                "task_id": task_id,
                "task_context": {
                    "writing_prompt": task["writing_prompt"],
                    "writing_context": task["writing_context"],
                },
                "status": "proposed",
                "created_at": "2026-07-30T12:00:00Z",
                "updated_at": "2026-07-30T12:00:00Z",
                "no_fsrs_note": "no FSRS scheduling or spaced-repetition state is stored in LearningItem v1",
                "no_practice_note": "no practice or tutor expansion is attached to LearningItem v1",
                "limitations": [],
            },
        ]

    # -- revision API --------------------------------------------------------

    def create_task(self, student_id: str, task_type: str, writing_context: str,
                    writing_prompt: str, *, metadata: dict[str, Any] | None = None,
                    declared_task_type: str | None = None) -> dict[str, Any]:
        allowed_types = {
            "opinion", "argumentative", "discussion", "problem_solution",
            "general_eap", "legacy_unclassified",
        }
        allowed_contexts = {
            "cet4", "cet6", "ielts_task2", "toefl_style", "course_essay",
            "email", "application", "reflective_journal", "other",
        }
        if task_type not in allowed_types:
            raise ValueError(f"Unknown task_type {task_type!r}")
        if writing_context not in allowed_contexts:
            raise ValueError(f"Unknown writing_context {writing_context!r}")
        if not writing_prompt.strip():
            raise ValueError("writing_prompt must not be blank")
        self._task_seq += 1
        task = {
            "task_id": f"T-{self._task_seq:04d}",
            "student_id": student_id,
            "task_type": task_type,
            "writing_context": writing_context,
            "writing_prompt": writing_prompt.strip(),
            "metadata": {
                "audience": (metadata or {}).get("audience"),
                "purpose": (metadata or {}).get("purpose"),
                "word_constraint": (metadata or {}).get("word_constraint"),
                "assessment_environment": (metadata or {}).get("assessment_environment"),
                "genre_expectations": (metadata or {}).get("genre_expectations") or [],
            },
            "modality": "written",
            "classification": {
                "task_type": task_type,
                "declared_task_type": declared_task_type or task_type,
            },
            "status": "active",
            "created_at": self._iso(),
            "limitations": [],
        }
        self._tasks[task["task_id"]] = task
        self._versions[task["task_id"]] = []
        return task

    def get_task(self, task_id: str) -> dict[str, Any]:
        try:
            return dict(self._tasks[task_id])
        except KeyError as exc:
            raise LookupError(f"Task {task_id} not found.") from exc

    def _store_version(self, task_id: str, essay_text: str, *, draft_stage: str,
                       tool_use: str, revision_of: int | None) -> dict[str, Any]:
        task = self.get_task(task_id)
        versions = self._versions[task_id]
        self._submission_seq += 1
        submission_id = self._submission_seq
        version_number = 1 if revision_of is None else len(versions) + 1
        ancestry = [v["submission_id"] for v in versions] + [submission_id]
        version = {
            "task_id": task_id,
            "submission_id": submission_id,
            "version_number": version_number,
            "revision_of_submission_id": revision_of,
            "ancestry": ancestry,
            "submitted_at": self._iso(),
            "task_context": {
                "writing_prompt": task["writing_prompt"],
                "writing_context": task["writing_context"],
                "task_type": task["task_type"],
            },
            "essay_text_hash": hashlib.sha256(essay_text.encode("utf-8")).hexdigest(),
            "draft_stage": draft_stage,
            "analysis_run_id": f"AR-{self._submission_seq:05d}",
            "analysis_version": "spacy-analyzer-v0.8.0",
            "feedback_record_id": self._submission_seq,
            "revision_group_id": f"RG-{self._submission_seq:06d}",
            "revision_snapshot_id": f"RS-{self._submission_seq:06d}",
            "corpus_routing": {"written": True, "secondary": False, "research_only": True},
            "reanalysis_events": [],
            "limitations": [],
        }
        versions.append(version)
        self._essays[(task_id, submission_id)] = essay_text
        return version

    def submit_v1(self, task_id: str, essay_text: str, *,
                  draft_stage: str = "first draft", tool_use: str = "none") -> dict[str, Any]:
        if task_id not in self._tasks:
            raise LookupError(f"Task {task_id} not found.")
        if not essay_text.strip():
            raise ValueError("essay_text must not be blank")
        return self._store_version(task_id, essay_text, draft_stage=draft_stage,
                                   tool_use=tool_use, revision_of=None)

    def revise(self, task_id: str, submission_id: int, essay_text: str, *,
               draft_stage: str = "revised draft", tool_use: str = "none") -> dict[str, Any]:
        if task_id not in self._tasks:
            raise LookupError(f"Task {task_id} not found.")
        known = {v["submission_id"] for v in self._versions[task_id]}
        if submission_id not in known:
            raise LookupError(f"Submission {submission_id} not found in task {task_id}.")
        if not essay_text.strip():
            raise ValueError("essay_text must not be blank")
        return self._store_version(task_id, essay_text, draft_stage=draft_stage,
                                   tool_use=tool_use, revision_of=submission_id)

    def version_history(self, task_id: str) -> dict[str, Any]:
        if task_id not in self._tasks:
            raise LookupError(f"Task {task_id} not found.")
        return {"task_id": task_id, "versions": [dict(v) for v in self._versions[task_id]]}

    def revision_observation(self, task_id: str, submission_id: int) -> dict[str, Any]:
        if task_id not in self._tasks:
            raise LookupError(f"Task {task_id} not found.")
        versions = self._versions[task_id]
        target = next((v for v in versions if v["submission_id"] == submission_id), None)
        if target is None:
            raise LookupError(f"Submission {submission_id} not found in task {task_id}.")
        if target["revision_of_submission_id"] is None:
            raise ValueError("Observation requires a revised version.")
        source_id = target["revision_of_submission_id"]
        source_text = self._essays[(task_id, source_id)]
        target_text = self._essays[(task_id, submission_id)]
        source_plan = self._plans_by_submission.get((task_id, source_id))
        previous_categories = {
            item["category"] for item in (source_plan or {}).get("items", [])
        }
        target_issues = {issue["category"] for issue in _detect_issues(target_text)}
        feedback_areas = []
        for category in sorted(previous_categories):
            feedback_areas.append({
                "category": category,
                "status": "remaining" if category in target_issues else "addressed",
            })
        new_observations = [
            {"category": category, "status": "new"}
            for category in sorted(target_issues - previous_categories)
        ]
        source_words = re.findall(r"[a-zA-Z']+", source_text.lower())
        target_words = re.findall(r"[a-zA-Z']+", target_text.lower())
        self._observation_seq += 1
        return {
            "observation_id": f"OBS-{self._observation_seq:04d}",
            "task_id": task_id,
            "source_submission_id": source_id,
            "target_submission_id": submission_id,
            "observed_at": self._iso(),
            "what_changed": {
                "summary": (
                    "Compared with the previous version, this draft changed in "
                    f"length (about {len(target_words)} words now vs "
                    f"{len(source_words)} before) and in the spots you edited."
                ),
                "added_word_count": max(0, len(target_words) - len(source_words)),
                "removed_word_count": max(0, len(source_words) - len(target_words)),
            },
            "feedback_areas": feedback_areas,
            "new_observations": new_observations,
            "apparent_independent_corrections": [],
            "no_intent_inference": (
                "This compares the two drafts as written. It does not infer "
                "what you intended or why the text changed."
            ),
            "limitations": [],
        }

    # -- personalized API ----------------------------------------------------

    def priority_plan(self, learner_id: str, task_id: str, submission_id: int) -> dict[str, Any]:
        if task_id not in self._tasks:
            raise LookupError(f"Task {task_id} not found.")
        known = {v["submission_id"] for v in self._versions[task_id]}
        if submission_id not in known:
            raise LookupError(f"Submission {submission_id} not found in task {task_id}.")
        essay = self._essays[(task_id, submission_id)]
        issues = _detect_issues(essay)[:3]
        history_state, history_reasons = self._learner_history_map(learner_id)
        historical_feedback = []
        if history_state == "sufficient":
            for seed in _HISTORICAL_SEED:
                historical_feedback.append({
                    "learner_id": learner_id,
                    "category": seed["category"],
                    "status": seed["status"],
                    "occurrence_count": seed["occurrence_count"],
                    "first_observed_at": seed["first"],
                    "last_observed_at": seed["last"],
                    "supporting_submission_ids": [1, 2, 3],
                    "evidence_refs": [f"EVID-{i:04d}" for i in range(1, 4)],
                    "contexts": seed["contexts"],
                    "revision_success_note": seed["note"],
                    "history_state": "sufficient",
                    "history_reasons": [],
                    "limitations": [],
                    "claims_status": "observation_only",
                })
        self._plan_seq += 1
        plan = {
            "plan_id": f"PLAN-{self._plan_seq:04d}",
            "learner_id": learner_id,
            "task_id": task_id,
            "submission_id": submission_id,
            "generated_at": self._iso(),
            "items": [
                {
                    "plan_item_id": f"PI-{self._plan_seq:04d}-{index + 1}",
                    "category": issue["category"],
                    "diagnosis_id": f"D-{self._plan_seq:04d}{index + 1}",
                    "recurrence_status": self._recurrence_for(learner_id, issue["category"]),
                    "context": dict(issue["context"]),
                    "action_statement": _ACTION_BY_CATEGORY.get(
                        issue["category"], _ACTION_BY_CATEGORY["general_revision"]
                    ),
                    "evidence_refs": [f"EVID-{self._plan_seq:04d}"],
                    "confidence": "low",
                    "ordering_note": (
                        "action-priority ordering only; not a learner-performance ranking"
                    ),
                    "limitations": [],
                }
                for index, issue in enumerate(issues)
            ],
            "history_state": history_state,
            "history_reasons": history_reasons,
            "local_observations": [
                {
                    "feature_id": f"LOC-{self._plan_seq:04d}-{index + 1}",
                    "value": None,
                    "available": True,
                    "statement": issue["context"]["explanation"],
                    "limitation": "Descriptive observation of this draft only.",
                }
                for index, issue in enumerate(issues)
            ],
            "global_observations": [
                {
                    "observation_id": f"GLO-{self._plan_seq:04d}",
                    "scope": "whole_text",
                    "kind": "length",
                    "value": len(re.findall(r"[a-zA-Z']+", essay.lower())),
                    "descriptive_statement": (
                        "Whole-draft description only; not a score or a "
                        "comparison with other writers."
                    ),
                    "limitation": "Descriptive; not a validated measurement.",
                }
            ],
            "historical_feedback": historical_feedback,
            "limitations": [
                "action-priority ordering only; not a learner-performance ranking"
            ],
            "claims_status": "observation_only",
        }
        self._plans_by_learner.setdefault(learner_id, []).append(plan)
        self._plans_by_submission[(task_id, submission_id)] = plan
        return plan

    def scaffold(self, learner_id: str, category: str, *, level: int | None = None,
                 plan_item_id: str | None = None, learning_item_id: str | None = None,
                 evidence: str | None = None) -> dict[str, Any]:
        del learner_id, plan_item_id, learning_item_id, evidence
        chosen = level if level is not None else 1
        if chosen not in range(1, 8):
            raise ValueError("level must be between 1 and 7")
        template = _scaffold_templates(category)[chosen - 1]
        return {
            "learner_id": "mock",
            "category": category,
            "level": chosen,
            "default_first": True,
            "available_levels": list(range(1, 8)),
            "content": {
                "level": chosen,
                "kind": template["kind"],
                "text": template["text"],
            },
            "learner_action": template["learner_action"],
            "never_writes_statement": _NEVER_WRITES,
            "limitations": [],
        }

    def list_learning_items(self, student_id: str, *, status: str | None = None) -> dict[str, Any]:
        items = [dict(item) for item in self._learning_items.get(student_id, [])]
        if status is not None:
            items = [item for item in items if item["status"] == status]
        return {"student_id": student_id, "items": items}

    def create_learning_item(self, learner_id: str, plan_item_id: str) -> dict[str, Any]:
        for plan in self._plans_by_learner.get(learner_id, []):
            for item in plan["items"]:
                if item["plan_item_id"] == plan_item_id:
                    task = self._tasks[plan["task_id"]]
                    self._item_seq += 1
                    new_item = {
                        "learning_item_id": f"LI-{self._item_seq:04d}",
                        "student_id": learner_id,
                        "category": item["category"],
                        "originating_evidence": {
                            "plan_items": [
                                {
                                    "category": item["category"],
                                    "recurrence_status": item["recurrence_status"],
                                }
                            ]
                        },
                        "feedback_reference": plan["plan_id"],
                        "revision_history": [],
                        "task_id": plan["task_id"],
                        "task_context": {
                            "writing_prompt": task["writing_prompt"],
                            "writing_context": task["writing_context"],
                        },
                        "status": "proposed",
                        "created_at": self._iso(),
                        "updated_at": self._iso(),
                        "no_fsrs_note": (
                            "no FSRS scheduling or spaced-repetition state is "
                            "stored in LearningItem v1"
                        ),
                        "no_practice_note": (
                            "no practice or tutor expansion is attached to "
                            "LearningItem v1"
                        ),
                        "limitations": [],
                    }
                    self._learning_items.setdefault(learner_id, []).append(new_item)
                    return new_item
        raise LookupError(f"Plan item {plan_item_id} not found for this learner.")

    def update_learning_item_status(self, learning_item_id: str, status: str) -> dict[str, Any]:
        if status not in {"proposed", "active", "superseded", "closed"}:
            raise ValueError(f"Invalid learning item status {status!r}")
        for items in self._learning_items.values():
            for item in items:
                if item["learning_item_id"] == learning_item_id:
                    item["status"] = status
                    item["updated_at"] = self._iso()
                    return dict(item)
        raise LookupError(f"Learning item {learning_item_id} not found.")

    # -- learner API ---------------------------------------------------------

    def _status_view(self, learner_id: str, kind: str, code: str, label: str,
                     occurrence_count: int, *, first: str, last: str,
                     contexts: list[str], revision_response: str) -> dict[str, Any]:
        self._observation_seq += 1
        return {
            "learner_id": learner_id,
            "observation_id": f"OBS-{self._observation_seq:04d}",
            "code": code,
            "label": label,
            "observation_type": kind,
            "occurrence_count": occurrence_count,
            "qualified_occurrence_count": occurrence_count,
            "prior_occurrence_count": max(0, occurrence_count - 1),
            "appeared_before": occurrence_count > 0,
            "first_observed_at": first,
            "last_observed_at": last,
            "days_since_last_observed": 3,
            "contexts": contexts,
            "revision_response": revision_response,
            "addressed_in_prior_revision": revision_response == "corrected_after_feedback",
            "frequency": {
                "qualified_occurrence_count": occurrence_count,
                "qualified_sample_count": 4,
                "window_size": 3,
                "descriptive_proportion": round(occurrence_count / 4, 2),
                "history_state": "sufficient",
                "history_reasons": [],
                "limitation": (
                    "Descriptive proportion over qualified recent samples only; "
                    "not a validated measurement."
                ),
            },
            "history_state": "sufficient",
            "history_reasons": [],
            "limitations": [],
            "claims_status": "observation_only",
        }

    def _seeded_observations(self, learner_id: str) -> list[dict[str, Any]]:
        if self.scenario != "returning_learner" or learner_id != "L-RET-001":
            return []
        return [
            self._status_view(
                learner_id, "difficulty", "LEX_REP", "Repeated word use", 3,
                first="2026-07-02T09:00:00Z", last="2026-07-28T11:30:00Z",
                contexts=["cet4", "course_essay", "cet4"],
                revision_response="corrected_after_feedback",
            ),
            self._status_view(
                learner_id, "strength", "ORG", "Clear overall structure", 2,
                first="2026-07-05T09:00:00Z", last="2026-07-30T12:00:00Z",
                contexts=["cet4", "cet6"],
                revision_response="no_revision_evidence",
            ),
        ]

    def list_observations(self, learner_id: str) -> dict[str, Any]:
        items = self._seeded_observations(learner_id)
        items.sort(key=lambda item: item["last_observed_at"], reverse=True)
        state, reasons = ("sufficient", []) if items else (
            "insufficient_history", ["no observations recorded for this learner"]
        )
        return {
            "learner_id": learner_id,
            "history_state": state,
            "items": items,
            "limitations": [
                "Longitudinal observations are descriptive; they do not establish "
                "mastery, proficiency, ability, or learning gain."
            ],
        }

    def observation_status(self, learner_id: str, observation_id: str) -> dict[str, Any] | None:
        for item in self._seeded_observations(learner_id):
            if item["observation_id"] == observation_id:
                return dict(item)
        return None

    def difficulties(self, learner_id: str, min_occurrences: int = 2,
                     recent_window: int = 3) -> dict[str, Any]:
        items = [
            dict(item) for item in self._seeded_observations(learner_id)
            if item["observation_type"] == "difficulty"
            and item["occurrence_count"] >= min_occurrences
        ]
        state, reasons = ("sufficient", []) if items else (
            "insufficient_history",
            ["not enough qualified recent writing to report recurring patterns"],
        )
        return {
            "learner_id": learner_id,
            "history_state": state,
            "items": items,
            "limitations": ["Observation-only; no ability or gain claims."],
        }

    def strengths(self, learner_id: str) -> dict[str, Any]:
        items = [
            dict(item) for item in self._seeded_observations(learner_id)
            if item["observation_type"] == "strength"
        ]
        return {"learner_id": learner_id, "items": items, "limitations": []}

    def stable(self, learner_id: str, recent_window: int = 3,
               min_qualified_recent: int = 2) -> dict[str, Any]:
        if self.scenario == "returning_learner" and learner_id == "L-RET-001":
            items = [{
                "learner_id": learner_id,
                "observation_id": "OBS-STABLE-1",
                "code": "CONN_USE",
                "label": "Connective use",
                "stability_kind": "previously_recurring_not_recently_observed",
                "occurrence_count": 2,
                "qualified_occurrence_count": 2,
                "recent_window_occurrence_count": 0,
                "recent_window_sample_count": 3,
                "first_observed_at": "2026-07-05T09:00:00Z",
                "last_observed_at": "2026-07-18T09:00:00Z",
                "history_state": "sufficient",
                "history_reasons": [],
                "limitations": [],
                "claims_status": "observation_only",
            }]
            return {"learner_id": learner_id, "items": items, "limitations": []}
        return {"learner_id": learner_id, "items": [], "limitations": []}

    def proficiency_context(self, learner_id: str) -> dict[str, Any]:
        anchors = []
        state, reasons = "insufficient_history", ["no declared anchors"]
        if self.scenario == "returning_learner" and learner_id == "L-RET-001":
            anchors = [{
                "anchor_id": "ANCHOR-1",
                "system": "CET-4",
                "declared_value": "Passed",
                "source": "self-declared by the learner",
                "recorded_at": "2026-07-01T08:00:00Z",
                "limitations": [],
            }]
            state, reasons = "sufficient", []
        return {
            "learner_id": learner_id,
            "anchors": anchors,
            "derived_from_corpus": False,
            "statement": (
                "External anchors are contextual reference points declared by "
                "or for the learner; they are not converted from corpus "
                "statistics and are not learner-performance labels."
            ),
            "history_state": state,
            "history_reasons": reasons,
            "limitations": [],
            "claims_status": "observation_only",
        }

    def current_evidence(self, learner_id: str) -> dict[str, Any]:
        items = []
        if self.scenario == "returning_learner" and learner_id == "L-RET-001":
            items = [{
                "learner_id": learner_id,
                "evidence": {
                    "evidence_id": "EVID-0001",
                    "source_kind": "submission",
                    "admitted_at": "2026-07-28T11:30:00Z",
                    "payload": {"note": "admitted observed evidence record"},
                },
            }]
        return {
            "learner_id": learner_id,
            "items": items,
            "excluded_count": 0,
            "limitations": [],
        }


class MockWave2Client:
    """Client-shaped wrapper around MockWave2Backend for tests/demos.

    ``available=False`` simulates the Wave-2 endpoints not being wired up at
    integration: every call fails closed with ``Wave2ApiUnavailable`` so the
    gateway degrades to the existing writing/feedback flow.
    """

    def __init__(self, backend: MockWave2Backend | None = None, *, available: bool = True) -> None:
        self._backend = backend or MockWave2Backend()
        self._available = available

    def probe(self) -> bool:
        return self._available

    def _guard(self) -> None:
        if not self._available:
            raise Wave2ApiUnavailable("Wave-2 endpoints unavailable (mock).")

    def _call(self, method: str, *args, **kwargs) -> Any:
        self._guard()
        try:
            return getattr(self._backend, method)(*args, **kwargs)
        except LookupError as exc:
            raise Wave2ApiClientError(str(exc), http_status=404, operation=method) from None
        except ValueError as exc:
            raise Wave2ApiClientError(str(exc), http_status=422, operation=method) from None

    # revision API
    def create_task(self, student_id, task_type, writing_context, writing_prompt, *,
                    metadata=None, declared_task_type=None) -> dict[str, Any]:
        return self._call("create_task", student_id, task_type, writing_context,
                          writing_prompt, metadata=metadata,
                          declared_task_type=declared_task_type)

    def get_task(self, task_id: str) -> dict[str, Any]:
        return self._call("get_task", task_id)

    def submit_v1(self, task_id, essay_text, *, draft_stage="first draft",
                  tool_use="none") -> dict[str, Any]:
        return self._call("submit_v1", task_id, essay_text, draft_stage=draft_stage,
                          tool_use=tool_use)

    def revise(self, task_id, submission_id, essay_text, *, draft_stage="revised draft",
               tool_use="none") -> dict[str, Any]:
        return self._call("revise", task_id, submission_id, essay_text,
                          draft_stage=draft_stage, tool_use=tool_use)

    def version_history(self, task_id: str) -> dict[str, Any]:
        return self._call("version_history", task_id)

    def revision_observation(self, task_id: str, submission_id: int) -> dict[str, Any]:
        return self._call("revision_observation", task_id, submission_id)

    # personalized API
    def priority_plan(self, learner_id, task_id, submission_id) -> dict[str, Any]:
        return self._call("priority_plan", learner_id, task_id, submission_id)

    def scaffold(self, learner_id, category, *, level=None, plan_item_id=None,
                 learning_item_id=None, evidence=None) -> dict[str, Any]:
        return self._call("scaffold", learner_id, category, level=level,
                          plan_item_id=plan_item_id, learning_item_id=learning_item_id,
                          evidence=evidence)

    def list_learning_items(self, student_id: str, *, status: str | None = None) -> dict[str, Any]:
        return self._call("list_learning_items", student_id, status=status)

    def create_learning_item(self, learner_id: str, plan_item_id: str) -> dict[str, Any]:
        return self._call("create_learning_item", learner_id, plan_item_id)

    def update_learning_item_status(self, learning_item_id: str, status: str) -> dict[str, Any]:
        return self._call("update_learning_item_status", learning_item_id, status)

    # learner API
    def list_observations(self, learner_id: str) -> dict[str, Any]:
        return self._call("list_observations", learner_id)

    def difficulties(self, learner_id: str) -> dict[str, Any]:
        return self._call("difficulties", learner_id)

    def strengths(self, learner_id: str) -> dict[str, Any]:
        return self._call("strengths", learner_id)

    def stable(self, learner_id: str) -> dict[str, Any]:
        return self._call("stable", learner_id)

    def proficiency_context(self, learner_id: str) -> dict[str, Any]:
        return self._call("proficiency_context", learner_id)

    def current_evidence(self, learner_id: str) -> dict[str, Any]:
        return self._call("current_evidence", learner_id)


__all__ = ["MockWave2Backend", "MockWave2Client"]
