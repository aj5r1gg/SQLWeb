"""Tests for the explicit SQLWeb middleware upgrade utility."""

import importlib.util
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/upgrade_middleware.py"
SCHEMA = ROOT / "sql/middleware_schema.sql"

spec = importlib.util.spec_from_file_location(
    "sqlweb_upgrade_middleware", TOOL
)
upgrade = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upgrade)


class MigrationUpgradeTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"

        with sqlite3.connect(self.db_path) as db:
            db.executescript(SCHEMA.read_text(encoding="utf-8"))
            db.execute(
                """
                INSERT INTO middleware_rules (
                    rule_id, priority, enabled, method, path,
                    action, status, content_type, body
                )
                VALUES (
                    99, 5, 0, 'GET', '/custom',
                    'DENY', 451, 'text/plain', 'Preserve me'
                )
                """
            )

    def tearDown(self):
        self.tmp.cleanup()

    def records(self):
        with sqlite3.connect(self.db_path) as db:
            return db.execute(
                """
                SELECT rule_id, priority, enabled, method, path,
                       action, status, content_type, body
                FROM middleware_rules
                ORDER BY rule_id
                """
            ).fetchall()

    def columns(self):
        with sqlite3.connect(self.db_path) as db:
            return [
                row[1] for row in db.execute(
                    "PRAGMA table_info(middleware_rules)"
                )
            ]

    def test_01_explicit_authorisation_required(self):
        before = self.records()

        result = subprocess.run(
            [
                sys.executable,
                str(TOOL),
                "--database",
                str(self.db_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--apply is required", result.stderr)
        self.assertEqual(self.records(), before)

    def test_02_successful_upgrade_preserves_records(self):
        before = self.records()

        result = subprocess.run(
            [
                sys.executable,
                str(TOOL),
                "--database",
                str(self.db_path),
                "--apply",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertEqual(
            result.returncode, 0,
            result.stdout + result.stderr,
        )
        self.assertIn(
            "Middleware schema upgraded to v2",
            result.stdout,
        )
        self.assertEqual(self.records(), before)
        self.assertEqual(self.columns()[-1], "destination")

    def test_03_repeated_upgrade_rejected(self):
        upgrade.upgrade(self.db_path)
        before = self.records()

        with self.assertRaisesRegex(
            ValueError, "already-upgraded"
        ):
            upgrade.upgrade(self.db_path)

        self.assertEqual(self.records(), before)

    def test_04_unknown_schema_rejected(self):
        with sqlite3.connect(self.db_path) as db:
            db.execute("DROP INDEX middleware_rules_lookup")

        before = self.records()

        with self.assertRaisesRegex(ValueError, "Unknown"):
            upgrade.upgrade(self.db_path)

        self.assertEqual(self.records(), before)
        self.assertNotIn("destination", self.columns())

    def test_05_foreign_key_dependency_rejected(self):
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                """
                CREATE TABLE dependent (
                    id INTEGER PRIMARY KEY,
                    rule_id INTEGER
                        REFERENCES middleware_rules(rule_id)
                )
                """
            )

        before = self.records()

        with self.assertRaisesRegex(
            ValueError, "foreign-key dependency"
        ):
            upgrade.upgrade(self.db_path)

        self.assertEqual(self.records(), before)

    def test_06_failed_migration_rolls_back(self):
        before = self.records()
        original = upgrade.statements()

        sabotaged = []
        found = False

        for statement in original:
            if "DROP TABLE middleware_rules;" in statement:
                sabotaged.append(
                    "SELECT * FROM deliberately_missing_table"
                )
                found = True

            sabotaged.append(statement)

        self.assertTrue(found)

        with patch.object(
            upgrade, "statements", return_value=sabotaged
        ):
            with self.assertRaises(sqlite3.OperationalError):
                upgrade.upgrade(self.db_path)

        self.assertEqual(self.records(), before)
        self.assertNotIn("destination", self.columns())

        with sqlite3.connect(self.db_path) as db:
            self.assertEqual(
                db.execute("PRAGMA integrity_check")
                .fetchone()[0],
                "ok",
            )


    def test_07_view_dependency_rejected(self):
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "CREATE VIEW rule_summary AS "
                "SELECT rule_id FROM middleware_rules"
            )

        before = self.records()

        with self.assertRaisesRegex(
            ValueError, "External middleware schema dependency"
        ):
            upgrade.upgrade(self.db_path)

        self.assertEqual(self.records(), before)
        self.assertNotIn("destination", self.columns())

    def test_08_trigger_dependency_rejected(self):
        with sqlite3.connect(self.db_path) as db:
            db.executescript("""
                CREATE TABLE audit_log (message TEXT);
                CREATE TRIGGER audit_route_change
                AFTER INSERT ON routes_dummy
                BEGIN
                    SELECT rule_id FROM middleware_rules;
                END;
            """.replace(
                "routes_dummy", "audit_log"
            ))

        before = self.records()

        with self.assertRaisesRegex(
            ValueError, "External middleware schema dependency"
        ):
            upgrade.upgrade(self.db_path)

        self.assertEqual(self.records(), before)
        self.assertNotIn("destination", self.columns())


if __name__ == "__main__":
    unittest.main()
