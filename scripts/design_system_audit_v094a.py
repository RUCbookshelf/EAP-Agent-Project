"""v0.9.4-A Hybrid Pixel System deterministic audit.

Combines the static style audit, measured contrast report, Streamlit theme
parity, selector policy, locale/UTF-8 checks, and the two-hardcoded-string
check into one runnable verification script.

Run: python scripts/design_system_audit_v094a.py
Exit: 0 = PASS, 1 = FAIL
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
import tomllib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
UI_MODULES = [
    PROJECT_ROOT / "app" / "ui" / "pixel_art.py",
    PROJECT_ROOT / "app" / "ui" / "components.py",
    PROJECT_ROOT / "app" / "ui" / "streamlit_app.py",
    PROJECT_ROOT / "app" / "ui" / "pages" / "student_pages.py",
    PROJECT_ROOT / "app" / "ui" / "pages" / "research_pages.py",
]

REQUIRED_CONTRAST_PAIRS = [
    ("primary normal", "colors.action-text", "colors.action", 4.5),
    ("primary hover", "colors.action-text", "colors.action-hover", 4.5),
    ("primary active", "colors.action-text", "colors.action-active", 4.5),
    ("body text", "colors.text", "colors.bg", 4.5),
    ("secondary text", "colors.text-secondary", "colors.bg", 4.5),
    ("muted text", "colors.muted", "colors.bg", 4.5),
    ("error text/surface", "semantic.on-error", "semantic.error", 4.5),
    ("warning text/surface", "semantic.on-warning", "semantic.warning", 4.5),
    ("info text/surface", "semantic.on-info", "semantic.info", 4.5),
    ("success text/surface", "semantic.on-success", "semantic.success", 4.5),
    ("unavailable text/surface", "semantic.on-unavailable", "semantic.unavailable", 4.5),
    ("disabled text/disabled bg", "colors.action-text-disabled", "colors.action-disabled", 4.5),
]

PROHIBITED = [
    ("gradient", r"linear-gradient|radial-gradient|conic-gradient"),
    ("blur", r"blur\("),
    ("backdrop-filter", r"backdrop-filter"),
    ("rgba surface", r"rgba\("),
    ("soft shadow", r"box-shadow\s*:\s*[^;]*\d+px\s+\d+px\s+\d+px"),
    ("keyframes", r"@keyframes"),
    ("transition-duration", r"transition-duration"),
    ("animation-duration", r"animation-duration"),
    ("remote url", r"url\(|@import|fonts\.googleapis|unpkg|cdn"),
    ("hashed streamlit class", r"\.st-[a-z0-9]+"),
    ("forbidden font", r"\bInter\b|\bRoboto\b|\bGeist\b"),
    ("Inter font literal", r"\bInter\b"),
]


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


def main() -> int:
    sys.path.insert(0, str(PROJECT_ROOT))
    from app.ui import pixel_art as pa

    failures: list[str] = []
    report: list[str] = []

    css = pa.PIXEL_CSS + pa.PIXEL_COMPONENT_CSS
    css_vars = pa.build_css_vars()

    # 1. Canonical token source
    if pa.PIXEL_CSS != pa.build_pixel_css():
        failures.append("PIXEL_CSS is not generated from the canonical tokens")
    if pa.PIXEL_COMPONENT_CSS != pa.build_component_css():
        failures.append("PIXEL_COMPONENT_CSS is not generated from the canonical tokens")
    report.append(f"Canonical token source: app/ui/pixel_art.py DESIGN_TOKENS "
                  f"(version {pa.DESIGN_TOKENS['version']}); CSS vars: {len(css_vars)}")

    # 2. Prohibited patterns
    for label, pattern in PROHIBITED:
        if re.search(pattern, css, re.IGNORECASE):
            failures.append(f"prohibited pattern: {label}")
    report.append("Prohibited-pattern scan: PASS" if not any(
        f.startswith("prohibited pattern") for f in failures
    ) else "Prohibited-pattern scan: FAIL")

    # 3. All referenced vars are defined
    used = set(re.findall(r"var\((--px-[a-z0-9-]+)\)", css))
    undefined = used - set(css_vars)
    if undefined:
        failures.append(f"undefined CSS vars: {sorted(undefined)}")

    # 4. Measured contrast
    report.append("\nMeasured contrast (WCAG 2.1):")
    for label, fg_path, bg_path, threshold in REQUIRED_CONTRAST_PAIRS:
        fg = pa.DESIGN_TOKENS
        bg = pa.DESIGN_TOKENS
        for part in fg_path.split("."):
            fg = fg[part]
        for part in bg_path.split("."):
            bg = bg[part]
        ratio = contrast(str(fg), str(bg))
        ok = ratio >= threshold
        report.append(f"  {label}: {ratio:.2f}:1 ({'PASS' if ok else 'FAIL'} >= {threshold}:1)")
        if not ok:
            failures.append(f"contrast {label}: {ratio:.2f}:1 < {threshold}:1")

    focus_ratio = contrast(pa.DESIGN_TOKENS["colors"]["focus"], pa.DESIGN_TOKENS["colors"]["bg"])
    focus_status = "PASS" if focus_ratio >= 3.0 else "FAIL"
    report.append(
        f"  focus outline vs adjacent surface: {focus_ratio:.2f}:1 "
        f"({focus_status} >= 3.0:1; visible 3px outline)"
    )
    if focus_ratio < 3.0:
        failures.append(f"focus contrast: {focus_ratio:.2f}:1 < 3.0:1")

    # 5. Theme parity
    config_path = PROJECT_ROOT / ".streamlit" / "config.toml"
    if config_path.is_file():
        with config_path.open("rb") as handle:
            theme = tomllib.load(handle).get("theme", {})
        pairs = [
            (theme.get("primaryColor"), pa.DESIGN_TOKENS["colors"]["action"], "primaryColor"),
            (theme.get("backgroundColor"), pa.DESIGN_TOKENS["colors"]["bg"], "backgroundColor"),
            (theme.get("secondaryBackgroundColor"), pa.DESIGN_TOKENS["colors"]["surface"], "secondaryBackgroundColor"),
            (theme.get("textColor"), pa.DESIGN_TOKENS["colors"]["text"], "textColor"),
        ]
        for actual, expected, name in pairs:
            if (actual or "").lower() != str(expected).lower():
                failures.append(f"theme parity {name}: {actual} != {expected}")
        if theme.get("font") != "sans serif":
            failures.append(f"theme font category: {theme.get('font')!r} != 'sans serif'")
        report.append("Streamlit theme parity: PASS" if not any(
            f.startswith("theme parity") or f.startswith("theme font") for f in failures
        ) else "Streamlit theme parity: FAIL")
    else:
        failures.append(".streamlit/config.toml missing")

    # 6. Locale foundation
    en = json.loads((PROJECT_ROOT / "locales" / "en.json").read_text(encoding="utf-8"))
    zh = json.loads((PROJECT_ROOT / "locales" / "zh_CN.json").read_text(encoding="utf-8"))
    if set(en) != set(zh):
        failures.append("locale key parity")
    for name in ("en.json", "zh_CN.json"):
        text = (PROJECT_ROOT / "locales" / name).read_text(encoding="utf-8")
        if "\ufffd" in text or "锘" in text or "Ã" in text:
            failures.append(f"mojibake in {name}")
    report.append("Locale parity + UTF-8: PASS" if not any(
        f.startswith("locale") or f.startswith("mojibake") for f in failures
    ) else "Locale parity + UTF-8: FAIL")

    # 7. Two hardcoded Research Data strings routed through locale keys
    research = (PROJECT_ROOT / "app" / "ui" / "pages" / "research_pages.py").read_text(encoding="utf-8")
    for literal in ('st.text_input("Target ID"', 'f"Export: '):
        if literal in research:
            failures.append(f"hardcoded string still present: {literal}")
    for key in ("human_review_target_id", "export_run_success"):
        if key not in en or key not in zh:
            failures.append(f"locale key missing: {key}")
    report.append("Hardcoded Research Data strings localized: PASS" if not any(
        f.startswith("hardcoded string") or f.startswith("locale key missing") for f in failures
    ) else "Hardcoded Research Data strings localized: FAIL")

    print("\n".join(report))
    if failures:
        print(f"\nDESIGN SYSTEM AUDIT v0.9.4-A: FAIL ({len(failures)})")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("\nDESIGN SYSTEM AUDIT v0.9.4-A: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
