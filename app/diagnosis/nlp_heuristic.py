from __future__ import annotations

from app.models import AnalysisResult, DiagnosisResult, DiagnosisSignal

from .heuristic import HeuristicDiagnoser, LIMITATION


class NlpHeuristicDiagnoser(HeuristicDiagnoser):
    version = "prototype-diagnosis-v0.4.0"

    def diagnose(self, analysis: AnalysisResult) -> DiagnosisResult:
        base = super().diagnose(analysis)
        lexical = analysis.artifacts.get("lexical_features", {})
        connective = analysis.artifacts.get("connective_features", {})
        syntactic = analysis.artifacts.get("syntactic_features", {})
        details = lexical.get("repeated_content_word_details", [])
        priorities = [item for item in base.improvement_priorities if item.category != "lexical_repetition"]

        weighted = [item for item in details if item.get("diagnostic_weight") != "low"]
        if weighted:
            item = weighted[0]
            locations = [str(x.get("sentence_id")) for x in item.get("occurrences", [])[:5]]
            priorities.insert(0, DiagnosisSignal(
                diagnosis_id="D000", category="lexical_repetition",
                evidence=(f"Lemma '{item['lemma']}' occurs {item['count']} times; detected sentence locations: "
                          f"{', '.join(locations)}. Local cluster: {item.get('local_cluster_detected', False)}."),
                source_metrics=["repeated_content_words", "repetition_density", "prompt_keywords"],
                interpretation="This pattern may be worth reviewing for local lexical repetition.",
                confidence="medium" if item.get("local_cluster_detected") else "low",
                limitation=(LIMITATION + " Prompt keywords and necessary task terms are down-weighted; lemma/parser analysis may be inaccurate."),
                rule_version=self.version, kind="improvement",
            ))

        detected = connective.get("detected_connectives", [])
        for index, item in enumerate(priorities):
            if item.category == "connective_use":
                forms = sorted({x["normalized_form"] for x in detected})
                priorities[index] = item.model_copy(update={
                    "evidence": f"Detected {len(detected)} listed connective expressions: {', '.join(forms) or 'none in the current dictionary' }.",
                    "interpretation": "The range or distribution of explicit links may be worth checking; a dictionary miss does not mean cohesion is absent.",
                    "rule_version": self.version,
                })

        long_sentences = syntactic.get("long_sentence_candidates", [])
        if long_sentences and all(item.category != "sentence_structure_candidate" for item in priorities):
            candidate = long_sentences[0]
            priorities.append(DiagnosisSignal(
                diagnosis_id="D000", category="sentence_structure_candidate",
                evidence=f"Sentence {candidate['sentence_id']} contains {candidate['token_count']} parser-detected tokens: {candidate['text']}",
                source_metrics=["sentence_length_distribution", "long_sentence_candidates"],
                interpretation="This sentence may be worth a manual readability and structure check.",
                confidence="low", limitation=(LIMITATION + " A long sentence is not automatically complex, advanced, or erroneous."),
                rule_version=self.version, kind="improvement",
            ))

        if not priorities:
            priorities = [base.improvement_priorities[0].model_copy(update={"rule_version": self.version})]
        strength = base.strengths[0].model_copy(update={"rule_version": self.version})
        selected = [strength, *priorities[:2]]
        selected = [item.model_copy(update={"diagnosis_id": f"D{i:03d}", "rule_version": self.version}) for i, item in enumerate(selected, 1)]
        return DiagnosisResult(
            strengths=selected[:1], improvement_priorities=selected[1:],
            diagnosis_version=self.version,
            limitation=(LIMITATION + " spaCy-derived signals are parser candidates and require human confirmation."),
        )

