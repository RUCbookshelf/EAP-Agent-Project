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
    prompt_version: str = "feedback-prompt-v0.1.1"
    analysis_version: str = "basic-analyzer-v0.1"
    diagnosis_version: str = "prototype-diagnosis-v0.1.1"


def load_settings(env_file: Path | None = None) -> Settings:
    load_dotenv(dotenv_path=env_file or PROJECT_ROOT / ".env", override=False)
    raw_db = Path(os.getenv("DATABASE_PATH", "data/writing_feedback.db"))
    db_path = raw_db if raw_db.is_absolute() else PROJECT_ROOT / raw_db
    return Settings(
        database_path=db_path,
        llm_provider=os.getenv("LLM_PROVIDER", "deepseek").lower(),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY") or None,
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
    )
