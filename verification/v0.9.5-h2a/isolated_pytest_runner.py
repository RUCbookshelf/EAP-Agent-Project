"""v0.9.5-H2A isolated pytest runner.

Same database-isolation safeguards as F5B..G runners:
- PYTHON_DOTENV_DISABLED=1, DATABASE_URL removed from the environment,
  DATABASE_PATH set to a fresh path inside a unique temporary directory,
  LLM_PROVIDER=local;
- resolved settings.database_path is printed and asserted to be inside the
  temporary directory (never the development database);
- the development database SHA-256, size, and mtime are recorded before and
  after the run and must not change;
- ports 8000/8501 are checked free before the run;
- the temporary directory and pytest cache are removed afterwards.

Usage:
    python verification/v0.9.5-h2a/isolated_pytest_runner.py [--full] [--targets f1 f2 ...]
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
PORTS = (8000, 8501)

DEFAULT_TARGETS = [
    "tests/test_v095f2_service_narrowing.py",
    "tests/test_v095f3_learner_read_model_narrowing.py",
    "tests/test_v095f4_reanalysis_journey_narrowing.py",
    "tests/test_v095f5a_calf_service_narrowing.py",
    "tests/test_v095f5b_research_service_narrowing.py",
    "tests/test_v095f6a0_revision_capability_completion.py",
    "tests/test_v095f6a_revision_runtime_narrowing.py",
    "tests/test_v095f6b_admin_reanalysis_narrowing.py",
    "tests/test_v095f6c_submission_service_narrowing.py",
    "tests/test_v095f6d_practice_boundary_narrowing.py",
    "tests/test_v095e_repository_modularization.py",
    "tests/test_v095g_facade_contraction.py",
    "tests/test_v095h2a_removed_contracts.py",
]

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


def digest(path: Path) -> dict[str, object]:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    stat = path.stat()
    return {
        "sha256": hasher.hexdigest().upper(),
        "size": stat.st_size,
        "mtime": stat.st_mtime,
    }


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="run the full non-live core suite")
    parser.add_argument("--targets", nargs="*", default=None, help="pytest target files")
    args = parser.parse_args()

    for port in PORTS:
        if not port_free(port):
            print(f"[h2a-isolation] FAIL: port {port} is busy")
            return 2

    before = digest(DEV_DB)
    print(f"[h2a-isolation] dev db before: {before}")

    tmp = Path(tempfile.mkdtemp(prefix="v095h2a-"))
    db_path = tmp / "h2a.db"
    env = dict(os.environ)
    env["PYTHON_DOTENV_DISABLED"] = "1"
    env.pop("DATABASE_URL", None)
    env["DATABASE_PATH"] = str(db_path)
    env["LLM_PROVIDER"] = "local"
    env["SERVICE_API_DIFF_ALLOWLIST"] = G_ALLOWLIST

    resolved = subprocess.run(
        [sys.executable, "-c", "from app.config import load_settings; print(load_settings().database_path)"],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )
    resolved_path = resolved.stdout.strip()
    print(f"[h2a-isolation] resolved settings.database_path = {resolved_path}")
    if resolved.returncode != 0 or not resolved_path.startswith(str(tmp)):
        print("[h2a-isolation] FAIL: resolved database path not inside temp dir")
        return 2
    if str(DEV_DB.resolve()) in resolved_path or "writing_feedback.db" in resolved_path:
        print("[h2a-isolation] FAIL: resolved path looks like the development database")
        return 2

    targets = ["--ignore=tests/live", "tests"] if args.full else (args.targets or DEFAULT_TARGETS)
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *targets]
    print(f"[h2a-isolation] running: {' '.join(command)}")
    result = subprocess.run(command, cwd=ROOT, env=env)

    after = digest(DEV_DB)
    print(f"[h2a-isolation] dev db after: {after}")
    if before != after:
        print("[h2a-isolation] FAIL: development database changed during verification")
        return 2

    shutil.rmtree(tmp, ignore_errors=True)
    cache = ROOT / ".pytest_cache"
    if cache.exists():
        shutil.rmtree(cache, ignore_errors=True)
    for port in PORTS:
        if not port_free(port):
            print(f"[h2a-isolation] FAIL: port {port} busy after run")
            return 2
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
