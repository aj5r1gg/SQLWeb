"""Explicit, fail-closed SQLWeb middleware v1 -> v2 upgrade."""

import argparse
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "sql/middleware_schema.sql"
MIGRATION = ROOT / "sql/middleware_migrate_v2_candidate.sql"


def fingerprint(db):
    return db.execute("""
        SELECT type, name, tbl_name, sql
        FROM sqlite_schema
        WHERE name IN ('middleware_rules', 'middleware_rules_lookup')
        ORDER BY type, name
    """).fetchall()


def expected_schema():
    with sqlite3.connect(":memory:") as db:
        db.executescript(SCHEMA.read_text(encoding="utf-8"))
        return fingerprint(db)


def statements():
    source = MIGRATION.read_text(encoding="utf-8")
    chunks = []
    buffer = ""

    boundaries = [
        line.strip()
        for line in source.splitlines()
        if line.strip() in ("BEGIN IMMEDIATE;", "COMMIT;")
    ]
    if boundaries != ["BEGIN IMMEDIATE;", "COMMIT;"]:
        raise ValueError("Unexpected migration transaction boundaries")

    for line in source.splitlines(keepends=True):
        if line.strip() in ("BEGIN IMMEDIATE;", "COMMIT;"):
            continue
        buffer += line
        if sqlite3.complete_statement(buffer):
            chunks.append(buffer.strip())
            buffer = ""

    if buffer.strip() or not chunks:
        raise ValueError("Invalid migration SQL")

    return chunks


def upgrade(path):
    if not path.is_file():
        raise ValueError("Database file does not exist")

    db = sqlite3.connect(path, timeout=5)
    try:
        db.execute("BEGIN IMMEDIATE")

        if fingerprint(db) != expected_schema():
            raise ValueError("Unknown or already-upgraded schema")

        dependencies = db.execute("""
            SELECT type, name
            FROM sqlite_schema
            WHERE tbl_name = 'middleware_rules'
              AND type NOT IN ('table', 'index')
        """).fetchall()

        if dependencies:
            raise ValueError("Unsupported middleware dependencies")

        tables = db.execute("""
            SELECT name FROM sqlite_schema
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
        """).fetchall()

        for (table,) in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            for fk in db.execute(
                f"PRAGMA foreign_key_list({quoted})"
            ):
                if fk[2].lower() == "middleware_rules":
                    raise ValueError("Middleware foreign-key dependency")

        external_objects = db.execute("""
            SELECT type, name
            FROM sqlite_schema
            WHERE sql IS NOT NULL
              AND name NOT IN (
                  'middleware_rules',
                  'middleware_rules_lookup'
              )
              AND lower(sql) LIKE '%middleware_rules%'
        """).fetchall()

        if external_objects:
            raise ValueError(
                "External middleware schema dependency: "
                + repr(external_objects)
            )

        before = db.execute("""
            SELECT rule_id, priority, enabled, method, path,
                   action, status, content_type, body
            FROM middleware_rules ORDER BY rule_id
        """).fetchall()

        for statement in statements():
            db.execute(statement)

        after = db.execute("""
            SELECT rule_id, priority, enabled, method, path,
                   action, status, content_type, body
            FROM middleware_rules ORDER BY rule_id
        """).fetchall()

        if after != before:
            raise ValueError("Middleware records changed")

        columns = [
            row[1] for row in db.execute(
                "PRAGMA table_info(middleware_rules)"
            )
        ]
        if len(columns) != 10 or columns[-1] != "destination":
            raise ValueError("Unexpected upgraded schema")

        if db.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0] != "ok":
            raise ValueError("Database integrity failure")

        db.commit()
        print("PASS: Middleware schema upgraded to v2")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument(
        "--apply", action="store_true",
        help="Explicitly authorise migration",
    )
    args = parser.parse_args()

    if not args.apply:
        parser.error("No changes made: --apply is required")

    upgrade(args.database)


if __name__ == "__main__":
    main()
