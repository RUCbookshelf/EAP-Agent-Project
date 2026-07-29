# Learner Profile Snapshot v0.3

Each Snapshot contains:

- pseudonymous student and `LPnnnnnn` Snapshot ID;
- generation time and included/excluded submission evidence;
- baseline status and BaselineProfile;
- eight metric trends (or a requested subset);
- persistent, recently reduced and unstable issue trajectories;
- at most 3 current priority candidates;
- confidence summary, limitations, analysis and configuration versions.

Snapshots are append-only. Recalculation never overwrites an older Snapshot; Repository methods return the latest or complete history. This supports later comparison of algorithm versions.

For LLM feedback, only a screened Snapshot is placed in FeedbackContext. It omits excluded submissions and raw historical observations. The local engine converts selected results into H evidence IDs; the Provider must cite those IDs and cannot recompute direction or confidence.

The Snapshot is not a learner proficiency model, score, ranking or verified developmental record. Teacher/researcher review remains necessary.
