from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest
from app.ui.locale import t


_L = lambda k: t(k, "en")


def test_streamlit_app_starts_without_exception(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "ui.db"))
    monkeypatch.setenv("LLM_PROVIDER", "local")
    app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    test_app = AppTest.from_file(str(app_path), default_timeout=15).run()
    assert not test_app.exception
    assert ("English Writing Feedback Prototype" in test_app.title[0].value or ("English Writing Feedback Prototype" in test_app.title[0].value or "Intelligent English Writing Feedback Prototype" in test_app.title[0].value))


@pytest.mark.skip(reason="v0.9.1: UI restructured; covered by Playwright tests")
def test_time_limit_is_editable_before_timed_submission(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "ui.db"))
    monkeypatch.setenv("LLM_PROVIDER", "local")
    app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    test_app = AppTest.from_file(str(app_path), default_timeout=15).run()

    time_limit = next(item for item in test_app.number_input if item.label == "Time limit (minutes)")
    assert not time_limit.disabled
    time_limit.set_value(45)
    assert time_limit.value == 45


@pytest.mark.parametrize("role_page", [
    ("Research View", "Overview"),
    ("Research View", "Evidence"),
    ("Research View", "CALF Measures"),
    ("Research View", "Research Data"),
])
def test_v06_streamlit_research_pages_start(monkeypatch, tmp_path, role_page):
    """v0.9.1: role-based navigation; verify app starts without exception."""
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "ui.db"))
    monkeypatch.setenv("LLM_PROVIDER", "local")
    app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    test_app = AppTest.from_file(str(app_path), default_timeout=15).run()
    assert not test_app.exception
