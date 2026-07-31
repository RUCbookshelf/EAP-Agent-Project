from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]




def kill_port_processes(port: int) -> int:
    import subprocess as _sp
    killed = 0
    try:
        result = _sp.run(
            ["netstat", "-ano"], capture_output=True, text=True, timeout=5,
        )
        pids_seen = set()
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.strip().split()
                pid = parts[-1]
                if pid.isdigit() and pid not in pids_seen:
                    pids_seen.add(pid)
                    try:
                        _sp.run(["taskkill", "/F", "/PID", pid],
                                capture_output=True, timeout=5)
                        killed += 1
                    except Exception:
                        pass
    except Exception:
        pass
    return killed

def require_free_port(host: str, port: int) -> None:
    with socket.socket() as sock:
        try:
            sock.bind((host, port))
        except OSError as exc:
            raise RuntimeError(f"Required port {host}:{port} is already in use.") from exc


def wait_http(url: str, *, timeout: float = 30.0) -> int:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                return int(response.status)
        except (OSError, URLError) as exc:
            last_error = exc
            time.sleep(0.25)
    raise RuntimeError(f"Timed out waiting for {url}: {type(last_error).__name__}")


def start_api(python: str, host: str, port: int, env: dict[str, str]) -> subprocess.Popen:
    return subprocess.Popen(
        [python, "-m", "uvicorn", "app.api.main:app", "--host", host, "--port", str(port)],
        cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )


def start_streamlit(python: str, port: int, env: dict[str, str]) -> subprocess.Popen:
    return subprocess.Popen(
        [python, "-m", "streamlit", "run", "streamlit_app.py", "--server.headless", "true", "--server.port", str(port)],
        cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )


def stop_process(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
