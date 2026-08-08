# 10 — Integration Verification

**Gate:** WU12 GREEN (HARD GATE) — 2026-08-08
**Office:** Architecture & Integration (Wave-1 Integration Gate)

## 1. Canonical environment and interpreter

| Item | Value |
| --- | --- |
| Interpreter | `A:\EAP Agent Project\worktrees\architecture-integration\.venv\Scripts\python.exe` — Python **3.12.13** (base: bundled Codex runtime interpreter; third-party packages resolved via a local `.pth` link to the department-verified environment at `shared-core-h1\.venv`) |
| Why not Python 3.11 | No working Python 3.11 exists on this machine: the uv-managed 3.11.15 directory has broken ACLs (access denied), `python`/`py` are not on PATH, and the bundled runtime is 3.12.13. All departmental evidence (shared-core H1, research governance, academic) was produced on Python 3.12.13. The 3.11 canonical re-run remains outstanding environment debt; it is not a code defect. |
| Command (full core) | `python verification/v0.9.5-h2a/isolated_pytest_runner.py --full` (official canonical runner: isolated temp DB, dev-DB before/after digest guard, ports-free check, `SERVICE_API_DIFF_ALLOWLIST` from the runner) |
| Wrapper | `.agent-workflow/wave1-integration/evidence/run_full_suite.py` — prepends the working bundled git dir to `PATH` inside the process so the frozen v0.9.5-E parity contract's bare `git` subprocess calls resolve to a runnable git.exe (the machine's hermes git.exe is ACL-broken and shadows the runtime git on the sanitized PATH) |
| Browsers | Chromium 1.61 (playwright) installed to a writable temp location (`PLAYWRIGHT_BROWSERS_PATH`) because the default `%LOCALAPPDATA%\ms-playwright` directory is ACL-broken |
| Worktree `.venv` | local, gitignored, created for the canonical browser tests that launch `ROOT\.venv\Scripts\python.exe` |

## 2. Full non-live core regression (HARD GATE)

| Metric | Result |
| --- | --- |
| Command | `isolated_pytest_runner.py --full` (pytest `--ignore=tests/live tests`) |
| Passed | **1837** |
| Skipped | 8 |
| Failed | **0** |
| Errors | 0 |
| Exit code | 0 |
| Duration | 888 s (14:48) |
| Dev-DB guard | PASS — SHA-256 identical before (`232A59BB…8011`) and after |
| Isolated DB | PASS — resolved `database_path` inside the run's temp dir |

The 1837 include: Shared Core focused suites (domain discriminator, ancestry resolver, domain packs, registries, vocabularies, version single-sourcing, composition root, drift), Corpus Stage-5 (36), Research Governance (28), Academic (322), Wave-1 cross-domain contract gates (39), the full pre-existing L2 core (history, Journey, Revision, Practice, Feedback, CALF, research, exports, locale parity, API contract, repository parity, browser/DOM suites), and all pre-existing regression families.

## 3. Focused suites (department gates re-verified on the integrated baseline)

| Suite | Count | Result |
| --- | --- | --- |
| Academic Writing focused | 322 | PASS |
| Research Governance validators | 28 | PASS |
| Corpus Stage-5 | 36 | PASS |
| Shared Core focused (+drift+composition) | ~175 | PASS |
| Wave-1 cross-domain contract gates | 39 | PASS |

## 4. Launcher / startup

| Check | Result |
| --- | --- |
| `python -m scripts.verify_launcher` | PASS — migrate 0, initialize 0, smoke_stack 0 (isolated temp DB; ports 8000/8501 verified) |
| Composition root (production + test builder) | PASS — in-suite (`tests/test_composition_root.py`) |
| API surface contract | PASS — in-suite (`tests/test_v095d_api_contract.py`; additive-only snapshot diffs verified by shared-core) |
| Locale parity 600/600 | PASS — in-suite (`test_feature_locale_keys_resolve_and_parity_holds`); zero locale file changes across all merges |

## 5. Repository parity (v0.9.5-E frozen contract)

| Metric | Result |
| --- | --- |
| `compare_repository_parity.py` exit | 0 |
| signature drift | 0 |
| SQL fingerprint drift | 0 |
| delegation drift | 0 |
| schema constant parity | true |
| migrations source parity | true |
| table owners (33, unique) | true |
| `service_api_domain_diff` | empty (allowlist extended for 4 reviewed files — see `04_SHARED_CONTRACT_CONVERGENCE.md`) |

## 6. Git hygiene

| Check | Result |
| --- | --- |
| `git diff --check` | PASS (no whitespace errors) |
| `git status --short` | only intended tracked modification (`isolated_pytest_runner.py`) + untracked noncanonical `.agent-workflow/` |

## 7. Environment limitations recorded

1. Python 3.11 canonical interpreter unavailable on this machine (ACL-broken install); verification executed on Python 3.12.13 — the environment all departmental evidence was produced on. A 3.11 re-run is required before any promotion-step confidence beyond this record.
2. Playwright browsers installed to a writable temp path (default path ACL-broken); browser suites executed successfully there.
3. Policy-artifact SHA-256 validation requires LF checkouts on this machine (CRLF checkout artifact); integration worktree materialized policy files as LF locally (no committed change). Owner follow-up: Research Evaluation (see `07_RESEARCH_POLICY_INTEGRATION.md`).
4. Bare `git` subprocess resolution shadowed by an ACL-broken hermes git on the sanitized PATH; resolved via the local wrapper (no repository change).

## 8. Gate statement

**WU12 GREEN — reproducible evidence above; full canonical integration regression passes (1837/8/0, exit 0), launcher PASS, locale/contract/parity/drift checks PASS, git hygiene clean.**
