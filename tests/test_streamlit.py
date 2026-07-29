from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_app_starts_without_exception(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "ui.db"))
    monkeypatch.setenv("LLM_PROVIDER", "local")
    app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    test_app = AppTest.from_file(str(app_path), default_timeout=15).run()
    assert not test_app.exception
    assert test_app.title[0].value == "Intelligent English Writing Feedback Prototype v0.3"
