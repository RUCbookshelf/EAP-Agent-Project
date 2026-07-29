from __future__ import annotations

from app.models import AnalysisResult, DiagnosisResult, DiagnosisSignal

from .heuristic import HeuristicDiagnoser, LIMITATION


class NlpHeuristicDiagnoser(HeuristicDiagnoser):
    """Generate raw candidates. DiagnosticCalibrationService decides admission."""

    version = "prototype-diagnosis-v0.6.1"

    def diagnose(self, analysis: AnalysisResult) -> DiagnosisResult:
        lexical = analysis.artifacts.get("lexical_features", {})
        connective = analysis.artifacts.get("connective_features", {})
        syntactic = analysis.artifacts.get("syntactic_features", {})
        raw: list[DiagnosisSignal] = []

        raw.append(self._signal(
            "draft_length_description",
            f"The draft contains {analysis.metrics.get('word_count', 0)} detected alphabetic tokens.",
            ["word_count"], "This is a descriptive count and not a writing-quality strength.",
            "high", "descriptive_signal", metadata={"word_count": analysis.metrics.get("word_count", 0)},
        ))

        for detail in lexical.get("repeated_content_word_details", []):
            sentence_text = {
                item["sentence_id"]: item["text"] for item in syntactic.get("sentences", [])
            }
            quotes = [sentence_text.get(item.get("sentence_id"), "") for item in detail.get("occurrences", [])]
            raw.append(self._signal(
                "lexical_repetition",
                f"Lemma '{detail['lemma']}' occurs {detail['count']} times at sentences {detail.get('sentence_ids', [])}; "
                f"density={detail.get('density')}; local_cluster={detail.get('local_cluster_detected')}.",
                ["repeated_content_words", "repetition_density"],
                "This lemma pattern may be worth monitoring or locally revising if the evidence is concentrated and replaceable.",
                "medium" if detail.get("local_cluster_detected") else "low", metadata={
                    "target_lemma": detail["lemma"], **detail,
                }, quotes=[quote for quote in quotes if quote],
            ))

        detected = connective.get("detected_connectives", [])
        sentences = syntactic.get("sentences", [])
        boundary = self._specific_boundary(sentences, detected)
        forms = sorted({item["normalized_form"] for item in detected})
        raw.append(self._signal(
            "connective_use",
            f"Detected listed expressions: {', '.join(forms) or 'none'}; functions: {connective.get('category_distribution', {})}.",
            ["connective_count"],
            "Dictionary results describe explicit markers only; a feedback priority requires a specific sentence or paragraph relation.",
            "medium" if boundary else "low", metadata={
                "detected_connectives": detected, "detected_forms": forms,
                "function_categories": connective.get("category_distribution", {}),
                "specific_location": bool(boundary), "boundary": boundary,
            }, quotes=[boundary["quote"]] if boundary else [],
        ))

        for candidate in syntactic.get("long_sentence_candidates", [])[:2]:
            raw.append(self._signal(
                "sentence_structure_candidate",
                f"Sentence {candidate['sentence_id']} has {candidate['token_count']} parser-detected tokens.",
                ["average_sentence_length"],
                "This sentence may be worth a manual readability check; length alone is not an error or complexity score.",
                "low", metadata={"flagged_sentence": candidate["text"], "magnitude": min(1, candidate["token_count"] / 60)},
                quotes=[candidate["text"]],
            ))

        for flag in analysis.input_quality.get("quality_flags", []):
            raw.append(self._signal(
                "input_quality", f"Input-quality flag {flag['category']} at offsets {flag['start_offset']}–{flag['end_offset']}.",
                ["input_quality"], "The flagged span may need removal or confirmation before language interpretation.",
                flag.get("confidence", "low"), metadata={"flag_span": flag.get("text_span", ""), "flag": flag},
                quotes=[flag.get("text_span", "")],
            ))

        strength = self._verified_strength(sentences, detected)
        if strength:
            raw.append(strength)

        # Compatibility fields remain populated for callers that inspect the raw diagnoser directly.
        raw_improvements = [
            item for item in raw if item.kind == "improvement" and not (
                item.category == "lexical_repetition"
                and item.evidence_metadata.get("is_prompt_keyword")
                and not item.evidence_metadata.get("local_cluster_detected")
            )
        ]
        raw_strengths = [item for item in raw if item.kind == "strength"]
        identified = [item.model_copy(update={"signal_id": f"S{i:03d}"}) for i, item in enumerate(raw, 1)]
        return DiagnosisResult(
            strengths=raw_strengths[:1], improvement_priorities=raw_improvements[:2],
            descriptive_signals=[item for item in identified if item.kind == "descriptive_signal"],
            raw_signals=identified, diagnosis_version=self.version,
            limitation=(LIMITATION + " Raw candidates require v0.6.1 Diagnostic Gate and evidence calibration before feedback."),
        )

    def _verified_strength(self, sentences: list[dict], detected: list[dict]) -> DiagnosisSignal | None:
        supported = {"because", "for example", "for instance", "therefore", "as a result"}
        for marker in detected:
            if marker["normalized_form"] not in supported:
                continue
            sentence = next((item for item in sentences if item["sentence_id"] == marker["sentence_id"]), None)
            if sentence:
                return self._signal(
                    "explicit_relation_marker",
                    f"Sentence {sentence['sentence_id']} contains the explicit {marker['function_category']} marker '{marker['text']}'.",
                    ["connective_count"],
                    "This exact sentence makes one local relationship explicit; it is not evidence of overall writing ability.",
                    "medium", "strength", metadata={"marker": marker}, quotes=[sentence["text"]],
                )
        return None

    @staticmethod
    def _specific_boundary(sentences: list[dict], detected: list[dict]) -> dict | None:
        for previous, current in zip(sentences, sentences[1:]):
            if previous.get("paragraph_id") == current.get("paragraph_id"):
                continue
            current_text = current["text"].strip().lower()
            current_markers = [
                item for item in detected
                if item.get("sentence_id") == current["sentence_id"]
                and current_text.startswith(str(item.get("normalized_form", "")).lower())
            ]
            if current_markers:
                continue
            return {
                "previous_sentence_id": previous["sentence_id"], "current_sentence_id": current["sentence_id"],
                "previous_paragraph_id": previous.get("paragraph_id"), "current_paragraph_id": current.get("paragraph_id"),
                "quote": previous["text"] + "\n\n" + current["text"],
                "limitation": "A visible paragraph boundary without a listed marker does not prove that cohesion is weak.",
            }
        return None

    @staticmethod
    def _signal(category: str, evidence: str, source_metrics: list[str], interpretation: str,
                confidence: str, kind: str = "improvement", *, metadata: dict | None = None,
                quotes: list[str] | None = None) -> DiagnosisSignal:
        return DiagnosisSignal(
            diagnosis_id="D000", category=category, evidence=evidence, source_metrics=source_metrics,
            interpretation=interpretation, confidence=confidence, limitation=LIMITATION,
            rule_version=NlpHeuristicDiagnoser.version, kind=kind,
            evidence_metadata=metadata or {}, evidence_quote_candidates=quotes or [],
        )
