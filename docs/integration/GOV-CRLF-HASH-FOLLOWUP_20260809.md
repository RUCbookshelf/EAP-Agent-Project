# GOV-CRLF-HASH-FOLLOWUP — Policy-Artifact Hash Line-Ending Normalization

**Goal:** GOV-CRLF-HASH-FOLLOWUP (Research Governance CRLF/Hash Follow-up)
**Owner:** GOV (Research Evaluation & Data Governance)
**Worktree:** `A:\EAP Agent Project\worktrees\research-governance`
**Branch:** `dept/research-governance`
**Baseline (starting SHA):** `5aafe2728d7135212bd675a6975b44bcf99ee099` (promoted master)
**Date:** 2026-08-09
**Verdict:** GREEN (bounded follow-up; targeted tests pass)

## 1. Scope and debt being closed

Wave-1 recorded, GOV-owned debt (Environment Foundation Gate re-verification
handoff `int-env-gate-reverify-001`): *"CRLF policy-hash debt remains Research
Evaluation-owned."* The policy registry validator hashed raw artifact bytes, so a
checkout whose working-tree files use CRLF line endings (Git `core.autocrlf=true`
with no `.gitattributes` rule for policy JSON) produced hashes that differ from the
recorded `artifact_hash` values — which were computed on the LF (Git blob) form.

This follow-up makes policy-artifact hash verification deterministic across
checkout line endings by normalizing CRLF to LF before hashing, documents the rule,
and adds targeted tests. No other governance policy change; no raw corpus access;
no scope expansion.

## 2. Root cause (direct evidence)

On this machine `core.autocrlf=true`; `docs/departments/research-evaluation-governance/
foundation/policies/*.json` contains no `.gitattributes` override, so every policy
artifact is checked out with CRLF endings (observed: 17–37 CRLF, 0 LF per file).

Recorded vs recomputed SHA-256 (all 8 artifacts, 2026-08-09):

| Artifact | Raw disk bytes match recorded? | LF-normalized match recorded? |
| --- | --- | --- |
| corpus_use_policy.json | no | **yes** |
| evaluation_protection_policy.json | no | **yes** |
| duplicate_policy.json | no | **yes** |
| reference_group_eligibility_policy.json | no | **yes** |
| measurement_claim_policy.json | no | **yes** |
| stage6_evidence_admissibility_policy.json | no | **yes** |
| audit_sampling_policy.json | no | **yes** |
| evaluation_leakage_policy.json | no | **yes** |

Baseline test run before the fix (Python 3.12.13, pytest 9.1.1, `--noconftest`):
`2 failed, 26 passed` — `test_policy_registry_consistency` and
`test_run_all_validators` failed with 8 `hash mismatch for <artifact>` findings.

## 3. Normalization rule (POLICY-HASH-1)

> The canonical content hash of a policy JSON artifact is SHA-256 over its
> LF-normalized bytes: every CRLF (`\r\n`) sequence is converted to LF (`\n`)
> before hashing (the Git blob form). Working-tree line-ending conversion
> (`core.autocrlf`, `.gitattributes`) therefore never changes registry hashes; a
> CRLF checkout hashes identically to an LF checkout, and the recorded
> `artifact_hash` values in `policy_registry.json` remain valid in both.

Recorded `artifact_hash` values are unchanged (they are already the LF-canonical
hashes). Content changes are still detected: normalization only collapses the
line-ending representation, not content.

## 4. Changes (minimal, GOV-owned)

1. `app/research/governance/validators.py` — added `_lf_canonical_bytes`,
   `_policy_artifact_digest_bytes`, `_policy_artifact_digest` and switched
   `validate_policy_registry` from `hashlib.sha256(path.read_bytes())` to the
   LF-canonical digest.
2. `docs/departments/research-evaluation-governance/foundation/02_POLICY_VERSIONING.md`
   — sections 3–4 now state the POLICY-HASH-1 rule and reference this record.
3. `tests/test_research_governance_v01.py` — 4 new targeted tests:
   - `test_policy_registry_hashes_are_lf_canonical` — every recorded hash equals the
     LF-canonical digest of its artifact.
   - `test_policy_hash_normalizes_crlf_to_lf` — digest invariant under CRLF↔LF
     conversion.
   - `test_policy_registry_valid_under_crlf_checkout` — simulated CRLF checkout
     (content identical, CRLF bytes) validates end-to-end.
   - `test_policy_registry_detects_hash_mismatch` — a real content change still
     produces the `hash mismatch` finding.

## 5. Verification (direct evidence)

Command (worktree root; interpreter from the Wave-1 gate venv, Python 3.12.13,
pytest 9.1.1, `--noconftest` per the foundation verification method, writable
`--basetemp`, no bytecode/cache writes):

```text
python -m pytest tests/test_research_governance_v01.py --noconftest -p no:cacheprovider --basetemp <tmp> -v
```

Result: **32 passed / 0 failed** in 0.46s (28 pre-existing + 4 new). Exit code 0.

## 6. Boundaries respected

- Writes confined to `worktrees\research-governance` (canonical GOV worktree).
- No master, other worktree, historical GOV evidence, or raw SWECCL touched.
- No pre-existing dirty/untracked file modified; no push/PR/promotion.
- No policy content, registry hash, schema, or other validator behavior changed.

## 7. Handoff summary

Department verdict: **GREEN**. Integration required (`integration_required=true`);
promotion not eligible from this follow-up alone. Remaining GOV-owned queue items
are unchanged (e.g., migration-14 review participation is a later coordinated
activity, not part of this goal).
