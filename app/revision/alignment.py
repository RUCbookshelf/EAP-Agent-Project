from __future__ import annotations

import re
from difflib import SequenceMatcher

from .schemas import SegmentAlignment


class LocalRevisionAligner:
    version = "local-sequence-alignment-v0.5.0"

    def align(self, source: str, target: str) -> tuple[list[SegmentAlignment], list[SegmentAlignment], dict]:
        paragraphs = self._align_segments(self._paragraphs(source), self._paragraphs(target), "paragraph", "P")
        sentences = self._align_segments(self._sentences(source), self._sentences(target), "sentence", "S")
        token_changes = self._token_changes(source, target)
        return paragraphs, sentences, token_changes

    def _align_segments(self, source: list[str], target: list[str], level: str, prefix: str) -> list[SegmentAlignment]:
        alignments: list[SegmentAlignment] = []
        used_source: set[int] = set()
        used_target: set[int] = set()

        # Detect adjacent split/merge cases before one-to-one matching.  The
        # combined match must be materially stronger than either fragment so
        # ordinary edits are not mislabeled as structural changes.
        for i, left in enumerate(source):
            for j in range(len(target) - 1):
                combined = self.similarity(left, target[j] + " " + target[j + 1])
                individual = max(self.similarity(left, target[j]), self.similarity(left, target[j + 1]))
                if combined >= 0.72 and combined >= individual + 0.10:
                    used_source.add(i); used_target.update({j, j + 1})
                    alignments.append(self._item(
                        level, prefix, i, j, left, target[j] + " " + target[j + 1], combined, "split",
                        target_id=f"{prefix}T{j+1:03d}+{prefix}T{j+2:03d}",
                    ))
                    break
        for j, right in enumerate(target):
            if j in used_target:
                continue
            for i in range(len(source) - 1):
                if i in used_source or i + 1 in used_source:
                    continue
                combined = self.similarity(source[i] + " " + source[i + 1], right)
                individual = max(self.similarity(source[i], right), self.similarity(source[i + 1], right))
                if combined >= 0.72 and combined >= individual + 0.10:
                    used_target.add(j); used_source.update({i, i + 1})
                    alignments.append(self._item(
                        level, prefix, i, j, source[i] + " " + source[i + 1], right, combined, "merged",
                        source_id=f"{prefix}S{i+1:03d}+{prefix}S{i+2:03d}",
                    ))
                    break
        candidates = sorted(
            ((self.similarity(left, right), i, j) for i, left in enumerate(source) for j, right in enumerate(target)),
            reverse=True,
        )
        for similarity, i, j in candidates:
            if similarity < 0.35 or i in used_source or j in used_target:
                continue
            used_source.add(i); used_target.add(j)
            kind = "unchanged" if similarity >= 0.98 else "lightly_modified" if similarity >= 0.72 else "heavily_modified"
            alignments.append(self._item(level, prefix, i, j, source[i], target[j], similarity, kind))

        # Lower-confidence split/merge candidates for remaining unmatched segments.
        for i, left in enumerate(source):
            if i in used_source:
                continue
            for j in range(len(target) - 1):
                if j in used_target or j + 1 in used_target:
                    continue
                similarity = self.similarity(left, target[j] + " " + target[j + 1])
                if similarity >= 0.55:
                    used_source.add(i); used_target.update({j, j + 1})
                    alignments.append(self._item(level, prefix, i, j, left, target[j] + " " + target[j + 1], similarity, "split", target_id=f"{prefix}T{j+1:03d}+{prefix}T{j+2:03d}"))
                    break
        for j, right in enumerate(target):
            if j in used_target:
                continue
            for i in range(len(source) - 1):
                if i in used_source or i + 1 in used_source:
                    continue
                similarity = self.similarity(source[i] + " " + source[i + 1], right)
                if similarity >= 0.55:
                    used_target.add(j); used_source.update({i, i + 1})
                    alignments.append(self._item(level, prefix, i, j, source[i] + " " + source[i + 1], right, similarity, "merged", source_id=f"{prefix}S{i+1:03d}+{prefix}S{i+2:03d}"))
                    break
        for i, text in enumerate(source):
            if i not in used_source:
                alignments.append(self._item(level, prefix, i, None, text, None, 0.0, "deleted"))
        for j, text in enumerate(target):
            if j not in used_target:
                alignments.append(self._item(level, prefix, None, j, None, text, 0.0, "inserted"))
        alignments.sort(key=lambda item: (item.target_segment_id or "ZZZ", item.source_segment_id or "ZZZ"))
        for index, item in enumerate(alignments, 1):
            item.alignment_id = f"AL{level[0].upper()}{index:03d}"
        return alignments

    def _item(self, level, prefix, i, j, source, target, similarity, kind, *, source_id=None, target_id=None):
        return SegmentAlignment(
            alignment_id="ALTEMP", level=level,
            source_segment_id=source_id or (f"{prefix}S{i+1:03d}" if i is not None else None),
            target_segment_id=target_id or (f"{prefix}T{j+1:03d}" if j is not None else None),
            source_text=source, target_text=target, similarity=round(similarity, 4), alignment_type=kind,
            confidence="high" if similarity >= 0.9 else "medium" if similarity >= 0.55 else "low",
            limitations=["Local sequence/lexical similarity is a transparent prototype, not semantic equivalence."],
        )

    @staticmethod
    def similarity(left: str, right: str) -> float:
        normalize = lambda value: " ".join(re.findall(r"[a-z]+(?:'[a-z]+)?", value.casefold()))
        a, b = normalize(left), normalize(right)
        if not a or not b:
            return 0.0
        seq = SequenceMatcher(None, a, b).ratio()
        sa, sb = set(a.split()), set(b.split())
        jaccard = len(sa & sb) / len(sa | sb)
        return 0.65 * seq + 0.35 * jaccard

    @staticmethod
    def _paragraphs(text: str) -> list[str]:
        return [item.strip() for item in re.split(r"(?:\r?\n\s*){2,}", text) if item.strip()]

    @staticmethod
    def _sentences(text: str) -> list[str]:
        return [item.strip() for item in re.findall(r"[^.!?]+(?:[.!?]+|$)", text) if item.strip()]

    @staticmethod
    def _token_changes(source: str, target: str) -> dict:
        tokenize = lambda value: re.findall(r"[A-Za-z]+(?:['’-][A-Za-z]+)?|[^\w\s]", value)
        left, right = tokenize(source), tokenize(target)
        matcher = SequenceMatcher(None, [x.casefold() for x in left], [x.casefold() for x in right])
        counts = {"unchanged": 0, "inserted": 0, "deleted": 0, "modified": 0}
        operations = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal": counts["unchanged"] += i2 - i1
            elif tag == "insert": counts["inserted"] += j2 - j1
            elif tag == "delete": counts["deleted"] += i2 - i1
            else: counts["modified"] += max(i2 - i1, j2 - j1)
            operations.append({"operation": tag, "source_tokens": left[i1:i2], "target_tokens": right[j1:j2]})
        denominator = max(len(left), len(right), 1)
        return {
            **counts, "source_token_count": len(left), "target_token_count": len(right),
            "inserted_ratio": round(counts["inserted"] / denominator, 4),
            "deleted_ratio": round(counts["deleted"] / denominator, 4),
            "modified_ratio": round(counts["modified"] / denominator, 4),
            "operations": operations, "algorithm_version": LocalRevisionAligner.version,
        }
