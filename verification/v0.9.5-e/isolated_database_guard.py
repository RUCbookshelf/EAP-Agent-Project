from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.config import load_settings
from app.database import Database


DEV_DB = (ROOT / "data" / "writing_feedback.db").resolve()
SEEDED_TABLES = {"schema_migrations", "configuration_versions", "configuration_audit"}


def resolved_paths() -> tuple[Path, Path]:
    assert os.getenv("PYTHON_DOTENV_DISABLED", "").casefold() in {"1", "true", "yes", "on"}
    assert "DATABASE_URL" not in os.environ
    assert os.getenv("LLM_PROVIDER") == "local"
    temp_root = Path(os.environ["V095E_TEMP_ROOT"]).resolve()
    expected = Path(os.environ["DATABASE_PATH"]).resolve()
    settings = load_settings()
    effective = Path(settings.database_path).resolve()
    print(f"effective_database_path={effective}")
    print(f"temporary_root={temp_root}")
    print(f"llm_provider={settings.llm_provider}")
    assert effective == expected
    assert effective.is_relative_to(temp_root)
    assert effective != temp_root
    assert effective != DEV_DB
    assert ROOT / "data" not in effective.parents
    assert settings.llm_provider == "local"
    return temp_root, effective


def prepare() -> None:
    _, path = resolved_paths()
    assert not path.exists(), f"Fresh database path already exists: {path}"
    database = Database(path)
    database.initialize()
    with database.connect() as connection:
        actual = Path(connection.execute("PRAGMA database_list").fetchone()[2]).resolve()
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        tables = sorted(
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        )
        counts = {
            table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            for table in tables
        }
        active = connection.execute(
            "SELECT version FROM configuration_versions WHERE status='active'"
        ).fetchone()[0]
    assert actual == path
    assert version == 12
    assert len(tables) == 33
    assert active == "config-v0.9.0"
    assert all(count == 0 for table, count in counts.items() if table not in SEEDED_TABLES)
    assert counts["schema_migrations"] == 12
    print("fresh_database_initial_state=PASS")
    print(f"migration={version}")
    print(f"table_count={len(tables)}")
    print(f"active_configuration={active}")


def verify() -> None:
    _, path = resolved_paths()
    assert path.exists(), f"Verification database was not created: {path}"
    database = Database(path)
    with database.connect() as connection:
        actual = Path(connection.execute("PRAGMA database_list").fetchone()[2]).resolve()
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    assert actual == path
    assert version == 12
    assert integrity == "ok"
    assert violations == []
    print("fresh_database_final_state=PASS")
    print(f"integrity_check={integrity}")
    print("foreign_key_violations=0")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "verify"))
    args = parser.parse_args()
    prepare() if args.mode == "prepare" else verify()


if __name__ == "__main__":
    main()
