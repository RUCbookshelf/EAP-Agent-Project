from __future__ import annotations

import argparse
import json
import os

from app.config import load_settings
from scripts.service_processes import require_free_port, start_api, start_streamlit, stop_process, wait_http


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", default=os.sys.executable)
    args = parser.parse_args()
    settings = load_settings()
    require_free_port(settings.api_host, settings.api_port)
    require_free_port("127.0.0.1", settings.streamlit_port)
    env = os.environ.copy()
    env["API_BASE_URL"] = settings.api_base_url
    api = ui = None
    try:
        api = start_api(args.python, settings.api_host, settings.api_port, env)
        health = wait_http(f"{settings.api_base_url}/api/v1/system/health")
        docs = wait_http(f"{settings.api_base_url}/docs")
        ui = start_streamlit(args.python, settings.streamlit_port, env)
        streamlit = wait_http(f"http://127.0.0.1:{settings.streamlit_port}")
        print(json.dumps({"status": "PASS", "health": health, "docs": docs, "streamlit": streamlit,
                          "api_port": settings.api_port, "streamlit_port": settings.streamlit_port}, indent=2))
    finally:
        stop_process(ui)
        stop_process(api)


if __name__ == "__main__":
    main()
