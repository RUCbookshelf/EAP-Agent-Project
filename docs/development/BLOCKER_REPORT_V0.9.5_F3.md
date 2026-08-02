# v0.9.5-F3 Blocker Report

## Resolution

Resolved on 2026-08-02 by explicit user authorization of one additional
production-file exception: `app/feedback/service.py`. The authorization is
limited to replacing the legacy `LearnerProfileService(self.database)`
composition with an explicitly constructed `ProgressService` and
`LearnerProfileService` that reuse the same facade-owned Learner and
Configuration repository instances. No other `FeedbackPipeline` behavior or
file is authorized to change.

The remaining report preserves the Phase 0 evidence that required this
exception.

## Original status

v0.9.5-F3 is blocked in Phase 0 before production edits. The approved target
requires `LearnerProfileService` to receive an explicitly supplied
`ProgressService` and forbids it from constructing `ProgressService` from a
broad repository internally. The same scope also forbids modifying
`FeedbackPipeline`.

## Confirmed conflict

At approved HEAD `7927ca7`, `FeedbackPipeline.__init__` constructs:

```python
LearnerProfileService(self.database)
```

at `app/feedback/service.py:42`. The target F3 constructor must instead require:

```python
LearnerProfileService(
    repository=LearnerProfileReadPort,
    progress_service=ProgressService(...),
)
```

The legacy pipeline is exercised by the core suite in:

- `tests/test_database.py:43`
- `tests/test_database.py:98`
- `tests/test_history.py:7`
- `tests/test_history.py:26`
- `tests/test_history.py:37`

Therefore, changing `LearnerProfileService` to the required explicit
constructor while leaving `FeedbackPipeline` untouched makes active core tests
fail at construction. Making `progress_service` optional and rebuilding it from
`repository` inside `LearnerProfileService` would violate the explicit F3
requirements that the dependency be supplied and that only the composition root
and submission-factory compatibility path know the broad legacy fallback.

## Why the blocker cannot be repaired inside the approved files

The allowed production files are the three F3 Services, the submission factory,
the application composition root, and (if required) the Service export module.
None can change the direct constructor call in `app/feedback/service.py`.

No compliant workaround exists without at least one prohibited action:

1. modify `FeedbackPipeline` to construct `ProgressService` explicitly from the
   existing facade-owned Learner and Configuration repository instances;
2. retain implicit fallback construction inside `LearnerProfileService`;
3. add a runtime proxy, global registry, or hidden dependency-discovery path;
4. weaken or remove the active core tests.

Options 2-4 directly violate the F3 contract. Option 1 is the narrow,
behavior-preserving composition repair, but the current scope expressly says
not to modify `FeedbackPipeline` and does not allow
`app/feedback/service.py` as a production change.

## Baseline evidence

- Branch: `master`
- HEAD: `7927ca7cb16339757c2a5794edf4ee8776925079`
- Required ancestors `172dbe1` and `7868b68`: confirmed
- Code Review Graph: rebuilt at `7927ca7cb163`
- GitNexus: rebuilt index-only and up to date at `7927ca7`
- Pre-edit graph risk: low to medium; no high or critical result
- No F3 production implementation exists at HEAD
- Development database SHA-256 before/after Phase 0 checks:
  `340E0F3739FEFFD3DEF87BB6E711CB6F90A8478E7E18D833C715EDCFAB03AFF4`
- Development database modification time before Phase 0 checks:
  `2026-08-02T03:02:25.8870088Z`
- No database was opened and no test or application process was started

## Required decision

Authorize exactly one additional F3 production change:
`app/feedback/service.py`, limited to explicit construction and injection of a
`ProgressService` from the same `Database` object's existing composed Learner
and Configuration repositories. No `FeedbackPipeline` workflow, public
constructor, ordering, persistence, transaction, provider, or return behavior
would change.

If that one-file composition exception is not authorized, the F3 requirements
must instead explicitly permit a legacy fallback inside
`LearnerProfileService`; that alternative is not recommended because it
contradicts the stated dependency-narrowing acceptance criteria.

No F3 implementation, F4 work, schema work, SQL change, repository change,
transaction change, API change, UI change, or database operation was performed.
