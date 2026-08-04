from __future__ import annotations

"""Hardened launcher verification with mandatory database isolation.

Invoked by run.bat --verify BEFORE any migration, API startup, health
check, smoke stack, or other write-capable action.

Rules:
  - If DATABASE_URL is set in the process environment, the effective
    database target is resolved the same way the application resolves it
    (app.config.load_settings) and must not be the development database or
    any database inside the repository data/ directory.  Unsafe targets
    fail before any process starts.
  - If DATABASE_URL is not set in the process environment, a fresh
    temporary database is automatically provisioned outside the repository
    and removed when verification finishes.  This applies regardless of
    .env content or DATABASE_PATH, so verification can never silently fall
    back to the development database.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from app.config import PROJECT_ROOT, load_settings


PROTECTED_DATA_DIR = PROJECT_ROOT / "data"
DEV_DATABASE = PROTECTED_DATA_DIR / "writing_feedback.db"


class LauncherIsolationError(RuntimeError):
    """Verification refused because the effective database target is unsafe."""


def normalized(path: Path) -> str:
    return os.path.normcase(str(Path(path).resolve()))


def is_development_database(path: Path) -> bool:
    return normalized(path) == normalized(DEV_DATABASE)


def is_inside_protected_data(path: Path) -> bool:
    resolved = Path(path).resolve()
    protected = PROTECTED_DATA_DIR.resolve()
    if normalized(resolved) == normalized(protected):
        return True
    return any(normalized(parent) == normalized(protected) for parent in resolved.parents)


def is_unsafe_target(path: Path) -> bool:
    return is_development_database(path) or is_inside_protected_data(path)


def classify_verify_environment(database_url: str | None, settings) -> dict[str, object]:
    """Decide explicit vs auto-provisioned isolation before any process starts.

    ``database_url`` must be the raw DATABASE_URL from the process
    environment BEFORE dotenv loading, so .env defaults can never be
    mistaken for an explicit operator choice.
    """
    if database_url is None:
        return {"mode": "auto_provision", "effective_path": None}
    if not database_url.strip():
        raise LauncherIsolationError(
            "Launcher verification refused before startup: DATABASE_URL is set but "
            "empty, so normal settings would fall back to the development database. "
            "Remove DATABASE_URL to use an automatically provisioned temporary "
            "database, or set it to a fresh isolated database file outside the "
            "repository data/ directory. No database connection or write was made."
        )
    effective = Path(settings.database_path)
    if is_unsafe_target(effective):
        raise LauncherIsolationError(
            "Launcher verification refused before startup: the effective database "
            "target resolves to the protected development database "
            "(data/writing_feedback.db or a database inside the repository data/ "
            "directory). Set DATABASE_URL to a fresh isolated database file outside "
            "data/ (for example a new file under the system temporary directory), or "
            "omit DATABASE_URL to use an automatically provisioned temporary "
            "database. No database connection or write was made."
        )
    return {"mode": "explicit", "effective_path": effective}


def provision_temp_database(tmp_root: Path | None = None) -> Path:
    root = Path(tmp_root) if tmp_root is not None else Path(tempfile.gettempdir())
    for _ in range(100):
        candidate = root / (
            f"wfm-verify-{time.strftime('%Y%m%dT%H%M%S')}-{os.getpid()}.db"
        )
        if not candidate.exists():
            return candidate
        time.sleep(0.01)
    raise RuntimeError("Could not allocate a unique temporary verification database name.")


def cleanup_database(path: Path) -> None:
    for candidate in (
        path,
        Path(str(path) + "-journal"),
        Path(str(path) + "-wal"),
        Path(str(path) + "-shm"),
    ):
        try:
            if candidate.exists():
                candidate.unlink()
        except OSError:
            pass


def run_step(args: list[str], env: dict[str, str]) -> int:
    result = subprocess.run(
        [sys.executable, *args],
        cwd=PROJECT_ROOT,
        env=env,
        check=False,
    )
    return result.returncode


def run_verification_steps(env: dict[str, str]) -> list[dict[str, object]]:
    steps = [
        ("migrate", ["-m", "scripts.migrate_database"]),
        ("initialize", ["-m", "scripts.initialize_project"]),
        ("smoke_stack", ["-m", "scripts.smoke_stack", "--python", sys.executable]),
    ]
    results = []
    for name, args in steps:
        code = run_step(args, env)
        results.append({"step": name, "exit_code": code})
        if code != 0:
            raise RuntimeError(f"Launcher verification step failed: {name} (exit {code}).")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tmp-root", default=None, help="Override temp location (testing only).")
    args = parser.parse_args(argv)

    os.environ.setdefault("PYTHONUTF8", "1")
    explicit_url = os.environ.get("DATABASE_URL")
    settings = load_settings()
    try:
        plan = classify_verify_environment(explicit_url, settings)
    except LauncherIsolationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    provisioned: Path | None = None
    if plan["mode"] == "auto_provision":
        provisioned = provision_temp_database(
            Path(args.tmp_root) if args.tmp_root else None
        )
        os.environ["DATABASE_URL"] = f"sqlite:///{provisioned.as_posix()}"
        effective = provisioned
        print(
            f"INFO: DATABASE_URL is not set in the environment; using fresh "
            f"temporary database {effective} for verification.",
            file=sys.stderr,
        )
    else:
        effective = plan["effective_path"]

    try:
        steps = run_verification_steps(os.environ)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        if provisioned is not None:
            cleanup_database(provisioned)

    print(json.dumps({
        "status": "PASS",
        "isolation_mode": plan["mode"],
        "effective_database_path": str(effective),
        "steps": steps,
    }, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())