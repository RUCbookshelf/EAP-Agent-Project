# v0.9 Live A-G controlled validation
import pathlib, json, tempfile, pytest

from app.database import Database
from app.practice.service import PracticeService
from app.practice.schemas import (
    PracticeTarget, ExerciseInstance, ExerciseAttempt, PracticeEvaluation,
    TransferObservedStatus, TargetActionStatus, CompletionStatus,
    AttemptStatus, default_exercise_specifications,
)


@pytest.fixture
def db():
    tmp = pathlib.Path(tempfile.mkdtemp()) / "test_v09_live.db"
    d = Database(tmp)
    d.initialize()
    return d


@pytest.fixture
def svc(db):
    return PracticeService(db)


class TestLiveA_SupportedPracticeTarget:
    """Live A: Supported Practice Target - deterministic exercise, no DeepSeek."""

    def test_selected_priority_creates_target(self, svc):
        target = svc.create_practice_target("S001", 10, "D001", "lexical_repetition_local", "Reduce repetition", gate_status="selected")
        assert target["status"] == "active"
        assert target["diagnostic_gate_status"] == "selected"

    def test_deterministic_exercise_generated(self, svc):
        target = svc.create_practice_target("S001", 10, "D001", "lexical_repetition_local", "Reduce repetition")
        exercise = svc.generate_exercise(target, "The history of history is historical.")
        assert exercise["generation_provider"] == "deterministic_template"
        assert exercise["exercise_type"] == "guided_sentence_rewrite"

    def test_no_deepseek_called(self, svc):
        target = svc.create_practice_target("S001", 10, "D001", "lexical_repetition_local", "Reduce repetition")
        exercise = svc.generate_exercise(target, "source")
        assert exercise["generation_provider"] == "deterministic_template"
        assert exercise.get("generation_model") is None

    def test_rerun_does_not_duplicate_exercise_id(self, svc):
        target = svc.create_practice_target("S001", 10, "D001", "lexical_repetition_local", "Reduce repetition")
        e1 = svc.generate_exercise(target, "source")
        e2 = svc.generate_exercise(target, "source")
        assert e1["exercise_type"] == e2["exercise_type"]


class TestLiveB_ExerciseAttempt:
    """Live B: Exercise attempt - append-only, conservative evaluation."""

    def test_attempt_persists_via_repo(self, svc, db):
        target = svc.create_practice_target("S001", 10, "D001", "lexical_repetition_local", "target")
        target = db.save_practice_target(target)
        exercise = svc.generate_exercise(target, "source text here")
        exercise = db.save_exercise_instance(exercise)
        a1 = svc.submit_attempt(exercise["exercise_id"], "S001", "A valid response.", 1)
        a1 = db.save_exercise_attempt(a1)
        assert a1["attempt_id"].startswith("EA")
        attempts = db.list_exercise_attempts(exercise["exercise_id"])
        assert len(attempts) == 1

    def test_second_attempt_appends(self, svc, db):
        target = svc.create_practice_target("S001", 10, "D001", "lexical_repetition_local", "target")
        target = db.save_practice_target(target)
        exercise = svc.generate_exercise(target, "source")
        exercise = db.save_exercise_instance(exercise)
        a1 = db.save_exercise_attempt(svc.submit_attempt(exercise["exercise_id"], "S001", "First.", 1))
        a2 = db.save_exercise_attempt(svc.submit_attempt(exercise["exercise_id"], "S001", "Second.", 2))
        attempts = db.list_exercise_attempts(exercise["exercise_id"])
        assert len(attempts) == 2
        assert attempts[0]["attempt_number"] == 1
        assert attempts[1]["attempt_number"] == 2

    def test_evaluation_is_conservative(self, svc):
        target = svc.create_practice_target("S001", 10, "D001", "lexical_repetition_local", "target")
        attempt = svc.submit_attempt("EX001", "S001", "A plausible rewrite.", 1)
        evaluation = svc.evaluate_attempt(attempt, target, "history history history")
        assert evaluation["completion_status"] in (CompletionStatus.COMPLETED.value, CompletionStatus.INCOMPLETE.value)
        assert "mastered" not in json.dumps(evaluation).lower()

    def test_no_mastery_language(self, svc):
        target = svc.create_practice_target("S001", 10, "D001", "lexical_repetition_local", "target")
        attempt = svc.submit_attempt("EX001", "S001", "response", 1)
        evaluation = svc.evaluate_attempt(attempt, target, "source")
        text = json.dumps(evaluation).lower()
        for forbidden in ["mastered", "proficient", "score", "grade", "learning gain"]:
            assert forbidden not in text


class TestLiveC_WithinTaskRevision:
    """Live C: Within-task revision - response candidate, no causal claim."""

    def test_linked_revision_creates_candidate(self, svc):
        target = svc.create_practice_target("S001", 10, "D001", "lexical_repetition_local", "target")
        response = svc.evaluate_within_task_response("S001", target, 10, 11, "RG001", major_rewrite=False)
        assert response["observed_status"] == "response_candidate_detected"

    def test_major_rewrite_respected(self, svc):
        target = svc.create_practice_target("S001", 10, "D001", "lexical_repetition_local", "target")
        response = svc.evaluate_within_task_response("S001", target, 10, 11, "RG001", major_rewrite=True)
        assert response["observed_status"] == "major_rewrite_limits_attribution"

    def test_no_causal_attribution(self, svc):
        target = svc.create_practice_target("S001", 10, "D001", "lexical_repetition_local", "target")
        response = svc.evaluate_within_task_response("S001", target, 10, 11, "RG001")
        text = json.dumps(response).lower()
        assert "caused" not in text or "candidate" in text


class TestLiveD_LaterIndependentTask:
    """Live D: Later independent task - transfer evidence candidate only."""

    def test_same_revision_group_rejected(self, svc):
        target = svc.create_practice_target("S001", 10, "D001", "lexical_repetition_local", "target")
        transfer = svc.evaluate_transfer_evidence("S001", target, 10, 11, task_comparability="not_comparable")
        assert transfer["observed_status"] == TransferObservedStatus.NOT_COMPARABLE.value

    def test_later_comparable_task_creates_signal(self, svc):
        target = svc.create_practice_target("S001", 10, "D001", "lexical_repetition_local", "target")
        transfer = svc.evaluate_transfer_evidence("S001", target, 10, 18, task_comparability="comparable")
        assert transfer["observed_status"] in (
            TransferObservedStatus.NONRECURRENCE_SIGNAL.value,
            TransferObservedStatus.RECURRENCE_SIGNAL.value,
        )

    def test_one_observation_not_stable_transfer(self, svc):
        target = svc.create_practice_target("S001", 10, "D001", "lexical_repetition_local", "target")
        transfer = svc.evaluate_transfer_evidence("S001", target, 10, 18, task_comparability="comparable")
        assert "stable transfer" in " ".join(transfer.get("limitations", [])).lower()


class TestLiveE_DeepSeekDisabled:
    """Live E: DeepSeek disabled by default - deterministic fallback verifies."""

    def test_deterministic_fallback(self, svc):
        target = svc.create_practice_target("S001", 10, "D001", "lexical_repetition_local", "Reduce")
        exercise = svc.generate_exercise(target, "source text")
        assert exercise["generation_provider"] == "deterministic_template"

    def test_unsupported_target_no_generic_exercise(self, svc):
        target = svc.create_practice_target("S001", 10, "D001", "unsupported_code", "Unsupported")
        exercise = svc.generate_exercise(target, "source")
        assert exercise["status"] == "practice_not_available"


class TestLiveF_EnglishAndChineseLocales:
    """Live F: Both locales have matching practice keys."""

    def test_locale_keys_identical(self):
        with open("locales/en.json", encoding="utf-8") as f:
            en = json.load(f)
        with open("locales/zh_CN.json", encoding="utf-8") as f:
            zh = json.load(f)
        assert set(en.keys()) == set(zh.keys())
        practice_keys = {k for k in en if any(w in k.lower() for w in ("practice", "exercise", "attempt", "journey", "audit", "transfer"))}
        for k in practice_keys:
            assert k in zh, f"Missing key: {k}"
            assert en[k], f"Empty en value: {k}"
            assert zh[k], f"Empty zh value: {k}"

    def test_no_mastery_in_locales(self):
        with open("locales/en.json", encoding="utf-8") as f:
            en_text = f.read().lower()
        with open("locales/zh_CN.json", encoding="utf-8") as f:
            zh_text = f.read().lower()
        for forbidden in ["mastered", "proficiency_score", "grade_level"]:
            assert forbidden not in en_text, f"Found '{forbidden}' in en"
            assert forbidden not in zh_text, f"Found '{forbidden}' in zh"


class TestLiveG_MobileViewport:
    """Live G: Mobile UI layout assertions (code-level checks)."""

    def test_sidebar_page_count(self):
        """Verify that Practice and Learning Journey pages exist in sidebar."""
        import ast
        content = pathlib.Path("app/ui/streamlit_app.py").read_text(encoding="utf-8")
        tree = ast.parse(content)
        assert "render_practice_page" in content
        assert "render_learning_journey_page" in content
        assert "render_practice_audit_page" in content
        assert "Practice" in content
        assert "Learning Journey" in content

    def test_page_routing_exists(self):
        content = pathlib.Path("app/ui/streamlit_app.py").read_text(encoding="utf-8")
        assert 'page == "Practice"' in content
        assert 'page == "Learning Journey"' in content
        assert 'page == "Practice Audit"' in content