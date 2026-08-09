# CORPUS-MINN-EVIDENCE — Reference-Group min-N / Exclusion / Duplicate Evidence Report

Goal: `CORPUS-MINN-EVIDENCE` (evidence-only; does NOT ratify Researcher
decisions). Owner: CORPUS. Baseline: promoted master `09264abbd93cdc6b62b83cefd94b3b640319ac9b`
(Stage-6 WU-A/B/C/E freeze commit), branch `dept/corpus`, worktree
`A:\EAP Agent Project\worktrees\corpus`. Date: 2026-08-09.

This report computes the empirical reference-group size distribution,
sparsity, fallback frequency, duplicate-handling sensitivity, exclusion-rule
sensitivity, implications of the current min-N=30, and the availability and
uncertainty impact of alternative thresholds (20/40/50, plus granular
values). It ends with a Researcher recommendation that carries no
ratification authority.

---

## 1. Inputs and method

Computed exclusively from governed artifacts at the promoted baseline:

| Artifact | Role |
| --- | --- |
| `docs/corpus-readiness/sweccl2/data/corpus_manifest.csv` | 4,950-row manifest (document attributes; prompt/timed/genre/major/grade/year) |
| `docs/corpus-readiness/sweccl2/data/duplicate_report.csv` | 348 duplicate-group rows (4 scopes, last-wins doc-level fold) |
| `docs/corpus-intelligence/l2/data/reference_group_membership.csv` | shipped effective membership, 75 approved groups, 33,543 rows |
| `docs/corpus-intelligence/l2/data/reference_distributions.jsonl` | 1,050 distribution records (75 groups x 14 features) |
| `docs/corpus-intelligence/l2/data/reference_group_version.json` | min-N=30, fallback hierarchy, duplicate policy |
| `docs/corpus-intelligence/l2/04/06/07` and Stage-6 docs 10-16 | policy, distribution, boundary, verification context |
| `SWECCL2.0_语料库概况报告.md` + RAW directory listing (raw SWECCL, metadata inspection only) | physical counts cross-check (4,950 files; 26 ARG + 1 EXP prompts) |

Method: the candidate-group census, duplicate fold, and fallback resolution
were re-implemented to mirror `app/corpus/groups.py`
(`ReferenceGroupIndex`) exactly, then **cross-validated against the shipped
artifacts**: the reconstructed approved set (75 groups), per-group
`n_raw`/`n_effective`, and membership counts match the membership CSV and
the distribution JSONL on every group (asserted in the analysis script).
Statistics (mean/std/quantiles) are taken from the shipped JSONL, not
re-derived. No raw SWECCL text was read; no files were mutated outside
`docs/corpus-intelligence/l2/evidence/` in the worktree.

Limits:
- Snapshot scope: v0.1.0 artifacts at `09264ab`; the per-document feature
  snapshots outside git were not re-read; below-threshold candidate groups
  are reconstructed from the manifest + duplicate report, not from a shipped
  "all-candidates" artifact (the shipped CSV/JSONL contain only the 75
  approved groups).
- Uncertainty proxies are descriptive (SE of mean = std/sqrt(n), percentile
  rank step = 100/n). No normative sufficiency or power claim is made.
- Three of 54 prompt x timed signatures are structurally empty (zero
  documents exist: ARG13-timed, ARG26-untimed, EXP01-untimed); the matcher
  still resolves them via fallback.

## 2. Reference-group size distribution

Effective universe: **4,830 documents** (4,950 physical minus 120
non-canonical duplicate members). Candidate space: **96 groups** (27 prompt,
54 prompt x timed, 2 genre, 2 timed, 2 major type, 4 grade, 5 entry year);
**75 approved** (all with effective N >= 30).

Effective-size distribution of the 75 approved groups:

| Band (n_effective) | Groups | Share |
| --- | --- | --- |
| 30-39 | 4 | 5.3% |
| 40-49 | 4 | 5.3% |
| 50-99 | 16 | 21.3% |
| 100-249 | 27 | 36.0% |
| 250-499 | 14 | 18.7% |
| >= 500 | 10 | 13.3% |

Approved groups: min 30 (ARG01-untimed), p25 87, median 145, p75 307,
max 4,560 (argumentative). Per-type medians: prompt 152 (range 14-555),
prompt x timed 64 (range 0-419), genre 2,415, timed 2,415, major type 2,415,
grade 1,277, entry year 453.

Largest prompt groups (effective): ARG17 555 (656 raw), ARG02 425, ARG26
419, ARG23 379, EXP01 270 (the full expository block). **Fragile tail
(30 <= n < 50): 8 groups (10.7% of approved)** — ARG01-untimed 30, ARG20 32,
ARG18-untimed 33, ARG16-untimed 39, ARG05-timed 41, ARG18 43,
ARG03-untimed 43, ARG03-timed 44.

## 3. Sparsity

- **21 of 96 candidates** fall below min-N=30 (6 prompt x timed groups in
  20-29: ARG22-timed 29, ARG16-timed 27, ARG20-untimed 27, ARG12-timed 26,
  ARG14-timed 24, ARG15-timed 22; ARG13 14, ARG19 18; 13 prompt x timed
  groups with <= 17 docs, 10 of them with <= 10 docs, including 3 with zero
  docs).
- ARG13 (14) and ARG19 (18) are below every threshold >= 20; their documents
  still participate in genre/timed/year/grade/major groups.
- Feature-level missingness: **100 of 1,050 records (9.5%) carry
  `n_missing > 0`** ("missing values: N of M", never imputed). Two documents
  cause all of it: WARG2081 (corrupt RAW; all 14 features; ARG23-untimed)
  and WARG0228 (t_unit_proxy only; ARG24-untimed). Nine groups are affected
  (ARG23, ARG23-untimed, ARG24, ARG24-untimed, argumentative, untimed,
  2006, grade 1, english_major); t_unit_proxy in 9 groups, the other 13
  features in 7 groups each. No group-level availability loss and no
  degenerate distributions (0 records with std==0 or IQR==0).

## 4. Fallback frequency

Hierarchy declared in `reference_group_version.json`:
prompt+timed -> prompt -> genre+timed -> genre -> UNAVAILABLE.

Resolution over all **54 prompt x timed signatures** (27 prompts x 2 timed
values):

| Outcome | Signatures | Share |
| --- | --- | --- |
| Exact (prompt x timed) | 35 | 64.8% |
| Prompt fallback | 15 | 27.8% |
| Genre fallback | 4 | 7.4% |
| Unavailable | 0 | 0.0% |

At prompt-only granularity (27 prompts): 25 exact, 2 genre-fallback
(ARG13, ARG19). Genre fallback therefore accounts for only 4 of 54
signatures (7.4%) and never yields UNAVAILABLE, because the two genre groups
are the deepest resolvable level.

**Structural finding:** the `genre+timed` hierarchy step is **dead in
v0.1.0** — the index defines no genre x timed candidate groups (0 of 96),
so that step can never resolve; the effective hierarchy is
prompt+timed -> prompt -> genre. Consistent with WU-B smoke evidence
(doc 16: ARG13 -> `RG-genre=argumentative`, disclosed fallback).

## 5. Sensitivity to duplicate handling

- Fold facts: 348 duplicate-report rows (raw bytes / raw text / lemma bytes /
  tagged bytes) -> last-wins document-level fold -> **120 duplicate groups,
  240 affected documents, 120 canonical + 120 non-canonical**; effective
  universe 4,950 -> 4,830 (-2.4%).
- Per-group exclusions concentrate in five prompts: ARG17 -101 (all timed),
  ARG23 -12 (all timed), ARG21 -5 (all timed), ARG02 -1 (untimed), ARG04 -1
  (untimed); total 120.
- **Availability frontier is insensitive to the duplicate policy**: at every
  threshold 10-100, the number of groups passing on raw counts equals the
  number passing on effective counts (e.g., 75 = 75 at min-N=30); no group
  is in the "limited" state (n_raw >= 30 > n_effective). The policy only
  shrinks N and thus narrows uncertainty.
- Strict counterfactual (exclude **all** 240 duplicate-touched documents,
  not just the 120 non-canonical): still 75 groups >= 30; no approved group
  drops below 30. The approved set is robust even to the strictest plausible
  duplicate exclusion.
- Duplicate policy remains consequential for statistics (per-group N),
  partitioning (duplicate-group members never split; WU-E) and leakage
  control — just not for which groups exist.

## 6. Sensitivity to exclusion rules

| Rule | Documents affected | Availability impact |
| --- | --- | --- |
| Non-canonical duplicate exclusion | -120 (2.4%) | none at any threshold 10-100 |
| Sparse-prompt exclusion (ARG13/ARG19) | -32 from prompt granularity | unavailable at every threshold >= 20; still inside broader groups |
| Corrupt-doc exclusion (WARG2081) | -1 x 14 features | n_missing in 7 groups; no group-level loss |
| t_unit_proxy exclusion (WARG0228) | -1 x 1 feature | n_missing in 9 groups; no group-level loss |
| TEM8 absence | 0 WECCL documents | none (outside WECCL scope) |

No exclusion rule currently changes the approved set; rules affect
per-group N and record-level missingness only.

## 7. Implications of min-N=30 and alternative thresholds

Availability curve (candidate groups with effective N >= t):

| min-N | 10 | 15 | 20 | 25 | **30** | 35 | 40 | 45 | 50 | 60 | 75 | 100 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Groups | 87 | 84 | 81 | 79 | **75** | 72 | 71 | 67 | 67 | 67 | 60 | 51 |

- Lowering to 20 gains **6 prompt x timed groups** (ARG22-timed 29,
  ARG16-timed 27, ARG20-untimed 27, ARG12-timed 26, ARG14-timed 24,
  ARG15-timed 22); ARG13/ARG19 remain unavailable. Percentile rank step in
  those groups is 3.4-4.6% (median 3.8%) - worse than every approved
  prompt x timed group except the four in the 30-39 band; their SE(mean) is
  not directly computable from governed aggregates because no distribution
  records exist for unapproved groups.
- Raising to 40 loses 4 groups (ARG01-untimed 30, ARG16-untimed 39,
  ARG18-untimed 33, ARG20 32; -5.3% of approved); raising to 50 loses 8
  (adds ARG03-timed/untimed 44/43, ARG05-timed 41, ARG18 43; -10.7%).
  The 35-45 range is where prompt x timed coverage of ARG01/03/05/16/18/20
  degrades fastest.
- min-N=30 mainly binds the **prompt x timed granularity**: prompt-level
  coverage would survive thresholds up to ~50 (only ARG13/19/20 + ARG18 are
  below 50 at prompt level).

Uncertainty impact (median over 14 features per band; SE of mean and
percentile rank step):

| Band | Median n | Median SE(mean) | Median percentile step |
| --- | --- | --- | --- |
| 30-39 | 32 | 0.0036 | 3.078% |
| 40-49 | 43 | 0.0031 | 2.326% |
| 50-99 | 80 | 0.0025 | 1.258% |
| 100-249 | 145 | 0.0019 | 0.690% |
| 250-499 | 343 | 0.0013 | 0.295% |
| >= 500 | 2,251 | 0.0006 | 0.045% |

Across the whole candidate set the median SE(mean) is flat (~0.002) at
min-N 20/30/40/50 and median percentile step moves only 0.690% -> 0.658%,
because most records sit in large groups. The threshold decision therefore
affects the **tail, not the center**: groups at 30-49 (8 of 75 approved)
carry percentile steps of 2.3-3.1% and SE(mean) roughly 6x the >= 500 band.

WU-E relevance: the protected block (270 expository texts) maps exactly to
EXP01 / EXP01-timed (n=270, zero missingness in EXP01 records) and is
unaffected by any threshold <= 270; min-N does not constrain the
document-level evaluation design.

## 8. Researcher recommendation (no ratification)

1. **Keep min-N = 30 as the availability gate.** It retains all prompt-level
   groups except ARG13/ARG19, preserves 35 of 54 prompt x timed groups, and
   sits in a flat part of the availability curve: 20 gains only 6 small
   groups with materially worse percentile resolution; 40/50 remove prompt x
   timed coverage for ARG01/03/05/16/18/20 without improving the mass of
   large groups.
2. **Add a "fragile" annotation for 30 <= n < 50** (8 groups, 10.7% of
   approved): recommend reporting n_effective on every result (already in
   the query contract) and treating percentile/SE evidence in this band as
   descriptive with an explicit caution; do not attach normative sufficiency
   meaning to 30 (policy doc 04 already disclaims this).
3. **Fix or document the dead `genre+timed` hierarchy step**: no genre x
   timed groups exist in v0.1.0, so the declared hierarchy is effectively
   prompt+timed -> prompt -> genre. Either build genre x timed groups in a
   future version or trim the published hierarchy.
4. **Duplicate policy: unchanged.** It does not affect availability at any
   threshold 10-100 and the strict 240-doc exclusion counterfactual leaves
   the approved set identical; keep canonical-only effective samples for
   statistics and never split duplicate groups across dev/eval.
5. **Uncertainty reporting:** consider carrying a per-record uncertainty
   hint (SE(mean) or percentile step) in the distribution contract, or a
   warning flag for n_effective < 50, in a future version. Current records
   carry only missingness flags.

None of the above is a ratification; ratification belongs to Research
Evaluation/Researcher decisions.

## 9. Evidence inventory and reproduction

Companion artifacts in `docs/corpus-intelligence/l2/evidence/`:

- `minn_evidence_analysis.py` — the analysis script (stdlib only), mirroring
  `app/corpus/groups.py` semantics with cross-validation asserts.
- `minn_group_census.csv` — 96 candidate groups (n_raw, n_effective,
  excluded, availability, criteria).
- `minn_threshold_sweep.csv` — availability at min-N in {10..100} under
  effective, raw, and current-approved policies.
- `minn_fallback_resolution.csv` — all 54 prompt x timed resolutions with
  requested/resolved groups and outcome.
- `minn_uncertainty_summary.csv` — per-band SE(mean) and percentile step.

Reproduce:

~~~powershell
& 'A:\EAP Agent Project\worktrees\shared-core-environment\.venv\Scripts\python.exe' `
  docs\corpus-intelligence\l2\evidence\minn_evidence_analysis.py
~~~

Run from `worktrees\corpus` at `09264ab`; the script asserts its
reconstruction against the governed artifacts and fails on any mismatch.
