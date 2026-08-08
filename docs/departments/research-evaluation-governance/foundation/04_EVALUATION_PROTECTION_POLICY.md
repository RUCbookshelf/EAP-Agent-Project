# 04 — Evaluation Protection Policy

**Department:** Research Evaluation & Data Governance
**Policy id:** `evaluation-protection-policy-v0.1.0`
**Ratification:** RD-POL-004 (2026-08-07)
**Status:** RATIFIED
**Supersedes:** none (first canonical version; formalizes the Stage-5 protection proposal, L2-03:40-41, and the readiness constraint, RD-10:37-42)

## 1. Protected block

The protected evaluation block is the set of **270 scored expository texts**
(document ids `WEXP####`) from SWECCL 2.0 / WECCL 2.0, with human rater scores linked
deterministically via `TOOLS/exp.xls` and `TOOLS/exp.sav` (270×8; `ID, Rater_A, Rater_B,
Rater_C, Language, Content, Organization, Average_score`; linkage 270/270 set equality
with the EXP01 manifest subset — L2-03:9-24; methodology review D1 APPROVED).

## 2. Reproducible protection keys

| Key | Value | Evidence |
| --- | --- | --- |
| Document id set | 270 unique `WEXP####` ids (0 duplicates, 0 missing) | L2-03:10-14; methodology review D1 |
| exp.xls SHA-256 | `FF2BFB95D4FE6515AF6F7ABDC53C931C59787179EE50BFC7451C138F3D4B2D4C` (computed 2026-08-07, read-only) | physical file `A:\[Linguistics Data] Corpus\SWECCL 2.0\TOOLS\exp.xls` |
| exp.sav SHA-256 | `A7EB8B0A2C890CA1A078880C395E3C4AA58278E9607D4C51D8553866103BC6B0` (computed 2026-08-07, read-only) | physical file `A:\[Linguistics Data] Corpus\SWECCL 2.0\TOOLS\exp.sav` |
| Corpus package / manifest hash | `sweccl2-weccl20-v0.1.0` / `0d8940ff84613807c11c0e492c61fb8d39fc1152a386061f9711a41487659eb9` | L2-01; corpus_version.json |
| Holdout candidate rows | 270 of the 511 `holdout_candidates.csv` rows (reason: "270 texts with rater scores - high-value evaluation candidate"), all `protection_status=CANDIDATE` | RD-10; independent review §7 |
| Text-feature reference participation | 1,890 membership rows across 7 reference groups (EXP01, EXP01+timed, genre=expository, timed, grade=3, major_type=english_major, entry_year=2006) — text identity only, no score values | `reference_group_membership.csv` (verified 2026-08-07); methodology review D3 |

## 3. What the block may be used for (`ALLOWED`)

| Use | Constraint | Evidence |
| --- | --- | --- |
| Evaluation / validation design of the target signal (scores as outcome or criterion evidence) | The evaluation design must declare target signal, construction source, and evaluation source (section 6). | L2-03:9-24 (linkage established for evaluation readiness); L2-10:92-94 (WU-E recommended) |
| Score-linkage verification and audit | Read-only; no distribution/score mutation. | methodology review D1 |
| Text-feature participation in descriptive reference distributions | `learner_exposure=research_only`; statistics only; no score fields; duplicate policy applied. | L2-06; methodology review D3 (non-blocking note) |
| Aggregate internal descriptive statistics (no raw text, no scores in derived artifacts) | RD-11 permitted local analysis. | RD-11:43-48 |
| Holdout/leakage design work (partition planning, not execution) | Partitions remain versioned, reproducible, leak-safe (WU10); no irreversible final partition in this goal. | RD-10:37-42 |

## 4. What the block must NOT be used for (`PROHIBITED` / `REQUIRES_REVIEW`)

| Use | State | Evidence |
| --- | --- | --- |
| Using the same scored block both to construct the target signal and to evaluate that signal (circular evaluation) | `PROHIBITED` (conservative default rule) | ARCH-07:45 (circularity prohibition); ARCH-08:43 |
| Using the scores to build reference norms for a measure that is later validated against these same scores | `PROHIBITED` | ARCH-07:45; methodology review D1/D3 |
| Including any score field (Rater_*, Language/Content/Organization, Average_score) in reference distributions, membership artifacts, or the query boundary | `PROHIBITED` | L2-03:23-24; L2-06 (statistics only); independent review §6 (0 score references in app/corpus) |
| Splitting the block (partial use across dev/eval boundaries) | `PROHIBITED` | RD-10:37-42; L2-03:40-41; L2-10:72-75 |
| Using the block as development material without Research Evaluation approval | `PROHIBITED` | L2-03:40-41 |
| Learner-facing raw display of these texts | `REQUIRES_REVIEW` (D-08 default disabled) | ARCH-14:77-84; CU-05 |
| Model training / fine-tuning on these texts | `REQUIRES_REVIEW` (with recorded legal basis) | CU-07 |
| Public release of texts or scores | `REQUIRES_REVIEW` | CU-08 |

## 5. Reference-distribution participation and validation reservation

- **Reference-distribution participation:** permitted for text features (observed
  descriptive evidence, research_only, no scores) — this is the current Stage-5
  practice and was explicitly reviewed (methodology review D3). It does **not** make
  the block "development material": the block's score signal is never used to build
  the feature norms it would later be evaluated against.
- **Validation reservation:** the block is reserved as the platform's first scored
  evaluation/validation resource. A final irreversible train/dev/test partition is
  **not** required by this policy and is **not** created; any future partition must be
  scientifically justified, versioned, reproducible from the protection keys, and
  leak-safe under 10_EVALUATION_LEAKAGE_POLICY.md.

## 6. Circular-evaluation prevention

Conservative rule (default, binding):

```text
Do not use the same scored block both to construct the target signal and to evaluate that signal.
```

Definitions (F5 resolution):

- **Target signal** — what is being measured/evaluated (e.g., a feature, score, or
  model output).
- **Construction source** — the data used to build, estimate, or calibrate the target
  signal (norms, features, thresholds, models, reference distributions).
- **Evaluation source** — the data providing the criterion/outcome against which the
  target signal is assessed (e.g., the 270 human scores).

Operational requirements for any evaluation design that touches the block:

1. Declare the **target signal**, the **construction source**, and the **evaluation
   source**.
2. Prove `construction source ∩ block = ∅` when the block is the evaluation source
   (and vice versa), or obtain an explicit Researcher decision with justification and
   a methodological review.
3. Because the block's **text features** participate in reference distributions
   (04 §3), any design whose construction source consumes one of those distributions
   has construction-source overlap with the block and **always routes through this
   declaration / Researcher-decision path** — the score signal is never used to
   construct the norms it would later be evaluated against.
4. Record the declaration in the evaluation design artifact (versioned, WU8-gated for
   Stage 6).

Machine check (WU11): distribution artifacts contain no score fields; membership
artifacts carry no score columns; `app/corpus` data and docs contain no score-bearing
reference records.

## 7. Change control

Any change to sections 3/4 (permitted/prohibited uses) is a **major** version change of
this policy (02 §2), requires methodological review, and — if it touches partitions,
shared contracts, or the query boundary — Architecture & Integration review (ARCH-13 §1).
No change may be made silently by engineering.

## 8. Machine artifact

`policies/evaluation_protection_policy.json` mirrors sections 3-4 and validates against
`policies/policy_schema.json` (WU11).