from __future__ import annotations

import json

from app.config import load_settings
from app.database import Database, LATEST_MIGRATION_VERSION


def main() -> None:
    settings = load_settings()
    repository = Database(settings.database_path)
    repository.initialize()
    version = repository._system_repository.migration_version()
    if version != LATEST_MIGRATION_VERSION:
        raise SystemExit(f"Migration stopped at {version}; expected {LATEST_MIGRATION_VERSION}.")
    print(json.dumps({
        "status": "PASS",
        "database_path": str(settings.database_path),
        "migration_version": version,
    }, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
