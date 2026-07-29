from __future__ import annotations

import os
import socket
from pathlib import Path

from streamlit.testing.v1 import AppTest

from scripts.service_processes import start_api, stop_process, wait_http


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_streamlit_submission_completes_through_http_api(monkeypatch, tmp_path):
    port = free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.update({
        "LLM_PROVIDER": "local",
        "DATABASE_URL": f"sqlite:///{(tmp_path / 'ui_api.db').as_posix()}",
        "API_HOST": "127.0.0.1",
        "API_PORT": str(port),
        "API_BASE_URL": base_url,
        "WRITING_FEEDBACK_ENV_FILE": str(tmp_path / "absent.env"),
    })
    api = start_api(os.sys.executable, "127.0.0.1", port, env)
    try:
        assert wait_http(f"{base_url}/api/v1/system/health") == 200
        monkeypatch.setenv("API_BASE_URL", base_url)
        monkeypatch.setenv("WRITING_FEEDBACK_ENV_FILE", str(tmp_path / "absent.env"))
        app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
        app = AppTest.from_file(str(app_path), default_timeout=30).run()
        app.text_input[0].input("UIAPI001")
        app.text_input[1].input("none")
        app.text_area[0].input("Should cities preserve public parks?")
        app.text_area[1].input(
            "Cities should preserve parks because residents need green space. "
            "Therefore, local plans should protect accessible public parks."
        )
        app.button[0].click().run(timeout=30)
        assert not app.exception
        assert any("Submission saved as essay" in item.value for item in app.success)
        assert any("Provider: local-demo" in item.value for item in app.caption)
    finally:
        stop_process(api)
