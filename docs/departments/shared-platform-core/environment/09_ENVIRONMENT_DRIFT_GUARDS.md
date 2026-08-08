# 09 — Environment Drift Guards

**Department:** Shared Platform & Core
**Goal:** Developer Environment Reproducibility Foundation
**Date:** 2026-08-08

## 1. Purpose

Deterministic, read-only tests that fail when the committed environment contract drifts:
version declarations, lockfile consistency, borrowed-environment references, developer-specific
absolute paths, unauthorized pip workflows, tooling agreement, compatibility exports, and
Python 3.11 parseability.

## 2. Guard inventory (`tests/test_environment_drift.py`, 10 checks)

| Guard | What it asserts |
| --- | --- |
| `test_python_version_declaration_is_exact` | `.python-version` == `3.12.13` (exact patch pin per 02 contract) |
| `test_requires_python_covers_policy_range` | `pyproject.toml` requires-python == `>=3.11,<3.13` |
| `test_uv_lock_exists_and_matches_manifest` | `uv.lock` present, requires-python range matches, project name/version match manifest |
| `test_no_sibling_worktree_venv_references` | no `worktrees\…\.venv`, `writing-feedback-mvp\.venv`, or `.pth` borrow references in scripts/tests/run.bat |
| `test_no_absolute_developer_specific_python_paths` | no `C:\Users\16073`, `codex-runtimes`, or `AppData\…\uv` absolute paths in committed tooling |
| `test_no_unauthorized_pip_install_in_canonical_scripts` | `scripts/dev/*.ps1` never pip-installs project dependencies (only the documented `install uv` provisioning line is allowed) |
| `test_bootstrap_and_verifier_agree_on_environment_location` | bootstrap/verifier/launcher all consume `uv_helpers.ps1` `Get-VenvPython` (single environment-location definition) |
| `test_requirements_txt_is_consistent_compatibility_export` | every pin in `requirements.txt` exists with the same version in pyproject runtime deps or dev group |
| `test_nlp_model_pin_is_explicit` | nlp group pins `en-core-web-sm` 3.8.0 |
| `test_python_311_syntax_gate` | all repository `.py` files parse with `ast.parse(feature_version=(3, 11))` (BOM-stripped) — 3.11 support cannot silently erode |

## 3. Design rules honored

- Legitimate test fixture paths are never prohibited (the guards target true environment drift
  only: sibling/absolute environment references, manifest mismatches).
- Guards are deterministic, offline, and require no uv/network — they run in every context,
  including CI and restricted sandboxes.
- The guards encode the contracts from 02/03/04/05 so doc drift and code drift fail together.

## 4. Gate statement

**WU12 GREEN — 10 drift guards implemented, all passing (10/10) in the canonical environment;
guard inventory documented; future CI consumes the same checks.**
