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
    assert "Intelligent English Writing Feedback Prototype" in test_app.title[0].value


def test_time_limit_is_editable_before_timed_submission(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "ui.db"))
    monkeypatch.setenv("LLM_PROVIDER", "local")
    app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    test_app = AppTest.from_file(str(app_path), default_timeout=15).run()

    time_limit = next(item for item in test_app.number_input if item.label == "Time limit (minutes)")
    assert not time_limit.disabled
    time_limit.set_value(45)
    assert time_limit.value == 45


@pytest.mark.parametrize(
    ("page", "header"),
    [
        (_L("nav_student_progress"), "Student progress evidence"),
        (_L("nav_revision_comparison"), "Revision comparison"),
        (_L("nav_diagnostic_audit"), "Diagnostic calibration audit"),
        (_L("nav_local_administration"), "Local researcher administration"),
    ],
)
def test_v06_streamlit_research_pages_start(monkeypatch, tmp_path, page, header):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "ui.db"))
    monkeypatch.setenv("LLM_PROVIDER", "local")
    app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    test_app = AppTest.from_file(str(app_path), default_timeout=15).run()
    test_app.sidebar.radio[0].set_value(page).run()
    assert not test_app.exception
    assert test_app.header[0].value == header
