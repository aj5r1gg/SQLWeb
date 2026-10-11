"""HTTP transport boundary qualification."""

import http.client
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from server import initialize_database, make_handler


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        db = Path(self.tmp.name) / "transport.db"
        initialize_database(db, middleware_version=1)

        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), make_handler(db)
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

    def connect(self):
        return http.client.HTTPConnection(
            "127.0.0.1",
            self.server.server_port,
            timeout=5,
        )

    def test_post_body_rejected_and_connection_closed(self):
        client = self.connect()
        try:
            client.request("POST", "/", body=b"test=123")
            response = client.getresponse()

            self.assertEqual(response.status, 405)
            self.assertEqual(response.getheader("Allow"), "GET")
            self.assertEqual(
                response.getheader("Connection"), "close"
            )
            self.assertEqual(response.read(), b"")
            self.assertTrue(response.will_close)
        finally:
            client.close()

    def test_head_has_no_body(self):
        client = self.connect()
        try:
            client.request("HEAD", "/")
            response = client.getresponse()

            self.assertEqual(response.status, 405)
            self.assertEqual(response.getheader("Allow"), "GET")
            self.assertEqual(
                response.getheader("Content-Length"), "0"
            )
            self.assertEqual(response.read(), b"")
        finally:
            client.close()

    def test_get_still_uses_sql_route(self):
        client = self.connect()
        try:
            client.request("GET", "/health")
            response = client.getresponse()

            self.assertEqual(response.status, 200)
            self.assertEqual(
                response.getheader("Content-Type"),
                "application/json",
            )
            self.assertIn(b'"status":"ok"', response.read())
        finally:
            client.close()


if __name__ == "__main__":
    unittest.main()
