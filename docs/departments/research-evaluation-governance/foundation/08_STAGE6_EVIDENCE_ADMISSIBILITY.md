# 08 — Stage-6 Evidence Admissibility

**Department:** Research Evaluation & Data Governance
**Policy id:** `stage6-evidence-admissibility-policy-v0.1.0`
**Ratification:** RD-POL-008 (2026-08-07)
**Status:** RATIFIED
**Supersedes:** none (first canonical version)

## 1. Purpose and scope

Without implementing Stage 6, this policy defines the evidence a future diagnostic
comparison (student feature vs reference distribution) must provide before any
comparison artifact may be admitted. It defines `ADMISSIBLE / LIMITED / UNAVAILABLE /
INVALID` and the required admissibility record. It does **not** define the diagnostic
algorithm, thresholds, or any inference procedure — those belong to future Stage-6 work
with Feedback & Learner Intelligence.

## 2. Required admissibility record (every field, no silent defaults)

| Field | Requirement | Missing consequence |
| --- | --- | --- |
| corpus_package_id + manifest_hash | `sweccl2-weccl20-v0.1.0` + `0d8940ff…59eb9` (registered, L2-01) | UNAVAILABLE (unregistered corpus) |
| FeatureSetVersion | known; student side must equal corpus side (`corpus-features-v0.1.0`); same implementation both sides (I3) | UNAVAILABLE / INVALID on mismatch — never "best-effort comparable" |
| ReferenceGroupVersion | known (`reference-groups-v0.1.0`) | UNAVAILABLE |
| DistributionVersion | known (`reference-distributions-v0.1.0`) + algorithm version | UNAVAILABLE |
| requested_reference_group | known, non-empty | INVALID (silent default forbidden) |
| resolved_reference_group + fallback_disclosure | resolved group disclosed; null only when exact match | LIMITED when fallback used (disclosure mandatory); INVALID when null/empty with resolved != requested |
| feature_id | known feature in `corpus-features-v0.1.0`; distribution record must exist for resolved group × feature | UNAVAILABLE when no record exists |
| effective N | n_effective (post-duplicate-policy) and n_raw reported | INVALID (unsupported statistics) |
| availability | status + reason from the distribution record | UNAVAILABLE |
| feature value reproducibility | feature_set_version + analyzer version + same extraction implementation; no fallback analyzer | INVALID when fallback-analyzer-produced (I3; ARCH-07:45) |
| missingness | n_missing + validity flags; never imputed | LIMITED when n_missing > 0; INVALID if imputed |
| comparison direction | descriptive only (observed reference evidence) | INVALID if normative wording present |
| epistemic status | L0 `observed_descriptive` (downgrade-only; D-09) | INVALID |
| learner_exposure | `research_only` | INVALID (D-08 default disabled) |
| provenance chain | the 7-field provenance of the distribution record | UNAVAILABLE |
| score fields | none (270-block protection, EP-06) | INVALID |
| banned vocabulary | none (I1 naming contract) | INVALID |

## 3. Status determination

### `ADMISSIBLE`

All record fields present and correct; versions match (I3); resolved group is
`ELIGIBLE` per 06 (effective N ≥ 30 and complete-case N ≥ 30); availability=available;
no validity flags; no fallback (exact group match); feature value reproducible under
the same feature contract; comparison expressed as observed descriptive evidence;
learner_exposure research_only.

### `LIMITED`

Admissible except one or more of: validity flags present (missingness > 0, degenerate
distribution), fragile entry-year group (2003/2007), or fallback disclosure non-null
(resolved group differs from requested). The comparison may be used descriptively with
the disclosure and limitation attached to the artifact; it may never be presented
without them.

### `UNAVAILABLE`

ARG13/ARG19 standalone; any group with effective N < 30 after duplicate policy;
missing distribution record; feature/version mismatch (I3); fallback-analyzer feature;
license-restricted operation (03); unknown corpus/feature/group; corrupt resource
(L2-07 failure states). UNAVAILABLE is a terminal status for that artifact version:
no widening, no substitution.

### `INVALID`

Any of: prohibited inference attempted (proficiency/mastery/learning-gain/CEFR wording;
normative interpretation without the validated-measurement gate — D-07); causal or
transfer claims; cross-version comparison; circular use of the 270 scored block
(04 EP-04/EP-05); score fields in the artifact (EP-06); learner-facing exposure without
the D-08 display policy and licensing/anonymization gate; missing required fields
silently defaulted; imputed missingness; fallback disclosure null/empty while the
resolved group differs from the requested group.

**Precedence (F14 resolution):** INVALID (prohibited use) is evaluated first, then
UNAVAILABLE (record-level version/availability/N/provenance failures), then LIMITED.
Record-level version mismatch ⇒ UNAVAILABLE; a design that *uses* a cross-version
comparison ⇒ INVALID at the design-review level. The machine check implements this
order (`assess_admissibility`).

## 4. Comparison-direction contract

```text
Permitted:  "this feature value is near the upper part of this reference distribution"
            (with group, versions, effective N, disclosure).
Prohibited: "the learner has advanced proficiency" / "the learner mastered this skill"
            / "the learner improved" (07 policy).
```

The comparison artifact carries descriptive statistics and position only. Any
interpretive sentence must come from a verified slot produced deterministically
(I5) and must pass the 07 claim templates.

## 5. Binding rules for Stage 6

1. Every comparison artifact is created with its admissibility record; no artifact
   without an admissible record may enter diagnosis, feedback, or research output.
2. Version mismatch between student feature extraction and the corpus feature contract
   ⇒ UNAVAILABLE, never "comparable".
3. Fallback usage is disclosed per artifact; the requested and resolved groups are
   both recorded.
4. Effective N and missingness are reported per artifact; complete-case N is reported
   (methodology review D4 non-blocking recommendation).
5. The 270 scored block and duplicate groups follow 04 and 05; no partition may split
   them (10).
6. Learner-facing corpus output remains disabled by default (D-08; 03 CU-05).
7. These rules are machine-checkable: WU11 provides `assess_admissibility(record)`
   returning one of the four statuses with reasons (department-owned; not part of the
   diagnostic algorithm). The check enforces every row of section 2, including
   score-field absence (EP-06), the 7-field provenance chain, n_raw sanity
   (n_raw >= 1 and >= n_effective), fallback/resolved consistency, approved-set
   membership, distribution-record existence, and n_effective agreement with the
   distribution record (F3/F6 resolutions).

## 6. Out of scope (explicit)

The diagnostic algorithm, threshold selection, band method (quantile vs SD), comparison
distance metric, and any inference procedure are NOT defined here (D4 remains a
Researcher decision; ARCH-15:43). This policy only defines what evidence must exist and
be disclosed before Stage 6 may admit a comparison.

## 7. Machine artifact

`policies/stage6_evidence_admissibility_policy.json` mirrors sections 2-4 and validates
against `policies/policy_schema.json` (WU11).