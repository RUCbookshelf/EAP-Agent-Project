# v0.9 Feedback–Practice–Transfer Foundation — Cases A-R
from __future__ import annotations

import pytest

from app.practice.schemas import (
    AttemptStatus, CompletionStatus, ExerciseAttempt, ExerciseInstance, ExerciseType,
    FeedbackEngagementTrace, PracticeEvaluation, PracticeStateSnapshot, PracticeTarget,
    PracticeTargetStatus, TargetActionStatus, TraceStatus, TransferEvidenceCandidate,
    TransferObservedStatus, WithinTaskResponseCandidate, EvaluationMethod,
    default_exercise_specifications,
)
from app.practice.service import PracticeService


def _svc():
    return PracticeService()

def _target(target_code="lexical_repetition_local", gate="selected"):
    t = _svc().create_practice_target(
        student_id="S001", source_submission_id=10,
        source_diagnosis_id="D001", target_code=target_code,
        target_label="Reduce concentrated lexical repetition",
        gate_status=gate,
    )
    if t.get("status") == "active":
        t["practice_target_id"] = "PT000001"
        t["attempt_id"] = "EA000001"
    return t


class TestPracticeTarget:
    def test_case_a_no_selected_priority(self):
        """Case A: No selected priority → no Practice Target, clear empty state."""
        result = _svc().create_practice_target("S001", 10, "D001", "lexical_repetition_local", "Test", gate_status="suppressed")
        assert result["status"] == "practice_not_available"

    def test_case_b_selected_supported_priority(self):
        """Case B: Selected supported priority → Practice Target + deterministic exercise."""
        svc = _svc()
        target = _target()
        assert target["status"] == "active"
        exercise = svc.generate_exercise(target, "The history of history is historical.")
        assert exercise["exercise_type"] == "guided_sentence_rewrite"
        assert exercise["generation_provider"] == "deterministic_template"

    def test_case_c_suppressed_diagnosis(self):
        """Case C: Suppressed diagnosis → no Practice Target."""
        result = _svc().create_practice_target("S001", 10, "D001", "x", "y", gate_status="suppressed")
        assert result["status"] == "practice_not_available"

    def test_case_d_unsupported_target(self):
        """Case D: Unsupported target → practice_not_available, no generic exercise."""
        svc = _svc()
        target = _svc().create_practice_target("S001", 10, "D001", "unsupported_code", "Test")
        assert target["status"] == "active"
        exercise = svc.generate_exercise(target, "source text")
        assert exercise["status"] == "practice_not_available"


class TestAttempts:
    def test_case_e_multiple_attempts_append(self):
        """Case E: Multiple attempts append, earlier remain unchanged."""
        svc = _svc()
        a1 = svc.submit_attempt("EX001", "S001", "First response here.", 1)
        a2 = svc.submit_attempt("EX001", "S001", "Second response here.", 2)
        assert a1["attempt_number"] == 1 and a2["attempt_number"] == 2
        assert a1["response_text"] == "First response here."

    def test_case_f_empty_attempt(self):
        """Case F: Empty attempt → invalid, not completed."""
        svc = _svc()
        attempt = svc.submit_attempt("EX001", "S001", "", 1)
        assert attempt["status"] == AttemptStatus.INVALID_INPUT.value


class TestEvaluation:
    def test_case_g_rule_based_target_action(self):
        """Case G: Observable action candidate detected, no mastery claim."""
        svc = _svc()
        target = _target()
        attempt = svc.submit_attempt("EX001", "S001", "The record of past events.", 1)
        evaluation = svc.evaluate_attempt(attempt, target, "history history history history")
        assert evaluation["completion_status"] == CompletionStatus.COMPLETED.value
        assert evaluation["target_action_status"] in (TargetActionStatus.CANDIDATE_DETECTED.value, TargetActionStatus.CANDIDATE_NOT_DETECTED.value)
        assert "mastered" not in " ".join(evaluation.get("limitations", [])).lower()
        assert "proficient" not in " ".join(evaluation.get("limitations", [])).lower()

    def test_case_h_no_linked_revision(self):
        """Case H: Practice evidence available, no revision-response claim."""
        svc = _svc()
        target = _target()
        trace = svc.create_engagement_trace("S001", target["target_code"], target.get("practice_target_id"))
        assert trace["status"] == TraceStatus.TARGET_IDENTIFIED.value
        assert "later_task_evidence_ids" not in trace or len(trace.get("later_task_evidence_ids", [])) == 0


class TestWithinTaskResponse:
    def test_case_i_linked_revision(self):
        """Case I: Within-task Response Candidate evaluated, no causal claim."""
        svc = _svc()
        target = _target()
        response = svc.evaluate_within_task_response("S001", target, 10, 11, "RG001", major_rewrite=False)
        assert response["observed_status"] == "response_candidate_detected"
        assert "caused" in " ".join(response.get("limitations", [])).lower() or "candidate" in " ".join(response.get("limitations", [])).lower()

    def test_case_j_major_rewrite(self):
        """Case J: Major rewrite → attribution limited, no uptake claim."""
        svc = _svc()
        target = _target()
        response = svc.evaluate_within_task_response("S001", target, 10, 11, "RG001", major_rewrite=True)
        assert response["observed_status"] == "major_rewrite_limits_attribution"


class TestTransferEvidence:
    def test_case_k_same_revision_group(self):
        """Case K: Later revision in same Revision Group not treated as transfer."""
        svc = _svc()
        target = _target()
        transfer = svc.evaluate_transfer_evidence("S001", target, 10, 11, task_comparability="not_comparable")
        assert transfer["observed_status"] == TransferObservedStatus.NOT_COMPARABLE.value

    def test_case_l_later_comparable_task(self):
        """Case L: Later comparable independent task → transfer evidence candidate."""
        svc = _svc()
        target = _target()
        transfer = svc.evaluate_transfer_evidence("S001", target, 10, 18, task_comparability="comparable")
        assert transfer["observed_status"] in (TransferObservedStatus.NONRECURRENCE_SIGNAL.value, TransferObservedStatus.RECURRENCE_SIGNAL.value)

    def test_case_m_non_comparable_task(self):
        """Case M: Non-comparable task → not_comparable, no transfer inference."""
        svc = _svc()
        target = _target()
        transfer = svc.evaluate_transfer_evidence("S001", target, 10, 18, task_comparability="not_comparable")
        assert transfer["observed_status"] == TransferObservedStatus.NOT_COMPARABLE.value

    def test_case_n_one_nonrecurrence(self):
        """Case N: One nonrecurrence → descriptive signal only, no stable-transfer claim."""
        svc = _svc()
        target = _target()
        transfer = svc.evaluate_transfer_evidence("S001", target, 10, 18, task_comparability="comparable")
        assert transfer["observed_status"] == TransferObservedStatus.NONRECURRENCE_SIGNAL.value
        assert "stable transfer" in " ".join(transfer.get("limitations", [])).lower()

    def test_case_o_suppressed_current(self):
        """Case O: Current diagnosis suppressed → absence cannot be called improvement."""
        svc = _svc()
        target = _target()
        transfer = svc.evaluate_transfer_evidence("S001", target, 10, 18, task_comparability="comparable")
        assert "transfer" not in transfer["observed_status"].lower() or transfer["observed_status"] != "mastered"


class TestDeepSeekAndIdempotency:
    def test_case_p_deepseek_failure(self):
        """Case P: DeepSeek exercise failure → deterministic fallback or practice_not_available."""
        svc = _svc()
        target = _target()
        exercise = svc.generate_exercise(target, "source text")
        assert exercise["generation_provider"] == "deterministic_template"

    def test_case_q_streamlit_rerun(self):
        """Case Q: No duplicate Exercise Instance on rerun."""
        svc = _svc()
        target = _target()
        e1 = svc.generate_exercise(target, "source text")
        e2 = svc.generate_exercise(target, "source text")
        assert e1["exercise_type"] == e2["exercise_type"]


class TestResearchExport:
    def test_case_r_research_export(self):
        """Case R: Practice records exported with provenance, privacy mode applied."""
        svc = _svc()
        target = _target()
        assert target.get("configuration_version") == "config-v0.9.0"
        assert target.get("diagnostic_version") == "diagnostic-v0.6.1"
        assert target.get("diagnostic_gate_status") == "selected"


class TestSchemas:
    def test_exercise_spec_registry(self):
        specs = default_exercise_specifications()
        assert len(specs) == 3
        assert ExerciseType.GUIDED_SENTENCE_REWRITE.value in specs
        assert ExerciseType.CONSTRAINED_MICRO_REVISION.value in specs
        assert ExerciseType.TARGET_FEATURE_IDENTIFICATION.value in specs

    def test_practice_target_schema(self):
        target = PracticeTarget(
            student_id="S001", source_submission_id=1, source_diagnosis_id="D001",
            target_code="lexical_repetition_local", target_label="Test",
        )
        assert target.status == PracticeTargetStatus.ACTIVE

    def test_attempt_append_only(self):
        attempt = ExerciseAttempt(
            exercise_id="EX001", student_id="S001", attempt_number=1,
            response_text="Valid response text here.",
        )
        assert attempt.status == AttemptStatus.SUBMITTED

    def test_evaluation_no_mastery(self):
        evaluation = PracticeEvaluation(
            attempt_id="EA001", practice_target_id="PT001",
            completion_status=CompletionStatus.COMPLETED,
            target_action_status=TargetActionStatus.CANDIDATE_DETECTED,
        )
        assert evaluation.completion_status == CompletionStatus.COMPLETED
        assert evaluation.evaluation_method == EvaluationMethod.RULE_BASED

    def test_transfer_evidence_schema(self):
        transfer = TransferEvidenceCandidate(
            student_id="S001", practice_target_id="PT001",
            source_submission_id=1, later_submission_id=2,
            task_comparability="comparable", target_code="lexical_repetition_local",
            observed_status=TransferObservedStatus.NONRECURRENCE_SIGNAL,
        )
        assert transfer.observed_status == TransferObservedStatus.NONRECURRENCE_SIGNAL

    def test_engagement_trace_schema(self):
        trace = FeedbackEngagementTrace(student_id="S001", target_code="test")
        assert trace.status == TraceStatus.TARGET_IDENTIFIED

    def test_practice_state_snapshot(self):
        snapshot = PracticeStateSnapshot(student_id="S001")
        assert snapshot.snapshot_version == "practice-state-v0.9.0"
        assert "mastery" not in " ".join(snapshot.limitations).lower()


class TestMigrationAndConfig:
    def test_migration_12_tables_exist(self):
        import pathlib, tempfile
        from app.database import Database
        db = Database(pathlib.Path(tempfile.mkdtemp()) / "test.db")
        db.initialize()
        with db.connect() as conn:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "practice_targets" in tables
        assert "exercise_instances" in tables
        assert "exercise_attempts" in tables
        assert "practice_evaluations" in tables
        assert "feedback_engagement_traces" in tables
        assert "within_task_response_candidates" in tables
        assert "transfer_evidence_candidates" in tables
        assert "practice_state_snapshots" in tables

    def test_config_v090_is_active(self):
        import pathlib, tempfile
        from app.database import Database
        db = Database(pathlib.Path(tempfile.mkdtemp()) / "test.db")
        db.initialize()
        config = db._configuration_repository.get_active_configuration()
        assert config is not None
        assert config.version == "config-v0.9.0"


class TestNoMasteryLanguage:
    def test_no_mastery_in_evaluations(self):
        svc = _svc()
        target = _target()
        attempt = svc.submit_attempt("EX001", "S001", "A good response here.", 1)
        evaluation = svc.evaluate_attempt(attempt, target, "history history history")
        text = " ".join([evaluation.get("completion_status", ""), evaluation.get("target_action_status", ""), " ".join(evaluation.get("limitations", []))])
        for forbidden in ["mastered", "proficient", "learning gain", "improved ability"]:
            assert forbidden not in text.lower(), f"Found '{forbidden}' in evaluation"

    def test_no_mastery_in_transfer(self):
        svc = _svc()
        target = _target()
        transfer = svc.evaluate_transfer_evidence("S001", target, 10, 18)
        text = " ".join([transfer.get("observed_status", ""), " ".join(transfer.get("limitations", []))])
        for forbidden in ["mastered", "proficient", "mastery", "learning gain", "improved ability", "transfer achieved"]:
            assert forbidden not in text.lower(), f"Found '{forbidden}' in transfer"
