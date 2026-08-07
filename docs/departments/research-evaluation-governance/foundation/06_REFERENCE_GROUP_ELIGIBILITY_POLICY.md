# 06 — Reference-Group Eligibility Policy

**Department:** Research Evaluation & Data Governance
**Policy id:** `reference-group-eligibility-policy-v0.1.0`
**Ratification:** RD-POL-006 (2026-08-07)
**Status:** RATIFIED
**Supersedes:** none (first canonical version; reviews and ratifies L2-04 with justification)

## 1. Scope

This policy governs which reference groups may be used, for what, and with which
disclosure, in the Corpus Intelligence layer (v0.1: `reference-groups-v0.1.0`,
`reference-distributions-v0.1.0`, `corpus-features-v0.1.0`). It decides the status of
`N >= 30`, defines `eligible / limited / unavailable / requires review` criteria, and
ratifies the fallback hierarchy. Group **selection** for a domain profile remains a
domain-department concern (D-37/RT-15); eligibility is this department's concern.

## 2. Status of min-N = 30 (the core question)

**Decision: for v0.1 descriptive reference distributions, `N >= 30` effective (after
duplicate policy) is ratified as a general, feature-independent eligibility floor —
with the explicit understanding that it is a conservative descriptive heuristic floor
(F8 resolution: no empirical stability property is claimed by the round number), NOT a
normative/scientific sufficiency guarantee. It is a temporary-heuristic boundary for any
normative use (which remains blocked by D-07), and feature-dependent floors are allowed
as future amendments when the feature set expands.**

Reasoning (documented, per goal section 10):

1. **Effective N and duplicate sensitivity.** The floor applies to effective N (canonical
   members only, 05 policy). Duplicate members never inflate the count. Verified:
   all 75 approved groups have n_effective ≥ 30; the minimum is exactly 30
   (`RG-prompt_id=ARG01-timed_status=untimed`); no group falls below (methodology review D4).
2. **Missingness.** Missing values are never imputed; the floor must hold for
   complete-case N as well (min over all distributions of n_effective − n_missing = 30;
   max n_missing = 2 across the 100 flagged records). Feature-level missingness is
   disclosed per distribution (validity_flags), and features with higher missingness are
   flagged (L2-04:16-17).
3. **Distribution stability.** A round number does not by itself guarantee stability.
   This policy therefore adds stability safeguards independent of N: zero-variance /
   zero-IQR distributions are flagged; entry-year groups 2003 (N=68) and 2007 (N=453)
   are `limited` (usable descriptively, fragile as norms — RD-08); prompt imbalance and
   timed/untimed differences are documented as group-level limitations, never normalized
   away (L2-06).
4. **Prompt imbalance.** Groups are defined with prompt control wherever possible
   (prompt-only and prompt×timed groups); genre-level and other broad groups are
   descriptive only (RD-08 hard constraints).
5. **Feature-specific availability.** All v0.1 features share one feature contract and
   similar missingness profiles at corpus scale (14 features × 75 groups; 100 flagged
   records), so a single floor is defensible at v0.1. When features with structurally
   different missingness or external resources are added (e.g., lexical sophistication,
   D11), a feature-dependent floor becomes a policy amendment (major or minor per 02 §2).
6. **No validity claim.** This floor establishes no statistical validity, proficiency,
   mastery, or measurement property. Normative interpretation of any band/percentile
   remains blocked by the validated-measurement gate (D-07; ARCH-14:68-75).

**Conclusion table:**

| Question | Answer |
| --- | --- |
| Is N ≥ 30 a temporary heuristic? | It is a conservative descriptive floor; for v0.1 reference eligibility it is policy (general, feature-independent). For normative/scientific sufficiency it remains a temporary heuristic with no validity claim. |
| Is it general policy? | Yes, for v0.1 descriptive reference distributions (feature-independent). |
| Is it feature-dependent policy? | Not at v0.1; feature-dependent floors are permitted as future amendments. |

## 3. Eligibility criteria

| Status | Criteria (all must hold) |
| --- | --- |
| `ELIGIBLE` | Group is in the approved set (75); effective N ≥ 30 after duplicate policy; complete-case N (n_effective − n_missing) ≥ 30; feature version matches the query contract; distribution record exists; no degenerate-distribution flag; purpose is observed descriptive reference evidence. |
| `LIMITED` | Eligible by N but: n_missing > 0 (flagged per distribution; **elevated missingness** defined operationally as n_missing >= 2 or n_missing / n_effective >= 0.05 — F7 resolution; observed maximum is 2), or degenerate/zero-variance/zero-IQR flag, or group is entry_year 2003/2007 (fragile for norms). Limited groups may be used descriptively with the flag disclosed; they may not be presented without their limitation. |
| `UNAVAILABLE` | ARG13 / ARG19 standalone; any group with effective N < 30 after duplicate policy; unknown/unsupported group id; missing distribution record; feature/version mismatch (I3); corrupt-resource conditions. |
| `REQUIRES REVIEW` | Any use outside the descriptive reference purpose: normative interpretation (D-07 gate), learner-facing output (D-08 gate), cross-version or fallback-analyzer comparisons (I3), model development (05 §4.4), frequency-resource-dependent features (D11), or selection of a group not in the approved set. |

## 4. Approved groups and unavailable groups (ratified facts)

- 75 approved groups = 25 prompt-only + 35 prompt×timed + 2 genre + 2 timed +
  2 major_type + 4 grade + 5 entry_year (L2-04:24; methodology review D4 condition 2 —
  the corrected decomposition is canonical).
- ARG13 (n_raw=14) and ARG19 (n_raw=18) exist in the runtime index as
  `availability=unavailable` standalone groups; their documents still participate in 11
  broader groups (32 documents, 160 membership rows) — preserved, not removed
  (methodology review D4).
- Any group whose effective N falls below 30 after duplicate policy is unavailable
  (L2-04:29-30).
- Unknown/unsupported group ids raise `CorpusInvalidRequestError` (L2-07).

## 5. Fallback hierarchy (ratified with disclosure contract)

```text
prompt+timed -> prompt -> genre+timed -> genre -> UNAVAILABLE
```

Conditions:

1. Genre is derived from the prompt prefix when not supplied (ARG → argumentative,
   EXP → expository) — a deterministic rule (L2-04:34-37).
2. Every query result must report the requested group, the resolved group, and the
   fallback disclosure; silent broadening is impossible by construction (I4; L2-04).
3. Fallback resolution is for descriptive reference lookups. Any artifact that uses a
   fallback-resolved group must carry the disclosure in its admissibility record
   (08_STAGE6_EVIDENCE_ADMISSIBILITY.md).
4. Fallback to a genre-level group without prompt control is descriptive only; it is
   not a prompt-controlled comparison (RD-08 hard constraints).
5. A human-readable fallback reason (e.g., "prompt+timed group effective N < 30") is
   recommended as a future enhancement to `fallback_disclosure` (methodology review D4
   non-blocking note); the machine key remains the disclosed resolved group id.

## 6. Group-selection boundary

This policy governs eligibility and disclosure, not domain-profile selection. Admissible
features per construct, reference-group selection, and interpretation wording are owned
by domain departments (D-37/RT-15; ARCH-07 amendment). Any domain profile selecting a
group must satisfy this policy's eligibility criteria first.

## 7. Change control

- Raising/lowering the floor, adding feature-dependent floors, or changing the fallback
  hierarchy = major policy change (02 §2) with methodological review and, where the
  query boundary contract is affected, Architecture & Integration review (ARCH-13 §1).
- Adding approved groups requires validation against the same criteria and a registry
  update (membership + distributions) by Corpus & NLP with this department's sign-off.

## 8. Machine artifact

`policies/reference_group_eligibility_policy.json` mirrors sections 3-5 and validates
against `policies/policy_schema.json` (WU11). WU11 also implements the eligibility
validator against the actual membership/distribution artifacts.