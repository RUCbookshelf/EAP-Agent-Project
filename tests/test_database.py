from app.database import Database
from app.feedback.service import FeedbackPipeline
from app.llm import LLMProvider, LocalDemoProvider, ProviderRouter
from app.models import StructuredFeedback
from app.prompts import PromptBuilder
import sqlite3


def test_database_creates_all_required_tables(settings):
    database = Database(settings.database_path)
    database.initialize()
    with database.connect() as connection:
        names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"students", "essays", "metrics", "diagnoses", "feedback_records", "exercises", "learner_history", "llm_call_records", "system_versions"} <= names


def test_v0_1_database_schema_is_migrated_in_place(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as connection:
        connection.executescript("""
        CREATE TABLE essays (essay_id INTEGER PRIMARY KEY, student_id TEXT, writing_prompt TEXT,
            genre TEXT, draft_stage TEXT, timed INTEGER, tool_use TEXT, essay_text TEXT, submitted_at TEXT);
        CREATE TABLE feedback_records (feedback_id INTEGER PRIMARY KEY, essay_id INTEGER,
            feedback_json TEXT, provider_name TEXT, model_name TEXT, success_status TEXT,
            fallback_reason TEXT, prompt_version TEXT, analysis_version TEXT, created_at TEXT);
        CREATE TABLE exercises (exercise_id INTEGER PRIMARY KEY, essay_id INTEGER,
            diagnosis_category TEXT, exercise_type TEXT, exercise_json TEXT, created_at TEXT);
        CREATE TABLE learner_history (history_id INTEGER PRIMARY KEY, student_id TEXT,
            essay_id INTEGER, history_summary TEXT, comparable_count INTEGER, created_at TEXT);
        """)
    database = Database(path)
    database.initialize()
    with database.connect() as connection:
        essay_columns = {row[1] for row in connection.execute("PRAGMA table_info(essays)")}
        feedback_columns = {row[1] for row in connection.execute("PRAGMA table_info(feedback_records)")}
        history_columns = {row[1] for row in connection.execute("PRAGMA table_info(learner_history)")}
    assert "time_limit_minutes" in essay_columns
    assert {"system_template_hash", "rendered_prompt_hash", "schema_version", "validation_status", "retry_count"} <= feedback_columns
    assert {"comparability_status", "history_evidence_json", "comparability_reasons_json"} <= history_columns


def test_essay_and_full_pipeline_are_saved(settings, submission):
    result = FeedbackPipeline(settings).submit(submission)
    database = Database(settings.database_path)
    counts = database.counts()
    assert result.essay_id == 1
    assert counts["essays"] == counts["metrics"] == counts["diagnoses"] == counts["feedback_records"] == 1
    assert counts["exercises"] >= 1
    assert counts["llm_call_records"] == 1
    record = database.get_feedback_record(1)
    assert record["analysis_version"] == "basic-analyzer-v0.1"
    assert record["prompt_version"] == "feedback-prompt-v0.7.1"
    assert len(record["system_template_hash"]) == 64
    assert len(record["user_template_hash"]) == 64
    assert len(record["rendered_prompt_hash"]) == 64
    assert record["schema_version"] == "structured-feedback-v0.7.1"
    assert record["validation_status"] == "passed"
    assert "API" not in " ".join(record.keys()).upper()
    call = database.get_llm_calls(1)[0]
    assert call["request_time"]
    assert call["response_time"]
    assert call["temperature"] == 0.2


def test_fallback_reason_redacts_provider_key(feedback_context):
    class LeakyProvider(LLMProvider):
        provider_name = "leaky-test"
        model_name = "leaky-test"
        configured = True
        api_key = "synthetic-secret-test-value"

        def generate(self, messages, *, temperature):
            raise RuntimeError(f"Bearer {self.api_key}")

    result = ProviderRouter(LeakyProvider()).generate(feedback_context)
    assert "synthetic-secret-test-value" not in result.fallback_reason
    assert "[REDACTED]" in result.fallback_reason


def test_unvalidated_primary_feedback_is_never_saved_as_formal_feedback(
    settings, submission, feedback_context
):
    bundle = PromptBuilder().build(feedback_context)
    valid = LocalDemoProvider().generate(bundle.messages, temperature=0.2)
    payload = valid.model_dump()
    payload["positive_finding"]["evidence_quote"] = "Fabricated quote not in essay."
    invalid = StructuredFeedback.model_validate(payload)

    class InvalidProvider(LLMProvider):
        provider_name = "invalid-primary"
        model_name = "invalid-test"
        configured = True

        def generate(self, messages, *, temperature):
            return invalid

    router = ProviderRouter(InvalidProvider())
    result = FeedbackPipeline(settings, router=router).submit(submission)
    database = Database(settings.database_path)
    record = database.get_feedback_record(result.essay_id)
    calls = database.get_llm_calls(result.essay_id)
    assert record["provider_name"] == "local-demo"
    assert "Fabricated quote not in essay." not in record["feedback_json"]
    assert [call["validation_status"] for call in calls] == ["failed", "failed", "passed"]
