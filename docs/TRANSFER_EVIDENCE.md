# Transfer Evidence v0.9

## Purpose

Transfer Evidence Candidates record observations of recurrence or nonrecurrence of a targeted pattern in a later independent writing task. They are descriptive signals, not proof of transfer.

## Requirements

A transfer candidate requires:
1. A previously established practice target
2. A later submission that is an independent writing task (different Revision Group)
3. Task comparability assessment (comparable / not_comparable)

## Observed Status

| Status | Meaning |
|--------|---------|
| `recurrence_signal` | Targeted pattern persists in the later task |
| `nonrecurrence_signal` | Targeted pattern was not observed in the later task |
| `mixed_signal` | Mixed evidence across later observations |
| `not_comparable` | Tasks are too different to compare |
| `insufficient_evidence` | Not enough data for assessment |
| `version_incompatible` | Metric or analysis versions differ |

## Boundaries

- One nonrecurrence signal does not establish stable transfer
- Same-revision-group submissions are rejected as transfer evidence
- The observation is descriptive, not causal
- "The practice caused the later pattern" is never claimed

## Storage

Candidates are persisted in `transfer_evidence_candidates` table with transfer_evidence_id (TE prefix), student_id, practice_target_id, source/later submission IDs, task comparability, and limitations.
