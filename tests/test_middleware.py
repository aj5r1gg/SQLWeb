"""SQLWeb middleware HTTP integration tests."""

import sqlite3
import tempfile
import threading
import unittest

from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from server import initialize_database, make_handler


class MiddlewareHTTPTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.database = Path(self.tmp.name) / "middleware.db"

        initialize_database(self.database, middleware_version=1)

        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            make_handler(self.database),
        )

        self.thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True,
        )
        self.thread.start()

        self.base = (
            f"http://127.0.0.1:{self.server.server_port}"
        )

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.tmp.cleanup()

    def request(self, path):
        try:
            with urlopen(
                self.base + path,
                timeout=5,
            ) as response:
                return (
                    response.status,
                    response.headers.get_content_type(),
                    response.read(),
                )

        except HTTPError as error:
            try:
                return (
                    error.code,
                    error.headers.get_content_type(),
                    error.read(),
                )
            finally:
                error.close()

    def add_rule(
        self,
        rule_id,
        priority,
        path,
        action,
        status=403,
        body="Blocked by SQLite",
    ):
        with sqlite3.connect(self.database) as db:
            db.execute(
                """
                INSERT INTO middleware_rules
                (
                    rule_id, priority, enabled,
                    method, path, action,
                    status, content_type, body
                )
                VALUES (?, ?, 1, 'GET', ?, ?, ?,
                        'text/plain; charset=utf-8', ?)
                """,
                (
                    rule_id,
                    priority,
                    path,
                    action,
                    status,
                    body,
                ),
            )

    def test_default_deny(self):
        status, content_type, body = self.request(
            "/forbidden"
        )

        self.assertEqual(status, 403)
        self.assertEqual(content_type, "text/plain")
        self.assertEqual(
            body,
            b"403: Igor refuses entry.",
        )

    def test_explicit_allow_continues_to_router(self):
        status, _, body = self.request("/igor")

        self.assertEqual(status, 200)
        self.assertEqual(
            body,
            b"Yes, Master. Unfortunately, it works.",
        )

    def test_unmatched_middleware_allows_routing(self):
        status, content_type, body = self.request(
            "/health"
        )

        self.assertEqual(status, 200)
        self.assertEqual(
            content_type,
            "application/json",
        )
        self.assertIn(b'"status":"ok"', body)

    def test_allow_does_not_invent_route(self):
        status, _, body = self.request("/missing")

        self.assertEqual(status, 404)
        self.assertIn(b"requested row", body)

    def test_priority_precedence(self):
        self.add_rule(
            10, 1, "/forbidden", "ALLOW", 200, ""
        )

        status, _, _ = self.request("/forbidden")

        # Middleware allows the request, but no route exists.
        self.assertEqual(status, 404)

    def test_disabled_rule_ignored(self):
        self.add_rule(
            11, 1, "/forbidden", "ALLOW", 200, ""
        )

        with sqlite3.connect(self.database) as db:
            db.execute(
                """
                UPDATE middleware_rules
                SET enabled = 0
                WHERE rule_id = 11
                """
            )

        status, _, body = self.request("/forbidden")

        self.assertEqual(status, 403)
        self.assertEqual(
            body,
            b"403: Igor refuses entry.",
        )

    def test_dynamic_rule_without_restart(self):
        status, _, _ = self.request("/health")
        self.assertEqual(status, 200)

        self.add_rule(
            12,
            1,
            "/health",
            "DENY",
            403,
            "Igor has closed the laboratory.",
        )

        status, _, body = self.request("/health")

        self.assertEqual(status, 403)
        self.assertEqual(
            body,
            b"Igor has closed the laboratory.",
        )

    def test_middleware_intercepts_before_router(self):
        self.add_rule(
            13,
            1,
            "/",
            "DENY",
            451,
            "SQL has declared this page unavailable.",
        )

        status, _, body = self.request("/")

        self.assertEqual(status, 451)
        self.assertEqual(
            body,
            b"SQL has declared this page unavailable.",
        )

    def test_equal_priority_uses_rule_id(self):
        self.add_rule(
            20, 5, "/health", "ALLOW", 200, ""
        )
        self.add_rule(
            21, 5, "/health", "DENY", 403, "Denied"
        )

        status, _, _ = self.request("/health")

        self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main()
