"""Adversarial qualification of SQLWeb middleware."""

import sqlite3
import tempfile
import threading
import unittest

from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from server import (
    REQUEST_PIPELINE_SQL,
    initialize_database,
    make_handler,
)


class MiddlewareBoundaryTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.database = Path(self.tmp.name) / "boundary.db"
        initialize_database(self.database)

    def tearDown(self):
        self.tmp.cleanup()

    def test_injection_is_not_executed(self):
        with sqlite3.connect(self.database) as db:
            result = db.execute(
                REQUEST_PIPELINE_SQL,
                {
                    "method": "GET",
                    "path": "' OR 1=1 --",
                },
            ).fetchone()

        self.assertEqual(result[0], "ALLOW")

    def test_equal_priority_uses_lowest_id(self):
        with sqlite3.connect(self.database) as db:
            for rule_id, action in [
                (101, "DENY"),
                (100, "ALLOW"),
            ]:
                db.execute(
                    """
                    INSERT INTO middleware_rules
                    VALUES (?, 1, 1, 'GET', '/health',
                            ?, 403, 'text/plain', 'test')
                    """,
                    (rule_id, action),
                )

            result = db.execute(
                REQUEST_PIPELINE_SQL,
                {"method": "GET", "path": "/health"},
            ).fetchone()

        self.assertEqual(result[0], "ALLOW")

    def test_invalid_actions_rejected(self):
        with sqlite3.connect(self.database) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    """
                    INSERT INTO middleware_rules
                    VALUES (200, 1, 1, 'GET', '/x',
                            'EXECUTE', 200, 'text/plain', '')
                    """
                )

    def test_invalid_enabled_value_rejected(self):
        with sqlite3.connect(self.database) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    """
                    INSERT INTO middleware_rules
                    VALUES (201, 1, 7, 'GET', '/x',
                            'DENY', 403, 'text/plain', '')
                    """
                )

    def test_missing_middleware_table_returns_500(self):
        server = None
        thread = None

        with sqlite3.connect(self.database) as db:
            db.execute("DROP TABLE middleware_rules")

        try:
            server = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                make_handler(self.database),
            )
            thread = threading.Thread(
                target=server.serve_forever,
                daemon=True,
            )
            thread.start()

            url = (
                f"http://127.0.0.1:"
                f"{server.server_port}/health"
            )

            with self.assertRaises(HTTPError) as result:
                urlopen(url, timeout=5)

            error = result.exception
            try:
                self.assertEqual(error.code, 500)
                self.assertIn(
                    b"Igor has encountered a complication",
                    error.read(),
                )
            finally:
                error.close()

        finally:
            if server is not None:
                server.shutdown()
                server.server_close()
            if thread is not None:
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
