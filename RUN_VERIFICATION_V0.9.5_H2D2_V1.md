# v0.9.5-H2D2-V1 Verification - Full-Core Closure

**Status:** **PASS - v0.9.5-H2D2 is COMPLETE and fully verified.** One fresh
full non-live core closure run: exit code 0, 709 passed, 8 skipped, 2
warnings, zero failures and zero errors.

## Baseline

| Item | Value |
| --- | --- |
| Branch | `master` |
| Baseline HEAD | `4cbf908` (v0.9.5-H2D2 verification commit) |
| H2D2 implementation | `10ed388` `refactor(v0.9.5-h2d2): bind api ports to dependency accessors` |
| H2D2 verification | `4cbf908` `test(v0.9.5-h2d2): verify api dependency port bindings` |
| Prior full-core (H2D2 run) | exit 1, 1 failed / 708 passed / 8 skipped (documented pre-existing lifecycle-race flake; passes in isolation) |

## Exactly one full-core run

- Command: `pytest -q -p no:cacheprovider --ignore=tests/live tests`
  (executed via `.venv\Scripts\python.exe -m pytest ...` under the isolated
  runner `verification/v0.9.5-h2a/isolated_pytest_runner.py --full`).
- Isolation: `PYTHON_DOTENV_DISABLED=1`, `DATABASE_URL` removed,
  `DATABASE_PATH=C:\Users\16073\AppData\Local\Temp\v095h2a-g__xwr8r\h2a.db`
  (fresh unique temporary directory; resolved settings path asserted inside
  the temp dir and confirmed not the development database),
  `LLM_PROVIDER=local`.
- Start: 2026-08-03T16:00:34 +08:00; end: 2026-08-03T16:05:48 +08:00;
  duration 313.9 s.
- Result: **exit code 0; 709 passed, 8 skipped, 2 warnings; 0 failed;
  0 errors.**
- Temporary directory removed after evidence capture; `.pytest_cache`
  removed; ports 8000/8501 free before and after.

## Research-export workspace

- Pre-run baseline: 776 files / 388 dirs (guard `--check` PASS).
- The run generated 8 new top-level export directories / 16 files:
  `export_20260803T080313`, `export_20260803T080322`,
  `export_20260803T080323`, `export_20260803T080324`,
  `export_20260803T080326`, `export_20260803T080436`,
  `export_20260803T080437`, `export_20260803T080537`.
- Cleanup: exact allowlist delta captured by
  `verification/v0.9.5-h2d2/export_workspace_guard.py --delta` (16 entries,
  classification A, content-signature + absent-from-baseline evidence) and
  deleted leaf-first by `--restore`; the root and all baseline entries were
  preserved.
- Final: **776 files / 388 dirs; all retained paths and SHA-256 hashes
  unchanged** (guard `--check` PASS; full manifest
  `verification/v0.9.5-h2d2-v1/research_exports_after.json`).
- The H2D2 tracked guard artifacts reused during cleanup
  (`verification/v0.9.5-h2d2/test_export_deltas.json`) were restored
  byte-identical from `4cbf908`.

## Database isolation

- Development database before and after the run: SHA-256
  `340E0F3739FEFFD3DEF87BB6E711CB6F90A8478E7E18D833C715EDCFAB03AFF4`, size
  8,298,496 bytes, mtime `2026-08-02T11:02:25.887+08:00` - unchanged; never
  opened.

## Source state

- No production file changed; no test file changed; no configuration changed.
- Preserved user-owned paths untouched: `AGENTS.md`,
  `RUN_VERIFICATION_V0.7.md`, `RUN_VERIFICATION_V0.8.2.md`, `.claude/`,
  `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`, `CLAUDE.md`,
  `data/demo_journey_manifest.json`, `data/writing_feedback.db`,
  `research_exports/` baseline.

## Evidence artifacts

- `verification/v0.9.5-h2d2-v1/baseline_state.json`
- `verification/v0.9.5-h2d2-v1/research_exports_before.json`
- `verification/v0.9.5-h2d2-v1/full_core_raw.log`
- `verification/v0.9.5-h2d2-v1/full_core_closure.json`
- `verification/v0.9.5-h2d2-v1/research_exports_delta.json`
- `verification/v0.9.5-h2d2-v1/research_exports_after.json`

## Conclusion

`v0.9.5-H2D2 is COMPLETE and fully verified.` H2E (architecture freeze)
proceeds under the same authorized goal.
