"""INT wiring tests for the Wave-2 studio/history pages (REPAIR goal).

Verifies the integration steps documented in PDW2-D-UX-STUDENT-20260810.md
against the real Streamlit entry:

1. ``STUDENT_PAGES`` mounts ``student_wave2_studio`` /
   ``student_wave2_history`` with the documented locale keys (resolvable in
   en and zh_CN through the additive Wave-2 locale registration).
2. The app builds ``Wave2Gateway(Wave2ApiClient, WritingFeedbackApiClient,
   mode="auto")`` once per app.
3. Routing: selecting each Wave-2 page in the real entry renders without
   exception; with no Wave-2 namespace present the gateway degrades to
   standard mode (honest notices, no fabricated guided features).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from streamlit.testing.v1 import AppTest

from app.ui.locale import t
from app.ui.api_client import WritingFeedbackApiClient
from app.ui.wave2.client import Wave2ApiClient
from app.ui.wave2.gateway import Wave2Gateway


ROOT = Path(__file__).resolve().parents[2]


def _load_streamlit_app():
    spec = importlib.util.spec_from_file_location(
        "streamlit_app_wave2_wiring",
        ROOT / "app" / "ui" / "streamlit_app.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _boot_app(monkeypatch, tmp_path) -> AppTest:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "ui.db"))
    monkeypatch.setenv("LLM_PROVIDER", "local")
    # No API server: the gateway probe fails closed and the app must degrade.
    monkeypatch.setenv("API_HOST", "127.0.0.1")
    monkeypatch.setenv("API_PORT", "1")
    app_path = ROOT / "streamlit_app.py"
    return AppTest.from_file(str(app_path), default_timeout=30).run()


def test_student_pages_mount_wave2_entries_with_locale_keys():
    streamlit_app = _load_streamlit_app()
    assert streamlit_app.STUDENT_PAGES["student_wave2_studio"] == "student_wave2_studio_title"
    assert streamlit_app.STUDENT_PAGES["student_wave2_history"] == "student_wave2_history_title"
    # Wave-2 locale keys resolve in both languages through the additive
    # runtime registration (frozen locale JSON files untouched).
    assert t("student_wave2_studio_title", "en") == "Writing Studio"
    assert t("student_wave2_studio_title", "zh_CN") == "写作工作室"
    assert t("student_wave2_history_title", "en") == "History & Learning"
    assert t("student_wave2_history_title", "zh_CN") == "历史与学习"


def test_gateway_factory_builds_auto_mode_gateway():
    streamlit_app = _load_streamlit_app()
    gateway = streamlit_app.get_wave2_gateway("http://127.0.0.1:1")
    assert isinstance(gateway, Wave2Gateway)
    assert isinstance(gateway._wave2, Wave2ApiClient)
    assert isinstance(gateway._legacy, WritingFeedbackApiClient)
    assert gateway._mode == "auto"


def test_studio_page_renders_in_real_entry(monkeypatch, tmp_path):
    at = _boot_app(monkeypatch, tmp_path)
    assert not at.exception, at.exception
    radio = next(r for r in at.radio if r.key == "sidebar_page")
    radio.set_value(t("student_wave2_studio_title", "en")).run()
    assert not at.exception, at.exception
    at.text_input(key="wave2_student").set_value("S-W2-001").run()
    assert not at.exception, at.exception
    text = " ".join(m.value for m in at.markdown)
    # With no Wave-2 namespace the gateway degrades to standard mode; the
    # studio start surface still renders (no fabricated guided features).
    assert "Start a new writing task" in text


def test_history_page_renders_in_real_entry(monkeypatch, tmp_path):
    at = _boot_app(monkeypatch, tmp_path)
    assert not at.exception, at.exception
    radio = next(r for r in at.radio if r.key == "sidebar_page")
    radio.set_value(t("student_wave2_history_title", "en")).run()
    assert not at.exception, at.exception
    at.text_input(key="wave2_history_student").set_value("S-W2-001").run()
    assert not at.exception, at.exception
    text = " ".join(m.value for m in at.markdown)
    # Standard-mode history renders the honest notice and an empty state
    # instead of fabricating Wave-2 long-term patterns/learning items.
    assert "Long-term patterns and learning items are part of the guided studio" in text
    assert "No writing stored yet for this learner" in text


def test_other_student_pages_still_render_after_mount(monkeypatch, tmp_path):
    at = _boot_app(monkeypatch, tmp_path)
    assert not at.exception, at.exception
    for page_label in (
        "Home",
        "Writing",
        "Feedback",
        "Revision",
        "Practice",
        "Learning Journey",
    ):
        radio = next(r for r in at.radio if r.key == "sidebar_page")
        radio.set_value(page_label).run()
        assert not at.exception, page_label
