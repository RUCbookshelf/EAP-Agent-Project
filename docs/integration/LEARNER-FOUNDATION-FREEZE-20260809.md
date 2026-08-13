# LEARNER-FOUNDATION-FREEZE — Gate-qualified commit record

**Goal:** `LEARNER-FOUNDATION-FREEZE`  
**Owner:** LEARNER (Feedback & Learner Intelligence)  
**Gate authority:** INT (`INT-INTEGRATION-GATES-WAVE5`)  
**Recorded at:** `2026-08-09T13:19:51Z`

## Commit identity

| Field | Verified value |
| --- | --- |
| Worktree | `A:\EAP Agent Project\worktrees\learner` |
| Branch | `dept/feedback-learner` |
| Starting SHA / required parent | `09264abbd93cdc6b62b83cefd94b3b640319ac9b` |
| Resulting commit | `14cdc18df0919af4cc5e3c35c2274cc8a0164bcd` |
| Commit tree OID | `98a625b50142ff813c7f93e8f96f70816f282c63` |
| Commit subject | `freeze(learner): commit gate-qualified foundation` |
| Commit scope | 16 paths; `2720` insertions, `1` deletion |

The verified parent is exactly the promoted baseline. No merge, rebase, reset,
clean, push, PR, or promotion was performed.

## Gate-qualified fingerprints

The Wave-5 gate-record prefixes match the current worktree bytes exactly:

| Gate artifact | SHA-256 |
| --- | --- |
| `app/learner/evidence.py` | `42316560B51BDEE823446E57FE3CE6D3586BDBAB1EE77A5BC2ABC283C1A9F87F` |
| `app/learner/exposure.py` | `BFA1BC5024F66B8DE531AFFD2A1C2864C3721E08EBE6E6B11057F3B69DB55C4F` |
| `app/learner/normative.py` | `B78312CD9ADE3722F1876604C40FE231DCD2665E92DF319D148CD7EE1A44A124` |
| `app/learner/feedback_policy.py` | `277A6357767C71FDB96598BE6BFFC5CF2BC737702209449BB476438382DDD58A` |
| `app/learner/practice_provenance.py` | `1AABEB9C3F0BDC13BD8FFA29AF8E312B3CD18BF3DF25C3AD4C099D14BBAFA561` |

- **Qualified working-tree scope fingerprint (SHA-256):** `3ed18751ec9934c484b5bd45313d2558e8cd6dd8bfd7167320c03659cef103f3`.
  This is SHA-256 of UTF-8 sorted `path|raw-file-SHA-256` lines for the 16
  gate-qualified paths, terminated by one LF.
- **Committed canonical blob-set fingerprint (SHA-256):** `83d19bc1fcc04b95b41584f94c18277e06d91eca4e445091daaa29d177f70b64`.
  This is SHA-256 of UTF-8 sorted `path|Git-blob-OID` lines for the same 16
  paths, terminated by one LF.
- Every committed blob OID equals the pre-commit staged blob OID. The
  worktree has no content diff against `HEAD` over those 16 paths.

`core.autocrlf=true` clean-normalized the existing manifest's 201 CRLF line
endings in the Git blob. This is not a scope or semantic drift: the staged
diff was inspected and contains exactly the five allowed LEARNER registrations
shown below; the other 15 paths were byte-identical between worktree and index.

## Committed inventory (exactly 16 paths)

```text
M  app/learner/__init__.py
A  app/learner/evidence.py
A  app/learner/exposure.py
A  app/learner/feedback_policy.py
A  app/learner/normative.py
A  app/learner/practice_provenance.py
A  docs/integration/LEARNER-FOUNDATION-20260809.md
A  docs/learner/LEARNER_FOUNDATION_OVERVIEW.md
A  docs/learner/LEARNER_FOUNDATION_PERSISTENCE_DESIGN_NOTE.md
A  tests/learner/test_evidence_records.py
A  tests/learner/test_exposure_enforcement.py
A  tests/learner/test_feedback_policy_scaffolding.py
A  tests/learner/test_no_normative_claims.py
A  tests/learner/test_practice_provenance.py
A  tests/learner/test_wu_d_contract_mirror.py
M  verification/shared-core-h1/module_set_manifest.json
```

The manifest diff is limited to these five registrations:

```text
learner/evidence.py
learner/exposure.py
learner/feedback_policy.py
learner/normative.py
learner/practice_provenance.py
```

## Verification evidence

| Check | Result |
| --- | --- |
| Wave-5 raw SHA-256 fingerprints | PASS — all five required prefixes matched full hashes above |
| Focused isolated gate (post-commit) | PASS — `123 passed in 0.30s` for `tests/learner`, `tests/contracts/test_wave1_vocabulary_convergence.py`, and `tests/shared/test_vocabularies.py` |
| Test isolation | PASS — a fresh temporary database was resolved; development database was absent before and after; no pytest cache or root bytecode cache remained |
| Staged scope and final commit scope | PASS — exactly the 16 paths above; parent equals the required baseline |
| Git whitespace check | PASS — `git diff --check HEAD^ HEAD` exit `0` |
| Committed-tree identity | PASS — full tree OID and all 16 pre-stage/HEAD blob OIDs matched the recorded qualified set |

Authoritative evidence read for this freeze:

- `program-control/handoff-digests/LEARNER-FOUNDATION__LEARNER-FOUNDATION__20260809T074629Z__aae1ed.digest.json`
- `program-control/handoffs/LEARNER/LEARNER-FOUNDATION__LEARNER-FOUNDATION__20260809T074629Z__aae1ed.handoff.json`
- `worktrees/int-study-base/docs/integration/INT-INTEGRATION-GATES-WAVE5-20260809.md`

## Exclusions and preserved state

- **No positively identified transient scratch handoff copy was removed.**
  The untracked-path check found no path containing `handoff`. The existing
  `docs/integration/LEARNER-FOUNDATION-20260809.md` is a required digest
  artifact and was committed, not removed.
- `tests/learner/__init__.py` was already untracked at preflight. It is a
  one-line package marker, is not in the digest's 14 `artifact_refs`, and is
  not one of the two explicitly authorized modified files. It was preserved
  unchanged and deliberately left unstaged; it did not enter the commit.
- This record was written after the immutable commit SHA was known and is
  deliberately left **uncommitted**. Keeping it as a handoff sidecar ensures
  commit `14cdc18...` contains only the packet's 16 gate-qualified foundation
  paths.

## Boundary

The resulting SHA is a local, integration-qualified freeze candidate only.
It has **not** been promoted and has not been pushed. Promotion requires a
separate exact-SHA authorization.
