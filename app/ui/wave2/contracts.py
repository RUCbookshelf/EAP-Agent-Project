"""Wave-2 contract constants and the student-facing allowlist policy.

The endpoint paths mirror the Wave-2 backend contracts as documented by
Goals PDW2-B (LEARNER) and PDW2-C (L2):

- ``/api/v1/wave2/revision/``  tasks, submit V1, revise V2, version
  history, revision observation, reanalysis.
- ``/api/v1/wave2/personalized/`` priority revision plan, progressive
  scaffold (SCAFFOLD FIRST, 7 levels), LearningItem v1 lifecycle.
- ``/api/v1/wave2/learner/`` longitudinal observation views, difficulties,
  strengths, stable observations, proficiency context (external anchors
  only), current evidence.

``STUDENT_INTERNAL_KEYS`` is the audit-only allowlist policy: these raw
technical fields (hashes, artifact paths, internal feature/record ids,
epistemic-status codes, provenance JSON, reference-group/distribution
internals) must never appear in student-facing views by default. Stable
references the journey needs to operate (task_id, submission_id,
learner_id, timestamps) may be carried in views but are never rendered by
the student surface.
"""

from __future__ import annotations

# -- revision API ------------------------------------------------------------
REVISION_TASKS = "/api/v1/wave2/revision/tasks"
REVISION_TASK = "/api/v1/wave2/revision/tasks/{task_id}"
REVISION_SUBMISSIONS = "/api/v1/wave2/revision/tasks/{task_id}/submissions"
REVISION_REVISIONS = (
    "/api/v1/wave2/revision/tasks/{task_id}/submissions/{submission_id}/revisions"
)
REVISION_VERSIONS = "/api/v1/wave2/revision/tasks/{task_id}/versions"
REVISION_OBSERVATION = (
    "/api/v1/wave2/revision/tasks/{task_id}/versions/{submission_id}/observation"
)
REVISION_REANALYSIS = "/api/v1/wave2/revision/submissions/{submission_id}/reanalysis"

# -- personalized API --------------------------------------------------------
PERSONALIZED_PRIORITY_PLAN = "/api/v1/wave2/personalized/priority-plan"
PERSONALIZED_SCAFFOLD = "/api/v1/wave2/personalized/scaffold"
PERSONALIZED_LEARNING_ITEMS = "/api/v1/wave2/personalized/learning-items"
PERSONALIZED_LEARNING_ITEM = "/api/v1/wave2/personalized/learning-items/{learning_item_id}"

# -- learner API -------------------------------------------------------------
LEARNER_OBSERVATIONS = "/api/v1/wave2/learner/observations"
LEARNER_OBSERVATION = "/api/v1/wave2/learner/observations/{observation_id}"
LEARNER_DIFFICULTIES = "/api/v1/wave2/learner/difficulties"
LEARNER_STRENGTHS = "/api/v1/wave2/learner/strengths"
LEARNER_STABLE = "/api/v1/wave2/learner/stable"
LEARNER_PROFICIENCY_CONTEXT = "/api/v1/wave2/learner/proficiency-context"
LEARNER_EVIDENCE = "/api/v1/wave2/learner/evidence"

PROBE_PATH = LEARNER_OBSERVATIONS

# HTTP statuses that mean "the Wave-2 endpoint is not wired up yet" rather
# than a real service failure. Everything else 4xx/5xx is a classified error.
UNAVAILABLE_STATUSES = frozenset({404, 405, 503})

# Audit/research-only payload fields. Student views are built by allowlist;
# this set is the explicit policy record and the test guard for it.
STUDENT_INTERNAL_KEYS = frozenset({
    "essay_text_hash",
    "analysis_run_id",
    "analysis_version",
    "feedback_record_id",
    "revision_group_id",
    "revision_snapshot_id",
    "corpus_routing",
    "reanalysis_events",
    "evidence_refs",
    "feature_id",
    "diagnosis_id",
    "plan_item_id",
    "observation_id",
    "occurrence_id",
    "behavior_id",
    "revision_event_id",
    "anchor_id",
    "evidence_id",
    "claims_status",
    "history_reasons",
    "record_version",
    "code",
    "provenance",
    "artifact_path",
    "reference_group",
    "distribution",
    "occurrence_count",
    "qualified_occurrence_count",
    "qualified_sample_count",
    "prior_occurrence_count",
    "window_size",
    "descriptive_proportion",
    "days_since_last_observed",
    "revision_response",
    "addressed_in_prior_revision",
    "supporting_submission_ids",
    "originating_evidence",
    "feedback_reference",
    "revision_history",
    "frequency",
    "generated_at",
    "plan_id",
    "observed_at",
    "first_observed_at",
    "last_observed_at",
    "recorded_at",
    "no_fsrs_note",
    "no_practice_note",
    "never_writes_statement",
    "default_first",
    "available_levels",
    "evidence",
    "occurrences",
})

# Written-context -> legacy genre mapping used by the degraded (standard)
# flow so the existing /api/v1/submissions path receives a valid genre.
LEGACY_GENRE_BY_CONTEXT = {
    "cet4": "argumentative essay",
    "cet6": "argumentative essay",
    "ielts_task2": "argumentative essay",
    "toefl_style": "argumentative essay",
    "course_essay": "argumentative essay",
    "other": "argumentative essay",
    "email": "expository essay",
    "application": "expository essay",
    "reflective_journal": "expository essay",
}