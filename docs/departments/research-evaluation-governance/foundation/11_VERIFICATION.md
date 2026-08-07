# 11 — Verification

**Department:** Research Evaluation & Data Governance
**Package:** `research-governance-foundation-v0.1.0`
**Date:** 2026-08-07
**Status:** VERIFIED (WU11 GREEN) — see environment note in section 5.

## 1. What was verified

1. **Policy artifacts (WU2/WU11):** all 8 policy JSON artifacts validate against
   `policies/policy_schema.json` (schema, consistency: policy_version == policy_id +
   version; status ratified; statement structure; evidence non-empty).
2. **Policy registry (WU2):** `policy_registry.json` entries match artifact bytes
   (SHA-256), policy ids, versions, and ratified status.
3. **Reference-group eligibility (WU6):** 75 approved groups; 1,050 distribution
   records; n_effective == membership rows per group; n_effective >= 30 and
   complete-case N >= 30 for every record (observed minimum 30); no ARG13/ARG19
   standalone group in approved sets; non-canonical duplicate members do not leak
   into reference membership (fold verified: 240 affected documents / 120 groups /
   120 canonical / 120 non-canonical).
4. **Evaluation protection (WU4):** holdout candidates total 511 = 270 scored +
   240 duplicate-group members + 1 corrupt variant; all CANDIDATE; no overlap
   between the scored block and duplicate members; no score-like fields in
   distribution records; membership header unchanged.
5. **Version provenance (WU8):** all 1,050 distribution records carry the 7-field
   provenance chain consistent with the registered corpus package and versions.
6. **Measurement-claim guardrails (WU7):** banned-token and risky-phrase checks
   behave as specified (word-boundary tokens; substring false positives excluded;
   longitudinal claim phrases detected).
7. **Audit sampler (WU9):** deterministic hash-based selection; identical reruns
   produce identical samples; rate bounds hold; seed changes the sample.
8. **Stage-6 admissibility (WU8):** ADMISSIBLE / LIMITED / UNAVAILABLE / INVALID
   determination exercised across representative records (exact match, fallback,
   version mismatch, ARG13, prohibited wording, low N, missing fields).
9. **Duplicate-group leakage (WU10):** partition-plan validator rejects split
   duplicate groups, split prompts without prompt-matching design, learner-isolation
   claims, and WARG2081 in raw/lemma sides; accepts intact plans.

## 2. Test results

| Suite | Command | Result |
| --- | --- | --- |
| Governance validators (this foundation) | `pytest tests/test_research_governance_v01.py` (28 tests, incl. review-fix coverage F1-F14) | **28 passed / 0 failed** (Python 3.12.13, pytest 9.1.1) |
| Corpus Stage-5 focused suite (regression evidence, unchanged) | `pytest tests/corpus` | 36/36 passed (Stage-5 record, L2-09; unchanged by this goal) |
| Full non-live core (regression authority) | canonical environment | see section 5 |

## 3. Artifact-level evidence

- 8 policy JSON artifacts + schema + registry under `policies/`; registry records the
  SHA-256 of every artifact (computed 2026-08-07; re-verified by the registry validator).
- Data facts verified against real artifacts: `reference_group_membership.csv`
  (33,543 rows), `reference_distributions.jsonl` (1,050 records),
  `duplicate_report.csv` (348 scope groups), `holdout_candidates.csv` (511 rows),
  `corpus_manifest.csv` (4,950 rows), `corpus_version.json`.
- Protection keys: exp.xls SHA-256 `FF2BFB95…2D4C`; exp.sav SHA-256 `A7EB8B0A…BC6B0`
  (read-only, computed 2026-08-07).

## 4. What was NOT changed

- No Corpus implementation or data artifact modified (`app/corpus/**`,
  `docs/corpus-intelligence/**`, `docs/corpus-readiness/**` untouched).
- No product code outside `app/research/governance/` touched; no migration; no
  configuration/prompt changes; `run.bat` unchanged (no runtime-affecting change,
  AGENTS.md runtime-sync rule not triggered); no existing test modified.

## 5. Environment note and limitations

- The canonical project environment (Python 3.11 + requirements.txt) could not be
  recreated in this worktree during verification: the main-repo `.venv` base
  interpreter is missing on this machine, no `py` launcher is installed, and two
  attempts to build a fresh verification environment failed on network read timeouts
  for the large pinned wheels (spacy 3.8.7 ~14 MB; en_core_web_sm 3.8.0 ~13 MB from
  GitHub; pypi reachable, downloads time out). This is an environment limitation, not
  a code issue.
- Validators were therefore executed in the Stage-5 corpus venv (Python 3.12.13,
  pytest 9.1.1) with `--noconftest` (the governance test module imports only the
  standard library; conftest requires the full app environment). All 28 tests pass.
- Additional regression evidence: the unchanged Corpus Stage-5 focused suite
  `pytest tests/corpus --confcutdir=tests/corpus` was rerun in the same venv with an
  isolated scratch basetemp — **36/36 passed** (matches the Stage-5 record, L2-09;
  no corpus code or artifact was touched by this goal).
- The full non-live core (1,237-test authority) remains unrun in this worktree and is
  listed in 12_INTEGRATION_HANDOFF.md §9 as a test Architecture & Integration must run
  at milestone verification. The foundation adds imports only under
  `app/research/governance/**`; collection-time compatibility was exercised by the
  governance suite, but the full-core run must confirm the rest.
- FastAPI/Streamlit/`run.bat` verification was not rerun: this goal introduces no
  runtime, dependency, entry-point, environment-variable, migration, or port change.
- Independent methodology review of the policy set is recorded in
  `handoffs/methodology_review.md` (fresh reviewer) — see section 6.

## 6. Independent review

- The research-governance foundation (policies 03-10, validators, tests) was reviewed
  by a fresh deepseek-v4-flash reviewer instance (independent, not an implementer).
  Verdict: **READY_WITH_CONDITIONS**; 14 findings (F1-F14; 3 HIGH, 2 MEDIUM, 9 LOW),
  all contained to this department's documents and `app/research/governance/**`. Full
  record: `evidence/methodology_review.md` (committed; copy in
  `.agent-workflow/research-evaluation-governance-foundation/handoffs/`).

### Review-finding dispositions (F1-F14)

| ID | Grade | Resolution |
| --- | --- | --- |
| F1 | HIGH | Explicit-prohibition-text exception implemented (`validate_disclaimer_text`; `contains_prohibited_claim(prohibition_exempt=True)`); mandated HISTORY_LIMITATION now passes the machine check. |
| F2 | HIGH | Frozen product term "priority score" exempted from the banned-token check (documented in 07 §4.1); the canonical §2.3 template passes. |
| F3 | HIGH | `assess_admissibility` now enforces 08 rows: score fields → INVALID; 7-field provenance required → UNAVAILABLE; n_raw sanity; fallback-null-with-mismatch → INVALID. |
| F4 | MEDIUM | `validate_claim_template(text, evidence_class)` implemented (class anchors + learner-quality assertion patterns); "The learner is a good writer" now fails. |
| F5 | MEDIUM | 04 §6 defines target/construction/evaluation source and the feature-bearing distribution overlap path; 10 §2 wording harmonized with 04 §3. |
| F6 | MEDIUM | Admissibility check now validates approved-set membership, distribution-record existence, n_effective agreement with the distribution record, and n_raw consistency. |
| F7 | LOW | "Elevated missingness" operationalized (n_missing >= 2 or ratio >= 0.05) in 06 §3. |
| F8 | LOW | 06 §2 reworded to "conservative descriptive heuristic floor"; no stability property claimed. |
| F9 | LOW | 09 §4 defines caps (50/batch systematic, 20/event on-demand) and the stratum-union rule (`apply_stratum_sampling`). |
| F10 | LOW | 10 §4 validator requires `prompt_matching_design_reason`, rejects unknown document ids, and requires explicit `side_type=tagged` for WARG2081. |
| F11 | LOW | `policy_registry.json` now lists the `evaluation-policy-versioning` framework entry (RD-POL-002; artifact null). |
| F12 | LOW | Risky-phrase additions documented in 07 §4.2; negation handled only via the explicit-prohibition path (documented limitation). |
| F13 | LOW | Review record committed at `evidence/methodology_review.md`; 11/12 references updated. |
| F14 | LOW | 08 §3 documents INVALID → UNAVAILABLE → LIMITED precedence; machine check implements it. |

All conditions closed before WU gates; no BLOCKING finding; no Stage-5 fact or other
department contract affected.

## 7. Gate result

All WU11 acceptance criteria are satisfied; validators/tests pass; no other
department contract was changed; Stage-5 facts remain traceable.

> **WU11 GREEN — RESEARCH EVALUATION & DATA GOVERNANCE FOUNDATION DEPARTMENT GREEN — READY FOR INTEGRATION** (not Integration GREEN; Architecture & Integration must run the tests listed in 12 before any milestone claim).