"""v0.9.5-C feature-extraction compatibility tests (updated for v0.9.5-D).

Pins the old import paths, render-function signatures, page order, facade
thinness, and locale-key integrity after the frontend feature extraction.
v0.9.5-D narrowed renderer API-client annotations to feature Ports; the
signature expectations below reflect that intentional type-only change
(parameter names, order, defaults, and call behavior are unchanged).
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
import re
from pathlib import Path

from app.ui.locale import load_locale
from app.ui.pages import student_pages, research_pages


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_FEATURES_ROOT = PROJECT_ROOT / "app" / "ui" / "features"


def _load_streamlit_app():
    """Load the real Streamlit entry point (app/ui/streamlit_app.py) by path."""
    spec = importlib.util.spec_from_file_location(
        "streamlit_app_v095c", PROJECT_ROOT / "app" / "ui" / "streamlit_app.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_old_import_style_still_works():
    from app.ui.pages.student_pages import (  # noqa: F401
        render_feedback_content,
        render_feedback_page,
        render_learning_journey_page,
        render_practice_page,
        render_revision_page,
        render_student_home,
        render_writing_page,
    )
    from app.ui.pages.research_pages import (  # noqa: F401
        render_research_calf,
        render_research_data,
        render_research_evidence,
        render_research_learning_process,
        render_research_overview,
        render_research_system_audit,
    )


def test_private_helpers_remain_importable_from_facade():
    """Explicit compatibility-resolution test (v0.9.5-D allow-list).

    Private-helper imports through the legacy facades are deprecated for new
    code; this test is the documented exception that pins their continued
    availability.
    """
    from app.ui.pages.student_pages import (  # noqa: F401
        _feedback_category_label,
        _home_action_contract,
        _journey_action_contract,
        _journey_description_params,
        _journey_evidence_label,
        _journey_source_label,
        _practice_constraint_label,
        _practice_instruction,
        _practice_status_label,
        _revision_observation_text,
        _revision_saved_for_source,
        _revision_status_label,
        _short_timestamp,
        _writing_saved_for_learner,
    )


# Signatures are stringified because the modules use `from __future__ import
# annotations`; v0.9.5-D narrowed the api_client annotation to feature Ports
# (type-only change; parameter names/order/defaults unchanged).
STUDENT_RENDERERS = {
    "render_student_home": "(api_client: 'StudentHomeApiPort', lang: 'str') -> 'None'",
    "render_writing_page": "(api_client: 'StudentWritingApiPort', lang: 'str') -> 'None'",
    "render_feedback_content": "(result: 'dict', api_client: 'StudentFeedbackApiPort', lang: 'str') -> 'None'",
    "render_feedback_page": "(api_client: 'StudentFeedbackApiPort', lang: 'str') -> 'None'",
    "render_revision_page": "(api_client: 'StudentRevisionApiPort', lang: 'str') -> 'None'",
    "render_practice_page": "(api_client: 'StudentPracticeApiPort', lang: 'str') -> 'None'",
    "render_learning_journey_page": "(api_client: 'StudentJourneyApiPort', lang: 'str') -> 'None'",
}

RESEARCH_RENDERERS = {
    "render_research_overview": "(api_client: 'ResearchOverviewApiPort', lang: 'str') -> 'None'",
    "render_research_evidence": "(api_client: 'ResearchEvidenceApiPort', lang: 'str') -> 'None'",
    "render_research_calf": "(api_client: 'ResearchCalfApiPort', lang: 'str') -> 'None'",
    "render_research_learning_process": "(api_client: 'ResearchLearningProcessApiPort', lang: 'str') -> 'None'",
    "render_research_data": "(api_client: 'ResearchDataApiPort', lang: 'str') -> 'None'",
    "render_research_system_audit": "(api_client: 'ResearchSystemAuditApiPort', lang: 'str') -> 'None'",
}


def test_render_function_signatures_are_unchanged():
    for name, expected in STUDENT_RENDERERS.items():
        assert str(inspect.signature(getattr(student_pages, name))) == expected, name
    for name, expected in RESEARCH_RENDERERS.items():
        assert str(inspect.signature(getattr(research_pages, name))) == expected, name


def test_page_order_and_navigation_contract():
    streamlit_app = _load_streamlit_app()
    assert list(streamlit_app.STUDENT_PAGES) == [
        "student_home",
        "student_writing",
        "student_feedback",
        "student_revision",
        "student_practice",
        "student_journey",
        "student_adaptive",
        "student_wave2_studio",
        "student_wave2_history",
    ]
    assert list(streamlit_app.RESEARCH_PAGES) == [
        "research_overview",
        "research_evidence",
        "research_calf",
        "research_learning",
        "research_data",
        "research_audit",
    ]


def test_facades_are_thin_re_export_modules():
    for module in (student_pages, research_pages):
        source = inspect.getsource(module)
        assert "def render_" not in source, "facade must not define renderers"
        assert "st." not in source, "facade must not call streamlit"
        assert "api_client." not in source, "facade must not call the API client"
        assert "import *" not in source
        assert "__all__" in source


def test_each_visible_page_has_one_owning_feature_module():
    expected_modules = {
        "render_student_home": ("student", "home.py"),
        "render_writing_page": ("student", "writing.py"),
        "render_feedback_page": ("student", "feedback.py"),
        "render_feedback_content": ("student", "feedback.py"),
        "render_revision_page": ("student", "revision.py"),
        "render_practice_page": ("student", "practice.py"),
        "render_learning_journey_page": ("student", "journey.py"),
        "render_research_overview": ("research", "overview.py"),
        "render_research_evidence": ("research", "evidence.py"),
        "render_research_calf": ("research", "calf.py"),
        "render_research_learning_process": ("research", "learning_process.py"),
        "render_research_data": ("research", "data.py"),
        "render_research_system_audit": ("research", "system_audit.py"),
    }
    for name, (role, filename) in expected_modules.items():
        module_file = UI_FEATURES_ROOT / role / filename
        assert module_file.is_file(), module_file
        assert name in module_file.read_text(encoding="utf-8"), name


def test_feature_locale_keys_resolve_and_parity_holds():
    en = load_locale("en")
    zh = load_locale("zh_CN")
    assert set(en) == set(zh), "locale parity must stay 520/520"
    key_re = re.compile(r'\bt\("([^"]+)"')
    used: set[str] = set()
    for path in UI_FEATURES_ROOT.rglob("*.py"):
        used.update(key_re.findall(path.read_text(encoding="utf-8")))
    unresolved = sorted(key for key in used if key not in en)
    assert unresolved == [], f"feature modules reference unknown locale keys: {unresolved}"


def test_import_graph_has_no_pages_features_cycle():
    # The facades import features; features never import app.ui.pages.
    for path in UI_FEATURES_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("app.ui.pages"), f"cycle risk in {path}"
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("app.ui.pages"), f"cycle risk in {path}"
