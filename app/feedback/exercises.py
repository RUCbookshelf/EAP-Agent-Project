from app.models import DiagnosisSignal, ExerciseItem


class ExerciseGenerator:
    """Generate replaceable, diagnosis-linked prototype practice tasks."""

    def generate(self, priorities: list[DiagnosisSignal]) -> list[ExerciseItem]:
        exercises: list[ExerciseItem] = []
        for index, signal in enumerate(priorities):
            category = signal.category
            if index == 0:
                exercises.append(ExerciseItem(
                    diagnosis_id=signal.diagnosis_id, exercise_type="error_identification",
                    diagnosis_category=category,
                    instructions="Identify the place where this pattern is most visible in your draft.",
                    exercise_content=f"Review the signal for '{category}': {signal.evidence} Mark one passage to revise.",
                    reference_guidance="Select a passage that is directly relevant to the cited prototype signal.",
                ))
                exercises.append(ExerciseItem(
                    diagnosis_id=signal.diagnosis_id, exercise_type="sentence_rewrite",
                    diagnosis_category=category,
                    instructions="Rewrite one relevant sentence while preserving its intended meaning.",
                    exercise_content="Produce two alternatives, then explain which one is clearer.",
                    expected_response="Two sentence alternatives plus a one-sentence comparison.",
                ))
                exercises.append(ExerciseItem(
                    diagnosis_id=signal.diagnosis_id, exercise_type="short_writing_transfer",
                    diagnosis_category=category,
                    instructions="Apply the revision principle in a new short passage.",
                    exercise_content=f"Write 60–80 words on a related example while monitoring the '{category}' signal.",
                    reference_guidance="Keep the new passage focused on the same diagnosis category; no score is assigned.",
                ))
            else:
                exercises.append(ExerciseItem(
                    diagnosis_id=signal.diagnosis_id, exercise_type="short_writing_transfer",
                    diagnosis_category=category,
                    instructions="Apply the revision principle in a new short passage.",
                    exercise_content=f"Write 60–80 words on a related example while monitoring the '{category}' signal.",
                    reference_guidance="Keep the new passage focused on the same diagnosis category; no score is assigned.",
                ))
        return exercises
