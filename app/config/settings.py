from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    database_path: Path
    llm_provider: str
    deepseek_api_key: str | None
    deepseek_base_url: str
    deepseek_model: str
    app_env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    streamlit_port: int = 8501
    api_base_url: str = "http://127.0.0.1:8000"
    application_version: str = "0.6.0"
    api_version: str = "v1"
    database_migration_version: int = 6
    prompt_version: str = "feedback-prompt-v0.5.0"
    analysis_version: str = "spacy-analyzer-v0.4.0"
    diagnosis_version: str = "prototype-diagnosis-v0.4.0"
    active_analyzer: str = "spacy"
    fallback_analyzer: str = "basic"
    spacy_model: str = "en_core_web_sm"
    mattr_window: int = 50
    local_repetition_window: int = 30
    long_sentence_threshold: int = 30
    analysis_configuration_version: str = "nlp-config-v0.4.0"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1800


def load_settings(env_file: Path | None = None) -> Settings:
    configured_env = os.getenv("WRITING_FEEDBACK_ENV_FILE")
    dotenv_path = env_file or (Path(configured_env) if configured_env else PROJECT_ROOT / ".env")
    load_dotenv(dotenv_path=dotenv_path, override=False)
    database_url = os.getenv("DATABASE_URL")
    database_value = database_url.removeprefix("sqlite:///") if database_url else os.getenv(
        "DATABASE_PATH", "data/writing_feedback.db"
    )
    raw_db = Path(database_value)
    db_path = raw_db if raw_db.is_absolute() else PROJECT_ROOT / raw_db
    api_host = os.getenv("API_HOST", "127.0.0.1")
    api_port = int(os.getenv("API_PORT", "8000"))
    return Settings(
        database_path=db_path,
        llm_provider=os.getenv("LLM_PROVIDER", "deepseek").lower(),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY") or None,
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        app_env=os.getenv("APP_ENV", "development"),
        api_host=api_host,
        api_port=api_port,
        streamlit_port=int(os.getenv("STREAMLIT_PORT", "8501")),
        api_base_url=os.getenv("API_BASE_URL", f"http://{api_host}:{api_port}").rstrip("/"),
        active_analyzer=os.getenv("ACTIVE_ANALYZER", "spacy").lower(),
        fallback_analyzer=os.getenv("FALLBACK_ANALYZER", "basic").lower(),
        spacy_model=os.getenv("SPACY_MODEL", "en_core_web_sm"),
        mattr_window=int(os.getenv("MATTR_WINDOW", "50")),
        local_repetition_window=int(os.getenv("LOCAL_REPETITION_WINDOW", "30")),
        long_sentence_threshold=int(os.getenv("LONG_SENTENCE_THRESHOLD", "30")),
        analysis_configuration_version=os.getenv("ANALYSIS_CONFIGURATION_VERSION", "nlp-config-v0.4.0"),
    )
