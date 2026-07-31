from __future__ import annotations

import os

from app.config import load_settings
import json
import time
from urllib.request import urlopen
from scripts.service_processes import kill_port_processes, require_free_port, start_api, start_streamlit, stop_process, wait_http


def main() -> None:
    settings = load_settings()
    # Kill any stale processes from a previous session
    killed_api = kill_port_processes(settings.api_port)
    killed_ui = kill_port_processes(settings.streamlit_port)
    if killed_api or killed_ui:
        print(f"Cleaned up stale processes: API={killed_api}, Streamlit={killed_ui}")

    require_free_port(settings.api_host, settings.api_port)
    require_free_port("127.0.0.1", settings.streamlit_port)
    env = os.environ.copy()
    env["API_BASE_URL"] = settings.api_base_url
    api = ui = None
    try:
        api = start_api(os.sys.executable, settings.api_host, settings.api_port, env)

        # Wait for liveness first (confirms process is alive)
        live_url = f"{settings.api_base_url}/api/v1/system/live"
        wait_http(live_url, timeout=15.0)
        print(f"FastAPI process alive: {settings.api_base_url}")

        # Poll readiness with bounded retries
        ready_url = f"{settings.api_base_url}/api/v1/system/ready"
        deadline = time.monotonic() + 60.0
        last_state = "unknown"
        while time.monotonic() < deadline:
            try:
                with urlopen(ready_url, timeout=2) as resp:
                    data = json.loads(resp.read())
                    current_state = data.get("status", "unknown")
                    if current_state != last_state:
                        print(f"API state: {current_state}")
                        last_state = current_state
                    if data.get("ready"):
                        print(f"FastAPI ready:   {settings.api_base_url}")
                        break
            except Exception:
                pass
            time.sleep(0.5)
        else:
            print(f"WARNING: API did not become ready within 60s (last state: {last_state})")
            print("Starting Streamlit anyway — it will show the current state.")

        print(f"API docs:  {settings.api_base_url}/docs")
        print(f"Streamlit: http://127.0.0.1:{settings.streamlit_port}")
        ui = start_streamlit(os.sys.executable, settings.streamlit_port, env)
        wait_http(f"http://127.0.0.1:{settings.streamlit_port}")
        ui.wait()
        if ui.returncode:
            raise SystemExit(ui.returncode)
    except KeyboardInterrupt:
        pass
    finally:
        stop_process(ui)
        stop_process(api)


if __name__ == "__main__":
    main()
