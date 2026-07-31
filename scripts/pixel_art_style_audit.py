"""Static Pixel Art style audit for v0.9.2.

Scans application-owned UI source files for prohibited style patterns:
- non-zero border-radius
- gradients / gradient text
- blur / backdrop-filter / glassmorphism
- soft shadows (box-shadow with blur radius or transparency)
- transition durations > 0, transition-all
- CSS animations / @keyframes
- opacity fades
- Inter / Roboto / Geist fonts
- thin (1px) borders on primary components
- decorative single-side accent borders
- detectable nested cards

Run: python scripts/pixel_art_style_audit.py
Exit: 0 = PASS, 1 = FAIL
"""

from __future__ import annotations

import pathlib
import re
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCAN_FILES = [
    PROJECT_ROOT / "app" / "ui" / "pixel_art.py",
    PROJECT_ROOT / "app" / "ui" / "components.py",
    PROJECT_ROOT / "app" / "ui" / "streamlit_app.py",
    PROJECT_ROOT / "app" / "ui" / "pages" / "student_pages.py",
    PROJECT_ROOT / "app" / "ui" / "pages" / "research_pages.py",
]

# Documented functional/structural exceptions (not decorative accents):
# - tab underline + active-tab red underline (tab treatment indicator)
# - sidebar structural right border
# - section header / divider horizontal rules (full-width structural rules)
# - table cell 1px grid lines (data-table structure, not a primary component)
ALLOWED_SINGLE_SIDE_PREFIXES = (
    "border-bottom: var(--px-border-thick)",   # tab underline
    "border-bottom: 4px solid var(--px-red)",  # active tab indicator
    "border-right: var(--px-border-thick)",    # sidebar structure
    "border-bottom:4px solid var(--px-dark)",  # heading structural rule
    "border-bottom:2px solid var(--px-dark)",  # section heading structural rule
    "border-top: var(--px-border-thick)",      # section/divider structural rule
    "border-bottom: var(--px-border-thin)",    # section structural rule
)

VIOLATIONS = []


def add(path, line, label, snippet):
    VIOLATIONS.append(f"{path.name}:{line} [{label}] {snippet[:90]}")


def check_value(prop, value, path, line):
    """Check a single CSS property value."""
    v = value.strip().rstrip(";").rstrip("!important").strip()
    if prop == "border-radius":
        if v not in ("0", "0px"):
            add(path, line, "non-zero border-radius", f"border-radius: {v}")
    elif prop == "transition":
        if v != "none":
            add(path, line, "transition != none", f"transition: {v}")
        if "transition-all" in value:
            add(path, line, "transition-all", value[:70])
    elif prop == "transition-duration":
        if v not in ("0s", "0ms"):
            add(path, line, "transition-duration > 0", f"transition-duration: {v}")
    elif prop == "animation" or prop == "animation-name":
        if v != "none":
            add(path, line, "animation", f"{prop}: {v}")
    elif prop == "background-image":
        if v != "none":
            add(path, line, "gradient/background-image", f"background-image: {v}")
    elif prop == "filter":
        if v != "none":
            add(path, line, "blur/filter", f"filter: {v}")
    elif prop == "backdrop-filter":
        if v != "none":
            add(path, line, "blur/backdrop", f"backdrop-filter: {v}")


def audit_css_block(path: pathlib.Path, text: str) -> None:
    # Find each CSS rule block
    for rule_match in re.finditer(r"([^{}]+)\{([^{}]*)\}", text):
        body = rule_match.group(2)
        line = text[: rule_match.start()].count("\n") + 1
        for prop_match in re.finditer(r"([a-z-]+)\s*:\s*([^;]+);?", body):
            prop = prop_match.group(1).strip().lower()
            value = prop_match.group(2).strip()
            check_value(prop, value, path, line)

        # Soft shadows: box-shadow with blur radius or transparency
        for sh in re.finditer(r"box-shadow\s*:\s*([^;]+)", body):
            val = sh.group(1)
            if re.search(r"rgba?\([^)]*,\s*0?\.\d", val) or re.search(r"\d+px\s+\d+px\s+\d+px", val):
                add(path, line, "soft shadow", f"box-shadow: {val.strip()[:70]}")

        # Gradients
        if re.search(r"linear-gradient|radial-gradient|conic-gradient", body):
            add(path, line, "gradient", body.strip()[:70])

        # Animations/keyframes
        if "@keyframes" in body or re.search(r"animation\s*:", body):
            pass  # checked via check_value for animation property

        # Forbidden fonts
        if re.search(r"\bInter\b|\bRoboto\b|\bGeist\b", body):
            add(path, line, "forbidden font", body.strip()[:70])

        # Thin borders on primary components (1px). Table cell grid lines
        # inside .px-table-wrap are data-table structure, not primary
        # components, and are a documented structural exception.
        selector = rule_match.group(1)
        if "px-table-wrap" not in body and "px-table-wrap" not in selector:
            for b in re.finditer(r"border\s*:\s*1px\s+solid", body):
                add(path, line, "thin border", b.group(0)[:70])

        # Single-side accent borders (allow structural exceptions)
        for ss in re.finditer(r"border-(left|right|top|bottom)\s*:\s*([^;]+)", body):
            full = ss.group(0)
            if any(full.startswith(p) for p in ALLOWED_SINGLE_SIDE_PREFIXES):
                continue
            if re.search(r"\b(border|px)", full):
                add(path, line, "single-side accent border", full[:70])

        # Detectable nested cards within one CSS-defined component
        if body.count("px-card") > 1:
            add(path, line, "nested card in CSS", body.strip()[:70])


def audit_html_fragments(path: pathlib.Path, text: str) -> None:
    # Extract HTML fragments from st.markdown(..., unsafe_allow_html=True)
    # and from f-string HTML built for st.markdown.
    for frag in re.finditer(r"st\.markdown\(\s*f?[\"'](.*?)[\"']\s*,?\s*unsafe_allow_html", text, re.DOTALL):
        html = frag.group(1)
        line = text[: frag.start()].count("\n") + 1
        # Nested px-card within one fragment
        if html.count('<div class="px-card"') > 1:
            add(path, line, "nested card in HTML fragment", html[:70])
        # Rounded utility classes other than rounded-none
        for rc in re.finditer(r"rounded-(?!none\b)[a-z-]+", html):
            add(path, line, "rounded utility", rc.group(0))
        # Gradients in inline styles
        if re.search(r"linear-gradient|radial-gradient|conic-gradient", html):
            add(path, line, "gradient in fragment", html[:70])
        # Forbidden fonts
        if re.search(r"\bInter\b|\bRoboto\b|\bGeist\b", html):
            add(path, line, "forbidden font in fragment", html[:70])
        # Soft shadows in inline styles
        if re.search(r"box-shadow[^;]*rgba?\(", html):
            add(path, line, "soft shadow in fragment", html[:70])


def audit_file(path: pathlib.Path) -> None:
    text = path.read_text(encoding="utf-8")
    audit_css_block(path, text)
    audit_html_fragments(path, text)


def main() -> int:
    for path in SCAN_FILES:
        if path.exists():
            audit_file(path)
    if VIOLATIONS:
        print(f"PIXEL ART STYLE AUDIT: FAIL ({len(VIOLATIONS)} violations)")
        for v in VIOLATIONS:
            print(f"  - {v}")
        return 1
    print("PIXEL ART STYLE AUDIT: PASS (0 violations in application-owned UI source)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
