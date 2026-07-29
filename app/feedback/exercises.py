from app.models import DiagnosisSignal, ExerciseItem


class ExerciseGenerator:
    """Generate replaceable, diagnosis-linked prototype practice tasks."""

    def generate(self, priorities: list[DiagnosisSignal], limits: dict | None = None) -> list[ExerciseItem]:
        limits = limits or {
            "max_for_high_confidence": 3, "max_for_medium_confidence": 2,
            "max_for_low_confidence": 1, "allow_for_monitored_signal": False,
        }
        exercises: list[ExerciseItem] = []
        for signal in priorities:
            if signal.selection_status not in {"selected_priority", "raw_signal"}:
                if not limits.get("allow_for_monitored_signal", False):
                    continue
            if signal.selection_status == "selected_priority" and signal.evidence_relevance_status != "verified":
                continue
            if signal.selection_status == "raw_signal" and signal.evidence_relevance_status not in {"verified", "insufficient_evidence"}:
                continue
            category = signal.category
            candidates = [
                ExerciseItem(
                    diagnosis_id=signal.diagnosis_id,
                    exercise_type="error_identification",
                    diagnosis_category=category,
                    instructions="Identify the place where this pattern is most visible in your draft.",
                    exercise_content=(
                        f"Review the signal for '{category}': {signal.evidence} "
                        "Mark one passage to revise."
                    ),
                    reference_guidance="Select a passage that is directly relevant to the cited prototype signal.",
                ),
                ExerciseItem(
                    diagnosis_id=signal.diagnosis_id,
                    exercise_type="sentence_rewrite",
                    diagnosis_category=category,
                    instructions="Rewrite one relevant sentence while preserving its intended meaning.",
                    exercise_content="Produce two alternatives, then explain which one is clearer.",
                    expected_response="Two sentence alternatives plus a one-sentence comparison.",
                ),
                ExerciseItem(
                diagnosis_id=signal.diagnosis_id,
                exercise_type="short_writing_transfer",
                diagnosis_category=category,
                instructions="Apply the revision principle in a new short passage.",
                exercise_content=(
                    f"Write 60–90 words on a related example while monitoring the '{category}' signal."
                ),
                reference_guidance=(
                    "Keep the new passage focused on the same diagnosis category; no score is assigned."
                ),
                ),
            ]
            maximum = int(limits.get(f"max_for_{signal.confidence}_confidence", 1))
            exercises.extend(candidates[:maximum])
        return exercises
