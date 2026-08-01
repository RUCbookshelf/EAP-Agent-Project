"""v0.9.4-A shared component primitive tests.

Uses structural/stable-semantic assertions (data-testid, role attributes)
and the pure validation helper; exact localized sentences are asserted
only in the dedicated localization contract tests.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st
import pytest
from streamlit.testing.v1 import AppTest

from app.ui import components as c
from app.ui.locale import t


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def captured_markdown(monkeypatch):
    """Capture st.markdown output for pure-HTML primitives."""
    captured: list[str] = []

    def fake_markdown(body: str, unsafe_allow_html: bool = False) -> None:
        captured.append(body)

    monkeypatch.setattr(st, "markdown", fake_markdown)
    return captured


class TestFieldError:
    def test_renders_stable_testid_and_role(self, captured_markdown):
        c.field_error("student_writing_need_prompt", "en")
        html = captured_markdown[-1]
        assert 'data-testid="px-field-error"' in html
        assert 'role="alert"' in html
        assert t("student_writing_need_prompt", "en") in html

    def test_localizes(self, captured_markdown):
        c.field_error("student_writing_need_prompt", "zh_CN")
        assert t("student_writing_need_prompt", "zh_CN") in captured_markdown[-1]

    def test_contains_accessible_icon(self, captured_markdown):
        c.field_error("student_writing_need_prompt", "en")
        assert 'aria-label="Validation error"' in captured_markdown[-1]


class TestLoadingBox:
    def test_renders_stable_testid_and_status(self, captured_markdown):
        c.loading_box("loading_research_export", "en")
        html = captured_markdown[-1]
        assert 'data-testid="px-loading"' in html
        assert 'role="status"' in html
        assert 'aria-live="polite"' in html
        assert t("loading_research_export", "en") in html

    def test_no_animation_markup(self, captured_markdown):
        c.loading_box("loading_research_export", "en")
        assert "animation" not in captured_markdown[-1]
        assert "spinner" not in captured_markdown[-1].lower()


class TestDataTable:
    def test_renders_escaped_table(self, captured_markdown):
        c.data_table(
            ["Record", "Count"],
            [["<script>alert(1)</script>", 3], ["submissions", 10]],
        )
        html = captured_markdown[-1]
        assert 'data-testid="px-table-wrap"' in html
        assert 'data-testid="px-table"' in html
        assert "&lt;script&gt;" in html
        assert "<script>" not in html

    def test_research_density_attribute(self, captured_markdown):
        c.data_table(["A"], [["1"]])
        assert 'data-density="research"' in captured_markdown[-1]


class TestTechnicalCaption:
    def test_mono_role(self, captured_markdown):
        c.technical_caption("Essay #12 | final")
        html = captured_markdown[-1]
        assert 'data-testid="px-mono"' in html
        assert "Essay #12 | final" in html


class TestValidateWritingForm:
    def test_empty_prompt_is_blocked(self):
        errors = c.validate_writing_form("S02", "   ", "some essay")
        assert "student_writing_need_prompt" in errors

    def test_missing_id_and_essay(self):
        errors = c.validate_writing_form("", "prompt", "")
        assert "student_writing_need_id" in errors
        assert "student_writing_need_text" in errors
        assert "student_writing_need_prompt" not in errors

    def test_revision_requires_selection(self):
        errors = c.validate_writing_form(
            "S02", "prompt", "essay", is_revision=True, revision_of_submission_id=None
        )
        assert "submission_choose_revision" in errors

    def test_valid_form_passes(self):
        assert c.validate_writing_form(
            "S02", "prompt", "essay", is_revision=True, revision_of_submission_id=3
        ) == []


class TestStatusBadge:
    def test_error_state_uses_semantic_error_tokens(self, captured_markdown):
        c.status_badge("failed", "en")
        html = captured_markdown[-1]
        assert 'data-testid="px-status-badge"' in html
        assert "var(--px-status-error)" in html
        assert "var(--px-status-on-error)" in html

    def test_warning_state_uses_warning_tokens(self, captured_markdown):
        c.status_badge("pending", "en")
        html = captured_markdown[-1]
        assert "var(--px-status-warning)" in html


class TestNoticeVariants:
    @pytest.mark.parametrize(
        "renderer,icon_name",
        [
            (c.warning_box, "warning"),
            (c.error_box, "error"),
            (c.info_box, "info"),
            (c.success_box, "check"),
            (c.limitation_notice, "info"),
        ],
    )
    def test_variants_have_testid_and_icon(self, captured_markdown, renderer, icon_name):
        renderer("app_prototype_warning", "en")
        html = captured_markdown[-1]
        assert 'data-testid="px-notice"' in html
        assert "px-icon" in html


class TestWritingPageValidationAppTest:
    def test_empty_prompt_is_blocked_with_field_error(self, monkeypatch, tmp_path):
        monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "ui.db"))
        monkeypatch.setenv("LLM_PROVIDER", "local")
        app_path = PROJECT_ROOT / "streamlit_app.py"
        test_app = AppTest.from_file(str(app_path), default_timeout=20).run()
        assert not test_app.exception

        # Navigate to the Writing page.
        pages_radio = next(r for r in test_app.radio if r.key == "sidebar_page")
        pages_radio.set_value("Writing").run()
        assert not test_app.exception

        # Fill Student ID and essay text but leave the prompt empty.
        test_app.text_input[0].set_value("S02")
        test_app.text_area[1].set_value("This is an essay body.")
        test_app.button[0].click().run()

        assert not test_app.exception
        markdown_values = [md.value for md in test_app.markdown]
        assert any("px-field-error" in value for value in markdown_values)


class TestRepresentativePagesAppTest:
    """AppTest is used only where real Streamlit behavior is required; the
    twelve pages are covered with two app boots instead of twelve."""

    def _boot(self, monkeypatch, tmp_path) -> AppTest:
        monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "ui.db"))
        monkeypatch.setenv("LLM_PROVIDER", "local")
        app_path = PROJECT_ROOT / "streamlit_app.py"
        return AppTest.from_file(str(app_path), default_timeout=20).run()

    def test_all_student_pages_render(self, monkeypatch, tmp_path):
        test_app = self._boot(monkeypatch, tmp_path)
        assert not test_app.exception
        for page_label in ["Home", "Writing", "Feedback", "Revision", "Practice", "Learning Journey"]:
            next(r for r in test_app.radio if r.key == "sidebar_page").set_value(page_label).run()
            assert not test_app.exception, page_label

    def test_all_research_pages_render(self, monkeypatch, tmp_path):
        test_app = self._boot(monkeypatch, tmp_path)
        assert not test_app.exception
        role_radio = next(r for r in test_app.radio if r.key == "sidebar_role")
        role_radio.set_value("Research View").run()
        assert not test_app.exception
        for page_label in [
            "Research Overview", "Research Evidence", "CALF Measures",
            "Learning Process", "Research Data", "System Audit",
        ]:
            next(r for r in test_app.radio if r.key == "sidebar_page").set_value(page_label).run()
            assert not test_app.exception, page_label
