# CORPUS PDW1 Throughput Expansion — Goal Handoff Report

| Field | Value |
| --- | --- |
| Goal | `PDW1-CORPUS-THROUGHPUT-EXPANSION` |
| Owner | CORPUS |
| Worktree | `A:\EAP Agent Project\worktrees\corpus` |
| Branch | `dept/corpus` |
| Starting SHA | `b6fce9a500502c6929fe0a0e8da4748348967426` |
| Verdict | **GREEN** (measured throughput; hygiene clean; regression green) |
| Date | 2026-08-10 |

## Delivered

Real measured corpus throughput over the SECCL20 spoken-transcript layer:
2,852 eligible documents, all previously unprocessed, processed via new
deterministic resumable tooling; 39,928 numeric snapshot rows (outside git);
21 governed reference groups; 294 distribution records (all available);
full provenance; `research_only` exposure everywhere.

## Measured counts

| Count | Value |
| --- | --- |
| Total eligible (SECCL20 manifest rows, prepared, decodable) | 2,852 |
| Already processed before this Goal | 0 |
| Newly processed | 2,852 |
| Failed | 0 |
| Excluded | 0 |
| Blocked | 0 (TEM8: 916 documented but absent from physical copy — separate scope) |
| Snapshot rows (2,852 docs x 14 features) | 39,928 |
| Reference groups / distribution records | 21 / 294 (all available) |
| Coverage of SECCL20 manifest | 100% |

## Verification

- 29 new unit tests (adapter, eligibility, groups, batch plan, partitions,
  hygiene) + 7 artifact tests: all pass.
- Existing corpus suite (70 tests): all pass (no frozen WECCL20 behavior
  changed).
- Idempotency: re-run skips all 2,852 processed docs (ledger), no duplicate
  rows.
- Determinism: distributions JSONL byte-identical across runs
  (SHA-256 `4B1B958CE9B083A954C892E4AE79A1F024F4E17BE6C9346714C2932F32DD2094`).
- Leak scans (raw paths, raw text, banned vocabulary, exposure fields):
  clean.

## Artifacts

- `docs/corpus-intelligence/l2/18_PDW1_THROUGHPUT_EXPANSION.md`
- `docs/corpus-intelligence/l2/data/seccl/*` (descriptor, versions,
  membership, distributions, artifact register)
- `app/corpus/seccl.py`, `scripts/corpus_intelligence/build_seccl.py`,
  `tests/corpus/test_seccl.py`, `tests/corpus/test_seccl_artifacts.py`

## Dependencies / gates

- Unlocked: SECCL20 spoken reference material now available as governed
  research-only aggregates for future CORPUS work.
- Remaining: D3/D8/D12 boundaries unchanged; no learner-facing exposure;
  no promotion (INT gate + exact-SHA authorization still required).
