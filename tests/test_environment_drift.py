"""Environment contract drift guards (Shared Platform & Core, environment goal).

Deterministic, read-only, no network, no uv required. Failures here mean the
committed environment contract (pyproject.toml / uv.lock / .python-version /
scripts/dev tooling) has drifted from its own rules.
"""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEV_SCRIPTS = ROOT / "scripts" / "dev"
CODE_SCAN_DIRS = [ROOT / "scripts", ROOT / "tests"]
CODE_SCAN_FILES = [ROOT / "run.bat", ROOT / "pyproject.toml", ROOT / ".python-version"]

EXPECTED_PYTHON_VERSION = "3.12.13"
EXPECTED_REQUIRES_PYTHON = ">=3.11,<3.13"

# requirements.txt is a COMPATIBILITY EXPORT: every pin must exist (same
# package + version) in pyproject.toml runtime deps or the dev group.
REQUIREMENTS_COMPAT = {
    "streamlit": "1.60.0",
    "fastapi": "0.135.2",
    "uvicorn": "0.41.0",
    "httpx": "0.28.1",
    "pydantic": "2.13.4",
    "python-dotenv": "1.2.2",
    "pytest": "9.1.1",
    "spacy": "3.8.7",
    "playwright": "1.61.0",
}


def _pyproject() -> dict:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def _pin_map(entries: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for entry in entries:
        match = re.match(r"^([A-Za-z0-9_.-]+)(?:\[[^\]]*\])?==([0-9][0-9A-Za-z.+-]*)", entry)
        if match:
            result[match.group(1)] = match.group(2)
    return result


def test_python_version_declaration_is_exact() -> None:
    declared = (ROOT / ".python-version").read_text(encoding="utf-8").strip()
    assert declared == EXPECTED_PYTHON_VERSION, (
        f".python-version drifted: {declared!r} != {EXPECTED_PYTHON_VERSION!r}"
    )


def test_requires_python_covers_policy_range() -> None:
    project = _pyproject()["project"]
    assert project["requires-python"] == EXPECTED_REQUIRES_PYTHON


def test_uv_lock_exists_and_matches_manifest() -> None:
    lock = ROOT / "uv.lock"
    assert lock.exists(), "uv.lock missing: dependency resolution is not locked"
    text = lock.read_text(encoding="utf-8")
    assert re.search(r'requires-python = ">=3\.11, ?<3\.13"', text), (
        "uv.lock requires-python drifted from >=3.11,<3.13"
    )
    project = _pyproject()["project"]
    assert "name = \"writing-feedback-mvp\"" in text
    assert f'version = "{project["version"]}"' in text


def test_no_sibling_worktree_venv_references() -> None:
    forbidden = [
        re.compile(r"worktrees\\.+\\\.venv", re.IGNORECASE),
        re.compile(r"writing-feedback-mvp\\\.venv", re.IGNORECASE),
        re.compile(r"\.pth"),
        re.compile(r"shared-core-h1\\\.venv", re.IGNORECASE),
    ]
    offenders: list[str] = []
    for path in _scan_targets():
        for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for pattern in forbidden:
                if pattern.search(line):
                    offenders.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()}")
    assert not offenders, "sibling-worktree / borrowed-environment references found:\n" + "\n".join(offenders[:20])


def test_no_absolute_developer_specific_python_paths() -> None:
    forbidden = [
        re.compile(r"C:\\Users\\16073", re.IGNORECASE),
        re.compile(r"codex-runtimes"),
        re.compile(r"AppData\\Roaming\\uv", re.IGNORECASE),
        re.compile(r"AppData\\Local\\uv", re.IGNORECASE),
        # Drive-letter absolute paths; the lookbehind prevents matching
        # "word:\n"-style escaped sequences inside string literals.
        re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:\\"),
    ]
    # Corpus & NLP owns pre-existing absolute corpus-data / checkout paths in
    # these scripts (recorded follow-up; the environment layer does not change
    # corpus semantics). Everything else in scripts/ and tests/ must be free of
    # machine-specific absolute paths.
    corpus_owned_allowed = {
        Path("scripts/corpus_readiness/01_inventory.py"),
        Path("scripts/corpus_readiness/02_encoding.py"),
        Path("scripts/corpus_readiness/03_manifest.py"),
        Path("scripts/corpus_readiness/04_pairing.py"),
        Path("scripts/corpus_readiness/05_quality.py"),
        Path("scripts/corpus_readiness/06_composition.py"),
        Path("scripts/corpus_readiness/07_reference_groups.py"),
        Path("scripts/corpus_readiness/08_features.py"),
        Path("scripts/corpus_readiness/09_leakage.py"),
        Path("scripts/corpus_readiness/10_version.py"),
        Path("scripts/corpus_readiness/README.md"),
        Path("scripts/corpus_readiness/tests/test_readiness.py"),
        Path("scripts/corpus_intelligence/build_stage5.py"),
    }
    offenders: list[str] = []
    for path in _scan_targets():
        if path.relative_to(ROOT) in corpus_owned_allowed:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for pattern in forbidden:
                if pattern.search(line):
                    offenders.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()}")
    assert not offenders, (
        "developer-specific or machine-specific absolute paths found:\n"
        + "\n".join(offenders[:20])
        + "\n(corpus-owned absolute paths are allowlisted with owner Corpus & NLP; "
        "new absolute paths must be removed or allowlisted with a documented owner)"
    )


def test_no_unauthorized_pip_install_in_canonical_scripts() -> None:
    offenders: list[str] = []
    for path in DEV_SCRIPTS.glob("*.ps1"):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "pip install" in line and "install uv" not in line.lower():
                offenders.append(f"{path.name}:{lineno}: {line.strip()}")
    assert not offenders, "unauthorized pip install instructions in canonical scripts:\n" + "\n".join(offenders)


def test_bootstrap_and_verifier_agree_on_environment_location() -> None:
    for name in ("bootstrap_environment.ps1", "verify_environment.ps1", "run_tests.ps1"):
        text = (DEV_SCRIPTS / name).read_text(encoding="utf-8")
        assert "uv_helpers.ps1" in text, f"{name} must dot-source uv_helpers.ps1"
        assert "Get-VenvPython" in text or "Get-VenvPython" in (DEV_SCRIPTS / name).read_text(encoding="utf-8")


def test_requirements_txt_is_consistent_compatibility_export() -> None:
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    pins = _pin_map([line for line in requirements.splitlines() if line and not line.startswith("#")])
    project = _pyproject()["project"]
    groups = _pyproject()["dependency-groups"]
    manifest_pins = dict(_pin_map(project["dependencies"]))
    manifest_pins.update(_pin_map(groups["dev"]))
    assert set(pins) == set(REQUIREMENTS_COMPAT), (
        f"requirements.txt package set drifted: {sorted(set(pins) ^ set(REQUIREMENTS_COMPAT))}"
    )
    for name, version in pins.items():
        assert manifest_pins.get(name) == version, (
            f"requirements.txt {name}=={version} drifted from pyproject {manifest_pins.get(name)}"
        )


def test_nlp_model_pin_is_explicit() -> None:
    groups = _pyproject()["dependency-groups"]
    nlp = " ".join(groups["nlp"])
    assert "en-core-web-sm" in nlp and "3.8.0" in nlp, "nlp group must pin en-core-web-sm 3.8.0"


def test_python_311_syntax_gate() -> None:
    """All repository Python files must remain parseable with 3.11 grammar."""
    failures: list[str] = []
    count = 0
    for path in ROOT.rglob("*.py"):
        if any(part.startswith(".") or part == ".venv" for part in path.relative_to(ROOT).parts):
            continue
        count += 1
        try:
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path), feature_version=(3, 11))
        except SyntaxError as exc:
            failures.append(f"{path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}")
    assert count > 100, "syntax gate did not scan the repository"
    assert not failures, "files not parseable with Python 3.11 grammar:\n" + "\n".join(failures[:20])


def _scan_targets() -> list[Path]:
    targets: list[Path] = []
    excluded = {Path(__file__).resolve()}
    for directory in CODE_SCAN_DIRS:
        if directory.exists():
            targets.extend(
                path
                for path in directory.rglob("*")
                if path.is_file()
                and path.suffix.lower() in {".py", ".ps1", ".bat", ".toml"}
                and path.resolve() not in excluded
            )
    for path in CODE_SCAN_FILES:
        if path.exists() and path.resolve() not in excluded:
            targets.append(path)
    return targets


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
