# Revision analysis v0.5

Revision analysis starts only from an explicit `revision_of_submission_id`. Matching prompts or student IDs may
produce candidates but never create a relationship. The service rejects cross-student, self, cyclic and duplicate
links and preserves every essay.

The deterministic local pipeline aligns paragraphs and sentences, then reports token insertions, deletions and
modifications. Alignment types are `unchanged`, `lightly_modified`, `heavily_modified`, `inserted`, `deleted`,
`split`, `merged` and `unaligned`. It records compatible metric differences, diagnosis trajectories, task
comparability, major-rewrite status, algorithms, resources and limitations.

Every calculation is stored as a new Revision Snapshot. Older Snapshots remain queryable, allowing later algorithm
comparisons. Outputs describe observed text changes only; they do not measure revision quality or learner ability.
