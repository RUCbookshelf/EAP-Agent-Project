from __future__ import annotations

import hashlib
import re

from .schemas import InputQualityResult, QualityFlag


class InputQualityService:
    version = "input-quality-v0.4.0"
    _prefaces = (
        "here is a refined version", "here is the revised version",
        "certainly!", "sure, here is", "editor's note", "editing note",
    )

    def inspect(self, text: str, *, draft_stage: str | None = None, tool_use: str | None = None) -> InputQualityResult:
        flags: list[QualityFlag] = []

        def add(category: str, start: int, end: int, confidence: str, action: str) -> None:
            flags.append(QualityFlag(
                flag_id=f"Q{len(flags)+1:03d}", category=category,
                text_span=text[start:end], start_offset=start, end_offset=end,
                confidence=confidence, recommended_action=action,
            ))

        lowered = text.lower()
        for phrase in self._prefaces:
            pos = lowered.find(phrase)
            if 0 <= pos <= 120:
                add("possible_non_essay_preface", pos, pos + len(phrase), "medium", "confirm_exclusion")
                break
        for match in re.finditer(r"```|^\s*---+\s*$|^\s*#{1,6}\s+", text, re.MULTILINE):
            category = "code_fence" if match.group().strip().startswith("```") else "markdown_marker"
            add(category, match.start(), match.end(), "high", "confirm_text_boundary")
        if re.search(r"\n[ \t]*\n[ \t]*\n", text):
            match = re.search(r"\n[ \t]*\n[ \t]*\n", text)
            assert match
            add("empty_paragraph", match.start(), match.end(), "medium", "review_formatting")
        paragraphs = [(m.group().strip(), m.start(), m.end()) for m in re.finditer(r"[^\r\n]+(?:\r?\n(?!\r?\n)[^\r\n]+)*", text) if m.group().strip()]
        seen: dict[str, tuple[int, int]] = {}
        for paragraph, start, end in paragraphs:
            normalized = " ".join(paragraph.lower().split())
            if len(normalized.split()) >= 5 and normalized in seen:
                add("repeated_paragraph", start, end, "high", "confirm_duplicate")
            seen.setdefault(normalized, (start, end))
        words = re.findall(r"[A-Za-z]+(?:['’-][A-Za-z]+)?", text)
        if len(words) < 30:
            add("extremely_short_text", 0, len(text), "high", "confirm_complete_draft")
        first_line = text.splitlines()[0].strip() if text.splitlines() else ""
        if first_line and len(first_line.split()) <= 10 and not re.search(r"[.!?]$", first_line) and "\n" in text:
            add("possible_title_or_instruction_line", 0, len(first_line), "low", "confirm_text_boundary")
        if draft_stage and draft_stage.lower().replace(" ", "_") in {"revised_draft", "final_draft"} and len(words) < 30:
            add("metadata_text_mismatch", 0, min(len(text), 120), "low", "confirm_submission_metadata")
        if tool_use and tool_use.lower() == "none" and any(p in lowered[:150] for p in self._prefaces):
            add("tool_metadata_text_mismatch", 0, min(len(text), 150), "low", "confirm_tool_use_metadata")
        return InputQualityResult(
            quality_flags=flags, analysis_text_changed=False,
            analysis_text_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            limitations=[
                "Flags are surface-pattern candidates and do not establish AI use or misconduct.",
                "The raw essay is preserved and no text is excluded automatically.",
            ],
        )

