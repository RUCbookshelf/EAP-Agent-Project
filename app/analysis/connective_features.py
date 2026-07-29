from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path


RESOURCE_PATH = Path(__file__).resolve().parent / "resources" / "connectives_v0_6_1.json"


class ConnectiveFeatureExtractor:
    def __init__(self, resource_path: Path = RESOURCE_PATH) -> None:
        raw = resource_path.read_bytes()
        self.resource_hash = hashlib.sha256(raw).hexdigest()
        self.resource = json.loads(raw.decode("utf-8"))
        self.version = self.resource["version"]

    def extract(self, text: str, sentence_spans: list[tuple[int, int]], paragraph_spans: list[tuple[int, int]]) -> dict:
        found: list[dict] = []
        lowered = text.lower()
        expression_classes = {
            form: class_name
            for class_name, forms in self.resource.get("expression_classes", {}).items()
            for form in forms
        }
        for category, forms in self.resource["items"].items():
            for form in sorted(forms, key=len, reverse=True):
                for match in re.finditer(rf"\b{re.escape(form)}\b", lowered):
                    sentence_id = next((i for i, (s, e) in enumerate(sentence_spans, 1) if s <= match.start() < e), None)
                    paragraph_id = next((i for i, (s, e) in enumerate(paragraph_spans, 1) if s <= match.start() < e), None)
                    found.append({
                        "connective_id": f"C{len(found)+1:03d}", "text": text[match.start():match.end()],
                        "normalized_form": form, "sentence_id": sentence_id,
                        "start_offset": match.start(), "end_offset": match.end(),
                        "function_category": category, "expression_class": expression_classes.get(form, "discourse_connective"),
                        "paragraph_id": paragraph_id,
                    })
        found.sort(key=lambda item: (item["start_offset"], -(item["end_offset"] - item["start_offset"])))
        # Prevent nested duplicate dictionary matches at the same start.
        deduped: list[dict] = []
        occupied: list[tuple[int, int]] = []
        for item in found:
            span = (item["start_offset"], item["end_offset"])
            if any(span[0] >= start and span[1] <= end for start, end in occupied):
                continue
            item["connective_id"] = f"C{len(deduped)+1:03d}"
            occupied.append(span)
            deduped.append(item)
        repetitions = Counter(item["normalized_form"] for item in deduped)
        for item in deduped:
            item["same_form_count"] = repetitions[item["normalized_form"]]
            item["same_form_repeated"] = repetitions[item["normalized_form"]] > 1
        return {
            "detected_connectives": deduped,
            "category_distribution": dict(Counter(item["function_category"] for item in deduped)),
            "expression_class_distribution": dict(Counter(item["expression_class"] for item in deduped)),
            "resource_version": self.version,
            "resource_hash": self.resource_hash,
            "limitations": self.resource["limitations"],
        }
