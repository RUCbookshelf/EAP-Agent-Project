from __future__ import annotations

import os

from app.config import load_settings
from scripts.service_processes import require_free_port, start_api, start_streamlit, stop_process, wait_http


def main() -> None:
    settings = load_settings()
    require_free_port(settings.api_host, settings.api_port)
    require_free_port("127.0.0.1", settings.streamlit_port)
    env = os.environ.copy()
    env["API_BASE_URL"] = settings.api_base_url
    api = ui = None
    try:
        api = start_api(os.sys.executable, settings.api_host, settings.api_port, env)
        wait_http(f"{settings.api_base_url}/api/v1/system/health")
        print(f"FastAPI:   {settings.api_base_url}")
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
