"""v0.9.5-G isolated pytest runner.

Reuses the F2-F6D isolation protocol:

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

The allow-list is the accumulated F2-G approved production diff under the
parity-guard paths (app/services, app/journey, app/practice, app/research,
app/api). G added app/api/ports.py and migrated six Routers plus app/api
dependencies; app/database/* and app/feedback/* are not scanned by the parity
guard. No wildcards.

Usage (from the repository root, with the project venv python):

    python verification/v0.9.5-g/isolated_pytest_runner.py -- <pytest args>
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
G_ALLOWLIST = (
    "app/services/calf.py,"
    "app/api/main.py,"
    "app/api/deps.py,"
    "app/api/ports.py,"
    "app/api/routers/journey.py,"
    "app/api/routers/analysis.py,"
    "app/api/routers/calf.py,"
    "app/api/routers/research.py,"
    "app/api/routers/revisions.py,"
    "app/api/routers/students.py,"
    "app/api/routers/submissions.py,"
    "app/api/routers/system.py,"
    "app/services/progress.py,"
    "app/services/learner_profile.py,"
    "app/services/dashboard.py,"
    "app/services/factory.py,"
    "app/services/reanalysis.py,"
    "app/journey/service.py,"
    "app/research/service.py,"
    "app/services/revision.py,"
    "app/services/admin_reanalysis.py,"
    "app/services/submission.py,"
    "app/practice/ports.py,"
    "app/practice/service.py,"
    "app/api/routers/practice.py"
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
    parser = argparse.ArgumentParser(description="Run pytest under the G isolation protocol.")
    parser.add_argument("pytest_args", nargs="*", help="pytest arguments (after --)")
    args = parser.parse_args()

    before = _digest(DEV_DB)
    print(f"[g-isolation] dev-db before sha256={before['sha256']} size={before['size']} "
          f"mtime_ns={before['mtime_ns']}")

    temp_dir = Path(tempfile.mkdtemp(prefix="v095g-"))
    db_path = temp_dir / "run.db"
    print(f"[g-isolation] temp dir: {temp_dir}")

    env = os.environ.copy()
    env["PYTHON_DOTENV_DISABLED"] = "1"
    env.pop("DATABASE_URL", None)
    env["DATABASE_PATH"] = str(db_path)
    env["LLM_PROVIDER"] = "local"
    env["SERVICE_API_DIFF_ALLOWLIST"] = G_ALLOWLIST

    probe = subprocess.run(
        [sys.executable, "-c",
         "from app.config import load_settings; print(load_settings().database_path)"],
        cwd=ROOT, env=env, capture_output=True, text=True, check=True,
    )
    resolved = Path(probe.stdout.strip())
    print(f"[g-isolation] resolved settings.database_path = {resolved}")
    if resolved != db_path:
        raise SystemExit(f"[g-isolation] FAIL: resolved path {resolved} != expected {db_path}")
    if not str(resolved.resolve()).startswith(str(temp_dir.resolve())):
        raise SystemExit(f"[g-isolation] FAIL: resolved path {resolved} is outside the temp dir")
    if any(fragment in str(resolved) for fragment in FORBIDDEN_FRAGMENTS):
        raise SystemExit(f"[g-isolation] FAIL: resolved path {resolved} looks like a user database")

    pytest_args = args.pytest_args or ["-q"]
    print(f"[g-isolation] running: {sys.executable} -m pytest {' '.join(pytest_args)}")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *pytest_args],
        cwd=ROOT, env=env,
    )

    after = _digest(DEV_DB)
    print(f"[g-isolation] dev-db after  sha256={after['sha256']} size={after['size']} "
          f"mtime_ns={after['mtime_ns']}")
    if after != before:
        raise SystemExit("[g-isolation] FAIL: development database changed during verification")

    shutil.rmtree(temp_dir, ignore_errors=True)
    busy = _ports_free()
    if busy:
        raise SystemExit(f"[g-isolation] FAIL: ports still busy: {busy}")
    print("[g-isolation] cleanup OK: temp dir removed, ports 8000/8501 free")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
