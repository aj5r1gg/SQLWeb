"""Exercise the installed SQLWeb v2 pipeline without mocking SQL."""

import http.client
import sqlite3
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

import server
from tools.upgrade_middleware import upgrade


class LiveV2PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.tmp.name) / "live_v2.db"
        cls.httpd = None
        cls.thread = None

        try:
            server.initialize_database(cls.db_path)
            upgrade(cls.db_path)

            with sqlite3.connect(cls.db_path) as db:
                db.executemany(
                    """
                    INSERT INTO middleware_rules (
                        rule_id, priority, enabled, method, path,
                        action, status, content_type, body,
                        destination
                    )
                    VALUES (?, 10, 1, 'GET', ?, ?, ?,
                            'text/plain', '', ?)
                    """,
                    (
                        (100, "/old", "REDIRECT", 301, "/new"),
                        (101, "/temp", "REDIRECT", 302, "/new"),
                        (102, "/alias", "REWRITE", 200, "/health"),
                        (103, "/missing-alias", "REWRITE",
                         200, "/absent"),
                        (104, "/loop", "REWRITE", 200, "/loop"),
                    ),
                )

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
                    raise AssertionError("HTTP thread did not stop")
        finally:
            cls.tmp.cleanup()

    def request(self, method, path):
        conn = http.client.HTTPConnection(
            "127.0.0.1",
            self.httpd.server_port,
            timeout=5,
        )
        try:
            conn.request(method, path)
            response = conn.getresponse()
            return (
                response.status,
                response.getheader("Location"),
                response.getheader("Allow"),
                response.read(),
            )
        finally:
            conn.close()

    def test_01_redirect(self):
        self.assertEqual(
            self.request("GET", "/old"),
            (301, "/new", None, b""),
        )
        self.assertEqual(
            self.request("GET", "/temp"),
            (302, "/new", None, b""),
        )

    def test_02_rewrite(self):
        status, location, allow, body = self.request(
            "GET", "/alias"
        )
        self.assertEqual(status, 200)
        self.assertIsNone(location)
        self.assertIsNone(allow)
        self.assertIn(b'"status":"ok"', body)

    def test_03_missing_and_self_rewrite(self):
        for path in ("/missing-alias", "/loop"):
            with self.subTest(path=path):
                status, location, allow, body = self.request(
                    "GET", path
                )
                self.assertEqual(status, 404)
                self.assertIsNone(location)
                self.assertIsNone(allow)
                self.assertIn(b"404:", body)

    def test_04_method_policy(self):
        self.assertEqual(
            self.request("POST", "/old"),
            (405, None, "GET", b""),
        )
        self.assertEqual(
            self.request("HEAD", "/alias"),
            (405, None, "GET", b""),
        )

    def test_05_legacy_routes_survive_upgrade(self):
        status, location, allow, body = self.request(
            "GET", "/igor"
        )
        self.assertEqual(status, 200)
        self.assertIsNone(location)
        self.assertIsNone(allow)
        self.assertIn(b"Yes, Master", body)

    def test_06_v2_schema_selected(self):
        with sqlite3.connect(self.db_path) as db:
            self.assertEqual(
                server.select_request_pipeline(db),
                server.REQUEST_PIPELINE_V2_SQL,
            )


if __name__ == "__main__":
    unittest.main()
