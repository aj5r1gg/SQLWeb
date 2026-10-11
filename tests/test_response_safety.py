"""Test rejection of invalid SQL-generated HTTP responses."""

import http.client
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from server import initialize_database, make_handler


class ResponseSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "safety.db"
        initialize_database(self.db, middleware_version=1)

        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), make_handler(self.db)
        )
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True,
        )
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.tmp.cleanup()

    def check_invalid(self, sql):
        client = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=5
        )
        try:
            with patch("server.REQUEST_PIPELINE_SQL", sql):
                client.request("GET", "/")
                response = client.getresponse()
                body = response.read()
                headers = response.getheaders()

            self.assertEqual(response.status, 500)
            self.assertIsNone(response.getheader("Allow"))
            self.assertEqual(
                body,
                b"500: Igor has encountered a complication.",
            )
            self.assertFalse(
                any(name.lower() == "x-injected" for name, _ in headers)
            )
        finally:
            client.close()

    def test_newline_in_allow_rejected(self):
        self.check_invalid("""
            SELECT 'ALLOW', 200, 'text/plain', 'OK',
                   NULL, '/', 'GET' || char(13,10)
                   || 'X-Injected: yes'
        """)

    def test_empty_allow_rejected(self):
        self.check_invalid("""
            SELECT 'ALLOW', 200, 'text/plain', 'OK',
                   NULL, '/', ''
        """)

    def test_invalid_status_rejected(self):
        self.check_invalid("""
            SELECT 'ALLOW', 999, 'text/plain', 'OK',
                   NULL, '/', NULL
        """)


if __name__ == "__main__":
    unittest.main()
