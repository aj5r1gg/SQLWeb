"""End-to-end SQL redirect and rewrite regression tests."""

import http.client
import sqlite3
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import server


ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "sql"


class HTTPTransformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.tmp.name) / "transforms.db"
        cls.httpd = None
        cls.thread = None

        try:
            server.initialize_database(cls.db_path, middleware_version=1)

            with sqlite3.connect(cls.db_path) as db:
                db.executescript(
                    (SQL / "middleware_upgrade_v2.sql")
                    .read_text(encoding="utf-8")
                )

                rules = [
                    (100, 10, "/old", "REDIRECT", 301, "/new"),
                    (101, 10, "/temporary", "REDIRECT", 302, "/new"),
                    (102, 10, "/preserve", "REDIRECT", 307, "/new"),
                    (103, 10, "/permanent", "REDIRECT", 308, "/new"),
                    (104, 10, "/alias", "REWRITE", 200, "/health"),
                    (105, 10, "/broken", "REWRITE", 200, "/absent"),
                    (106, 1, "/health", "DENY", 451, None),
                    (107, 10, "/loop", "REWRITE", 200, "/loop"),
                    (108, 20, "/old", "REDIRECT", 302, "/wrong"),
                    (109, 10, "/second", "REWRITE", 200, "/alias"),
                    (110, 10, "/equal", "REDIRECT", 302, "/first"),
                    (111, 10, "/equal", "REDIRECT", 308, "/second"),
                ]

                db.executemany(
                    """
                    INSERT INTO middleware_rules (
                        rule_id, priority, enabled, method, path,
                        action, status, content_type, body, destination
                    )
                    VALUES (
                        ?, ?, 1, 'GET', ?, ?, ?, 'text/plain', '', ?
                    )
                    """,
                    rules,
                )

            cls.pipeline = (
                SQL / "request_pipeline_v2.sql"
            ).read_text(encoding="utf-8")

            cls.httpd = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                server.make_handler(cls.db_path),
            )
            cls.thread = threading.Thread(
                target=cls.httpd.serve_forever,
                daemon=True,
            )
            cls.thread.start()
        except Exception:
            if cls.httpd is not None:
                cls.httpd.server_close()
            cls.tmp.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            if cls.httpd is not None:
                cls.httpd.shutdown()
                cls.httpd.server_close()
            if cls.thread is not None:
                cls.thread.join(timeout=5)
                if cls.thread.is_alive():
                    raise AssertionError("HTTP server did not terminate")
        finally:
            cls.tmp.cleanup()

    def request(self, method, path):
        client = http.client.HTTPConnection(
            "127.0.0.1", self.httpd.server_port, timeout=5
        )
        try:
            with patch.object(server, "REQUEST_PIPELINE_SQL", self.pipeline):
                client.request(method, path)
                response = client.getresponse()
                result = (
                    response.status,
                    response.getheader("Location"),
                    response.getheader("Allow"),
                    response.read(),
                )
            return result
        finally:
            client.close()

    def test_all_redirect_statuses(self):
        cases = (
            ("/old", 301),
            ("/temporary", 302),
            ("/preserve", 307),
            ("/permanent", 308),
        )
        for path, status in cases:
            with self.subTest(path=path):
                self.assertEqual(
                    self.request("GET", path),
                    (status, "/new", None, b""),
                )

    def test_internal_rewrite(self):
        status, location, allow, body = self.request("GET", "/alias")
        self.assertEqual(status, 200)
        self.assertIsNone(location)
        self.assertIsNone(allow)
        self.assertIn(b'"status":"ok"', body)

    def test_rewrite_boundaries(self):
        for path in ("/broken", "/loop", "/second"):
            with self.subTest(path=path):
                status, location, _, body = self.request("GET", path)
                self.assertEqual(status, 404)
                self.assertIsNone(location)
                self.assertIn(b"404:", body)

        self.assertEqual(self.request("GET", "/health")[0], 451)

    def test_rule_precedence(self):
        self.assertEqual(
            self.request("GET", "/old")[:2],
            (301, "/new"),
        )
        self.assertEqual(
            self.request("GET", "/equal")[:2],
            (302, "/first"),
        )

    def test_unsupported_methods(self):
        for method, path in (
            ("HEAD", "/alias"),
            ("POST", "/old"),
        ):
            with self.subTest(method=method):
                self.assertEqual(
                    self.request(method, path),
                    (405, None, "GET", b""),
                )


if __name__ == "__main__":
    unittest.main()
