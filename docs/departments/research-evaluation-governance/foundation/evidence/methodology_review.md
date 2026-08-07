# Independent Methodology Review — Research Evaluation & Data Governance Foundation

**Role:** Independent methodology reviewer (fresh reviewer; did NOT implement any reviewed document; no planning files modified; only this handoff file written).
**Date:** 2026-08-07
**Review target:** `research-governance-foundation-v0.1.0` deliverables 00-12, `policies/*.json`, `app/research/governance/validators.py`, `tests/test_research_governance_v01.py`.
**Baseline:** branch `dept/research-governance-foundation`, HEAD `b171cce921975f5ac8491e9bb344a06043eecd69`.
**Method:** Read-only review against the cited governing evidence; direct execution of the governance validator suite in the Stage-5 corpus venv (Python 3.12.13, pytest 9.1.1): **20/20 tests pass** (matches `11_VERIFICATION.md`); targeted runtime probes of `assess_admissibility`, `validate_claim_text`, and `contains_prohibited_claim`; artifact spot-checks (`reference_group_membership.csv` = 33,543 rows; policy registry; statement-id cross-references).
**Limitation:** The physical corpus files `TOOLS/exp.xls` / `TOOLS/exp.sav` sit outside this repository; their recorded SHA-256 protection keys (04 §2) were not re-computed by this reviewer. Score-linkage facts are accepted on the strength of L2-03:9-24 and the Stage-5 methodology review D1.

---

## A. Measurement-claim policy (07) — PASS_WITH_CONDITIONS

The per-evidence-class bounds are correctly anchored:

- L0 observed feature and L1 gated inference match the D-09 taxonomy and downgrade-only invariant (ARCH-14:86-95; ARCH-08:15-17) and the frozen wording contracts (`app/calibration/service.py:16-18,117`; `app/configuration/schemas.py:36-47`).
- Reference comparison (07 §2.2) is bounded to observed descriptive evidence with mandatory group/versions/N/disclosure, consistent with D-07 (ARCH-14:68-75) and I3/I4 (ARCH-07:29-30).
- Longitudinal evidence (07 §2.5) reproduces `HISTORY_LIMITATION` verbatim (`app/learner/history.py:15-18`) and preserves within-task/cross-task separation and the 2-comparable-tasks rule (ARCH-04:34-37; D-021 in DECISION_LOG).
- Learning outcome (07 §2.6) is reserved, matching the validated-measurement gate (ARCH-08:27-34); learner-facing corpus content stays disabled (D-08, ARCH-14:77-84).
- Banned vocabulary matches I1 (ARCH-07:27) and the configuration risky-phrase contract (`app/configuration/schemas.py:72-77`).

**Conditions / missing classes:**
- Direct learner-to-learner comparison statements (e.g., "outperforms peers") are not named in the 2.2 prohibited column even though cross-student comparison is forbidden in the architecture (ARCH-04:34). The general "no normative interpretation without the validated-measurement gate" rule covers them, but an explicit row is recommended.
- The guardrails contradict the policy's own canonical templates and mandated disclaimer (findings F1, F2, F4) — must be fixed before the "machine-checkable" claim (07 §4) is relied on.

## B. Duplicate policy (05) — PASS

The per-purpose ratification is methodologically sound and matches the Stage-5 facts:

- Descriptive statistics keep all documents (RD-06; L2-03:31-33) — physical N is never silently reduced.
- Reference distributions use effective membership (L2-03:26-35); verified 0 non-canonical leakage, per-group rows == n_effective, 33,543 membership rows (independent_review_stage5.md §5; validator `test_reference_group_eligibility_real_artifacts`).
- Evaluation isolates duplicate groups (RD-10:37-42; L2-10:72-75; 240 holdout rows, all CANDIDATE).
- Model development is explicitly NOT settled (05 §4.4) — an honest open Researcher decision, not a silent extension.
- Fold facts are consistent: 240 affected documents / 120 groups × 2 / 120 canonical + 120 non-canonical, canonical = lexicographically smallest document_id, fold = `Path(member).stem` + last-wins (methodology_review.md D2 condition 1; independent_review_stage5.md §5; `test_fold_duplicates_matches_stage5_facts` passes). Logical N 4,830 = 4,950 − 120 is arithmetically consistent.

No conditions. The arbitrary-but-auditable canonical rule is adequately disclosed (05 §3).

## C. Reference-group eligibility (06) — PASS

- The min-N=30 classification as a general, feature-independent **descriptive floor** — explicitly not a validity/normative-sufficiency claim — is justified: it is artifact-enforced (all 75 groups n_effective ≥ 30, minimum exactly 30 at `RG-prompt_id=ARG01-timed_status=untimed`; complete-case min = 30; max n_missing = 2; methodology_review.md D4), with missingness never imputed (I4, ARCH-07:30), fragile entry-year groups 2003/2007 flagged LIMITED (RD-08), degenerate distributions flagged, and prompt imbalance documented (L2-06).
- Normative use remains blocked by D-07 (ARCH-14:68-75); feature-dependent floors and D11 frequency-resource features are deferred as future amendments (06 §2.5-2.6; ARCH-15:50). No statistical overreach: the floor carries no stability guarantee and the band method / normative min-N remain Researcher decisions (D4).

**LOW findings only:** F7 ("elevated missingness" undefined) and F8 ("descriptive-stability floor" wording implies an unestablished stability property).

## D. Evaluation protection (04) — PASS_WITH_CONDITIONS

The circularity rule (04 §6; EP-04/EP-05) correctly operationalizes the architecture prohibition (ARCH-07:45; ARCH-08:43) and the verified linkage facts (L2-03:9-24; methodology_review.md D1). The reference-distribution text-feature participation (04 §3/§5; 1,890 membership rows across 7 groups, methodology_review.md D3) is coherent with the score-signal rule: score fields are absent from distributions, membership, and query boundary (independent_review_stage5.md §6; EP-06), so the block's *scores* never construct the norms it would later be evaluated against.

**Conditions:**
- 04 §6's "construction source" is undefined (score-bearing vs feature-bearing). Because the block's text features participate in reference distributions, any future evaluation whose target signal consumes such a distribution has construction-source overlap with the block; the policy should state explicitly that such designs always route through the §6 declaration / Researcher-decision path (F5).
- 10 §2's risk row "using them as both reference and evaluation is circular" (RD-10:21-22) reads, literally, as contradicting 04 §3's ALLOWED text-feature participation. The two-stage review resolved this (scores as reference vs features as reference), but the wording should be harmonized (F5).

## E. Stage-6 admissibility (08) — PASS_WITH_CONDITIONS

- The required admissibility record is complete: corpus package/hash, FeatureSetVersion equality (I3), ReferenceGroupVersion, DistributionVersion (+algorithm), requested/resolved group with fallback disclosure (I4), effective N + n_raw, availability, reproducibility (no fallback analyzer), missingness without imputation, descriptive direction, L0 epistemic status (D-09), research_only exposure (D-08), 7-field provenance, no score fields (EP-06), banned-vocabulary-free (I1). The four statuses are internally consistent; UNAVAILABLE is terminal (no widening/substitution), INVALID covers prohibited use.
- The mandate is respected: no diagnostic algorithm, threshold, band method, or distance metric is defined (08 §6; D4 stays open, ARCH-15:43; 12 §3).

**Conditions:** the machine layer (`assess_admissibility`) does not yet enforce several table rows — score fields, full provenance, n_raw sanity, fallback-null consistency (F3, F6); clarify the UNAVAILABLE/INVALID precedence for version mismatch (F14).

## F. Leakage (10) + audit sampling (09) — PASS_WITH_CONDITIONS

- Leakage constraints are sound and consistent with RD-10:37-42: duplicate groups never split; same-prompt splits require a prompt-matching design; 270 block moves as one unit; unknown learner IDs acknowledged (no learner-level isolation claim); versioned, reproducible partition logic; domain scoping (D-19/D-36). The partition validator rejects split duplicate groups, split prompts without design, learner-isolation claims, and WARG2081 in raw/lemma sides (tests pass).
- Audit sampling is correctly separated from learner-outcome evaluation (ARCH-08:23-25), with a closed failure vocabulary that includes `leakage_or_domain_violation` and `unsupported_claim`, and evidence requirements that reference the existing human-review contract (`app/research/schemas.py:57-77,208-235`; `structured-feedback-v0.7.1` exists in `app/feedback/registry.py:83`).

**Conditions / gaps:**
- The prompt-matching design is reduced to a single boolean in the validator; policy 10 §3.2 requires the design to *record grouping and justification* — not enforced (F10).
- Unknown document ids in a partition plan are silently ignored; `side_types` defaults to "mixed", so a raw/lemma side containing WARG2081 without declared side types escapes detection (F10).
- Audit caps ("documented cap", on-demand "capped") are referenced but not specified anywhere; the interaction of the 100% HIGH-stratum override with the systematic 5% selection is undefined (F9).

## G. Validators — FAIL (contained to the department's own layer)

Direct execution confirms the machine checks diverge from the policy tables and from I1:

1. **The policy-mandated HISTORY_LIMITATION is rejected by the guardrail.** `contains_prohibited_claim` flags the verbatim disclaimer required by 07 §2.5 ("does not establish language-ability improvement, decline, mastery, or regression" → banned tokens `ability`, `mastery` + risky phrase `mastery`), even though I1 exempts "explicit prohibition text" (ARCH-07:27). The mandated longitudinal disclaimer cannot pass the current machine check (F1, HIGH).
2. **A canonical permitted template fails the guardrail.** 07 §2.3's permitted example "priority score P (workflow ranking only)" is rejected as banned token `score` (F2, HIGH).
3. **`assess_admissibility` admits records the 08 table marks INVALID/UNAVAILABLE:** score fields present in the record (08:36, EP-06) → ADMISSIBLE; 1-field provenance dict (08:35 requires the 7-field chain) → ADMISSIBLE; `n_raw=0` (08:28) → ADMISSIBLE; `fallback_disclosure=None` with `resolved != requested` (08:27: null only on exact match) → ADMISSIBLE (F3, HIGH).
4. **07 §4.3 promises `validate_claim_template(text, evidence_class)`; the implementation provides `validate_claim_text`, which only checks vocabulary and passes prohibited statements** such as "The learner is a good writer" (07 §2.1 prohibits it) and template-less "word count is X" (F4, MEDIUM).
5. Minor: the risky-phrase list extends the documented configuration contract without documentation, and substring matching false-positives negations such as "does not have advanced proficiency" (F12, LOW).

The validator tests pass only because they encode the implementation's own behavior; they do not test the policy's canonical templates or the 08 table rows listed above.

---

## Findings

| ID | Grade | Finding |
| --- | --- | --- |
| F1 | HIGH | Guardrail rejects the policy-mandated HISTORY_LIMITATION verbatim (07 §2.5 vs I1's "except explicit prohibition text", ARCH-07:27; `validators.py:55,222`). |
| F2 | HIGH | Canonical permitted template in 07 §2.3 ("priority score P") fails the banned-token check; doc/code contradiction in the claim policy's own machine layer. |
| F3 | HIGH | `assess_admissibility` (validators.py:531) returns ADMISSIBLE for score-field records, partial provenance, `n_raw=0`, and fallback-null-with-mismatch — all INVALID/UNAVAILABLE per 08:27-28,35-36. |
| F4 | MEDIUM | 07 §4.3 promises `validate_claim_template`; implementation `validate_claim_text` (validators.py:234) does not validate templates and passes prohibited semantic claims (e.g., "The learner is a good writer"). |
| F5 | MEDIUM | 04 §6 "construction source" undefined (score-bearing vs feature-bearing); 10 §2 / RD-10:21-22 "reference and evaluation is circular" wording clashes with 04 §3 text-feature participation (1,890 rows, methodology_review.md D3). |
| F6 | MEDIUM | Admissibility validator does not check resolved-group membership in the approved set / distribution-record existence beyond an ARG13/ARG19 substring, nor `n_raw >= n_effective >= n_missing` consistency. |
| F7 | LOW | 06 §3 LIMITED criterion "feature-specific missingness is elevated" has no operational threshold. |
| F8 | LOW | 06 §2 "conservative descriptive-stability floor" implies an empirical stability property not demonstrated; recommend heuristic-floor wording (normative use already gated by D4/D-07). |
| F9 | LOW | 09 §3-4: "documented cap" / "capped" unspecified; 100% HIGH-stratum override vs 5% systematic selection combination undefined. |
| F10 | LOW | 10 §4 validator: `prompt_matching_design` boolean not tied to recorded grouping/justification; unknown plan document ids ignored; `side_types` default "mixed" can hide WARG2081 in raw/lemma sides. |
| F11 | LOW | 02 §3 registry table lists `evaluation-policy-versioning-v0.1.0` (RD-POL-002) but `policy_registry.json` contains only the 8 artifact policies; clarify scope or add the framework entry. |
| F12 | LOW | `RISKY_ABILITY_PHRASES` extends the documented configuration contract (schemas.py:73-77) with undocumented phrases; negation false positives ("does not have advanced proficiency"). |
| F13 | LOW | 11 §5-6 references `handoffs/methodology_review.md` as already recorded; the file did not exist before this review — the "AMBER/RED resolved before WU gates closed" claim is now verifiable only via this report. |
| F14 | LOW | 08 §3: version-mismatch appears in both UNAVAILABLE (record-level) and INVALID (comparison-level); clarify precedence. |

No BLOCKING findings. No Stage-5 fact, Corpus artifact, or other-department contract is affected; all conditions are contained to the department's own documents and `app/research/governance/**`.

---

## Final verdict: READY_WITH_CONDITIONS

The foundation's substantive policies (03-10) are methodologically sound, evidence-traceable, within the charter authority (ARCH-10:127-152), and consistent with the Stage-5 facts and the architecture invariants. The claim that the machine layer enforces the policies is not yet true: the guardrails contradict I1 and the policy's own mandated text and canonical templates (F1/F2), and the admissibility validator does not enforce several 08 table rows (F3); the template validator promised in 07 §4.3 does not exist as documented (F4).

Conditions to close before (a) the claim policy's machine-checkability is asserted, and (b) the WU11 utilities are used as a Stage-6 gate:
1. Add an explicit-prohibition-text exception to the banned-vocabulary guardrail so the mandated HISTORY_LIMITATION passes (F1); resolve the "priority score" template conflict (F2) — either an I1-consistent exception for frozen product wording or template rewording with Feedback & Learner Intelligence.
2. Implement `validate_claim_template` semantics or correct 07 §4.3 to describe the vocabulary-only check (F4).
3. Extend `assess_admissibility` to enforce 08's score-field, 7-field provenance, n_raw sanity, and fallback/resolved-consistency rows (F3/F6).
4. Define "construction source" in 04 §6 and harmonize the reference/evaluation wording across 04 and 10 (F5).
5. Close the LOW items F7-F14 opportunistically; none block integration.

**Department GREEN is endorsed as a foundation-scope claim; Integration GREEN remains subject to 12_INTEGRATION_HANDOFF.md's cross-department verification.**
