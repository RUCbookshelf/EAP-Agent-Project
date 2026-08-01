"""Layer 1 static, locale, asset, token, and Student-text audit."""

from __future__ import annotations

import ast
import importlib
import json
import pathlib
import re
import sys


HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))


def main() -> int:
    evidence: dict[str, object] = {"run_id": "v0.9.4-b-20260801-r1"}
    python_paths = [
        *sorted((ROOT / "app/ui").rglob("*.py")),
        ROOT / "scripts/pixel_art_style_audit.py",
        ROOT / "scripts/design_system_audit_v094a.py",
        ROOT / "tests/test_student_experience_v094b.py",
        ROOT / "tests/test_design_tokens_v094a.py",
    ]
    parsed = []
    for path in python_paths:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        parsed.append(str(path.relative_to(ROOT)))
    evidence["python_ast_files"] = len(parsed)

    imported = [
        "app.ui.components",
        "app.ui.pixel_art",
        "app.ui.student_context",
        "app.ui.pages.student_pages",
        "app.ui.pages.research_pages",
        "app.ui.streamlit_app",
    ]
    for module in imported:
        importlib.import_module(module)
    evidence["imports"] = imported

    locales = {}
    mojibake_markers = ("\ufffd", "锘", "Ã", "Â", "鈥", "鈫")
    for language in ("en", "zh_CN"):
        path = ROOT / f"locales/{language}.json"
        raw = path.read_text(encoding="utf-8")
        payload = json.loads(raw)
        assert not any(marker in raw for marker in mojibake_markers), language
        assert all(isinstance(key, str) and isinstance(value, str) for key, value in payload.items())
        locales[language] = payload
    assert set(locales["en"]) == set(locales["zh_CN"])
    evidence["locale_parity"] = {
        "en": len(locales["en"]), "zh_CN": len(locales["zh_CN"]), "equal": True
    }
    evidence["utf8_mojibake_markers"] = []

    ui_paths = sorted((ROOT / "app/ui").rglob("*.py"))
    ui_text = "\n".join(path.read_text(encoding="utf-8") for path in ui_paths)
    remote_patterns = re.findall(
        r"https?://|fonts\.googleapis|fonts\.gstatic|cdn\.jsdelivr|unpkg|cdnjs",
        ui_text,
        flags=re.IGNORECASE,
    )
    assert not remote_patterns
    evidence["remote_asset_references"] = remote_patterns

    student_source = (ROOT / "app/ui/pages/student_pages.py").read_text(encoding="utf-8")
    token_declarations = re.findall(r"--px-[a-z0-9-]+\s*:", student_source)
    hardcoded_colors = re.findall(r"#[0-9a-fA-F]{3,8}\b", student_source)
    assert not token_declarations and not hardcoded_colors
    evidence["page_local_token_declarations"] = token_declarations
    evidence["student_page_color_literals"] = hardcoded_colors

    tree = ast.parse(student_source)
    user_facing_calls = {
        "button", "text_input", "text_area", "selectbox", "radio", "checkbox",
        "warning", "caption", "write", "markdown", "header", "subheader",
    }
    direct_application_literals = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in user_facing_calls or not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            value = first.value.strip()
            if re.search(r"[A-Za-z]{3,}\s+[A-Za-z]{3,}", value):
                direct_application_literals.append(
                    {"line": node.lineno, "call": node.func.attr, "value": value[:100]}
                )
    assert not direct_application_literals, direct_application_literals
    evidence["new_direct_student_application_literals"] = direct_application_literals

    from app.ui.pixel_art import DESIGN_TOKENS
    assert DESIGN_TOKENS["colors"]["focus"] == "#0f6dbd"
    evidence["focus_token"] = DESIGN_TOKENS["colors"]["focus"]

    path = HERE / "final_static_evidence.json"
    path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    print(f"FINAL STATIC AUDIT: PASS -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
