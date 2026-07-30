# Revision analysis v0.5

## v0.7.1 within-task trajectory

The new trajectory is a read-only composition of existing explicit relationships and append-only Revision Snapshots. It reports the ordered Draft Chain, adjacent pairwise comparisons, first-to-latest comparison, diagnosis/metric changes, prior selected priorities, feedback-uptake candidates, major-rewrite status and attribution confidence. It never adds a cross-task observation, claims revision quality, or attributes change to feedback. See [WITHIN_TASK_REVISION_TRAJECTORY.md](WITHIN_TASK_REVISION_TRAJECTORY.md).

## v0.7 integration

Revision Snapshot v0.5 remains unchanged and continues to compare all explicitly linked drafts. Learner Model v0.7 separately selects one representative per Revision Group for default long-term description (`final_or_latest`). Excluding earlier drafts from a long-term trajectory does not delete or suppress revision alignment evidence. Alternative representative strategies are versioned configuration choices.

Revision analysis starts only from an explicit `revision_of_submission_id`. Matching prompts or student IDs may
produce candidates but never create a relationship. The service rejects cross-student, self, cyclic and duplicate
links and preserves every essay.

The deterministic local pipeline aligns paragraphs and sentences, then reports token insertions, deletions and
modifications. Alignment types are `unchanged`, `lightly_modified`, `heavily_modified`, `inserted`, `deleted`,
`split`, `merged` and `unaligned`. It records compatible metric differences, diagnosis trajectories, task
comparability, major-rewrite status, algorithms, resources and limitations.

Every calculation is stored as a new Revision Snapshot. Older Snapshots remain queryable, allowing later algorithm
comparisons. Outputs describe observed text changes only; they do not measure revision quality or learner ability.

The v0.6 revision page renders the stored API Snapshot: relationships, edit ratios, metric changes, diagnosis
trajectories, uptake candidates, major-rewrite warning, versions and limitations. Revision changes remain separate
from the long-term dashboard except for the configured single representative draft.
