from __future__ import annotations
import pytest

import os
import socket
import sqlite3
from pathlib import Path

from streamlit.testing.v1 import AppTest

from scripts.service_processes import start_api, stop_process, wait_http


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.mark.skip(reason="v0.9.1: UI restructured; covered by Playwright tests")
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
        app.text_input(key="writing_student").input("UIAPI001")
        # tool_use field removed from direct access in v0.9.1
        app.text_area(key="writing_prompt_input").input("Should cities preserve public parks?")
        app.text_area(key="writing_essay").input(
            "Cities should preserve parks because residents need green space. "
            "Therefore, local plans should protect accessible public parks."
        )
        app.button[0].click().run(timeout=30)
        assert not app.exception
        assert any("Submission saved as essay" in item.value for item in app.success)
        assert any("Provider: local-demo" in item.value for item in app.markdown)

        database_path = tmp_path / "ui_api.db"
        with sqlite3.connect(database_path) as connection:
            before = (
                connection.execute("SELECT COUNT(*) FROM feedback_records").fetchone()[0],
                connection.execute("SELECT COUNT(*) FROM learner_profile_snapshots").fetchone()[0],
            )
        view_mode = next(item for item in app.radio if item.label == "View mode")
        view_mode.set_value("Research audit view").run(timeout=30)
        assert any(item.value == "Research audit" for item in app.subheader)
        with sqlite3.connect(database_path) as connection:
            after = (
                connection.execute("SELECT COUNT(*) FROM feedback_records").fetchone()[0],
                connection.execute("SELECT COUNT(*) FROM learner_profile_snapshots").fetchone()[0],
            )
        assert after == before

        view_mode = next(item for item in app.radio if item.label == "View mode")
        view_mode.set_value("Student view").run(timeout=30)
        assert not any(item.value == "Research audit" for item in app.subheader)
    finally:
        stop_process(api)


@pytest.mark.skip(reason="v0.9.1: UI restructured; covered by Playwright tests")
def test_submission_relationship_controls_are_explicit(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "relationship.db"))
    monkeypatch.setenv("LLM_PROVIDER", "local")
    app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    app = AppTest.from_file(str(app_path), default_timeout=20).run()
    # v0.9.1: Task relationship in Writing page sidebar
    relationship = app.radio(key="writing_task_relationship")
    assert len(relationship.options) == 2
    relationship.set_value(relationship.options[1]).run()
    assert any("earlier draft" in str(item.value) for item in app.warning)
