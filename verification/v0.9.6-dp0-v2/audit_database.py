from __future__ import annotations

"""v0.9.6-DP0-V2 read-only development-database integrity audit.

Opens SQLite databases strictly in read-only URI mode.  Never writes,
never extracts essay text into artifacts (row-level data is reduced to
SHA-256 hashes), and records only metadata, counts, and identifiers.
"""

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


USER_DOMAIN_TABLES = [
    "students",
    "essays",
    "feedback_records",
    "diagnoses",
    "metrics",
    "learner_history",
    "analysis_runs",
    "llm_call_records",
    "practice_targets",
    "exercise_instances",
]


def open_readonly(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def table_names(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [row[0] for row in rows]


def schema_snapshot(conn: sqlite3.Connection) -> dict[str, object]:
    tables = table_names(conn)
    schema_rows = conn.execute(
        "SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
    ).fetchall()
    schema_text = "\n".join(f"{t}|{n}|{s or ''}" for t, n, s in schema_rows)
    indexes = conn.execute(
        "SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    triggers = conn.execute(
        "SELECT name, tbl_name FROM sqlite_master WHERE type='trigger' ORDER BY name"
    ).fetchall()
    return {
        "table_count": len(tables),
        "tables": tables,
        "schema_sha256": hashlib.sha256(schema_text.encode("utf-8")).hexdigest(),
        "indexes": [{"name": n, "table": t} for n, t in indexes],
        "triggers": [{"name": n, "table": t} for n, t in triggers],
    }


def primary_key_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cols = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    return [col[1] for col in cols if col[5] > 0]


def stable_row_hash(conn: sqlite3.Connection, table: str) -> str:
    """SHA-256 over sorted serialized rows; never exposes cell content."""
    pk = primary_key_columns(conn, table)
    order = ", ".join(f'"{c}"' for c in pk) if pk else "1"
    digest = hashlib.sha256()
    for row in conn.execute(f'SELECT * FROM "{table}" ORDER BY {order}'):
        digest.update(repr(row).encode("utf-8", errors="replace"))
    return digest.hexdigest()


def audit_database(path: Path, *, include_domain_hashes: bool) -> dict[str, object]:
    with open_readonly(path) as conn:
        snapshot = schema_snapshot(conn)
        migrations = [
            row[0] for row in conn.execute("SELECT version FROM schema_migrations ORDER BY version")
        ]
        config_rows = conn.execute(
            "SELECT version, status, activated_at FROM configuration_versions ORDER BY version"
        ).fetchall()
        system_rows = conn.execute(
            "SELECT component, version, recorded_at FROM system_versions ORDER BY component"
        ).fetchall()
        system_digest = hashlib.sha256(
            "\n".join(f"{c}|{v}|{r}" for c, v, r in system_rows).encode("utf-8")
        ).hexdigest()
        row_counts = {
            table: conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in snapshot["tables"]
        }
        domain = {}
        for table in USER_DOMAIN_TABLES:
            if table not in row_counts:
                continue
            entry: dict[str, object] = {
                "row_count": row_counts[table],
                "primary_keys": primary_key_columns(conn, table),
                "pk_sha256": stable_row_hash(conn, table),
            }
            if include_domain_hashes:
                entry["all_columns_sha256"] = stable_row_hash(conn, table)
            domain[table] = entry
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        quick = conn.execute("PRAGMA quick_check").fetchone()[0]
        fk_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        user_version = conn.execute("PRAGMA user_version").fetchone()[0]
    return {
        "path": str(path),
        "user_version": user_version,
        "schema": snapshot,
        "schema_migrations": migrations,
        "configuration_versions": [
            {"version": v, "status": s, "activated_at": a} for v, s, a in config_rows
        ],
        "system_versions": {
            "row_count": len(system_rows),
            "rows": [{"component": c, "version": v, "recorded_at": r} for c, v, r in system_rows],
            "sha256_including_recorded_at": system_digest,
        },
        "row_counts": row_counts,
        "user_domain_tables": domain,
        "integrity_check": integrity,
        "quick_check": quick,
        "foreign_key_violations": [tuple(v) for v in fk_violations],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--domain-hashes", action="store_true")
    args = parser.parse_args()
    result = audit_database(Path(args.database), include_domain_hashes=args.domain_hashes)
    Path(args.output).write_text(
        json.dumps(result, indent=2, ensure_ascii=True, default=str), encoding="utf-8"
    )
    print(json.dumps({
        "user_version": result["user_version"],
        "table_count": result["schema"]["table_count"],
        "row_counts": result["row_counts"],
        "integrity_check": result["integrity_check"],
        "quick_check": result["quick_check"],
        "foreign_key_violations": len(result["foreign_key_violations"]),
        "written_to": args.output,
    }, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()