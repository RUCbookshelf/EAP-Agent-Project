from __future__ import annotations

import json
from pathlib import Path

from app.config import PROJECT_ROOT, load_settings
from app.database import Database
from app.prompts.versioning import (
    PROMPT_MANIFEST_PATH,
    SYSTEM_TEMPLATE_PATH,
    system_template_hash,
    validate_prompt_versioning,
)
from app.prompts import versioning_v04, versioning_v05


def initialize() -> dict[str, object]:
    settings = load_settings()
    (PROJECT_ROOT / "data").mkdir(parents=True, exist_ok=True)
    if not SYSTEM_TEMPLATE_PATH.is_file() or not SYSTEM_TEMPLATE_PATH.read_text(encoding="utf-8").strip():
        raise RuntimeError("Required system prompt template is missing or empty")
    validate_prompt_versioning()
    versioning_v04.validate_prompt_versioning()
    prompt_manifest = versioning_v05.validate_prompt_versioning()
    database = Database(settings.database_path)
    database.initialize()
    active_configuration = database.get_active_configuration()
    with database.connect() as connection:
        tables = sorted(
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        )
    return {
        "status": "PASS",
        "database_path": str(settings.database_path),
        "database_table_count": len(tables),
        "prompt_template_found": True,
        "prompt_manifest_found": (
            PROMPT_MANIFEST_PATH.is_file()
            and versioning_v04.PROMPT_MANIFEST_PATH.is_file()
            and versioning_v05.PROMPT_MANIFEST_PATH.is_file()
        ),
        "prompt_version": prompt_manifest["prompt_version"],
        "database_migration_version": database.migration_version(),
        "active_configuration_version": active_configuration.version,
        "system_template_hash": versioning_v05.system_template_hash(),
        "llm_provider": settings.llm_provider,
        "deepseek_model": settings.deepseek_model,
        "deepseek_base_url_configured": bool(settings.deepseek_base_url),
        "deepseek_key_configured": bool(settings.deepseek_api_key),
        "api_key_recorded": False,
    }


if __name__ == "__main__":
    print(json.dumps(initialize(), indent=2))
