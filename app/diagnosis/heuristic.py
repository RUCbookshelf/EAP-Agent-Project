from __future__ import annotations

from app.models import AnalysisResult, DiagnosisResult, DiagnosisSignal

from .base import Diagnoser


LIMITATION = "This is a prototype heuristic signal, not a validated judgment of language ability; teacher review is required."


class HeuristicDiagnoser(Diagnoser):
    version = "prototype-diagnosis-v0.1.1"

    def diagnose(self, analysis: AnalysisResult) -> DiagnosisResult:
        m = analysis.metrics
        improvements: list[tuple[int, DiagnosisSignal]] = []
        strengths: list[tuple[int, DiagnosisSignal]] = []
        word_count = int(m["word_count"])
        sentence_count = int(m["sentence_count"])
        connective_count = int(m["connective_count"])
        repeated = m["repeated_content_words"]
        average = float(m["average_sentence_length"])
        ttr = float(m["type_token_ratio"])

        if word_count < 120:
            improvements.append((100, self._signal(
                "essay_length", f"The draft contains {word_count} words.", ["word_count"],
                "The current draft may be too short to develop its main ideas fully.", "high",
            )))
        elif word_count >= 180:
            strengths.append((30, self._signal(
                "idea_development_space", f"The draft contains {word_count} words.", ["word_count"],
                "The draft provides some space for developing ideas.", "medium", "strength",
            )))

        repeated_total = sum(repeated.values()) if isinstance(repeated, dict) else 0
        if repeated_total >= 6:
            words = ", ".join(f"{w} ({c})" for w, c in list(repeated.items())[:4])
            improvements.append((90, self._signal(
                "lexical_repetition", f"Repeated content-word forms include: {words}.",
                ["repeated_content_words", "word_count"],
                "The pattern may indicate that lexical repetition is worth reviewing.", "medium",
            )))
        elif word_count >= 100 and ttr >= 0.55:
            strengths.append((40, self._signal(
                "lexical_variety_signal", f"Surface-form type-token ratio is {ttr:.3f}.",
                ["type_token_ratio", "unique_word_count", "word_count"],
                "This draft shows a relatively broad range of word forms for its length.", "low", "strength",
            )))

        expected_connectives = max(1, sentence_count // 4)
        if sentence_count >= 4 and connective_count < expected_connectives:
            improvements.append((80, self._signal(
                "connective_use", f"Detected {connective_count} listed connectives across {sentence_count} sentences.",
                ["connective_count", "sentence_count"],
                "Explicit links between ideas may be worth checking; unlisted cohesive devices are not counted.", "low",
            )))
        elif connective_count >= 3:
            strengths.append((20, self._signal(
                "explicit_connections", f"Detected {connective_count} listed connectives.",
                ["connective_count"], "The draft provides some explicit signals between ideas.", "low", "strength",
            )))

        if sentence_count >= 3 and (average < 8 or average > 28):
            improvements.append((70, self._signal(
                "sentence_length_pattern", f"Average sentence length is {average:.2f} words.",
                ["average_sentence_length", "sentence_count"],
                "The current sentence-length pattern may be worth reviewing for readability and variation.", "low",
            )))

        if not strengths:
            strengths.append((1, self._signal(
                "task_engagement", f"The submitted draft contains {word_count} words in {sentence_count} detected sentences.",
                ["word_count", "sentence_count"],
                "A complete submitted draft gives a concrete basis for revision.", "low", "strength",
            )))
        if not improvements:
            improvements.append((1, self._signal(
                "targeted_review", "No high-priority surface-pattern flag crossed the v0.1.1 thresholds.",
                ["word_count", "connective_count", "repeated_content_words"],
                "A teacher-guided review of clarity and evidence is still worth conducting.", "low",
            )))

        selected = [max(strengths, key=lambda item: item[0])[1]]
        selected.extend(item[1] for item in sorted(improvements, key=lambda item: item[0], reverse=True)[:2])
        identified = [
            signal.model_copy(update={"diagnosis_id": f"D{index:03d}"})
            for index, signal in enumerate(selected, start=1)
        ]
        return DiagnosisResult(
            strengths=identified[:1],
            improvement_priorities=identified[1:],
            diagnosis_version=self.version,
            limitation=LIMITATION,
        )

    @staticmethod
    def _signal(category: str, evidence: str, source_metrics: list[str], message: str,
                confidence: str, kind: str = "improvement") -> DiagnosisSignal:
        cautious = message if any(w in message.lower() for w in ("may", "worth", "signal", "suggest")) else f"This signal suggests: {message}"
        return DiagnosisSignal(
            diagnosis_id="D000", category=category, evidence=evidence, source_metrics=source_metrics,
            confidence=confidence, interpretation=cautious, limitation=LIMITATION,
            rule_version=HeuristicDiagnoser.version, kind=kind,
        )
