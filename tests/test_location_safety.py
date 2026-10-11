"""Security qualification of SQL-controlled Location headers."""

import http.client
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import server


class LocationSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "location.db"
        server.initialize_database(self.db)

        self.httpd = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            server.make_handler(self.db),
        )
        self.thread = threading.Thread(
            target=self.httpd.serve_forever,
            daemon=True,
        )
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)
        self.tmp.cleanup()

    def request_with_location(self, location_sql, status_sql='302'):
        sql = f"""
            SELECT 'REDIRECT', {status_sql}, 'text/plain', '',
                   {location_sql}, '/', NULL
        """

        with patch.object(server, "REQUEST_PIPELINE_SQL", sql):
            client = http.client.HTTPConnection(
                "127.0.0.1",
                self.httpd.server_port,
                timeout=5,
            )
            try:
                client.request("GET", "/")
                response = client.getresponse()
                result = (
                    response.status,
                    response.getheaders(),
                    response.read(),
                )
            finally:
                client.close()

        return result

    def assert_rejected(self, location_sql, status_sql='302'):
        status, headers, body = self.request_with_location(
            location_sql, status_sql
        )
        names = [name.lower() for name, _ in headers]

        self.assertEqual(status, 500)
        self.assertNotIn("location", names)
        self.assertNotIn("x-injected", names)
        self.assertEqual(
            body,
            b"500: Igor has encountered a complication.",
        )

    def test_protocol_relative_destination(self):
        self.assert_rejected("'//evil.example/path'")

    def test_crlf_header_injection(self):
        self.assert_rejected(
            "'/safe' || char(13,10) || 'X-Injected: yes'"
        )

    def test_backslash_destination(self):
        self.assert_rejected("'/back' || char(92) || 'slash'")

    def test_unicode_destination(self):
        self.assert_rejected("'/caf' || char(233)")

    def test_null_destination(self):
        self.assert_rejected("NULL")

    def test_oversized_destination(self):
        self.assert_rejected("'/' || replace(hex(zeroblob(512)), '00', 'a')")

    def test_location_on_http_200_rejected(self):
        self.assert_rejected("'/safe'", status_sql="200")

    def test_location_on_http_404_rejected(self):
        self.assert_rejected("'/safe'", status_sql="404")

    def test_valid_local_destination(self):
        status, headers, body = self.request_with_location(
            "'/valid_path-1.0~test'"
        )
        headers = dict(headers)

        self.assertEqual(status, 302)
        self.assertEqual(
            headers.get("Location"),
            "/valid_path-1.0~test",
        )
        self.assertEqual(body, b"")


if __name__ == "__main__":
    unittest.main()
