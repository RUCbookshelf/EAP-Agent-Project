# 08 — CI / Local Parity Contract

**Department:** Shared Platform & Core
**Goal:** Developer Environment Reproducibility Foundation
**Date:** 2026-08-08

## 1. Current state

There is **no CI** in this repository (no `.github/`, no other CI configuration). Per Goal §16,
this Goal does NOT create a CI platform. Instead it defines the future CI contract and makes the
local commands CI-consumable, so that when CI is introduced it consumes the exact same contract
as local development.

## 2. One contract, three consumers

```text
local development      CI (future)          verification tooling
        \                   |                     /
         \                  v                    /
          pyproject.toml -> uv.lock -> `uv sync` (--locked)
                        -> `uv run pytest ...`
```

There must never again be "local setup A / CI setup B / agent setup C". All consumers use:

| Concern | Single source | Local command | Future CI command |
| --- | --- | --- | --- |
| Python version | `.python-version` (3.12.13) + `requires-python` | `uv sync` | `astral-sh/setup-uv` + `uv sync --locked` |
| Dependency resolution | `uv.lock` | `uv sync --check` (drift) | `uv sync --locked` (hard failure on drift) |
| Environment validation | `scripts/dev/verify_environment.ps1` | full check | `--json` output consumed by CI step |
| Test invocation | `scripts/dev/run_tests.ps1` | focused/full | the same canonical command: `python verification/v0.9.5-h2a/isolated_pytest_runner.py --full` (venv interpreter) |
| DB isolation | `verification/v0.9.5-h2a/isolated_pytest_runner.py` + `scripts/verify_launcher.py` | runner handles it | same runner, fresh temp DB |
| External resources | 06_EXTERNAL_RESOURCE_CONTRACT.md | `uv sync` (model); documented browser install | same commands with cache dirs |

## 3. Future CI contract (documented, not implemented)

When CI is introduced (separate decision; not this Goal), it must:

1. Use the official uv action (e.g., `astral-sh/setup-uv`) with the same uv minimum version.
2. Run `uv sync --locked` (all default groups) — a stale `uv.lock` fails the pipeline.
3. Run the environment verifier (`--json`) as a job gate before tests.
4. Run the full non-live core exactly as the local canonical runner does
   (`pytest -q -p no:cacheprovider --ignore=tests/live tests`) with an isolated temporary
   database and `LLM_PROVIDER=local`.
5. Cover Python 3.12 as the primary lane. A Python 3.11 lane is optional and only after the
   recorded canonical 3.11 re-run exists (02_PYTHON_RUNTIME_CONTRACT.md, Option B).
6. Add the cheap syntax-level 3.11 gate (`ast.parse(feature_version=(3, 11))` over the repo's
   Python files, BOM-stripped) so future dependency churn cannot silently drop 3.11 parseability.
7. Never duplicate dependency-install logic: CI consumes `uv.lock` exactly as local bootstrap.

## 4. Gate statement

**WU10 GREEN (draft) — no competing environment contracts are introduced; the future CI
contract is documented and every local command is CI-consumable.**
