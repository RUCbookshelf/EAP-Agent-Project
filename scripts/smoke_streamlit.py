from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PORT = 8523


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--python", type=Path,
        default=PROJECT_ROOT / ".venv" / "Scripts" / "python.exe",
        help="Python executable whose installed Streamlit should be tested.",
    )
    args = parser.parse_args()
    command = [
        str(args.python.resolve()), "-m", "streamlit", "run",
        "streamlit_app.py", "--server.headless", "true", "--server.port", str(PORT),
        "--browser.gatherUsageStats", "false",
    ]
    process = subprocess.Popen(
        command, cwd=PROJECT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    status = None
    try:
        for _ in range(40):
            if process.poll() is not None:
                break
            try:
                with urlopen(f"http://127.0.0.1:{PORT}", timeout=1) as response:
                    status = response.status
                    if status == 200:
                        break
            except (URLError, TimeoutError):
                time.sleep(0.25)
        if status != 200:
            output = process.stdout.read() if process.stdout else ""
            raise RuntimeError(f"Streamlit startup failed. Output: {output[-2000:]}")
        print(json.dumps({
            "http_status": status, "port": PORT, "startup": "PASS",
            "python": str(args.python.resolve()),
        }, indent=2))
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    main()
