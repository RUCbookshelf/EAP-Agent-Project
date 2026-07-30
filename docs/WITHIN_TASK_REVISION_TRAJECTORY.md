# Within-task Revision Trajectory v0.7.1

## Purpose

The trajectory answers how one explicitly linked writing task changed across drafts. It is independent of the cross-task learner model: four drafts in one Revision Group are four draft submissions, one Revision Group, one independent writing task and one default longitudinal representative.

## Contract

`WithinTaskRevisionTrajectory` contains:

- ordered `draft_chain` entries with submission ID, sequence, stage and time;
- adjacent `pairwise_comparisons` derived from saved Revision Snapshots;
- `first_to_latest_comparison` derived with the same deterministic comparison routine;
- aggregated diagnosis and compatible metric changes;
- previous selected priorities and feedback-uptake candidates;
- `major_rewrite_detected`, `attribution_confidence` and limitations.

The API endpoint is `GET /api/v1/revisions/{revision_group_id}/trajectory`. The same object is returned on a revision submission and rendered in the Revision tab.

## Interpretation boundary

Alignment and metric/diagnosis differences are observed prototype evidence. They do not score revision quality, establish learning or proficiency growth, or prove that feedback caused a change. When a major rewrite prevents reliable alignment, uptake candidates are `not_assessable`, the UI explains the limitation, and attribution confidence is `insufficient`.

The trajectory is computed from existing append-only data and does not append a new Snapshot during UI reads.
