# Practice Model v0.9

The practice model establishes an auditable formative-learning loop connecting validated diagnoses to targeted practice exercises and observational evidence. It does not produce mastery, proficiency, scoring, or causal claims.

## Architecture

Feedback delivery → Diagnosis → Selected revision priority → Practice Target → Exercise Instance → Student Attempt → Practice Evaluation → Within-task Response Candidate → Later-task Transfer Evidence Candidate

## Key Concepts

### Practice Target
Created only from selected (non-suppressed) diagnostic gate outputs. Each target binds a specific diagnosis to a practice scope. Multiple targets may exist per student across submissions.

### Exercise Specification Registry
Three deterministic exercise types:
- `guided_sentence_rewrite`: learner rewrites a source sentence addressing the target
- `constrained_micro_revision`: learner revises a short text under constraints
- `target_feature_identification`: learner identifies the targeted feature in a passage

### Exercise Instance
An immutable exercise record with instructions, constraints, source text, and generation metadata. Currently all exercises use deterministic templates; DeepSeek-assisted generation is disabled by default.

### Student Attempt
Append-only response records. Each attempt is numbered and time-stamped. Empty or invalid responses are stored as INVALID_INPUT status.

### Practice Evaluation
Conservative rule-based evaluation producing:
- Completion status (completed/incomplete/invalid)
- Target-action status (candidate detected/not detected/inconclusive)
- Evidence and limitations

Evaluations never produce mastery language.

### Feedback Engagement Trace
Tracks the lifecycle of a feedback priority through the practice pipeline: target_identified, practice_available, practice_attempted, practice_response_candidate, within_task_response_candidate, later_task_recurrence/nonrecurrence, insufficient_evidence.

### Within-task Response Candidate
Observation that a linked revision within the same task group shows a target-action pattern. Major rewrites limit attribution. Not causal.

### Transfer Evidence Candidate
Observation of recurrence/nonrecurrence in a later independent comparable task. One signal does not establish stable transfer. Same-task revisions are rejected.

## Boundaries

- An attempt is not engagement
- Engagement is not learning
- A response candidate is not causation
- One nonrecurrence is not transfer
- No mastery/proficiency/CEFR/score labels are stored or emitted

## Persistence

All 8 practice tables are managed by migration 12. Repository methods save/list all entities with ID generation (PT/EX/EA/PE/FET/WTR/TE/PSS prefixes).
