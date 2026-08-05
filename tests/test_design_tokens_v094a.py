"""v0.9.4-A Hybrid Pixel System foundation tests.

Covers the canonical token contract, generated CSS, measured contrast,
selector policy, typography contract, icon policy, theme parity, and
UTF-8/locale foundations.

The authoritative browser matrix (48 renders, computed styles, touch
targets) is executed separately in Phase 7; these tests are the fast
foundation layer.
"""

from __future__ import annotations

import json
import pathlib
import re
import tomllib

import pytest

from app.ui import pixel_art as pa


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]


# ── WCAG 2.1 relative-luminance helpers ────────────────────────────────

def _channel(value: float) -> float:
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(fg: str, bg: str) -> float:
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def token(path: str) -> str:
    node: object = pa.DESIGN_TOKENS
    for part in path.split("."):
        node = node[part]  # type: ignore[index]
    return str(node)


@pytest.fixture(scope="module")
def css() -> str:
    return pa.PIXEL_CSS + pa.PIXEL_COMPONENT_CSS


@pytest.fixture(scope="module")
def css_vars() -> dict[str, str]:
    return pa.build_css_vars()


# ── 1. Canonical token source ──────────────────────────────────────────

class TestCanonicalTokenSource:
    def test_design_tokens_is_the_single_source(self):
        assert pa.DESIGN_TOKENS["version"].startswith("hybrid-pixel-system-2.0")
        # Generated CSS must be derived from the token contract.
        assert pa.PIXEL_CSS == pa.build_pixel_css()
        assert pa.PIXEL_COMPONENT_CSS == pa.build_component_css()

    def test_no_second_token_map_in_ui_modules(self):
        """Pages and components must reference tokens, not literal values."""
        for relative in (
            "app/ui/components.py",
            "app/ui/pages/student_pages.py",
            "app/ui/pages/research_pages.py",
            "app/ui/streamlit_app.py",
        ):
            text = (PROJECT_ROOT / relative).read_text(encoding="utf-8")
            assert not re.search(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", text), relative
            assert "linear-gradient" not in text, relative

    def test_no_duplicate_conflicting_token_declarations(self):
        vars_map = pa.build_css_vars()
        assert len(vars_map) == len(set(vars_map))
        # Each custom property appears exactly once in the :root block.
        root = pa.build_root_css()
        for name in ("--px-action", "--px-font-body", "--px-space-4"):
            assert root.count(f"{name}:") == 1


# ── 2. Required token inventory ────────────────────────────────────────

class TestTokenInventory:
    REQUIRED = [
        # foundational colors
        "--px-bg", "--px-surface", "--px-surface-elevated", "--px-text",
        "--px-text-secondary", "--px-muted", "--px-border", "--px-focus",
        "--px-border-subtle", "--px-destructive",
        "--px-action", "--px-action-hover", "--px-action-active",
        "--px-action-disabled", "--px-action-text",
        "--px-action-text-disabled", "--px-secondary-action", "--px-link",
        "--px-red",
        # semantic states
        "--px-status-success", "--px-status-warning", "--px-status-error",
        "--px-status-info", "--px-status-unavailable",
        "--px-status-candidate", "--px-status-insufficient",
        "--px-status-selected", "--px-status-neutral",
        "--px-status-on-success", "--px-status-on-warning",
        "--px-status-on-error", "--px-status-on-info",
        "--px-status-on-unavailable", "--px-status-on-insufficient",
        "--px-status-on-neutral",
        "--px-status-accent-success", "--px-status-accent-warning",
        "--px-status-accent-error", "--px-status-accent-info",
        "--px-status-accent-unavailable", "--px-status-accent-insufficient",
        "--px-status-accent-neutral",
        # typography
        "--px-font-body", "--px-font-display", "--px-font-mono",
        "--px-font-heading", "--px-font-size-card-title",
        "--px-font-weight-semibold",
        "--px-font-size-h1", "--px-font-size-h2", "--px-font-size-h3",
        "--px-font-size-body", "--px-font-size-compact",
        "--px-font-size-label", "--px-font-size-metric",
        "--px-line-height-body", "--px-line-height-compact",
        # spacing
        "--px-space-1", "--px-space-2", "--px-space-3", "--px-space-4",
        "--px-space-5", "--px-space-6", "--px-space-8", "--px-space-10",
        "--px-space-12", "--px-inline-gap", "--px-control-gap",
        "--px-card-pad", "--px-section-space", "--px-page-space",
        # geometry
        "--px-border-thick", "--px-border-thin", "--px-border-hairline",
        "--px-radius", "--px-focus-width", "--px-focus-offset",
        "--px-shadow-sm", "--px-shadow-md", "--px-shadow-lg",
        "--px-control-height", "--px-control-height-mobile",
        "--px-touch-target", "--px-content-width-student",
        "--px-content-width-research", "--px-table-font-size",
        "--px-table-cell-pad",
        "--px-icon-sm", "--px-icon-md", "--px-icon-lg",
        # density + responsive + motion
        "--px-density-student-section", "--px-density-research-section",
        "--px-density-student-card-pad", "--px-density-research-card-pad",
        "--px-bp-mobile", "--px-bp-tablet", "--px-transition",
        "--px-animation",
    ]

    def test_required_tokens_present(self, css_vars):
        missing = [name for name in self.REQUIRED if name not in css_vars]
        assert missing == []

    def test_semantic_state_values(self):
        assert token("colors.action") == "#e00047"
        assert token("colors.pixel-red") == "#ff004d"
        # v0.9.7-D: quiet tint fills + accent bars; action red is reserved
        # for forward actions only.
        assert token("semantic.error") == "#fdeaef"
        assert token("semantic.accent-error") == "#c01048"
        assert token("colors.border-subtle") == "#8a8a9c"
        assert token("colors.destructive") == "#a30d3d"


# ── 3. CSS generation ──────────────────────────────────────────────────

class TestCssGeneration:
    def test_css_is_valid_and_balanced(self, css):
        assert css.count("{") == css.count("}")
        assert ":root {" in css
        assert css.rstrip().endswith("</style>")

    def test_all_css_vars_are_defined(self, css, css_vars):
        used = set(re.findall(r"var\((--px-[a-z0-9-]+)\)", css))
        undefined = used - set(css_vars)
        assert undefined == set()

    def test_no_gradient(self, css):
        assert "linear-gradient" not in css
        assert "radial-gradient" not in css
        assert "conic-gradient" not in css

    def test_no_blur_or_glassmorphism(self, css):
        assert "blur(" not in css
        assert "backdrop-filter" not in css
        # No semi-transparent decorative surfaces.
        assert "rgba(" not in css
        assert "hsla(" not in css

    def test_no_soft_shadow(self, css):
        for match in re.finditer(r"box-shadow\s*:\s*([^;}]+)", css):
            value = match.group(1).strip()
            # A third length (blur radius) or alpha means a soft shadow.
            assert not re.search(r"\d+px\s+\d+px\s+\d+px", value), value
            assert "rgba" not in value, value

    def test_no_nonzero_transition_or_animation(self, css):
        assert "@keyframes" not in css
        assert re.search(r"animation\s*:\s*none", css)
        assert re.search(r"transition\s*:\s*none", css)
        assert "transition-duration" not in css
        assert "animation-duration" not in css

    def test_square_corner_policy(self, css, css_vars):
        assert css_vars["--px-radius"] == "0px"
        values = re.findall(r"border-radius\s*:\s*([^;}]+)", css)
        assert values
        for value in values:
            clean = value.strip().removesuffix("!important").strip()
            assert clean in ("0", "0px", "var(--px-radius)"), clean

    def test_hard_shadow_policy(self, css_vars):
        for name in ("--px-shadow-sm", "--px-shadow-md", "--px-shadow-lg"):
            value = css_vars[name]
            assert value.endswith("0 #1a1c2c")
            assert "blur" not in value

    def test_geometry_values(self, css_vars):
        assert css_vars["--px-touch-target"] == "44px"
        assert css_vars["--px-control-height"] == "40px"
        assert css_vars["--px-control-height-mobile"] == "44px"
        assert css_vars["--px-focus-width"] == "3px"
        assert css_vars["--px-focus-offset"] == "2px"

    def test_spacing_scale(self, css_vars):
        expected = {
            "--px-space-1": "4px", "--px-space-2": "8px", "--px-space-3": "12px",
            "--px-space-4": "16px", "--px-space-5": "20px", "--px-space-6": "24px",
            "--px-space-8": "32px", "--px-space-10": "40px", "--px-space-12": "48px",
        }
        for name, value in expected.items():
            assert css_vars[name] == value

    def test_density_aliases(self, css_vars):
        assert css_vars["--px-density-student-section"] == "var(--px-space-8)"
        assert css_vars["--px-density-research-section"] == "var(--px-space-4)"
        assert css_vars["--px-density-student-card-pad"] == "var(--px-space-5)"
        assert css_vars["--px-density-research-card-pad"] == "var(--px-space-3)"

    def test_responsive_aliases(self, css_vars):
        assert css_vars["--px-bp-mobile"] == "640px"
        assert css_vars["--px-bp-tablet"] == "1024px"

    def test_mobile_touch_target_rule(self, css):
        mobile_block = css.split("@media (max-width: 640px)")[1]
        assert "min-height: var(--px-touch-target)" in mobile_block

    def test_motion_disabled_and_reduced_motion(self, css):
        assert "prefers-reduced-motion" in css
        assert "transition: none !important" in css
        assert "animation: none !important" in css


# ── 4. Measured contrast ───────────────────────────────────────────────

class TestContrast:
    def test_primary_normal(self):
        assert contrast(token("colors.action-text"), token("colors.action")) >= 4.5

    def test_primary_hover(self):
        assert contrast(token("colors.action-text"), token("colors.action-hover")) >= 4.5

    def test_primary_active(self):
        assert contrast(token("colors.action-text"), token("colors.action-active")) >= 4.5

    def test_body_text(self):
        assert contrast(token("colors.text"), token("colors.white")) >= 4.5
        assert contrast(token("colors.text"), token("colors.bg")) >= 4.5

    def test_secondary_and_muted_text(self):
        assert contrast(token("colors.text-secondary"), token("colors.white")) >= 4.5
        assert contrast(token("colors.muted"), token("colors.white")) >= 4.5
        assert contrast(token("colors.muted"), token("colors.surface")) >= 4.5

    def test_semantic_status_pairs(self):
        assert contrast(token("semantic.on-error"), token("semantic.error")) >= 4.5
        assert contrast(token("semantic.on-warning"), token("semantic.warning")) >= 4.5
        assert contrast(token("semantic.on-info"), token("semantic.info")) >= 4.5
        assert contrast(token("semantic.on-success"), token("semantic.success")) >= 4.5
        assert contrast(token("semantic.on-unavailable"), token("semantic.unavailable")) >= 4.5
        assert contrast(token("semantic.on-insufficient"), token("semantic.insufficient")) >= 4.5

    def test_disabled_text(self):
        assert contrast(token("colors.action-text-disabled"), token("colors.action-disabled")) >= 4.5

    def test_focus_outline_measured(self):
        """Focus indicator meets the non-text contrast threshold on adjacent surfaces."""
        focus = token("colors.focus")
        assert contrast(focus, token("colors.white")) >= 3.0
        assert contrast(focus, token("colors.surface")) >= 3.0
        assert contrast(focus, token("colors.text")) >= 3.0
        assert token("geometry.focus-width") == "3px"

    def test_accent_and_subtle_borders_non_text(self):
        """State accent bars and subtle hairlines meet >=3:1 non-text."""
        for name in (
            "accent-success", "accent-warning", "accent-error", "accent-info",
            "accent-unavailable", "accent-insufficient", "accent-neutral",
        ):
            value = token(f"semantic.{name}")
            assert contrast(value, token("colors.white")) >= 3.0, name
            assert contrast(value, token("colors.surface")) >= 3.0, name
        assert contrast(token("colors.border-subtle"), token("colors.white")) >= 3.0

    def test_quiet_state_label_pairs(self):
        for fill, label in (
            ("success", "on-success"),
            ("warning", "on-warning"),
            ("error", "on-error"),
            ("info", "on-info"),
            ("unavailable", "on-unavailable"),
            ("insufficient", "on-insufficient"),
            ("neutral", "on-neutral"),
        ):
            assert contrast(
                token(f"semantic.{label}"), token(f"semantic.{fill}")
            ) >= 4.5, fill

    def test_decorative_red_is_not_a_text_background(self):
        """#ff004d must not appear as a text-bearing background in CSS."""
        assert token("colors.action") != token("colors.pixel-red")
        css = pa.PIXEL_CSS + pa.PIXEL_COMPONENT_CSS
        for match in re.finditer(r"background(?:-color)?\s*:\s*([^;!]+)", css):
            value = match.group(1).strip()
            if "#ff004d" in value or "var(--px-red)" in value:
                # Allowed only for the non-text tab underline accent.
                assert "border-bottom" in css[max(0, match.start() - 160) : match.start()]


# ── 5. Typography contract ─────────────────────────────────────────────

class TestTypography:
    def test_system_sans_body_stack(self, css_vars):
        stack = css_vars["--px-font-body"]
        assert "sans-serif" in stack
        assert "Segoe UI" in stack or "-apple-system" in stack
        assert "Microsoft YaHei" in stack or "PingFang SC" in stack or "Noto Sans SC" in stack
        assert "url(" not in stack
        assert "@import" not in stack
        for forbidden in ("Inter", "Roboto", "Geist"):
            assert forbidden not in stack

    def test_monospace_technical_stack(self, css_vars):
        stack = css_vars["--px-font-mono"]
        assert stack.endswith("monospace")
        assert "Cascadia" in stack or "Consolas" in stack
        assert "url(" not in stack

    def test_monospace_usage_is_constrained(self, css):
        # Body roles are sans; only technical/brand roles are mono.
        assert ".stApp p, .stApp li" in css
        assert "font-family: var(--px-font-mono) !important" in css
        assert ".px-badge, .px-table-wrap table" in css
        assert "stMetricValue" in css

    def test_heading_role_is_sans_display(self, css_vars):
        # v0.9.7-D: headings use the sans display role (mono is technical).
        assert css_vars["--px-font-heading"] == "var(--px-font-display)"
        assert css_vars["--px-font-display"] == css_vars["--px-font-body"]


# ── 6. Selector policy ─────────────────────────────────────────────────

class TestSelectorPolicy:
    def test_no_hashed_streamlit_classes(self, css):
        for match in re.finditer(r"\.st-[a-z0-9]+", css):
            pytest.fail(f"hashed/generated Streamlit class in CSS: {match.group(0)}")

    def test_documented_stable_selectors_only(self, css):
        allowed = (
            ".stApp", ".stButton", ".stDownloadButton", ".stTextInput",
            ".stTextArea", ".stSelectbox", ".stMultiSelect", ".stNumberInput",
            ".stCheckbox", ".stRadio", ".stAlert",
            "stVerticalBlock", "stHorizontalBlock", "stSidebar",
            "stExpander", "stTabs", "stNotification", "stException",
            "stAppViewContainer", "stMetricValue", "stBaseButton-primary",
            "stBaseButton-secondary", "px-", "data-testid",
        )
        for selector in re.findall(r"([.#]st[A-Za-z0-9_-]+)", css):
            if not any(selector.startswith(prefix) for prefix in allowed):
                pytest.fail(f"undocumented selector: {selector}")

    def test_new_primitives_have_stable_testids(self, css):
        # Component-level `data-testid` attributes are asserted by the
        # component tests; here we verify the matching stable CSS classes.
        for testid, css_class in (
            ("px-notice", ".px-notice"),
            ("px-field-error", ".px-field-error"),
            ("px-loading", ".px-loading"),
            ("px-empty-state", ".px-empty"),
            ("px-table-wrap", ".px-table-wrap"),
            ("px-icon", ".px-icon"),
            ("px-status-badge", ".px-status-badge"),
            ("px-mono", ".px-mono"),
            ("px-cycle-head", ".px-cycle-head"),
            ("px-stage-item", ".px-stage-item"),
        ):
            assert css_class in css, testid


# ── 7. Icon policy ─────────────────────────────────────────────────────

class TestIconPolicy:
    def test_local_svg_only(self):
        assert pa.ICON_PATHS
        for name, path in pa.ICON_PATHS.items():
            assert path.startswith("<path")
            assert "url(" not in path

    def test_decorative_icon_is_hidden(self):
        svg = pa.icon("check")
        assert 'aria-hidden="true"' in svg
        assert "aria-label" not in svg

    def test_meaningful_icon_is_labeled(self):
        svg = pa.icon("warning", label="Warning")
        assert 'role="img"' in svg
        assert 'aria-label="Warning"' in svg

    def test_unknown_icon_falls_back_safely(self):
        svg = pa.icon("not-a-real-icon")
        assert 'aria-hidden="true"' in svg

    def test_no_external_icon_dependency(self, css):
        assert "url(" not in css
        assert "@import" not in css
        assert "fonts.googleapis" not in css
        assert "unpkg" not in css


# ── 8. Streamlit theme parity (Phase 3) ────────────────────────────────

@pytest.fixture(scope="module")
def theme() -> dict:
    config_path = PROJECT_ROOT / ".streamlit" / "config.toml"
    assert config_path.is_file(), ".streamlit/config.toml must exist"
    with config_path.open("rb") as handle:
        config = tomllib.load(handle)
    assert "theme" in config
    return config["theme"]


class TestThemeParity:

    def test_theme_parse_and_supported_keys(self, theme):
        supported = {
            "primaryColor", "backgroundColor", "secondaryBackgroundColor",
            "textColor", "font", "base",
        }
        assert set(theme) <= supported

    def test_primary_color_parity(self, theme):
        assert theme["primaryColor"].lower() == token("colors.action")

    def test_background_parity(self, theme):
        assert theme["backgroundColor"].lower() == token("colors.bg")
        assert theme["secondaryBackgroundColor"].lower() == token("colors.surface")

    def test_text_color_parity(self, theme):
        assert theme["textColor"].lower() == token("colors.text")

    def test_font_category_is_system_sans(self, theme):
        assert theme["font"] == "sans serif"
        assert "monospace" != theme["font"]


# ── 9. Locale / UTF-8 foundation ───────────────────────────────────────

class TestLocaleFoundation:
    def _load(self, name: str) -> dict:
        return json.loads((PROJECT_ROOT / "locales" / name).read_text(encoding="utf-8"))

    def test_english_and_chinese_parse(self):
        en = self._load("en.json")
        zh = self._load("zh_CN.json")
        assert en and zh

    def test_key_parity(self):
        en = self._load("en.json")
        zh = self._load("zh_CN.json")
        assert set(en) == set(zh)

    def test_no_mojibake_or_replacement_characters(self):
        for name in ("en.json", "zh_CN.json"):
            text = (PROJECT_ROOT / "locales" / name).read_text(encoding="utf-8")
            assert "\ufffd" not in text
            for marker in ("Ã", "锘", "â€"):
                assert marker not in text

    def test_utf8_integrity(self):
        for name in ("en.json", "zh_CN.json"):
            raw = (PROJECT_ROOT / "locales" / name).read_bytes()
            raw.decode("utf-8")  # must not raise
