"""v0.9.5-F4 isolated pytest runner.

Reuses the F2/F3 isolation protocol with the exact approved production-file
allow-list for the v0.9.5-E facade-parity guard:

- PYTHON_DOTENV_DISABLED=1, DATABASE_URL removed from the environment,
  DATABASE_PATH set to a new path inside a unique temporary directory,
  LLM_PROVIDER=local;
- settings resolved and the effective database path printed and asserted to be
  inside the temporary directory and not the development database or any
  user-owned database;
- the development database SHA-256, size, and mtime are recorded before and
  after and must be unchanged;
- the temporary directory is removed and ports 8000/8501 are verified free
  afterward.

The allow-list is the union of the F2/F3/F4 approved production diffs under
the parity-guard paths (app/services, app/journey, app/api). No wildcards.
scripts/demo_journey.py is not scanned by the parity guard.

Usage (from the repository root, with the project venv python):

    python verification/v0.9.5-f4/isolated_pytest_runner.py -- <pytest args>
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEV_DB = ROOT / "data" / "writing_feedback.db"
FORBIDDEN_FRAGMENTS = ("writing_feedback", "backup")
PORTS = (8000, 8501)
F4_ALLOWLIST = (
    "app/api/main.py,"
    "app/api/deps.py,"
    "app/api/routers/journey.py,"
    "app/services/progress.py,"
    "app/services/learner_profile.py,"
    "app/services/dashboard.py,"
    "app/services/factory.py,"
    "app/services/reanalysis.py,"
    "app/journey/service.py"
)


def _digest(path: Path) -> dict[str, object]:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    stat = path.stat()
    return {
        "sha256": hasher.hexdigest(),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def _ports_free() -> list[int]:
    busy = []
    for port in PORTS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                busy.append(port)
    return busy


def main() -> int:
    parser = argparse.ArgumentParser(description="Run pytest under the F4 isolation protocol.")
    parser.add_argument("pytest_args", nargs="*", help="pytest arguments (after --)")
    args = parser.parse_args()

    before = _digest(DEV_DB)
    print(f"[f4-isolation] dev-db before sha256={before['sha256']} size={before['size']} "
          f"mtime_ns={before['mtime_ns']}")

    temp_dir = Path(tempfile.mkdtemp(prefix="v095f4-"))
    db_path = temp_dir / "run.db"
    print(f"[f4-isolation] temp dir: {temp_dir}")

    env = os.environ.copy()
    env["PYTHON_DOTENV_DISABLED"] = "1"
    env.pop("DATABASE_URL", None)
    env["DATABASE_PATH"] = str(db_path)
    env["LLM_PROVIDER"] = "local"
    env["SERVICE_API_DIFF_ALLOWLIST"] = F4_ALLOWLIST

    probe = subprocess.run(
        [sys.executable, "-c",
         "from app.config import load_settings; print(load_settings().database_path)"],
        cwd=ROOT, env=env, capture_output=True, text=True, check=True,
    )
    resolved = Path(probe.stdout.strip())
    print(f"[f4-isolation] resolved settings.database_path = {resolved}")
    if resolved != db_path:
        raise SystemExit(f"[f4-isolation] FAIL: resolved path {resolved} != expected {db_path}")
    if not str(resolved.resolve()).startswith(str(temp_dir.resolve())):
        raise SystemExit(f"[f4-isolation] FAIL: resolved path {resolved} is outside the temp dir")
    if any(fragment in str(resolved) for fragment in FORBIDDEN_FRAGMENTS):
        raise SystemExit(f"[f4-isolation] FAIL: resolved path {resolved} looks like a user database")

    pytest_args = args.pytest_args or ["-q"]
    print(f"[f4-isolation] running: {sys.executable} -m pytest {' '.join(pytest_args)}")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *pytest_args],
        cwd=ROOT, env=env,
    )

    after = _digest(DEV_DB)
    print(f"[f4-isolation] dev-db after  sha256={after['sha256']} size={after['size']} "
          f"mtime_ns={after['mtime_ns']}")
    if after != before:
        raise SystemExit("[f4-isolation] FAIL: development database changed during verification")

    shutil.rmtree(temp_dir, ignore_errors=True)
    busy = _ports_free()
    if busy:
        raise SystemExit(f"[f4-isolation] FAIL: ports still busy: {busy}")
    print("[f4-isolation] cleanup OK: temp dir removed, ports 8000/8501 free")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
