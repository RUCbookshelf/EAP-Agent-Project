# Feedback Engagement Trace v0.9

## Purpose

A Feedback Engagement Trace records the observable lifecycle of a feedback-derived practice target through the system. It tracks events without claiming learning or mastery.

## Lifecycle States

| State | Meaning |
|-------|---------|
| `target_identified` | A practice target was created from a selected diagnosis |
| `practice_available` | An exercise instance was generated for the target |
| `practice_attempted` | At least one student attempt was submitted |
| `practice_response_candidate` | A practice evaluation detected a target-action |
| `within_task_response_candidate` | A linked revision shows the targeted pattern |
| `later_task_recurrence` | A later independent task shows the same issue |
| `later_task_nonrecurrence` | A later independent task does not show recurrence |
| `later_task_mixed_evidence` | Mixed signals across later tasks |
| `insufficient_evidence` | Not enough comparable data |
| `archived` | Target closed |

## Storage

Traces are persisted in the `feedback_engagement_traces` table with trace_id (FET prefix), student_id, target_code, and full trace JSON. They are append-only and never overwritten.

## Interpretation Boundaries

- An attempt is not engagement
- Engagement is not learning
- A trace is a descriptive record, not an evaluation of teaching effectiveness
- Later-task signals are candidates, not proof of transfer
