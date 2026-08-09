"""CORPUS-MINN-EVIDENCE analysis script.

Evidence-only companion for
docs/corpus-intelligence/l2/evidence/CORPUS-MINN-EVIDENCE-20260809.md

Reads governed artifacts ONLY (promoted baseline 09264ab):
  - docs/corpus-readiness/sweccl2/data/corpus_manifest.csv      (4,950 rows)
  - docs/corpus-readiness/sweccl2/data/duplicate_report.csv      (348 rows)
  - docs/corpus-intelligence/l2/data/reference_group_membership.csv
  - docs/corpus-intelligence/l2/data/reference_distributions.jsonl (1,050)
  - docs/corpus-intelligence/l2/data/reference_group_version.json

The group index logic mirrors app/corpus/groups.py (ReferenceGroupIndex) so
the census, duplicate fold, and fallback resolution are identical to the
product implementation. Cross-validation asserts the reconstruction against
the shipped membership CSV and distribution JSONL.

No raw SWECCL content is read; no files outside docs/ are written.
Outputs (this directory):
  minn_group_census.csv         96 candidate groups (n_raw/n_effective/...)
  minn_threshold_sweep.csv      availability at alternative min-N thresholds
  minn_fallback_resolution.csv  54 prompt x timed signature resolutions
  minn_uncertainty_summary.csv  SE-of-mean / percentile-step per size band
"""

from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
READINESS_DATA = REPO / "docs" / "corpus-readiness" / "sweccl2" / "data"
INTEL_DATA = REPO / "docs" / "corpus-intelligence" / "l2" / "data"
OUT = Path(__file__).resolve().parent

MIN_N = 30
THRESHOLDS = [10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 75, 100]
FEATURES = (
    ["text_length_tokens", "sentence_length_mean", "t_unit_proxy", "connective_density"]
    + [f"pos_share_{c}" for c in (
        "noun", "verb", "adjective", "adverb", "pronoun",
        "determiner", "preposition", "conjunction", "numeral", "other")]
)


def load_manifest() -> list[dict]:
    with open(READINESS_DATA / "corpus_manifest.csv", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_duplicates() -> dict[str, str]:
    """Mirror app/corpus/groups.py::_load_duplicate_members (last-wins fold)."""
    members: dict[str, str] = {}
    with open(READINESS_DATA / "duplicate_report.csv", encoding="utf-8-sig", newline="") as f:
        for i, row in enumerate(csv.DictReader(f), start=1):
            gid = f"DUP-{i:03d}"
            for member in row["members"].split(","):
                members[Path(member).stem] = gid
    return members


def gid_of(criteria: dict[str, str]) -> str:
    return "RG-" + "-".join(f"{k}={v}" for k, v in sorted(criteria.items()))


def build_census(manifest: list[dict], duplicates: dict[str, str], min_n: int = MIN_N) -> dict:
    canonical: dict[str, str] = {}
    for doc, group in duplicates.items():
        if group not in canonical or doc < canonical[group]:
            canonical[group] = doc

    def members(criteria: dict[str, str]) -> list[dict]:
        return [r for r in manifest if all(r.get(k) == v for k, v in criteria.items())]

    def effective(rows: list[dict]) -> tuple[int, list[str]]:
        keep: list[str] = []
        for row in rows:
            doc = row["document_id"]
            group = duplicates.get(doc)
            if group is None or doc == canonical[group]:
                keep.append(doc)
        return len(keep), keep

    candidates: list[tuple[dict, str]] = []
    prompts = sorted({r["prompt_id"] for r in manifest})
    for prompt in prompts:
        candidates.append(({"prompt_id": prompt}, "prompt"))
    for genre in ("argumentative", "expository"):
        candidates.append(({"genre": genre}, "genre"))
    for timed in ("timed", "untimed"):
        candidates.append(({"timed_status": timed}, "timed"))
    for major in ("english_major", "non_english_major"):
        candidates.append(({"major_type": major}, "major_type"))
    for grade in ("1", "2", "3", "4"):
        candidates.append(({"grade": grade}, "grade"))
    for year in ("2003", "2004", "2005", "2006", "2007"):
        candidates.append(({"entry_year": year}, "entry_year"))
    for prompt in prompts:
        for timed in ("timed", "untimed"):
            candidates.append(({"prompt_id": prompt, "timed_status": timed}, "prompt+timed"))

    census: dict[str, dict] = {}
    seen: set[tuple] = set()
    for criteria, gtype in candidates:
        key = tuple(sorted(criteria.items()))
        if key in seen:
            continue
        seen.add(key)
        rows = members(criteria)
        n_raw = len(rows)
        n_eff, _ = effective(rows)
        avail = "available" if n_eff >= min_n else "unavailable"
        if n_raw >= min_n and n_eff < min_n:
            avail = "limited"
        census[gid_of(criteria)] = {
            "criteria": dict(sorted(criteria.items())),
            "group_type": gtype,
            "n_raw": n_raw,
            "n_effective": n_eff,
            "excluded": n_raw - n_eff,
            "availability": avail,
        }
    return census


def resolve(census: dict, *, prompt_id: str | None = None,
            timed_status: str | None = None, genre: str | None = None) -> tuple[str | None, str | None]:
    """Mirror ReferenceGroupIndex.resolve() -> (resolved_gid, fallback_requested_gid)."""
    candidates = []
    if prompt_id and timed_status:
        candidates.append(gid_of({"prompt_id": prompt_id, "timed_status": timed_status}))
    if prompt_id:
        candidates.append(gid_of({"prompt_id": prompt_id}))
    if genre is None and prompt_id:
        genre = "argumentative" if prompt_id.startswith("ARG") else "expository"
    if genre and timed_status:
        candidates.append(gid_of({"genre": genre, "timed_status": timed_status}))
    if genre:
        candidates.append(gid_of({"genre": genre}))
    for gid in candidates:
        group = census.get(gid)
        if group is not None and group["n_effective"] >= MIN_N:
            return gid, None if gid == candidates[0] else candidates[0]
    return None, candidates[0] if candidates else None


def main() -> int:
    manifest = load_manifest()
    duplicates = load_duplicates()
    census = build_census(manifest, duplicates)

    # ---- cross-validate reconstruction against governed artifacts ----
    membership: dict[str, Counter] = defaultdict(Counter)
    with open(INTEL_DATA / "reference_group_membership.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            membership[r["reference_group_id"]][r["role"]] += 1

    dists: list[dict] = []
    with open(INTEL_DATA / "reference_distributions.jsonl", encoding="utf-8") as f:
        for line in f:
            dists.append(json.loads(line))

    jl_groups = {}
    for d in dists:
        prev = jl_groups.get(d["reference_group_id"])
        if prev is None:
            jl_groups[d["reference_group_id"]] = {"n_effective": set(), "n_raw": set()}
        jl_groups[d["reference_group_id"]]["n_effective"].add(d["n_effective"])
        jl_groups[d["reference_group_id"]]["n_raw"].add(d["n_raw"])

    approved_ids = sorted(g for g, c in census.items() if c["availability"] in ("available", "limited"))
    assert len(approved_ids) == 75, f"approved count {len(approved_ids)} != 75"
    assert set(jl_groups) == set(approved_ids), "JSONL group set != approved census set"
    assert set(membership) == set(approved_ids), "membership CSV group set != approved census set"
    for gid in approved_ids:
        assert len(jl_groups[gid]["n_effective"]) == 1 and len(jl_groups[gid]["n_raw"]) == 1
        assert census[gid]["n_effective"] == next(iter(jl_groups[gid]["n_effective"]))
        assert census[gid]["n_raw"] == next(iter(jl_groups[gid]["n_raw"]))
        assert census[gid]["n_effective"] == membership[gid]["member"]
    print(f"cross-validation OK: 96 candidates, 75 approved, census == membership CSV == JSONL")

    # ---- 1. duplicate fold facts ----
    dups_per_doc = Counter(duplicates.values())
    dup_docs = len(duplicates)                                  # docs touched by any row (last-wins)
    distinct_groups = len(dups_per_doc)                          # one canonical per group
    groups_with_2plus = sum(1 for n in dups_per_doc.values() if n >= 2)
    canonical_docs = distinct_groups
    non_canonical = dup_docs - canonical_docs
    print(f"duplicate fold: rows=348 docs_touched_after_fold={dup_docs} "
          f"groups_with_2plus={groups_with_2plus} canonical={canonical_docs} "
          f"non_canonical={non_canonical} excluded={non_canonical}")

    # ---- 2. census write + summaries ----
    with open(OUT / "minn_group_census.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["reference_group_id", "group_type", "n_raw",
                                          "n_effective", "excluded", "availability",
                                          "selection_criteria"])
        w.writeheader()
        for gid in sorted(census):
            c = census[gid]
            w.writerow({"reference_group_id": gid, "group_type": c["group_type"],
                        "n_raw": c["n_raw"], "n_effective": c["n_effective"],
                        "excluded": c["excluded"], "availability": c["availability"],
                        "selection_criteria": json.dumps(c["criteria"])})

    by_type = defaultdict(list)
    for gid, c in census.items():
        by_type[c["group_type"]].append(c["n_effective"])
    print("\n== effective size by group type (n_effective) ==")
    for t in sorted(by_type):
        vals = sorted(by_type[t])
        print(f"{t:12s} n={len(vals):2d} min={vals[0]:4d} median={statistics.median(vals):6.0f} "
              f"max={vals[-1]:4d} vals={vals}")

    eff_all = sorted(c["n_effective"] for c in census.values())
    approved_eff = sorted(c["n_effective"] for c in census.values() if c["availability"] == "available")
    print(f"\nall candidates (96): min={eff_all[0]} p25={statistics.quantiles(eff_all, n=4)[0]:.0f} "
          f"median={statistics.median(eff_all):.0f} p75={statistics.quantiles(eff_all, n=4)[2]:.0f} "
          f"max={eff_all[-1]}")
    print(f"approved (75):       min={approved_eff[0]} p25={statistics.quantiles(approved_eff, n=4)[0]:.0f} "
          f"median={statistics.median(approved_eff):.0f} p75={statistics.quantiles(approved_eff, n=4)[2]:.0f} "
          f"max={approved_eff[-1]}")
    bands = [(30, 39), (40, 49), (50, 99), (100, 249), (250, 499), (500, 10**9)]
    print("approved size bands:")
    for lo, hi in bands:
        n = sum(1 for v in approved_eff if lo <= v <= hi)
        print(f"  [{lo:3d},{hi:>5d}] {n:2d} groups")
    fragile = [gid for gid, c in census.items() if 30 <= c["n_effective"] < 50]
    print("fragile tail (30<=n_eff<50):", [(g, census[g]["n_effective"]) for g in fragile])

    # ---- 3. threshold sweep ----
    sweep_rows = []
    for t in THRESHOLDS:
        avail_eff = sum(1 for c in census.values() if c["n_effective"] >= t)
        avail_raw = sum(1 for c in census.values() if c["n_raw"] >= t)
        approved_survivors = sum(1 for c in census.values()
                                 if c["availability"] == "available" and c["n_effective"] >= t)
        sweep_rows.append({"min_n": t, "candidates_n_effective": avail_eff,
                           "candidates_n_raw": avail_raw, "current_approved_survivors": approved_survivors})
    with open(OUT / "minn_threshold_sweep.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["min_n", "candidates_n_effective",
                                          "candidates_n_raw", "current_approved_survivors"])
        w.writeheader()
        w.writerows(sweep_rows)
    print("\n== threshold sweep (candidate-group availability) ==")
    for r in sweep_rows:
        print(f"min_n={r['min_n']:3d}  effective-policy groups={r['candidates_n_effective']:2d}  "
              f"raw-count groups={r['candidates_n_raw']:2d}  current-approved survivors={r['current_approved_survivors']:2d}")

    # groups gained/lost vs min_n=30
    for t in (20, 40, 50):
        gained = sorted(gid for gid, c in census.items()
                        if t <= c["n_effective"] < MIN_N or (MIN_N <= c["n_effective"] < t and c["availability"] != "available"))
        gained = sorted(gid for gid, c in census.items() if c["n_effective"] >= t and c["n_effective"] < MIN_N)
        lost = sorted(gid for gid, c in census.items() if c["n_effective"] >= MIN_N and c["n_effective"] < t)
        print(f"t={t}: gained vs 30 = {[(g, census[g]['n_effective']) for g in gained]}; "
              f"lost vs 30 = {[(g, census[g]['n_effective']) for g in lost]}")

    # strict duplicate exclusion counterfactual (drop ALL dup-touched docs)
    strict_eff = {}
    for gid, c in census.items():
        rows = [r for r in manifest if all(r.get(k) == v for k, v in c["criteria"].items())]
        strict_eff[gid] = sum(1 for r in rows if r["document_id"] not in duplicates)
    strict_avail = sum(1 for gid, c in census.items() if strict_eff[gid] >= MIN_N)
    print(f"\nstrict-exclusion counterfactual (exclude all {dup_docs} dup-touched docs): "
          f"{strict_avail} groups >= 30 vs {sum(1 for c in census.values() if c['n_effective'] >= MIN_N)} current")
    print("approved groups whose strict-exclusion N drops below 30:",
          [(g, strict_eff[g]) for g in approved_ids if strict_eff[g] < MIN_N])

    # ---- 4. fallback resolution over 54 signatures ----
    prompts = sorted({r["prompt_id"] for r in manifest})
    fallback_rows = []
    counts = Counter()
    for prompt in prompts:
        for timed in ("timed", "untimed"):
            resolved, fallback = resolve(census, prompt_id=prompt, timed_status=timed)
            requested = f"RG-prompt_id={prompt}-timed_status={timed}"
            if fallback is None and resolved is not None:
                outcome = "exact"
            elif resolved is None:
                outcome = "unavailable"
            elif resolved.startswith("RG-prompt_id=") and "timed_status" not in resolved:
                outcome = "prompt_fallback"
            elif resolved.startswith("RG-genre="):
                outcome = "genre_fallback"
            else:
                outcome = "other"
            counts[outcome] += 1
            fallback_rows.append({"prompt_id": prompt, "timed_status": timed,
                                  "requested": requested, "resolved": resolved, "outcome": outcome})
    with open(OUT / "minn_fallback_resolution.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["prompt_id", "timed_status", "requested", "resolved", "outcome"])
        w.writeheader()
        w.writerows(sorted(fallback_rows, key=lambda r: (r["prompt_id"], r["timed_status"])))
    print("\n== fallback resolution over 54 prompt x timed signatures ==")
    total = sum(counts.values())
    for k, v in sorted(counts.items()):
        print(f"  {k:16s} {v:2d}  ({100*v/total:.1f}%)")
    # genre+timed reachability
    gt = [gid for gid in census if "genre=" in gid and "timed_status=" in gid]
    print(f"  genre+timed candidate groups in index: {len(gt)} -> hierarchy step structurally dead: {not gt}")

    # ---- 5. distribution-level statistics (JSONL) ----
    n_missing_records = sum(1 for d in dists if d["n_missing"] > 0)
    flag_counter = Counter()
    for d in dists:
        for fl in d["validity_flags"]:
            flag_counter[str(fl)] += 1
    print(f"\n== distribution records (1050) == availability=",
          Counter(d["availability"] for d in dists),
          f"n_missing>0 records={n_missing_records} validity_flags={dict(flag_counter)}")
    missing_feats = Counter(d["feature_id"] for d in dists if d["n_missing"] > 0)
    print("  features with missingness:", dict(missing_feats))
    missing_groups = sorted({d["reference_group_id"] for d in dists if d["n_missing"] > 0})
    print(f"  groups with missingness ({len(missing_groups)}):", missing_groups)
    zero_std = sum(1 for d in dists if d["std"] == 0)
    zero_iqr = sum(1 for d in dists if d["iqr"] == 0)
    print(f"  degenerate records: std==0: {zero_std}, iqr==0: {zero_iqr}")

    # ---- 6. uncertainty summary per size band ----
    band_rows = []
    for lo, hi in bands:
        recs = [d for d in dists if lo <= d["n_effective"] <= hi]
        if not recs:
            continue
        ses = [d["std"] / math.sqrt(d["n_effective"]) for d in recs if d["std"] > 0]
        steps = [100.0 / d["n_effective"] for d in recs]
        band_rows.append({"band": f"{lo}-{hi}", "records": len(recs),
                          "median_n": statistics.median(d["n_effective"] for d in recs),
                          "median_se_mean": statistics.median(ses) if ses else None,
                          "median_percentile_step_pct": statistics.median(steps)})
    with open(OUT / "minn_uncertainty_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["band", "records", "median_n",
                                          "median_se_mean", "median_percentile_step_pct"])
        w.writeheader()
        w.writerows(band_rows)
    print("\n== uncertainty by size band (median over 14 features) ==")
    for r in band_rows:
        print(f"  n_eff {r['band']:>8s} records={r['records']:3d} median_n={r['median_n']:5.0f} "
              f"median_SE(mean)={r['median_se_mean']:.4f} percentile_step={r['median_percentile_step_pct']:.3f}%")

    # ---- 6b. threshold-level availability/uncertainty medians ----
    by_gid_records: dict[str, list[dict]] = defaultdict(list)
    for d in dists:
        by_gid_records[d["reference_group_id"]].append(d)
    print("\n== threshold availability vs uncertainty (all 96 candidates) ==")
    for t in (20, 30, 40, 50):
        avail = sorted(g for g, c in census.items() if c["n_effective"] >= t)
        ses = [d["std"] / math.sqrt(d["n_effective"]) for g in avail for d in by_gid_records[g] if d["std"] > 0]
        steps = [100.0 / d["n_effective"] for g in avail for d in by_gid_records[g]]
        n_effs = [c["n_effective"] for g, c in census.items() if c["n_effective"] >= t]
        print(f"  t={t}: groups={len(avail)} median_n_eff={statistics.median(n_effs):.0f} "
              f"median_SE(mean)={statistics.median(ses):.4f} "
              f"median_percentile_step={statistics.median(steps):.3f}%")

    print("\n== duplicate-exclusion deltas per group (excluded > 0) ==")
    for g, c in sorted(census.items(), key=lambda kv: -kv[1]["excluded"]):
        if c["excluded"] > 0:
            print(f"  {g}: raw={c['n_raw']} eff={c['n_effective']} excluded={c['excluded']}")
    print(f"  groups with availability='limited': "
          f"{sum(1 for c in census.values() if c['availability'] == 'limited')}")

    # ---- 7. feature-level availability (n_missing per feature over 75 groups) ----
    per_feature_missing = defaultdict(int)
    for d in dists:
        per_feature_missing[d["feature_id"]] += (1 if d["n_missing"] > 0 else 0)
    print("\nfeatures with any missingness (groups affected):", dict(per_feature_missing))

    # ---- 8. prompt-level table ----
    print("\n== per-prompt census (raw -> effective; timed combos) ==")
    for prompt in prompts:
        n_raw = sum(1 for r in manifest if r["prompt_id"] == prompt)
        g = census.get(f"RG-prompt_id={prompt}")
        gt = [c["n_effective"] for gid, c in census.items()
              if gid == f"RG-prompt_id={prompt}-timed_status=timed"]
        gu = [c["n_effective"] for gid, c in census.items()
              if gid == f"RG-prompt_id={prompt}-timed_status=untimed"]
        print(f"  {prompt} raw={n_raw:3d} eff={g['n_effective'] if g else '-':>3} "
              f"timed={gt[0] if gt else '-'} untimed={gu[0] if gu else '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
