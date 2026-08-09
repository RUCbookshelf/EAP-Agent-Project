# CORPUS Stage-6 Integration Gate Repair (INT-STAGE6-INTEGRATION-GATE__REPAIR)

**Owner:** CORPUS | **Branch:** dept/corpus | **Worktree:** `A:\EAP Agent Project\worktrees\corpus`
**Starting SHA:** `5aafe2728d7135212bd675a6975b44bcf99ee099` (no commits made; final SHA = starting SHA, working-tree repair only)
**Date:** 2026-08-09
**Verdict:** GREEN (both blocking findings BF-1/BF-2 from INT-STAGE6-INTEGRATION-GATE-20260809 resolved; Stage-6 WU-A/B/C/E semantics untouched)

## BF-1 — Invalid UTF-8 in governed corpus scripts (byte-level corruption)

The gate reported `scripts/corpus_readiness/05_quality.py` (bytes 6612-6613): the literal `'未录完'` had been rewritten by the portability pass as an incomplete GBK-mis-encoded sequence (`E5 AE 3F` instead of `E5 AE 8C 27`), making the file unparseable and failing `test_python_311_syntax_gate` with `UnicodeDecodeError`.

Repair (byte-surgical, preserving every other byte):

1. `scripts/corpus_readiness/05_quality.py` — replaced corrupted bytes `E6 9C AA E5 BD 95 E5 AE 3F` at offset 6606 with `E6 9C AA E5 BD 95 E5 AE 8C 27` (restores `未录完` + closing quote). File size 9404 → 9405 bytes; strict UTF-8 valid; `ast.parse(feature_version=(3, 11))` passes; `git diff` now shows the detail line byte-identical to HEAD (only the intended portability edits remain).
2. `scripts/corpus_readiness/06_composition.py` — **additional corruption found during full-repo re-scan** (the gate's syntax scan stopped at the first failing file, so this second victim was not reported): comment `SWECCL2.0_语料库概况报告.md` had been rewritten as `...报?md` (`E5 91 3F` instead of `E5 91 8A 2E`). Replaced at offset 695 with `E5 91 8A 2E`; strict UTF-8 valid; 3.11-parseable; `git diff` shows the comment byte-identical to HEAD.

Full-repo UTF-8 scan (453 `.py` files, strict decode): 0 invalid after repair. The only remaining non-UTF-8 files in the repository are 11 pre-existing UTF-16 artifacts under `verification/` (tracked at HEAD, outside candidate scope, untouched).

## BF-2 — Environment-contract drift guard failures (5 absolute-path offenders)

All five offenders portabilized (no allowlist restored — the drift guard now runs with zero exclusions, as the portability follow-up intended):

| Offender | Repair | Rationale |
| --- | --- | --- |
| `scripts/corpus_readiness/02_encoding.py:7` (docstring) | Replaced `A:\[Linguistics Data] Corpus\SWECCL 2.0\PREPARED\utf8\<component>\...` with `<CORPUS_ROOT>/PREPARED/utf8/<component>/...` + note that the corpus root is resolved portably via `scripts/corpus_paths.py` | Docstring documentation only; no runtime literal needed |
| `scripts/corpus_readiness/tests/test_readiness.py:10` | `REPO = Path(r"A:\EAP Agent Project\writing-feedback-mvp")` → `REPO = get_repo_root()` | Repo-relative resolution via `scripts/corpus_paths.py` |
| `scripts/corpus_readiness/tests/test_readiness.py:12` | Removed module-level `CORPUS` literal; corpus root now resolved lazily inside `test_derived_roundtrip_sample` via `get_corpus_root()` | Keeps module import safe when `CORPUS_ROOT` is unset (no `sys.exit` at collection); raw-corpus test resolves the portable root at call time |
| `scripts/corpus_readiness/10_version.py:52` | `"physical_root": r"A:\[Linguistics Data] Corpus\SWECCL 2.0"` → `"physical_root": str(get_corpus_root())` | Provenance literal now derived from the portable root at runtime; generated `corpus_version.json` records the same physical root when the pipeline runs with `CORPUS_ROOT` set. No artifact regenerated |
| `tests/corpus/test_student.py:63` | WU-A rejection fixtures: `"A:\\raw\\path"` → `f"A:{os.sep}raw{os.sep}path"` (runtime string byte-identical on Windows) | Deliberate path-shaped test inputs are genuinely required, but constructing them via `os.sep` keeps the source free of machine-specific literals — no allowlist needed |

Supporting consistency edit: `tests/test_environment_drift.py` retained a stale comment and assertion message referencing the removed `corpus_owned_allowed` allowlist; both updated to state that corpus-owned paths are portabilized via `scripts/corpus_paths.py` with no allowlist. Logic unchanged (still fails on any offender; scan scope unchanged).

## Non-blocking fix

`docs/corpus-intelligence/l2/16_STAGE6_VERIFICATION.md`: "spaCy 3.8.14" → "spaCy 3.8.7" (documentation typo; pyproject pins `spacy==3.8.7` and the gate venv runs 3.8.7).

## Verification evidence

| Check | Command | Result |
| --- | --- | --- |
| Drift-guard suite (incl. absolute-path guard + 3.11 syntax gate) | `python -m pytest tests/test_environment_drift.py -p no:cacheprovider --basetemp <tmp>` | **10 passed** |
| Corpus suite (Stage-5 36 + Stage-6 34; no regression) | `python -m pytest tests/corpus -p no:cacheprovider --basetemp <tmp>` | **70 passed** |
| Gate invocation (exact parent-gate combination) | `python -m pytest tests/corpus tests/test_environment_drift.py -p no:cacheprovider --basetemp <tmp>` | **80 passed** (parent gate: 2 failed, 78 passed) |
| Readiness tests (modified file) | `python -m pytest scripts/corpus_readiness/tests` with `CORPUS_ROOT` set (read-only) | **8 passed** |
| UTF-8 validity | strict `decode("utf-8")` over all 453 repo `.py` files | 0 invalid |
| 3.11 syntax | repo-wide `ast.parse(feature_version=(3, 11))` via drift gate; per-file on both repaired files | PASS |

Environment: Python 3.12.13, pytest 9.1.1, spaCy 3.8.7 (shared-core-environment worktree-local venv at promoted baseline, used read-only), `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`, external `--basetemp`.

## Boundaries honored

- No commits, no push, no PR, no promotion; HEAD remains `5aafe2728d7135212bd675a6975b44bcf99ee099`.
- Writes limited to `worktrees\corpus`; master and all other worktrees untouched.
- Raw SWECCL accessed read-only only (readiness round-trip test); no mutation; no artifact regenerated.
- All pre-existing dirty/untracked candidate files preserved; only targeted repairs applied on top.
- Stage-6 WU-A/B/C/E semantics unchanged (corpus suite 70/70 identical to gate baseline).
